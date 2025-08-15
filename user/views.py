from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout as django_logout
from django.utils import timezone
import logging

from .models import User
from .serializers import UserProfileSerializer, UserUpdateSerializer, AvatarUploadSerializer
from common_utils import APIResponse, format_validation_errors, build_media_url

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """获取用户资料"""
    try:
        # 使用select_related优化查询
        user = User.objects.select_related(
            'student_profile',
            'organization_profile__organization'
        ).get(id=request.user.id)
        
        serializer = UserProfileSerializer(user, context={'request': request})
        
        return APIResponse.success(serializer.data)
        
    except User.DoesNotExist:
        return APIResponse.not_found('用户不存在')
    except Exception as e:
        logger.error(f"获取用户资料失败: {str(e)}")
        return APIResponse.server_error('获取用户资料失败，请稍后重试')


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """更新用户资料"""
    try:
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return APIResponse.validation_error(
                format_validation_errors(serializer.errors)
            )
        
        # 保存更新
        updated_user = serializer.save()
        
        # 重新获取用户数据，使用select_related优化查询
        updated_user = User.objects.select_related(
            'student_profile',
            'organization_profile__organization'
        ).get(id=updated_user.id)
        
        # 使用UserProfileSerializer返回完整的用户资料格式
        profile_serializer = UserProfileSerializer(updated_user, context={'request': request})
        
        return APIResponse.success(profile_serializer.data, '资料更新成功')
        
    except Exception as e:
        logger.error(f"更新用户资料失败: {str(e)}")
        return APIResponse.server_error('更新用户资料失败，请稍后重试')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_avatar(request):
    """上传用户头像"""
    user = request.user
    
    # 检查是否有文件上传
    if 'avatar' not in request.FILES:
        return APIResponse.error('请选择要上传的头像文件', code=400)
    
    # 使用序列化器验证和处理文件
    serializer = AvatarUploadSerializer(user, data=request.data, partial=True)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    try:
        # 保存头像
        updated_user = serializer.save()
        
        # 构建头像URL
        return APIResponse.success({
            'avatar': build_media_url(updated_user.avatar, request),
            'message': '头像上传成功'
        }, '头像上传成功')
        
    except Exception as e:
        logger.error(f"头像上传失败: {str(e)}")
        return APIResponse.error('头像上传失败，请稍后重试', code=500)
