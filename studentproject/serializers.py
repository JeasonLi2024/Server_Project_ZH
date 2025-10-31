from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.storage import default_storage
from .models import (
    StudentProject,
    ProjectParticipant,
    ProjectDeliverable,
    ProjectComment,
    ProjectInvitation
)
from user.models import Student
from project.models import Requirement, File, generate_unique_filename, get_resource_file_path
from common_utils import build_media_url
from .mixins import AvatarMixin, FilesMixin, LeaderMixin, ContactMixin, StudentBasicFieldsMixin, ReviewMixin, CloudLinkMixin, AuthorInfoMixin
from .utils import ensure_virtual_folder_exists, handle_cloud_links, validate_file_size, validate_file_type
from notification.services import notification_service, org_notification_service
import uuid
import os
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class StudentBasicSerializer(StudentBasicFieldsMixin, serializers.ModelSerializer):
    """学生基本信息序列化器"""
    school = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'school', 'major', 'grade',
            'real_name', 'username', 'avatar'
        ]
    
    def get_school(self, obj):
        """序列化学校信息"""
        if obj.school:
            return {
                'id': obj.school.id,
                'name': obj.school.school
            }
        return None


class StudentContactSerializer(StudentBasicFieldsMixin, serializers.ModelSerializer):
    """学生联系信息序列化器（包含邮箱和手机号）"""
    school = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    
    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'school', 'major', 'grade',
            'real_name', 'username', 'avatar', 'email', 'phone'
        ]
    
    def get_school(self, obj):
        """序列化学校信息"""
        if obj.school:
            return {
                'id': obj.school.id,
                'name': obj.school.school
            }
        return None


class StudentMaskedContactSerializer(StudentBasicFieldsMixin, ContactMixin, serializers.ModelSerializer):
    """学生脱敏联系信息序列化器（邮箱和手机号脱敏）"""
    school = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'school', 'major', 'grade',
            'real_name', 'username', 'avatar', 'email', 'phone'
        ]
    
    def get_school(self, obj):
        """序列化学校信息"""
        if obj.school:
            return {
                'id': obj.school.id,
                'name': obj.school.school
            }
        return None


class RequirementBasicSerializer(serializers.ModelSerializer):
    """需求基本信息序列化器"""
    organization_name = serializers.CharField(
        source='organization.name', read_only=True
    )
    evaluation_criteria_id = serializers.IntegerField(
        source='evaluation_criteria.id', read_only=True
    )
    
    class Meta:
        model = Requirement
        fields = [
            'id', 'title', 'description', 'budget', 'people_count',
            'status', 'organization_name', 'evaluation_criteria_id', 'created_at'
        ]


class ProjectParticipantSerializer(AvatarMixin, serializers.ModelSerializer):
    """项目参与者序列化器"""
    student = StudentBasicSerializer(read_only=True)
    student_id = serializers.IntegerField(write_only=True)

    
    class Meta:
        model = ProjectParticipant
        fields = [
            'id', 'student', 'student_id', 'role', 'status',
        ]


class ProjectParticipantDetailSerializer(AvatarMixin, serializers.ModelSerializer):
    """项目参与者详情序列化器（支持脱敏）"""
    student = serializers.SerializerMethodField()
    student_id = serializers.IntegerField(write_only=True)

    
    class Meta:
        model = ProjectParticipant
        fields = [
            'id', 'student', 'student_id', 'role', 'status',
        ]
    
    def get_student(self, obj):
        """根据权限返回学生信息"""
        request = self.context.get('request')
        project = obj.project
        
        # 如果是项目leader，显示完整信息
        if obj.role == 'leader':
            return StudentContactSerializer(obj.student, context=self.context).data
        
        # 判断当前用户是否有权限查看完整信息
        if self._has_full_access(request, project, obj):
            return StudentContactSerializer(obj.student, context=self.context).data
        else:
            return StudentMaskedContactSerializer(obj.student, context=self.context).data
    
    def _has_full_access(self, request, project, participant):
        """判断是否有完整访问权限"""
        if not request or not request.user.is_authenticated:
            return False
        
        # 项目关联需求所属的组织用户有完整权限
        if hasattr(request.user, 'organization_profile') and project.requirement:
            if request.user.organization_profile.organization == project.requirement.organization:
                return True
        
        # 项目内参与者有完整权限
        if hasattr(request.user, 'student_profile'):
            try:
                ProjectParticipant.objects.get(
                    project=project,
                    student=request.user.student_profile,
                    status='approved'
                )
                return True
            except ProjectParticipant.DoesNotExist:
                pass
        
        return False


