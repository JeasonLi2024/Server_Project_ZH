from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import timedelta
import logging

# 导入相关模型
from user.models import OrganizationUser
from project.models import Requirement
from studentproject.models import StudentProject

from .services import org_notification_service, NotificationService, notification_service, student_notification_service
from .models import Notification, NotificationLog

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def send_requirement_deadline_reminders():
    """发送需求截止评分提醒 - 提醒需求创建者：需求已截止，可以为已完成项目评分"""
    logger.info("开始执行需求截止评分提醒任务")
    
    if not Requirement:
        logger.warning("Requirement模型不可用，跳过任务")
        return
    
    # 获取已截止的需求：finish_time已过，状态为completed，但evaluation_published为false
    expired_requirements = Requirement.objects.filter(
        finish_time__lt=timezone.now().date(),
        status='completed',
        evaluation_published=False
    ).select_related('publish_people__user')
    
    reminder_count = 0
    
    for requirement in expired_requirements:
        try:
            # 检查该需求下是否有已完成的项目
            completed_projects_count = 0
            pending_score_count = 0
            
            if StudentProject:
                completed_projects_count = StudentProject.objects.filter(
                    requirement=requirement,
                    status='completed'
                ).count()
                
                # 计算待评分项目数（已完成但未评分的项目）
                # 注意：StudentProject模型中没有score字段，需要通过projectscore应用查询
                from projectscore.models import ProjectEvaluation
                pending_score_count = StudentProject.objects.filter(
                    requirement=requirement,
                    status='completed'
                ).exclude(
                    id__in=ProjectEvaluation.objects.values_list('project_id', flat=True)
                ).count()
                
                # 只有当存在已完成项目时才发送提醒
                if completed_projects_count == 0:
                    continue
            
            # 检查是否已经发送过提醒（避免重复发送）
            recent_reminder = Notification.objects.filter(
                recipient=requirement.publish_people.user,
                notification_type__code='org_requirement_deadline_reminder',
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).exists()
            
            if not recent_reminder:
                org_notification_service.send_requirement_deadline_reminder(
                    requirement_creator=requirement.publish_people.user,
                    requirement_title=requirement.title,
                    deadline=requirement.finish_time,
                    requirement_status=requirement.get_status_display(),
                    completed_project_count=completed_projects_count,
                    pending_score_count=pending_score_count,
                    requirement_obj=requirement
                )
                
                reminder_count += 1
                logger.info(f"发送截止评分提醒: {requirement.title} -> {requirement.publish_people.user.username}")
        
        except Exception as e:
            logger.error(f"发送截止评分提醒失败 {requirement.title}: {str(e)}")
    
    logger.info(f"需求截止评分提醒任务完成，共发送 {reminder_count} 条提醒")
    return reminder_count





@shared_task
def auto_complete_expired_requirements():
    """自动将已到截止时间的需求状态修改为completed - 优化版本"""
    logger.info("开始执行需求状态自动更新任务")
    
    if not Requirement:
        logger.warning("Requirement模型不可用，跳过任务")
        return
    
    try:
        # 使用bulk_update进行批量更新，减少锁定时间
        with transaction.atomic():
            expired_requirements = Requirement.objects.filter(
                finish_time__lt=timezone.now().date(),
                status='in_progress'
            )
            
            # 记录要更新的需求信息（用于日志）
            requirement_info = list(expired_requirements.values('id', 'title'))
            
            # 批量更新状态
            updated_count = expired_requirements.update(status='completed')
            
            # 记录更新的需求信息
            for req_info in requirement_info:
                logger.info(f"需求状态已更新为completed: {req_info['title']} (ID: {req_info['id']})")
            
            logger.info(f"需求状态自动更新任务完成，共更新 {updated_count} 个需求")
            return updated_count
            
    except Exception as e:
        logger.error(f"批量更新需求状态失败，错误: {str(e)}")
        return 0


