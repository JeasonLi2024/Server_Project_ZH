import logging
import pytz
from rest_framework import generics, status, permissions
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Case, When, IntegerField
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    StudentProject,
    ProjectParticipant,
    ProjectDeliverable,
    ProjectComment,
    ProjectInvitation
)
from notification.services import notification_service, student_notification_service, org_notification_service
from .serializers import (
    StudentProjectCreateSerializer,
    StudentProjectUpdateSerializer,
    StudentProjectDetailSerializer,
    StudentProjectListSerializer,
    ProjectApplicationSerializer,
    ApplicationReviewSerializer,
    BatchApplicationReviewSerializer,
    UnifiedApplicationReviewSerializer,
    ParticipantListSerializer,
    ParticipantDetailSerializer,
    ParticipantStatusUpdateSerializer,
    LeadershipTransferSerializer,
    ProjectInvitationSerializer,
    SendInvitationSerializer,
    InvitationResponseSerializer,
    ProjectDeliverableSubmitSerializer,
    ProjectDeliverableUpdateSerializer,
    ProjectDeliverableListSerializer,
    ProjectDeliverableDetailSerializer
)
from user.models import Student, OrganizationUser, Tag2
from user.services import UserHistoryService
from project.models import File, Requirement, Resource
from common_utils import APIResponse, format_validation_errors
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

logger = logging.getLogger(__name__)

User = get_user_model()


class IsStudentUser(permissions.BasePermission):
    """检查用户是否为学生用户"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.user_type == 'student' and
            hasattr(request.user, 'student_profile')
        )


class IsProjectLeader(permissions.BasePermission):
    """检查用户是否为项目leader"""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if request.user.user_type != 'student':
            return False
            
        if not hasattr(request.user, 'student_profile'):
            return False
            
        # 检查是否为项目的leader
        try:
            participant = ProjectParticipant.objects.get(
                project=obj,
                student=request.user.student_profile,
                role='leader',
                status='approved'
            )
            return True
        except ProjectParticipant.DoesNotExist:
            return False


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudentUser])
def create_project(request):
    """
    创建新项目接口
    
    权限：所有学生用户
    功能：创建项目时，创建学生自动成为该项目的leader
    """
    serializer = StudentProjectCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                # 创建项目
                project = serializer.save()
                
                # 创建者自动成为leader
                ProjectParticipant.objects.create(
                    project=project,
                    student=request.user.student_profile,
                    role='leader',
                    status='approved',
                    application_message='项目创建者自动成为leader'
                )
                
                # 发送项目创建通知（情形3：学生创建项目对接需求时通知需求创建者）
                if project.requirement:
                    try:
                        from notification.services import org_notification_service
                        org_notification_service.send_project_requirement_notification(
                            requirement_creator=project.requirement.publish_people.user,
                            student=request.user,
                            project_title=project.title,
                            requirement_title=project.requirement.title,
                            project_obj=project,
                            project_status=project.status
                        )
                    except Exception as e:
                        logger.error(f"发送项目创建通知失败: {str(e)}")
                
                # 返回详细信息
                detail_serializer = StudentProjectDetailSerializer(project)
                return APIResponse.success(
                    data=detail_serializer.data,
                    message='项目创建成功',
                    code=201
                )
                
        except Exception as e:
            return APIResponse.server_error(
                message=f'项目创建失败: {str(e)}'
            )
    
    return APIResponse.validation_error(
        errors=format_validation_errors(serializer.errors),
        message='数据验证失败'
    )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsStudentUser])
def update_project(request, project_id):
    """
    修改项目接口
    
    权限：仅项目leader
    """
    project = get_object_or_404(StudentProject, id=project_id)
    
    # 检查权限
    permission = IsProjectLeader()
    if not permission.has_object_permission(request, None, project):
        return APIResponse.forbidden(
            message='权限不足，只有项目leader可以修改项目'
        )
    
    # 部分更新或完整更新
    partial = request.method == 'PATCH'
    serializer = StudentProjectUpdateSerializer(
        project, 
        data=request.data, 
        partial=partial
    )
    
    if serializer.is_valid():
        try:
            # 保存更新前的状态
            old_status = project.status
            updated_project = serializer.save()
            
            # 检查状态是否发生变更
            if old_status != updated_project.status:
                # 发送项目状态变更通知给项目参与者（不包括leader）
                try:
                    # 获取项目leader
                    project_leader = updated_project.get_leader()
                    # 获取项目参与者（排除leader）
                    project_members = [
                        participant.student.user for participant in updated_project.project_participants.filter(status='approved') 
                        if project_leader is None or participant.student != project_leader
                    ]
                    if project_members:
                        student_notification_service.send_project_status_change_notification(
                            members=project_members,
                            project=updated_project,
                            old_status=old_status,
                            new_status=updated_project.status,
                            operator=request.user
                        )
                except Exception as e:
                    logger.error(f"发送项目状态变更通知失败: {str(e)}")
                
                # 发送组织通知（给需求发布人）
                if updated_project.requirement and updated_project.requirement.publish_people:
                    try:
                        # 情况1：项目状态由draft改为recruiting或in_progress时，调用org_project_requirement_created
                        if (old_status == 'draft' and 
                            updated_project.status in ['recruiting', 'in_progress']):
                            org_notification_service.send_project_requirement_notification(
                                requirement_creator=updated_project.requirement.publish_people.user,
                                student=request.user,
                                project_title=updated_project.title,
                                requirement_title=updated_project.requirement.title,
                                project_obj=updated_project,
                                project_status=updated_project.status
                            )
                        
                        # 情况2：项目状态改为completed时，发送项目完成通知
                        elif updated_project.status == 'completed':
                            org_notification_service.send_project_completion_notification(
                                requirement_creator=updated_project.requirement.publish_people.user,
                                project_title=updated_project.title,
                                project_obj=updated_project
                            )
                        
                        # 情况3：其他普通状态修改，使用send_project_status_change_notification
                        else:
                            org_notification_service.send_project_status_change_notification(
                                requirement_creator=updated_project.requirement.publish_people.user,
                                project_title=updated_project.title,
                                old_status=old_status,
                                new_status=updated_project.status,
                                project_obj=updated_project,
                                operator=request.user
                            )
                    
                    except Exception as e:
                        logger.error(f"发送组织通知失败: {str(e)}")
            
            # 返回详细信息
            detail_serializer = StudentProjectDetailSerializer(updated_project)
            return APIResponse.success(
                data=detail_serializer.data,
                message='项目更新成功'
            )
            
        except Exception as e:
            return APIResponse.server_error(
                message=f'项目更新失败: {str(e)}'
            )
    
    return APIResponse.validation_error(
        errors=format_validation_errors(serializer.errors),
        message='数据验证失败'
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsStudentUser])
def delete_project(request, project_id):
    """
    删除项目接口
    
    权限：仅项目leader
    功能：删除项目时会：
    1. 解除与所有参与者的关系
    2. 删除所有关联的成果（包括完整的成果链）
    3. 删除所有相关联的文件信息
    4. 删除所有项目评论
    5. 删除所有相关通知
    """
    project = get_object_or_404(StudentProject, id=project_id)
    
    # 检查权限
    permission = IsProjectLeader()
    if not permission.has_object_permission(request, None, project):
        return APIResponse.forbidden(
            message='权限不足，只有项目leader可以删除项目'
        )
    
    try:
        with transaction.atomic():
            project_title = project.title
            
            # 1. 获取所有成果及其关联的文件
            deliverables = ProjectDeliverable.objects.filter(project=project)
            file_ids = []
            for deliverable in deliverables:
                file_ids.extend(deliverable.files.values_list('id', flat=True))
            
            # 2. 删除所有项目评论
            ProjectComment.objects.filter(project=project).delete()
            
            # 3. 删除所有相关通知
            from notification.models import Notification
            from django.contrib.contenttypes.models import ContentType
            project_content_type = ContentType.objects.get_for_model(StudentProject)
            Notification.objects.filter(
                content_type=project_content_type,
                object_id=project.id
            ).delete()
            
            # 4. 删除所有成果（会自动删除成果链关系）
            deliverables.delete()
            
            # 5. 删除关联的文件记录（注意：这里只删除File记录，实际文件可能需要额外处理）
            if file_ids:
                File.objects.filter(id__in=file_ids).delete()
            
            # 6. 删除所有参与者关系
            ProjectParticipant.objects.filter(project=project).delete()
            
            # 7. 最后删除项目本身
            project.delete()
            
            return APIResponse.success(
                message=f'项目 "{project_title}" 及其所有相关数据已成功删除'
            )
            
    except Exception as e:
        return APIResponse.server_error(
            message=f'项目删除失败: {str(e)}'
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_organization_overview(request):
    """
    获取组织数据概览
    包括：发布需求及增长率、发布资源及增长率、进行中学生项目及增长率、
    项目完成率及增长率、项目进度统计、项目技能分布
    """
    try:
        # 检查用户是否为组织用户
        try:
            org_user = OrganizationUser.objects.get(user=request.user)
            organization = org_user.organization
        except OrganizationUser.DoesNotExist:
            return APIResponse.forbidden(
                message="您不是组织用户，无权访问此数据"
            )
        
        # 获取当前时间和上个月同期时间
        now = timezone.now()
        current_date = now.date()
        
        # 计算上个月同期时间
        if current_date.month == 1:
            last_month_same_date = current_date.replace(year=current_date.year - 1, month=12)
        else:
            try:
                last_month_same_date = current_date.replace(month=current_date.month - 1)
            except ValueError:
                # 处理月末日期问题（如3月31日 -> 2月28/29日）
                last_month = current_date.month - 1
                if last_month == 2:
                    # 2月最多29天
                    day = min(current_date.day, 29)
                else:
                    # 其他月份最多30天
                    day = min(current_date.day, 30)
                last_month_same_date = current_date.replace(month=last_month, day=day)
        
        # 1. 发布需求及增长率
        current_requirements = Requirement.objects.filter(
            organization=organization,
            created_at__lte=now
        ).count()
        
        # 计算上月同期的时间点
        last_month_datetime = now.replace(
            year=last_month_same_date.year,
            month=last_month_same_date.month,
            day=last_month_same_date.day
        )
        
        last_month_requirements = Requirement.objects.filter(
            organization=organization,
            created_at__lte=last_month_datetime
        ).count()
        
        requirements_growth_rate = 0
        if last_month_requirements > 0:
            requirements_growth_rate = round(
                ((current_requirements - last_month_requirements) / last_month_requirements) * 100, 2
            )
        
        # 2. 发布资源及增长率
        current_resources = Resource.objects.filter(
            create_person__organization=organization,
            created_at__lte=now
        ).count()
        
        last_month_resources = Resource.objects.filter(
            create_person__organization=organization,
            created_at__lte=last_month_datetime
        ).count()
        
        resources_growth_rate = 0
        if last_month_resources > 0:
            resources_growth_rate = round(
                ((current_resources - last_month_resources) / last_month_resources) * 100, 2
            )
        
        # 3. 进行中学生项目及增长率
        current_in_progress_projects = StudentProject.objects.filter(
            requirement__organization=organization,
            status='in_progress',
            created_at__lte=now
        ).count()
        
        last_month_in_progress_projects = StudentProject.objects.filter(
            requirement__organization=organization,
            status='in_progress',
            created_at__lte=last_month_datetime
        ).count()
        
        in_progress_growth_rate = 0
        if last_month_in_progress_projects > 0:
            in_progress_growth_rate = round(
                ((current_in_progress_projects - last_month_in_progress_projects) / last_month_in_progress_projects) * 100, 2
            )
        
        # 4. 项目完成率及增长率
        total_projects = StudentProject.objects.filter(
            requirement__organization=organization,
            created_at__lte=now
        ).count()
        
        completed_projects = StudentProject.objects.filter(
            requirement__organization=organization,
            status='completed',
            created_at__lte=now
        ).count()
        
        current_completion_rate = 0
        if total_projects > 0:
            current_completion_rate = round((completed_projects / total_projects) * 100, 2)
        
        # 上个月同期的完成率
        last_month_total_projects = StudentProject.objects.filter(
            requirement__organization=organization,
            created_at__lte=last_month_datetime
        ).count()
        
        last_month_completed_projects = StudentProject.objects.filter(
            requirement__organization=organization,
            status='completed',
            created_at__lte=last_month_datetime
        ).count()
        
        last_month_completion_rate = 0
        if last_month_total_projects > 0:
            last_month_completion_rate = round((last_month_completed_projects / last_month_total_projects) * 100, 2)
        
        completion_rate_growth = 0
        if last_month_completion_rate > 0:
            completion_rate_growth = round(
                ((current_completion_rate - last_month_completion_rate) / last_month_completion_rate) * 100, 2
            )
        
        # 5. 项目进度统计（按月统计当前年份已过月份的数据）
        current_year = current_date.year
        current_month = current_date.month
        
        monthly_progress = []
        for month in range(1, current_month):  # 只统计已过的月份
            month_start = datetime(current_year, month, 1, tzinfo=pytz.UTC)
            if month == 12:
                month_end = datetime(current_year + 1, 1, 1, tzinfo=pytz.UTC) - timedelta(seconds=1)
            else:
                month_end = datetime(current_year, month + 1, 1, tzinfo=pytz.UTC) - timedelta(seconds=1)
            
            # 统计该月的项目状态
            month_projects = StudentProject.objects.filter(
                requirement__organization=organization,
                created_at__gte=month_start,
                created_at__lte=month_end
            )
            
            completed_count = month_projects.filter(status='completed').count()
            in_progress_count = month_projects.filter(status='in_progress').count()
            recruiting_count = month_projects.filter(status='recruiting').count()
            
            monthly_progress.append({
                'month': f'{month}月',
                'completed': completed_count,
                'in_progress': in_progress_count,
                'recruiting': recruiting_count
            })
        
        # 6. 项目技能分布（需求技能分布，前10个tag2标签及其占比）
        # 获取该组织发布的所有需求关联的tag2
        requirements_with_tags = Requirement.objects.filter(
            organization=organization
        ).prefetch_related('tag2')
        
        tag_counts = {}
        total_tag_count = 0
        
        for requirement in requirements_with_tags:
            for tag in requirement.tag2.all():
                tag_name = tag.post  # 使用tag2的post字段作为标签名
                tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1
                total_tag_count += 1
        
        # 获取前10个标签并计算占比
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        skill_distribution = []
        
        # 计算前10个标签的总数
        top_tags_count = sum(count for _, count in top_tags)
        
        for tag_name, count in top_tags:
            percentage = round((count / total_tag_count) * 100, 2) if total_tag_count > 0 else 0
            skill_distribution.append({
                'skill': tag_name,
                'count': count,
                'percentage': percentage
            })
        
        # 添加"其他"类别，包含剩余的所有标签
        other_count = total_tag_count - top_tags_count
        if other_count > 0:
            other_percentage = round((other_count / total_tag_count) * 100, 2)
            skill_distribution.append({
                'skill': '其他',
                'count': other_count,
                'percentage': other_percentage
            })
        
        # 构建返回数据
        data = {
            'published_requirements': {
                'count': current_requirements,
                'growth_rate': f"{requirements_growth_rate}%"
            },
            'published_resources': {
                'count': current_resources,
                'growth_rate': f"{resources_growth_rate}%"
            },
            'in_progress_projects': {
                'count': current_in_progress_projects,
                'growth_rate': f"{in_progress_growth_rate}%"
            },
            'project_completion_rate': {
                'rate': f"{current_completion_rate}%",
                'growth_rate': f"{completion_rate_growth}%"
            },
            'monthly_progress': monthly_progress,
            'skill_distribution': skill_distribution
        }
        
        return APIResponse.success(
            data=data,
            message="组织数据概览获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取组织数据概览失败: {str(e)}")
        return APIResponse.server_error(
            message="获取组织数据概览失败"
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_project_list(request):
    """
    获取项目列表接口
    
    权限：所有认证用户
    功能：支持分页、筛选和搜索，区分三种场景：
    1. my_projects=true: 我创建/负责的项目（仅学生用户）
    2. my_projects=false: 我加入的项目（仅学生用户）
    3. 不传my_projects参数: 项目广场，显示所有项目
    
    查询参数：
    - page: 页码 (默认: 1)
    - page_size: 每页数量 (默认: 10, 最大: 50)
    - status: 项目状态筛选，支持多状态筛选，用逗号分隔
    - requirement_id: 需求ID筛选
    - leader_id: 负责人ID筛选
    - keyword: 搜索关键词 (项目标题、描述)
    - my_projects: true=我创建/负责的项目, false=我加入的项目（仅学生用户可用）
    - organization_id: 组织ID筛选，筛选该组织关联需求下的所有项目（仅组织用户可用）
    - is_evaluated: 评分状态筛选，true=已评分项目, false=未评分项目（仅对已完成项目有效）
    """
    try:
        
        # 获取查询参数
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 10)), 50)
        status_filter = request.GET.get('status', '')
        requirement_id = request.GET.get('requirement_id')
        leader_id = request.GET.get('leader_id')
        keyword = request.GET.get('keyword', '')
        my_projects = request.GET.get('my_projects')
        organization_id = request.GET.get('organization_id')
        is_evaluated = request.GET.get('is_evaluated')
        
        # 基础查询集
        user = request.user
        
        # 检查用户类型和my_projects参数
        if my_projects in ['true', 'false'] and user.user_type == 'student' and hasattr(user, 'student_profile'):
            student = user.student_profile
            if my_projects == 'true':
                # 我创建/负责的项目
                queryset = StudentProject.objects.filter(
                    project_participants__student=student,
                    project_participants__role='leader',
                    project_participants__status='approved'
                ).distinct()
            else:  # my_projects == 'false'
                # 我加入的项目（排除我负责的项目）
                # 首先获取该学生作为leader的项目ID列表
                leader_project_ids = StudentProject.objects.filter(
                    project_participants__student=student,
                    project_participants__role='leader',
                    project_participants__status='approved'
                ).values_list('id', flat=True)
                
                # 然后获取该学生参与但不是leader的项目
                queryset = StudentProject.objects.filter(
                    project_participants__student=student,
                    project_participants__status='approved'
                ).exclude(
                    id__in=leader_project_ids
                ).distinct()
        else:
            # 默认情况（项目广场）：显示所有公开的项目
            # 对于非学生用户或未指定my_projects参数的情况
            queryset = StudentProject.objects.all()
            
            # 组织用户筛选：如果传入organization_id，只显示该组织关联需求下的项目
            if organization_id and user.user_type == 'organization':
                try:
                    org_id = int(organization_id)
                    # 筛选该组织发布的需求下的所有项目
                    queryset = queryset.filter(requirement__organization_id=org_id)
                except ValueError:
                    pass
        
        # 状态筛选
        if status_filter:
            status_list = [s.strip() for s in status_filter.split(',') if s.strip()]
            if status_list:
                queryset = queryset.filter(status__in=status_list)
        
        # 需求ID筛选
        if requirement_id:
            try:
                req_id = int(requirement_id)
                queryset = queryset.filter(requirement_id=req_id)
            except ValueError:
                pass
        
        # 负责人ID筛选
        if leader_id:
            try:
                l_id = int(leader_id)
                queryset = queryset.filter(
                    project_participants__student_id=l_id,
                    project_participants__role='leader',
                    project_participants__status='approved'
                )
            except ValueError:
                pass
        
        # 关键词搜索
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) | 
                Q(description__icontains=keyword)
            )
        
        # 评分状态筛选（仅对已完成项目有效）
        if is_evaluated is not None:
            is_evaluated_bool = is_evaluated.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(
                status='completed',
                is_evaluated=is_evaluated_bool
            )
        
        # 排序：创建时间倒序
        queryset = queryset.order_by('-created_at')
        
        # 使用通用分页工具
        from common_utils import paginate_queryset
        pagination_result = paginate_queryset(request, queryset, default_page_size=page_size)
        paginator = pagination_result['paginator']
        page_data = pagination_result['page_data']
        pagination_info = pagination_result['pagination_info']
        
        # 序列化数据
        serializer = StudentProjectListSerializer(
            page_data, many=True, context={'request': request}
        )
        
        # 构建返回数据
        data = {
            'projects': serializer.data,
            'pagination': pagination_info
        }
        
        return APIResponse.success(
            data=data,
            message="项目列表获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取项目列表失败: {str(e)}")
        return APIResponse.server_error(
            message="获取项目列表失败"
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_project_detail(request, project_id):
    """
    获取项目详情接口
    
    权限：所有认证用户
    功能：返回项目的详细信息，包括参与者、成果、评论等
    
    补充说明：每个学生项目都必须有且仅有一个leader
    - 项目创建时，创建者自动成为leader
    - leader可以转让给其他已批准的参与者
    - 项目必须始终保持有一个leader
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        
        # 记录浏览历史
        UserHistoryService.record_view(request.user.id, project_id, 'project')
        
        # 序列化项目详情
        serializer = StudentProjectDetailSerializer(project, context={'request': request})
        
        return APIResponse.success(
            data=serializer.data,
            message="项目详情获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取项目详情失败: {str(e)}")
        return APIResponse.server_error(
            message="获取项目详情失败"
        )