class ProjectDeliverableListSerializer(serializers.ModelSerializer):
    """项目成果列表序列化器"""
    submitter = StudentBasicSerializer(read_only=True)
    last_modifier = StudentBasicSerializer(read_only=True)
    file_count = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectDeliverable
        fields = [
            'id', 'title', 'stage_type', 'stage_version', 'is_milestone',
            'submitter', 'last_modifier', 'is_updated', 'is_deprecated',
            'file_count', 'files', 'created_at', 'updated_at'
        ]
    
    def get_file_count(self, obj):
        return obj.files.count()
    
    def get_files(self, obj):
        """获取关联的文件信息"""
        from project.serializers import FileSerializer
        request = self.context.get('request')
        return FileSerializer(obj.files.all(), many=True, context={'request': request}).data


class ProjectDeliverableDetailSerializer(FilesMixin, serializers.ModelSerializer):
    """项目成果详情序列化器"""
    submitter = StudentBasicSerializer(read_only=True)
    last_modifier = StudentBasicSerializer(read_only=True)
    submitter_id = serializers.IntegerField(write_only=True)
    files = serializers.SerializerMethodField()
    parent_deliverable = ProjectDeliverableListSerializer(read_only=True)
    child_versions = ProjectDeliverableListSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProjectDeliverable
        fields = [
            'id', 'title', 'description', 'stage_type', 'version_number',
            'stage_version', 'parent_deliverable', 'child_versions',
            'is_milestone', 'progress_description', 'files',
            'submitter', 'last_modifier', 'submitter_id', 'is_updated', 
            'is_deprecated', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['stage_version', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # 自动设置版本号
        project = validated_data.get('project')
        stage_type = validated_data.get('stage_type')
        
        # 获取下一个版本号
        next_version = ProjectDeliverable.objects.filter(
            project=project,
            stage_type=stage_type
        ).aggregate(
            max_version=serializers.models.Max('version_number')
        )['max_version']
        
        validated_data['version_number'] = (next_version or 0) + 1
        
        return super().create(validated_data)


# 旧的ProjectCommentSerializer已移除，使用下方更完整的版本


class StudentProjectListSerializer(LeaderMixin, serializers.ModelSerializer):
    """学生项目列表序列化器"""
    requirement = RequirementBasicSerializer(read_only=True)
    leader = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    deliverable_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProject
        fields = [
            'id', 'title', 'description', 'requirement', 'status',
            'leader', 'participant_count', 'deliverable_count',
            'created_at', 'updated_at'
        ]
    
    def get_participant_count(self, obj):
        return obj.get_active_participants().count()
    
    def get_deliverable_count(self, obj):
        return obj.deliverables.count()


class StudentProjectDetailSerializer(LeaderMixin, serializers.ModelSerializer):
    """学生项目详情序列化器"""
    requirement = RequirementBasicSerializer(read_only=True)
    requirement_id = serializers.IntegerField(write_only=True)
    participants = serializers.SerializerMethodField()
    deliverables = ProjectDeliverableListSerializer(many=True, read_only=True)
    recent_comments = serializers.SerializerMethodField()
    leader = serializers.SerializerMethodField()
    evaluation_info = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProject
        fields = [
            'id', 'title', 'description', 'requirement', 'requirement_id',
            'status', 'participants', 'deliverables', 'recent_comments',
            'leader', 'evaluation_info', 'is_evaluated', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_evaluated']
    
    def get_participants(self, obj):
        participants = obj.project_participants.filter(status='approved')
        return ProjectParticipantDetailSerializer(
            participants, many=True, context=self.context
        ).data
    
    def get_recent_comments(self, obj):
        recent_comments = obj.comments.all()[:5]
        return ProjectCommentSerializer(recent_comments, many=True, context=self.context).data
    
    def get_evaluation_info(self, obj):
        """获取项目评分信息"""
        try:
            # 导入ProjectEvaluation模型
            from projectscore.models import ProjectEvaluation
            
            # 查找该项目的评分记录
            evaluation = ProjectEvaluation.objects.filter(
                project=obj,
                is_deleted=False
            ).first()
            
            if not evaluation:
                return None
            
            # 检查需求是否已公示评分
            is_published = getattr(obj.requirement, 'evaluation_published', False)
            
            # 基础评分信息（始终显示）
            result = {
                'status': evaluation.status,
                'status_display': evaluation.get_status_display(),
                'evaluator_name': evaluation.evaluator.real_name if evaluation.evaluator else None,
                'evaluated_at': evaluation.updated_at,
                'overall_comment': evaluation.overall_comment if evaluation.status == 'published' else None
            }
            
            # 只有在公示后才显示总成绩和排名信息
            if is_published and evaluation.status == 'published':
                # 获取同需求下所有已公示评分项目的排名
                same_requirement_evaluations = ProjectEvaluation.objects.filter(
                    project__requirement=obj.requirement,
                    is_deleted=False,
                    status='published'
                ).select_related('project').order_by('-weighted_total_score')
                
                # 计算排名
                rank = None
                total_evaluated_projects = same_requirement_evaluations.count()
                
                for index, eval_item in enumerate(same_requirement_evaluations, 1):
                    if eval_item.project.id == obj.id:
                        rank = index
                        break
                
                # 添加成绩和排名信息
                result.update({
                    'total_score': evaluation.total_score,
                    'weighted_total_score': evaluation.weighted_total_score,
                    'rank': rank,
                    'total_evaluated_projects': total_evaluated_projects,
                    'is_published': True
                })
            else:
                # 未公示时不显示成绩和排名
                result.update({
                    'total_score': None,
                    'weighted_total_score': None,
                    'rank': None,
                    'total_evaluated_projects': None,
                    'is_published': False
                })
            
            return result
        except ImportError:
            # 如果projectscore应用不可用，返回None
            return None
        except Exception:
            # 其他异常也返回None，避免影响主要功能
            return None


class StudentProjectCreateSerializer(serializers.ModelSerializer):
    """学生项目创建序列化器"""
    
    class Meta:
        model = StudentProject
        fields = ['title', 'description', 'requirement', 'status']
    
    def validate_requirement(self, value):
        """验证需求是否允许关联"""
        if not value:
            raise serializers.ValidationError("需求不能为空")
        
        # 检查需求是否已经公示评分结果
        if hasattr(value, 'evaluation_published') and value.evaluation_published:
            raise serializers.ValidationError("该需求已公示评分结果，不允许创建新项目")
        
        return value
    
    def create(self, validated_data):
        # 创建项目，如果没有指定状态则默认为draft
        validated_data.setdefault('status', 'draft')
        project = super().create(validated_data)
        return project


class StudentProjectUpdateSerializer(serializers.ModelSerializer):
    """学生项目更新序列化器"""
    
    class Meta:
        model = StudentProject
        fields = ['title', 'description', 'status']
        # requirement字段在更新时通常不允许修改
    
    def update(self, instance, validated_data):
        """更新项目并发送状态变更通知"""
        old_status = instance.status
        updated_instance = super().update(instance, validated_data)
        
        # 注释掉重复的项目状态变更通知发送逻辑
        # 该通知已在views.py的update_project函数中处理
        # if 'status' in validated_data and old_status != updated_instance.status:
        #     if updated_instance.requirement:
        #         try:
        #             org_notification_service.send_project_status_change_notification(
        #                 requirement_creator=updated_instance.requirement.publish_people.user,
        #                 project_title=updated_instance.title,
        #                 old_status=old_status,
        #                 new_status=updated_instance.status,
        #                 project_obj=updated_instance
        #             )
        #         except Exception as e:
        #             logger.error(f"发送项目状态变更通知失败: {str(e)}")
        
        return updated_instance





# 用于申请加入项目的序列化器
class ProjectApplicationSerializer(serializers.Serializer):
    """项目申请序列化器"""
    project_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=ProjectParticipant.ROLE_CHOICES, default='member')
    application_message = serializers.CharField(max_length=500, required=True, allow_blank=False)
    
    def validate_project_id(self, value):
        try:
            project = StudentProject.objects.get(id=value)
            if project.status not in ['recruiting', 'in_progress']:
                raise serializers.ValidationError('该项目当前不接受申请')
            return value
        except StudentProject.DoesNotExist:
            raise serializers.ValidationError('项目不存在')


class ProjectInvitationSerializer(serializers.ModelSerializer):
    """项目邀请序列化器"""
    inviter = StudentBasicSerializer(read_only=True)
    invitee = StudentBasicSerializer(read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    is_expired = serializers.SerializerMethodField()
    can_respond = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectInvitation
        fields = [
            'id', 'project', 'project_title', 'inviter', 'invitee',
            'status', 'invitation_message', 'response_message',
            'created_at', 'responded_at', 'expires_at',
            'is_expired', 'can_respond'
        ]
        read_only_fields = ['created_at', 'responded_at', 'expires_at']
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_can_respond(self, obj):
        return obj.can_respond()


class SendInvitationSerializer(serializers.Serializer):
    """发送邀请序列化器"""
    invitee_username = serializers.CharField(
        max_length=30,
        help_text="被邀请学生的用户名"
    )
    invitation_message = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="邀请留言"
    )
    
    def validate_invitee_username(self, value):
        """验证被邀请者用户名"""
        try:
            # 通过用户名查找用户，并确保是学生用户
            user = User.objects.get(username=value, user_type='student')
            # 确保该用户有对应的学生档案
            student = Student.objects.get(user=user)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError('用户名不存在或该用户不是学生')
        except Student.DoesNotExist:
            raise serializers.ValidationError('该用户没有学生档案')


class InvitationResponseSerializer(serializers.Serializer):
    """邀请响应序列化器"""
    action = serializers.ChoiceField(
        choices=['accept', 'reject'],
        help_text="响应动作：accept(接受) 或 reject(拒绝)"
    )
    response_message = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="响应留言"
    )


# 用于审核申请的序列化器
class ApplicationReviewSerializer(ReviewMixin, serializers.Serializer):
    """申请审核序列化器"""


class BatchApplicationReviewSerializer(ReviewMixin, serializers.Serializer):
    """批量申请审核序列化器"""
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="参与者ID列表"
    )

    def validate_participant_ids(self, value):
        """验证参与者ID列表"""
        if len(value) != len(set(value)):
            raise serializers.ValidationError("参与者ID列表中不能有重复项")
        return value


