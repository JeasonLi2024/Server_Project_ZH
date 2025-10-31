import logging
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    EvaluationCriteria,
    EvaluationIndicator,
    ProjectEvaluation,
    ProjectRanking
)
from .serializers import (
    EvaluationCriteriaListSerializer,
    EvaluationCriteriaDetailSerializer,
    EvaluationCriteriaCreateSerializer,
    EvaluationCriteriaUpdateSerializer,
    EvaluationCriteriaBatchIndicatorUpdateSerializer,
    EvaluationCriteriaStatusUpdateSerializer,
    EvaluationCriteriaCloneSerializer,
    EvaluationCriteriaTemplateSerializer,
    EvaluationIndicatorSerializer,
    EvaluationIndicatorCreateSerializer,
    EvaluationIndicatorBatchCreateSerializer,
    EvaluationIndicatorUpdateSerializer,
    ProjectEvaluationCreateSerializer,
    ProjectEvaluationDetailSerializer,
    ProjectEvaluationUpdateSerializer,
    ProjectRankingSerializer
)
from project.models import Requirement
from organization.models import Organization
from studentproject.models import StudentProject
from common_utils import APIResponse, format_validation_errors, paginate_queryset
from notification.services import student_notification_service

logger = logging.getLogger(__name__)

User = get_user_model()


