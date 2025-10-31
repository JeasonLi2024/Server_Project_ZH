from django.core.management.base import BaseCommand
from notification.models import NotificationType, NotificationTemplate


class Command(BaseCommand):
    help = '初始化系统广播通知类型'
    
    def handle(self, *args, **options):
        """创建系统广播通知类型"""
        
        # 系统广播通知类型配置
        broadcast_types = [
            {
                'code': 'system_announcement',
                'name': '系统公告',
                'category': 'system',
                'description': '系统重要公告通知',
                'title_template': '【系统公告】{title}',
                'content_template': '{content}\n\n发布时间：{created_at}\n有效期至：{expires_at}'
            },
            {
                'code': 'maintenance_notice',
                'name': '维护通知',
                'category': 'system',
                'description': '系统维护相关通知',
                'title_template': '【维护通知】{title}',
                'content_template': '{content}\n\n维护时间：{maintenance_time}\n预计影响：{impact}\n\n如有疑问，请联系技术支持。'
            },
            {
                'code': 'version_update',
                'name': '版本更新',
                'category': 'system',
                'description': '系统版本更新通知',
                'title_template': '【版本更新】{title}',
                'content_template': '{content}\n\n更新版本：{version}\n更新时间：{update_time}\n主要改进：{improvements}'
            },
            {
                'code': 'urgent_notice',
                'name': '紧急通知',
                'category': 'system',
                'description': '系统紧急通知',
                'title_template': '【紧急通知】{title}',
                'content_template': '⚠️ 紧急通知 ⚠️\n\n{content}\n\n请立即关注并采取相应措施。\n\n发布时间：{created_at}'
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for type_config in broadcast_types:
            # 提取模板配置
            title_template = type_config.pop('title_template')
            content_template = type_config.pop('content_template')
            
            # 创建或更新通知类型
            notification_type, created = NotificationType.objects.get_or_create(
                code=type_config['code'],
                defaults=type_config
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 创建通知类型: {notification_type.name} ({notification_type.code})')
                )
            else:
                # 更新现有类型
                for key, value in type_config.items():
                    setattr(notification_type, key, value)
                notification_type.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ 更新通知类型: {notification_type.name} ({notification_type.code})')
                )
            
            # 创建或更新通知模板
            template, template_created = NotificationTemplate.objects.get_or_create(
                notification_type=notification_type,
                defaults={
                    'title_template': title_template,
                    'content_template': content_template,
                    'variables': {
                        'title': '通知标题',
                        'content': '通知内容',
                        'created_at': '创建时间',
                        'expires_at': '过期时间',
                        'maintenance_time': '维护时间',
                        'impact': '影响范围',
                        'version': '版本号',
                        'update_time': '更新时间',
                        'improvements': '改进内容'
                    }
                }
            )
            
            if not template_created:
                # 更新现有模板
                template.title_template = title_template
                template.content_template = content_template
                template.save()
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'系统广播通知类型初始化完成！'))
        self.stdout.write(f'新创建: {created_count} 个')
        self.stdout.write(f'已更新: {updated_count} 个')
        self.stdout.write('='*50)
        
        # 显示使用说明
        self.stdout.write('\n📋 使用说明:')
        self.stdout.write('1. 进入Django管理后台')
        self.stdout.write('2. 访问 "通知详情" 页面')
        self.stdout.write('3. 点击 "发送系统广播通知" 按钮')
        self.stdout.write('4. 填写广播内容并选择目标用户')
        self.stdout.write('5. 点击 "发送系统广播" 完成发送')
        self.stdout.write('\n✨ 系统广播功能已就绪！')