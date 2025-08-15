from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, ProjectMember

User = get_user_model()


class ProjectMemberSerializer(serializers.ModelSerializer):
    """项目成员序列化器"""
    user_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'user_info', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']
    
    def get_user_info(self, obj):
        """获取用户基本信息"""
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email,
            'real_name': obj.user.real_name,
            'avatar': obj.user.avatar.url if obj.user.avatar else None,
        }


class ProjectSerializer(serializers.ModelSerializer):
    """项目序列化器"""
    creator_info = serializers.SerializerMethodField()
    members_info = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'creator', 'creator_info',
            'members_info', 'member_count', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']
    
    def get_creator_info(self, obj):
        """获取创建者信息"""
        return {
            'id': obj.creator.id,
            'username': obj.creator.username,
            'email': obj.creator.email,
            'real_name': obj.creator.real_name,
            'avatar': obj.creator.avatar.url if obj.creator.avatar else None,
        }
    
    def get_members_info(self, obj):
        """获取项目成员信息"""
        members = ProjectMember.objects.filter(project=obj).select_related('user')
        return ProjectMemberSerializer(members, many=True).data
    
    def get_member_count(self, obj):
        """获取成员数量"""
        return obj.members.count()
    
    def create(self, validated_data):
        """创建项目时自动设置创建者"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['creator'] = request.user
        
        project = Project.objects.create(**validated_data)
        
        # 自动将创建者添加为项目所有者
        ProjectMember.objects.create(
            project=project,
            user=project.creator,
            role='owner'
        )
        
        return project


class ProjectCreateSerializer(serializers.ModelSerializer):
    """项目创建序列化器"""
    
    class Meta:
        model = Project
        fields = ['name', 'description']
    
    def create(self, validated_data):
        """创建项目"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['creator'] = request.user
        
        project = Project.objects.create(**validated_data)
        
        # 自动将创建者添加为项目所有者
        ProjectMember.objects.create(
            project=project,
            user=project.creator,
            role='owner'
        )
        
        return project


class ProjectUpdateSerializer(serializers.ModelSerializer):
    """项目更新序列化器"""
    
    class Meta:
        model = Project
        fields = ['name', 'description', 'is_active']


class ProjectMemberCreateSerializer(serializers.ModelSerializer):
    """添加项目成员序列化器"""
    
    class Meta:
        model = ProjectMember
        fields = ['user', 'role']
    
    def validate(self, attrs):
        """验证数据"""
        project = self.context.get('project')
        user = attrs.get('user')
        
        # 检查用户是否已经是项目成员
        if ProjectMember.objects.filter(project=project, user=user).exists():
            raise serializers.ValidationError('该用户已经是项目成员')
        
        return attrs
    
    def create(self, validated_data):
        """创建项目成员"""
        project = self.context.get('project')
        validated_data['project'] = project
        return ProjectMember.objects.create(**validated_data)