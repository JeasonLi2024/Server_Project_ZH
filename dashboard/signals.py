import redis
import json
from datetime import date
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
import logging

# 导入相关模型
from studentproject.models import StudentProject
from organization.models import Organization

logger = logging.getLogger(__name__)


def get_redis_client():
    """获取Redis客户端"""
    return redis.Redis(
        host=getattr(settings, 'REDIS_HOST', 'localhost'),
        port=getattr(settings, 'REDIS_PORT', 6379),
        db=getattr(settings, 'REDIS_DB', 0),
        decode_responses=True
    )


def clear_dashboard_cache(cache_types):
    """清除指定类型的dashboard缓存
    
    Args:
        cache_types (list): 要清除的缓存类型列表，如 ['project_status', 'org_status']
    """
    try:
        redis_client = get_redis_client()
        today_str = date.today().strftime('%Y%m%d')
        
        cleared_keys = []
        for cache_type in cache_types:
            cache_key = f"dashboard:{cache_type}:{today_str}"
            result = redis_client.delete(cache_key)
            if result:
                cleared_keys.append(cache_key)
                logger.info(f"已清除缓存: {cache_key}")
        
        if cleared_keys:
            logger.info(f"Dashboard缓存清除完成，共清除 {len(cleared_keys)} 个缓存键")
        
        return cleared_keys
    except Exception as e:
        logger.error(f"清除dashboard缓存失败: {str(e)}")
        return []


@receiver([post_save, post_delete], sender=StudentProject)
def handle_student_project_change(sender, instance, **kwargs):
    """处理StudentProject模型变更，清除相关缓存"""
    try:
        # 当StudentProject发生变更时，需要清除以下缓存：
        # 1. project_status - 项目状态统计
        # 2. project_completion - 项目完成度统计  
        # 3. project_tag1 - 项目标签统计（如果项目有关联需求和标签）
        cache_types_to_clear = ['project_status', 'project_completion']
        
        # 如果项目有关联需求且需求有tag1标签，也清除项目标签统计缓存
        if hasattr(instance, 'requirement') and instance.requirement:
            if hasattr(instance.requirement, 'tag1') and instance.requirement.tag1.exists():
                cache_types_to_clear.append('project_tag1')
        
        cleared_keys = clear_dashboard_cache(cache_types_to_clear)
        
        # 记录变更信息
        action = "创建" if kwargs.get('created', False) else "更新"
        if 'signal' in kwargs and kwargs['signal'] == post_delete:
            action = "删除"
            
        logger.info(f"StudentProject {action}: {instance.title} (ID: {instance.id}), 已清除相关缓存")
        
    except Exception as e:
        logger.error(f"处理StudentProject变更信号失败: {str(e)}")


@receiver([post_save, post_delete], sender=Organization)
def handle_organization_change(sender, instance, **kwargs):
    """处理Organization模型变更，清除相关缓存"""
    try:
        # 当Organization发生变更时，需要清除以下缓存：
        # 1. org_status - 组织状态统计
        cache_types_to_clear = ['org_status']
        
        cleared_keys = clear_dashboard_cache(cache_types_to_clear)
        
        # 记录变更信息
        action = "创建" if kwargs.get('created', False) else "更新"
        if 'signal' in kwargs and kwargs['signal'] == post_delete:
            action = "删除"
            
        logger.info(f"Organization {action}: {instance.name} (ID: {instance.id}), 已清除相关缓存")
        
    except Exception as e:
        logger.error(f"处理Organization变更信号失败: {str(e)}")


# 可选：提供手动清除所有dashboard缓存的函数
def clear_all_dashboard_cache():
    """清除所有dashboard相关缓存"""
    all_cache_types = [
        'project_status',
        'org_status', 
        'project_completion',
        'project_tag1',
        'tag1_student',
        'tag2_student',
        'user_registration',
        'student_tag'
    ]
    return clear_dashboard_cache(all_cache_types)


# 提供按需清除特定缓存的函数
def clear_project_related_cache():
    """清除项目相关的所有缓存"""
    project_cache_types = ['project_status', 'project_completion', 'project_tag1']
    return clear_dashboard_cache(project_cache_types)


def clear_organization_related_cache():
    """清除组织相关的所有缓存"""
    org_cache_types = ['org_status']
    return clear_dashboard_cache(org_cache_types)