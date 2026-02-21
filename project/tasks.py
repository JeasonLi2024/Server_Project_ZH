from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db.models import F, Q
from .models import Requirement
from .services import get_or_create_collection, delete_requirement_vectors, sync_requirement_vectors, sync_raw_docs_auto
import logging
import os
import time
from pymilvus import utility

logger = logging.getLogger(__name__)

COLLECTION_EMBEDDINGS = 'project_embeddings'
COLLECTION_RAW_DOCS = 'project_raw_docs'

@shared_task
def sync_requirement_views_to_db():
    """
    定时任务：将 Redis 中的需求浏览量缓冲同步回 MySQL
    建议执行频率：每 5 分钟执行一次
    """
    logger.info("Starting sync_requirement_views_to_db task...")
    try:
        # 1. 扫描 Redis 中所有浏览量缓冲的 key
        # 注意：keys 命令在生产环境慎用，如果 key 数量巨大建议使用 scan_iter
        # pattern: requirement_views_buffer_*
        if hasattr(cache, 'keys'):
            keys = cache.keys("requirement_views_buffer_*")
        elif hasattr(cache, 'iter_keys'):
            keys = list(cache.iter_keys("requirement_views_buffer_*"))
        else:
            # 如果 cache backend 不支持 keys/iter_keys (如 Memcached)，则无法自动扫描
            # 需要在写入时维护一个 key 集合，这里假设是 Redis
            # 尝试使用 django-redis 的原生 client
            try:
                from django_redis import get_redis_connection
                con = get_redis_connection("default")
                # 使用 scan_iter 避免阻塞
                keys = [k.decode('utf-8') for k in con.scan_iter("requirement_views_buffer_*")]
            except ImportError:
                logger.warning("django-redis not installed or keys not supported, skipping sync.")
                return "Skipped (backend not supported)"

        if not keys:
            logger.info("No views to sync.")
            return "No views to sync"

        count = 0
        for key in keys:
            try:
                # 解析 requirement_id
                # key format: requirement_views_buffer_123
                # 注意：django-redis 的 keys 可能会带上前缀 (prefix:version:key)
                # 这里做简单处理，提取最后一部分数字
                import re
                match = re.search(r'requirement_views_buffer_(\d+)', key)
                if not match:
                    continue
                
                req_id = int(match.group(1))
                
                # 获取并删除 key (原子操作 getset 或者 get + delete)
                # 为防止并发丢失，使用 getset (getset 将 key 设为 0 并返回旧值)
                # 但 cache 接口通常没有 getset，这里使用 get + delete 的简单策略
                # 风险：在 get 和 delete 之间如果有新写入，会丢失这部分计数
                # 优化策略：使用 pipeline 或者 lua 脚本，或者只 decr
                
                # 简单策略：读取 -> 数据库 + N -> Redis decr N
                # 这样即使有新写入，也只会保留在 Redis 中等待下次同步
                
                # 获取当前缓冲值
                views_to_add = cache.get(key)
                if not views_to_add:
                    continue
                
                views_to_add = int(views_to_add)
                
                if views_to_add > 0:
                    # 更新数据库 (F 表达式原子更新)
                    Requirement.objects.filter(id=req_id).update(views=F('views') + views_to_add)
                    
                    # Redis 中减去已同步的值 (decr)
                    try:
                        cache.decr(key, views_to_add)
                        # 如果减到 0 或负数，删除 key 以节省空间
                        # (由于并发，可能减完后变成负数或者还有剩余，这里简单判断)
                        new_val = cache.get(key)
                        if new_val is not None and int(new_val) <= 0:
                            cache.delete(key)
                    except Exception:
                        # 如果不支持 decr，直接 delete (会有微小丢失风险)
                        cache.delete(key)
                    
                    count += 1
            except Exception as e:
                logger.error(f"Error syncing key {key}: {e}")
                continue
                
        logger.info(f"Synced views for {count} requirements.")
        return f"Synced {count} requirements"
        
    except Exception as e:
        logger.error(f"Error in sync_requirement_views_to_db: {e}")
        return f"Error: {e}"


