import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OrganizationUser
from notification.services import org_notification_service

logger = logging.getLogger(__name__)


@receiver(post_save, sender=OrganizationUser)
def handle_organization_user_created(sender, instance, created, **kwargs):
    """
    处理组织用户创建后的通知
    情形1：新用户注册"组织用户"身份并选择了现有的组织后，
    该组织创建者和组织管理员会收到新用户加入的审核通知
    """
    if created and instance.status == 'pending':
        try:
            # 获取组织管理员和创建者
            from user.models import OrganizationUser
            admins = OrganizationUser.objects.filter(
                organization=instance.organization,
                permission__in=['owner', 'admin'],
                status='approved'
            ).select_related('user')
            
            # 发送新用户加入审核通知给组织创建者和管理员
            for admin in admins:
                org_notification_service.send_user_registration_audit_notification(
                    organization_admin=admin.user,
                    applicant=instance.user,
                    organization_name=instance.organization.name
                )
        except Exception as e:
            logger.error(f"发送新用户注册通知失败: {str(e)}")