class ParticipantSerializer(serializers.ModelSerializer):
    """参与者序列化器（支持详情和列表模式）"""
    student = serializers.SerializerMethodField()
    applied_at = serializers.DateTimeField(read_only=True)
    approved_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = ProjectParticipant
        fields = [
            'id', 'student', 'role', 'status', 'application_message',
            'review_message', 'applied_at', 'approved_at'
        ]
    
    def get_student(self, obj):
        """根据上下文返回不同详细程度的学生信息"""
        detail_mode = self.context.get('detail_mode', False)
        if detail_mode:
            return StudentContactSerializer(obj.student, context=self.context).data
        else:
            return StudentBasicSerializer(obj.student, context=self.context).data


# 为了向后兼容，保留别名
ParticipantListSerializer = ParticipantSerializer
ParticipantDetailSerializer = ParticipantSerializer


class ParticipantStatusUpdateSerializer(serializers.Serializer):
    """参与者状态更新序列化器"""
    status = serializers.ChoiceField(
        choices=ProjectParticipant.STATUS_CHOICES,
        help_text="新的参与者状态"
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="状态变更原因"
    )


class UnifiedApplicationReviewSerializer(ReviewMixin, serializers.Serializer):
    """统一申请处理序列化器（支持单个和批量处理）"""
    participant_ids = serializers.CharField(
        help_text="参与者ID，单个ID或多个ID用逗号分隔"
    )

    def validate_participant_ids(self, value):
        """验证参与者ID列表"""
        try:
            # 支持单个ID或逗号分隔的多个ID
            if ',' in value:
                ids = [int(id_str.strip()) for id_str in value.split(',') if id_str.strip()]
            else:
                ids = [int(value.strip())]
            
            if not ids:
                raise serializers.ValidationError("至少需要提供一个参与者ID")
            
            if len(ids) > 50:  # 限制批量处理数量
                raise serializers.ValidationError("一次最多只能处理50个申请")
            
            return ids
        except ValueError:
            raise serializers.ValidationError("参与者ID必须是有效的整数")


