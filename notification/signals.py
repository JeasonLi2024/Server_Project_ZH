from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

# 导入相关模型
try:
    from user.models import OrganizationUser
except ImportError:
    OrganizationUser = None
    logger.warning("OrganizationUser模型未找到，组织相关通知功能将不可用")

try:
    from studentproject.models import StudentProject, ProjectDeliverable, ProjectComment
except ImportError:
    StudentProject = None
    ProjectDeliverable = None
    ProjectComment = None

from .services import org_notification_service, student_notification_service

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def handle_user_registration(sender, instance, created, **kwargs):
    """处理用户注册信号"""
    if created:
        logger.info(f"新用户注册: {instance.username}")
        # 这里可以添加欢迎通知等逻辑
        # TODO: 发送欢迎通知


# if OrganizationUser:
#     @receiver(post_save, sender=OrganizationUser)
#     def handle_organization_member_change(sender, instance, created, **kwargs):
#         """处理组织成员变更信号"""
#         # 这个逻辑已经移到user/signals.py中实现


if StudentProject:
    @receiver(post_save, sender=StudentProject)
    def handle_project_change(sender, instance, created, **kwargs):
        """处理项目变更信号"""
        if created:
            # 新项目创建
            leader = instance.get_leader()
            leader_name = leader.user.username if leader else "未知用户"
            logger.info(f"新项目创建: {instance.title} by {leader_name}")
            
            # 如果项目有对接需求且状态为recruiting或in_progress，通知需求创建者
            if hasattr(instance, 'requirement') and instance.requirement:
                if instance.status in ['recruiting', 'in_progress']:
                    # 检查项目是否有负责人
                    project_leader = instance.get_leader()
                    if project_leader:
                        try:
                            org_notification_service.send_project_requirement_notification(
                                    requirement_creator=instance.requirement.publish_people.user,
                                    student=project_leader,
                                    project_title=instance.title,
                                    requirement_title=instance.requirement.title,
                                    project_obj=instance
                                )
                        except Exception as e:
                            logger.error(f"发送项目需求通知失败: {str(e)}")
                    else:
                        logger.warning(f"项目 {instance.title} 没有负责人，跳过需求通知发送")
        
        else:
            # 项目状态更新
            if hasattr(instance, '_old_status') and instance._old_status != instance.status:
                logger.info(f"项目状态变更: {instance.title} {instance._old_status} -> {instance.status}")
                
                # 如果项目有对接需求
                if hasattr(instance, 'requirement') and instance.requirement:
                    try:
                        # 如果项目状态从draft变为recruiting或in_progress，发送项目需求创建通知
                        if (instance._old_status == 'draft' and 
                            instance.status in ['recruiting', 'in_progress']):
                            project_leader = instance.get_leader()
                            if project_leader:
                                org_notification_service.send_project_requirement_notification(
                                requirement_creator=instance.requirement.publish_people.user,
                                student=project_leader,
                                project_title=instance.title,
                                requirement_title=instance.requirement.title,
                                project_obj=instance
                            )
                            else:
                                logger.warning(f"项目 {instance.title} 没有负责人，跳过状态变更通知发送")
                        
                        # 项目状态变更通知已在views.py中处理，避免重复发送
                        # org_notification_service.send_project_status_change_notification(
                        #     requirement_creator=instance.requirement.creator,
                        #     project_title=instance.title,
                        #     old_status=instance._old_status,
                        #     new_status=instance.status,
                        #     project_obj=instance
                        # )
                    except Exception as e:
                        logger.error(f"发送项目状态变更通知失败: {str(e)}")


