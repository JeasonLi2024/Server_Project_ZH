from rest_framework import serializers
from django.core.files.storage import default_storage
from django.conf import settings
from user.models import Tag1, Tag2
from .models import File, get_requirement_file_path, get_resource_file_path, generate_unique_filename
from common_utils import build_media_url
import uuid
import os


class ProjectRelatedMixin:
    """项目相关方法 Mixin"""

    def get_related_projects(self, obj):
        """获取关联的项目信息"""
        try:
            from studentproject.models import StudentProject, ProjectParticipant
            projects = StudentProject.objects.filter(requirement=obj)
            result = []
            for project in projects:
                participants = ProjectParticipant.objects.filter(project=project, status='approved')
                project_participants = [{
                    'id': participant.student.id,
                    'username': participant.student.user.username,
                    'school': participant.student.school,
                    'role': participant.role,
                } for participant in participants]

                result.append({
                    'id': project.id,
                    'title': project.title,
                    'status': project.status,
                    'created_at': project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else None,
                    'leader': {
                        'id': project.get_leader().id,
                        'username': project.get_leader().user.username,
                        'school': project.get_leader().school
                    } if project.get_leader() else None,
                    'participants': project_participants,
                })
            return result
        except ImportError:
            return []

    def get_total_project_members(self, obj):
        """获取项目总成员数（只记录状态为已通过的项目成员数）"""
        try:
            from studentproject.models import StudentProject, ProjectParticipant
            total_members = 0
            projects = StudentProject.objects.filter(requirement=obj)

            for project in projects:
                # 统计每个项目状态为已通过的参与者数量
                participants_count = ProjectParticipant.objects.filter(project=project, status='approved').count()
                total_members += participants_count

            return total_members
        except ImportError:
            return 0

    def get_total_project(self, obj):
        """获取关联的项目总数"""
        try:
            from studentproject.models import StudentProject
            return StudentProject.objects.filter(requirement=obj).count()
        except ImportError:
            return 0


class BaseFieldsMixin:
    """基础字段定义 Mixin，用于减少 Create 和 Update 序列化器中的重复字段定义"""

    @classmethod
    def get_common_fields(cls):
        """获取通用字段列表"""
        return [
            'tag1_ids', 'tag2_ids', 'files_ids', 'files',
            'cloud_links', 'virtual_folder_path', 'maintain_structure'
        ]

    @classmethod
    def get_requirement_fields(cls):
        """获取需求相关字段列表"""
        return [
            'title', 'brief', 'description', 'status', 'organization',
            'finish_time', 'budget', 'people_count', 'support_provided', 'evaluation_criteria_id'
        ] + cls.get_common_fields()

    @classmethod
    def get_resource_fields(cls):
        """获取资源相关字段列表"""
        return [
            'title', 'description', 'type', 'status'
        ] + cls.get_common_fields()

    @classmethod
    def get_requirement_extra_kwargs(cls, required_fields=None):
        """获取需求序列化器的 extra_kwargs"""
        if required_fields is None:
            required_fields = []

        extra_kwargs = {}
        optional_fields = [
            'title', 'brief', 'description', 'status', 'organization',
            'finish_time', 'budget', 'people_count', 'support_provided'
        ]

        for field in optional_fields:
            if field not in required_fields:
                extra_kwargs[field] = {'required': False}

        return extra_kwargs

    @classmethod
    def get_resource_extra_kwargs(cls, required_fields=None):
        """获取资源序列化器的 extra_kwargs"""
        if required_fields is None:
            required_fields = []

        extra_kwargs = {}
        optional_fields = ['title', 'description', 'type', 'status']

        for field in optional_fields:
            if field not in required_fields:
                extra_kwargs[field] = {'required': False}
            else:
                extra_kwargs[field] = {'required': True}

        return extra_kwargs


class TagValidationMixin:
    """标签验证 Mixin"""

    def validate_tag1_ids(self, value):
        """验证兴趣标签ID列表"""
        if not value:
            return []

        try:
            tag_ids = [int(tag_id.strip()) for tag_id in value.split(',') if tag_id.strip()]
            if tag_ids:
                existing_tags = Tag1.objects.filter(id__in=tag_ids)
                if len(existing_tags) != len(tag_ids):
                    raise serializers.ValidationError("部分兴趣标签不存在")
            return tag_ids
        except ValueError:
            raise serializers.ValidationError("兴趣标签ID格式错误")

    def validate_tag2_ids(self, value):
        """验证能力标签ID列表"""
        if not value:
            return []

        try:
            tag_ids = [int(tag_id.strip()) for tag_id in value.split(',') if tag_id.strip()]
            if tag_ids:
                existing_tags = Tag2.objects.filter(id__in=tag_ids)
                if len(existing_tags) != len(tag_ids):
                    raise serializers.ValidationError("部分能力标签不存在")
            return tag_ids
        except ValueError:
            raise serializers.ValidationError("能力标签ID格式错误")


