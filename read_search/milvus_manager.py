from pymilvus import connections, Collection, utility
from django.conf import settings
import logging
import threading

logger = logging.getLogger(__name__)

class MilvusManager:
    """
    Milvus连接管理器，提供单例模式的连接管理
    避免重复连接/断开，提升性能
    """
    _instance = None
    _lock = threading.Lock()
    _connected = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MilvusManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.host = getattr(settings, 'MILVUS_HOST', '10.129.22.101')
            self.port = getattr(settings, 'MILVUS_PORT', '19530')
            self.collection_name = getattr(settings, 'MILVUS_COLLECTION', 'enterprise_vectors')
            self.initialized = True
    
    def connect(self):
        """
        建立Milvus连接（如果尚未连接）
        
        Returns:
            bool: 连接是否成功
        """
        if self._connected:
            logger.debug(f"[Milvus] 已连接，跳过重复连接")
            return True
            
        try:
            connections.connect("default", host=self.host, port=self.port)
            self._connected = True
            logger.info(f"[Milvus] 连接管理器连接成功: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"[Milvus ERROR] 连接失败: {e}")
            self._connected = False
            return False
    
    def get_collection(self, load=True):
        """
        获取Collection对象（按需连接）
        
        Args:
            load (bool): 是否加载collection到内存
            
        Returns:
            Collection: Milvus collection对象
            
        Raises:
            ValueError: 如果collection不存在
        """
        # 按需连接：只有在需要获取collection时才建立连接
        if not self._connected:
            if not self.connect():
                raise ConnectionError("无法连接到Milvus")
        
        if not utility.has_collection(self.collection_name):
            logger.error(f"[Milvus] 未找到集合: {self.collection_name}")
            raise ValueError(f"Collection '{self.collection_name}' 不存在，请先创建")
        
        collection = Collection(self.collection_name)
        if load:
            try:
                collection.load()
                logger.debug(f"[Milvus] Collection '{self.collection_name}' 已加载")
            except Exception as e:
                logger.error(f"[Milvus ERROR] 加载集合失败: {e}")
                raise
        
        return collection
    
    def disconnect(self):
        """
        断开Milvus连接
        """
        if self._connected:
            try:
                connections.disconnect("default")
                self._connected = False
                logger.info(f"[Milvus] 连接管理器已断开连接")
            except Exception as e:
                logger.error(f"[Milvus ERROR] 断开连接失败: {e}")
    
    def is_connected(self):
        """
        检查是否已连接
        
        Returns:
            bool: 连接状态
        """
        return self._connected
    
    @classmethod
    def reset_instance(cls):
        """
        重置单例实例（主要用于测试）
        """
        with cls._lock:
            if cls._instance:
                cls._instance.disconnect()
            cls._instance = None
            cls._connected = False

# 全局实例（按需初始化，不会在导入时自动连接）
milvus_manager = MilvusManager()