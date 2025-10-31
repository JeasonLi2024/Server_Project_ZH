from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.template import Template, Context
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
import pytz

from .models import (
    Notification,
    NotificationType,
    NotificationTemplate,
    NotificationPreference,
    NotificationLog
)
from .serializers import NotificationSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationStrategy(ABC):
    """通知策略抽象基类"""
    
    @abstractmethod
    def send(self, notification: Notification) -> bool:
        """发送通知"""
        pass
    
    @abstractmethod
    def is_available(self, user: User) -> bool:
        """检查该策略对用户是否可用"""
        pass


class WebSocketNotificationStrategy(NotificationStrategy):
    """WebSocket实时通知策略"""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def send(self, notification: Notification) -> bool:
        """通过WebSocket发送通知"""
        if not self.channel_layer:
            logger.warning("Channel layer 未配置，无法发送WebSocket通知")
            return False
        
        try:
            # 临时标记为已发送状态以便正确序列化
            original_status = notification.status
            original_sent_at = notification.sent_at
            notification.status = 'sent'
            notification.sent_at = timezone.now()
            
            # 序列化通知数据
            serializer = NotificationSerializer(notification)
            notification_data = serializer.data
            
            # 恢复原始状态（将在send_notification方法中正式更新）
            notification.status = original_status
            notification.sent_at = original_sent_at
            
            # 发送到用户的WebSocket组
            room_group_name = f'notifications_{notification.recipient.id}'
            async_to_sync(self.channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'notification_message',
                    'notification': notification_data
                }
            )
            
            logger.debug(f"WebSocket通知已发送: {notification.id} -> 用户 {notification.recipient.id}")
            return True
            
        except Exception as e:
            logger.error(f"发送WebSocket通知失败: {str(e)}")
            return False
    
    def is_available(self, user: User) -> bool:
        """检查WebSocket通知是否可用"""
        try:
            # 如果是OrganizationUser对象，获取其关联的User对象
            if hasattr(user, 'user') and hasattr(user.user, 'notification_preference'):
                preference = user.user.notification_preference
            else:
                preference = user.notification_preference
            return preference.enable_websocket
        except (NotificationPreference.DoesNotExist, AttributeError):
            return True  # 默认启用