class IsOrganizationUser(permissions.BasePermission):
    """检查用户是否为组织用户"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.user_type == 'organization' and
            hasattr(request.user, 'organization_profile')
        )


class IsOrganizationAdminOrCreator(permissions.BasePermission):
    """检查用户是否为组织管理员或评分标准创建者"""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if request.user.user_type != 'organization':
            return False
            
        if not hasattr(request.user, 'organization_profile'):
            return False
        
        user_org = request.user.organization_profile
        
        # 检查是否为同一组织
        if obj.organization != user_org.organization:
            return False
        
        # 组织创建者或管理员有权限
        if user_org.permission in ['owner', 'admin']:
            return True
        
        # 评分标准创建者有权限
        if obj.creator == request.user:
            return True
        
        return False


class IsOrganizationOwnerOrAdmin(permissions.BasePermission):
    """检查用户是否为组织创建者或管理员"""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if request.user.user_type != 'organization':
            return False
            
        if not hasattr(request.user, 'organization_profile'):
            return False
        
        user_org = request.user.organization_profile
        
        # 检查是否为同一组织
        if obj.organization != user_org.organization:
            return False
        
        # 组织创建者或管理员有权限
        return user_org.permission in ['owner', 'admin']


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOrganizationUser])
def create_evaluation_criteria(request):
    """
    创建评分标准接口
    
    权限：组织用户
    功能：创建全新的评分标准，新标准默认状态为 active
    """
    serializer = EvaluationCriteriaCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                criteria = serializer.save()
                
                # 返回详细信息
                detail_serializer = EvaluationCriteriaDetailSerializer(
                    criteria,
                    context={'request': request}
                )
                return APIResponse.success(
                    data=detail_serializer.data,
                    message='评分标准创建成功',
                    code=201
                )
                
        except Exception as e:
            logger.error(f'创建评分标准失败: {str(e)}')
            return APIResponse.server_error(
                message=f'评分标准创建失败: {str(e)}'
            )
    
    return APIResponse.validation_error(
        errors=format_validation_errors(serializer.errors),
        message='数据验证失败'
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsOrganizationUser])
def list_evaluation_criteria(request):
    """
    获取评分标准列表接口
    
    权限：组织用户
    功能：分页查询评分标准，支持搜索，按状态、关联需求、创建者等筛选
    限制：组织用户只能访问本组织下的所有评分标准列表
    """
    # 获取用户组织
    user_org = request.user.organization_profile
    
    # 基础查询集 - 只查询本组织的评分标准
    queryset = EvaluationCriteria.objects.filter(
        organization=user_org.organization
    )
    
    # 搜索功能
    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # 状态筛选
    status_filter = request.GET.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # 关联需求筛选
    requirement_id = request.GET.get('requirement_id')
    if requirement_id:
        try:
            requirement_id = int(requirement_id)
            queryset = queryset.filter(requirement_id=requirement_id)
        except (ValueError, TypeError):
            pass
    
    # 创建者筛选
    creator_id = request.GET.get('creator_id')
    if creator_id:
        try:
            creator_id = int(creator_id)
            queryset = queryset.filter(creator_id=creator_id)
        except (ValueError, TypeError):
            pass
    
    # 模板筛选 - 支持获取模板列表功能
    is_template = request.GET.get('is_template')
    if is_template is not None:
        is_template_bool = is_template.lower() in ['true', '1', 'yes']
        if is_template_bool:
            # 当筛选模板时，使用模板专用的查询方法
            if hasattr(request.user, 'organization_profile'):
                user_org = request.user.organization_profile
                queryset = EvaluationCriteria.get_available_templates(organization=user_org.organization)
            else:
                queryset = queryset.filter(is_template=True)
            # 重新应用搜索条件（因为get_available_templates返回新的queryset）
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(description__icontains=search)
                )
        else:
            queryset = queryset.filter(is_template=False)
    
    # 使用状态筛选
    is_used_by_requirements = request.GET.get('is_used_by_requirements')
    if is_used_by_requirements is not None:
        is_used_bool = is_used_by_requirements.lower() in ['true', '1', 'yes']
        if is_used_bool:
            # 筛选已被需求使用的评分标准
            from project.models import Requirement
            used_criteria_ids = Requirement.objects.filter(
                evaluation_criteria__organization=user_org.organization
            ).values_list('evaluation_criteria_id', flat=True).distinct()
            queryset = queryset.filter(id__in=used_criteria_ids)
        else:
            # 筛选未被需求使用的评分标准
            from project.models import Requirement
            used_criteria_ids = Requirement.objects.filter(
                evaluation_criteria__organization=user_org.organization
            ).values_list('evaluation_criteria_id', flat=True).distinct()
            queryset = queryset.exclude(id__in=used_criteria_ids)
    
    # 排序
    ordering = request.GET.get('ordering', '-created_at')
    allowed_orderings = [
        'created_at', '-created_at',
        'updated_at', '-updated_at',
        'name', '-name',
        'status', '-status'
    ]
    if ordering in allowed_orderings:
        queryset = queryset.order_by(ordering)
    else:
        queryset = queryset.order_by('-created_at')
    
    # 分页
    pagination_data = paginate_queryset(request, queryset, default_page_size=20)
    paginator = pagination_data['paginator']
    page_data = pagination_data['page_data']
    
    # 序列化
    serializer = EvaluationCriteriaListSerializer(
        page_data,
        many=True,
        context={'request': request}
    )
    
    # 返回分页响应
    response_data = paginator.get_paginated_response_data(
        serializer.data,
        request
    )
    
    return APIResponse.success(
        data=response_data,
        message='获取评分标准列表成功'
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_evaluation_criteria_detail(request, criteria_id):
    """
    获取评分标准详情接口
    
    权限：学生用户可以访问所有评分标准详情，组织用户仅可访问本组织的评分标准详情
    功能：获取单个评分标准的完整信息，包含其关联的所有评分指标
    """
    criteria = get_object_or_404(
        EvaluationCriteria,
        id=criteria_id
    )
    
    # 权限检查
    user = request.user
    if user.user_type == 'student':
        # 学生用户可以访问所有评分标准详情
        pass
    elif user.user_type == 'organization':
        # 组织用户仅可访问本组织的评分标准详情
        if not hasattr(user, 'organization_profile'):
            return APIResponse.forbidden(
                message='您没有权限访问此评分标准'
            )
        
        user_org = user.organization_profile.organization
        if criteria.organization != user_org:
            return APIResponse.forbidden(
                message='您只能访问本组织的评分标准'
            )
    elif user.user_type == 'admin':
        # 管理员可以访问所有评分标准
        pass
    else:
        return APIResponse.forbidden(
            message='您没有权限访问此评分标准'
        )
    
    serializer = EvaluationCriteriaDetailSerializer(
        criteria,
        context={'request': request}
    )
    
    return APIResponse.success(
        data=serializer.data,
        message='获取评分标准详情成功'
    )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsOrganizationAdminOrCreator])
def update_evaluation_criteria(request, criteria_id):
    """
    更新评分标准基础信息接口
    
    权限：组织创建者、组织管理员、该评分标准创建者
    功能：仅更新评分标准的"非核心规则字段"（名称、描述、关联需求）
    限制：仅"草稿"或"启用"状态的可更新；若标准已关联"已提交/已公示"的项目评分，不可更新
    """
    user_org = request.user.organization_profile
    
    criteria = get_object_or_404(
        EvaluationCriteria,
        id=criteria_id,
        organization=user_org.organization
    )
    
    # 检查对象级权限
    permission = IsOrganizationAdminOrCreator()
    if not permission.has_object_permission(request, None, criteria):
        return APIResponse.forbidden(
            message='权限不足，只有组织管理员或评分标准创建者可以修改'
        )
    
    # 部分更新或完整更新
    partial = request.method == 'PATCH'
    serializer = EvaluationCriteriaUpdateSerializer(
        criteria,
        data=request.data,
        partial=partial,
        context={'request': request}
    )
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                updated_criteria = serializer.save()
                
                # 返回详细信息
                detail_serializer = EvaluationCriteriaDetailSerializer(
                    updated_criteria,
                    context={'request': request}
                )
                return APIResponse.success(
                    data=detail_serializer.data,
                    message='评分标准更新成功'
                )
                
        except ValidationError as e:
            return APIResponse.validation_error(
                errors={'non_field_errors': [str(e)]},
                message='业务规则验证失败'
            )
        except Exception as e:
            logger.error(f'更新评分标准失败: {str(e)}')
            return APIResponse.server_error(
                message=f'评分标准更新失败: {str(e)}'
            )
    
    return APIResponse.validation_error(
        errors=format_validation_errors(serializer.errors),
        message='数据验证失败'
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsOrganizationOwnerOrAdmin])
def update_evaluation_criteria_status(request, criteria_id):
    """
    切换评分标准状态接口
    
    权限：组织创建者、组织管理员
    功能：单独切换评分标准的状态，支持双向状态流转：active ↔ archived
    说明：支持在启用和归档状态之间自由切换
    """
    user_org = request.user.organization_profile
    
    criteria = get_object_or_404(
        EvaluationCriteria,
        id=criteria_id,
        organization=user_org.organization
    )
    
    # 检查对象级权限
    permission = IsOrganizationOwnerOrAdmin()
    if not permission.has_object_permission(request, None, criteria):
        return APIResponse.forbidden(
            message='权限不足，只有组织创建者或管理员可以切换状态'
        )
    
    serializer = EvaluationCriteriaStatusUpdateSerializer(
        criteria,
        data=request.data
    )
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                new_status = serializer.validated_data['status']
                criteria.status = new_status
                criteria.save(update_fields=['status', 'updated_at'])
                
                # 返回详细信息
                detail_serializer = EvaluationCriteriaDetailSerializer(
                    criteria,
                    context={'request': request}
                )
                return APIResponse.success(
                    data=detail_serializer.data,
                    message=f'评分标准状态已更新为{criteria.get_status_display()}'
                )
                
        except Exception as e:
            logger.error(f'更新评分标准状态失败: {str(e)}')
            return APIResponse.server_error(
                message=f'状态更新失败: {str(e)}'
            )
    
    return APIResponse.validation_error(
        errors=format_validation_errors(serializer.errors),
        message='数据验证失败'
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOrganizationUser])
def clone_evaluation_criteria(request):
    """
    复制评分标准生成新标准接口
    
    权限：组织用户
    功能：基于已有评分标准（源标准）复制生成新标准，复制内容包括所有关联指标
    """
    serializer = EvaluationCriteriaCloneSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                new_criteria = serializer.save()
                
                # 返回详细信息
                detail_serializer = EvaluationCriteriaDetailSerializer(
                    new_criteria,
                    context={'request': request}
                )
                return APIResponse.success(
                    data=detail_serializer.data,
                    message='评分标准复制成功',
                    code=201
                )
                
        except ValidationError as e:
            return APIResponse.validation_error(
                errors={'non_field_errors': [str(e)]},
                message='业务规则验证失败'
            )
        except Exception as e:
            logger.error(f'复制评分标准失败: {str(e)}')
            return APIResponse.server_error(
                message=f'评分标准复制失败: {str(e)}'
            )
    
    return APIResponse.validation_error(
        errors=format_validation_errors(serializer.errors),
        message='数据验证失败'
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsOrganizationAdminOrCreator])
def batch_update_evaluation_criteria_indicators(request, criteria_id):
    """
    批量更新评分标准下的多个指标接口
    
    权限：组织创建者、组织管理员、该评分标准创建者
    功能：一次性更新评分标准下的多个指标信息
    限制：仅状态为 active 的评分标准可修改指标；
          若评分标准已被用于项目评选，不可修改指标
    """
    user_org = request.user.organization_profile
    
    criteria = get_object_or_404(
        EvaluationCriteria,
        id=criteria_id,
        organization=user_org.organization
    )
    
    # 检查对象级权限
    permission = IsOrganizationAdminOrCreator()
    if not permission.has_object_permission(request, None, criteria):
        return APIResponse.forbidden(
            message='权限不足，只有组织管理员或评分标准创建者可以修改指标'
        )
    
    serializer = EvaluationCriteriaBatchIndicatorUpdateSerializer(
        data=request.data,
        context={'instance': criteria, 'request': request}
    )
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                indicators_data = serializer.validated_data['indicators']
                updated_indicators = serializer.update_indicators(criteria, indicators_data)
                
                # 返回更新后的指标列表
                result_serializer = EvaluationIndicatorSerializer(
                    updated_indicators,
                    many=True,
                    context={'request': request}
                )
                return APIResponse.success(
                    data=result_serializer.data,
                    message=f'成功更新 {len(updated_indicators)} 个评分指标'
                )
                
        except ValidationError as e:
            return APIResponse.validation_error(
                errors={'non_field_errors': [str(e)]},
                message='业务规则验证失败'
            )
        except Exception as e:
            logger.error(f'批量更新评分指标失败: {str(e)}')
            return APIResponse.server_error(
                message=f'评分指标批量更新失败: {str(e)}'
            )
    
    return APIResponse.validation_error(
        errors=format_validation_errors(serializer.errors),
        message='数据验证失败'
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsOrganizationAdminOrCreator])
def delete_evaluation_criteria(request, criteria_id):
    """
    删除评分标准接口
    
    权限：组织创建者、组织管理员、该评分标准创建者
    功能：物理删除评分标准
    限制：已关联"已提交/已公示"项目评分的标准不可删除
    """
    user_org = request.user.organization_profile
    
    criteria = get_object_or_404(
        EvaluationCriteria,
        id=criteria_id,
        organization=user_org.organization
    )
    
    # 检查对象级权限
    permission = IsOrganizationAdminOrCreator()
    if not permission.has_object_permission(request, None, criteria):
        return APIResponse.forbidden(
            message='权限不足，只有组织管理员或评分标准创建者可以删除'
        )
    
    # 检查是否可以删除
    if not criteria.can_be_modified():
        return APIResponse.validation_error(
            errors={'non_field_errors': ['该评分标准已用于项目评选，不可删除']},
            message='删除失败，评分标准已被使用'
        )
    
    try:
        with transaction.atomic():
            criteria_name = criteria.name
            criteria.delete()
            
            return APIResponse.success(
                message=f'评分标准 "{criteria_name}" 删除成功'
            )
            
    except Exception as e:
        logger.error(f'删除评分标准失败: {str(e)}')
        return APIResponse.server_error(
            message=f'评分标准删除失败: {str(e)}'
        )


# 注意：原来的 list_evaluation_criteria_templates 函数已被整合到 list_evaluation_criteria 中
# 通过 is_template=true 参数来获取模板列表


# ==================== 评分指标 CRUD 接口 ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOrganizationAdminOrCreator])
def create_evaluation_indicator(request, criteria_id):
    """
    创建评分指标接口
    
    权限：组织创建者、组织管理员、该评分标准创建者
    功能：为指定评分标准添加新的评分指标，支持单个或批量创建
    限制：仅状态为 active 的评分标准可添加指标；
          若评分标准已被用于项目评选，不可添加指标；
          所有指标权重总和必须 = 100%
    """
    user_org = request.user.organization_profile
    
    criteria = get_object_or_404(
        EvaluationCriteria,
        id=criteria_id,
        organization=user_org.organization
    )
    
    # 检查对象级权限
    permission = IsOrganizationAdminOrCreator()
    if not permission.has_object_permission(request, None, criteria):
        return APIResponse.forbidden(
            message='权限不足，只有组织管理员或评分标准创建者可以添加指标'
        )
    
    # 判断是单个创建还是批量创建
    if 'indicators' in request.data:
        # 批量创建
        serializer = EvaluationIndicatorBatchCreateSerializer(
            data=request.data,
            context={'criteria': criteria, 'request': request}
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    indicators = serializer.save()
                    
                    # 返回创建的指标列表
                    result_serializer = EvaluationIndicatorSerializer(
                        indicators,
                        many=True,
                        context={'request': request}
                    )
                    return APIResponse.success(
                        data=result_serializer.data,
                        message=f'成功创建 {len(indicators)} 个评分指标',
                        code=201
                    )
                    
            except Exception as e:
                logger.error(f'批量创建评分指标失败: {str(e)}')
                return APIResponse.server_error(
                    message=f'评分指标创建失败: {str(e)}'
                )
        
        return APIResponse.validation_error(
            errors=format_validation_errors(serializer.errors),
            message='数据验证失败'
        )
    
    else:
        # 单个创建
        serializer = EvaluationIndicatorCreateSerializer(
            data=request.data,
            context={'criteria': criteria, 'request': request}
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    indicator = serializer.save()
                    
                    # 返回创建的指标
                    result_serializer = EvaluationIndicatorSerializer(
                        indicator,
                        context={'request': request}
                    )
                    return APIResponse.success(
                        data=result_serializer.data,
                        message='评分指标创建成功',
                        code=201
                    )
                    
            except Exception as e:
                logger.error(f'创建评分指标失败: {str(e)}')
                return APIResponse.server_error(
                    message=f'评分指标创建失败: {str(e)}'
                )
        
        return APIResponse.validation_error(
            errors=format_validation_errors(serializer.errors),
            message='数据验证失败'
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_evaluation_indicators(request, criteria_id):
    """
    获取指标列表接口
    
    权限：学生用户可以访问所有评分标准的指标，组织用户仅可访问本组织的评分标准指标
    功能：获取指定评分标准下的所有评分指标，按 order 排序
    """
    # 获取评分标准
    criteria = get_object_or_404(
        EvaluationCriteria,
        id=criteria_id
    )
    
    # 权限检查
    user = request.user
    if user.user_type == 'student':
        # 学生用户可以访问所有评分标准的指标
        pass
    elif user.user_type == 'organization':
        # 组织用户仅可访问本组织的评分标准指标
        if not hasattr(user, 'organization_profile'):
            return APIResponse.forbidden(
                message='您没有权限访问此评分标准的指标'
            )
        
        user_org = user.organization_profile.organization
        if criteria.organization != user_org:
            return APIResponse.forbidden(
                message='您只能访问本组织的评分标准指标'
            )
    elif user.user_type == 'admin':
        # 管理员可以访问所有评分标准的指标
        pass
    else:
        return APIResponse.forbidden(
            message='您没有权限访问此评分标准的指标'
        )
    
    # 获取指标列表，按order排序
    indicators = criteria.indicators.all().order_by('order', 'id')
    
    # 序列化
    serializer = EvaluationIndicatorSerializer(
        indicators,
        many=True,
        context={'request': request}
    )
    
    return APIResponse.success(
        data=serializer.data,
        message='获取评分指标列表成功'
    )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsOrganizationAdminOrCreator])
def update_evaluation_indicator(request, criteria_id, indicator_id):
    """
    更新指标接口
    
    权限：组织创建者、组织管理员、该评分标准创建者
    功能：更新评分指标的信息，支持全量更新（PUT）或部分更新（PATCH）
    限制：仅状态为 active 的评分标准可修改指标；
          若评分标准已被用于项目评选，不可修改指标；
          权重更新后需保证所有指标总和 = 100%
    """
    user_org = request.user.organization_profile
    
    criteria = get_object_or_404(
        EvaluationCriteria,
        id=criteria_id,
        organization=user_org.organization
    )
    
    indicator = get_object_or_404(
        EvaluationIndicator,
        id=indicator_id,
        criteria=criteria
    )
    
    # 检查对象级权限
    permission = IsOrganizationAdminOrCreator()
    if not permission.has_object_permission(request, None, criteria):
        return APIResponse.forbidden(
            message='权限不足，只有组织管理员或评分标准创建者可以修改指标'
        )
    
    # 部分更新或完整更新
    partial = request.method == 'PATCH'
    serializer = EvaluationIndicatorUpdateSerializer(
        indicator,
        data=request.data,
        partial=partial,
        context={'request': request}
    )
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                updated_indicator = serializer.save()
                
                # 返回更新后的指标
                result_serializer = EvaluationIndicatorSerializer(
                    updated_indicator,
                    context={'request': request}
                )
                return APIResponse.success(
                    data=result_serializer.data,
                    message='评分指标更新成功'
                )
                
        except ValidationError as e:
            return APIResponse.validation_error(
                errors={'non_field_errors': [str(e)]},
                message='业务规则验证失败'
            )
        except Exception as e:
            logger.error(f'更新评分指标失败: {str(e)}')
            return APIResponse.server_error(
                message=f'评分指标更新失败: {str(e)}'
            )
    
    return APIResponse.validation_error(
        errors=format_validation_errors(serializer.errors),
        message='数据验证失败'
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsOrganizationAdminOrCreator])
def delete_evaluation_indicator(request, criteria_id, indicator_id):
    """
    删除指标接口
    
    权限：组织创建者、组织管理员、该评分标准创建者
    功能：删除指定评分指标（物理删除）
    限制：仅状态为 active 的评分标准可删除指标；
          若评分标准已被用于项目评选，不可删除指标；
          已被 IndicatorScore 引用的指标不可删除；
          删除后需保证剩余指标权重总和 = 100%
    """
    user_org = request.user.organization_profile
    
    criteria = get_object_or_404(
        EvaluationCriteria,
        id=criteria_id,
        organization=user_org.organization
    )
    
    indicator = get_object_or_404(
        EvaluationIndicator,
        id=indicator_id,
        criteria=criteria
    )
    
    # 检查对象级权限
    permission = IsOrganizationAdminOrCreator()
    if not permission.has_object_permission(request, None, criteria):
        return APIResponse.forbidden(
            message='权限不足，只有组织管理员或评分标准创建者可以删除指标'
        )
    
    # 检查评分标准状态
    if criteria.status != 'active':
        return APIResponse.validation_error(
            errors={'non_field_errors': ['只有启用状态的评分标准可以删除指标']},
            message='删除失败，评分标准状态不允许'
        )
    
    # 检查是否已被使用
    if not criteria.can_be_modified():
        return APIResponse.validation_error(
            errors={'non_field_errors': ['该评分标准已用于项目评选，不可删除指标']},
            message='删除失败，评分标准已被使用'
        )
    
    # 检查是否被 IndicatorScore 引用
    if hasattr(indicator, 'indicator_scores') and indicator.indicator_scores.exists():
        return APIResponse.validation_error(
            errors={'non_field_errors': ['该指标已被评分记录引用，不可删除']},
            message='删除失败，指标已被使用'
        )
    
    # 注意：删除指标后权重总和可能不为100%，这是允许的
    # 用户可以在后续操作中调整其他指标的权重
    
    try:
        with transaction.atomic():
            indicator_name = indicator.name
            indicator.delete()
            
            return APIResponse.success(
                message=f'评分指标 "{indicator_name}" 删除成功'
            )
            
    except Exception as e:
        logger.error(f'删除评分指标失败: {str(e)}')
        return APIResponse.server_error(
            message=f'评分指标删除失败: {str(e)}'
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsOrganizationAdminOrCreator])
def batch_delete_evaluation_indicators(request, criteria_id):
    """
    批量删除评分指标接口
    
    权限：组织创建者、组织管理员、该评分标准创建者
    功能：批量删除指定的评分指标（物理删除）
    限制：仅状态为 active 的评分标准可删除指标；
          若评分标准已被用于项目评选，不可删除指标；
          已被 IndicatorScore 引用的指标不可删除；
    错误处理策略：策略B - 部分成功处理，返回成功和失败的详细信息
    """
    user_org = request.user.organization_profile
    
    criteria = get_object_or_404(
        EvaluationCriteria,
        id=criteria_id,
        organization=user_org.organization
    )
    
    # 检查对象级权限
    permission = IsOrganizationAdminOrCreator()
    if not permission.has_object_permission(request, None, criteria):
        return APIResponse.forbidden(
            message='权限不足，只有组织管理员或评分标准创建者可以删除指标'
        )
    
    # 检查评分标准状态
    if criteria.status != 'active':
        return APIResponse.validation_error(
            errors={'non_field_errors': ['只有启用状态的评分标准可以删除指标']},
            message='删除失败，评分标准状态不允许'
        )
    
    # 检查是否已被使用
    if not criteria.can_be_modified():
        return APIResponse.validation_error(
            errors={'non_field_errors': ['该评分标准已用于项目评选，不可删除指标']},
            message='删除失败，评分标准已被使用'
        )
    
    # 获取indicator_ids参数
    indicator_ids_str = request.data.get('indicator_ids', '')
    if not indicator_ids_str:
        return APIResponse.validation_error(
            errors={'indicator_ids': ['indicator_ids字段为必填项']},
            message='参数验证失败'
        )
    
    # 解析indicator_ids
    try:
        indicator_ids = [int(id_str.strip()) for id_str in indicator_ids_str.split(',') if id_str.strip()]
        if not indicator_ids:
            return APIResponse.validation_error(
                errors={'indicator_ids': ['indicator_ids不能为空']},
                message='参数验证失败'
            )
    except ValueError:
        return APIResponse.validation_error(
            errors={'indicator_ids': ['indicator_ids格式错误，应为逗号分隔的数字']},
            message='参数验证失败'
        )
    
    # 获取要删除的指标
    indicators = EvaluationIndicator.objects.filter(
        id__in=indicator_ids,
        criteria=criteria
    )
    
    # 检查指标是否存在
    found_ids = set(indicators.values_list('id', flat=True))
    missing_ids = set(indicator_ids) - found_ids
    
    success_results = []
    error_results = []
    
    # 处理每个指标
    for indicator in indicators:
        try:
            # 检查是否被 IndicatorScore 引用
            if hasattr(indicator, 'indicator_scores') and indicator.indicator_scores.exists():
                error_results.append({
                    'id': indicator.id,
                    'name': indicator.name,
                    'error': '该指标已被评分记录引用，不可删除'
                })
                continue
            
            # 删除指标
            with transaction.atomic():
                indicator_name = indicator.name
                indicator_id = indicator.id
                indicator.delete()
                
                success_results.append({
                    'id': indicator_id,
                    'name': indicator_name,
                    'message': '删除成功'
                })
                
        except Exception as e:
            logger.error(f'删除评分指标 {indicator.id} 失败: {str(e)}')
            error_results.append({
                'id': indicator.id,
                'name': indicator.name,
                'error': f'删除失败: {str(e)}'
            })
    
    # 处理不存在的指标ID
    for missing_id in missing_ids:
        error_results.append({
            'id': missing_id,
            'name': None,
            'error': '指标不存在或不属于该评分标准'
        })
    
    # 构建响应
    total_count = len(indicator_ids)
    success_count = len(success_results)
    error_count = len(error_results)
    
    response_data = {
        'total_count': total_count,
        'success_count': success_count,
        'error_count': error_count,
        'success_results': success_results,
        'error_results': error_results
    }
    
    if success_count > 0 and error_count == 0:
        # 全部成功
        return APIResponse.success(
            data=response_data,
            message=f'批量删除成功，共删除 {success_count} 个评分指标'
        )
    elif success_count > 0 and error_count > 0:
        # 部分成功
        return APIResponse.success(
            data=response_data,
            message=f'批量删除部分成功，成功删除 {success_count} 个，失败 {error_count} 个',
            code=207  # 207 Multi-Status
        )
    else:
        # 全部失败
        return APIResponse.validation_error(
            errors=response_data,
            message=f'批量删除失败，共 {error_count} 个指标删除失败'
        )


# ==================== 项目评分管理接口 ====================

class IsProjectEvaluationPermission(permissions.BasePermission):
    """项目评分权限检查"""
    
    def has_permission(self, request, view):
        """检查基础权限"""
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """检查对象级权限"""
        if not request.user.is_authenticated:
            return False
        
        # 获取项目和需求信息
        project = obj.project if hasattr(obj, 'project') else obj
        requirement = project.requirement
        
        # 组织用户权限检查
        if request.user.user_type == 'organization':
            if not hasattr(request.user, 'organization_profile'):
                return False
            
            user_org = request.user.organization_profile
            
            # 检查是否为组织创建者或管理员
            if user_org.permission in ['owner', 'admin']:
                return True
            
            # 检查是否为需求创建者
            if requirement.publish_people.user == request.user:
                return True
            
            # 检查是否为评分创建者（仅对ProjectEvaluation对象）
            if hasattr(obj, 'evaluator') and obj.evaluator == request.user:
                return True
        
        return False


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_project_evaluation(request, project_id):
    """
    创建项目评分接口
    
    权限：组织创建者、组织管理员、该需求创建者
    功能：为已完成的项目创建评分记录，支持同时完成所有指标评分
    """
    # 获取项目
    project = get_object_or_404(
        StudentProject,
        id=project_id
    )
    
    # 通过项目获取关联的需求和评分标准
    requirement = project.requirement
    if not requirement.evaluation_criteria:
        return APIResponse.validation_error(
            errors={'requirement': ['该项目关联的需求未设置评分标准']},
            message='需求未设置评分标准'
        )
    
    criteria = requirement.evaluation_criteria
    
    # 检查项目状态
    if project.status != 'completed':
        return APIResponse.validation_error(
            errors={'project': ['只能为已完成的项目创建评分']},
            message='项目状态不符合要求'
        )
    
    # 检查评分标准状态
    if criteria.status != 'active':
        return APIResponse.validation_error(
            errors={'criteria': ['只能使用启用状态的评分标准']},
            message='评分标准状态不符合要求'
        )
    
    # 检查是否已存在评分记录
    existing_evaluation = ProjectEvaluation.objects.filter(
        project=project,
        criteria=criteria,
        evaluator=request.user
    ).first()
    
    if existing_evaluation:
        return APIResponse.validation_error(
            errors={'non_field_errors': ['该项目已存在评分记录']},
            message='评分记录已存在'
        )
    
    # 准备数据
    data = request.data.copy()
    data['project'] = project_id
    data['criteria'] = criteria.id
    
    serializer = ProjectEvaluationCreateSerializer(
        data=data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                evaluation = serializer.save()
                
                # 返回详细信息
                detail_serializer = ProjectEvaluationDetailSerializer(
                    evaluation,
                    context={'request': request}
                )
                return APIResponse.success(
                    data=detail_serializer.data,
                    message='项目评分创建成功',
                    code=201
                )
                
        except Exception as e:
            logger.error(f'创建项目评分失败: {str(e)}')
            return APIResponse.server_error(
                message=f'项目评分创建失败: {str(e)}'
            )
    
    return APIResponse.validation_error(
        errors=format_validation_errors(serializer.errors),
        message='数据验证失败'
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_project_evaluation_detail(request, project_id):
    """
    获取项目评分详情接口
    
    权限：认证用户
    功能：获取指定项目的评分详细信息
    """
    # 获取项目
    project = get_object_or_404(
        StudentProject,
        id=project_id
    )
    
    # 获取该项目的评分记录（一个项目对应一个评分）
    evaluation = get_object_or_404(
        ProjectEvaluation,
        project=project
    )
    
    serializer = ProjectEvaluationDetailSerializer(
        evaluation,
        context={'request': request}
    )
    
    return APIResponse.success(
        data=serializer.data,
        message='获取项目评分详情成功'
    )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsProjectEvaluationPermission])
def update_project_evaluation(request, project_id):
    """
    更新项目评分接口
    
    权限：组织创建者、组织管理员、该评分创建者
    功能：批量更新多个评分指标的分数和评语
    """
    # 获取项目
    project = get_object_or_404(
        StudentProject,
        id=project_id
    )
    
    # 获取该项目的评分记录
    evaluation = get_object_or_404(
        ProjectEvaluation,
        project=project
    )
    
    # 检查对象级权限
    permission = IsProjectEvaluationPermission()
    if not permission.has_object_permission(request, None, evaluation):
        return APIResponse.forbidden(
            message='权限不足，只有组织管理员、需求创建者或评分创建者可以修改'
        )
    
    # 检查评分状态
    if evaluation.status == 'published':
        return APIResponse.validation_error(
            errors={'non_field_errors': ['已公示的评分不可修改']},
            message='修改失败，评分已公示'
        )
    
    # 部分更新或完整更新
    partial = request.method == 'PATCH'
    serializer = ProjectEvaluationUpdateSerializer(
        evaluation,
        data=request.data,
        partial=partial,
        context={'request': request}
    )
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                updated_evaluation = serializer.save()
                
                # 返回详细信息
                detail_serializer = ProjectEvaluationDetailSerializer(
                    updated_evaluation,
                    context={'request': request}
                )
                return APIResponse.success(
                    data=detail_serializer.data,
                    message='项目评分更新成功'
                )
                
        except Exception as e:
            logger.error(f'更新项目评分失败: {str(e)}')
            return APIResponse.server_error(
                message=f'项目评分更新失败: {str(e)}'
            )
    
    return APIResponse.validation_error(
        errors=format_validation_errors(serializer.errors),
        message='数据验证失败'
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsProjectEvaluationPermission])
def submit_project_evaluation(request, project_id):
    """
    提交项目评分接口
    
    权限：组织创建者、组织管理员、该评分创建者
    功能：检查该项目对应评分标准下所有的必填评分指标已完全填写，然后把状态改为submitted
    """
    # 获取项目
    project = get_object_or_404(
        StudentProject,
        id=project_id
    )
    
    # 获取该项目的评分记录
    evaluation = get_object_or_404(
        ProjectEvaluation,
        project=project
    )
    
    # 检查对象级权限
    permission = IsProjectEvaluationPermission()
    if not permission.has_object_permission(request, None, evaluation):
        return APIResponse.forbidden(
            message='权限不足，只有组织管理员、需求创建者或评分创建者可以提交评分'
        )
    
    # 检查评分状态
    if evaluation.status != 'draft':
        return APIResponse.validation_error(
            errors={'non_field_errors': ['只有草稿状态的评分可以提交']},
            message='提交失败，评分状态不正确'
        )
    
    # 检查必填指标是否已完全填写
    required_indicators = evaluation.criteria.indicators.filter(is_required=True)
    completed_scores = evaluation.indicator_scores.filter(
        indicator__is_required=True,
        score__isnull=False
    )
    
    if required_indicators.count() != completed_scores.count():
        missing_indicators = required_indicators.exclude(
            id__in=completed_scores.values_list('indicator_id', flat=True)
        )
        missing_names = list(missing_indicators.values_list('name', flat=True))
        
        return APIResponse.validation_error(
            errors={'non_field_errors': [f'以下必填指标尚未评分：{", ".join(missing_names)}']},
            message='提交失败，存在未完成的必填指标'
        )
    
    try:
        with transaction.atomic():
            # 更新状态为已提交
            evaluation.status = 'submitted'
            evaluation.submitted_at = timezone.now()
            evaluation.save(update_fields=['status', 'submitted_at'])
            
            # 重新计算分数
            evaluation.calculate_scores()
            evaluation.save(update_fields=['total_score', 'weighted_score'])
            
            # 返回详细信息
            detail_serializer = ProjectEvaluationDetailSerializer(
                evaluation,
                context={'request': request}
            )
            return APIResponse.success(
                data=detail_serializer.data,
                message='项目评分提交成功'
            )
            
    except Exception as e:
        logger.error(f'提交项目评分失败: {str(e)}')
        return APIResponse.server_error(
            message=f'项目评分提交失败: {str(e)}'
        )


class IsRequirementRankingPermission(permissions.BasePermission):
    """项目排名公示权限检查"""
    
    def has_permission(self, request, view):
        """检查基础权限"""
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """检查对象级权限"""
        if not request.user.is_authenticated:
            return False
        
        # 获取需求对象
        requirement = obj if hasattr(obj, 'organization') else None
        if not requirement:
            return False
        
        # 组织用户权限检查
        if request.user.user_type == 'organization':
            if not hasattr(request.user, 'organization_profile'):
                return False
            
            user_org = request.user.organization_profile
            
            # 检查是否为同一组织
            if requirement.organization != user_org.organization:
                return False
            
            # 检查是否为组织创建者或管理员
            if user_org.permission in ['owner', 'admin']:
                return True
            
            # 检查是否为需求创建者
            if requirement.publish_people == user_org:
                return True
        
        return False


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_project_ranking(request, requirement_id):
    """
    获取需求下已评分项目排名接口（公示功能）
    
    权限：需求对应组织的组织创建者、组织管理员和需求创建者
    功能：获取指定需求下已完成并评分的项目排名，同时实现公示机制
    限制：只能在需求截止日期后调用，调用成功后将所有已完成并评分的ProjectEvaluation状态改为published
    """
    requirement = get_object_or_404(
        Requirement,
        id=requirement_id
    )
    
    # 检查权限
    permission_checker = IsRequirementRankingPermission()
    if not permission_checker.has_object_permission(request, None, requirement):
        return APIResponse.error(
            message='您没有权限公示此需求的项目排名',
            code=403
        )
    
    # 检查需求截止时间
    if requirement.finish_time and timezone.now().date() < requirement.finish_time:
        return APIResponse.validation_error(
            errors={'non_field_errors': ['需求尚未截止，无法查看排名']},
            message=f'排名将在需求截止后（{requirement.finish_time.strftime("%Y-%m-%d")}）公布'
        )
    
    # 获取已完成并评分的项目
    projects = StudentProject.objects.filter(
        requirement=requirement,
        status='completed',
        is_evaluated=True
    ).select_related('requirement').prefetch_related(
        'evaluations__criteria',
        'evaluations__indicator_scores__indicator'
    )
    
    # 计算排名
    project_scores = []
    for project in projects:
        # 获取最新的评分记录
        latest_evaluation = project.evaluations.order_by('-created_at').first()
        
        if latest_evaluation:
            project_scores.append({
                'project': project,
                'evaluation': latest_evaluation,
                'weighted_total_score': latest_evaluation.weighted_score or 0
            })
    
    # 按加权总分排序
    project_scores.sort(key=lambda x: x['weighted_total_score'], reverse=True)
    
    # 添加排名
    for i, item in enumerate(project_scores):
        item['rank'] = i + 1
    
    try:
        with transaction.atomic():
            # 公示机制：将所有已完成并评分的ProjectEvaluation状态改为published
            evaluations_to_publish = ProjectEvaluation.objects.filter(
                project__requirement=requirement,
                project__status='completed',
                project__is_evaluated=True,
                status='submitted'
            )
            
            published_count = evaluations_to_publish.update(
                status='published',
                published_at=timezone.now()
            )
            
            # 更新需求的evaluation_published字段
            if not requirement.evaluation_published:
                requirement.evaluation_published = True
                requirement.save(update_fields=['evaluation_published'])
            
            # 创建或更新ProjectRanking记录
            ranking_objects = []
            for item in project_scores:
                project = item['project']
                evaluation = item['evaluation']
                rank = item['rank']
                final_score = item['weighted_total_score']
                
                # 获取或创建ProjectRanking对象
                ranking, created = ProjectRanking.objects.get_or_create(
                    project=project,
                    criteria=evaluation.criteria,
                    defaults={
                        'rank': rank,
                        'final_score': final_score
                    }
                )
                
                # 如果已存在，更新排名和分数
                if not created:
                    ranking.rank = rank
                    ranking.final_score = final_score
                    ranking.save(update_fields=['rank', 'final_score', 'updated_at'])
                
                ranking_objects.append(ranking)
            
            # 序列化ProjectRanking对象
            serializer = ProjectRankingSerializer(
                ranking_objects,
                many=True,
                context={'request': request}
            )
            
            # 发送项目评分公示通知给所有项目成员
            for item in project_scores:
                project = item['project']
                rank = item['rank']
                final_score = item['weighted_total_score']
                
                try:
                    # 获取项目所有成员
                    from studentproject.models import ProjectParticipant
                    project_members = User.objects.filter(
                        student_profile__project_participations__project=project,
                        student_profile__project_participations__status='approved'
                    ).distinct()
                    
                    student_notification_service.send_project_score_published_notification(
                        members=list(project_members),
                        project=project,
                        total_score=final_score,
                        weighted_score=final_score
                    )
                except Exception as e:
                    logger.error(f'发送项目评分公示通知失败 - 项目ID: {project.id}, 错误: {str(e)}')
            
            return APIResponse.success(
                data={
                    'requirement': {
                        'id': requirement.id,
                        'title': requirement.title,
                        'evaluation_published': requirement.evaluation_published
                    },
                    'projects': serializer.data,
                    'total_count': len(project_scores),
                    'published_evaluations_count': published_count
                },
                message=f'项目排名公示成功，共公示{published_count}个评分记录'
            )
            
    except Exception as e:
        logger.error(f'公示项目排名失败: {str(e)}')
        return APIResponse.server_error(
            message=f'公示项目排名失败: {str(e)}'
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_project_ranking(request, requirement_id):
    """
    查看需求下项目排名接口（纯展示功能）
    
    权限：认证用户
    功能：查看指定需求下已公示的项目排名结果
    限制：只能查看已公示的排名（evaluation_published=True）
    """
    requirement = get_object_or_404(
        Requirement,
        id=requirement_id
    )
    
    # 检查是否已公示
    if not requirement.evaluation_published:
        return APIResponse.validation_error(
            errors={'non_field_errors': ['该需求的项目排名尚未公示']},
            message='排名尚未公示，请等待管理员公示后查看'
        )
    
    try:
        # 获取已公示的ProjectRanking记录
        rankings = ProjectRanking.objects.filter(
            project__requirement=requirement
        ).select_related(
            'project__requirement',
            'criteria'
        ).prefetch_related(
            'project__evaluations__criteria',
            'project__evaluations__indicator_scores__indicator'
        ).order_by('rank')
        
        if not rankings.exists():
            return APIResponse.success(
                data={
                    'requirement': {
                        'id': requirement.id,
                        'title': requirement.title,
                        'evaluation_published': requirement.evaluation_published
                    },
                    'projects': [],
                    'total_count': 0
                },
                message='该需求下暂无项目排名记录'
            )
        
        # 序列化排名数据
        serializer = ProjectRankingSerializer(
            rankings,
            many=True,
            context={'request': request}
        )
        
        return APIResponse.success(
            data={
                'requirement': {
                    'id': requirement.id,
                    'title': requirement.title,
                    'evaluation_published': requirement.evaluation_published
                },
                'projects': serializer.data,
                'total_count': rankings.count()
            },
            message='项目排名获取成功'
        )
        
    except Exception as e:
        logger.error(f'获取项目排名失败: {str(e)}')
        return APIResponse.server_error(
            message=f'获取项目排名失败: {str(e)}'
        )
