from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Organization, OrganizationJoinApplication
from user.models import OrganizationUser
from notification.services import org_notification_service
from notification.models import NotificationType, NotificationTemplate
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Organization)
def handle_organization_verification_status_change(sender, instance, **kwargs):
    """
    处理组织认证状态变更信号
    当管理员将组织状态修改为'verified'或'rejected'时，通知组织创建者
    """
    # 检查是否是状态变更为已认证或被拒绝
    if instance.status in ['verified', 'rejected']:
        try:
            # 查找组织创建者（权限为owner的用户）
            owner = OrganizationUser.objects.filter(
                organization=instance,
                permission='owner',
                status='approved'
            ).select_related('user').first()
            
            if owner and owner.user:
                # 确保通知类型和模板存在
                ensure_organization_verification_notification_setup()
                
                if instance.status == 'verified':
                    # 发送认证通过通知
                    org_notification_service.send_organization_verification_success_notification(
                        organization_creator=owner.user,
                        organization=instance,
                        operator=None  # 系统自动认证
                    )
                    logger.info(f"已向组织 {instance.name} 的创建者 {owner.user.username} 发送认证通过通知")
                elif instance.status == 'rejected':
                    # 发送认证被拒绝通知
                    org_notification_service.send_organization_verification_rejected_notification(
                        organization_creator=owner.user,
                        organization=instance,
                        operator=None,  # 系统自动认证
                        verification_comment=instance.verification_comment
                    )
                    logger.info(f"已向组织 {instance.name} 的创建者 {owner.user.username} 发送认证被拒绝通知")
            else:
                logger.warning(f"组织 {instance.name} 未找到有效的创建者用户")
                
        except Exception as e:
            logger.error(f"发送组织认证状态变更通知失败: {str(e)}")


def ensure_organization_verification_notification_setup():
    """
    确保组织认证通知类型和模板存在，并标记为系统级通知
    """
    try:
        # 创建或获取认证通过通知类型
        success_type, success_created = NotificationType.objects.get_or_create(
            code='organization_verification_success',
            defaults={
                'name': '组织认证通过通知',
                'category': 'system',
                'description': '当组织认证状态变更为已认证时发送给创建者的通知',
                'default_template': '恭喜！您的组织认证已通过审核。',
                'is_active': True
            }
        )
        
        # 创建或获取认证被拒绝通知类型
        rejected_type, rejected_created = NotificationType.objects.get_or_create(
            code='organization_verification_rejected',
            defaults={
                'name': '组织认证被拒绝通知',
                'category': 'system',
                'description': '当组织认证状态变更为被拒绝时发送给创建者的通知',
                'default_template': '很抱歉，您的组织认证申请未通过审核。',
                'is_active': True
            }
        )
        
        # 如果通知类型已存在但category不是system，则更新
        for ntype in [success_type, rejected_type]:
            if ntype.category != 'system':
                ntype.category = 'system'
                ntype.save()
        
        if success_created:
            logger.info(f"创建了新的系统级通知类型: {success_type.name}")
        if rejected_created:
            logger.info(f"创建了新的系统级通知类型: {rejected_type.name}")
        
        # 创建或获取认证通过通知模板
        success_template, success_template_created = NotificationTemplate.objects.get_or_create(
            notification_type=success_type,
            defaults={
                'title_template': '组织认证通过通知',
                'content_template': '恭喜！您的组织 {{ organization_name }} 已通过认证审核。认证时间：{{ verification_time }}。您现在可以享受认证组织的所有权益。',
                'variables': {
                    'organization_name': '组织名称',
                    'organization_id': '组织ID',
                    'creator_name': '创建者姓名',
                    'operator_name': '操作员姓名',
                    'verification_time': '认证时间',
                    'organization_url': '组织链接'
                }
            }
        )
        
        # 创建或获取认证被拒绝通知模板
        rejected_template, rejected_template_created = NotificationTemplate.objects.get_or_create(
            notification_type=rejected_type,
            defaults={
                'title_template': '组织认证被拒绝通知',
                'content_template': '很抱歉，您的组织 {{ organization_name }} 的认证申请未通过审核。拒绝原因：{{ verification_comment }}。认证时间：{{ verification_time }}。如有疑问，请联系管理员。',
                'variables': {
                    'organization_name': '组织名称',
                    'organization_id': '组织ID',
                    'creator_name': '创建者姓名',
                    'operator_name': '操作员姓名',
                    'verification_time': '认证时间',
                    'verification_comment': '认证意见',
                    'organization_url': '组织链接'
                }
            }
        )
        
        if success_template_created:
            logger.info(f"创建了新的系统级通知模板: {success_template.title_template}")
        if rejected_template_created:
            logger.info(f"创建了新的系统级通知模板: {rejected_template.title_template}")
            
        return success_type, rejected_type, success_template, rejected_template
            
    except Exception as e:
        logger.error(f"设置组织认证通知类型和模板失败: {str(e)}")
        return None, None, None, None