class FileHandlingMixin:
    """文件处理 Mixin"""

    def validate_files_ids(self, value):
        """验证文件ID列表"""
        if not value:
            return []

        try:
            file_ids = [int(file_id.strip()) for file_id in value.split(',') if file_id.strip()]
            if file_ids:
                # 检查文件是否存在且未被关联
                existing_files = File.objects.filter(
                    id__in=file_ids,
                    requirement__isnull=True,
                    resource__isnull=True
                )
                if len(existing_files) != len(file_ids):
                    raise serializers.ValidationError("部分文件不存在或已被关联")
            return file_ids
        except ValueError:
            raise serializers.ValidationError("文件ID格式错误")

    def _handle_file_upload(self, instance, uploaded_files, virtual_folder_path="/", maintain_structure=False):
        """处理文件上传"""
        if not uploaded_files:
            return

        # 确保虚拟文件夹存在
        self._ensure_virtual_folder_exists(virtual_folder_path)

        for uploaded_file in uploaded_files:
            # 生成唯一文件名
            unique_filename = generate_unique_filename(uploaded_file.name)

            # 根据实例类型选择文件路径函数
            if hasattr(instance, 'requirement'):
                file_path = get_requirement_file_path(instance, unique_filename)
            else:
                file_path = get_resource_file_path(instance, unique_filename)

            # 保存文件
            saved_path = default_storage.save(file_path, uploaded_file)

            # 创建文件记录
            file_obj = File.objects.create(
                name=uploaded_file.name,
                file=saved_path,
                virtual_folder_path=virtual_folder_path,
                is_cloud_link=False
            )

            # 关联文件到实例
            if hasattr(instance, 'requirement'):
                file_obj.requirement = instance
            else:
                file_obj.resource = instance
            file_obj.save()

    def _handle_cloud_links(self, instance, cloud_links_data, virtual_folder_path="/"):
        """处理网盘链接"""
        if not cloud_links_data:
            return

        # 确保虚拟文件夹存在
        self._ensure_virtual_folder_exists(virtual_folder_path)

        for link_data in cloud_links_data:
            url = link_data.get('url', '').strip()
            password = link_data.get('password', '').strip()
            path = link_data.get('path', virtual_folder_path).strip()

            if not url:
                continue

            # 从URL中提取文件名
            filename = link_data.get('name', f"云盘文件_{uuid.uuid4().hex[:8]}")

            # 创建文件记录
            file_obj = File.objects.create(
                name=filename,
                cloud_link_url=url,
                cloud_password=password,
                virtual_folder_path=path,
                is_cloud_link=True
            )

            # 关联文件到实例
            if hasattr(instance, 'requirement'):
                file_obj.requirement = instance
            else:
                file_obj.resource = instance
            file_obj.save()

    def _ensure_virtual_folder_exists(self, folder_path):
        """确保虚拟文件夹路径存在"""
        if not folder_path or folder_path == "/":
            return

        # 标准化路径
        folder_path = folder_path.strip()
        if not folder_path.startswith("/"):
            folder_path = "/" + folder_path
        if not folder_path.endswith("/"):
            folder_path += "/"

        # 这里可以添加创建虚拟文件夹的逻辑
        # 目前只是确保路径格式正确
        return folder_path

    def _set_relations(self, instance, relations_data, is_update=False):
        """设置关联关系"""
        # 处理标签关联
        tag1_ids = relations_data.get('tag1_ids', [])
        tag2_ids = relations_data.get('tag2_ids', [])

        if tag1_ids:
            instance.tag1.set(tag1_ids)
        elif is_update:
            instance.tag1.clear()

        if tag2_ids:
            instance.tag2.set(tag2_ids)
        elif is_update:
            instance.tag2.clear()

        # 处理文件关联
        files_ids = relations_data.get('files_ids', [])
        if files_ids:
            File.objects.filter(id__in=files_ids).update(
                requirement=instance if hasattr(instance, 'requirement') else None,
                resource=instance if hasattr(instance, 'resource') else None
            )