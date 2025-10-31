# read_search/services.py
import logging
import threading
from typing import List, Dict, Any, Optional
from django.core.cache import cache
from django.conf import settings
from .models import TagMatch
from .read_search import get_embeddings, search_in_milvus, split_text

logger = logging.getLogger(__name__)


class SearchService:
    """
    搜索服务类 - 处理学生标签匹配的初筛逻辑
    """
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'SEARCH_CACHE_TIMEOUT', 3600)  # 默认1小时缓存
    
    def get_student_matched_requirements(self, student_id: int) -> List[Dict[str, Any]]:
        """
        获取学生匹配的项目需求列表（初筛）- 实时查询，不使用缓存
        
        Args:
            student_id (int): 学生ID
            
        Returns:
            List[Dict]: 匹配的项目需求列表
        """
        try:
            # 使用Django ORM查询TagMatch模型
            tag_matches = TagMatch.objects.filter(
                student_id=student_id
            ).distinct()
            
            # 获取所有相关的需求ID
            requirement_ids = list(tag_matches.values_list('requirement_id', flat=True).distinct())
            
            # 批量查询需求信息
            from project.models import Requirement
            requirements_dict = {}
            if requirement_ids:
                requirements = Requirement.objects.filter(id__in=requirement_ids)
                requirements_dict = {req.id: req for req in requirements}
            
            # 转换为字典格式
            result = []
            for tag_match in tag_matches:
                requirement = requirements_dict.get(tag_match.requirement_id)
                requirement_data = {
                    "Sid": tag_match.student_id,
                    "Pid": tag_match.requirement_id,
                    "requirement_title": requirement.title if requirement else f"需求{tag_match.requirement_id}",
                    "tag_source": tag_match.tag_source,
                    "tag_id": tag_match.tag_id,
                }
                result.append(requirement_data)
            
            logger.info(f"实时查询为学生{student_id}找到{len(result)}个匹配的项目需求")
            
            return result
            
        except Exception as e:
            logger.error(f"获取学生{student_id}匹配需求时出错: {e}")
            return []
    
    def get_requirement_ids_for_student(self, student_id: int) -> List[int]:
        """
        获取学生匹配的项目需求ID列表（去重）
        
        Args:
            student_id (int): 学生ID
            
        Returns:
            List[int]: 去重后的项目需求ID列表
        """
        matched_requirements = self.get_student_matched_requirements(student_id)
        # 使用set去重，然后转换回list并保持顺序
        requirement_ids = [req["Pid"] for req in matched_requirements]
        return list(dict.fromkeys(requirement_ids))  # 保持顺序的去重
    
    def clear_student_cache(self, student_id: int) -> bool:
        """
        清除学生相关的缓存（已禁用缓存，此方法保留兼容性）
        
        Args:
            student_id (int): 学生ID
            
        Returns:
            bool: 总是返回True（缓存已禁用）
        """
        logger.info(f"缓存已禁用，无需清除学生{student_id}的缓存")
        return True


class CacheService:
    """
    统一缓存管理服务类
    """
    
    @staticmethod
    def get_cache_key(prefix: str, *args) -> str:
        """
        生成标准化的缓存键
        
        Args:
            prefix (str): 缓存键前缀
            *args: 缓存键参数
            
        Returns:
            str: 标准化的缓存键
        """
        key_parts = [str(arg) for arg in args]
        return f"{prefix}_{'_'.join(key_parts)}"
    
    @staticmethod
    def set_cache(key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """
        设置缓存
        
        Args:
            key (str): 缓存键
            value (Any): 缓存值
            timeout (Optional[int]): 过期时间（秒）
            
        Returns:
            bool: 是否成功设置缓存
        """
        try:
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            logger.error(f"设置缓存时出错: {e}")
            return False
    
    @staticmethod
    def get_cache(key: str, default: Any = None) -> Any:
        """
        获取缓存
        
        Args:
            key (str): 缓存键
            default (Any): 默认值
            
        Returns:
            Any: 缓存值或默认值
        """
        try:
            return cache.get(key, default)
        except Exception as e:
            logger.error(f"获取缓存时出错: {e}")
            return default
    
    @staticmethod
    def delete_cache(key: str) -> bool:
        """
        删除缓存
        
        Args:
            key (str): 缓存键
            
        Returns:
            bool: 是否成功删除缓存
        """
        try:
            cache.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除缓存时出错: {e}")
            return False
    
    @staticmethod
    def clear_pattern_cache(pattern: str) -> bool:
        """
        根据模式清除缓存（需要Redis后端支持）
        
        Args:
            pattern (str): 缓存键模式
            
        Returns:
            bool: 是否成功清除缓存
        """
        try:
            # 这里需要根据实际的缓存后端实现
            # 对于Redis，可以使用KEYS命令或SCAN命令
            logger.info(f"清除模式缓存: {pattern}")
            return True
        except Exception as e:
            logger.error(f"清除模式缓存时出错: {e}")
            return False


# 创建服务实例
search_service = SearchService()
cache_service = CacheService()