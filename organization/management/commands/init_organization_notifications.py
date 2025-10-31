from django.core.management.base import BaseCommand
from organization.signals import ensure_organization_verification_notification_setup


class Command(BaseCommand):
    help = '初始化组织认证通知类型和模板'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始初始化组织认证通知...'))
        
        try:
            notification_type, template = ensure_organization_verification_notification_setup()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ 成功初始化组织认证通知系统：\n'
                    f'   - 通知类型：{notification_type.name} (分类: {notification_type.category})\n'
                    f'   - 通知模板：{template.title_template[:50]}...'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 初始化失败：{str(e)}')
            )
            raise e
        
        self.stdout.write(self.style.SUCCESS('🎉 组织认证通知系统初始化完成！'))