@shared_task
def sync_all_requirement_vectors():
    """
    全量校对任务：
    1. 扫描 MySQL 中所有有效状态的需求
    2. 扫描 Milvus 中所有向量的 project_id
    3. 补全 MySQL 有但 Milvus 无的
    4. 删除 Milvus 有但 MySQL 无（或状态无效）的
    """
    logger.info("Starting full vector sync task...")
    
    # 获取 MySQL 中的有效需求 ID
    VALID_STATUSES = ['under_review', 'in_progress', 'completed', 'paused']
    valid_reqs = Requirement.objects.filter(status__in=VALID_STATUSES).values_list('id', flat=True)
    valid_ids_set = set(valid_reqs)
    
    # 检查 Milvus 集合
    for col_name in [COLLECTION_EMBEDDINGS, COLLECTION_RAW_DOCS]:
        try:
            collection = get_or_create_collection(col_name)
            
            # 获取所有 project_id
            # 使用 Query Iterator 处理大数据集
            # 假设数据量在万级以上，使用 iterator 分批获取
            milvus_pids = set()
            iterator = collection.query_iterator(
                batch_size=1000, 
                expr="id > 0", 
                output_fields=["project_id"]
            )
            
            while True:
                result = iterator.next()
                if not result:
                    iterator.close()
                    break
                for r in result:
                    milvus_pids.add(r['project_id'])
            
            # 1. 找出需要删除的 (Milvus 有，但 MySQL 没有或无效)
            to_delete = milvus_pids - valid_ids_set
            if to_delete:
                logger.info(f"Found {len(to_delete)} stale records in {col_name}, deleting...")
                ids_str = ','.join(str(pid) for pid in to_delete)
                collection.delete(f"project_id in [{ids_str}]")
                
            # 2. 找出需要补全的 (MySQL 有，但 Milvus 没有)
            # 仅针对 project_embeddings (推荐库) 进行自动补全
            # project_raw_docs (QA库) 通常依赖文件上传，不便自动补全
            if col_name == COLLECTION_EMBEDDINGS:
                to_add = valid_ids_set - milvus_pids
                if to_add:
                    logger.info(f"Found {len(to_add)} missing records in {col_name}, syncing...")
                    for pid in to_add:
                        try:
                            req = Requirement.objects.get(id=pid)
                            sync_requirement_vectors(req)
                        except Requirement.DoesNotExist:
                            continue
                            
        except Exception as e:
            logger.error(f"Error syncing collection {col_name}: {e}")
            
    logger.info("Full vector sync task completed.")


@shared_task
def cleanup_temp_cover_images():
    """
    清理超过24小时的临时封面图片
    目录: MEDIA_ROOT/cover/tmp/
    """
    logger.info("Starting cleanup_temp_cover_images task...")
    
    try:
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'cover', 'tmp')
        if not os.path.exists(temp_dir):
            logger.info(f"Temp directory {temp_dir} does not exist, skipping.")
            return "Temp directory not found"
            
        current_time = time.time()
        # 24小时 = 24 * 3600 秒
        expiration_time = 24 * 3600
        
        deleted_count = 0
        error_count = 0
        
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            
            # 确保是文件
            if not os.path.isfile(file_path):
                continue
                
            # 检查最后修改时间
            file_mtime = os.path.getmtime(file_path)
            if current_time - file_mtime > expiration_time:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting temp file {file_path}: {e}")
                    error_count += 1
                    
        logger.info(f"Cleanup completed. Deleted: {deleted_count}, Errors: {error_count}")
        return f"Deleted {deleted_count} files"
        
    except Exception as e:
        logger.error(f"Error in cleanup_temp_cover_images: {e}")
        return f"Error: {e}"

@shared_task
def sync_requirement_vectors_task(requirement_id):
    """
    异步同步需求向量 (Semantic)
    """
    try:
        req = Requirement.objects.get(id=requirement_id)
        sync_requirement_vectors(req)
    except Requirement.DoesNotExist:
        logger.warning(f"Requirement {requirement_id} not found for vector sync")
    except Exception as e:
        logger.error(f"Error in sync_requirement_vectors_task: {e}")

@shared_task
def sync_raw_docs_auto_task(requirement_id):
    """
    异步同步需求 Raw Docs (QA)
    """
    try:
        req = Requirement.objects.get(id=requirement_id)
        sync_raw_docs_auto(req)
    except Requirement.DoesNotExist:
        logger.warning(f"Requirement {requirement_id} not found for raw docs sync")
    except Exception as e:
        logger.error(f"Error in sync_raw_docs_auto_task: {e}")

@shared_task
def delete_requirement_vectors_task(requirement_id):
    """
    异步删除需求向量
    """
    try:
        delete_requirement_vectors(requirement_id)
    except Exception as e:
        logger.error(f"Error in delete_requirement_vectors_task: {e}")