if ProjectDeliverable:
    @receiver(post_save, sender=ProjectDeliverable)
    def handle_deliverable_submission(sender, instance, created, **kwargs):
        """处理项目成果提交和更新信号"""
        if created:
            # 新成果提交
            logger.info(f"新成果提交: {instance.title} by {instance.project.get_leader().user.username}")
            
            # 通知需求创建者
            if hasattr(instance.project, 'requirement') and instance.project.requirement:
                try:
                    org_notification_service.send_deliverable_submission_notification(
                        requirement_creator=instance.project.requirement.publish_people.user,
                        student=instance.submitter.user,
                        project_title=instance.project.title,
                        deliverable_title=instance.title,
                        deliverable_obj=instance
                    )
                except Exception as e:
                    logger.error(f"发送成果提交通知失败: {str(e)}")
        else:
            # 成果更新
            # 检查是否有实质性更新（排除弃用操作和文件操作导致的批量更新）
            if not getattr(instance, 'is_deprecated', False):
                # 检查是否是由文件操作导致的批量更新
                # 如果只是更新了last_modifier、is_updated、updated_at字段，则认为是文件操作
                # 这种情况下不发送更新通知，避免重复通知
                
                # 获取模型的脏字段（已更改的字段）
                dirty_fields = getattr(instance, '_dirty_fields', set())
                
                # 如果只更新了这些字段，说明是文件操作导致的批量更新
                file_operation_fields = {'last_modifier', 'is_updated', 'updated_at'}
                
                # 如果脏字段只包含文件操作相关字段，则跳过通知
                if dirty_fields and dirty_fields.issubset(file_operation_fields):
                    logger.info(f"成果文件操作更新: {instance.title} - 跳过通知")
                    return
                
                # 安全获取修改者信息
                modifier = getattr(instance, 'last_modifier', None)
                if not modifier:
                    modifier = instance.project.get_leader()
                
                modifier_username = modifier.user.username if modifier and hasattr(modifier, 'user') else 'Unknown'
                logger.info(f"成果更新: {instance.title} by {modifier_username}")
                
                # 通知需求创建者
                if hasattr(instance.project, 'requirement') and instance.project.requirement:
                    try:
                        # 安全获取学生用户信息
                        student_user = None
                        if modifier and hasattr(modifier, 'user'):
                            student_user = modifier.user
                        
                        if student_user:
                            org_notification_service.send_deliverable_update_notification(
                                requirement_creator=instance.project.requirement.publish_people.user,
                                student=student_user,
                                project_title=instance.project.title,
                                deliverable_title=instance.title,
                                deliverable_obj=instance
                            )
                        else:
                            logger.warning(f"无法获取成果 {instance.title} 的提交者信息，跳过通知")
                    except Exception as e:
                        logger.error(f"发送成果更新通知失败: {str(e)}")


if ProjectComment:
    @receiver(post_save, sender=ProjectComment)
    def handle_comment_creation_and_reply(sender, instance, created, **kwargs):
        """处理评论创建和回复信号"""
        if not created:
            return
            
        try:
            # 获取项目信息
            project = None
            project_title = ''
            deliverable = None
            deliverable_title = ''
            
            # 先检查是否为成果级评语
            if hasattr(instance, 'deliverable') and instance.deliverable:
                deliverable = instance.deliverable
                project = deliverable.project
                project_title = project.title
                deliverable_title = deliverable.title
            elif hasattr(instance, 'project') and instance.project:
                project = instance.project
                project_title = project.title
            
            if not project:
                logger.warning(f"评论 {instance.id} 没有关联的项目")
                return
                
            # 检查评论作者是否为组织用户
            is_org_user = False
            if OrganizationUser:
                try:
                    org_user = OrganizationUser.objects.get(user=instance.author)
                    is_org_user = True
                except OrganizationUser.DoesNotExist:
                    is_org_user = False
            
            if instance.parent_comment:
                # 这是回复评论
                logger.info(f"新评论回复: {instance.author.username} 回复了 {instance.parent_comment.author.username}")
                
                # 通知原评论作者
                if instance.parent_comment.author != instance.author:
                    if deliverable:
                        # 成果级评语回复
                        org_notification_service.send_deliverable_comment_reply_notification(
                            original_commenter=instance.parent_comment.author,
                            replier=instance.author,
                            project_title=project_title,
                            deliverable_title=deliverable_title,
                            reply_content=instance.content,
                            original_comment_content=instance.parent_comment.content,
                            comment_obj=instance
                        )
                    else:
                        # 项目级评语回复
                        org_notification_service.send_project_comment_reply_notification(
                            original_commenter=instance.parent_comment.author,
                            replier=instance.author,
                            project_title=project_title,
                            reply_content=instance.content,
                            original_comment_content=instance.parent_comment.content,
                            comment_obj=instance
                        )
            elif is_org_user:
                # 这是组织用户发布的新评语（非回复）
                logger.info(f"组织用户发布评语: {instance.author.username} 在项目 {project_title}")
                
                # 获取项目所有参与者（包括负责人和成员）
                project_members = []
                if hasattr(project, 'get_active_participants'):
                    # 使用get_active_participants方法获取所有活跃参与者
                    active_participants = project.get_active_participants()
                    project_members = [participant.student.user for participant in active_participants]
                else:
                    # 备用方案：通过ProjectParticipant模型直接查询
                    try:
                        from studentproject.models import ProjectParticipant
                        participants = ProjectParticipant.objects.filter(
                            project=project,
                            status='approved'
                        ).select_related('student__user')
                        project_members = [participant.student.user for participant in participants]
                    except Exception as e:
                        logger.error(f"获取项目参与者失败: {str(e)}")
                        # 最后备用方案：获取项目负责人
                        if hasattr(project, 'get_leader'):
                            leader = project.get_leader()
                            if leader and hasattr(leader, 'user'):
                                project_members = [leader.user]
                
                # 排除评语发布者本人
                project_members = [member for member in project_members if member != instance.author]
                
                if project_members:
                    if deliverable:
                        # 成果级评语
                        org_notification_service.send_student_deliverable_comment_notification(
                            project_members=project_members,
                            commenter=instance.author,
                            project_title=project_title,
                            deliverable_title=deliverable_title,
                            comment_content=instance.content,
                            project_obj=project,
                            deliverable_obj=deliverable,
                            comment_obj=instance
                        )
                    else:
                        # 项目级评语
                        org_notification_service.send_student_project_comment_notification(
                            project_members=project_members,
                            commenter=instance.author,
                            project_title=project_title,
                            comment_content=instance.content,
                            project_obj=project,
                            comment_obj=instance
                        )
                        
        except Exception as e:
            logger.error(f"处理评论通知失败: {str(e)}")