# ==================== 企业用户组织切换功能信号处理 ====================

@receiver(post_save, sender=OrganizationJoinApplication)
def handle_organization_join_application_change(sender, instance, created, **kwargs):
    """
    处理组织加入申请状态变更信号
    """
    try:
        if created:
            # 新申请提交时，通知组织管理员
            send_join_application_notification_to_admins(instance)
        else:
            # 申请状态变更时，通知申请人
            if instance.status in ['approved', 'rejected']:
                send_join_application_result_notification(instance)
                
    except Exception as e:
        logger.error(f"处理组织加入申请信号失败: {str(e)}")


def send_join_application_notification_to_admins(application):
    """
    向组织管理员发送新申请通知
    """
    try:
        # 确保通知类型和模板存在
        ensure_join_application_notification_setup()
        
        # 获取组织的管理员和所有者
        admins = OrganizationUser.objects.filter(
            organization=application.organization,
            permission__in=['admin', 'owner'],
            status='approved'
        ).select_related('user')
        
        for admin in admins:
            if admin.user:
                org_notification_service.send_join_application_submitted_notification(
                    recipient=admin.user,
                    applicant=application.applicant,
                    organization=application.organization,
                    application=application
                )
                logger.info(f"已向管理员 {admin.user.username} 发送新申请通知")
                
    except Exception as e:
        logger.error(f"发送申请通知给管理员失败: {str(e)}")


def send_join_application_result_notification(application):
    """
    向申请人发送审核结果通知
    """
    try:
        # 确保通知类型和模板存在
        ensure_join_application_notification_setup()
        
        if application.status == 'approved':
            org_notification_service.send_join_application_approved_notification(
                applicant=application.applicant,
                organization=application.organization,
                reviewer=application.reviewer,
                application=application
            )
            logger.info(f"已向申请人 {application.applicant.username} 发送申请通过通知")
        elif application.status == 'rejected':
            org_notification_service.send_join_application_rejected_notification(
                applicant=application.applicant,
                organization=application.organization,
                reviewer=application.reviewer,
                application=application
            )
            logger.info(f"已向申请人 {application.applicant.username} 发送申请被拒绝通知")
            
    except Exception as e:
        logger.error(f"发送审核结果通知失败: {str(e)}")


