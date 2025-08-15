from rest_framework import serializers
from .models import User, Student, OrganizationUser
from authentication.utils import get_default_avatar_url
from common_utils import build_media_url
import os
from django.conf import settings


class AvatarUploadSerializer(serializers.ModelSerializer):
    """头像上传序列化器"""
    avatar = serializers.FileField(required=True)
    
    class Meta:
        model = User
        fields = ['avatar']
    
    def validate_avatar(self, value):
        """验证头像文件"""
        # 检查文件大小 (5MB限制)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("头像文件大小不能超过5MB")
        
        # 检查文件格式
        allowed_extensions = getattr(settings, 'ALLOWED_IMAGE_EXTENSIONS', ['jpg', 'jpeg', 'png', 'gif', 'svg'])
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(f"不支持的文件格式，请上传 {', '.join(allowed_extensions)} 格式的图片")
        
        # 对于非SVG文件，进行图片验证
        if ext != 'svg':
            try:
                from PIL import Image
                # 尝试打开图片文件进行验证
                image = Image.open(value)
                image.verify()
                # 重置文件指针，因为verify()会消耗文件
                value.seek(0)
            except Exception:
                raise serializers.ValidationError("请上传有效图片。您上传的该文件不是图片或者图片已经损坏。")
        else:
            # 对于SVG文件，进行基本的内容验证
            value.seek(0)
            content = value.read().decode('utf-8', errors='ignore')
            value.seek(0)
            if not content.strip().startswith('<svg') or '</svg>' not in content:
                raise serializers.ValidationError("请上传有效的SVG文件。")
        
        return value
    
    def update(self, instance, validated_data):
        """更新用户头像"""
        # 如果用户已有头像，删除旧文件
        if instance.avatar:
            old_avatar_path = instance.avatar.path
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)
        
        # 更新头像
        instance.avatar = validated_data['avatar']
        instance.save()
        return instance


class StudentProfileSerializer(serializers.ModelSerializer):
    """学生资料序列化器"""
    class Meta:
        model = Student
        fields = ['student_id', 'school', 'major', 'grade', 'education_level', 'expected_graduation']

        
class OrganizationUserSerializer(serializers.ModelSerializer):
    """组织用户序列化器"""
    organization = serializers.SerializerMethodField()
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = OrganizationUser
        fields = [
            'id', 'organization', 'position', 'department', 'permission', 'status',
            'created_at', 'updated_at'
        ]
    
    def get_organization(self, obj):
        """获取组织信息"""
        from organization.serializers import OrganizationSerializer
        return OrganizationSerializer(obj.organization).data if obj.organization else None


