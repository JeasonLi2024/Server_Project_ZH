from rest_framework import serializers
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import requests
from .models import Requirement, Resource, File, RequirementFavorite, get_requirement_file_path, get_resource_file_path, generate_unique_filename
from user.models import Tag1, Tag2, OrganizationUser
from organization.models import Organization
from common_utils import build_media_url
from .mixins import TagValidationMixin, FileHandlingMixin, ProjectRelatedMixin, BaseFieldsMixin
from audit.utils import AuditLogMixin
import uuid
import os


class FileSerializer(serializers.ModelSerializer):
    """文件序列化器 - 支持虚拟文件系统"""
    url = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    cloud_link_url = serializers.SerializerMethodField()
    cloud_password = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    class Meta:
        model = File
        fields = [
            'id', 'name', 'url', 'size', 'is_cloud_link',
            'cloud_link_url', 'cloud_password', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_url(self, obj):
        """获取文件完整URL（实体文件返回完整HTTP URL，网盘链接返回网盘链接地址）"""
        if obj.is_cloud_link:
            # 网盘链接形式的文件，返回网盘链接地址
            return obj.url if obj.url else None
        if obj.real_path:
            request = self.context.get('request')
            return build_media_url(obj.real_path, request)
        return None
    
    def get_size(self, obj):
        """获取文件大小（网盘链接返回null）"""
        if obj.is_cloud_link:
            return None
        return obj.size
    
    def get_cloud_link_url(self, obj):
        """获取网盘链接URL（仅网盘链接有效）"""
        if obj.is_cloud_link and obj.url:
            return obj.url
        return None
    
    def get_cloud_password(self, obj):
        """获取网盘链接密码（仅网盘链接有效）"""
        if obj.is_cloud_link and obj.cloud_password:
            return obj.cloud_password
        return None


class ResourceSerializer(serializers.ModelSerializer):
    """资源序列化器"""
    tag1 = serializers.SerializerMethodField()
    tag2 = serializers.SerializerMethodField()
    files = FileSerializer(many=True, read_only=True)
    create_person_name = serializers.CharField(source='create_person.user.username', read_only=True)
    update_person_name = serializers.CharField(source='update_person.user.username', read_only=True)
    
    class Meta:
        model = Resource
        fields = [
            'id', 'title', 'description', 'type', 'tag1', 'tag2', 'files',
            'status', 'create_person', 'create_person_name',
            'update_person', 'update_person_name', 'downloads', 'views',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_tag1(self, obj):
        """获取兴趣标签列表"""
        return [{'id': tag.id, 'name': str(tag)} for tag in obj.tag1.all()]
    
    def get_tag2(self, obj):
        """获取能力标签列表"""
        return [{'id': tag.id, 'name': str(tag)} for tag in obj.tag2.all()]
    
    def get_related_projects(self, obj):
        """获取关联的项目信息"""
        from studentproject.models import StudentProject
        projects = StudentProject.objects.filter(requirement=obj)
        return [{
            'id': project.id,
            'name': project.name,
            'status': project.status,
            'created_at': project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else None,
            'leader': {
                'id': project.leader.id,
                'username': project.leader.user.username,
                'student_id': project.leader.student_id,
                'avatar': build_media_url(project.leader.user.avatar, self.context.get('request')) if project.leader.user.avatar else None
            } if project.leader else None
        } for project in projects]
    
    def get_project_participants(self, obj):
        """获取项目参与者信息"""
        from studentproject.models import StudentProject, ProjectParticipant
        participants_data = []
        projects = StudentProject.objects.filter(requirement=obj)
        
        for project in projects:
            participants = ProjectParticipant.objects.filter(project=project)
            project_participants = [{
                'id': participant.student.id,
                'username': participant.student.user.username,
                'student_id': participant.student.student_id,
                'avatar': build_media_url(participant.student.user.avatar, self.context.get('request')) if participant.student.user.avatar else None,
                'role': participant.role,
                'joined_at': participant.joined_at.strftime('%Y-%m-%d %H:%M:%S') if participant.joined_at else None
            } for participant in participants]
            
            participants_data.append({
                'project_id': project.id,
                'project_name': project.name,
                'participants': project_participants
            })
        
        return participants_data
    
    def get_total_project_members(self, obj):
        """获取项目总成员数"""
        from studentproject.models import StudentProject, ProjectParticipant
        total_members = 0
        projects = StudentProject.objects.filter(requirement=obj)
        
        for project in projects:
            # 统计每个项目的参与者数量（包括项目负责人）
            participants_count = ProjectParticipant.objects.filter(project=project).count()
            # 加上项目负责人（如果负责人不在参与者列表中）
            if project.leader and not ProjectParticipant.objects.filter(project=project, student=project.leader).exists():
                participants_count += 1
            total_members += participants_count
        
        return total_members
    
    def get_related_projects(self, obj):
        """获取关联的项目列表"""
        try:
            from studentproject.models import StudentProject
            projects = StudentProject.objects.filter(requirement=obj).select_related('creator__user')
            request = self.context.get('request')
            return [{
                'id': project.id,
                'title': project.title,
                'status': project.status,
                'creator': project.creator.user.real_name or project.creator.user.username,
                'avatar': build_media_url(project.creator.user.avatar.url, request) if project.creator.user.avatar else None,
                'created_at': project.created_at
            } for project in projects]
        except ImportError:
            return []
    
    def get_project_participants(self, obj):
        """获取项目参与者信息"""
        try:
            from studentproject.models import StudentProject, ProjectParticipant
            participants = []
            projects = StudentProject.objects.filter(requirement=obj)
            
            for project in projects:
                # 获取项目参与者
                project_participants = ProjectParticipant.objects.filter(
                    project=project,
                    status__in=['approved', 'active']
                ).select_related('student__user')
                
                for participant in project_participants:
                    participants.append({
                        'project_id': project.id,
                        'project_title': project.title,
                        'student_id': participant.student.id,
                        'student_name': participant.student.user.real_name or participant.student.user.username,
                        'avatar': build_media_url(participant.student.user.avatar.url, self.context.get('request')) if participant.student.user.avatar else None,
                        'role': participant.role,
                        'status': participant.status,
                        'joined_at': participant.joined_at
                    })
                
                # 添加项目创建者
                if project.creator:
                    participants.append({
                        'project_id': project.id,
                        'project_title': project.title,
                        'student_id': project.creator.id,
                        'student_name': project.creator.user.real_name or project.creator.user.username,
                        'avatar': build_media_url(project.creator.user.avatar.url, self.context.get('request')) if project.creator.user.avatar else None,
                        'role': '项目负责人',
                        'status': 'active',
                        'joined_at': project.created_at
                    })
            
            return participants
        except ImportError:
            return []
    
    def get_related_projects(self, obj):
        """获取关联的项目列表"""
        try:
            from studentproject.models import StudentProject
            projects = StudentProject.objects.filter(requirement=obj).select_related('creator__user')
            return [{
                'id': project.id,
                'title': project.title,
                'status': project.status,
                'creator': project.creator.user.real_name or project.creator.user.username,
                'created_at': project.created_at
            } for project in projects]
        except ImportError:
            return []
    
    def get_project_participants(self, obj):
        """获取项目参与者信息"""
        try:
            from studentproject.models import StudentProject, ProjectParticipant
            participants = []
            projects = StudentProject.objects.filter(requirement=obj)
            
            for project in projects:
                # 获取项目参与者
                project_participants = ProjectParticipant.objects.filter(
                    project=project,
                    status__in=['approved', 'active']
                ).select_related('student__user')
                
                for participant in project_participants:
                    participants.append({
                        'project_id': project.id,
                        'project_title': project.title,
                        'student_id': participant.student.id,
                        'student_name': participant.student.user.real_name or participant.student.user.username,
                        'role': participant.role,
                        'status': participant.status,
                        'joined_at': participant.joined_at
                    })
                
                # 添加项目创建者
                if project.creator:
                    participants.append({
                        'project_id': project.id,
                        'project_title': project.title,
                        'student_id': project.creator.id,
                        'student_name': project.creator.user.real_name or project.creator.user.username,
                        'role': '项目负责人',
                        'joined_at': project.created_at
                    })
            
            return participants
        except ImportError:
            return []
    
    def get_total_project_members(self, obj):
        """获取项目参与者总数"""
        try:
            from studentproject.models import StudentProject, ProjectParticipant
            total_members = 0
            projects = StudentProject.objects.filter(requirement=obj)
            
            for project in projects:
                # 统计参与者数量
                participants_count = ProjectParticipant.objects.filter(
                    project=project,
                    status__in=['approved', 'active']
                ).count()
                
                # 加上项目创建者
                total_members += participants_count + (1 if project.creator else 0)
            
            return total_members
        except ImportError:
            return 0
    
class OrganizationSimpleSerializer(serializers.ModelSerializer):
    """组织简单信息序列化器"""
    logo = serializers.SerializerMethodField()

    def get_logo(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        return build_media_url(obj.logo, request)

    class Meta:
        model = Organization
        fields = ['id', 'name', 'logo', 'status']
        read_only_fields = ['id', 'name', 'logo', 'status']


class ResourceSimpleSerializer(serializers.ModelSerializer):
    """资源简单信息序列化器"""
    class Meta:
        model = Resource
        fields = ['id', 'title', 'type']
        read_only_fields = ['id', 'title', 'type']


class RequirementSerializer(ProjectRelatedMixin, serializers.ModelSerializer):
    """需求序列化器（用于返回数据）"""
    tag1 = serializers.SerializerMethodField()
    tag2 = serializers.SerializerMethodField()
    organization = OrganizationSimpleSerializer(read_only=True)
    publish_people = serializers.CharField(source='publish_people.user.username', read_only=True)
    resources = ResourceSimpleSerializer(many=True, read_only=True)
    files = FileSerializer(many=True, read_only=True)
    # 新增项目相关字段
    related_projects = serializers.SerializerMethodField()
    total_project_members = serializers.SerializerMethodField()
    total_project = serializers.SerializerMethodField()
    # 评分标准对象
    evaluation_criteria = serializers.SerializerMethodField()
    # 收藏状态字段
    is_favorited = serializers.SerializerMethodField()
    
    class Meta:
        model = Requirement
        fields = [
            'id', 'title', 'brief', 'description', 'tag1', 'tag2', 'status',
            'organization', 'publish_people', 'finish_time',
            'budget', 'people_count', 'support_provided', 'evaluation_criteria', 'views',
            'resources', 'files', 'cover', 'related_projects', 'total_project_members', 'total_project',
            'evaluation_published', 'is_favorited', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'views', 'evaluation_published', 'is_favorited', 'created_at', 'updated_at']
    
    def get_tag1(self, obj):
        """获取兴趣标签列表"""
        return [{'id': tag.id, 'name': str(tag)} for tag in obj.tag1.all()]
    
    def get_tag2(self, obj):
        """获取能力标签列表"""
        return [{'id': tag.id, 'name': str(tag)} for tag in obj.tag2.all()]
    
    def get_evaluation_criteria(self, obj):
        """获取关联的评分标准基础信息"""
        if obj.evaluation_criteria:
            try:
                criteria = obj.evaluation_criteria
                return {
                    'id': criteria.id,
                    'name': criteria.name,
                    'description': criteria.description,
                    'status': criteria.status,
                    'indicator_count': criteria.indicators.count(),
                    'total_weight': sum(indicator.weight for indicator in criteria.indicators.all()),
                    'created_at': criteria.created_at.strftime('%Y-%m-%d %H:%M:%S') if criteria.created_at else None
                }
            except Exception as e:
                # 记录异常但返回None，避免整个序列化失败
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"获取评分标准信息失败: {str(e)}")
                return None
        return None
    
    def get_is_favorited(self, obj):
        """获取当前用户是否收藏了该需求"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        # 只有学生用户才能收藏需求
        if not hasattr(request.user, 'student_profile'):
            return False
        
        # 优化：使用预取的收藏数据避免N+1查询
        favorited_requirements = self.context.get('favorited_requirements')
        if favorited_requirements is not None:
            return obj.id in favorited_requirements
        
        # 回退到单个查询（用于单个需求详情）
        return RequirementFavorite.objects.filter(
            student=request.user.student_profile,
            requirement=obj
        ).exists()


class RequirementBaseSerializer(TagValidationMixin, FileHandlingMixin, serializers.ModelSerializer):
    """需求序列化器基类，包含公共字段和验证方法"""
    tag1_ids = serializers.CharField(
        write_only=True,
        required=False,
        help_text="兴趣标签ID列表，逗号分隔（如：1,2,3）"
    )
    tag2_ids = serializers.CharField(
        write_only=True,
        required=False,
        help_text="能力标签ID列表，逗号分隔（如：1,2,3）"
    )
    resource_ids = serializers.CharField(
        write_only=True,
        required=False,
        help_text="关联资源ID列表，逗号分隔（如：1,2,3）"
    )
    files_ids = serializers.CharField(
        write_only=True,
        required=False,
        help_text="文件ID列表，逗号分隔（如：1,2,3）"
    )
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        help_text="直接上传的文件列表（支持form-data格式）"
    )
    # 网盘链接上传支持
    cloud_links = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="网盘链接列表，每个链接包含：url(网盘链接), password(提取密码，可选), path(虚拟路径，可选)"
    )
    virtual_folder_path = serializers.CharField(
        write_only=True,
        required=False,
        default="/",
        help_text="虚拟文件夹路径，文件将上传到此路径下（如：/documents/images）"
    )
    maintain_structure = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
        help_text="是否保持文件夹结构（自动调整：virtual_folder_path为'/'时为true，否则为false）"
    )
    cover_file = serializers.ImageField(
        write_only=True, 
        required=False, 
        help_text="用户上传的本地图片文件"
    )
    cover_url = serializers.URLField(
        write_only=True, 
        required=False, 
        help_text="用户选中的AI生成图片URL"
    )
    
    class Meta:
        model = Requirement
        fields = [
            'title', 'brief', 'description', 'status', 'organization',
            'finish_time', 'budget', 'people_count', 'support_provided', 'evaluation_criteria_id',
            'tag1_ids', 'tag2_ids', 'resource_ids', 'files_ids', 'files',
            'cloud_links', 'virtual_folder_path', 'maintain_structure',
            'cover_file', 'cover_url'
        ]
        abstract = True
    
    def _process_cover_url(self, cover_url):
        """处理封面URL（支持本地临时文件移动和远程文件下载）"""
        if not cover_url:
            return None
            
        import urllib.parse
        
        # 1. 检查是否是本地临时文件 (/cover/tmp/)
        # 统一路径分隔符为正斜杠进行检查
        normalized_url = cover_url.replace('\\', '/')
        if '/cover/tmp/' in normalized_url:
            try:
                # 解析路径
                parsed_url = urllib.parse.urlparse(normalized_url)
                path = parsed_url.path
                
                # 提取文件名
                filename = os.path.basename(path)
                
                # 构建本地绝对路径
                temp_path = os.path.join(settings.MEDIA_ROOT, 'cover', 'tmp', filename)
                
                if os.path.exists(temp_path):
                    # 读取文件内容
                    with open(temp_path, 'rb') as f:
                        content = f.read()
                        
                    # 创建 ContentFile
                    # 使用新文件名（uuid）
                    new_file_name = f"{uuid.uuid4().hex}.png"
                    content_file = ContentFile(content, name=new_file_name)
                    
                    # 清理同批次临时文件
                    # 文件名格式: {batch_id}_{idx}.png
                    try:
                        batch_id = filename.split('_')[0]
                        temp_dir = os.path.dirname(temp_path)
                        for f in os.listdir(temp_dir):
                            if f.startswith(batch_id + '_'):
                                try:
                                    os.remove(os.path.join(temp_dir, f))
                                except OSError:
                                    pass
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"清理临时封面失败: {e}")
                        
                    return content_file
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"处理本地临时封面失败: {e}")
                
        # 2. 远程文件下载
        try:
            response = requests.get(cover_url, timeout=30)
            if response.status_code == 200:
                file_name = f"{uuid.uuid4().hex}.jpg"
                return ContentFile(response.content, name=file_name)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"下载封面图片失败: {str(e)}")
            
        return None
    
    def validate_organization(self, value):
        """验证组织权限"""
        user = self.context['request'].user
        try:
            org_user = OrganizationUser.objects.get(user=user, organization=value)
            # 只要是企业用户（组织成员）即可操作需求
        except OrganizationUser.DoesNotExist:
            raise serializers.ValidationError("您不是此组织的成员")
        return value
    
    def validate_resource_ids(self, value):
        """验证资源ID"""
        if value:
            # 解析逗号分隔的字符串
            try:
                resource_ids = [id.strip() for id in value.split(',') if id.strip()]
                # 转换为整数列表
                resource_ids = [int(id) for id in resource_ids]
            except ValueError:
                raise serializers.ValidationError("资源ID必须是有效的整数，用逗号分隔")
            
            existing_ids = set(Resource.objects.filter(id__in=resource_ids).values_list('id', flat=True))
            invalid_ids = set(resource_ids) - existing_ids
            if invalid_ids:
                raise serializers.ValidationError(f"无效的资源ID: {list(invalid_ids)}")
            return resource_ids
        return []
    
    def validate_files_ids(self, value):
        """验证文件ID"""
        if value:
            # 解析逗号分隔的字符串
            try:
                file_ids = [id.strip() for id in value.split(',') if id.strip()]
                # 转换为整数列表
                file_ids = [int(id) for id in file_ids]
            except ValueError:
                raise serializers.ValidationError("文件ID必须是有效的整数，用逗号分隔")
            
            # 检查文件是否存在
            existing_files = File.objects.filter(id__in=file_ids)
            existing_ids = set(existing_files.values_list('id', flat=True))
            invalid_ids = set(file_ids) - existing_ids
            if invalid_ids:
                raise serializers.ValidationError(f"无效的文件ID: {list(invalid_ids)}")
            
            # 检查是否包含文件夹
            folder_files = existing_files.filter(is_folder=True)
            if folder_files.exists():
                folder_names = list(folder_files.values_list('name', flat=True))
                raise serializers.ValidationError(
                    f"不能直接关联文件夹到需求，请使用虚拟文件系统管理文件夹。包含的文件夹: {folder_names}"
                )
            
            return file_ids
        return []
    
    def _handle_file_upload(self, instance, uploaded_files, virtual_folder_path="/", maintain_structure=False):
        """处理文件上传的公共方法 - 支持虚拟文件系统"""
        created_file_ids = []
        if uploaded_files:
            for uploaded_file in uploaded_files:
                # 解析文件路径结构（如果保持结构）
                if maintain_structure and hasattr(uploaded_file, 'name'):
                    # 从文件名中提取路径信息（前端可能会传递相对路径）
                    file_path_parts = uploaded_file.name.split('/')
                    if len(file_path_parts) > 1:
                        # 有文件夹结构
                        folder_path = '/'.join(file_path_parts[:-1])
                        file_name = file_path_parts[-1]
                        virtual_path = f"{virtual_folder_path.rstrip('/')}/{folder_path}/{file_name}"
                        parent_path = f"{virtual_folder_path.rstrip('/')}/{folder_path}"
                        
                        # 确保父文件夹存在
                        self._ensure_virtual_folder_exists(parent_path)
                    else:
                        file_name = uploaded_file.name
                        if virtual_folder_path == "/":
                            virtual_path = f"/{file_name}"
                            parent_path = None
                        else:
                            virtual_path = f"{virtual_folder_path.rstrip('/')}/{file_name}"
                            parent_path = virtual_folder_path
                else:
                    file_name = uploaded_file.name
                    if virtual_folder_path == "/":
                        virtual_path = f"/{file_name}"
                        parent_path = None
                    else:
                        virtual_path = f"{virtual_folder_path.rstrip('/')}/{file_name}"
                        parent_path = virtual_folder_path
                
                # 生成UUID文件名和实际存储路径
                real_filename = generate_unique_filename(file_name)
                real_relative_path = get_requirement_file_path(instance.id, real_filename)
                full_path = os.path.join(settings.MEDIA_ROOT, real_relative_path)
                
                # 确保目录存在
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # 保存文件到指定路径
                saved_path = default_storage.save(real_relative_path, uploaded_file)
                
                # 生成完整的URL地址
                file_url = f"{settings.MEDIA_URL}{saved_path}"
                if hasattr(settings, 'SITE_URL'):
                    file_url = f"{settings.SITE_URL}{file_url}"
                
                # 确保虚拟父文件夹存在
                if parent_path != "/":
                    self._ensure_virtual_folder_exists(parent_path)
                
                # 创建文件记录
                file_obj = File.objects.create(
                    name=file_name,
                    path=virtual_path,  # 虚拟路径
                    real_path=saved_path,  # 实际存储路径
                    parent_path=parent_path if parent_path != "/" else None,
                    is_folder=False,
                    url=file_url,
                    size=uploaded_file.size
                )
                created_file_ids.append(file_obj.id)
        return created_file_ids
    
    def _handle_cloud_links(self, instance, cloud_links_data, virtual_folder_path="/"):
        """处理网盘链接上传的公共方法"""
        created_file_ids = []
        if cloud_links_data:
            for cloud_link_data in cloud_links_data:
                url = cloud_link_data.get('url')
                password = cloud_link_data.get('password', '')
                custom_path = cloud_link_data.get('path')
                
                if not url:
                    continue
                
                # 确定虚拟路径
                if custom_path:
                    virtual_path = custom_path
                    parent_path = '/'.join(custom_path.split('/')[:-1]) or None
                else:
                    file_name = "网盘链接"
                    if virtual_folder_path == "/":
                        virtual_path = f"/{file_name}"
                        parent_path = None
                    else:
                        virtual_path = f"{virtual_folder_path.rstrip('/')}/{file_name}"
                        parent_path = virtual_folder_path
                
                # 确保虚拟父文件夹存在
                if parent_path and parent_path != "/":
                    self._ensure_virtual_folder_exists(parent_path)
                
                # 创建网盘链接文件记录
                file_obj = File.objects.create(
                    name="网盘链接",
                    path=virtual_path,
                    parent_path=parent_path if parent_path != "/" else None,
                    is_folder=False,
                    is_cloud_link=True,
                    cloud_password=password,
                    url=url,
                    size=0  # 网盘链接不记录大小
                )
                created_file_ids.append(file_obj.id)
        return created_file_ids
    
    def _ensure_virtual_folder_exists(self, folder_path):
        """确保虚拟文件夹存在"""
        if folder_path == "/" or not folder_path:
            return
        
        # 检查文件夹是否已存在
        if File.objects.filter(path=folder_path, is_folder=True).exists():
            return
        
        # 递归创建父文件夹
        parent_path = '/'.join(folder_path.rstrip('/').split('/')[:-1])
        if parent_path and parent_path != "/":
            self._ensure_virtual_folder_exists(parent_path)
        
        # 创建当前文件夹
        folder_name = folder_path.rstrip('/').split('/')[-1]
        File.objects.create(
            name=folder_name,
            path=folder_path,
            parent_path=parent_path if parent_path != "/" else None,
            is_folder=True,
            size=0
        )
    
    def _set_relations(self, instance, relations_data, is_update=False):
        """设置关联关系"""
        tag1_ids = relations_data.get('tag1_ids')
        tag2_ids = relations_data.get('tag2_ids')
        resource_ids = relations_data.get('resource_ids')
        files_ids = relations_data.get('files_ids')
        
        if tag1_ids is not None:
            instance.tag1.set(tag1_ids)
        if tag2_ids is not None:
            instance.tag2.set(tag2_ids)
        if resource_ids is not None:
            instance.resources.set(resource_ids)
        if files_ids is not None:
            # 无论是创建还是更新模式，都直接设置文件ID（替换现有关联）
            instance.files.set(files_ids)


class RequirementCreateSerializer(BaseFieldsMixin, AuditLogMixin, RequirementBaseSerializer):
    """需求创建序列化器"""
    
    class Meta:
        model = Requirement
        fields = BaseFieldsMixin.get_requirement_fields() + ['resource_ids']
        extra_kwargs = BaseFieldsMixin.get_requirement_extra_kwargs()
    
    def create(self, validated_data):
        """创建需求"""
        # 提取关联数据
        tag1_ids = validated_data.pop('tag1_ids', [])
        tag2_ids = validated_data.pop('tag2_ids', [])
        resource_ids = validated_data.pop('resource_ids', [])
        files_ids = validated_data.pop('files_ids', [])
        uploaded_files = validated_data.pop('files', [])
        cloud_links_data = validated_data.pop('cloud_links', [])
        virtual_folder_path = validated_data.pop('virtual_folder_path', '/')
        maintain_structure = validated_data.pop('maintain_structure', False)
        
        # 提取封面数据
        cover_file = validated_data.pop('cover_file', None)
        cover_url = validated_data.pop('cover_url', None)
        
        # 处理封面
        if cover_file:
            validated_data['cover'] = cover_file
        elif cover_url:
            processed_cover = self._process_cover_url(cover_url)
            if processed_cover:
                validated_data['cover'] = processed_cover
        
        # 自动调整 maintain_structure：当 virtual_folder_path 为默认值 "/" 时设为 true，否则设为 false
        maintain_structure = (virtual_folder_path == "/")
        
        # 设置发布人和默认组织
        user = self.context['request'].user
        
        # 如果没有指定组织，使用发布者所属的组织（默认取第一个组织）
        if not validated_data.get('organization'):
            try:
                org_user = OrganizationUser.objects.filter(user=user).first()
                if org_user:
                    validated_data['organization'] = org_user.organization
                else:
                    raise serializers.ValidationError("用户未加入任何组织，无法发布需求")
            except Exception:
                raise serializers.ValidationError("获取用户组织信息失败")
        
        org_user = OrganizationUser.objects.get(
            user=user, 
            organization=validated_data['organization']
        )
        validated_data['publish_people'] = org_user
        
        # 设置默认状态为under_review（待审核）
        if not validated_data.get('status'):
            validated_data['status'] = 'under_review'
                     
        # 创建需求
        requirement = Requirement.objects.create(**validated_data)
        
        # 使用基类方法处理文件上传（支持虚拟文件系统）
        created_file_ids = self._handle_file_upload(
            requirement, 
            uploaded_files, 
            virtual_folder_path=virtual_folder_path,
            maintain_structure=maintain_structure
        )
        
        # 处理网盘链接上传
        cloud_link_file_ids = self._handle_cloud_links(
            requirement,
            cloud_links_data,
            virtual_folder_path=virtual_folder_path
        )
        
        # 合并文件ID列表
        all_file_ids = list(files_ids) + created_file_ids + cloud_link_file_ids
        
        # 使用基类方法设置关联关系
        relations_data = {
            'tag1_ids': tag1_ids,
            'tag2_ids': tag2_ids,
            'resource_ids': resource_ids,
            'files_ids': all_file_ids
        }
        self._set_relations(requirement, relations_data)
        
        return requirement


class RequirementUpdateSerializer(BaseFieldsMixin, AuditLogMixin, RequirementBaseSerializer):
    """需求更新序列化器"""
    
    # 显式定义evaluation_criteria_id为可写字段
    evaluation_criteria_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="评分标准ID"
    )
    
    class Meta:
        model = Requirement
        fields = [
            'title', 'brief', 'description', 'status', 'organization',
            'finish_time', 'budget', 'people_count', 'support_provided', 'evaluation_criteria_id',
            'tag1_ids', 'tag2_ids', 'resource_ids', 'cover_file', 'cover_url'
        ]
        extra_kwargs = BaseFieldsMixin.get_requirement_extra_kwargs()
    
    def validate_evaluation_criteria_id(self, value):
        """验证评分标准ID"""
        if value is not None:
            from projectscore.models import EvaluationCriteria
            try:
                criteria = EvaluationCriteria.objects.get(id=value)
                if criteria.status != 'active':
                    raise serializers.ValidationError("评分标准未激活，无法使用")
                return value
            except EvaluationCriteria.DoesNotExist:
                raise serializers.ValidationError("评分标准不存在")
        return value
    
    def update(self, instance, validated_data):
        """更新需求"""
        from django.db import transaction
        
        # 使用数据库事务确保操作原子性
        with transaction.atomic():
            # 获取原始状态
            old_status = instance.status
            
            # 提取关联数据
            tag1_ids = validated_data.pop('tag1_ids', None)
            tag2_ids = validated_data.pop('tag2_ids', None)
            resource_ids = validated_data.pop('resource_ids', None)
            
            # 提取封面数据
            cover_file = validated_data.pop('cover_file', None)
            cover_url = validated_data.pop('cover_url', None)
            
            # 处理封面更新
            if cover_file:
                instance.cover = cover_file
            elif cover_url:
                processed_cover = self._process_cover_url(cover_url)
                if processed_cover:
                    # save=False 避免立即保存导致多次写库
                    instance.cover.save(processed_cover.name, processed_cover, save=False)
            
            # 状态判断逻辑：当前状态为审核失败时重置为待审核
            if 'status' not in validated_data and instance.status == 'review_failed':
                validated_data['status'] = 'under_review'
            
            # 更新基本字段
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            
            # 设置关联关系（不包含文件，文件操作由虚拟文件系统路由完成）
            relations_data = {
                'tag1_ids': tag1_ids,
                'tag2_ids': tag2_ids,
                'resource_ids': resource_ids,
                'files_ids': None  # 不处理文件关联
            }
            self._set_relations(instance, relations_data, is_update=True)
            
            # 记录审核历史（如果状态发生变更）
            new_status = instance.status
            if old_status != new_status:
                comment = validated_data.get('review_comment', '')
                extra_details = {
                    'updated_fields': list(validated_data.keys()),
                    'tag1_updated': tag1_ids is not None,
                    'tag2_updated': tag2_ids is not None,
                    'resources_updated': resource_ids is not None,
                }
                self.log_requirement_status_change(
                    requirement=instance,
                    old_status=old_status,
                    new_status=new_status,
                    comment=comment,
                    **extra_details
                )
        
        return instance


class RequirementFavoriteSerializer(serializers.ModelSerializer):
    """需求收藏序列化器"""
    requirement = RequirementSerializer(read_only=True)
    student_name = serializers.CharField(source='student.user.username', read_only=True)
    
    class Meta:
        model = RequirementFavorite
        fields = ['id', 'student', 'student_name', 'requirement', 'created_at']
        read_only_fields = ['id', 'created_at']


class RequirementFavoriteCreateSerializer(serializers.ModelSerializer):
    """需求收藏创建序列化器"""
    
    class Meta:
        model = RequirementFavorite
        fields = ['requirement']
    
    def validate_requirement(self, value):
        """验证需求是否存在且状态有效"""
        if not value:
            raise serializers.ValidationError("需求不能为空")
        
        # 检查需求状态是否允许收藏
        if value.status in ['review_failed']:
            raise serializers.ValidationError("该需求当前状态不允许收藏")
        
        return value
    
    def create(self, validated_data):
        """创建收藏记录"""
        student = self.context['request'].user.student_profile
        requirement = validated_data['requirement']
        
        # 检查是否已经收藏
        if RequirementFavorite.objects.filter(student=student, requirement=requirement).exists():
            raise serializers.ValidationError("您已经收藏过这个需求了")
        
        return RequirementFavorite.objects.create(
            student=student,
            requirement=requirement
        )


class ResourceBaseSerializer(TagValidationMixin, FileHandlingMixin, serializers.ModelSerializer):
    """资源序列化器基类，包含公共字段和验证方法"""
    tag1_ids = serializers.CharField(
        write_only=True,
        required=False,
        help_text="兴趣标签ID列表，逗号分隔（如：1,2,3）"
    )
    tag2_ids = serializers.CharField(
        write_only=True,
        required=False,
        help_text="能力标签ID列表，逗号分隔（如：1,2,3）"
    )
    files_ids = serializers.CharField(
        write_only=True,
        required=False,
        help_text="文件ID列表，逗号分隔（如：1,2,3）"
    )
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        help_text="直接上传的文件列表（支持form-data格式）"
    )
    # 网盘链接上传支持
    cloud_links = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="网盘链接列表，每个链接包含：url(网盘链接), password(提取密码，可选), path(虚拟路径，可选)"
    )
    virtual_folder_path = serializers.CharField(
        write_only=True,
        required=False,
        default="/",
        help_text="虚拟文件夹路径，文件将上传到此路径下（如：/documents/images）"
    )
    maintain_structure = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
        help_text="是否保持文件夹结构（自动调整：virtual_folder_path为'/'时为true，否则为false）"
    )
    
    class Meta:
        model = Resource
        fields = [
            'title', 'description', 'type', 'status',
            'tag1_ids', 'tag2_ids', 'files_ids', 'files',
            'cloud_links', 'virtual_folder_path', 'maintain_structure'
        ]
        abstract = True
    

class ResourceCreateSerializer(BaseFieldsMixin, AuditLogMixin, ResourceBaseSerializer):
    """资源创建序列化器"""
    
    class Meta:
        model = Resource
        fields = BaseFieldsMixin.get_resource_fields()
        extra_kwargs = BaseFieldsMixin.get_resource_extra_kwargs(['title', 'description', 'type'])
    
    def validate(self, attrs):
        """验证用户权限"""
        user = self.context['request'].user
        
        # 检查用户是否为组织用户
        if user.user_type != 'organization':
            raise serializers.ValidationError("只有组织用户可以发布资源")
        
        # 检查用户是否属于某个组织
        try:
            org_user = OrganizationUser.objects.filter(user=user, status='approved').first()
            if not org_user:
                raise serializers.ValidationError("您不属于任何已审核的组织，无法发布资源")
        except Exception:
            raise serializers.ValidationError("获取用户组织信息失败")
        
        return attrs
    
    def create(self, validated_data):
        """创建资源"""
        # 提取关联数据
        tag1_ids = validated_data.pop('tag1_ids', [])
        tag2_ids = validated_data.pop('tag2_ids', [])
        files_ids = validated_data.pop('files_ids', [])
        uploaded_files = validated_data.pop('files', [])
        cloud_links = validated_data.pop('cloud_links', [])
        virtual_folder_path = validated_data.pop('virtual_folder_path', '/')
        maintain_structure = validated_data.pop('maintain_structure', False)
        
        # 自动调整 maintain_structure：当 virtual_folder_path 为默认值 "/" 时设为 true，否则设为 false
        maintain_structure = (virtual_folder_path == "/")
        
        # 设置创建人和更新人
        user = self.context['request'].user
        org_user = OrganizationUser.objects.filter(user=user, status='approved').first()
        
        validated_data['create_person'] = org_user
        validated_data['update_person'] = org_user
        
        # 设置默认状态为draft（草稿）
        if not validated_data.get('status'):
            validated_data['status'] = 'draft'
                     
        # 创建资源
        resource = Resource.objects.create(**validated_data)
        
        # 使用基类方法处理文件上传（支持虚拟文件系统）
        created_file_ids = self._handle_file_upload(
            resource, 
            uploaded_files, 
            virtual_folder_path=virtual_folder_path,
            maintain_structure=maintain_structure
        )
        
        # 处理网盘链接上传
        cloud_link_file_ids = self._handle_cloud_links(
            resource,
            cloud_links,
            virtual_folder_path=virtual_folder_path
        )
        
        # 合并文件ID列表
        all_file_ids = list(files_ids) + created_file_ids + cloud_link_file_ids
        
        # 使用基类方法设置关联关系
        relations_data = {
            'tag1_ids': tag1_ids,
            'tag2_ids': tag2_ids,
            'files_ids': all_file_ids
        }
        self._set_relations(resource, relations_data)
        
        return resource


class ResourceUpdateSerializer(BaseFieldsMixin, AuditLogMixin, ResourceBaseSerializer):
    """资源更新序列化器"""
    
    class Meta:
        model = Resource
        fields = [
            'title', 'description', 'type', 'status',
            'tag1_ids', 'tag2_ids'
        ]
        extra_kwargs = BaseFieldsMixin.get_resource_extra_kwargs()
    
    def validate(self, attrs):
        """验证用户权限"""
        user = self.context['request'].user
        resource = self.instance
        
        # 检查是否是资源创建者
        if resource.create_person.user == user:
            return attrs
        
        # 检查是否是组织所有者或管理员
        try:
            org_user = OrganizationUser.objects.get(
                user=user, 
                organization=resource.create_person.organization,
                status='approved'
            )
            if org_user.permission not in ['owner', 'admin']:
                raise serializers.ValidationError("只有资源创建者、组织所有者或管理员可以修改资源")
        except OrganizationUser.DoesNotExist:
            raise serializers.ValidationError("您不是此资源所属组织的成员")
        
        return attrs
    
    def update(self, instance, validated_data):
        """更新资源"""
        # 提取关联数据
        tag1_ids = validated_data.pop('tag1_ids', None)
        tag2_ids = validated_data.pop('tag2_ids', None)
        
        # 更新基本字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # 更新更新人
        user = self.context['request'].user
        org_user = OrganizationUser.objects.filter(user=user, status='approved').first()
        if org_user:
            instance.update_person = org_user
        
        instance.save()
        
        # 设置关联关系（不包含文件，文件操作由虚拟文件系统路由完成）
        relations_data = {
            'tag1_ids': tag1_ids,
            'tag2_ids': tag2_ids,
            'files_ids': None  # 不处理文件关联
        }
        self._set_relations(instance, relations_data, is_update=True)
        
        return instance
from common_utils import build_media_url