class EmailNotificationStrategy(NotificationStrategy):
    """邮件通知策略"""
    
    def send(self, notification: Notification) -> bool:
        """通过邮件发送通知"""
        try:
            from django.core.mail import EmailMultiAlternatives
            from django.conf import settings
            
            # 获取用户邮箱
            user_email = self._get_user_email(notification.recipient)
            if not user_email:
                logger.warning(f"用户 {notification.recipient.id} 没有邮箱地址")
                return False
            
            # 获取通知模板
            try:
                template = notification.notification_type.notification_template
            except:
                logger.warning(f"通知类型 {notification.notification_type.code} 没有关联的通知模板")
                return False
            
            if not template or not hasattr(template, 'email_subject') or not hasattr(template, 'email_content'):
                logger.warning(f"通知类型 {notification.notification_type.code} 没有配置邮件模板")
                return False
            
            if not template.email_subject or not template.email_content:
                logger.warning(f"通知类型 {notification.notification_type.code} 的邮件模板内容为空")
                return False
            
            # 渲染邮件主题和内容
            context = notification.extra_data or {}
            context.update({
                'recipient_name': self._get_user_display_name(notification.recipient),
                'title': notification.title,
                'content': notification.content,
                'notification_id': notification.id,
            })
            
            subject = self._render_template_content(template.email_subject, context)
            html_content = self._render_template_content(template.email_content, context)
            
            # 创建纯文本版本（从HTML中提取）
            import re
            text_content = re.sub(r'<[^>]+>', '', html_content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            # 创建邮件对象
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email]
            )
            msg.attach_alternative(html_content, "text/html")
            
            # 发送邮件
            msg.send()
            
            logger.info(f"邮件通知发送成功: {notification.title} -> {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"邮件通知发送失败: {notification.title} -> {str(e)}")
            return False
    
    def _get_user_email(self, user):
        """获取用户邮箱地址"""
        if hasattr(user, 'user') and hasattr(user.user, 'email'):
            return user.user.email
        return getattr(user, 'email', None)
    
    def _get_user_display_name(self, user):
        """获取用户显示名称"""
        if hasattr(user, 'user'):
            actual_user = user.user
        else:
            actual_user = user
        
        return getattr(actual_user, 'real_name', None) or getattr(actual_user, 'get_full_name', lambda: None)() or getattr(actual_user, 'username', '用户')
    
    def _render_template_content(self, template_content, context):
        """渲染模板内容"""
        try:
            from django.template import Template, Context
            template = Template(template_content)
            return template.render(Context(context))
        except Exception as e:
            logger.error(f"模板渲染失败: {str(e)}")
            return template_content
    
    def is_available(self, user: User) -> bool:
        """检查邮件通知是否可用"""
        try:
            # 如果是OrganizationUser对象，获取其关联的User对象
            if hasattr(user, 'user') and hasattr(user.user, 'notification_preference'):
                preference = user.user.notification_preference
                user_email = user.user.email
            else:
                preference = user.notification_preference
                user_email = user.email
            return preference.enable_email and bool(user_email)
        except (NotificationPreference.DoesNotExist, AttributeError):
            user_email = getattr(user, 'email', None) or getattr(getattr(user, 'user', None), 'email', None)
            return bool(user_email)


class SMSNotificationStrategy(NotificationStrategy):
    """短信通知策略"""
    
    def send(self, notification: Notification) -> bool:
        """通过短信发送通知"""
        # TODO: 实现短信发送逻辑
        logger.info(f"短信通知: {notification.title} -> {notification.recipient.phone}")
        return True
    
    def is_available(self, user: User) -> bool:
        """检查短信通知是否可用"""
        try:
            # 如果是OrganizationUser对象，获取其关联的User对象
            if hasattr(user, 'user') and hasattr(user.user, 'notification_preference'):
                preference = user.user.notification_preference
                user_phone = getattr(user.user, 'phone', None)
            else:
                preference = user.notification_preference
                user_phone = getattr(user, 'phone', None)
            return preference.enable_sms and bool(user_phone)
        except (NotificationPreference.DoesNotExist, AttributeError):
            user_phone = getattr(user, 'phone', None) or getattr(getattr(user, 'user', None), 'phone', None)
            return bool(user_phone)


class NotificationService:
    """通知服务类"""
    
    def __init__(self):
        self.strategies = {
            'websocket': WebSocketNotificationStrategy(),
            'email': EmailNotificationStrategy(),
            'sms': SMSNotificationStrategy(),
        }
        self.channel_layer = get_channel_layer()
    
    def create_notification(
        self,
        recipient: User,
        notification_type_code: str,
        title: str = None,
        content: str = None,
        sender: User = None,
        related_object: Any = None,
        priority: str = 'normal',
        extra_data: Dict = None,
        expires_at: timezone.datetime = None,
        template_vars: Dict = None
    ) -> Optional[Notification]:
        """创建通知"""
        try:
            # 获取通知类型
            notification_type = NotificationType.objects.get(
                code=notification_type_code,
                is_active=True
            )
            
            # 检查用户偏好设置
            if not self._should_send_notification(recipient, notification_type_code):
                logger.info(f"用户 {recipient.id} 已禁用通知类型 {notification_type_code}")
                return None
            
            # 使用模板生成标题和内容
            if not title or not content:
                title, content = self._render_template(
                    notification_type, template_vars or {}
                )
            
            # 处理关联对象
            content_type = None
            object_id = None
            if related_object:
                content_type = ContentType.objects.get_for_model(related_object)
                object_id = related_object.pk
            
            # 合并template_vars到extra_data中，以便邮件模板可以访问
            merged_extra_data = extra_data or {}
            if template_vars:
                merged_extra_data.update(template_vars)
            
            # 创建通知
            with transaction.atomic():
                notification = Notification.objects.create(
                    recipient=recipient,
                    sender=sender,
                    notification_type=notification_type,
                    title=title,
                    content=content,
                    priority=priority,
                    content_type=content_type,
                    object_id=object_id,
                    extra_data=merged_extra_data,
                    expires_at=expires_at
                )
                
                # 记录创建日志
                NotificationLog.objects.create(
                    notification=notification,
                    action='created',
                    result='success',
                    message=f'通知已创建: {notification.title}'
                )
            
            logger.info(f"通知已创建: {notification.id} -> 用户 {recipient.id}")
            return notification
            
        except NotificationType.DoesNotExist:
            logger.error(f"通知类型 {notification_type_code} 不存在或未启用")
            return None
        except Exception as e:
            logger.error(f"创建通知失败: {str(e)}")
            return None
    
    def send_notification(
        self,
        notification: Notification,
        strategies: List[str] = None
    ) -> Dict[str, bool]:
        """发送通知"""
        if strategies is None:
            strategies = ['websocket']  # 默认只发送WebSocket通知
        
        results = {}
        
        for strategy_name in strategies:
            if strategy_name not in self.strategies:
                logger.warning(f"未知的通知策略: {strategy_name}")
                results[strategy_name] = False
                continue
            
            strategy = self.strategies[strategy_name]
            
            # 检查策略是否可用
            if not strategy.is_available(notification.recipient):
                logger.info(f"策略 {strategy_name} 对用户 {notification.recipient.id} 不可用")
                results[strategy_name] = False
                continue
            
            # 发送通知
            try:
                success = strategy.send(notification)
                results[strategy_name] = success
                
                # 记录发送日志
                NotificationLog.objects.create(
                    notification=notification,
                    action=f'send_{strategy_name}',
                    result='success' if success else 'failed',
                    message=f'通过 {strategy_name} 发送通知'
                )
                
            except Exception as e:
                logger.error(f"通过 {strategy_name} 发送通知失败: {str(e)}")
                results[strategy_name] = False
                
                # 记录失败日志
                NotificationLog.objects.create(
                    notification=notification,
                    action=f'send_{strategy_name}',
                    result='failed',
                    message=f'发送失败: {str(e)}'
                )
        
        # 更新通知状态
        if any(results.values()):
            notification.mark_as_sent()
        else:
            notification.mark_as_failed()
        
        # 更新未读数量
        self._update_unread_count(notification.recipient.id)
        
        return results
    
    def create_and_send_notification(
        self,
        recipient: User,
        notification_type_code: str,
        title: str = None,
        content: str = None,
        sender: User = None,
        related_object: Any = None,
        priority: str = 'normal',
        extra_data: Dict = None,
        expires_at: timezone.datetime = None,
        template_vars: Dict = None,
        strategies: List[str] = None
    ) -> Optional[Notification]:
        """创建并发送通知"""
        notification = self.create_notification(
            recipient=recipient,
            notification_type_code=notification_type_code,
            title=title,
            content=content,
            sender=sender,
            related_object=related_object,
            priority=priority,
            extra_data=extra_data,
            expires_at=expires_at,
            template_vars=template_vars
        )
        
        if notification:
            self.send_notification(notification, strategies)
        
        return notification
    
    def bulk_create_and_send_notifications(
        self,
        recipients: List[User],
        notification_type_code: str,
        title: str = None,
        content: str = None,
        sender: User = None,
        related_object: Any = None,
        priority: str = 'normal',
        extra_data: Dict = None,
        expires_at: timezone.datetime = None,
        template_vars: Dict = None,
        strategies: List[str] = None
    ) -> List[Notification]:
        """批量创建并发送通知"""
        notifications = []
        
        for recipient in recipients:
            notification = self.create_and_send_notification(
                recipient=recipient,
                notification_type_code=notification_type_code,
                title=title,
                content=content,
                sender=sender,
                related_object=related_object,
                priority=priority,
                extra_data=extra_data,
                expires_at=expires_at,
                template_vars=template_vars,
                strategies=strategies
            )
            
            if notification:
                notifications.append(notification)
        
        return notifications
    
    def _should_send_notification(self, user: User, notification_type_code: str) -> bool:
        """检查是否应该发送通知"""
        try:
            # 如果是OrganizationUser对象，获取其关联的User对象
            if hasattr(user, 'user') and hasattr(user.user, 'notification_preference'):
                preference = user.user.notification_preference
            else:
                preference = user.notification_preference
            
            # 检查类型偏好
            if not preference.is_type_enabled(notification_type_code):
                return False
            
            # 检查免打扰时间
            if preference.is_in_quiet_time():
                return False
            
            return True
            
        except (NotificationPreference.DoesNotExist, AttributeError):
            return True  # 默认发送
    
    def _render_template(
        self,
        notification_type: NotificationType,
        template_vars: Dict
    ) -> tuple[str, str]:
        """渲染通知模板"""
        try:
            template = notification_type.notification_template
            if template:
                title_template = Template(template.title_template)
                content_template = Template(template.content_template)
                
                context = Context(template_vars)
                title = title_template.render(context)
                content = content_template.render(context)
                
                return title, content
        except Exception as e:
            logger.warning(f"渲染模板失败: {str(e)}")
        
        # 使用默认模板或空值
        return notification_type.name, notification_type.description or ''
    
    def _update_unread_count(self, user_id: int):
        """更新用户未读通知数量"""
        if not self.channel_layer:
            return
        
        try:
            unread_count = Notification.objects.filter(
                recipient_id=user_id,
                is_read=False
            ).count()
            
            room_group_name = f'notifications_{user_id}'
            async_to_sync(self.channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'unread_count_update',
                    'count': unread_count
                }
            )
            
        except Exception as e:
            logger.error(f"更新未读数量失败: {str(e)}")


