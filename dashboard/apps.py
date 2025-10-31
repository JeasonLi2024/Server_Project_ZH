from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"
    verbose_name = 'Dashboard统计'
    
    def ready(self):
        """应用启动时注册信号处理器"""
        import dashboard.signals  # 导入信号处理器
