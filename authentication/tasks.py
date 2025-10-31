from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from .models import AccountDeletionLog, OrganizationInvitationCode
from user.models import User, Student, OrganizationUser
from organization.models import Organization
# from .invitation_utils import cleanup_expired_invitation_codes  # 函数不存在，注释掉
import logging
import os
import json

logger = logging.getLogger(__name__)


@shared_task
def process_scheduled_account_deletions():
    """处理计划中的账户删除任务"""
    try:
        current_time = timezone.now()
        
        # 查找所有到期的删除申请
        pending_deletions = AccountDeletionLog.objects.filter(
            status__in=['pending', 'approved'],
            scheduled_deletion_at__lte=current_time
        )
        
        processed_count = 0
        failed_count = 0
        
        for deletion_log in pending_deletions:
            try:
                # 执行单个账户删除
                success = execute_account_deletion(deletion_log.id)
                if success:
                    processed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"处理账户删除失败 - 删除ID: {deletion_log.id}, 错误: {str(e)}")
                failed_count += 1
        
        logger.info(f"账户删除任务完成 - 成功: {processed_count}, 失败: {failed_count}")
        return {
            'processed': processed_count,
            'failed': failed_count,
            'total': processed_count + failed_count
        }
        
    except Exception as e:
        logger.error(f"处理计划账户删除任务失败: {str(e)}")
        return {'error': str(e)}


@shared_task
def execute_account_deletion(deletion_log_id):
    """执行单个账户删除"""
    try:
        with transaction.atomic():
            # 获取删除记录
            deletion_log = AccountDeletionLog.objects.select_for_update().get(
                id=deletion_log_id
            )
            
            # 检查状态是否仍然有效
            if deletion_log.status not in ['pending', 'approved']:
                logger.warning(f"删除申请状态无效: {deletion_log.status}")
                return False
            
            # 获取用户信息
            try:
                user = User.objects.get(id=deletion_log.user_id)
            except User.DoesNotExist:
                logger.warning(f"用户不存在: {deletion_log.user_id}")
                deletion_log.status = 'completed'
                deletion_log.actual_deletion_at = timezone.now()
                deletion_log.save()
                return True
            
            # 数据备份
            backup_path = backup_user_data(user, deletion_log)
            
            # 执行删除操作
            delete_user_data(user)
            
            # 更新删除记录
            deletion_log.status = 'completed'
            deletion_log.actual_deletion_at = timezone.now()
            deletion_log.processed_at = timezone.now()
            deletion_log.data_backup_path = backup_path
            deletion_log.is_data_anonymized = True
            deletion_log.save()
            
            # 发送删除确认邮件
            send_account_deletion_completion_email(user.email, user.username, deletion_log)
            
            logger.info(f"账户删除成功 - 用户ID: {user.id}, 用户名: {user.username}")
            return True
            
    except Exception as e:
        logger.error(f"执行账户删除失败 - 删除ID: {deletion_log_id}, 错误: {str(e)}")
        return False


def backup_user_data(user, deletion_log):
    """备份用户数据"""
    try:
        # 创建备份目录
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'user_backups', str(timezone.now().year))
        os.makedirs(backup_dir, exist_ok=True)
        
        # 备份文件路径
        backup_filename = f"user_{user.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # 收集用户数据
        user_data = {
            'user_info': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'real_name': user.real_name,
                'user_type': user.user_type,
                'phone': user.phone,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
            },
            'deletion_info': {
                'deletion_id': str(deletion_log.id),
                'deletion_type': deletion_log.deletion_type,
                'reason': deletion_log.reason,
                'requested_at': deletion_log.requested_at.isoformat(),
                'scheduled_deletion_at': deletion_log.scheduled_deletion_at.isoformat() if deletion_log.scheduled_deletion_at else None,
            },
            'backup_metadata': {
                'backup_time': timezone.now().isoformat(),
                'backup_version': '1.0',
            }
        }
        
        # 根据用户类型收集特定数据
        if user.user_type == 'student':
            try:
                student = Student.objects.get(user=user)
                user_data['student_info'] = {
                    'student_id': student.student_id,
                    'school': student.school,
                    'major': student.major,
                    'grade': student.grade,
                    'graduation_year': student.graduation_year,
                }
            except Student.DoesNotExist:
                pass
                
        elif user.user_type == 'company':
            try:
                organization_user = OrganizationUser.objects.get(user=user)
                user_data['company_info'] = {
                    'organization_name': organization_user.organization.name if organization_user.organization else None,
                    'industry': organization_user.organization.industry_or_discipline if organization_user.organization else None,
                    'organization_scale': organization_user.organization.scale if organization_user.organization else None,
                    'position': organization_user.position,
                    'permission': organization_user.permission,
                    'status': organization_user.status,
                }
            except OrganizationUser.DoesNotExist:
                pass
        
        # 写入备份文件
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"用户数据备份成功: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"用户数据备份失败 - 用户ID: {user.id}, 错误: {str(e)}")
        return None


