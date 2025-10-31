from django.apps import AppConfig


class OrganizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "organization"
    verbose_name = '组织管理'
    
    def ready(self):
        """应用启动时注册信号处理器"""
        import organization.signals  # 导入信号处理器