class LeadershipTransferSerializer(serializers.Serializer):
    """身份转移序列化器"""
    new_leader_id = serializers.IntegerField(help_text="新负责人的参与者ID")
    transfer_message = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="转移说明消息"
    )

    def validate_new_leader_id(self, value):
        """验证新负责人ID"""
        try:
            participant = ProjectParticipant.objects.get(id=value)
            if participant.status != 'approved':
                raise serializers.ValidationError("只能将负责人权限转移给已批准的参与者")
            if participant.role == 'leader':
                raise serializers.ValidationError("该参与者已经是负责人")
        except ProjectParticipant.DoesNotExist:
            raise serializers.ValidationError("指定的参与者不存在")
        return value


class ProjectDeliverableSubmitSerializer(CloudLinkMixin, serializers.ModelSerializer):
    """项目成果提交序列化器"""
    files_ids = serializers.CharField(
        write_only=True,
        required=False,
        help_text="文件ID列表，逗号分隔（如：1,2,3）"
    )
    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        help_text="直接上传的文件列表（支持form-data格式）"
    )
    
    class Meta:
        model = ProjectDeliverable
        fields = [
            'title', 'description', 'stage_type', 'is_milestone',
            'progress_description', 'notes', 'files_ids', 'uploaded_files',
            'cloud_links', 'cloud_password', 'virtual_folder_path'
        ]
        extra_kwargs = {
            'title': {'required': True},
            'description': {'required': True},
            'stage_type': {'required': True},
        }
    
    def validate_files_ids(self, value):
        """验证文件ID列表"""
        if not value:
            return []
        
        try:
            file_ids = [int(id.strip()) for id in value.split(',') if id.strip()]
        except ValueError:
            raise serializers.ValidationError("文件ID必须为数字")
        
        # 验证文件是否存在
        existing_files = File.objects.filter(id__in=file_ids)
        if len(existing_files) != len(file_ids):
            raise serializers.ValidationError("部分文件不存在")
        
        return file_ids
    
    def validate_cloud_links(self, value):
        """验证网盘链接格式"""
        if not value:
            return value
            
        # 简单的URL格式验证
        if not (value.startswith('http://') or value.startswith('https://')):
            raise serializers.ValidationError("网盘链接URL格式不正确")
        
        return value
    
    def validate(self, attrs):
        """验证整体数据"""
        files_ids = attrs.get('files_ids', [])
        uploaded_files = attrs.get('uploaded_files', [])
        cloud_links = attrs.get('cloud_links', '')
        
        # 至少需要提供一种文件方式
        if not files_ids and not uploaded_files and not cloud_links:
            raise serializers.ValidationError("至少需要提供一种文件（已存在文件、上传文件或网盘链接）")
        
        return attrs
    
    def create(self, validated_data):
        """创建成果记录"""
        # 提取文件相关数据
        files_ids = validated_data.pop('files_ids', [])
        uploaded_files = validated_data.pop('uploaded_files', [])
        cloud_links = validated_data.pop('cloud_links', '')
        cloud_password = validated_data.pop('cloud_password', '')
        virtual_folder_path = validated_data.pop('virtual_folder_path', '/')
        
        # 获取项目和提交者
        project = validated_data.get('project')
        submitter = validated_data.get('submitter')
        
        # 自动设置版本号
        stage_type = validated_data.get('stage_type')
        next_version = ProjectDeliverable.objects.filter(
            project=project,
            stage_type=stage_type
        ).aggregate(
            max_version=serializers.models.Max('version_number')
        )['max_version']
        
        validated_data['version_number'] = (next_version or 0) + 1
        validated_data['stage_version'] = f"{stage_type}_v{validated_data['version_number']}"
        
        # 创建成果记录
        deliverable = super().create(validated_data)
        
        # 处理文件关联
        all_files = []
        
        # 1. 关联已存在的文件
        if files_ids:
            existing_files = File.objects.filter(id__in=files_ids)
            all_files.extend(existing_files)
        
        # 处理文件上传
        if uploaded_files:
            uploaded_file_objects = self._handle_file_upload(
                deliverable, uploaded_files, virtual_folder_path
            )
            all_files.extend(uploaded_file_objects)
        
        # 3. 处理网盘链接
        if cloud_links:
            cloud_link_object = self._handle_cloud_links(
                deliverable, cloud_links, cloud_password, virtual_folder_path
            )
            all_files.append(cloud_link_object)
        
        # 关联所有文件到成果
        deliverable.files.set(all_files)
        
        # 注意：成果提交通知已通过Django信号自动发送，无需在此处重复调用
        # 参见 notification/signals.py 中的 handle_deliverable_submission 函数
        
        return deliverable
    
    def _handle_file_upload(self, deliverable, uploaded_files, virtual_folder_path="/"):
        """处理文件上传"""
        file_objects = []
        
        # 确保虚拟文件夹存在
        ensure_virtual_folder_exists(None, virtual_folder_path)  # 传入None作为project参数
        
        for uploaded_file in uploaded_files:
            # 验证文件
            validate_file_size(uploaded_file)
            validate_file_type(uploaded_file)
            
            # 生成唯一文件名
            unique_filename = generate_unique_filename(uploaded_file.name)
            
            # 构建存储路径
            file_path = get_resource_file_path(None, unique_filename)
            
            # 保存文件
            saved_path = default_storage.save(file_path, uploaded_file)
            
            # 构建虚拟路径
            virtual_path = os.path.join(virtual_folder_path, uploaded_file.name).replace('\\', '/')
            if not virtual_path.startswith('/'):
                virtual_path = '/' + virtual_path
            
            # 创建文件记录
            file_obj = File.objects.create(
                name=uploaded_file.name,
                path=virtual_path,
                real_path=saved_path,
                parent_path=virtual_folder_path,
                is_folder=False,
                is_cloud_link=False,
                size=uploaded_file.size,
                url=saved_path
            )
            
            file_objects.append(file_obj)
        
        return file_objects
    
    def _handle_cloud_links(self, deliverable, cloud_link_url, cloud_password="", virtual_folder_path="/"):
        """处理单个网盘链接"""
        # 确保虚拟文件夹存在
        ensure_virtual_folder_exists(None, virtual_folder_path)  # 传入None作为project参数
        
        # 统一文件名为"网盘链接"
        file_name = "网盘链接"
        
        # 构建虚拟路径
        virtual_path = os.path.join(virtual_folder_path, file_name).replace('\\', '/')
        if not virtual_path.startswith('/'):
            virtual_path = '/' + virtual_path
        
        # 创建网盘链接文件记录
        file_obj = File.objects.create(
            name=file_name,
            url=cloud_link_url,  # 网盘链接直接存储在url字段中
            cloud_password=cloud_password,  # 存储网盘密码
            parent_path=virtual_folder_path,
            is_folder=False,
            is_cloud_link=True,
            size=0  # 网盘链接无法获取大小，不保存实体文件相关字段
        )
        
        return file_obj