def delete_user_data(user):
    """删除用户相关数据"""
    try:
        # 删除用户特定数据
        if user.user_type == 'student':
            Student.objects.filter(user=user).delete()
        elif user.user_type == 'company':
            OrganizationUser.objects.filter(user=user).delete()
        
        # 删除用户主记录（级联删除相关数据）
        user.delete()
        
        logger.info(f"用户数据删除成功 - 用户ID: {user.id}")
        
    except Exception as e:
        logger.error(f"用户数据删除失败 - 用户ID: {user.id}, 错误: {str(e)}")
        raise


def send_account_deletion_completion_email(email, username, deletion_log):
    """发送账户删除完成确认邮件"""
    try:
        subject = '【校企对接平台】账户删除完成确认'
        message = f'''
尊敬的用户 {username}：

您的账户删除操作已完成。

删除详情：
- 原申请时间：{deletion_log.requested_at.strftime('%Y-%m-%d %H:%M:%S')}
- 实际删除时间：{deletion_log.actual_deletion_at.strftime('%Y-%m-%d %H:%M:%S')}
- 删除原因：{deletion_log.reason or '未提供'}

重要说明：
1. 您的账户及相关数据已被永久删除
2. 相关数据已按照隐私政策进行安全备份
3. 如有疑问，请联系客服支持

感谢您曾经使用校企对接平台。

校企对接平台团队
{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,  # 删除完成后邮件发送失败不应影响删除操作
        )
        
        logger.info(f"账户删除完成邮件发送成功: {email}")
        
    except Exception as e:
        logger.error(f"账户删除完成邮件发送失败: {email} - {str(e)}")


@shared_task
def cleanup_old_deletion_logs():
    """清理旧的删除日志（保留已完成的记录用于审计）"""
    try:
        # 删除超过1年的已取消申请记录
        one_year_ago = timezone.now() - timezone.timedelta(days=365)
        
        deleted_count = AccountDeletionLog.objects.filter(
            status='cancelled',
            processed_at__lt=one_year_ago
        ).delete()[0]
        
        logger.info(f"清理旧删除日志完成，删除了 {deleted_count} 条记录")
        return deleted_count
        
    except Exception as e:
        logger.error(f"清理旧删除日志失败: {str(e)}")
        return 0


@shared_task
def send_deletion_reminder_emails():
    """发送删除提醒邮件（删除前24小时）"""
    try:
        # 查找24小时内将被删除的账户
        tomorrow = timezone.now() + timezone.timedelta(hours=24)
        day_after_tomorrow = timezone.now() + timezone.timedelta(hours=48)
        
        pending_deletions = AccountDeletionLog.objects.filter(
            status__in=['pending', 'approved'],
            scheduled_deletion_at__gte=tomorrow,
            scheduled_deletion_at__lt=day_after_tomorrow
        )
        
        sent_count = 0
        
        for deletion_log in pending_deletions:
            try:
                user = User.objects.get(id=deletion_log.user_id)
                send_deletion_reminder_email(user, deletion_log)
                sent_count += 1
            except User.DoesNotExist:
                continue
            except Exception as e:
                logger.error(f"发送删除提醒邮件失败 - 用户ID: {deletion_log.user_id}, 错误: {str(e)}")
        
        logger.info(f"删除提醒邮件发送完成，发送了 {sent_count} 封邮件")
        return sent_count
        
    except Exception as e:
        logger.error(f"发送删除提醒邮件任务失败: {str(e)}")
        return 0


def send_deletion_reminder_email(user, deletion_log):
    """发送单个删除提醒邮件"""
    subject = '【校企对接平台】账户删除最后提醒'
    message = f'''
尊敬的用户 {user.username}：

这是您账户删除的最后提醒。

删除详情：
- 申请时间：{deletion_log.requested_at.strftime('%Y-%m-%d %H:%M:%S')}
- 计划删除时间：{deletion_log.scheduled_deletion_at.strftime('%Y-%m-%d')} 00:00:00
- 剩余时间：约24小时

重要提醒：
1. 您的账户将在24小时内被永久删除
2. 删除后无法恢复，请谨慎考虑
3. 如需取消删除，请立即登录账户进行操作

如果这不是您的操作，请立即联系客服。