def ensure_join_application_notification_setup():
    """
    确保组织加入申请相关的通知类型和模板存在
    """
    try:
        # 创建或获取申请提交通知类型（发给管理员）
        submitted_type, submitted_created = NotificationType.objects.get_or_create(
            code='organization_join_application_submitted',
            defaults={
                'name': '组织加入申请提交通知',
                'category': 'organization',
                'description': '当有用户提交加入组织申请时发送给管理员的通知',
                'default_template': '有新的用户申请加入您的组织。',
                'is_active': True
            }
        )
        
        # 创建或获取申请通过通知类型（发给申请人）
        approved_type, approved_created = NotificationType.objects.get_or_create(
            code='organization_join_application_approved',
            defaults={
                'name': '组织加入申请通过通知',
                'category': 'organization',
                'description': '当用户的加入申请被批准时发送的通知',
                'default_template': '恭喜！您的组织加入申请已通过审核。',
                'is_active': True
            }
        )
        
        # 创建或获取申请被拒绝通知类型（发给申请人）
        rejected_type, rejected_created = NotificationType.objects.get_or_create(
            code='organization_join_application_rejected',
            defaults={
                'name': '组织加入申请被拒绝通知',
                'category': 'organization',
                'description': '当用户的加入申请被拒绝时发送的通知',
                'default_template': '很抱歉，您的组织加入申请未通过审核。',
                'is_active': True
            }
        )
        
        # 创建或获取申请提交通知模板
        submitted_template, submitted_template_created = NotificationTemplate.objects.get_or_create(
            notification_type=submitted_type,
            defaults={
                'title_template': '新的组织加入申请',
                'content_template': '用户 {{ applicant_name }}（{{ applicant_username }}）申请加入组织 {{ organization_name }}。申请理由：{{ application_reason }}。申请时间：{{ application_time }}。请及时处理。',
                'variables': {
                    'applicant_name': '申请人姓名',
                    'applicant_username': '申请人用户名',
                    'applicant_email': '申请人邮箱',
                    'organization_name': '组织名称',
                    'organization_id': '组织ID',
                    'application_reason': '申请理由',
                    'application_time': '申请时间',
                    'application_id': '申请ID'
                }
            }
        )
        
        # 创建或获取申请通过通知模板
        approved_template, approved_template_created = NotificationTemplate.objects.get_or_create(
            notification_type=approved_type,
            defaults={
                'title_template': '组织加入申请通过',
                'content_template': '恭喜！您申请加入组织 {{ organization_name }} 的申请已通过审核。审核人：{{ reviewer_name }}。{% if review_comment %}审核意见：{{ review_comment }}。{% endif %}审核时间：{{ review_time }}。欢迎加入我们！',
                'variables': {
                    'organization_name': '组织名称',
                    'organization_id': '组织ID',
                    'reviewer_name': '审核人姓名',
                    'reviewer_username': '审核人用户名',
                    'review_comment': '审核意见',
                    'review_time': '审核时间',
                    'application_id': '申请ID'
                }
            }
        )
        
        # 创建或获取申请被拒绝通知模板
        rejected_template, rejected_template_created = NotificationTemplate.objects.get_or_create(
            notification_type=rejected_type,
            defaults={
                'title_template': '组织加入申请被拒绝',
                'content_template': '很抱歉，您申请加入组织 {{ organization_name }} 的申请未通过审核。审核人：{{ reviewer_name }}。{% if review_comment %}拒绝原因：{{ review_comment }}。{% endif %}审核时间：{{ review_time }}。如有疑问，请联系组织管理员。',
                'variables': {
                    'organization_name': '组织名称',
                    'organization_id': '组织ID',
                    'reviewer_name': '审核人姓名',
                    'reviewer_username': '审核人用户名',
                    'review_comment': '审核意见',
                    'review_time': '审核时间',
                    'application_id': '申请ID'
                }
            }
        )
        
        if submitted_created:
            logger.info(f"创建了新的通知类型: {submitted_type.name}")
        if approved_created:
            logger.info(f"创建了新的通知类型: {approved_type.name}")
        if rejected_created:
            logger.info(f"创建了新的通知类型: {rejected_type.name}")
            
        if submitted_template_created:
            logger.info(f"创建了新的通知模板: {submitted_template.title_template}")
        if approved_template_created:
            logger.info(f"创建了新的通知模板: {approved_template.title_template}")
        if rejected_template_created:
            logger.info(f"创建了新的通知模板: {rejected_template.title_template}")
            
        return submitted_type, approved_type, rejected_type, submitted_template, approved_template, rejected_template
            
    except Exception as e:
        logger.error(f"设置组织加入申请通知类型和模板失败: {str(e)}")
        return None, None, None, None, None, None