# 为模型添加变更追踪
def add_change_tracking():
    """为模型添加变更追踪"""
    
    if OrganizationUser:
        def save_with_tracking(self, *args, **kwargs):
            """保存时追踪变更"""
            if self.pk:
                old_instance = OrganizationUser.objects.get(pk=self.pk)
                self._old_permission = old_instance.permission
                self._old_status = old_instance.status
            super(OrganizationUser, self).save(*args, **kwargs)
        
        OrganizationUser.save = save_with_tracking
    
    if StudentProject:
        def save_with_tracking(self, *args, **kwargs):
            """保存时追踪变更"""
            if self.pk:
                old_instance = StudentProject.objects.get(pk=self.pk)
                self._old_status = old_instance.status
            super(StudentProject, self).save(*args, **kwargs)
        
        StudentProject.save = save_with_tracking
    
    if ProjectDeliverable:
        def save_with_tracking(self, *args, **kwargs):
            """保存时追踪变更"""
            if self.pk:
                try:
                    old_instance = ProjectDeliverable.objects.get(pk=self.pk)
                    # 记录所有可能变更的字段
                    dirty_fields = set()
                    
                    # 检查各个字段是否有变更
                    if old_instance.title != self.title:
                        dirty_fields.add('title')
                    if old_instance.description != self.description:
                        dirty_fields.add('description')
                    if old_instance.stage_type != self.stage_type:
                        dirty_fields.add('stage_type')
                    if old_instance.last_modifier != self.last_modifier:
                        dirty_fields.add('last_modifier')
                    if old_instance.is_updated != self.is_updated:
                        dirty_fields.add('is_updated')
                    if old_instance.is_deprecated != self.is_deprecated:
                        dirty_fields.add('is_deprecated')
                    # updated_at字段总是会变更，所以单独处理
                    if abs((old_instance.updated_at - self.updated_at).total_seconds()) > 1:
                        dirty_fields.add('updated_at')
                    
                    self._dirty_fields = dirty_fields
                except ProjectDeliverable.DoesNotExist:
                    # 如果旧实例不存在，说明是新创建的
                    self._dirty_fields = set()
            else:
                # 新实例
                self._dirty_fields = set()
            
            super(ProjectDeliverable, self).save(*args, **kwargs)
        
        ProjectDeliverable.save = save_with_tracking


# 在应用启动时添加变更追踪
add_change_tracking()