class UserProfileSerializer(serializers.ModelSerializer):
    """用户资料序列化器 - 返回完整的用户信息，区分学生和企业用户"""
    # 基础字段
    avatar = serializers.SerializerMethodField()
    
    # 根据用户类型返回不同的详细信息
    student_profile = serializers.SerializerMethodField()
    company_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'real_name', 'phone', 'avatar', 
            'gender', 'age', 'bio', 'user_type', 'is_active', 'is_staff',
            'date_joined', 'last_login', 'student_profile', 'company_profile'
        ]
    
    def get_avatar(self, obj):
        """获取头像URL"""
        request = self.context.get('request')
        
        if obj.avatar:
            return build_media_url(obj.avatar, request)
        else:
            # 返回默认头像的完整绝对URL
            default_avatar_path = get_default_avatar_url()
            return build_media_url(default_avatar_path, request)
    
    def get_student_profile(self, obj):
        """获取学生详细信息"""
        if obj.user_type == 'student' and hasattr(obj, 'student_profile'):
            student = obj.student_profile
            return {
                'student_id': student.student_id,
                'school': student.school,
                'major': student.major,
                'grade': student.grade,
                'education_level': student.education_level,
                'education_level_display': student.get_education_level_display(),
                'status': student.status,
                'status_display': student.get_status_display(),
                'expected_graduation': student.expected_graduation,
                'interests': [{'id': tag.id, 'value': tag.value} for tag in student.interests.all()],
                'skills': [{'id': tag.id, 'post': tag.post, 'subclasses': tag.subclasses, 'subdivision': tag.subdivision} for tag in student.skills.all()],
                'created_at': student.created_at,
                'updated_at': student.updated_at
            }
        return None
    
    def get_company_profile(self, obj):
        """获取企业用户详细信息"""
        if obj.user_type == 'organization' and hasattr(obj, 'organization_profile'):
            organization_user = obj.organization_profile
            organization_data = None
            request = self.context.get('request')
            
            if organization_user.organization:
                organization = organization_user.organization
                # 处理logo URL
                logo_url = None
                if organization.logo:
                    if request:
                        logo_url = request.build_absolute_uri(organization.logo.url)
                    else:
                        logo_url = organization.logo.url
                
                organization_data = {
                    'id': str(organization.id),
                    'name': organization.name,
                    'code': organization.code,
                    'leader_name': organization.leader_name,
                    'leader_title': organization.leader_title,
                    'registration_number': organization.registration_number,
                    'organization_type': organization.organization_type,
                    'organization_type_display': organization.get_organization_type_display(),
                    'enterprise_type': organization.enterprise_type,
                    'enterprise_type_display': organization.get_enterprise_type_display() if organization.enterprise_type else None,
                    'university_type': organization.university_type,
                    'university_type_display': organization.get_university_type_display() if organization.university_type else None,
                    'other_type': organization.other_type,
                    'other_type_display': organization.get_other_type_display() if organization.other_type else None,
                    'organization_nature': organization.organization_nature,
                    'organization_nature_display': organization.get_organization_nature_display() if organization.organization_nature else None,
                    'business_scope': organization.business_scope,
                    'regulatory_authority': organization.regulatory_authority,
                    'license_info': organization.license_info,
                    'service_target': organization.service_target,
                    'service_target_display': organization.get_service_target_display() if organization.service_target else None,
                    'industry_or_discipline': organization.industry_or_discipline,
                    'scale': organization.scale,
                    'scale_display': organization.get_scale_display(),
                    'contact_person': organization.contact_person,
                    'contact_position': organization.contact_position,
                    'contact_phone': organization.contact_phone,
                    'contact_email': organization.contact_email,
                    'address': organization.address,
                    'postal_code': organization.postal_code,
                    'description': organization.description,
                    'website': organization.website,
                    'logo': logo_url,
                    'status': organization.status,
                    'status_display': organization.get_status_display(),
                    'verified_at': organization.verified_at,
                    'established_date': organization.established_date,
                    'created_at': organization.created_at,
                    'updated_at': organization.updated_at
                }
            
            return {
                'position': organization_user.position,
                'department': organization_user.department,
                'permission': organization_user.permission,
                'permission_display': organization_user.get_permission_display(),
                'status': organization_user.status,
                'status_display': organization_user.get_status_display(),
                'joined_at': organization_user.created_at,
                'updated_at': organization_user.updated_at,
                'organization': organization_data
            }
        return None


class OrganizationUserUpdateSerializer(serializers.ModelSerializer):
    """组织用户资料更新序列化器"""
    class Meta:
        model = OrganizationUser
        fields = ['position']


class UserUpdateSerializer(serializers.ModelSerializer):
    """用户资料更新序列化器"""
    student_profile = StudentProfileSerializer(required=False)
    organization_user_profile = OrganizationUserUpdateSerializer(required=False)
    
    class Meta:
        model = User
        fields = [
            'username', 'real_name', 'phone', 'avatar', 'gender', 'age', 'bio', 
            'student_profile', 'organization_user_profile'
        ]
    
    def update(self, instance, validated_data):
        # 处理学生资料更新
        student_data = validated_data.pop('student_profile', None)
        if student_data and instance.user_type == 'student':
            student_profile, created = Student.objects.get_or_create(user=instance)
            for attr, value in student_data.items():
                setattr(student_profile, attr, value)
            student_profile.save()
        
        # 处理组织用户资料更新
        organization_user_data = validated_data.pop('organization_user_profile', None)
        if organization_user_data and instance.user_type == 'organization':
            try:
                organization_user_profile = OrganizationUser.objects.get(user=instance)
                for attr, value in organization_user_data.items():
                    setattr(organization_user_profile, attr, value)
                organization_user_profile.save()
            except OrganizationUser.DoesNotExist:
                pass
        
        # 更新用户基本信息
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance