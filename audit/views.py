from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from common_utils import APIResponse, format_validation_errors
from user.models import OrganizationUser
from project.models import Requirement
from organization.models import Organization
from .models import RequirementAuditLog, OrganizationAuditLog
from .serializers import RequirementAuditLogSerializer, OrganizationAuditLogSerializer
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_requirement_audit_history(request, requirement_id):
    """获取需求审核历史记录"""
    try:
        user = request.user
        
        # 获取需求对象
        requirement = get_object_or_404(Requirement, id=requirement_id)
        
        # 权限检查：只有需求发布者、组织管理员或组织所有者可以查看审核历史
        try:
            org_user = OrganizationUser.objects.get(
                user=user, 
                organization=requirement.organization,
                status='approved'
            )
            
            # 检查权限
            if (requirement.publish_people != org_user and 
                org_user.permission not in ['admin', 'owner']):
                return APIResponse.forbidden("只有需求发布者、组织管理员或组织所有者可以查看审核历史")
                
        except OrganizationUser.DoesNotExist:
            return APIResponse.forbidden("您不是此需求所属组织的成员")
        
        # 获取查询参数
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 20)), 100)  # 限制最大页面大小
        action = request.GET.get('action')  # 筛选操作类型
        operator_id = request.GET.get('operator_id')  # 筛选操作者
        start_date = request.GET.get('start_date')  # 开始日期
        end_date = request.GET.get('end_date')  # 结束日期
        
        # 构建查询条件
        queryset = RequirementAuditLog.objects.filter(
            requirement=requirement
        ).select_related('operator').order_by('-created_at')
        
        # 应用筛选条件
        if action:
            queryset = queryset.filter(action=action)
        
        if operator_id:
            queryset = queryset.filter(operator_id=operator_id)
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # 分页处理
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        # 序列化数据
        serializer = RequirementAuditLogSerializer(
            page_obj.object_list, 
            many=True,
            context={'request': request}
        )
        
        return APIResponse.success({
            'results': serializer.data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'page_size': page_size,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })
        
    except Exception as e:
        logger.error(f"获取需求审核历史失败: {str(e)}")
        return APIResponse.server_error('获取审核历史失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_organization_audit_history(request, organization_id=None):
    """获取组织认证审核历史记录"""
    try:
        user = request.user
        
        # 如果没有指定组织ID，获取用户所属组织
        if organization_id:
            organization = get_object_or_404(Organization, id=organization_id)
        else:
            try:
                org_user = OrganizationUser.objects.select_related('organization').get(
                    user=user, 
                    status='approved'
                )
                organization = org_user.organization
            except OrganizationUser.DoesNotExist:
                return APIResponse.error('您不属于任何组织', code=403)
        
        # 权限检查：只有组织管理员或组织所有者可以查看审核历史
        try:
            org_user = OrganizationUser.objects.get(
                user=user, 
                organization=organization,
                status='approved'
            )
            
            if org_user.permission != 'owner':
                return APIResponse.forbidden("只有组织所有者可以查看审核历史")
                
        except OrganizationUser.DoesNotExist:
            return APIResponse.forbidden("您不是此组织的成员")
        
        # 获取查询参数
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 20)), 100)  # 限制最大页面大小
        action = request.GET.get('action')  # 筛选操作类型
        operator_id = request.GET.get('operator_id')  # 筛选操作者
        start_date = request.GET.get('start_date')  # 开始日期
        end_date = request.GET.get('end_date')  # 结束日期
        
        # 构建查询条件
        queryset = OrganizationAuditLog.objects.filter(
            organization=organization
        ).select_related('operator').order_by('-created_at')
        
        # 应用筛选条件
        if action:
            queryset = queryset.filter(action=action)
        
        if operator_id:
            queryset = queryset.filter(operator_id=operator_id)
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # 分页处理
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        # 序列化数据
        serializer = OrganizationAuditLogSerializer(
            page_obj.object_list, 
            many=True,
            context={'request': request}
        )
        
        return APIResponse.success({
            'results': serializer.data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'page_size': page_size,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })
        
    except Exception as e:
        logger.error(f"获取组织审核历史失败: {str(e)}")
        return APIResponse.server_error('获取审核历史失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_audit_statistics(request):
    """获取审核统计信息"""
    try:
        user = request.user
        
        # 获取用户所属组织
        try:
            org_user = OrganizationUser.objects.select_related('organization').get(
                user=user, 
                status='approved'
            )
            organization = org_user.organization
        except OrganizationUser.DoesNotExist:
            return APIResponse.error('您不属于任何组织', code=403)
        
        # 权限检查：只有组织管理员或组织所有者可以查看统计信息
        if org_user.permission not in ['admin', 'owner']:
            return APIResponse.forbidden("只有组织管理员或组织所有者可以查看统计信息")
        
        # 获取需求审核统计
        requirement_stats = {
            'total_requirements': Requirement.objects.filter(organization=organization).count(),
            'under_review': Requirement.objects.filter(organization=organization, status='under_review').count(),
            'approved': Requirement.objects.filter(organization=organization, status='approved').count(),
            'rejected': Requirement.objects.filter(organization=organization, status='review_failed').count(),
            'audit_logs_count': RequirementAuditLog.objects.filter(
                requirement__organization=organization
            ).count()
        }
        
        # 获取组织认证审核统计
        organization_stats = {
            'current_status': organization.status,
            'audit_logs_count': OrganizationAuditLog.objects.filter(
                organization=organization
            ).count()
        }
        
        return APIResponse.success({
            'requirement_audit_stats': requirement_stats,
            'organization_audit_stats': organization_stats
        })
        
    except Exception as e:
        logger.error(f"获取审核统计信息失败: {str(e)}")
        return APIResponse.server_error('获取统计信息失败，请稍后重试')