校企对接平台团队
    '''
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@shared_task(bind=True)
def cleanup_expired_invitation_codes_task(self):
    """
    定时清理过期的邀请码
    将过期的邀请码状态更新为 'expired'
    """
    try:
        with transaction.atomic():
            # 获取所有过期但状态仍为active的邀请码
            expired_codes = OrganizationInvitationCode.objects.filter(
                status='active',
                expires_at__lt=timezone.now()
            )
            
            expired_count = expired_codes.count()
            
            if expired_count > 0:
                # 批量更新状态为过期
                expired_codes.update(
                    status='expired',
                    updated_at=timezone.now()
                )
                
                logger.info(f"成功清理了 {expired_count} 个过期的邀请码")
                
                return {
                    'status': 'success',
                    'message': f'成功清理了 {expired_count} 个过期的邀请码',
                    'expired_count': expired_count
                }
            else:
                logger.info("没有发现过期的邀请码")
                return {
                    'status': 'success',
                    'message': '没有发现过期的邀请码',
                    'expired_count': 0
                }
                
    except Exception as e:
        logger.error(f"清理过期邀请码时发生错误: {str(e)}")
        return {
            'status': 'error',
            'message': f'清理过期邀请码时发生错误: {str(e)}'
        }


@shared_task(bind=True)
def cleanup_old_invitation_codes_task(self):
    """
    定时清理旧的邀请码记录
    删除创建时间超过90天的已过期或已禁用的邀请码记录
    """
    try:
        with transaction.atomic():
            # 计算90天前的时间
            cutoff_date = timezone.now() - timezone.timedelta(days=90)
            
            # 获取需要删除的旧邀请码记录
            old_codes = OrganizationInvitationCode.objects.filter(
                status__in=['expired', 'disabled'],
                created_at__lt=cutoff_date
            )
            
            old_count = old_codes.count()
            
            if old_count > 0:
                # 删除旧记录
                old_codes.delete()
                
                logger.info(f"成功清理了 {old_count} 个旧的邀请码记录")
                
                return {
                    'status': 'success',
                    'message': f'成功清理了 {old_count} 个旧的邀请码记录',
                    'deleted_count': old_count
                }
            else:
                logger.info("没有发现需要清理的旧邀请码记录")
                return {
                    'status': 'success',
                    'message': '没有发现需要清理的旧邀请码记录',
                    'deleted_count': 0
                }
                
    except Exception as e:
        logger.error(f"清理旧邀请码记录时发生错误: {str(e)}")
        return {
            'status': 'error',
            'message': f'清理旧邀请码记录时发生错误: {str(e)}'
        }


@shared_task(bind=True)
def send_invitation_code_expiry_notification(self):
    """
    发送邀请码即将过期的通知
    提醒管理员邀请码将在24小时内过期
    """
    try:
        from notification.services import notification_service
        from notification.models import NotificationLog
        
        # 计算24小时后的时间
        tomorrow = timezone.now() + timezone.timedelta(hours=24)
        
        # 获取即将在24小时内过期的活跃邀请码，且未发送过期通知的
        expiring_codes = OrganizationInvitationCode.objects.filter(
            status='active',
            expires_at__lte=tomorrow,
            expires_at__gt=timezone.now(),
            expiry_notification_sent=False  # 防重复通知
        ).select_related('organization', 'created_by')
        
        notification_count = 0
        
        for code in expiring_codes:
            try:
                # 计算剩余小时数
                time_diff = code.expires_at - timezone.now()
                hours_left = max(0, int(time_diff.total_seconds() / 3600))
                
                # 准备模板变量
                template_vars = {
                    'invitation_code': code.code,
                    'organization_name': code.organization.name,
                    'expires_at': code.expires_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'hours_left': hours_left,
                    'organization_url': f'/organization/{code.organization.id}/'
                }
                
                # 发送通知给邀请码创建者
                notification = notification_service.create_and_send_notification(
                    recipient=code.created_by,
                    notification_type_code='org_invitation_code_expiring_soon',
                    template_vars=template_vars,
                    strategies=['websocket', 'email']  # 同时发送WebSocket和邮件通知
                )
                
                if notification:
                    # 标记已发送过期通知
                    code.expiry_notification_sent = True
                    code.save(update_fields=['expiry_notification_sent'])
                    
                    notification_count += 1
                    logger.info(
                        f"邀请码即将过期通知已发送: {code.code} -> {code.created_by.username}, "
                        f"剩余 {hours_left} 小时"
                    )
                else:
                    logger.warning(f"邀请码过期通知发送失败: {code.code}")
                
            except Exception as e:
                logger.error(f"发送邀请码过期通知时发生错误: {str(e)}")
                continue
        
        return {
            'status': 'success',
            'message': f'成功发送了 {notification_count} 个邀请码过期通知',
            'notification_count': notification_count
        }
        
    except Exception as e:
        logger.error(f"发送邀请码过期通知时发生错误: {str(e)}")
        return {
            'status': 'error',
            'message': f'发送邀请码过期通知时发生错误: {str(e)}'
        }


@shared_task(bind=True)
def send_invitation_code_expired_notification(self):
    """
    发送邀请码已过期的通知
    通知创建者邀请码已过期
    """
    try:
        from notification.services import notification_service
        
        # 获取已过期但未发送过期通知的邀请码
        expired_codes = OrganizationInvitationCode.objects.filter(
            expires_at__lt=timezone.now(),
            expired_notification_sent=False  # 防重复通知
        ).select_related('organization', 'created_by')
        
        notification_count = 0
        
        for code in expired_codes:
            try:
                # 准备模板变量
                template_vars = {
                    'invitation_code': code.code,
                    'organization_name': code.organization.name,
                    'expires_at': code.expires_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by_name': code.created_by.get_full_name() or code.created_by.username
                }
                
                # 发送通知给邀请码创建者
                notification = notification_service.create_and_send_notification(
                    recipient=code.created_by,
                    notification_type_code='org_invitation_code_expired',
                    template_vars=template_vars,
                    strategies=['websocket', 'email']  # 同时发送WebSocket和邮件通知
                )
                
                if notification:
                    # 标记已发送过期通知
                    code.expired_notification_sent = True
                    code.save(update_fields=['expired_notification_sent'])
                    
                    notification_count += 1
                    logger.info(
                        f"邀请码已过期通知已发送: {code.code} -> {code.created_by.username}"
                    )
                else:
                    logger.warning(f"邀请码已过期通知发送失败: {code.code}")
                
            except Exception as e:
                logger.error(f"发送邀请码已过期通知时发生错误: {str(e)}")
                continue
        
        return {
            'status': 'success',
            'message': f'成功发送了 {notification_count} 个邀请码已过期通知',
            'notification_count': notification_count
        }
        
    except Exception as e:
        logger.error(f"发送邀请码已过期通知时发生错误: {str(e)}")
        return {
            'status': 'error',
            'message': f'发送邀请码已过期通知时发生错误: {str(e)}'
        }


@shared_task(bind=True)
def send_invitation_code_used_notification(self, invitation_code_id, user_id):
    """
    发送邀请码已使用的通知
    当邀请码被使用时触发此任务
    
    Args:
        invitation_code_id: 邀请码ID
        user_id: 使用邀请码的用户ID
    """
    try:
        from notification.services import notification_service
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # 获取邀请码和使用者信息
        try:
            invitation_code = OrganizationInvitationCode.objects.select_related(
                'organization', 'created_by'
            ).get(id=invitation_code_id)
            user = User.objects.get(id=user_id)
        except (OrganizationInvitationCode.DoesNotExist, User.DoesNotExist) as e:
            logger.error(f"邀请码或用户不存在: {str(e)}")
            return {
                'status': 'error',
                'message': f'邀请码或用户不存在: {str(e)}'
            }
        
        # 每次邀请码被使用都应该发送通知，不设置防重复机制
        now = timezone.now()
        
        # 计算剩余使用次数
        remaining_uses = invitation_code.max_uses - invitation_code.used_count if invitation_code.max_uses else None
        
        # 准备模板变量
        template_vars = {
            'invitation_code_last_4': invitation_code.code[-4:],  # 只保留后4位
            'organization_name': invitation_code.organization.name,
            'created_by_name': invitation_code.created_by.get_full_name() or invitation_code.created_by.username,
            'user_name': user.get_full_name() or user.username,
            'user_email': user.email,
            'used_at': now.strftime('%Y-%m-%d %H:%M:%S'),
            'used_count': invitation_code.used_count,
            'max_uses': invitation_code.max_uses,
            'remaining_uses': remaining_uses
        }
        
        # 发送通知给邀请码创建者
        notification = notification_service.create_and_send_notification(
            recipient=invitation_code.created_by,
            notification_type_code='org_invitation_code_used',
            template_vars=template_vars,
            strategies=['websocket', 'email']  # 同时发送WebSocket和邮件通知
        )
        
        if notification:
            logger.info(
                f"邀请码使用通知已发送: {invitation_code.code} -> {invitation_code.created_by.username} (用户: {user.username})"
            )
            
            return {
                'status': 'success',
                'message': f'邀请码使用通知已发送给 {invitation_code.created_by.username}'
            }
        else:
            logger.warning(f"邀请码使用通知发送失败: {invitation_code.code}")
            return {
                'status': 'error',
                'message': '通知发送失败'
            }
        
    except Exception as e:
        logger.error(f"发送邀请码使用通知时发生错误: {str(e)}")
        return {
            'status': 'error',
            'message': f'发送邀请码使用通知时发生错误: {str(e)}'
        }