from django.apps import AppConfig


class NotificationConfig(AppConfig):
    """通知应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notification'
    verbose_name = '通知系统'
    
    def ready(self):
        """应用准备就绪时的初始化"""
        # 导入信号处理器
        try:
            from . import signals
        except ImportError:
            pass
        
        # 导入任务（如果使用Celery）
        try:
            from . import tasks
        except ImportError:
            pass