# ==================== 项目参与者管理接口 ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudentUser])
def apply_to_join_project(request, project_id):
    """
    申请加入项目接口
    
    权限：学生用户
    功能：学生可以申请加入项目，需要填写申请消息
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        user = request.user
        student = user.student_profile
        
        # 检查项目状态
        if project.status not in ['recruiting', 'in_progress']:
            return APIResponse.error(
                message="该项目当前不接受新成员申请"
            )
        
        # 检查是否已经是参与者
        existing_participant = ProjectParticipant.objects.filter(
            project=project,
            student=student
        ).first()
        
        if existing_participant:
            if existing_participant.status == 'pending':
                return APIResponse.error(
                    message="您已经申请过该项目，请等待审核结果"
                )
            elif existing_participant.status == 'approved':
                return APIResponse.error(
                    message="您已经是该项目的成员"
                )
            elif existing_participant.status in ['rejected', 'left']:
                # 允许重新申请被拒绝或已退出的项目
                existing_participant.delete()
        
        # 验证申请数据
        serializer = ProjectApplicationSerializer(data={
            'project_id': project_id,
            'role': request.data.get('role', 'member'),
            'application_message': request.data.get('application_message', '')
        })
        
        if not serializer.is_valid():
            return APIResponse.error(
                message="申请数据无效",
                errors=serializer.errors
            )
        
        # 创建申请记录
        with transaction.atomic():
            participant = ProjectParticipant.objects.create(
                project=project,
                student=student,
                role=serializer.validated_data['role'],
                status='pending',
                application_message=serializer.validated_data.get('application_message', ''),
                applied_at=timezone.now()
            )
            
            # 创建通知给项目负责人
            leader_participant = ProjectParticipant.objects.filter(
                project=project,
                role='leader',
                status='approved'
            ).first()
            
            if leader_participant:
                student_notification_service.send_project_application_notification(
                    leader=leader_participant.student.user,
                    applicant=student.user,
                    project=project,
                    application_message=serializer.validated_data.get('application_message', '')
                )
        
        return APIResponse.success(
            message="申请提交成功，请等待项目负责人审核"
        )
        
    except Exception as e:
        logger.error(f"申请加入项目失败: {str(e)}")
        return APIResponse.server_error(
            message="申请提交失败"
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudentUser])
def handle_applications(request, project_id):
    """
    统一申请处理接口（支持单个和批量处理）
    
    权限：项目负责人
    功能：项目负责人可以同意或拒绝申请，支持form-data格式
    支持单个ID或逗号分隔的多个ID
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        user = request.user
        
        # 检查权限：只有项目负责人可以处理申请
        leader_participant = ProjectParticipant.objects.filter(
            project=project,
            student__user=user,
            role='leader',
            status='approved'
        ).first()
        
        if not leader_participant:
            return APIResponse.error(
                message="只有项目负责人可以处理申请"
            )
        
        # 验证请求数据（支持form-data格式）
        serializer = UnifiedApplicationReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="请求数据无效",
                errors=serializer.errors
            )
        
        participant_ids = serializer.validated_data['participant_ids']
        action = serializer.validated_data['action']
        review_message = serializer.validated_data.get('review_message', '')
        
        # 设置默认审核消息
        if not review_message:
            if action == 'approve':
                review_message = "欢迎加入项目团队！"
            else:
                review_message = "很抱歉你的申请未能通过。"
        
        # 获取待处理的参与者
        participants = ProjectParticipant.objects.filter(
            id__in=participant_ids,
            project=project,
            status='pending'
        )
        
        if participants.count() != len(participant_ids):
            return APIResponse.error(
                message="部分申请不存在或已被处理"
            )
        
        # 批量更新申请状态
        with transaction.atomic():
            updated_count = 0
            processed_students = []
            for participant in participants:
                if action == 'approve':
                    participant.status = 'approved'
                    participant.approved_at = timezone.now()
                else:
                    participant.status = 'rejected'
                
                participant.review_message = review_message
                participant.reviewed_at = timezone.now()
                participant.reviewed_by = leader_participant.student
                participant.save()
                
                # 创建通知给申请者
                if action == "approve":
                    student_notification_service.send_application_result_notification(
                        applicant=participant.student.user,
                        project=project,
                        result='approved',
                        reviewer=leader_participant.student.user,
                        review_message=review_message
                    )
                else:
                    student_notification_service.send_application_result_notification(
                        applicant=participant.student.user,
                        project=project,
                        result='rejected',
                        reviewer=leader_participant.student.user,
                        review_message=review_message
                    )
                
                # 记录处理的学生信息
                student_info = f"{participant.student.user.username}（{participant.student.user.real_name or participant.student.user.username}）"
                processed_students.append(student_info)
                updated_count += 1
        
        # 根据处理数量返回不同的消息
        action_text = '已通过' if action == 'approve' else '已拒绝'
        if updated_count == 1:
            return APIResponse.success(
                message=f"{processed_students[0]}申请{action_text}"
            )
        else:
            return APIResponse.success(
                message=f"成功{('通过' if action == 'approve' else '拒绝')}了 {updated_count} 个申请"
            )
        
    except Exception as e:
        logger.error(f"处理申请失败: {str(e)}")
        return APIResponse.server_error(
            message="处理申请失败"
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStudentUser])
def get_project_participants(request, project_id):
    """
    获取项目参与者列表接口
    
    权限：项目内参与者和负责人
    功能：获取项目的所有参与者信息
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        user = request.user
        
        # 检查权限：只有项目参与者可以查看参与者列表
        user_participant = ProjectParticipant.objects.filter(
            project=project,
            student__user=user,
            status='approved'
        ).first()
        
        if not user_participant:
            return APIResponse.forbidden(
                message="只有项目成员可以查看参与者列表"
            )
        
        # 获取查询参数
        page_size_param = request.GET.get('page_size', '10')
        try:
            page_size = min(int(page_size_param) if page_size_param else 10, 50)
        except (ValueError, TypeError):
            page_size = 10
        
        # 获取所有已批准的参与者
        participants_queryset = ProjectParticipant.objects.filter(
            project=project,
            status='approved'
        ).select_related('student__user').order_by('-role', 'applied_at')
        
        # 使用通用分页工具
        from common_utils import paginate_queryset
        pagination_result = paginate_queryset(request, participants_queryset, default_page_size=page_size)
        participants_data = ParticipantListSerializer(
            pagination_result['page_data'], 
            many=True, 
            context={'request': request}
        ).data
        
        # 获取待审核的申请（仅负责人可见）
        pending_applications = []
        if user_participant.role == 'leader':
            pending_applications = ProjectParticipant.objects.filter(
                project=project,
                status='pending'
            ).select_related('student__user').order_by('applied_at')
            pending_data = ParticipantListSerializer(pending_applications, many=True, context={'request': request}).data
        else:
            pending_data = []
        
        return APIResponse.success(
            data={
                'participants': participants_data,
                'pending_applications': pending_data,
                'pagination': pagination_result['pagination_info'],
                'total_participants': participants_queryset.count(),
                'total_pending': len(pending_applications)
            }
        )
        
    except Exception as e:
        logger.error(f"获取项目参与者列表失败: {str(e)}")
        return APIResponse.server_error(
            message="获取参与者列表失败"
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStudentUser])
def get_participant_detail(request, project_id, participant_id):
    """
    获取参与者详细信息接口
    
    权限：项目内参与者和负责人
    功能：获取特定参与者的详细信息
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        participant = get_object_or_404(ProjectParticipant, id=participant_id, project=project)
        user = request.user
        
        # 检查权限：只有项目参与者可以查看参与者详情
        user_participant = ProjectParticipant.objects.filter(
            project=project,
            student__user=user,
            status='approved'
        ).first()
        
        if not user_participant:
            return APIResponse.forbidden(
                message="只有项目成员可以查看参与者详情"
            )
        
        # 序列化数据
        serializer = ParticipantDetailSerializer(participant, context={'request': request})
        
        return APIResponse.success(
            data=serializer.data
        )
        
    except Exception as e:
        logger.error(f"获取参与者详情失败: {str(e)}")
        return APIResponse.server_error(
            message="获取参与者详情失败"
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsStudentUser])
def update_participant_status(request, project_id, participant_id):
    """
    修改参与者状态接口
    
    权限：
    1. 项目负责人：可以修改所有成员的状态（除了自己和其他负责人）
    2. 项目参与者：只能修改自己的状态为 'left'（退出项目）
    
    功能：统一处理参与者状态修改和用户自行退出项目
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        participant = get_object_or_404(ProjectParticipant, id=participant_id, project=project)
        user = request.user
        
        # 检查用户是否为项目负责人
        leader_participant = ProjectParticipant.objects.filter(
            project=project,
            student__user=user,
            role='leader',
            status='approved'
        ).first()
        
        # 检查用户是否为被修改的参与者本人
        is_self = participant.student.user == user
        
        # 权限验证
        if not leader_participant and not is_self:
            return APIResponse.forbidden(
                message="只有项目负责人或参与者本人可以修改参与者状态"
            )
        
        # 负责人不能直接退出项目
        if is_self and participant.role == 'leader':
            return APIResponse.error(
                message="项目负责人不能直接退出项目，请先转移负责人身份"
            )
        
        # 负责人不能修改其他负责人的状态
        if leader_participant and not is_self and participant.role == 'leader':
            return APIResponse.error(
                message="不能修改其他负责人的状态"
            )
        
        # 验证请求数据
        serializer = ParticipantStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="请求数据无效",
                errors=serializer.errors
            )
        
        new_status = serializer.validated_data['status']
        reason = serializer.validated_data.get('reason', '')
        
        # 如果是参与者本人操作，只能设置为 'left'
        if is_self and new_status != 'left':
            return APIResponse.error(
                message="参与者只能将自己的状态修改为退出（left）"
            )
        
        # 更新参与者状态
        with transaction.atomic():
            old_status = participant.status
            participant.status = new_status
            participant.save()
            
            # 获取被操作者信息
            target_user_name = participant.student.user.real_name or participant.student.user.username
            
            # 根据操作者和状态变更创建相应的通知
            if is_self and new_status == 'left':
                # 用户自行退出项目，通知项目负责人
                # 获取项目负责人
                project_leader = ProjectParticipant.objects.filter(
                    project=project,
                    role='leader',
                    status='approved'
                ).first()
                
                if project_leader:
                    student_notification_service.send_member_left_notification(
                        leader=project_leader.student.user,
                        member=participant.student.user,
                        project=project,
                        member_role=participant.role
                    )
                return APIResponse.success(
                    message="已成功退出项目"
                )
            elif leader_participant and not is_self:
                # 负责人修改其他成员状态
                if new_status == 'left':
                    # 踢出成员，通知被踢出者
                    student_notification_service.send_member_kicked_notification(
                        member=participant.student.user,
                        project=project,
                        operator=leader_participant.student.user,
                        reason=reason
                    )
                    return APIResponse.success(
                        message=f"{target_user_name} 已被移出项目"
                    )
                elif new_status == 'approved':
                    # 激活成员
                    student_notification_service.send_member_status_change_notification(
                        member=participant.student.user,
                        project=project,
                        old_status=old_status,
                        new_status=new_status,
                        operator=leader_participant.student.user
                    )
                    return APIResponse.success(
                        message=f"{target_user_name} 已被激活"
                    )
                else:
                    # 其他状态变更
                    student_notification_service.send_member_status_change_notification(
                        member=participant.student.user,
                        project=project,
                        old_status=old_status,
                        new_status=new_status,
                        operator=leader_participant.student.user
                    )
                    return APIResponse.success(
                        message=f"{target_user_name} 已被停用"
                    )
        
        return APIResponse.success(
            message="参与者状态修改成功"
        )
        
    except Exception as e:
        logger.error(f"修改参与者状态失败: {str(e)}")
        return APIResponse.server_error(
            message="修改参与者状态失败"
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudentUser])
def transfer_leadership(request, project_id):
    """
    转移身份权限接口
    
    权限：项目负责人
    功能：项目负责人可以将负责人身份转移给其他参与者
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        user = request.user
        
        # 检查权限：只有项目负责人可以转移身份
        current_leader = ProjectParticipant.objects.filter(
            project=project,
            student__user=user,
            role='leader',
            status='approved'
        ).first()
        
        if not current_leader:
            return APIResponse.forbidden(
                message="只有项目负责人可以转移身份权限"
            )
        
        # 验证请求数据
        serializer = LeadershipTransferSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="请求数据无效",
                errors=serializer.errors
            )
        
        new_leader_id = serializer.validated_data['new_leader_id']
        transfer_reason = serializer.validated_data.get('transfer_reason', '')
        
        # 获取新负责人
        new_leader = get_object_or_404(
            ProjectParticipant,
            id=new_leader_id,
            project=project,
            status='approved'
        )
        
        # 不能转移给自己
        if new_leader.student.user == user:
            return APIResponse.error(
                message="不能将负责人身份转移给自己"
            )
        
        # 不能转移给已经是负责人的人
        if new_leader.role == 'leader':
            return APIResponse.error(
                message="该用户已经是项目负责人"
            )
        
        # 执行身份转移
        with transaction.atomic():
            # 将当前负责人改为普通成员
            current_leader.role = 'member'
            current_leader.save()
            
            # 将新成员提升为负责人
            new_leader.role = 'leader'
            new_leader.save()
        
        # 数据库操作成功后，发送通知
        try:
            # 发送专门的负责人转移通知给新负责人
            student_notification_service.send_leadership_transfer_notification(
                new_leader=new_leader.student.user,
                project=project,
                original_leader=current_leader.student.user,
                transfer_message=serializer.validated_data.get('transfer_message')
            )
            
            # 发送负责人变更通知给其他成员（不包括新旧负责人）
            # 获取除新旧负责人外的所有项目成员
            other_members = project.project_participants.exclude(
                id__in=[new_leader.id, current_leader.id]
            ).filter(status='approved')
            member_users = [participant.student.user for participant in other_members]
            
            if member_users:  # 只有当有其他成员时才发送通知
                student_notification_service.send_leadership_change_notification(
                    members=member_users,
                    project=project,
                    new_leader=new_leader.student.user,
                    original_leader=current_leader.student.user,
                    transfer_message=serializer.validated_data.get('transfer_message')
                )
        except Exception as notification_error:
            # 通知发送失败不影响身份转移的成功
            logger.warning(f"身份转移成功，但通知发送失败: {str(notification_error)}")
            

        
        return APIResponse.success(
            message=f"负责人身份已成功转移给 {new_leader.student.user.real_name}"
        )
        
    except Exception as e:
        logger.error(f"转移身份权限失败: {str(e)}")
        return APIResponse.server_error(
            message="转移身份权限失败"
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudentUser])
def send_invitation(request, project_id):
    """
    发送项目邀请接口
    
    权限：学生用户（项目负责人）
    功能：项目负责人可以邀请学生用户加入项目
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        user = request.user
        student = user.student_profile
        
        # 检查是否为项目负责人
        leader_participant = ProjectParticipant.objects.filter(
            project=project,
            student=student,
            role='leader',
            status='approved'
        ).first()
        
        if not leader_participant:
            return APIResponse.error(
                message="只有项目负责人可以发送邀请"
            )
        
        # 验证请求数据
        serializer = SendInvitationSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="请求参数错误",
                errors=format_validation_errors(serializer.errors)
            )
        
        invitee_username = serializer.validated_data['invitee_username']
        invitation_message = serializer.validated_data.get('invitation_message', '')
        
        # 获取被邀请者（通过用户名查找）
        try:
            invitee_user = User.objects.get(username=invitee_username, user_type='student')
            invitee = Student.objects.get(user=invitee_user)
        except User.DoesNotExist:
            return APIResponse.error(
                message="用户名不存在或该用户不是学生"
            )
        except Student.DoesNotExist:
            return APIResponse.error(
                message="该用户没有学生档案"
            )
        
        # 检查是否已经是项目成员
        existing_participant = ProjectParticipant.objects.filter(
            project=project,
            student=invitee
        ).first()
        
        if existing_participant:
            if existing_participant.status == 'approved':
                return APIResponse.error(
                    message="该学生已经是项目成员"
                )
            elif existing_participant.status == 'pending':
                return APIResponse.error(
                    message="该学生已有待审核的申请"
                )
        
        # 检查是否已有待处理的邀请
        existing_invitation = ProjectInvitation.objects.filter(
            project=project,
            invitee=invitee,
            status='pending'
        ).first()
        
        if existing_invitation and not existing_invitation.is_expired():
            return APIResponse.error(
                message="已向该学生发送过邀请，请等待回复"
            )
        
        # 检查是否有被拒绝或过期的邀请，如果有则可以重新邀请
        # 先处理过期但状态仍为pending的邀请
        expired_pending_invitations = ProjectInvitation.objects.filter(
            project=project,
            invitee=invitee,
            status='pending'
        ).filter(expires_at__lt=timezone.now())
        
        # 更新过期邀请的状态
        if expired_pending_invitations.exists():
            expired_pending_invitations.update(status='expired')
        
        # 删除之前被拒绝或过期的邀请记录，避免唯一性约束冲突
        old_invitations = ProjectInvitation.objects.filter(
            project=project,
            invitee=invitee,
            status__in=['rejected', 'expired']
        )
        
        if old_invitations.exists():
            old_count = old_invitations.count()
            old_invitations.delete()
            logger.info(f"删除了 {old_count} 个旧邀请记录，项目ID: {project_id}, 被邀请者: {invitee_username}")
        
        # 创建邀请
        with transaction.atomic():
            invitation = ProjectInvitation.objects.create(
                project=project,
                inviter=student,
                invitee=invitee,
                invitation_message=invitation_message
            )
            
            # 创建通知
            student_notification_service.send_project_invitation_notification(
                invitee=invitee.user,
                inviter=student.user,
                project=project,
                invitation=invitation,
                invitation_message=invitation_message
            )
        
        return APIResponse.success(
            message=f"已成功向 {invitee.user.real_name} 发送邀请",
            data=ProjectInvitationSerializer(invitation, context={'request': request}).data
        )
        
    except Exception as e:
        logger.error(f"发送邀请失败: {str(e)}")
        return APIResponse.server_error(
            message="发送邀请失败"
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudentUser])
def respond_to_invitation(request, invitation_id):
    """
    响应项目邀请接口
    
    权限：学生用户（被邀请者）
    功能：被邀请的学生可以接受或拒绝项目邀请
    """
    try:
        invitation = get_object_or_404(ProjectInvitation, id=invitation_id)
        user = request.user
        student = user.student_profile
        
        # 检查是否为被邀请者
        if invitation.invitee != student:
            return APIResponse.error(
                message="您无权响应此邀请"
            )
        
        # 检查邀请是否可以响应
        if not invitation.can_respond():
            if invitation.is_expired():
                return APIResponse.error(
                    message="邀请已过期"
                )
            else:
                return APIResponse.error(
                    message="邀请已处理，无法重复响应"
                )
        
        # 验证请求数据
        serializer = InvitationResponseSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="请求参数错误",
                errors=format_validation_errors(serializer.errors)
            )
        
        action = serializer.validated_data['action']
        response_message = serializer.validated_data.get('response_message', '')
        
        with transaction.atomic():
            # 更新邀请状态
            invitation.status = 'accepted' if action == 'accept' else 'rejected'
            invitation.response_message = response_message
            invitation.responded_at = timezone.now()
            invitation.save()
            
            if action == 'accept':
                # 接受邀请，直接创建项目参与者记录
                participant = ProjectParticipant.objects.create(
                    project=invitation.project,
                    student=student,
                    role='member',
                    status='approved',  # 邀请的学生直接通过，无需审核
                    application_message=f"通过邀请加入项目。邀请留言：{invitation.invitation_message}",
                    reviewed_by=invitation.inviter,
                    review_message="通过项目邀请直接加入",
                    reviewed_at=timezone.now()
                )
                
                # 通知邀请者
                student_notification_service.send_invitation_response_notification(
                    inviter=invitation.inviter.user,
                    invitee=student.user,
                    project=invitation.project,
                    response='accepted',
                    response_message=response_message
                )
                
                message = f"已成功加入项目 \"{invitation.project.title}\""
            else:
                # 拒绝邀请
                student_notification_service.send_invitation_response_notification(
                    inviter=invitation.inviter.user,
                    invitee=student.user,
                    project=invitation.project,
                    response='rejected',
                    response_message=response_message
                )
                
                message = f"已拒绝加入项目 \"{invitation.project.title}\""
        
        return APIResponse.success(
            message=message,
            data=ProjectInvitationSerializer(invitation, context={'request': request}).data
        )
        
    except Exception as e:
        logger.error(f"响应邀请失败: {str(e)}")
        return APIResponse.server_error(
            message="响应邀请失败"
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStudentUser])
def get_invitations(request):
    """
    获取邀请列表接口
    
    权限：学生用户
    功能：获取发出的邀请和收到的邀请列表
    """
    try:
        user = request.user
        student = user.student_profile
        
        invitation_type = request.GET.get('type', 'received')  # received 或 sent
        status_filter = request.GET.get('status', '')  # pending, accepted, rejected, expired
        page = int(request.GET.get('page') or 1)
        page_size = int(request.GET.get('page_size') or 10)
        
        if invitation_type == 'sent':
            # 获取发出的邀请
            queryset = ProjectInvitation.objects.filter(
                inviter=student
            ).select_related('project', 'invitee__user')
        else:
            # 获取收到的邀请
            queryset = ProjectInvitation.objects.filter(
                invitee=student
            ).select_related('project', 'inviter__user')
        
        # 状态过滤
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 使用通用分页工具
        from common_utils import paginate_queryset
        pagination_result = paginate_queryset(request, queryset, default_page_size=page_size)
        paginator = pagination_result['paginator']
        page_data = pagination_result['page_data']
        pagination_info = pagination_result['pagination_info']
        
        # 序列化数据
        serializer = ProjectInvitationSerializer(
            page_data,
            many=True,
            context={'request': request}
        )
        
        return APIResponse.success(
            data={
                'invitations': serializer.data,
                'pagination': pagination_info
            }
        )
        
    except Exception as e:
        logger.error(f"获取邀请列表失败: {str(e)}")
        return APIResponse.server_error(
            message="获取邀请列表失败"
        )


# ==================== 项目成果管理视图 ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudentUser])
def submit_deliverable(request, project_id):
    """
    提交项目成果接口
    
    权限：学生用户（项目参与者和项目负责人）
    功能：提交项目成果，支持文件上传和网盘链接
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        user = request.user
        student = user.student_profile
        
        # 检查是否为项目参与者或负责人
        participant = ProjectParticipant.objects.filter(
            project=project,
            student=student,
            status='approved'
        ).first()
        
        if not participant:
            return APIResponse.error(
                message="您没有权限提交该项目的成果"
            )
        
        # 验证请求数据
        from .serializers import ProjectDeliverableSubmitSerializer
        serializer = ProjectDeliverableSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="请求参数错误",
                errors=format_validation_errors(serializer.errors)
            )
        
        # 创建成果记录
        deliverable = serializer.save(project=project, submitter=student)
        
        # 返回详细信息
        from .serializers import ProjectDeliverableDetailSerializer
        detail_serializer = ProjectDeliverableDetailSerializer(
            deliverable,
            context={'request': request}
        )
        
        return APIResponse.success(
            message="成果提交成功",
            data=detail_serializer.data
        )
        
    except Exception as e:
        logger.error(f"成果提交失败: {str(e)}")
        return APIResponse.server_error(
            message=f"成果提交失败: {str(e)}"
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsStudentUser])
def update_deliverable(request, project_id, deliverable_id):
    """
    更新项目成果接口（包含弃用功能）
    
    权限：学生用户（项目参与者和项目负责人）
    功能：更新项目成果，不支持修改实体文件，但可以修改或补充网盘链接
          支持通过设置is_deprecated=true来弃用成果
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        deliverable = get_object_or_404(ProjectDeliverable, id=deliverable_id, project=project)
        user = request.user
        student = user.student_profile
        
        # 检查是否为项目参与者或负责人
        participant = ProjectParticipant.objects.filter(
            project=project,
            student=student,
            status='approved'
        ).first()
        
        if not participant:
            return APIResponse.error(
                message="您没有权限更新该成果"
            )
        
        # 验证请求数据
        from .serializers import ProjectDeliverableUpdateSerializer
        serializer = ProjectDeliverableUpdateSerializer(
            deliverable, 
            data=request.data, 
            partial=True
        )
        if not serializer.is_valid():
            return APIResponse.error(
                message="请求参数错误",
                data=format_validation_errors(serializer.errors)
            )
        
        # 更新成果记录，设置最新修改人和更新标识
        # 如果不是弃用操作，则设置is_updated=True
        save_kwargs = {'last_modifier': student}
        if not request.data.get('is_deprecated', False):
            save_kwargs['is_updated'] = True
        
        updated_deliverable = serializer.save(**save_kwargs)
        
        # 返回详细信息
        from .serializers import ProjectDeliverableDetailSerializer
        detail_serializer = ProjectDeliverableDetailSerializer(
            updated_deliverable,
            context={'request': request}
        )
        
        # 根据操作类型返回不同的消息
        if updated_deliverable.is_deprecated:
            message = "成果已标记为弃用"
        else:
            message = "成果更新成功"
        
        return APIResponse.success(
            message=message,
            data=detail_serializer.data
        )
        
    except Exception as e:
        logger.error(f"成果更新失败: {str(e)}")
        return APIResponse.server_error(
            message=f"成果更新失败: {str(e)}"
        )



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_deliverable_list(request, project_id):
    """
    获取项目成果列表接口
    
    权限：项目参与者、项目负责人和项目所属组织的组织用户
    功能：获取项目的成果列表，支持多种筛选和展示模式
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        user = request.user
        
        # 检查权限
        has_permission = False
        
        # 检查是否为项目参与者或负责人
        if user.user_type == 'student':
            participant = ProjectParticipant.objects.filter(
                project=project,
                student=user.student_profile,
                status='approved'
            ).first()
            if participant:
                has_permission = True
        
        # 检查是否为项目所属组织的组织用户
        elif user.user_type == 'organization':
            org_user = OrganizationUser.objects.filter(
                user=user,
                organization=project.requirement.organization
            ).first()
            if org_user:
                has_permission = True
        
        if not has_permission:
            return APIResponse.error(
                message="您没有权限查看该项目的成果"
            )
        
        # 获取查询参数
        stage_type = request.GET.get('stage_type')
        include_deprecated = request.GET.get('include_deprecated', 'true').lower() == 'true'
        milestone = request.GET.get('milestone', 'false').lower() == 'true'
        latest_per_stage = request.GET.get('latest_per_stage', 'false').lower() == 'true'
        
        try:
            page = int(request.GET.get('page', 1) or 1)
        except (ValueError, TypeError):
            page = 1
        
        try:
            page_size = int(request.GET.get('page_size', 10) or 10)
        except (ValueError, TypeError):
            page_size = 10
        
        # 构建查询
        queryset = ProjectDeliverable.objects.filter(project=project)
        
        if stage_type:
            queryset = queryset.filter(stage_type=stage_type)
        
        if not include_deprecated:
            queryset = queryset.filter(is_deprecated=False)
        
        # 处理里程碑成果筛选
        if milestone:
            queryset = queryset.filter(is_milestone=True)
        
        # 处理每阶段最新成果展示
        if latest_per_stage:
            # 获取每个阶段的最新成果（版本号最大的成果）
            from django.db.models import Max
            
            # 先获取每个阶段的最大版本号
            stage_max_versions = queryset.values('stage_type').annotate(
                max_version=Max('version_number')
            )
            
            # 构建筛选条件 - 只有当存在阶段数据时才进行筛选
            if stage_max_versions.exists():
                stage_version_filters = Q()
                for stage_info in stage_max_versions:
                    stage_version_filters |= Q(
                        stage_type=stage_info['stage_type'],
                        version_number=stage_info['max_version']
                    )
                
                # 应用每阶段最新成果筛选到当前queryset
                queryset = queryset.filter(stage_version_filters)
            else:
                # 如果没有任何阶段数据，返回空查询集
                queryset = queryset.none()
        
        # 默认排序：阶段从末期到前期，阶段内版本号从大到小
        queryset = queryset.annotate(
            stage_priority=Case(
                When(stage_type='final', then=3),
                When(stage_type='middle', then=2),
                When(stage_type='early', then=1),
                default=0,
                output_field=IntegerField()
            )
        ).order_by('-stage_priority', '-version_number')
        
        # 添加关联查询优化
        queryset = queryset.select_related(
            'project', 'submitter'
        ).prefetch_related('files')
        
        # 使用通用分页工具
        from common_utils import paginate_queryset
        pagination_result = paginate_queryset(request, queryset, default_page_size=page_size)
        paginator = pagination_result['paginator']
        page_data = pagination_result['page_data']
        pagination_info = pagination_result['pagination_info']
        
        # 序列化数据
        from .serializers import ProjectDeliverableListSerializer
        serializer = ProjectDeliverableListSerializer(
            page_data,
            many=True,
            context={'request': request}
        )
        
        return APIResponse.success(
            data={
                'deliverables': serializer.data,
                'pagination': pagination_info
            }
        )
        
    except Exception as e:
        logger.error(f"获取成果列表失败: {str(e)}")
        return APIResponse.server_error(
            message="获取成果列表失败"
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_deliverable_detail(request, project_id, deliverable_id):
    """
    获取项目成果详情接口
    
    权限：项目参与者、项目负责人和项目所属组织的组织用户
    功能：获取项目成果的详细信息
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        deliverable = get_object_or_404(ProjectDeliverable, id=deliverable_id, project=project)
        user = request.user
        
        # 检查权限
        has_permission = False
        
        # 检查是否为项目参与者或负责人
        if user.user_type == 'student':
            participant = ProjectParticipant.objects.filter(
                project=project,
                student=user.student_profile,
                status='approved'
            ).first()
            if participant:
                has_permission = True
        
        # 检查是否为项目所属组织的组织用户
        elif user.user_type == 'organization':
            org_user = OrganizationUser.objects.filter(
                user=user,
                organization=project.requirement.organization
            ).first()
            if org_user:
                has_permission = True
        
        if not has_permission:
            return APIResponse.error(
                message="您没有权限查看该成果详情"
            )
        
        # 序列化数据
        from .serializers import ProjectDeliverableDetailSerializer
        serializer = ProjectDeliverableDetailSerializer(
            deliverable,
            context={'request': request}
        )
        
        return APIResponse.success(
            data=serializer.data
        )
        
    except Exception as e:
        logger.error(f"获取成果详情失败: {str(e)}")
        return APIResponse.server_error(
            message="获取成果详情失败"
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_comment_list(request, project_id):
    """
    获取评语列表接口
    
    权限：项目参与者、项目负责人和项目所属组织的组织用户
    功能：获取项目级或成果级评语列表
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        user = request.user
        deliverable_id = request.GET.get('deliverable_id')
        
        # 权限检查：项目参与者、负责人或所属组织用户
        has_permission = False
        
        if user.user_type == 'student':
            participant = ProjectParticipant.objects.filter(
                project=project,
                student=user.student_profile,
                status='approved'
            ).first()
            if participant:
                has_permission = True
        elif user.user_type == 'organization':
            org_user = OrganizationUser.objects.filter(
                user=user,
                organization=project.requirement.organization
            ).first()
            if org_user:
                has_permission = True
        
        if not has_permission:
            return APIResponse.error(
                message="您没有权限查看评语"
            )
        
        # 构建查询条件
        queryset = ProjectComment.objects.filter(project=project)
        
        if deliverable_id:
            # 成果级评语
            deliverable = get_object_or_404(ProjectDeliverable, id=deliverable_id, project=project)
            queryset = queryset.filter(deliverable=deliverable)
        else:
            # 项目级评语
            queryset = queryset.filter(deliverable__isnull=True)
        
        # 只获取顶级评论（非回复）
        queryset = queryset.filter(parent_comment__isnull=True)
        
        # 预加载相关数据
        queryset = queryset.select_related('author', 'deliverable').prefetch_related('replies')
        
        # 排序
        queryset = queryset.order_by('-created_at')
        
        # 分页
        try:
            page = int(request.GET.get('page', 1) or 1)
        except (ValueError, TypeError):
            page = 1
        
        try:
            page_size = int(request.GET.get('page_size', 10) or 10)
        except (ValueError, TypeError):
            page_size = 10
        
        from common_utils import paginate_queryset
        pagination_result = paginate_queryset(request, queryset, default_page_size=page_size)
        page_data = pagination_result['page_data']
        pagination_info = pagination_result['pagination_info']
        
        # 序列化数据
        from .serializers import ProjectCommentSerializer
        serializer = ProjectCommentSerializer(
            page_data,
            many=True,
            context={'request': request}
        )
        
        return APIResponse.success(
            data={
                'comments': serializer.data,
                'pagination': pagination_info
            }
        )
        
    except Exception as e:
        logger.error(f"获取评语列表失败: {str(e)}")
        return APIResponse.server_error(
            message="获取评语列表失败"
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_comment(request, project_id):
    """
    发布评语接口
    
    权限：只有项目关联需求所属的组织用户可以发布
    功能：发布项目级或成果级评语
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        user = request.user
        deliverable_id = request.GET.get('deliverable_id')
        parent_comment_id = request.GET.get('parent_comment_id')
        
        # 权限检查：只有项目关联需求所属的组织用户可以发布
        if user.user_type != 'organization':
            return APIResponse.error(
                message="只有组织用户可以发布评语"
            )
        
        org_user = OrganizationUser.objects.filter(
            user=user,
            organization=project.requirement.organization
        ).first()
        
        if not org_user:
            return APIResponse.error(
                message="您没有权限发布评语"
            )
        
        # 获取关联成果（如果是成果级评语）
        deliverable = None
        if deliverable_id:
            deliverable = get_object_or_404(ProjectDeliverable, id=deliverable_id, project=project)
        
        # 获取父评论（如果是回复）
        parent_comment = None
        if parent_comment_id:
            parent_comment = get_object_or_404(ProjectComment, id=parent_comment_id, project=project)
        
        # 准备序列化数据
        serializer_data = request.data.copy()
        if parent_comment:
            serializer_data['parent_comment'] = parent_comment.id
        
        # 序列化和验证数据
        from .serializers import ProjectCommentCreateSerializer
        serializer = ProjectCommentCreateSerializer(
            data=serializer_data,
            context={
                'request': request,
                'project': project,
                'deliverable': deliverable
            }
        )
        
        if serializer.is_valid():
            comment = serializer.save()
            
            # 发送项目评论通知给所有项目成员
            try:
                # 获取项目所有成员
                project_members = [p.user for p in project.participants.filter(status='active')]
                student_notification_service.send_project_commented_notification(
                    members=project_members,
                    project=project,
                    commenter=user,
                    comment_content=comment.content,
                    comment_obj=comment
                )
            except Exception as e:
                logger.error(f"发送项目评论通知失败: {str(e)}")
            
            # 返回创建的评语详情
            from .serializers import ProjectCommentSerializer
            response_serializer = ProjectCommentSerializer(
                comment,
                context={'request': request}
            )
            
            return APIResponse.success(
                data=response_serializer.data,
                message="评语发布成功"
            )
        else:
            return APIResponse.error(
                message="数据验证失败",
                errors=format_validation_errors(serializer.errors)
            )
            
    except Exception as e:
        logger.error(f"发布评语失败: {str(e)}")
        return APIResponse.server_error(
            message="发布评语失败"
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_comment(request, project_id, comment_id):
    """
    更新评语接口
    
    权限：只有评语发布者可以更新
    功能：更新评语内容并记录更新时间
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        comment = get_object_or_404(ProjectComment, id=comment_id, project=project)
        user = request.user
        
        # 权限检查：只有评语发布者可以更新
        if comment.author != user:
            return APIResponse.error(
                message="您只能更新自己发布的评语"
            )
        
        # 序列化和验证数据
        from .serializers import ProjectCommentUpdateSerializer
        serializer = ProjectCommentUpdateSerializer(
            comment,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            updated_comment = serializer.save()
            
            # 返回更新后的评语详情
            from .serializers import ProjectCommentSerializer
            response_serializer = ProjectCommentSerializer(
                updated_comment,
                context={'request': request}
            )
            
            return APIResponse.success(
                data=response_serializer.data,
                message="评语更新成功"
            )
        else:
            return APIResponse.error(
                message="数据验证失败",
                errors=format_validation_errors(serializer.errors)
            )
            
    except Exception as e:
        logger.error(f"更新评语失败: {str(e)}")
        return APIResponse.server_error(
            message="更新评语失败"
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_comment(request, project_id, comment_id):
    """
    删除评语接口
    
    权限：只有评语发布者可以删除
    功能：删除评语（级联删除所有回复）
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        comment = get_object_or_404(ProjectComment, id=comment_id, project=project)
        user = request.user
        
        # 权限检查：只有评语发布者可以删除
        if comment.author != user:
            return APIResponse.error(
                message="您只能删除自己发布的评语"
            )
        
        # 删除评语（会级联删除所有回复）
        comment.delete()
        
        return APIResponse.success(
            message="评语删除成功"
        )
        
    except Exception as e:
        logger.error(f"删除评语失败: {str(e)}")
        return APIResponse.server_error(
            message="删除评语失败"
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_comment_replies(request, project_id, comment_id):
    """
    获取评语回复列表接口
    
    权限：项目参与者、项目负责人和项目所属组织的组织用户
    功能：获取指定评语的所有回复
    """
    try:
        project = get_object_or_404(StudentProject, id=project_id)
        comment = get_object_or_404(ProjectComment, id=comment_id, project=project)
        user = request.user
        
        # 权限检查：项目参与者、负责人或所属组织用户
        has_permission = False
        
        if user.user_type == 'student':
            participant = ProjectParticipant.objects.filter(
                project=project,
                student=user.student_profile,
                status='approved'
            ).first()
            if participant:
                has_permission = True
        elif user.user_type == 'organization':
            org_user = OrganizationUser.objects.filter(
                user=user,
                organization=project.requirement.organization
            ).first()
            if org_user:
                has_permission = True
        
        if not has_permission:
            return APIResponse.error(
                message="您没有权限查看评语回复"
            )
        
        # 获取回复列表
        replies = comment.replies.select_related('author').order_by('created_at')
        
        # 分页处理
        from common_utils import paginate_queryset
        pagination_result = paginate_queryset(request, replies, default_page_size=10)
        page_data = pagination_result['page_data']
        pagination_info = pagination_result['pagination_info']
        
        # 序列化数据
        from .serializers import ProjectCommentSerializer
        serializer = ProjectCommentSerializer(
            page_data,
            many=True,
            context={'request': request}
        )
        
        return APIResponse.success(
            data={
                'replies': serializer.data,
                'pagination': pagination_info
            }
        )
        
    except Exception as e:
        logger.error(f"获取评语回复失败: {str(e)}")
        return APIResponse.server_error(
            message="获取评语回复失败"
        )
