import logging
import pytz
import os
import hashlib
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F, Q, Count, Sum, Case, When, IntegerField, FloatField
from django.db.models.functions import TruncWeek, Cast, Log
from datetime import datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Requirement, Resource, File
from user.models import OrganizationUser, User, Tag1
from .serializers import (
    RequirementSerializer, RequirementCreateSerializer, RequirementUpdateSerializer,
    ResourceSerializer, ResourceCreateSerializer, ResourceUpdateSerializer
)
from common_utils import APIResponse, format_validation_errors, paginate_queryset, build_media_url
from django.utils import timezone
from .ai_utils import generate_poster_images, save_temp_images
from django.core.cache import cache

from user.services import UserHistoryService
from project.services import (
    search_similar_requirements, 
    get_vectors_by_ids, 
    generate_embedding,
    EmbeddingService
)
import numpy as np

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_requirement_statistics(request):
    """
    获取当前用户所属组织的需求统计数据接口
    
    统计截止当天最近七周发布的需求总数、状态分布和每周发布数量。
    系统会自动根据用户的组织身份确定organization_id。
    """
    try:
        user = request.user
        # 检查用户是否为组织用户并获取组织ID
        try:
            org_user = OrganizationUser.objects.get(user=user)
            organization_id = org_user.organization_id
        except OrganizationUser.DoesNotExist:
            return APIResponse.forbidden("只有组织用户才能访问需求统计数据")
        
        # 使用Shanghai时区计算当前日期
        shanghai_tz = pytz.timezone('Asia/Shanghai')
        today = timezone.now().astimezone(shanghai_tz).date()
        seven_weeks_ago = today - timedelta(weeks=7)
        
        # 使用datetime范围查询避免时区问题
        start_datetime = timezone.make_aware(timezone.datetime.combine(seven_weeks_ago, timezone.datetime.min.time()))
        end_datetime = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        
        # 过滤该组织的最近七周需求（包含今天）
        queryset = Requirement.objects.filter(
            organization_id=organization_id,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        )
        
        # 总需求数
        total_requirements = queryset.count()
        
        # 状态统计 - 统计所有状态的需求数量
        status_counts = queryset.aggregate(
            under_review=Count('id', filter=Q(status='under_review')),
            review_failed=Count('id', filter=Q(status='review_failed')),

            in_progress=Count('id', filter=Q(status='in_progress')),
            completed=Count('id', filter=Q(status='completed')),
            paused=Count('id', filter=Q(status='paused'))
        )
        
        dates = []
        publish_count = []
        
        # 计算7个周的结束日期（从今天开始，每周往前推7天）
        week_end_dates = []
        current_end = today
        for i in range(7):
            week_end_dates.append(current_end)
            current_end = current_end - timedelta(weeks=1)
        
        # 反转列表，使其按时间顺序排列（最早的周在前）
        week_end_dates.reverse()
        
        # 为每周生成标签和统计数据
        for i, week_end in enumerate(week_end_dates):
            dates.append(week_end.strftime('%m-%d'))
            
            # 计算该周的开始日期（7天前，即上一个周的结束日期+1天）
            if i == 0:
                # 第一周的开始日期是7周前
                week_start = seven_weeks_ago
            else:
                # 其他周的开始日期是上一周的结束日期+1天
                week_start = week_end_dates[i-1] + timedelta(days=1)
            
            # 转换为datetime范围进行查询
            week_start_dt = timezone.make_aware(timezone.datetime.combine(week_start, timezone.datetime.min.time()))
            week_end_dt = timezone.make_aware(timezone.datetime.combine(week_end, timezone.datetime.max.time()))
            
            # 统计该周内发布的需求数量
            week_count = queryset.filter(
                created_at__gte=week_start_dt,
                created_at__lte=week_end_dt
            ).count()
            
            publish_count.append(week_count)
        
        # 确保正好7个数据点
        if len(dates) > 7:
            dates = dates[:7]
            publish_count = publish_count[:7]
        
        data = {
            'totalRequirements': total_requirements,
            'statusCounts': {
                'under_review': status_counts['under_review'],
                'review_failed': status_counts['review_failed'],
    
                'in_progress': status_counts['in_progress'],
                'completed': status_counts['completed'],
                'paused': status_counts['paused']
            },
            'chartData': {
                'dates': dates,
                'publishCount': publish_count
            }
        }
        
        return APIResponse.success(data, "获取成功")
    except Exception as e:
        logger.error(f"获取需求统计失败: {str(e)}")
        return APIResponse.server_error('获取失败，请稍后重试', errors={'exception': str(e)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_requirement(request):
    """
    发布需求接口
    
    创建新的需求记录，支持设置标题、描述、领域、标签、关联资源等信息。
    只要是企业用户（组织成员）即可发布需求。
    如果上传的文件中包含PDF文件，会自动调用PDF处理服务进行向量化存储。
    
    请求参数:
    - title: 需求标题 (必填)
    - brief: 需求简介 (必填)
    - description: 详细描述 (必填)
    - status: 需求状态 (可选，默认为'under_review')
    - organization: 组织ID (必填)
    
    - finish_time: 完成时间 (可选)
    - budget: 预算 (可选)
    - people_count: 人数需求 (可选)
    - tag1_ids: 兴趣标签ID列表 (可选)
    - tag2_ids: 能力标签ID列表 (可选)
    - resource_ids: 关联资源ID列表 (可选)
    - file_ids: 文件ID列表 (可选)
    """
    try:
        # 如果是前端表单直接提交，通常不会传status，默认为under_review
        # 如果是Agent或其他方式，可以显式传 'draft'
        
        # 验证status是否合法
        status = request.data.get('status')
        if status and status not in [choice[0] for choice in Requirement.STATUS_CHOICES]:
             return APIResponse.validation_error(f"无效的状态: {status}")

        serializer = RequirementCreateSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return APIResponse.validation_error(
                format_validation_errors(serializer.errors)
            )
        
        # 创建需求
        with transaction.atomic():
            requirement = serializer.save()
            
            # 这里的显式 PDF 处理已移除，转由 project/signals.py 中的 m2m_changed 和 post_save 自动处理
            # 这样可以统一管理 Semantic Embeddings 和 Raw Docs 的同步逻辑，并支持多种文件格式
            
            # 使用详情序列化器返回完整信息
            detail_serializer = RequirementSerializer(
                requirement, 
                context={'request': request}
            )
            
            return APIResponse.success(
                detail_serializer.data, 
                "需求发布成功", 
                201
            )
            
    except Exception as e:
        logger.error(f"发布需求失败: {str(e)}")
        return APIResponse.server_error(
            '发布需求失败，请稍后重试',
            errors={'exception': str(e)}
        )
# 辅助函数 _process_requirement_pdfs 已弃用，逻辑移至 project/services.py:sync_raw_docs_auto



@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_requirement(request, requirement_id):
    """
    修改需求接口
    
    更新指定需求的信息，支持对所有关键字段的修改。
    只允许需求发布者、同一组织管理员和同一组织所有者修改需求。
    
    URL参数:
    - requirement_id: 需求ID
    
    请求参数:
    - title: 需求标题 (可选)
    - brief: 需求简介 (可选)
    - description: 详细描述 (可选)
    - status: 需求状态 (可选)
    - organization: 组织ID (可选)
    
    - finish_time: 完成时间 (可选)
    - budget: 预算 (可选)
    - people_count: 人数需求 (可选)
    - tag1_ids: 兴趣标签ID列表 (可选)
    - tag2_ids: 能力标签ID列表 (可选)
    - resource_ids: 关联资源ID列表 (可选)
    - file_ids: 文件ID列表 (可选)
    """
    try:
        # 获取需求对象（不锁定，用于权限检查）
        requirement = get_object_or_404(Requirement, id=requirement_id)
        
        # 检查权限：只允许需求发布者、同一组织管理员和同一组织所有者修改
        user = request.user
        
        # 检查是否是需求发布者
        if requirement.publish_people.user == user:
            # 需求发布者有权限修改
            pass
        else:
            # 检查是否是同一组织的管理员或所有者
            try:
                org_user = OrganizationUser.objects.get(
                    user=user, 
                    organization=requirement.organization
                )
                # 只有管理员(admin)和所有者(owner)可以修改其他人发布的需求
                if org_user.permission not in ['admin', 'owner']:
                    return APIResponse.forbidden("只有需求发布者、组织管理员或组织所有者可以修改需求")
            except OrganizationUser.DoesNotExist:
                return APIResponse.forbidden("您不是此需求所属组织的成员")
        
        # 使用PATCH方法支持部分更新
        partial = request.method == 'PATCH'
        
        # 先进行数据验证，减少锁定时间
        temp_serializer = RequirementUpdateSerializer(
            requirement,
            data=request.data,
            partial=partial,
            context={'request': request}
        )
        
        if not temp_serializer.is_valid():
            return APIResponse.validation_error(
                errors=format_validation_errors(temp_serializer.errors),
                message="数据验证失败"
            )
        
        # 只在保存时使用悲观锁，缩短事务范围
        with transaction.atomic():
            # 锁定需求记录
            requirement = get_object_or_404(
                Requirement.objects.select_for_update(),
                id=requirement_id
            )
            
            # 重新创建序列化器进行保存
            serializer = RequirementUpdateSerializer(
                requirement,
                data=request.data,
                partial=partial,
                context={'request': request}
            )
            
            # 由于之前已经验证过，这里应该不会失败
            if not serializer.is_valid():
                raise ValueError(format_validation_errors(serializer.errors))
            
            updated_requirement = serializer.save()
            
            # 刷新实例以获取最新的数据库状态
            updated_requirement.refresh_from_db()
            
            # 使用详情序列化器返回完整信息
            detail_serializer = RequirementSerializer(
                updated_requirement,
                context={'request': request}
            )
            
            return APIResponse.success(
                detail_serializer.data,
                "需求更新成功"
            )
            
    except Exception as e:
        logger.error(f"更新需求失败: {str(e)}")
        return APIResponse.server_error(
            '更新需求失败，请稍后重试',
            errors={'exception': str(e)}
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_requirement(request, requirement_id):
    """
    删除需求接口
    
    删除指定的需求记录，同时删除关联的文件（实际删除），但保留关联的资源。
    只允许需求发布者、同一组织管理员和同一组织所有者删除需求。
    
    URL参数:
    - requirement_id: 需求ID
    
    注意:
    - 删除需求时会保留所有关联的资源（Resource），只清除关联关系
    - 删除需求时会同时删除关联的文件（File），包括物理文件和数据库记录
    - 删除操作不可逆，请谨慎操作
    """
    try:
        # 获取需求对象
        requirement = get_object_or_404(Requirement, id=requirement_id)
        
        # 检查权限：只允许需求发布者、同一组织管理员和同一组织所有者删除
        user = request.user
        
        # 检查是否是需求发布者
        if requirement.publish_people.user == user:
            # 需求发布者有权限删除
            pass
        else:
            # 检查是否是同一组织的管理员或所有者
            try:
                org_user = OrganizationUser.objects.get(
                    user=user, 
                    organization=requirement.organization
                )
                # 只有管理员(admin)和所有者(owner)可以删除其他人发布的需求
                if org_user.permission not in ['admin', 'owner']:
                    return APIResponse.forbidden("只有需求发布者、组织管理员或组织所有者可以删除需求")
            except OrganizationUser.DoesNotExist:
                return APIResponse.forbidden("您不是此需求所属组织的成员")
        
        # 删除需求（使用悲观锁防止并发问题）
        with transaction.atomic():
            # 锁定需求记录
            requirement = get_object_or_404(
                Requirement.objects.select_for_update(),
                id=requirement_id
            )
            
            # 保存需求信息用于返回
            requirement_info = {
                'id': requirement.id,
                'title': requirement.title,
                'organization': requirement.organization.name,
                'status': requirement.get_status_display()
            }
            
            # 获取关联的文件列表（用于实际删除）
            associated_files = list(requirement.files.all())
            deleted_files_info = []
            
            # 删除关联的文件（实际删除文件和数据库记录）
            for file_obj in associated_files:
                file_info = {
                    'id': file_obj.id,
                    'name': file_obj.name,
                    'path': file_obj.path
                }
                
                # 如果是实际文件（非文件夹），删除物理文件
                if not file_obj.is_folder and file_obj.real_path:
                    try:
                        import os
                        from django.conf import settings
                        
                        # 构建完整的文件路径
                        full_path = os.path.join(settings.MEDIA_ROOT, file_obj.real_path)
                        if os.path.exists(full_path):
                            os.remove(full_path)
                            logger.info(f"已删除物理文件: {full_path}")
                    except Exception as e:
                        logger.warning(f"删除物理文件失败: {file_obj.real_path}, 错误: {str(e)}")
                
                # 删除数据库中的文件记录
                file_obj.delete()
                deleted_files_info.append(file_info)
            
            # 删除海报封面文件
            if requirement.cover:
                try:
                    import os
                    from django.conf import settings
                    
                    # 获取封面文件的完整路径
                    cover_path = requirement.cover.path
                    if os.path.exists(cover_path):
                        os.remove(cover_path)
                        logger.info(f"已删除海报封面文件: {cover_path}")
                except Exception as e:
                    logger.warning(f"删除海报封面文件失败: {requirement.cover.name}, 错误: {str(e)}")

            # 删除需求（关联的资源会被保留，只清除关联关系）
            # Django会自动处理多对多关系的清理
            # 关联的Resource对象不会被删除，只会清除关联关系
            requirement.delete()
            
            return APIResponse.success(
                {
                    'deleted_requirement': requirement_info,
                    'deleted_files': deleted_files_info,
                    'deleted_files_count': len(deleted_files_info),
                    'message': f'需求已删除，同时删除了{len(deleted_files_info)}个关联文件，关联的资源已保留'
                },
                "需求删除成功"
            )
            
    except Exception as e:
        logger.error(f"删除需求失败: {str(e)}")
        return APIResponse.server_error(
            '删除需求失败，请稍后重试',
            errors={'exception': str(e)}
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_requirement(request, requirement_id):
    """
    获取需求详情接口
    
    获取指定需求的详细信息，包括关联的标签、资源和文件。
    
    URL参数:
    - requirement_id: 需求ID
    """
    try:
        # 获取需求对象，使用select_related和prefetch_related优化查询
        requirement = get_object_or_404(
            Requirement.objects.select_related(
                'organization', 'publish_people__user'
            ).prefetch_related(
                'tag1', 'tag2', 'resources', 'files'
            ),
            id=requirement_id
        )
        
        # 增加浏览量（使用Redis缓冲 + 异步写入策略）
        # 防抖机制：同一用户在24小时内访问同一需求只计算一次浏览量
        
        # 记录用户已访问标记
        user_viewed_key = f"requirement_viewed_{requirement_id}_{request.user.id}"
        has_viewed = cache.get(user_viewed_key)
        
        # 记录浏览历史 (Redis ZSet) - 无论是否增加浏览量，只要访问了就记录（更新时间戳）
        UserHistoryService.record_view(request.user.id, requirement_id, 'requirement')
        
        # 异步更新动态标签权重
        try:
            from project.tasks import update_user_dynamic_tags_task
            update_user_dynamic_tags_task.delay(request.user.id, requirement_id, 'view')
        except Exception as e:
            logger.error(f"触发动态标签更新任务失败: {e}")
        
        if not has_viewed:
            # 如果未访问过，增加浏览量并设置访问标记
            try:
                # 1. 设置访问标记，有效期24小时
                cache.set(user_viewed_key, 1, timeout=86400)
                
                # 2. 写入 Redis 增量
                cache_key = f"requirement_views_buffer_{requirement_id}"
                
                # 使用 incr 原子操作，如果 key 不存在会自动创建并初始化为 0 后加 1
                # timeout 设置为 None 表示不过期（或者设置一个较长时间，如 24 小时）
                # 注意：Django 的 cache backend 可能会有不同的 incr 行为，Redis backend 通常支持
                try:
                    cache.incr(cache_key, 1)
                except ValueError:
                    # 如果 key 不存在，incr 可能会抛出 ValueError (取决于后端实现)
                    # 或者如果 key 存在但不是 int 类型
                    cache.set(cache_key, 1, timeout=86400)
                except Exception:
                     # 尝试降级
                    current_val = cache.get(cache_key, 0)
                    cache.set(cache_key, int(current_val) + 1, timeout=86400)
            except Exception as e:
                logger.warning(f"Redis 浏览量写入失败: {str(e)}")
                # 再次降级：直接写库（兜底）
                # 注意：直接写库会失去防抖的高效性，但在Redis失败时是必要的
                Requirement.objects.filter(id=requirement_id).update(views=F('views') + 1)
                requirement.refresh_from_db(fields=['views'])
        else:
            logger.info(f"用户 {request.user.id} 在24小时内已访问过需求 {requirement_id}，跳过浏览量增加")
        
        # 2. 读时合并：从 Redis 获取增量，叠加到数据库的 views 上
        try:
            cache_key = f"requirement_views_buffer_{requirement_id}"
            buffer_views = cache.get(cache_key, 0)
            if buffer_views:
                requirement.views += int(buffer_views)
        except Exception:
            pass  # 读取缓存失败不影响主流程
        
        # 序列化返回
        serializer = RequirementSerializer(
            requirement,
            context={'request': request}
        )
        
        return APIResponse.success(
            serializer.data,
            "获取需求详情成功"
        )
        
    except Exception as e:
        logger.error(f"获取需求详情失败: {str(e)}")
        return APIResponse.server_error(
            '获取需求详情失败，请稍后重试',
            errors={'exception': str(e)}
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_requirements(request):
    """
    获取需求列表接口
    
    获取需求列表，支持分页、筛选、排序和搜索。
    
    查询参数:
    - page: 页码 (默认: 1)
    - page_size: 每页数量 (默认: 10, 最大: 100)
    - budget: 需求预算筛选（支持范围筛选，格式：min-max 或 单个值）
    - time: 需求发布时间筛选（支持单日和范围筛选，格式：YYYY-MM-DD 或 start_date-end_date）
    - status: 需求状态筛选
    - organization_id: 组织ID筛选
    - publisher_id: 发布者用户ID筛选（用于获取特定用户发布的需求）
    - sort_type: 排序字段（title/time/view）
    - sort_order: 排序方式（up升序/down降序）
    - keyword: 搜索关键词（可从需求标题、描述、tag1和tag2中模糊检索）
    """
    try:
        # 构建基础查询集，使用数据库索引优化
        queryset = Requirement.objects.select_related(
            'organization', 'publish_people__user'
        ).prefetch_related(
            'tag1', 'tag2', 'resources', 'files'
        )
        
        # 应用筛选条件
        # 状态筛选（支持多状态查询，用逗号分隔）
        status_filter = request.GET.get('status')
        if status_filter:
            # 支持多状态查询：status=pending,in_progress,completed
            status_list = [s.strip() for s in status_filter.split(',') if s.strip()]
            if len(status_list) == 1:
                # 单状态查询
                queryset = queryset.filter(status=status_list[0])
            elif len(status_list) > 1:
                # 多状态查询
                queryset = queryset.filter(status__in=status_list)
        
        # 组织筛选
        organization_id = request.GET.get('organization_id')
        if organization_id:
            try:
                queryset = queryset.filter(organization_id=int(organization_id))
            except (ValueError, TypeError):
                pass
        
        # 发布者筛选（新增）
        publisher_id = request.GET.get('publisher_id')
        if publisher_id:
            try:
                # 筛选 publish_people (OrganizationUser) 关联的 user 的 id
                queryset = queryset.filter(publish_people__user_id=int(publisher_id))
            except (ValueError, TypeError):
                pass
        
        # 预算范围筛选
        budget_filter = request.GET.get('budget')
        if budget_filter:
            try:
                if '-' in budget_filter:
                    # 范围筛选：min-max
                    budget_parts = budget_filter.split('-', 1)
                    if len(budget_parts) == 2:
                        min_budget_str = budget_parts[0].strip()
                        max_budget_str = budget_parts[1].strip()
                        
                        # 转换为数值进行比较
                        try:
                            min_budget = float(min_budget_str) if min_budget_str else 0
                            max_budget = float(max_budget_str) if max_budget_str else float('inf')
                            
                            # 构建复杂查询条件
                            budget_q = Q()
                            
                            # 获取所有需求，然后在Python中进行预算范围匹配
                            all_requirements = queryset.all()
                            matching_ids = []
                            
                            for req in all_requirements:
                                if req.budget:
                                    budget_str = req.budget.strip()
                                    if '-' in budget_str:
                                        # 数据库中存储的是范围格式，如"50-100"
                                        try:
                                            db_parts = budget_str.split('-', 1)
                                            db_min = float(db_parts[0].strip())
                                            db_max = float(db_parts[1].strip())
                                            
                                            # 检查范围是否有重叠
                                            if not (max_budget < db_min or min_budget > db_max):
                                                matching_ids.append(req.id)
                                        except (ValueError, IndexError):
                                            continue
                                    else:
                                        # 数据库中存储的是单个值
                                        try:
                                            db_budget = float(budget_str)
                                            if min_budget <= db_budget <= max_budget:
                                                matching_ids.append(req.id)
                                        except ValueError:
                                            continue
                            
                            if matching_ids:
                                queryset = queryset.filter(id__in=matching_ids)
                            else:
                                queryset = queryset.none()
                                
                        except ValueError:
                            # 如果转换失败，使用字符串匹配作为后备
                            queryset = queryset.filter(budget__icontains=budget_filter)
                else:
                    # 精确匹配或包含匹配
                    queryset = queryset.filter(budget__icontains=budget_filter)
            except Exception:
                pass
        
        # 时间范围筛选（基于created_at字段）
        time_filter = request.GET.get('time')
        if time_filter:
            try:
                # 检查是否为日期范围格式（YYYY-MM-DD-YYYY-MM-DD）
                if time_filter.count('-') >= 5:  # 至少包含两个完整日期的连字符
                    # 范围筛选：YYYY-MM-DD-YYYY-MM-DD
                    # 找到中间的分隔符位置
                    parts = time_filter.split('-')
                    if len(parts) >= 6:  # 至少有6个部分（年-月-日-年-月-日）
                        # 重新组合日期
                        start_date = f"{parts[0]}-{parts[1]}-{parts[2]}"
                        end_date = f"{parts[3]}-{parts[4]}-{parts[5]}"
                        if start_date:
                            # 转换为datetime对象（当天开始时间）
                            start_datetime = timezone.make_aware(
                                timezone.datetime.strptime(start_date, '%Y-%m-%d').replace(
                                    hour=0, minute=0, second=0, microsecond=0
                                )
                            )
                            queryset = queryset.filter(created_at__gte=start_datetime)
                        if end_date:
                            # 转换为datetime对象（当天结束时间）
                            end_datetime = timezone.make_aware(
                                timezone.datetime.combine(
                                    timezone.datetime.strptime(end_date, '%Y-%m-%d').date(),
                                    timezone.datetime.max.time()
                                )
                            )
                            queryset = queryset.filter(created_at__lte=end_datetime)
                else:
                    # 单日筛选 - 使用时间范围避免时区问题
                    try:
                        target_date = timezone.datetime.strptime(time_filter, '%Y-%m-%d').date()
                        start_datetime = timezone.make_aware(
                            timezone.datetime.combine(target_date, timezone.datetime.min.time())
                        )
                        end_datetime = timezone.make_aware(
                            timezone.datetime.combine(target_date, timezone.datetime.max.time())
                        )
                        queryset = queryset.filter(
                            created_at__gte=start_datetime,
                            created_at__lte=end_datetime
                        )
                    except ValueError:
                        # 如果日期格式不正确，忽略筛选
                        pass
            except Exception:
                pass
        
        # 关键词搜索（支持标题、描述、tag1、tag2）
        keyword = request.GET.get('keyword')
        if keyword:
            search_q = Q(title__icontains=keyword) | Q(description__icontains=keyword)
            # 搜索tag1和tag2
            search_q |= Q(tag1__value__icontains=keyword) | Q(tag2__category__icontains=keyword) | Q(tag2__subcategory__icontains=keyword) | Q(tag2__specialty__icontains=keyword)
            queryset = queryset.filter(search_q).distinct()
        
        # 排序处理（针对海量数据优化）
        sort_type = request.GET.get('sort_type')
        # 如果未指定排序方式，根据用户类型设置默认值
        if not sort_type:
            # 智能排序策略：学生用户默认使用推荐排序，其他用户默认按时间排序
            if request.user.is_authenticated and getattr(request.user, 'user_type', '') == 'student':
                sort_type = 'recommend'
            else:
                sort_type = 'time'

        sort_order = request.GET.get('sort_order', 'down')  # 默认降序
        
        # 推荐排序逻辑（仅针对学生用户）
        if sort_type == 'recommend' and request.user.is_authenticated and getattr(request.user, 'user_type', '') == 'student':
            # 获取分页参数用于生成缓存键
            try:
                page_num = int(request.GET.get('page', 1))
                page_size_num = int(request.GET.get('page_size', 10))
            except (ValueError, TypeError):
                page_num = 1
                page_size_num = 10

            # -------------------------------------------------------------------------
            # 新逻辑：双路召回 (Dual-Path Retrieval) 与 动态画像 (Dynamic User Profiling)
            # 使用 RecommendationService 统一处理
            # -------------------------------------------------------------------------
            
            # 候选集缓存键：仅与用户ID相关，与筛选条件无关
            candidate_cache_key = f"recommend_candidates_{request.user.id}"
            candidate_ids = cache.get(candidate_cache_key)
            
            if not candidate_ids:
                try:
                    # 调用 Service 生成候选集
                    from project.services import RecommendationService
                    candidate_ids = RecommendationService.generate_candidates(request.user.id)
                    
                    # 写入缓存 (10分钟)
                    if candidate_ids:
                        cache.set(candidate_cache_key, candidate_ids, 600)
                    
                except Exception as e:
                    logger.error(f"双路推荐算法执行失败 (View): {str(e)}")
                    candidate_ids = []

            # 将当前的 queryset (已经应用了 filter) 限制在候选集范围内
            # 这就是 "在推荐结果中筛选" 的核心：取交集
            if candidate_ids:
                queryset = queryset.filter(id__in=candidate_ids)
                
                # 保持推荐顺序
                # 使用 Case/When 按照 candidate_ids 中的顺序排序
                preserved_order = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(candidate_ids)])
                queryset = queryset.order_by(preserved_order)
            else:
                # 如果候选集为空（极端情况），或者生成失败，降级为不限制范围，但依然按照时间排序
                queryset = queryset.order_by('-created_at')


            # -------------------------------------------------------------------------
            # 缓存处理：缓存最终的分页结果 (包含筛选状态)
            # -------------------------------------------------------------------------
            
            # 由于 "分页结果缓存" 容易导致筛选状态不一致、缓存键复杂且维护成本高，
            # 且我们已经引入了 "候选集缓存" 来分担计算压力，
            # 这里的第二层缓存可以移除，以确保数据实时性和筛选的准确性。
            
            # (移除原有的 cached_data 获取逻辑)

            # 如果没有命中页面缓存，继续执行后续的分页和序列化逻辑
            # 注意：下面的 annotate 逻辑其实对于排序已经不再需要了（因为我们已经强制指定了顺序），
            # 但是为了生成 recommendation_reason，我们还是需要计算分数的上下文
            
            try:
                # 获取用户浏览历史（用于去重）
                # 注意：这里我们获取全量历史ID，UserHistoryService 已经限制了 ZSet 最大长度为 1000
                viewed_ids = UserHistoryService.get_all_viewed_ids(request.user.id, 'requirement')
                
                # 软去重策略：
                # 不直接排除已读内容，而是将其排序权重降低（沉底）
                # 这样当没有新内容时，用户仍然可以看到已读的热门/相关内容，而不是空列表
                
                student = request.user.student_profile
                # 获取ID列表
                skill_ids = list(student.skills.values_list('id', flat=True))
                interest_ids = list(student.interests.values_list('id', flat=True))
                
                # 重新获取动态标签 (因为 view 可能会有延迟更新，这里再次读取可能也读不到最新的，
                # 但为了逻辑一致性，还是应该合并动态标签。或者为了性能直接复用上面的 combined_ids?)
                # 鉴于上面逻辑很长，这里直接复制获取逻辑或重构
                
                dynamic_tag1_ids = []
                dynamic_tag2_ids = []
                try:
                    redis_key = f"user:dynamic_tags:{request.user.id}"
                    redis_client = None
                    if hasattr(cache, 'client') and hasattr(cache.client, 'get_client'):
                        redis_client = cache.client.get_client()
                    elif hasattr(cache, '_cache') and hasattr(cache._cache, 'get_client'):
                        redis_client = cache._cache.get_client()
                        
                    if redis_client:
                        all_tags = redis_client.hgetall(redis_key)
                        for field, score in all_tags.items():
                            try:
                                field_str = field.decode('utf-8') if isinstance(field, bytes) else field
                                score_val = float(score)
                                if score_val >= 2.0:
                                    if field_str.startswith('tag1_'):
                                        dynamic_tag1_ids.append(int(field_str.split('_')[1]))
                                    elif field_str.startswith('tag2_'):
                                        dynamic_tag2_ids.append(int(field_str.split('_')[1]))
                            except:
                                pass
                except:
                    pass

                combined_skill_ids = list(set(skill_ids + dynamic_tag2_ids))
                combined_interest_ids = list(set(interest_ids + dynamic_tag1_ids))
                
                # 重新计算一次分数，仅用于生成推荐理由 (reasons)
                # 排序已经由 candidate_ids 决定了，这里不再 order_by
                
                # 冷启动处理
                if not combined_skill_ids and not combined_interest_ids:
                    now = timezone.now()
                    three_days_ago = now - timedelta(days=3)
                    seven_days_ago = now - timedelta(days=7)
                    
                    queryset = queryset.annotate(
                        freshness_score=Case(
                            When(created_at__gte=three_days_ago, then=50),
                            When(created_at__gte=seven_days_ago, then=20),
                            default=0,
                            output_field=IntegerField()
                        ),
                        hot_score=Log(F('views') + 1, 10) * 5
                    )
                    is_cold_start = True
                else:
                    is_cold_start = False
                    now = timezone.now()
                    three_days_ago = now - timedelta(days=3)
                    seven_days_ago = now - timedelta(days=7)
                    
                    queryset = queryset.annotate(
                        skill_score=Count('tag2', filter=Q(tag2__id__in=combined_skill_ids)) * 10,
                        interest_score=Count('tag1', filter=Q(tag1__id__in=combined_interest_ids)) * 5,
                        freshness_score=Case(
                            When(created_at__gte=three_days_ago, then=20),
                            When(created_at__gte=seven_days_ago, then=10),
                            default=0,
                            output_field=IntegerField()
                        ),
                        hot_score=Log(F('views') + 1, 10) * 2
                    )
                    
            except Exception as e:
                logger.warning(f"推荐理由上下文计算失败: {str(e)}")
                # 降级处理
                sort_type = 'time'
                
        # 如果不是推荐排序或推荐排序失败，使用常规排序

        if sort_type != 'recommend':
            # 构建排序字段
            sort_field_map = {
                'title': 'title',
                'time': 'created_at',  # 使用数据库时间戳字段，有索引
                'view': 'views'
            }
            
            sort_field = sort_field_map.get(sort_type, 'created_at')
            if sort_order == 'up':
                order_by = sort_field
            else:
                order_by = f'-{sort_field}'
            
            # 应用排序，使用数据库索引优化
            queryset = queryset.order_by(order_by)
        
        # 使用通用分页工具
        pagination_result = paginate_queryset(request, queryset, default_page_size=10)
        paginator = pagination_result['paginator']
        page_data = pagination_result['page_data']
        pagination_info = pagination_result['pagination_info']
        paginator_page = pagination_info['current_page']
        paginator_page_size = pagination_info['page_size']
        
        # 预取收藏状态数据，避免N+1查询
        favorited_requirements = set()
        if request.user.is_authenticated and hasattr(request.user, 'student_profile'):
            from .models import RequirementFavorite
            requirement_ids = [req.id for req in page_data]
            favorited_requirements = set(
                RequirementFavorite.objects.filter(
                    student=request.user.student_profile,
                    requirement_id__in=requirement_ids
                ).values_list('requirement_id', flat=True)
            )

        # 3. 批量读时合并：将 Redis 中的浏览量增量合并到列表数据中
        try:
            # 收集本页所有需求的 ID
            page_req_ids = [req.id for req in page_data]
            if page_req_ids:
                # 构造所有 keys
                cache_keys = [f"requirement_views_buffer_{rid}" for rid in page_req_ids]
                # 批量获取 (如果 cache backend 支持 get_many)
                if hasattr(cache, 'get_many'):
                    buffer_data = cache.get_many(cache_keys)
                else:
                    buffer_data = {k: cache.get(k) for k in cache_keys}
                
                # 更新内存中的对象 (不存库)
                for req in page_data:
                    key = f"requirement_views_buffer_{req.id}"
                    buffer_val = buffer_data.get(key, 0)
                    if buffer_val:
                        req.views += int(buffer_val)
        except Exception as e:
            logger.warning(f"列表页批量合并浏览量失败: {str(e)}")

        # 4. 生成推荐理由（仅针对推荐排序）
        if sort_type == 'recommend':
            for req in page_data:
                reasons = []
                
                # 如果是冷启动模式，只显示热门或近期
                if 'is_cold_start' in locals() and is_cold_start:
                    if req.views > 9:
                        reasons.append("热门需求")
                    # 判断近期
                    try:
                        req_date = req.created_at.date() if hasattr(req.created_at, 'date') else req.created_at
                        if (timezone.now().date() - req_date).days <= 7:
                            reasons.append("近期发布")
                    except Exception:
                        pass
                else:
                    # 检查评分注解是否存在
                    has_static_match = False
                    if (getattr(req, 'skill_score', 0) or 0) > 0:
                        reasons.append("技能匹配")
                        has_static_match = True
                    if (getattr(req, 'interest_score', 0) or 0) > 0:
                        reasons.append("兴趣匹配")
                        has_static_match = True
                    if (getattr(req, 'freshness_score', 0) or 0) > 0:
                        reasons.append("近期发布")
                        has_static_match = True
                    
                    # 热门需求：浏览量产生的热度分
                    if (getattr(req, 'hot_score', 0) or 0) > 2:
                        reasons.append("热门需求")
                        has_static_match = True
                        
                    # 如果没有静态匹配理由，且不是冷启动，则可能是语义推荐
                    # 我们没有直接传递 vector_score 到这里，但可以推断
                    if not has_static_match and not reasons:
                        reasons.append("语义推荐")
                
                req.recommendation_reason = reasons

        # 序列化
        serializer = RequirementSerializer(
            page_data,
            many=True,
            context={
                'request': request,
                'favorited_requirements': favorited_requirements
            }
        )
        
        response_data = {
            'requirements': serializer.data,
            'pagination': pagination_info
        }
        
        # 如果是推荐排序，写入缓存
        # (已移除第二层分页缓存，仅保留候选集缓存)


        return APIResponse.success(response_data, "获取需求列表成功")
        
    except Exception as e:
        logger.error(f"获取需求列表失败: {str(e)}")
        return APIResponse.server_error(
            '获取需求列表失败，请稍后重试',
            errors={'exception': str(e)}
        )


def _check_resource_permission(user, resource, action):
    """
    检查用户对资源的操作权限
    
    Args:
        user: 当前用户
        resource: 资源对象
        action: 操作类型 ('create', 'update', 'delete', 'read')
    
    Returns:
        bool: 是否有权限
    """
    if action == 'create':
        # 创建资源：只有组织用户可以创建
        if user.user_type != 'organization':
            return False
        
        # 检查用户是否属于已审核的组织
        try:
            org_user = OrganizationUser.objects.filter(user=user, status='approved').first()
            return org_user is not None
        except Exception:
            return False
    
    elif action in ['update', 'delete']:
        # 修改/删除资源：创建者、组织所有者或管理员
        if not resource:
            return False
        
        # 检查是否是资源创建者
        if resource.create_person.user == user:
            return True
        
        # 检查是否是组织所有者或管理员
        try:
            org_user = OrganizationUser.objects.get(
                user=user, 
                organization=resource.create_person.organization,
                status='approved'
            )
            return org_user.permission in ['owner', 'admin']
        except OrganizationUser.DoesNotExist:
            return False
    
    elif action == 'read':
        # 读取资源：根据资源状态和用户类型判断
        if not resource:
            return False
        
        # 已发布的资源所有认证用户都可以查看
        if resource.status == 'published':
            return True
        
        # 草稿资源只有创建者和同组织用户可以查看
        if resource.status == 'draft':
            # 检查是否是资源创建者
            if resource.create_person.user == user:
                return True
            
            # 检查是否是同组织用户
            try:
                org_user = OrganizationUser.objects.get(
                    user=user, 
                    organization=resource.create_person.organization,
                    status='approved'
                )
                return True
            except OrganizationUser.DoesNotExist:
                return False
        
        return False
    
    return False


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_resource(request):
    """
    发布新资源/资源草稿
    
    支持form-data表单上传，根据status字段判断是否为草稿
    草稿资源只对创建者和同组织用户可见
    """
    # 权限检查
    if not _check_resource_permission(request.user, None, 'create'):
        return APIResponse.forbidden(
            message="只有组织用户可以发布资源"
        )
    
    try:
        with transaction.atomic():
            serializer = ResourceCreateSerializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                resource = serializer.save()
                
                # 返回创建的资源信息
                response_serializer = ResourceSerializer(resource)
                return APIResponse.success(
                    data=response_serializer.data,
                    message="资源创建成功"
                )
            else:
                return APIResponse.error(
                    message="数据验证失败",
                    code=400,
                    errors=serializer.errors
                )
    
    except Exception as e:
        return APIResponse.error(
            message=f"创建资源失败: {str(e)}",
            code=500
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_resource(request, resource_id):
    """
    修改资源
    
    支持修改资源状态和基本信息，但不支持文件修改
    文件修改需要使用虚拟文件管理接口
    """
    try:
        # 先获取资源进行权限检查（不加锁）
        resource = get_object_or_404(Resource, id=resource_id)
        
        # 权限检查
        if not _check_resource_permission(request.user, resource, 'update'):
            return APIResponse.forbidden(
                message="只有资源创建者、组织所有者或管理员可以修改资源"
            )
        
        # 数据验证
        serializer = ResourceUpdateSerializer(
            resource, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return APIResponse.error(
                message="数据验证失败",
                code=400,
                errors=serializer.errors
            )
        
        # 只在实际更新时使用悲观锁，缩短事务范围
        with transaction.atomic():
            resource = get_object_or_404(
                Resource.objects.select_for_update(), 
                id=resource_id
            )
            
            # 重新验证权限（防止在验证期间权限发生变化）
            if not _check_resource_permission(request.user, resource, 'update'):
                return APIResponse.forbidden(
                    message="只有资源创建者、组织所有者或管理员可以修改资源"
                )
            
            # 使用已验证的数据进行更新
            updated_resource = serializer.save()
            
            # 返回更新后的资源信息
            response_serializer = ResourceSerializer(updated_resource)
            return APIResponse.success(
                data=response_serializer.data,
                message="资源更新成功"
            )
    
    except Resource.DoesNotExist:
        return APIResponse.not_found(
            message="资源不存在"
        )
    except Exception as e:
        return APIResponse.error(
            message=f"更新资源失败: {str(e)}",
            code=500
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_resource(request, resource_id):
    """
    删除资源
    
    删除资源时同时删除关联的文件，但不影响关联的需求
    使用悲观锁确保并发安全
    """
    try:
        # 使用悲观锁获取资源
        with transaction.atomic():
            resource = get_object_or_404(
                Resource.objects.select_for_update(), 
                id=resource_id
            )
            
            # 权限检查
            if not _check_resource_permission(request.user, resource, 'delete'):
                return APIResponse.forbidden(
                    message="只有资源创建者、组织所有者或管理员可以删除资源"
                )
            
            # 保存资源信息用于返回
            resource_info = {
                'id': resource.id,
                'title': resource.title,
                'type': resource.get_type_display(),
                'status': resource.get_status_display(),
                'create_person': resource.create_person.user.username
            }
            
            # 获取关联的文件列表
            associated_files = list(resource.files.all())
            deleted_files_info = []
            
            # 删除实际文件
            for file_obj in associated_files:
                file_info = {
                    'id': file_obj.id,
                    'name': file_obj.name,
                    'path': file_obj.path
                }
                
                # 如果是实际文件（非文件夹），删除物理文件
                if not file_obj.is_folder and file_obj.real_path:
                    try:
                        from django.core.files.storage import default_storage
                        if default_storage.exists(file_obj.real_path):
                            default_storage.delete(file_obj.real_path)
                            logger.info(f"已删除物理文件: {file_obj.real_path}")
                    except Exception as e:
                        # 记录文件删除失败，但不阻止资源删除
                        logger.warning(f"删除文件失败: {file_obj.real_path}, 错误: {str(e)}")
                
                # 删除数据库中的文件记录
                file_obj.delete()
                deleted_files_info.append(file_info)
            
            # 删除资源记录（注意：这里不会影响关联的需求，因为需求和资源是多对多关系）
            resource_title = resource.title
            resource.delete()
            
            return APIResponse.success(
                {
                    'deleted_resource': resource_info,
                    'deleted_files': deleted_files_info,
                    'deleted_files_count': len(deleted_files_info),
                    'message': f'资源已删除，同时删除了{len(deleted_files_info)}个关联文件，关联的需求已保留'
                },
                message=f"资源 '{resource_title}' 删除成功"
            )
    
    except Resource.DoesNotExist:
        return APIResponse.not_found(
            message="资源不存在"
        )
    except Exception as e:
        return APIResponse.error(
            message=f"删除资源失败: {str(e)}",
            code=500
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_resource_statistics(request):
    """
    获取资源统计数据
    支持周度、月度、季度统计
    权限：仅限组织用户访问，自动根据用户身份设置organization_id
    """
    try:
        user = request.user
        
        # 检查用户是否为组织用户
        try:
            org_user = OrganizationUser.objects.get(user=user)
            # 自动设置organization_id为用户所属组织
            organization_id = org_user.organization_id
        except OrganizationUser.DoesNotExist:
            return APIResponse.forbidden('只有组织用户才能访问资源统计数据')
        
        # 获取参数
        period = request.GET.get('period', 'week')  # week, month, quarter
        date_str = request.GET.get('date')  # 可选，默认当前时间
        # 注意：不再从请求参数获取organization_id，而是使用用户所属组织
        
        # 解析日期
        if date_str:
            try:
                current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return APIResponse.bad_request('日期格式错误，请使用YYYY-MM-DD格式')
        else:
            current_date = timezone.now().date()
        
        # 计算时间范围
        def get_time_ranges(period, current_date):
            if period == 'week':
                # 计算当前周的开始（周一）
                current_week_start = current_date - timedelta(days=current_date.weekday())
                # 上一周的同一天
                previous_date = current_date - timedelta(days=7)
                previous_week_start = previous_date - timedelta(days=previous_date.weekday())
                return current_date, previous_date
            elif period == 'month':
                # 当前月的同一天 vs 上个月的同一天
                if current_date.month == 1:
                    previous_month = current_date.replace(year=current_date.year-1, month=12)
                else:
                    try:
                        previous_month = current_date.replace(month=current_date.month-1)
                    except ValueError:
                        # 处理月末日期（如3月31日 -> 2月28日）
                        previous_month = current_date.replace(month=current_date.month-1, day=28)
                return current_date, previous_month
            elif period == 'quarter':
                # 计算季度
                current_quarter = (current_date.month - 1) // 3 + 1
                if current_quarter == 1:
                    previous_quarter_date = current_date.replace(year=current_date.year-1, month=current_date.month+9)
                else:
                    previous_quarter_date = current_date.replace(month=current_date.month-3)
                return current_date, previous_quarter_date
            else:
                raise ValueError('不支持的统计周期')
        
        current_end_date, previous_end_date = get_time_ranges(period, current_date)
        
        # 将日期转换为当天结束时间，确保包含当天创建的资源
        current_end_datetime = timezone.make_aware(datetime.combine(current_end_date, datetime.max.time()))
        previous_end_datetime = timezone.make_aware(datetime.combine(previous_end_date, datetime.max.time()))
        
        # 基础查询集
        base_queryset = Resource.objects.all()
        if organization_id:
            base_queryset = base_queryset.filter(create_person__organization_id=organization_id)
        
        # 1. 状态分布统计（当前时间点的累计数据）
        status_distribution = {}
        status_counts = base_queryset.filter(
            created_at__lte=current_end_datetime
        ).values('status').annotate(count=Count('id'))
        
        for item in status_counts:
            status_distribution[item['status']] = item['count']
        
        # 确保所有状态都有值
        for status_code, status_name in Resource.STATUS_CHOICES:
            if status_code not in status_distribution:
                status_distribution[status_code] = 0
        
        # 2. 数据统计（累计数据对比）
        def get_cumulative_stats(end_date):
            queryset = base_queryset.filter(created_at__lte=end_date)
            return queryset.aggregate(
                total=Count('id'),
                published_count=Count('id', filter=Q(status='published')),
                total_downloads=Sum(
                    Case(
                        When(downloads__regex=r'^\d+$', then=Cast('downloads', IntegerField())),
                        default=0,
                        output_field=IntegerField()
                    )
                ),
                total_views=Sum(
                    Case(
                        When(views__regex=r'^\d+$', then=Cast('views', IntegerField())),
                        default=0,
                        output_field=IntegerField()
                    )
                )
            )
        
        current_stats = get_cumulative_stats(current_end_datetime)
        previous_stats = get_cumulative_stats(previous_end_datetime)
        
        # 计算增长率
        def calculate_growth_rate(current, previous):
            if previous and previous > 0:
                growth_rate = round((current - previous) / previous * 100, 1)
                return f"{growth_rate}%"  # 添加百分号
            elif current > 0:
                return "100%"  # 从0增长到有数据，添加百分号
            else:
                return "0%"  # 添加百分号
        
        data_statistics = {
            'total': current_stats['total'] or 0,
            'total_up': calculate_growth_rate(
                current_stats['total'] or 0, 
                previous_stats['total'] or 0
            ),
            'published_count': current_stats['published_count'] or 0,
            'published_count_up': calculate_growth_rate(
                current_stats['published_count'] or 0,
                previous_stats['published_count'] or 0
            ),
            'downloads': current_stats['total_downloads'] or 0,
            'downloads_up': calculate_growth_rate(
                current_stats['total_downloads'] or 0,
                previous_stats['total_downloads'] or 0
            ),
            'views': current_stats['total_views'] or 0,
            'views_up': calculate_growth_rate(
                current_stats['total_views'] or 0,
                previous_stats['total_views'] or 0
            )
        }
        
        # 3. 热门标签统计（累计数据，不受时间段限制）
        hot_tags_queryset = Tag1.objects.annotate(
            resource_count=Count('resource', filter=Q(resource__in=base_queryset))
        ).filter(resource_count__gt=0).order_by('-resource_count')[:10]
        
        hot_tag1s = []
        for tag in hot_tags_queryset:
            hot_tag1s.append({
                'tag': tag.value,
                'count': str(tag.resource_count)
            })
        
        # 4. 热门资源统计（累计数据，不受时间段限制）
        # 4.1 下载量最高的前5个资源
        hot_downloads_queryset = base_queryset.annotate(
            download_count=Case(
                When(downloads__regex=r'^\d+$', then=Cast('downloads', IntegerField())),
                default=0,
                output_field=IntegerField()
            )
        ).select_related('create_person__user').order_by('-download_count')[:5]
        
        hot_downloads = []
        for resource in hot_downloads_queryset:
            # 修复：直接使用整数值，downloads和views字段在数据库中是整数类型
            downloads = resource.downloads if resource.downloads is not None else 0
            views = resource.views if resource.views is not None else 0
            
            hot_downloads.append({
                'id': str(resource.id),
                'title': resource.title,
                'downloads': str(downloads),
                'views': str(views),
                'auther': resource.create_person.user.username if resource.create_person and resource.create_person.user else '未知用户'
            })
        
        # 4.2 浏览量最高的前5个资源
        hot_views_queryset = base_queryset.annotate(
            view_count=Case(
                When(views__regex=r'^\d+$', then=Cast('views', IntegerField())),
                default=0,
                output_field=IntegerField()
            )
        ).select_related('create_person__user').order_by('-view_count')[:5]
        
        hot_views = []
        for resource in hot_views_queryset:
            # 修复：直接使用整数值，downloads和views字段在数据库中是整数类型
            downloads = resource.downloads if resource.downloads is not None else 0
            views = resource.views if resource.views is not None else 0
            
            hot_views.append({
                'id': str(resource.id),
                'title': resource.title,
                'downloads': str(downloads),
                'views': str(views),
                'auther': resource.create_person.user.username if resource.create_person and resource.create_person.user else '未知用户'
            })
        
        return APIResponse.success({
            'status_distribution': status_distribution,
            'data_statistics': data_statistics,
            'hot_tag1s': hot_tag1s,
            'hot_downloads': hot_downloads,
            'hot_views': hot_views
        }, "获取资源统计成功")
        
    except ValueError as e:
        logger.error(f"资源统计参数错误: {str(e)}")
        return APIResponse.bad_request(f"参数错误: {str(e)}")
    except Exception as e:
        logger.error(f"获取资源统计失败: {str(e)}")
        return APIResponse.server_error(
            '获取资源统计失败，请稍后重试',
            errors={'exception': str(e)}
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_resources(request):
    """
    获取资源列表接口
    
    获取资源列表，支持分页、筛选、排序和搜索。
    
    查询参数:
    - page: 页码 (默认: 1)
    - page_size: 每页数量 (默认: 10, 最大: 100)
    - keyword: 搜索关键词（可从资源标题、标签中搜索）
    - status: 资源状态筛选（支持多状态查询，用逗号分隔多个状态值）
    - type: 资源类型筛选（支持多类型查询，用逗号分隔多个类型值，如：code,dataset,document）
    - time: 资源发布时间筛选（支持单日或范围筛选，格式：YYYY-MM-DD 或 YYYY-MM-DD-YYYY-MM-DD）
    - sort_type: 排序字段（name/time/download/view）
    - sort_order: 排序方式（up升序/down降序）
    - organization_id: 组织ID筛选
    """
    try:
        # 构建基础查询集，使用数据库索引优化
        queryset = Resource.objects.select_related(
            'create_person__user', 'update_person__user'
        ).prefetch_related(
            'tag1', 'tag2', 'files'
        )
        
        # 应用筛选条件
        # 状态筛选（支持多状态查询，用逗号分隔）
        status_filter = request.GET.get('status')
        if status_filter:
            # 支持多状态查询：status=published,draft,unpublished
            status_list = [s.strip() for s in status_filter.split(',') if s.strip()]
            if len(status_list) == 1:
                # 单状态查询
                queryset = queryset.filter(status=status_list[0])
            else:
                # 多状态查询
                queryset = queryset.filter(status__in=status_list)
        
        # 组织筛选（通过创建者的组织）
        organization_id = request.GET.get('organization_id')
        if organization_id:
            try:
                queryset = queryset.filter(create_person__organization_id=int(organization_id))
            except (ValueError, TypeError):
                pass
        
        # 资源类型筛选
        type_filter = request.GET.get('type')
        if type_filter:
            # 支持多类型查询：type=code,dataset,document
            type_list = [t.strip() for t in type_filter.split(',') if t.strip()]
            if len(type_list) == 1:
                # 单类型查询
                queryset = queryset.filter(type=type_list[0])
            else:
                # 多类型查询
                queryset = queryset.filter(type__in=type_list)
        
        # 时间范围筛选（基于created_at字段）
        time_filter = request.GET.get('time')
        if time_filter:
            try:
                # 检查是否为日期范围格式（YYYY-MM-DD-YYYY-MM-DD）
                if time_filter.count('-') >= 5:  # 至少包含两个完整日期的连字符
                    # 范围筛选：YYYY-MM-DD-YYYY-MM-DD
                    # 找到中间的分隔符位置
                    parts = time_filter.split('-')
                    if len(parts) >= 6:  # 至少有6个部分（年-月-日-年-月-日）
                        # 重新组合日期
                        start_date = f"{parts[0]}-{parts[1]}-{parts[2]}"
                        end_date = f"{parts[3]}-{parts[4]}-{parts[5]}"
                        if start_date:
                            # 转换为datetime对象（当天开始时间）
                            start_datetime = timezone.make_aware(
                                timezone.datetime.strptime(start_date, '%Y-%m-%d').replace(
                                    hour=0, minute=0, second=0, microsecond=0
                                )
                            )
                            queryset = queryset.filter(created_at__gte=start_datetime)
                        if end_date:
                            # 转换为datetime对象（当天结束时间）
                            end_datetime = timezone.make_aware(
                                timezone.datetime.combine(
                                    timezone.datetime.strptime(end_date, '%Y-%m-%d').date(),
                                    timezone.datetime.max.time()
                                )
                            )
                            queryset = queryset.filter(created_at__lte=end_datetime)
                else:
                    # 单日筛选 - 使用时间范围避免时区问题
                    try:
                        target_date = timezone.datetime.strptime(time_filter, '%Y-%m-%d').date()
                        start_datetime = timezone.make_aware(
                            timezone.datetime.combine(target_date, timezone.datetime.min.time())
                        )
                        end_datetime = timezone.make_aware(
                            timezone.datetime.combine(target_date, timezone.datetime.max.time())
                        )
                        queryset = queryset.filter(
                            created_at__gte=start_datetime,
                            created_at__lte=end_datetime
                        )
                    except ValueError:
                        # 如果日期格式不正确，忽略筛选
                        pass
            except Exception:
                pass
        
        # 关键词搜索（支持标题、标签）
        keyword = request.GET.get('keyword')
        if keyword:
            search_q = Q(title__icontains=keyword)
            # 搜索tag1和tag2
            search_q |= Q(tag1__value__icontains=keyword) | Q(tag2__category__icontains=keyword) | Q(tag2__subcategory__icontains=keyword) | Q(tag2__specialty__icontains=keyword)
            queryset = queryset.filter(search_q).distinct()
        
        # 排序处理（针对海量数据优化）
        sort_type = request.GET.get('sort_type', 'time')  # 默认按时间排序
        sort_order = request.GET.get('sort_order', 'down')  # 默认降序
        
        # 构建排序字段
        sort_field_map = {
            'name': 'title',
            'time': 'created_at',  # 使用数据库时间戳字段，有索引
            'download': 'downloads',
            'view': 'views'
        }
        
        sort_field = sort_field_map.get(sort_type, 'created_at')
        if sort_order == 'up':
            order_by = sort_field
        else:
            order_by = f'-{sort_field}'
        
        # 应用排序，使用数据库索引优化
        queryset = queryset.order_by(order_by)
        
        # 使用通用分页工具
        pagination_result = paginate_queryset(request, queryset, default_page_size=10)
        paginator = pagination_result['paginator']
        page_data = pagination_result['page_data']
        pagination_info = pagination_result['pagination_info']
        
        # 序列化
        serializer = ResourceSerializer(
            page_data,
            many=True,
            context={'request': request}
        )
        
        return APIResponse.success({
            'resources': serializer.data,
            'pagination': pagination_info
        }, "获取资源列表成功")
        
    except Exception as e:
        logger.error(f"获取资源列表失败: {str(e)}")
        return APIResponse.server_error(
            '获取资源列表失败，请稍后重试',
            errors={'exception': str(e)}
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_resource(request, resource_id):
    """
    获取资源详情接口
    
    根据resource_id获取对应资源的详细信息。
    
    URL参数:
    - resource_id: 资源ID
    """
    try:
        # 获取资源详情，使用select_related和prefetch_related优化查询
        resource = get_object_or_404(
            Resource.objects.select_related(
                'create_person__user', 'update_person__user'
            ).prefetch_related(
                'tag1', 'tag2', 'files'
            ),
            id=resource_id
        )
        
        # 增加浏览次数（仅限学生用户）
        if hasattr(request.user, 'user_type') and request.user.user_type == 'student':
            Resource.objects.filter(id=resource_id).update(
                views=F('views') + 1
            )
        
        # 序列化资源数据
        serializer = ResourceSerializer(
            resource,
            context={'request': request}
        )
        
        return APIResponse.success(
            serializer.data,
            "获取资源详情成功"
        )
        
    except Exception as e:
        logger.error(f"获取资源详情失败: {str(e)}")
        return APIResponse.server_error(
            '获取资源详情失败，请稍后重试',
            errors={'exception': str(e)}
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_resource_download_info(request, resource_id):
    """
    获取资源下载信息接口
    
    根据resource_id获取对应资源关联的文件的完整url。
    
    URL参数:
    - resource_id: 资源ID
    """
    try:
        # 获取资源及其关联文件
        resource = get_object_or_404(
            Resource.objects.prefetch_related('files'),
            id=resource_id
        )
        
        # 获取关联文件信息
        files = resource.files.all()
        
        # 构建文件下载信息
        file_info = []
        for file in files:
            download_url = None
            if file.url:
                download_url = file.url
            elif file.real_path:
                download_url = build_media_url(file.real_path, request)
            file_data = {
                'id': file.id,
                'name': file.name,
                'size': file.size,
                'download_url': download_url,
                'created_at': file.created_at
            }
            file_info.append(file_data)
        
        # 增加下载次数（仅限学生用户）
        if hasattr(request.user, 'user_type') and request.user.user_type == 'student':
            Resource.objects.filter(id=resource_id).update(
                downloads=F('downloads') + 1
            )
        
        return APIResponse.success({
            'resource_id': resource.id,
            'resource_title': resource.title,
            'files': file_info
        }, "获取资源下载信息成功")
        
    except Exception as e:
        logger.error(f"获取资源下载信息失败: {str(e)}")
        return APIResponse.server_error(
            '获取资源下载信息失败，请稍后重试',
            errors={'exception': str(e)}
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_requirement_favorite(request):
    """
    切换需求收藏状态接口
    
    只有学生用户可以切换收藏状态。
    如果未收藏则收藏，如果已收藏则取消收藏。
    """
    try:
        user = request.user
        
        # 检查用户是否为学生用户
        if not hasattr(user, 'student_profile'):
            return APIResponse.forbidden("只有学生用户才能操作收藏")
        
        requirement_id = request.data.get('requirement_id')
        if not requirement_id:
            return APIResponse.error("缺少requirement_id参数", code=400)
        
        from .models import RequirementFavorite, Requirement
        
        # 检查需求是否存在
        try:
            requirement = Requirement.objects.get(id=requirement_id)
        except Requirement.DoesNotExist:
            return APIResponse.not_found("需求不存在")
        
        # 检查需求状态
        if requirement.status == 'under_review':
            return APIResponse.error("审核中的需求暂时无法收藏", code=400)
        
        # 检查是否已收藏
        try:
            favorite = RequirementFavorite.objects.get(
                student=user.student_profile,
                requirement_id=requirement_id
            )
            # 已收藏，执行取消收藏
            favorite.delete()
            return APIResponse.success(
                data={'is_favorited': False},
                message="取消收藏成功"
            )
        except RequirementFavorite.DoesNotExist:
            # 未收藏，执行收藏
            favorite = RequirementFavorite.objects.create(
                student=user.student_profile,
                requirement=requirement
            )
            
            # 异步更新动态标签权重 (action='favorite')
            try:
                from project.tasks import update_user_dynamic_tags_task
                update_user_dynamic_tags_task.delay(user.id, requirement_id, 'favorite')
            except Exception as e:
                logger.error(f"触发动态标签更新任务失败: {e}")
            
            # 返回收藏信息
            from .serializers import RequirementFavoriteSerializer
            response_serializer = RequirementFavoriteSerializer(favorite)
            
            return APIResponse.success(
                data={
                    'is_favorited': True,
                    'favorite_info': response_serializer.data
                },
                message="收藏成功"
            )
            
    except Exception as e:
        logger.error(f"切换收藏状态失败: {str(e)}")
        return APIResponse.server_error("操作失败，请稍后重试")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_favorite_requirements(request):
    """
    获取学生用户收藏的需求列表接口
    
    只有学生用户可以查看自己的收藏列表。
    支持分页和基本筛选。
    """
    try:
        user = request.user
        
        # 检查用户是否为学生用户
        if not hasattr(user, 'student_profile'):
            return APIResponse.forbidden("只有学生用户才能查看收藏列表")
        
        from .models import RequirementFavorite
        
        # 获取收藏记录
        queryset = RequirementFavorite.objects.filter(
            student=user.student_profile
        ).select_related('requirement', 'requirement__organization', 'requirement__publish_people')
        
        # 状态筛选
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(requirement__status=status)
        
        # 组织筛选
        organization_id = request.GET.get('organization_id')
        if organization_id:
            queryset = queryset.filter(requirement__organization_id=organization_id)
        
        # 关键词搜索
        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(requirement__title__icontains=search) |
                Q(requirement__brief__icontains=search) |
                Q(requirement__description__icontains=search)
            )
        
        # 排序
        ordering = request.GET.get('ordering', '-created_at')
        if ordering in ['-created_at', 'created_at', '-requirement__created_at', 'requirement__created_at']:
            queryset = queryset.order_by(ordering)
        
        # 分页
        page_data = paginate_queryset(request, queryset)
        
        # 序列化数据
        from .serializers import RequirementFavoriteSerializer
        serializer = RequirementFavoriteSerializer(page_data['page_data'], many=True)
        
        return APIResponse.success(
            data={
                'results': serializer.data,
                'pagination': page_data['pagination_info']
            }
        )
        
    except Exception as e:
        logger.error(f"获取收藏列表失败: {str(e)}")
        return APIResponse.server_error("获取收藏列表失败，请稍后重试")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_requirement_favorite_status(request, requirement_id):
    """
    检查需求收藏状态接口
    
    返回当前学生用户是否已收藏指定需求。
    """
    try:
        user = request.user
        
        # 检查用户是否为学生用户
        if not hasattr(user, 'student_profile'):
            return APIResponse.success(
                data={'is_favorited': False},
                message="非学生用户无法收藏需求"
            )
        
        from .models import RequirementFavorite
        
        # 检查是否已收藏
        is_favorited = RequirementFavorite.objects.filter(
            student=user.student_profile,
            requirement_id=requirement_id
        ).exists()
        
        return APIResponse.success(
            data={'is_favorited': is_favorited}
        )
        
    except Exception as e:
        logger.error(f"检查收藏状态失败: {str(e)}")
        return APIResponse.server_error("检查收藏状态失败，请稍后重试")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_poster(request):
    """
    生成需求海报接口
    
    根据需求标题、简介、标签和风格生成海报图片。
    
    请求参数:
    - title: 需求标题 (必填)
    - brief: 需求简介 (必填)
    - tags: 标签列表 (可选)
    - style: 风格 (可选，默认'default')
    
    返回:
    - images: 生成的图片URL列表
    """
    try:
        title = request.data.get('title')
        brief = request.data.get('brief')
        tags = request.data.get('tags', [])
        style = request.data.get('style', 'default')
        
        if not title or not brief:
            return APIResponse.validation_error("标题和简介不能为空")
            
        # 调用AI生图工具
        # 注意：现在 generate_poster_images 内部处理下载，所以直接返回本地URL
        local_urls = generate_poster_images(title, brief, tags, style, request=request)
        
        if not local_urls:
            return APIResponse.server_error("图片生成失败，请稍后重试")
            
        return APIResponse.success({
            'images': local_urls
        }, "海报生成成功")
        
    except Exception as e:
        logger.error(f"生成海报失败: {str(e)}")
        return APIResponse.server_error(
            '生成海报失败，请稍后重试',
            errors={'exception': str(e)}
        )