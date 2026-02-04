from celery import shared_task
from django.conf import settings
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