class StudentNotificationService:
    """学生端通知服务"""
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    def _get_user_display_name(self, user_obj):
        """获取用户显示名称，兼容User和Student对象"""
        if hasattr(user_obj, 'get_full_name'):
            # User对象
            return user_obj.get_full_name() or user_obj.username
        elif hasattr(user_obj, 'user'):
            # Student对象
            return user_obj.user.get_full_name() or user_obj.user.username
        else:
            return str(user_obj)
    
    def send_project_application_notification(
        self,
        leader: User,
        applicant: User,
        project,
        application_message: str = None
    ):
        """发送项目申请审核通知给项目负责人"""
        template_vars = {
            'applicant_name': applicant.get_full_name() or applicant.username,
            'leader_name': leader.get_full_name() or leader.username,
            'project_title': project.title,
            'application_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'application_message': application_message or '',
            'project_url': f'/student/projects/{project.id}/'
        }
        
        return self.notification_service.create_and_send_notification(
            recipient=leader,
            notification_type_code='student_project_application',
            sender=applicant,
            related_object=project,
            template_vars=template_vars
        )
    
    def send_application_result_notification(
        self,
        applicant: User,
        project,
        result: str,
        review_message: str = None,
        reviewer: User = None
    ):
        """发送申请审核结果通知给申请人"""
        result_display_map = {
            'approved': '已通过',
            'rejected': '已拒绝',
            'pending': '待审核'
        }
        
        template_vars = {
            'applicant_name': self._get_user_display_name(applicant),
            'project_title': project.title,
            'result': result,
            'result_display': result_display_map.get(result, result),
            'review_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'review_message': review_message or '',
            'project_url': f'/student/projects/{project.id}/'
        }
        
        return self.notification_service.create_and_send_notification(
            recipient=applicant,
            notification_type_code='student_application_result',
            sender=reviewer,
            related_object=project,
            template_vars=template_vars
        )
    

    
    def send_leadership_transfer_notification(
        self,
        new_leader: User,
        project,
        original_leader: User,
        transfer_message: str = None
    ):
        """发送项目负责人转移通知给新负责人"""
        template_vars = {
            'new_leader_name': new_leader.get_full_name() or new_leader.username,
            'project_title': project.title,
            'original_leader': original_leader.get_full_name() or original_leader.username,
            'transfer_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'transfer_message': transfer_message or '',
            'project_url': f'/student/projects/{project.id}/'
        }
        
        return self.notification_service.create_and_send_notification(
            recipient=new_leader,
            notification_type_code='student_leadership_transfer',
            sender=original_leader,
            related_object=project,
            template_vars=template_vars
        )
    
    def send_leadership_change_notification(
        self,
        members: List[User],
        project,
        new_leader: User,
        original_leader: User,
        transfer_message: str = None
    ):
        """发送项目负责人变更通知给除新旧负责人外的所有成员"""
        # 获取新负责人的联系方式
        new_leader_contact = new_leader.email or new_leader.phone or '暂无'
        
        template_vars = {
            'project_title': project.title,
            'new_leader_name': new_leader.get_full_name() or new_leader.username,
            'new_leader_contact': new_leader_contact,
            'original_leader': original_leader.get_full_name() or original_leader.username,
            'transfer_time': timezone.now(),
            'transfer_message': transfer_message or '',
            'project_url': f'/student/projects/{project.id}/'
        }
        
        # 过滤掉新负责人和原负责人
        filtered_members = [member for member in members if member.id not in [new_leader.id, original_leader.id]]
        
        return self.notification_service.bulk_create_and_send_notifications(
            recipients=filtered_members,
            notification_type_code='student_leadership_change_notification',
            sender=original_leader,
            related_object=project,
            template_vars=template_vars
        )
    
    def send_member_kicked_notification(
        self,
        member: User,
        project,
        operator: User = None,
        reason: str = None
    ):
        """发送成员被移出项目通知"""
        template_vars = {
            'member_name': member.get_full_name() or member.username,
            'project_title': project.title,
            'change_time': timezone.now(),
            'operator_name': (operator.get_full_name() or operator.username) if operator else '项目负责人',
            'reason': reason or ''
        }
        
        return self.notification_service.create_and_send_notification(
            recipient=member,
            notification_type_code='student_member_kicked',
            sender=operator,
            related_object=project,
            template_vars=template_vars
        )
    
    def send_project_invitation_notification(
        self,
        invitee: User,
        inviter: User,
        project,
        invitation,
        invitation_message: str = None
    ):
        """发送项目邀请通知给被邀请人"""
        template_vars = {
            'inviter_name': inviter.get_full_name() or inviter.username,
            'invitee_name': invitee.get_full_name() or invitee.username,
            'project_title': project.title,
            'invitation_time': invitation.created_at,
            'invitation_message': invitation_message or '',
            'expires_at': invitation.expires_at
        }
        
        return self.notification_service.create_and_send_notification(
            recipient=invitee,
            notification_type_code='student_project_invitation',
            sender=inviter,
            related_object=invitation,
            expires_at=invitation.expires_at,
            template_vars=template_vars
        )
    
    def send_invitation_expiry_reminder(
        self,
        invitee: User,
        inviter: User,
        project,
        invitation
    ):
        """发送邀请过期提醒通知"""
        template_vars = {
            'invitee_name': invitee.get_full_name() or invitee.username,
            'inviter_name': inviter.get_full_name() or inviter.username,
            'project_title': project.title,
            'expires_at': invitation.expires_at
        }
        
        return self.notification_service.create_and_send_notification(
            recipient=invitee,
            notification_type_code='student_invitation_expiry_reminder',
            sender=None,
            related_object=invitation,
            template_vars=template_vars
        )
    
    def send_invitation_response_notification(
        self,
        inviter: User,
        invitee: User,
        project,
        response: str,
        response_message: str = None
    ):
        """发送邀请回复通知给项目负责人"""
        response_display_map = {
            'accepted': '已接受',
            'rejected': '已拒绝'
        }
        
        template_vars = {
            'inviter_name': inviter.get_full_name() or inviter.username,
            'invitee_name': invitee.get_full_name() or invitee.username,
            'project_title': project.title,
            'response': response,
            'response_display': response_display_map.get(response, response),
            'response_time': timezone.now(),
            'response_message': response_message or '',
            'project_url': f'/student/projects/{project.id}/'
        }
        
        return self.notification_service.create_and_send_notification(
            recipient=inviter,
            notification_type_code='student_invitation_response',
            sender=invitee,
            related_object=project,
            template_vars=template_vars
        )
    
    def send_project_status_change_notification(
        self,
        members: List[User],
        project,
        old_status: str,
        new_status: str,
        operator: User = None,
        members_removed: bool = False
    ):
        """发送项目状态变更通知给所有成员"""
        status_display_map = {
            'active': '进行中',
            'completed': '已完成',
            'suspended': '已暂停',
            'cancelled': '已取消'
        }
        
        template_vars = {
            'project_title': project.title,
            'old_status': old_status,
            'new_status': new_status,
            'old_status_display': status_display_map.get(old_status, old_status),
            'new_status_display': status_display_map.get(new_status, new_status),
            'change_time': timezone.now(),
            'operator_name': self._get_user_display_name(operator) if operator else '系统',
            'members_removed': members_removed,
            'project_url': f'/student/projects/{project.id}/'
        }
        
        return self.notification_service.bulk_create_and_send_notifications(
            recipients=members,
            notification_type_code='student_project_status_changed',
            sender=operator,
            related_object=project,
            template_vars=template_vars
        )
    
    def send_member_left_notification(
        self,
        leader: User,
        member: User,
        project,
        member_role: str = None
    ):
        """发送成员退出通知给项目负责人"""
        role_display_map = {
            'leader': '项目负责人',
            'member': '项目成员',
            'observer': '观察者'
        }
        
        template_vars = {
            'leader_name': leader.get_full_name() or leader.username,
            'member_name': member.get_full_name() or member.username,
            'project_title': project.title,
            'left_time': timezone.now(),
            'member_role_display': role_display_map.get(member_role, member_role) if member_role else '成员',
            'project_url': f'/student/projects/{project.id}/'
        }
        
        return self.notification_service.create_and_send_notification(
            recipient=leader,
            notification_type_code='student_member_left',
            sender=member,
            related_object=project,
            template_vars=template_vars
        )
    
    def send_project_commented_notification(
        self,
        members: List[User],
        project,
        commenter: User,
        comment_content: str,
        comment_obj=None
    ):
        """发送项目被评价通知给所有成员"""
        template_vars = {
            'project_title': project.title,
            'commenter_name': commenter.get_full_name() or commenter.username,
            'comment_time': timezone.now(),
            'comment_content': comment_content,
            'comment_url': f'/student/projects/{project.id}/comments/'
        }
        
        return self.notification_service.bulk_create_and_send_notifications(
            recipients=members,
            notification_type_code='student_project_commented',
            sender=commenter,
            related_object=comment_obj or project,
            template_vars=template_vars
        )
    
    def send_project_score_published_notification(
        self,
        members: List[User],
        project,
        total_score: float,
        weighted_score: float = None,
        evaluator: User = None
    ):
        """发送项目评分公示通知给所有成员"""
        template_vars = {
            'project_title': project.title,
            'total_score': total_score,
            'weighted_score': weighted_score or total_score,
            'evaluator_name': self._get_user_display_name(evaluator) if evaluator else '系统',
            'publish_time': timezone.now(),
            'score_url': f'/student/projects/{project.id}/scores/'
        }
        
        return self.notification_service.bulk_create_and_send_notifications(
            recipients=members,
            notification_type_code='student_project_score_published',
            sender=evaluator,
            related_object=project,
            template_vars=template_vars
        )


