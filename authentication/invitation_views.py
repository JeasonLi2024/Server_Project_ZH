from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from user.models import OrganizationUser
from organization.models import Organization
from .models import OrganizationInvitationCode
from .serializers import (
    OrganizationInvitationCodeSerializer,
    InvitationCodeGenerateSerializer,
    InvitationCodeValidateSerializer
)
from .invitation_utils import (
    create_invitation_code,
    get_organization_invitation_code,
    get_invitation_code_info,
    validate_invitation_code
)
from common_utils import APIResponse, format_validation_errors


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_invitation_code(request):
    """
    生成组织邀请码
    权限：只有企业创建者和管理员可以生成
    """
    try:
        # 获取用户的组织关系
        org_user = OrganizationUser.objects.get(
            user=request.user,
            status='approved'
        )
        
        # 检查权限：只有owner和admin可以生成邀请码
        if org_user.permission not in ['owner', 'admin']:
            return APIResponse.forbidden('权限不足，只有企业创建者和管理员可以生成邀请码')
        
        organization = org_user.organization
        
        # 验证请求数据
        serializer = InvitationCodeGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(
                format_validation_errors(serializer.errors),
                '请求参数无效'
            )
        
        expire_days = serializer.validated_data.get('expire_days', 30)
        max_uses = serializer.validated_data.get('max_uses', 100)
        
        # 生成邀请码
        success, invitation_code, message = create_invitation_code(
            organization_id=organization.id,
            created_by_user=request.user,
            expire_days=expire_days,
            max_uses=max_uses
        )
        
        if not success:
            return APIResponse.error(f'邀请码生成失败：{message}')
        
        # 序列化返回结果
        serializer = OrganizationInvitationCodeSerializer(invitation_code)
        
        return APIResponse.success(serializer.data, '邀请码生成成功', 201)
        
    except OrganizationUser.DoesNotExist:
        return APIResponse.error('您不属于任何组织')
    except Exception as e:
        return APIResponse.server_error(f'服务器内部错误：{str(e)}')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_invitation_code(request):
    """
    获取组织的邀请码信息
    权限：该企业所有成员都有权限查看
    """
    try:
        # 获取用户的组织关系
        org_user = OrganizationUser.objects.get(
            user=request.user,
            status='approved'
        )
        
        organization = org_user.organization
        
        # 获取当前活跃的邀请码
        invitation_code = get_organization_invitation_code(organization)
        
        if not invitation_code:
            return APIResponse.success(None, '当前组织没有活跃的邀请码')
        
        # 序列化返回结果
        serializer = OrganizationInvitationCodeSerializer(invitation_code)
        
        return APIResponse.success(serializer.data, '获取邀请码成功')
        
    except OrganizationUser.DoesNotExist:
        return APIResponse.error('您不属于任何组织')
    except Exception as e:
        return APIResponse.server_error(f'服务器内部错误：{str(e)}')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_invitation_code_history(request):
    """
    获取组织的邀请码历史记录
    权限：只有企业创建者和管理员可以查看历史记录
    """
    try:
        # 获取用户的组织关系
        org_user = OrganizationUser.objects.get(
            user=request.user,
            status='approved'
        )
        
        # 检查权限：只有owner和admin可以查看历史记录
        if org_user.permission not in ['owner', 'admin']:
            return APIResponse.forbidden('权限不足，只有企业创建者和管理员可以查看邀请码历史')
        
        organization = org_user.organization
        
        # 获取邀请码历史记录
        invitation_codes = OrganizationInvitationCode.objects.filter(
            organization=organization
        ).order_by('-created_at')
        
        # 序列化返回结果
        serializer = OrganizationInvitationCodeSerializer(invitation_codes, many=True)
        
        return APIResponse.success({
            'invitation_codes': serializer.data,
            'count': invitation_codes.count()
        }, '获取邀请码历史成功')
        
    except OrganizationUser.DoesNotExist:
        return APIResponse.error('您不属于任何组织')
    except Exception as e:
        return APIResponse.server_error(f'服务器内部错误：{str(e)}')


@api_view(['POST'])
def validate_invitation_code_view(request):
    """
    验证邀请码（公开接口，用于注册时验证）
    """
    try:
        # 验证请求数据
        serializer = InvitationCodeValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(
                format_validation_errors(serializer.errors),
                '请求参数无效'
            )
        
        code = serializer.validated_data['code']
        
        # 验证邀请码
        is_valid, message, organization = validate_invitation_code(code)
        
        if not is_valid:
            return APIResponse.error(message)
        
        # 获取邀请码详细信息
        invitation_code = get_invitation_code_info(code)
        
        return APIResponse.success({
            'valid': True,
            'organization_id': organization.id,
            'organization_name': organization.name,
            'organization_type': organization.organization_type,
            'invitation_code': {
                'code': invitation_code.code,
                'expires_at': invitation_code.expires_at,
                'used_count': invitation_code.used_count,
                'max_uses': invitation_code.max_uses,
                'remaining_uses': invitation_code.max_uses - invitation_code.used_count
            }
        }, '邀请码验证成功')
        
    except Exception as e:
        return APIResponse.server_error(f'服务器内部错误：{str(e)}')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disable_invitation_code(request):
    """
    禁用当前组织的邀请码
    权限：只有企业创建者和管理员可以禁用
    """
    try:
        # 获取用户的组织关系
        org_user = OrganizationUser.objects.get(
            user=request.user,
            status='approved'
        )
        
        # 检查权限：只有owner和admin可以禁用邀请码
        if org_user.permission not in ['owner', 'admin']:
            return APIResponse.forbidden('权限不足，只有企业创建者和管理员可以禁用邀请码')
        
        organization = org_user.organization
        
        # 获取当前活跃的邀请码
        invitation_code = get_organization_invitation_code(organization)
        
        if not invitation_code:
            return APIResponse.error('当前组织没有活跃的邀请码')
        
        # 禁用邀请码
        invitation_code.disable_code()
        
        return APIResponse.success(None, '邀请码已成功禁用')
        
    except OrganizationUser.DoesNotExist:
        return APIResponse.error('您不属于任何组织')
    except Exception as e:
        return APIResponse.server_error(f'服务器内部错误：{str(e)}')