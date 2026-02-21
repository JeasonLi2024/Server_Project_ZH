import time
import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

class UserHistoryService:
    """
    用户浏览历史服务
    使用 Redis Sorted Set (ZSet) 存储，支持时间排序和去重
    """
    
    # 历史记录最大保留数量
    MAX_HISTORY_SIZE = 1000
    # 历史记录过期时间（秒）- 90天
    HISTORY_TTL = 90 * 24 * 60 * 60
    
    @staticmethod
    def _get_history_key(user_id, item_type='requirement'):
        """
        获取历史记录的 Redis Key
        item_type: 'requirement' (需求) or 'project' (项目)
        """
        return f"user:view_history:{item_type}:{user_id}"
    
    @classmethod
    def record_view(cls, user_id, item_id, item_type='requirement'):
        """
        记录用户浏览行为
        """
        if not user_id or not item_id:
            return
            
        try:
            key = cls._get_history_key(user_id, item_type)
            timestamp = time.time()
            
            # 使用 pipeline 保证原子性和性能
            # 注意：Django cache backend 可能不直接支持 pipeline，这里假设使用 redis backend
            # 如果是默认的 django-redis，可以直接通过 cache.client.get_client() 获取原始 redis 连接
            
            # 尝试获取原始 Redis 连接
            redis_client = None
            if hasattr(cache, 'client') and hasattr(cache.client, 'get_client'):
                redis_client = cache.client.get_client()
            elif hasattr(cache, '_cache') and hasattr(cache._cache, 'get_client'):
                # 兼容不同版本的 django-redis
                redis_client = cache._cache.get_client()
                
            if redis_client:
                pipeline = redis_client.pipeline()
                # ZADD: 添加记录，分数是时间戳
                pipeline.zadd(key, {str(item_id): timestamp})
                # ZREMRANGEBYRANK: 移除旧记录，保留最新的 N 条
                # 索引是从 0 开始的，保留最后 MAX_HISTORY_SIZE 条
                # 删除从 0 到 -(MAX_HISTORY_SIZE + 1) 的元素
                pipeline.zremrangebyrank(key, 0, -(cls.MAX_HISTORY_SIZE + 1))
                # EXPIRE: 设置过期时间
                pipeline.expire(key, cls.HISTORY_TTL)
                pipeline.execute()
            else:
                # 降级处理：使用 cache 接口（虽然 cache 不直接支持 zset，但如果是 RedisCache，通常有扩展方法）
                # 这里假设如果获取不到 raw client，就暂时无法操作 ZSet，或者记录日志
                # 实际生产环境中应该确保配置了 Redis Cache
                logger.warning(f"无法获取 Redis 客户端，浏览历史记录失败: user={user_id}, item={item_id}")
                
        except Exception as e:
            logger.error(f"记录浏览历史失败: {e}")

    @classmethod
    def get_history(cls, user_id, item_type='requirement', page=1, page_size=20):
        """
        获取浏览历史列表 (分页)
        返回: (item_ids, total_count)
        """
        try:
            key = cls._get_history_key(user_id, item_type)
            redis_client = None
            if hasattr(cache, 'client') and hasattr(cache.client, 'get_client'):
                redis_client = cache.client.get_client()
            elif hasattr(cache, '_cache') and hasattr(cache._cache, 'get_client'):
                redis_client = cache._cache.get_client()
                
            if not redis_client:
                return [], 0
                
            # 获取总数
            total = redis_client.zcard(key)
            if total == 0:
                return [], 0
                
            # 计算索引（倒序，最新的在前）
            start = (page - 1) * page_size
            end = start + page_size - 1
            
            # ZREVRANGE: 获取指定范围的元素（按分数倒序）
            item_ids = redis_client.zrevrange(key, start, end)
            
            # 转换为 int 列表
            item_ids = [int(i) for i in item_ids]
            
            return item_ids, total
            
        except Exception as e:
            logger.error(f"获取浏览历史失败: {e}")
            return [], 0

    @classmethod
    def get_all_viewed_ids(cls, user_id, item_type='requirement'):
        """
        获取用户所有浏览过的 ID 集合（用于去重）
        """
        try:
            key = cls._get_history_key(user_id, item_type)
            redis_client = None
            if hasattr(cache, 'client') and hasattr(cache.client, 'get_client'):
                redis_client = cache.client.get_client()
            elif hasattr(cache, '_cache') and hasattr(cache._cache, 'get_client'):
                redis_client = cache._cache.get_client()
                
            if not redis_client:
                return set()
                
            # ZRANGE 0 -1: 获取所有元素
            item_ids = redis_client.zrange(key, 0, -1)
            return {int(i) for i in item_ids}
            
        except Exception as e:
            logger.error(f"获取全量浏览历史失败: {e}")
            return set()

    @classmethod
    def get_recent_viewed_items(cls, user_id, item_type='requirement', limit=5):
        """
        获取最近浏览的 N 个项目 ID (用于计算动态画像)
        """
        try:
            key = cls._get_history_key(user_id, item_type)
            redis_client = None
            if hasattr(cache, 'client') and hasattr(cache.client, 'get_client'):
                redis_client = cache.client.get_client()
            elif hasattr(cache, '_cache') and hasattr(cache._cache, 'get_client'):
                redis_client = cache._cache.get_client()
                
            if not redis_client:
                return []
                
            # ZREVRANGE: 获取指定范围的元素（按分数倒序）
            item_ids = redis_client.zrevrange(key, 0, limit - 1)
            
            # 转换为 int 列表
            return [int(i) for i in item_ids]
            
        except Exception as e:
            logger.error(f"获取最近浏览记录失败: {e}")
            return []
