from django.conf import settings
from rest_framework import serializers
from django.contrib.auth import get_user_model
from common_utils import build_media_url
from .models import StudentProject
import os

User = get_user_model()


class StudentBasicFieldsMixin(serializers.Serializer):
    """学生基础字段 Mixin"""
    real_name = serializers.CharField(source='user.real_name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj):
        """获取头像URL"""
        if hasattr(obj, 'user') and obj.user and obj.user.avatar:
            request = self.context.get('request')
            return build_media_url(obj.user.avatar.url, request)
        return None


class ReviewMixin(serializers.Serializer):
    """审核相关字段 Mixin"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    review_message = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="审核消息，如果不提供将使用默认消息"
    )

    def validate_action(self, value):
        """验证审核动作"""
        if value not in ['approve', 'reject']:
            raise serializers.ValidationError("审核动作必须是 'approve' 或 'reject'")
        return value


class CloudLinkMixin(serializers.Serializer):
    """云盘链接相关字段 Mixin"""
    cloud_links = serializers.CharField(
        write_only=True,
        required=False,
        help_text="网盘链接地址，直接存储链接URL"
    )
    cloud_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="网盘链接提取密码（可选）"
    )
    virtual_folder_path = serializers.CharField(
        write_only=True,
        required=False,
        default="/",
        help_text="虚拟文件夹路径，文件将上传到此路径下"
    )

    def validate_cloud_links(self, value):
        """验证网盘链接格式"""
        if value:
            # 简单的URL格式验证
            if not (value.startswith('http://') or value.startswith('https://')):
                raise serializers.ValidationError("网盘链接必须是有效的URL格式")

            # 检查是否为常见网盘链接
            valid_domains = ['pan.baidu.com', 'cloud.189.cn', 'pan.xunlei.com', 'drive.google.com']
            if not any(domain in value for domain in valid_domains):
                raise serializers.ValidationError("请提供有效的网盘链接")

        return value


class AuthorInfoMixin:
    """作者信息处理 Mixin"""

    def get_author_info(self, obj):
        """获取作者信息"""
        if hasattr(obj, 'author') and obj.author:
            try:
                student = obj.author.student_profile
                return {
                    'id': student.id,
                    'real_name': obj.author.real_name,
                    'username': obj.author.username,
                    'avatar': self._get_avatar_url(obj.author),
                    'student_id': student.student_id
                }
            except AttributeError:
                return {
                    'id': obj.author.id,
                    'real_name': obj.author.real_name,
                    'username': obj.author.username,
                    'avatar': self._get_avatar_url(obj.author)
                }
        return None

    def _get_avatar_url(self, user):
        """获取头像URL"""
        if user and user.avatar:
            request = self.context.get('request')
            return build_media_url(user.avatar.url, request)
        return None


class AvatarMixin:
    """提供头像URL获取功能的Mixin类"""

    def get_avatar(self, obj):
        """获取用户头像URL"""
        if hasattr(obj, 'avatar') and obj.avatar:
            return obj.avatar.url
        elif hasattr(obj, 'user') and hasattr(obj.user, 'avatar') and obj.user.avatar:
            return obj.user.avatar.url
        elif hasattr(obj, 'student') and hasattr(obj.student, 'avatar') and obj.student.avatar:
            return obj.student.avatar.url
        return None


class FilesMixin:
    """提供文件列表获取功能的Mixin类"""

    def get_files(self, obj):
        """获取项目成果文件列表"""
        if hasattr(obj, 'files'):
            return [{
                'id': file.id,
                'name': file.name,
                'file_url': file.file.url if file.file else None,
                'uploaded_at': file.uploaded_at
            } for file in obj.files.all()]
        return []


class LeaderMixin:
    """提供项目负责人信息获取功能的Mixin类"""

    def get_leader(self, obj):
        """获取项目负责人信息"""
        if hasattr(obj, 'leader') and obj.leader:
            # 延迟导入避免循环引用
            from .serializers import StudentContactSerializer
            return StudentContactSerializer(obj.leader).data
        elif hasattr(obj, 'get_leader'):
            leader = obj.get_leader()
            if leader:
                from .serializers import StudentContactSerializer
                return StudentContactSerializer(leader).data
        return None


class ContactMixin:
    """提供联系方式脱敏功能的Mixin类"""

    def get_masked_email(self, obj):
        """获取脱敏邮箱"""
        email = getattr(obj, 'email', None)
        if email:
            parts = email.split('@')
            if len(parts) == 2:
                username, domain = parts
                if len(username) > 2:
                    masked_username = username[:2] + '*' * (len(username) - 2)
                else:
                    masked_username = username[0] + '*' * (len(username) - 1)
                return f"{masked_username}@{domain}"
        return email

    def get_masked_phone(self, obj):
        """获取脱敏手机号"""
        phone = getattr(obj, 'phone', None)
        if phone and len(phone) >= 7:
            return phone[:3] + '*' * 4 + phone[-4:]
        return phone