@shared_task
def cleanup_old_notifications(days=30):
    """清理旧通知"""
    logger.info(f"开始清理 {days} 天前的旧通知")
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # 删除已读的旧通知
    deleted_count = Notification.objects.filter(
        created_at__lt=cutoff_date,
        is_read=True
    ).delete()[0]
    
    logger.info(f"清理旧通知完成，删除了 {deleted_count} 条通知")
    return deleted_count


@shared_task
def cleanup_old_notification_logs(days=90):
    """清理旧通知日志"""
    logger.info(f"开始清理 {days} 天前的通知日志")
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    deleted_count = NotificationLog.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"清理通知日志完成，删除了 {deleted_count} 条日志")
    return deleted_count


@shared_task
def send_bulk_notification(user_ids, notification_type_code, title, content, extra_data=None):
    """批量发送通知"""
    logger.info(f"开始批量发送通知: {notification_type_code} 给 {len(user_ids)} 个用户")
    
    users = User.objects.filter(id__in=user_ids)
    notification_service = NotificationService()
    
    success_count = 0
    
    for user in users:
        try:
            notification_service.create_notification(
                recipient=user,
                notification_type_code=notification_type_code,
                title=title,
                content=content,
                extra_data=extra_data or {}
            )
            success_count += 1
        except Exception as e:
            logger.error(f"批量发送通知失败 {user.username}: {str(e)}")
    
    logger.info(f"批量通知发送完成，成功发送 {success_count}/{len(user_ids)} 条")
    return success_count


@shared_task
def send_system_maintenance_notification(maintenance_time, duration_hours, affected_services=None):
    """发送系统维护通知"""
    logger.info("开始发送系统维护通知")
    
    # 获取所有活跃用户
    active_users = User.objects.filter(is_active=True)
    
    notification_service = NotificationService()
    
    title = "系统维护通知"
    content = f"系统将于 {maintenance_time} 进行维护，预计持续 {duration_hours} 小时。"
    
    if affected_services:
        content += f"\n受影响的服务：{', '.join(affected_services)}"
    
    content += "\n维护期间可能无法正常使用系统，请提前做好准备。感谢您的理解与配合！"
    
    success_count = 0
    
    for user in active_users:
        try:
            notification_service.create_notification(
                recipient=user,
                notification_type_code='system_maintenance',
                title=title,
                content=content,
                extra_data={
                    'maintenance_time': str(maintenance_time),
                    'duration_hours': duration_hours,
                    'affected_services': affected_services or []
                }
            )
            success_count += 1
        except Exception as e:
            logger.error(f"发送维护通知失败 {user.username}: {str(e)}")
    
    logger.info(f"系统维护通知发送完成，成功发送 {success_count}/{active_users.count()} 条")
    return success_count


@shared_task
def generate_notification_statistics(date=None):
    """生成通知统计报告"""
    if date is None:
        date = timezone.now().date()
    
    logger.info(f"生成 {date} 的通知统计报告")
    
    # 统计当日通知数据
    daily_notifications = Notification.objects.filter(
        created_at__date=date
    )
    
    stats = {
        'date': str(date),
        'total_sent': daily_notifications.count(),
        'total_read': daily_notifications.filter(is_read=True).count(),
        'by_type': {},
        'by_channel': {}
    }
    
    # 按类型统计
    for notification in daily_notifications.select_related('notification_type'):
        type_code = notification.notification_type.code
        if type_code not in stats['by_type']:
            stats['by_type'][type_code] = {'sent': 0, 'read': 0}
        
        stats['by_type'][type_code]['sent'] += 1
        if notification.is_read:
            stats['by_type'][type_code]['read'] += 1
    
    # 按渠道统计（从日志中获取）
    daily_logs = NotificationLog.objects.filter(
        created_at__date=date
    )
    
    for log in daily_logs:
        channel = log.channel
        if channel not in stats['by_channel']:
            stats['by_channel'][channel] = {'sent': 0, 'success': 0, 'failed': 0}
        
        stats['by_channel'][channel]['sent'] += 1
        if log.status == 'success':
            stats['by_channel'][channel]['success'] += 1
        else:
            stats['by_channel'][channel]['failed'] += 1
    
    # 计算读取率
    if stats['total_sent'] > 0:
        stats['read_rate'] = round(stats['total_read'] / stats['total_sent'] * 100, 2)
    else:
        stats['read_rate'] = 0
    
    logger.info(f"通知统计报告生成完成: {stats}")
    return stats