class ProjectCommentSerializer(AuthorInfoMixin, serializers.ModelSerializer):
    """项目评论序列化器"""
    author_info = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    is_reply = serializers.SerializerMethodField()
    deliverable_info = serializers.SerializerMethodField()
    parent_comment = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectComment
        fields = [
            'id', 'content', 'author_info', 'parent_comment',
            'reply_count', 'is_reply', 'deliverable_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_reply_count(self, obj):
        """获取回复数量"""
        return obj.get_reply_count()
    
    def get_is_reply(self, obj):
        """判断是否为回复"""
        return obj.is_reply()
    
    def get_deliverable_info(self, obj):
        """获取关联成果信息"""
        if obj.deliverable:
            return {
                'id': obj.deliverable.id,
                'title': obj.deliverable.title,
                'stage_version': obj.deliverable.stage_version
            }
        return None
    
    def get_parent_comment(self, obj):
        """获取父评论信息"""
        if obj.parent_comment:
            from user.serializers import UserBasicSerializer
            from authentication.utils import get_default_avatar_url
            
            request = self.context.get('request')
            author = obj.parent_comment.author
            
            # 处理头像URL，如果用户没有头像则使用默认头像
            if author.avatar:
                author_avatar = build_media_url(author.avatar, request)
            else:
                # 返回默认头像的完整绝对URL
                default_avatar_path = get_default_avatar_url()
                author_avatar = build_media_url(default_avatar_path, request)
            
            return {
                'id': obj.parent_comment.id,
                'author_username': author.username,
                'author_avatar': author_avatar
            }
        return None


class ProjectCommentCreateSerializer(AuthorInfoMixin, serializers.ModelSerializer):
    """创建评论序列化器"""
    
    class Meta:
        model = ProjectComment
        fields = ['content', 'parent_comment']
    
    def validate(self, attrs):
        """验证评论数据"""
        # 验证父评论是否存在且属于同一项目
        parent_comment = attrs.get('parent_comment')
        if parent_comment:
            project = self.context.get('project')
            deliverable = self.context.get('deliverable')
            
            # 父评论必须属于同一项目
            if parent_comment.project != project:
                raise serializers.ValidationError("父评论不属于当前项目")
            
            # 如果是成果级评论，父评论也必须属于同一成果
            if deliverable and parent_comment.deliverable != deliverable:
                raise serializers.ValidationError("父评论不属于当前成果")
            
            # 如果是项目级评论，父评论也必须是项目级的
            if not deliverable and parent_comment.deliverable is not None:
                raise serializers.ValidationError("项目级评论不能回复成果级评论")
        
        return attrs
    
    def create(self, validated_data):
        """创建评论"""
        validated_data['project'] = self.context['project']
        validated_data['deliverable'] = self.context.get('deliverable')
        validated_data['author'] = self.context['request'].user
        comment = super().create(validated_data)
        
        # 发送评语回复通知（情形7：评语被回复时通知评语创建者）
        if comment.parent_comment and comment.parent_comment.author != comment.author:
            # 检查原评语作者是否为组织用户
            if hasattr(comment.parent_comment.author, 'organizationuser_profile'):
                try:
                    # 根据评语类型选择合适的通知方法
                    if comment.deliverable:
                        # 成果级评语回复
                        org_notification_service.send_deliverable_comment_reply_notification(
                            original_commenter=comment.parent_comment.author,
                            replier=comment.author,
                            project=comment.project,
                            deliverable=comment.deliverable,
                            comment_content=comment.content
                        )
                    else:
                        # 项目级评语回复
                        org_notification_service.send_project_comment_reply_notification(
                            original_commenter=comment.parent_comment.author,
                            replier=comment.author,
                            project=comment.project,
                            comment_content=comment.content
                        )
                except Exception as e:
                    logger.error(f"发送评语回复通知失败: {str(e)}")
        
        return comment


class ProjectCommentUpdateSerializer(AuthorInfoMixin, serializers.ModelSerializer):
    """更新评论序列化器"""
    
    class Meta:
        model = ProjectComment
        fields = ['content']
    
    def update(self, instance, validated_data):
        """更新评论内容"""
        instance.content = validated_data.get('content', instance.content)
        instance.save()
        return instance


class ProjectDeliverableUpdateSerializer(CloudLinkMixin, serializers.ModelSerializer):
    """项目成果更新序列化器（不支持修改实体文件）"""
    
    class Meta:
        model = ProjectDeliverable
        fields = [
            'title', 'description', 'progress_description', 'notes',
            'cloud_links', 'cloud_password', 'virtual_folder_path'
        ]
        extra_kwargs = {
            'title': {'required': False},
            'description': {'required': False},
        }
    
    def validate_cloud_links(self, value):
        """验证网盘链接"""
        if not value:
            return []
        
        for link_data in value:
            if not isinstance(link_data, dict):
                raise serializers.ValidationError("网盘链接数据格式错误")
            
            url = link_data.get('url', '').strip()
            if not url:
                raise serializers.ValidationError("网盘链接URL不能为空")
            
            # 简单的URL格式验证
            if not (url.startswith('http://') or url.startswith('https://')):
                raise serializers.ValidationError("网盘链接URL格式不正确")
        
        return value
    
    def update(self, instance, validated_data):
        """更新成果记录"""
        # 提取网盘链接数据
        cloud_links = validated_data.pop('cloud_links', '')
        cloud_password = validated_data.pop('cloud_password', '')
        virtual_folder_path = validated_data.pop('virtual_folder_path', '/')
        
        # 更新基本字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 处理新增的网盘链接
        if cloud_links:
            cloud_link_object = self._handle_cloud_links(
                instance, cloud_links, cloud_password, virtual_folder_path
            )
            # 将新的网盘链接添加到现有文件中
            current_files = list(instance.files.all())
            current_files.append(cloud_link_object)
            instance.files.set(current_files)
        
        return instance
    
    def _handle_cloud_links(self, deliverable, cloud_link_url, cloud_password="", virtual_folder_path="/"):
        """处理单个网盘链接"""
        from .utils import ensure_file_folder_exists
        
        # 确保虚拟文件夹存在
        ensure_file_folder_exists(virtual_folder_path)
        
        # 统一文件名为"网盘链接"
        file_name = "网盘链接"
        
        # 构建虚拟路径
        virtual_path = os.path.join(virtual_folder_path, file_name).replace('\\', '/')
        if not virtual_path.startswith('/'):
            virtual_path = '/' + virtual_path
        
        # 创建网盘链接文件记录
        file_obj = File.objects.create(
            name=file_name,
            url=cloud_link_url,  # 网盘链接直接存储在url字段中
            cloud_password=cloud_password,  # 存储网盘密码
            parent_path=virtual_folder_path,
            is_folder=False,
            is_cloud_link=True,
            size=0  # 网盘链接无法获取大小，不保存实体文件相关字段
        )
        
        return file_obj