# 创建全局通知服务实例
notification_service = NotificationService()
student_notification_service = StudentNotificationService()


# 企业端组织用户通知功能实现
class OrganizationNotificationService:
    """企业端组织用户通知服务"""
    
    def __init__(self):
        self.notification_service = notification_service
    
    def send_user_registration_audit_notification(
        self,
        organization_admin: User,
        applicant: User,
        organization_name: str
    ):
        """发送新用户注册组织身份审核通知"""
        return self.notification_service.create_and_send_notification(
            recipient=organization_admin,
            notification_type_code='org_user_registration_audit',
            sender=applicant,
            template_vars={
                'applicant_name': applicant.real_name or applicant.username,
                'organization_name': organization_name,
                'applicant_email': applicant.email
            }
        )
    
    def send_user_registration_review_result(
        self,
        user: User,
        organization,
        approved: bool,
        reviewer: User
    ):
        """发送用户注册审核结果通知"""
        notification_type = 'org_user_registration_approved' if approved else 'org_user_registration_rejected'
        return self.notification_service.create_and_send_notification(
            recipient=user,
            notification_type_code=notification_type,
            sender=reviewer,
            template_vars={
                'user_name': user.real_name or user.username,
                'organization_name': organization.name,
                'reviewer_name': reviewer.real_name or reviewer.username,
                'review_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
    
    def send_admin_permission_granted(
        self,
        user: User,
        organization,
        granter: User
    ):
        """发送管理员权限授予通知"""
        return self.notification_service.create_and_send_notification(
            recipient=user,
            notification_type_code='org_admin_permission_granted',
            sender=granter,
            template_vars={
                'user_name': user.real_name or user.username,
                'organization_name': organization.name,
                'granter_name': granter.real_name or granter.username,
                'grant_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
    
    def send_organization_permission_change_notification(
        self,
        target_user: User,
        operator: User,
        organization_name: str,
        old_permission: str,
        new_permission: str
    ):
        """发送组织用户权限变更通知（适用于所有权限变更，不仅限于管理员）"""
        # 权限显示名称映射
        permission_display_map = {
            'admin': '管理员',
            'member': '普通成员',
            'viewer': '查看者',
            'editor': '编辑者',
            'pending': '待审核',
            'owner': '组织拥有者'
        }
        
        return self.notification_service.create_and_send_notification(
            recipient=target_user,
            notification_type_code='org_user_permission_change',
            sender=operator,
            template_vars={
                'user_name': target_user.real_name or target_user.username,
                'operator_name': operator.real_name or operator.username,
                'organization_name': organization_name,
                'old_permission': old_permission,
                'new_permission': new_permission,
                'old_permission_display': permission_display_map.get(old_permission, old_permission),
                'new_permission_display': permission_display_map.get(new_permission, new_permission),
                'change_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
    
    def send_organization_status_change_notification(
        self,
        target_user: User,
        operator: User,
        organization_name: str,
        old_status: str,
        new_status: str
    ):
        """发送组织用户状态变更通知"""
        # 状态显示名称映射
        status_display_map = {
            'pending': '待审核',
            'approved': '已通过',
            'rejected': '已拒绝',
            'suspended': '已暂停'
        }
        
        return self.notification_service.create_and_send_notification(
            recipient=target_user,
            notification_type_code='org_user_status_change',
            sender=operator,
            template_vars={
                'user_name': target_user.real_name or target_user.username,
                'operator_name': operator.real_name or operator.username,
                'organization_name': organization_name,
                'old_status': old_status,
                'new_status': new_status,
                'old_status_display': status_display_map.get(old_status, old_status),
                'new_status_display': status_display_map.get(new_status, new_status),
                'change_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
    
    def send_organization_permission_and_status_change_notification(
        self,
        target_user: User,
        operator: User,
        organization_name: str,
        old_permission: str,
        new_permission: str,
        old_status: str,
        new_status: str
    ):
        """发送组织用户权限和状态同时变更通知"""
        # 权限和状态显示名称映射
        permission_display_map = {
            'admin': '管理员',
            'member': '普通成员',
            'viewer': '查看者',
            'editor': '编辑者',
            'pending': '待审核',
            'owner': '组织拥有者'
        }
        
        status_display_map = {
            'pending': '待审核',
            'approved': '已通过',
            'rejected': '已拒绝',
            'suspended': '已暂停'
        }
        
        return self.notification_service.create_and_send_notification(
            recipient=target_user,
            notification_type_code='org_user_permission_and_status_change',
            sender=operator,
            template_vars={
                'user_name': target_user.real_name or target_user.username,
                'operator_name': operator.real_name or operator.username,
                'organization_name': organization_name,
                'old_permission': old_permission,
                'new_permission': permission_display_map.get(new_permission, new_permission),
                'old_status': old_status,
                'new_status': status_display_map.get(new_status, new_status),
                'old_permission_display': permission_display_map.get(old_permission, old_permission),
                'new_permission_display': permission_display_map.get(new_permission, new_permission),
                'old_status_display': status_display_map.get(old_status, old_status),
                'new_status_display': status_display_map.get(new_status, new_status),
                'change_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
    
    # 保持向后兼容性的别名方法
    def send_admin_permission_change_notification(
        self,
        target_user: User,
        operator: User,
        organization_name: str,
        old_permission: str,
        new_permission: str
    ):
        """发送组织管理员权限变更通知（已废弃，请使用send_organization_permission_change_notification）"""
        return self.send_organization_permission_change_notification(
            target_user, operator, organization_name, old_permission, new_permission
        )
    
    def send_project_requirement_notification(
        self,
        requirement_creator: User,
        student: User,
        project_title: str,
        requirement_title: str,
        project_obj=None,
        project_status: str = None
    ):
        """发送学生创建项目对接需求通知（仅在项目状态为recruiting或in_progress时触发）"""
        # 检查项目状态，只有recruiting或in_progress状态的项目才发送通知
        valid_statuses = ['recruiting', 'in_progress']
        
        if project_status and project_status not in valid_statuses:
            logger.info(f"项目 {project_title} 状态为 {project_status}，不发送对接需求通知")
            return None
        
        # 如果有项目对象，从对象中获取状态进行二次确认
        if project_obj and hasattr(project_obj, 'status') and project_obj.status not in valid_statuses:
            logger.info(f"项目 {project_title} 状态为 {project_obj.status}，不发送对接需求通知")
            return None
            
        return self.notification_service.create_and_send_notification(
            recipient=requirement_creator,
            notification_type_code='org_project_requirement_created',
            sender=student,
            related_object=project_obj,
            template_vars={
                'student_name': student.real_name or student.username,
                'project_title': project_title,
                'requirement_title': requirement_title
            }
        )
    
    def send_deliverable_submission_notification(
        self,
        requirement_creator: User,
        student: User,
        project_title: str,
        deliverable_title: str,
        deliverable_obj=None
    ):
        """发送项目成果提交通知"""
        return self.notification_service.create_and_send_notification(
            recipient=requirement_creator,
            notification_type_code='org_deliverable_submitted',
            sender=student,
            related_object=deliverable_obj,
            template_vars={
                'student_name': student.real_name or student.username,
                'project_title': project_title,
                'deliverable_title': deliverable_title
            }
        )
    
    def send_deliverable_update_notification(
        self,
        requirement_creator: User,
        student: User,
        project_title: str,
        deliverable_title: str,
        deliverable_obj=None
    ):
        """发送项目成果更新通知"""
        from django.utils import timezone
        
        return self.notification_service.create_and_send_notification(
            recipient=requirement_creator,
            notification_type_code='org_deliverable_updated',
            sender=student,
            related_object=deliverable_obj,
            template_vars={
                'student_name': student.real_name or student.username,
                'project_title': project_title,
                'deliverable_title': deliverable_title,
                'update_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'deliverable_description': getattr(deliverable_obj, 'description', '暂无描述'),
                'file_count': getattr(deliverable_obj, 'files', []) and len(deliverable_obj.files.all()) or 0,
                'deliverable_url': f'/project/deliverable/{deliverable_obj.id}/' if deliverable_obj else '#'
            }
        )
    
    def send_project_completion_notification(
        self,
        requirement_creator: User,
        project_title: str,
        project_obj=None
    ):
        """发送项目完成通知"""
        return self.notification_service.create_and_send_notification(
            recipient=requirement_creator,
            notification_type_code='org_project_completed',
            related_object=project_obj,
            template_vars={
                'project_title': project_title,
                'requirement_creator_name': requirement_creator.get_full_name() or requirement_creator.username
            }
        )
    
    def send_project_status_change_notification(
        self,
        requirement_creator: User,
        project_title: str,
        old_status: str,
        new_status: str,
        project_obj=None,
        operator: User = None
    ):
        """发送项目状态变更通知（仅在状态变更为已暂停或已取消时触发）"""
        # 定义需要发送通知的状态变更（排除completed，因为有专门的完成通知）
        notification_statuses = ['suspended', 'cancelled', '已暂停', '已取消']
        
        # 检查新状态是否在需要通知的状态列表中
        if new_status not in notification_statuses:
            logger.info(f"项目 {project_title} 状态变更为 {new_status}，不在通知范围内，跳过发送通知")
            return None
        
        # 状态显示名称映射
        status_display_map = {
            'active': '进行中',
            'completed': '已完成',
            'suspended': '已暂停',
            'cancelled': '已取消',
            'draft': '草稿',
            'recruiting': '招募中',
            'in_progress': '进行中'
        }
            
        return self.notification_service.create_and_send_notification(
            recipient=requirement_creator,
            notification_type_code='org_project_status_changed',
            sender=operator,
            related_object=project_obj,
            template_vars={
                'project_title': project_title,
                'old_status': old_status,
                'new_status': new_status,
                'old_status_display': status_display_map.get(old_status, old_status),
                'new_status_display': status_display_map.get(new_status, new_status),
                'change_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'operator_name': (operator.real_name or operator.username) if operator else '系统',
                'student_name': (operator.real_name or operator.username) if operator else '系统',
                'project_url': f'/student/projects/{project_obj.id}/' if project_obj else ''
            }
        )
    
    def send_requirement_deadline_reminder(
        self,
        requirement_creator: User,
        requirement_title: str,
        deadline: timezone.datetime,
        requirement_status: str,
        completed_project_count: int,
        pending_score_count: int,
        requirement_obj=None
    ):
        """发送需求截止评分提醒通知（提醒需求创建者：需求已截止，可以为已完成项目评分）"""
        return self.notification_service.create_and_send_notification(
            recipient=requirement_creator,
            notification_type_code='org_requirement_deadline_reminder',
            related_object=requirement_obj,
            template_vars={
                'requirement_title': requirement_title,
                'deadline': deadline.strftime('%Y-%m-%d %H:%M'),
                'requirement_status': requirement_status,
                'completed_project_count': completed_project_count,
                'pending_score_count': pending_score_count
            }
        )
    

    
    def send_project_comment_reply_notification(
        self,
        original_commenter: User,
        replier: User,
        project_title: str,
        reply_content: str,
        original_comment_content: str,
        comment_obj=None
    ):
        """发送项目评语回复通知"""
        return self.notification_service.create_and_send_notification(
            recipient=original_commenter,
            notification_type_code='org_project_comment_reply',
            sender=replier,
            related_object=comment_obj,
            template_vars={
                'project_title': project_title,
                'replier_name': self._get_user_display_name(replier),
                'reply_time': timezone.now().strftime('%Y-%m-%d %H:%M'),
                'reply_content': reply_content,
                'original_comment_content': original_comment_content[:100] + '...' if len(original_comment_content) > 100 else original_comment_content,
                'comment_url': f'/projects/{comment_obj.project.id}/comments' if comment_obj and hasattr(comment_obj, 'project') else '#'
            }
        )
    
    def send_deliverable_comment_reply_notification(
        self,
        original_commenter: User,
        replier: User,
        project_title: str,
        deliverable_title: str,
        reply_content: str,
        original_comment_content: str,
        comment_obj=None
    ):
        """发送成果评语回复通知"""
        return self.notification_service.create_and_send_notification(
            recipient=original_commenter,
            notification_type_code='org_deliverable_comment_reply',
            sender=replier,
            related_object=comment_obj,
            template_vars={
                'project_title': project_title,
                'deliverable_title': deliverable_title,
                'replier_name': self._get_user_display_name(replier),
                'reply_time': timezone.now().strftime('%Y-%m-%d %H:%M'),
                'reply_content': reply_content,
                'original_comment_content': original_comment_content[:100] + '...' if len(original_comment_content) > 100 else original_comment_content,
                'comment_url': f'/projects/{comment_obj.deliverable.project.id}/deliverables/{comment_obj.deliverable.id}/comments' if comment_obj and hasattr(comment_obj, 'deliverable') else '#'
            }
        )
    

    
    def send_org_project_comment_notification(
        self,
        project_members: List[User],
        commenter: User,
        project_title: str,
        comment_content: str,
        project_obj=None,
        comment_obj=None
    ):
        """发送组织用户发布项目级评语通知给所有项目参与者"""
        template_vars = {
            'commenter_name': self._get_user_display_name(commenter),
            'project_title': project_title,
            'comment_content': comment_content,
            'comment_time': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'comment_url': f'/projects/{project_obj.id}/comments/' if project_obj else '#'
        }
        
        return self.notification_service.bulk_create_and_send_notifications(
            recipients=project_members,
            notification_type_code='student_project_comment',
            sender=commenter,
            template_vars=template_vars,
            related_object=comment_obj or project_obj
        )
    
    def send_org_deliverable_comment_notification(
        self,
        project_members: List[User],
        commenter: User,
        project_title: str,
        deliverable_title: str,
        comment_content: str,
        project_obj=None,
        deliverable_obj=None,
        comment_obj=None
    ):
        """发送组织用户发布成果级评语通知给所有项目参与者"""
        template_vars = {
            'commenter_name': self._get_user_display_name(commenter),
            'project_title': project_title,
            'deliverable_title': deliverable_title,
            'comment_content': comment_content,
            'comment_time': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'comment_url': f'/projects/{project_obj.id}/deliverables/{deliverable_obj.id}/comments/' if project_obj and deliverable_obj else '#'
        }
        
        return self.notification_service.bulk_create_and_send_notifications(
            recipients=project_members,
            notification_type_code='student_deliverable_comment',
            sender=commenter,
            template_vars=template_vars,
            related_object=comment_obj or deliverable_obj
        )
    
    def send_student_deliverable_comment_notification(
        self,
        project_members: List[User],
        commenter: User,
        project_title: str,
        deliverable_title: str,
        comment_content: str,
        project_obj=None,
        deliverable_obj=None,
        comment_obj=None
    ):
        """发送学生成果评语通知（别名方法，调用send_org_deliverable_comment_notification）"""
        return self.send_org_deliverable_comment_notification(
            project_members=project_members,
            commenter=commenter,
            project_title=project_title,
            deliverable_title=deliverable_title,
            comment_content=comment_content,
            project_obj=project_obj,
            deliverable_obj=deliverable_obj,
            comment_obj=comment_obj
        )
    
    def send_student_project_comment_notification(
        self,
        project_members: List[User],
        commenter: User,
        project_title: str,
        comment_content: str,
        project_obj=None,
        comment_obj=None
    ):
        """发送学生项目评语通知（别名方法，调用send_org_project_comment_notification）"""
        return self.send_org_project_comment_notification(
            project_members=project_members,
            commenter=commenter,
            project_title=project_title,
            comment_content=comment_content,
            project_obj=project_obj,
            comment_obj=comment_obj
        )
    
    def send_organization_verification_success_notification(
        self,
        organization_creator: User,
        organization,
        operator: User = None
    ):
        """
        发送组织认证通过通知
        """
        template_vars = {
            'organization_name': organization.name,
            'creator_name': self._get_user_display_name(organization_creator),
            'operator_name': self._get_user_display_name(operator) if operator else '系统管理员',
            'verification_time': timezone.now().astimezone(pytz.timezone('Asia/Shanghai')).strftime('%Y年%m月%d日 %H:%M')
        }
        
        self.notification_service.create_and_send_notification(
            recipient=organization_creator,
            notification_type_code='organization_verification_success',
            sender=operator,
            related_object=organization,
            template_vars=template_vars,
            strategies=['websocket', 'email']
        )
    
    def send_organization_verification_rejected_notification(
        self,
        organization_creator: User,
        organization,
        operator: User = None,
        verification_comment: str = None
    ):
        """
        发送组织认证被拒绝通知
        """
        template_vars = {
            'organization_name': organization.name,
            'creator_name': self._get_user_display_name(organization_creator),
            'operator_name': self._get_user_display_name(operator) if operator else '系统管理员',
            'verification_time': timezone.now().astimezone(pytz.timezone('Asia/Shanghai')).strftime('%Y年%m月%d日 %H:%M'),
            'verification_comment': verification_comment or '未提供具体原因'
        }
        
        self.notification_service.create_and_send_notification(
            recipient=organization_creator,
            notification_type_code='organization_verification_rejected',
            sender=operator,
            related_object=organization,
            template_vars=template_vars,
            strategies=['websocket', 'email']
        )

    def _get_user_display_name(self, user_obj):
        """获取用户显示名称，兼容User和OrganizationUser对象"""
        if hasattr(user_obj, 'get_full_name'):
            # User对象
            return user_obj.get_full_name() or user_obj.username
        elif hasattr(user_obj, 'user'):
            # OrganizationUser对象
            return user_obj.user.get_full_name() or user_obj.user.username
        else:
            return str(user_obj)


# 创建企业端通知服务实例
org_notification_service = OrganizationNotificationService()