@shared_task
def send_new_deadline_reminders(days_before=1):
    """
    发送需求截止日期提醒的定时任务（新版本）
    
    Args:
        days_before (int): 提前多少天发送提醒
    
    Returns:
        dict: 执行结果统计
    """
    try:
        if not Requirement:
            logger.warning("Requirement模型不可用，跳过任务")
            return {'success': False, 'error': 'Requirement model not available'}
        
        # 计算目标日期范围
        now = timezone.now()
        target_date = now + timedelta(days=days_before)
        
        # 查找即将到期的需求
        upcoming_deadlines = Requirement.objects.filter(
            deadline__date=target_date.date(),
            status='published'
        ).select_related('organization')
        
        sent_count = 0
        error_count = 0
        
        for requirement in upcoming_deadlines:
            try:
                notification_service.send_requirement_deadline_reminder(
                    requirement=requirement
                )
                sent_count += 1
                logger.info(f'已发送截止提醒: {requirement.title}')
                
            except Exception as e:
                error_count += 1
                logger.error(f'发送需求截止提醒失败 (需求ID: {requirement.id}): {str(e)}')
        
        result = {
            'success': True,
            'sent_count': sent_count,
            'error_count': error_count,
            'total_requirements': upcoming_deadlines.count(),
            'target_date': target_date.date().isoformat()
        }
        
        logger.info(f'截止提醒任务完成: {result}')
        return result
        
    except Exception as e:
        logger.error(f'截止提醒任务执行失败: {str(e)}')
        return {
            'success': False,
            'error': str(e),
            'sent_count': 0,
            'error_count': 0
        }


@shared_task
def send_daily_deadline_reminders():
    """
    每日定时发送截止日期提醒（提前1天）
    """
    return send_new_deadline_reminders(days_before=1)


@shared_task
def send_weekly_deadline_reminders():
    """
    每周定时发送截止日期提醒（提前7天）
    """
    return send_new_deadline_reminders(days_before=7)


@shared_task
def send_invitation_expiry_reminders():
    """发送邀请过期提醒 - 提醒被邀请人邀请即将过期"""
    logger.info("开始执行邀请过期提醒任务")
    
    try:
        from studentproject.models import ProjectInvitation
    except ImportError:
        logger.warning("ProjectInvitation模型不可用，跳过任务")
        return 0
    
    # 获取明天过期的邀请（提前一天提醒）
    tomorrow = timezone.now() + timedelta(days=1)
    expiring_invitations = ProjectInvitation.objects.filter(
        expires_at__date=tomorrow.date(),
        status='pending'
    ).select_related('invitee', 'inviter', 'project')
    
    reminder_count = 0
    
    for invitation in expiring_invitations:
        try:
            # 检查是否已经发送过提醒（避免重复发送）
            recent_reminder = Notification.objects.filter(
                recipient=invitation.invitee,
                notification_type__code='student_invitation_expiry_reminder',
                created_at__gte=timezone.now() - timedelta(hours=12)
            ).exists()
            
            if not recent_reminder:
                student_notification_service.send_invitation_expiry_reminder(
                    invitee=invitation.invitee,
                    inviter=invitation.inviter,
                    project=invitation.project,
                    invitation=invitation
                )
                
                reminder_count += 1
                logger.info(f"发送邀请过期提醒: {invitation.project.title} -> {invitation.invitee.username}")
        
        except Exception as e:
            logger.error(f"发送邀请过期提醒失败 {invitation.id}: {str(e)}")
    
    logger.info(f"邀请过期提醒任务完成，共发送 {reminder_count} 条提醒")
    return reminder_count