@shared_task
def update_user_dynamic_tags_task(user_id, requirement_id, action_type):
    """
    更新用户动态标签权重
    action_type: 'view' (+1), 'favorite' (+3), 'apply' (+5)
    """
    if not user_id or not requirement_id:
        return
        
    try:
        from django.core.cache import cache
        from project.models import Requirement
        import random
        
        # 1. 获取需求标签
        try:
            req = Requirement.objects.prefetch_related('tag1', 'tag2').get(id=requirement_id)
        except Requirement.DoesNotExist:
            return
            
        # 2. 确定权重
        weights = {
            'view': 1.0,
            'favorite': 3.0,
            'apply': 5.0
        }
        score_add = weights.get(action_type, 1.0)
        score_add_tag2 = score_add
        if action_type == 'view':
            score_add_tag2 = 0.5
        
        # 3. 更新 Redis
        redis_key = f"user:dynamic_tags:{user_id}"
        
        # 获取 redis client
        redis_client = None
        if hasattr(cache, 'client') and hasattr(cache.client, 'get_client'):
            redis_client = cache.client.get_client()
        elif hasattr(cache, '_cache') and hasattr(cache._cache, 'get_client'):
            redis_client = cache._cache.get_client()
            
        if not redis_client:
            logger.warning("Redis client not available for dynamic tags update")
            return
            
        pipeline = redis_client.pipeline()
        
        # 处理 Tag1 (兴趣/领域)
        for tag in req.tag1.all():
            field = f"tag1_{tag.id}"
            pipeline.hincrbyfloat(redis_key, field, score_add)
            
        # 处理 Tag2 (技能)
        for tag in req.tag2.all():
            field = f"tag2_{tag.id}"
            pipeline.hincrbyfloat(redis_key, field, score_add_tag2)
            
        # 4. 衰减机制：每次更新时有 10% 概率触发全量衰减 (x 0.95)
        # 这样避免每次请求都读取全量并重写，又能保证长期不膨胀
        if random.random() < 0.1:
            all_tags = redis_client.hgetall(redis_key)
            if all_tags:
                decay_pipeline = redis_client.pipeline()
                for field, score in all_tags.items():
                    try:
                        new_score = float(score) * 0.95
                        # 如果分数过小 (<0.1)，直接删除，清理空间
                        if new_score < 0.1:
                            decay_pipeline.hdel(redis_key, field)
                        else:
                            decay_pipeline.hset(redis_key, field, new_score)
                    except ValueError:
                        pass
                decay_pipeline.execute()
            
        # 执行增量 pipeline
        pipeline.execute()
        
        # 保持有效期
        redis_client.expire(redis_key, 7 * 24 * 3600)
        
        logger.info(f"Updated dynamic tags for user {user_id} on req {requirement_id} ({action_type})")
        
    except Exception as e:
        logger.error(f"Error updating dynamic tags: {e}")

@shared_task
def generate_daily_candidates_task(user_id=None):
    """
    生成每日推荐候选集 (Base Pool)
    如果指定 user_id，则只为该用户生成
    如果不指定，则为所有活跃学生用户生成 (批量)
    活跃定义: 账号启用且最近7天内登录过
    """
    from user.models import Student
    from project.services import RecommendationService
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        if user_id:
            logger.info(f"Starting daily candidate generation for user {user_id}")
            RecommendationService.generate_candidates(user_id)
        else:
            # 批量处理所有活跃学生
            # 定义活跃：最近7天登录过
            seven_days_ago = timezone.now() - timedelta(days=7)
            
            # 筛选条件: 用户激活 AND (最近7天登录 OR 刚刚注册)
            # 注意：刚注册的用户 last_login 可能为空，但 date_joined 是新的
            students = Student.objects.select_related('user').filter(
                user__is_active=True
            ).filter(
                Q(user__last_login__gte=seven_days_ago) | 
                Q(user__date_joined__gte=seven_days_ago)
            )
            
            logger.info(f"Starting daily candidate generation for {students.count()} active students")
            
            for student in students:
                # 为避免阻塞 worker 太久，可以再次 dispatch 子任务，或者在这里顺序执行
                # 鉴于用户量可能较大，建议 dispatch 子任务
                generate_daily_candidates_task.delay(student.user.id)
                
    except Exception as e:
        logger.error(f"Error in generate_daily_candidates_task: {e}")

@shared_task
def refresh_realtime_candidates_task(user_id):
    """
    刷新实时推荐候选集 (Incremental Update)
    触发时机：用户行为积累或定时
    """
    from project.services import RecommendationService
    
    try:
        if not user_id:
            return
            
        logger.info(f"Refreshing realtime candidates for user {user_id}")
        # 复用核心逻辑，重新生成候选集并覆盖缓存
        # 由于 generate_candidates 已经包含了动态画像和双路召回，
        # 重新运行它就是"刷新"
        RecommendationService.generate_candidates(user_id)
        
    except Exception as e:
        logger.error(f"Error in refresh_realtime_candidates_task: {e}")
