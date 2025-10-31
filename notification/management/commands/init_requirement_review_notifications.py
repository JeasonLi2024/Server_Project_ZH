from django.core.management.base import BaseCommand
from notification.models import NotificationType, NotificationTemplate


class Command(BaseCommand):
    help = '初始化需求审核通知类型和模板'
    
    def handle(self, *args, **options):
        """创建需求审核相关的通知类型和模板"""
        
        # 需求审核通知类型配置
        review_notification_types = [
            {
                'code': 'requirement_review_approved',
                'name': '需求审核通过通知',
                'category': 'organization',
                'description': '当需求审核状态从审核中变更为进行中时发送给需求发布者的通知',
                'title_template': '需求审核通过通知',
                'content_template': '恭喜！您发布的需求 {{ requirement_title }} 已通过审核。审核时间：{{ review_time }}。您现在可以开始接收学生的项目申请了。',

                'variables': {
                    'publisher_name': '需求发布者姓名',
                    'requirement_title': '需求标题',
                    'organization_name': '发布组织名称',
                    'review_time': '审核时间',
                    'reviewer_name': '审核人员姓名',
                    'requirement_url': '需求详情链接'
                }
            },
            {
                'code': 'requirement_review_failed',
                'name': '需求审核失败通知',
                'category': 'organization',
                'description': '当需求审核状态从审核中变更为审核失败时发送给需求发布者的通知',
                'title_template': '需求审核未通过通知',
                'content_template': '很抱歉，您发布的需求 {{ requirement_title }} 未通过审核。审核意见：{{ review_comment }}。审核时间：{{ review_time }}。请根据审核意见修改后重新提交。如有疑问，请联系系统管理员。',

                'variables': {
                    'publisher_name': '需求发布者姓名',
                    'requirement_title': '需求标题',
                    'organization_name': '发布组织名称',
                    'review_time': '审核时间',
                    'reviewer_name': '审核人员姓名',
                    'review_comment': '审核意见',
                    'requirement_url': '需求详情链接'
                }
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for type_config in review_notification_types:
            # 提取模板配置
            title_template = type_config.pop('title_template')
            content_template = type_config.pop('content_template')

            variables = type_config.pop('variables')
            
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

                    'variables': variables
                }
            )
            
            if not template_created:
                # 更新现有模板
                template.title_template = title_template
                template.content_template = content_template

                template.variables = variables
                template.save()
                self.stdout.write(
                    self.style.WARNING(f'↻ 更新通知模板: {template.notification_type.name} 模板')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 创建通知模板: {template.notification_type.name} 模板')
                )
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'需求审核通知类型初始化完成！'))
        self.stdout.write(f'新创建通知类型: {created_count} 个')
        self.stdout.write(f'已更新通知类型: {updated_count} 个')
        self.stdout.write('='*60)
        
        # 显示使用说明
        self.stdout.write('\n📋 使用说明:')
        self.stdout.write('1. requirement_review_approved: 需求审核通过时使用')
        self.stdout.write('2. requirement_review_failed: 需求审核失败时使用')
        self.stdout.write('\n💡 在需求状态变更时调用通知服务发送相应通知')
        self.stdout.write('\n示例代码:')
        self.stdout.write('from notification.services import NotificationService')
        self.stdout.write('notification_service = NotificationService()')
        self.stdout.write('notification_service.create_and_send_notification(')
        self.stdout.write('    recipient=requirement.publish_people.user,')
        self.stdout.write('    notification_type_code="requirement_review_approved",')
        self.stdout.write('    related_object=requirement,')
        self.stdout.write('    template_vars={...}')
        self.stdout.write(')')