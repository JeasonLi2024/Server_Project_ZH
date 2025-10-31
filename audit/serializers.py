from rest_framework import serializers
from .models import RequirementAuditLog, OrganizationAuditLog
from user.models import OrganizationUser
from django.contrib.auth import get_user_model

User = get_user_model()


class RequirementAuditLogSerializer(serializers.ModelSerializer):
    """需求审核历史日志序列化器"""
    
    operator_info = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    old_status_display = serializers.SerializerMethodField()
    new_status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = RequirementAuditLog
        fields = [
            'id', 'requirement', 'operator_info', 'action', 'action_display',
            'old_status', 'old_status_display', 'new_status', 'new_status_display',
            'comment', 'review_details', 'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_operator_info(self, obj):
        """获取操作者信息"""
        if obj.operator:
            return {
                'id': obj.operator.id,
                'username': obj.operator.username,
                'real_name': getattr(obj.operator, 'real_name', ''),
                'role': getattr(obj, 'operator_role', 'unknown')
            }
        return None
    
    def get_old_status_display(self, obj):
        """获取旧状态显示名称"""
        if obj.old_status:
            status_choices = dict(obj.requirement.STATUS_CHOICES)
            return status_choices.get(obj.old_status, obj.old_status)
        return None
    
    def get_new_status_display(self, obj):
        """获取新状态显示名称"""
        if obj.new_status:
            status_choices = dict(obj.requirement.STATUS_CHOICES)
            return status_choices.get(obj.new_status, obj.new_status)
        return None


class OrganizationAuditLogSerializer(serializers.ModelSerializer):
    """组织认证审核历史日志序列化器"""
    
    operator_info = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    old_status_display = serializers.SerializerMethodField()
    new_status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = OrganizationAuditLog
        fields = [
            'id', 'organization', 'operator_info', 'action', 'action_display',
            'old_status', 'old_status_display', 'new_status', 'new_status_display',
            'comment', 'review_details', 'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_operator_info(self, obj):
        """获取操作者信息"""
        if obj.operator:
            return {
                'id': obj.operator.id,
                'username': obj.operator.username,
                'real_name': getattr(obj.operator, 'real_name', ''),
                'role': getattr(obj, 'operator_role', 'unknown')
            }
        return None
    
    def get_old_status_display(self, obj):
        """获取旧状态显示名称"""
        if obj.old_status:
            status_choices = dict(obj.organization.STATUS_CHOICES)
            return status_choices.get(obj.old_status, obj.old_status)
        return None
    
    def get_new_status_display(self, obj):
        """获取新状态显示名称"""
        if obj.new_status:
            status_choices = dict(obj.organization.STATUS_CHOICES)
            return status_choices.get(obj.new_status, obj.new_status)
        return None


class AuditLogListSerializer(serializers.Serializer):
    """审核日志列表查询参数序列化器"""
    
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)
    action = serializers.CharField(required=False, help_text="筛选操作类型")
    operator_id = serializers.IntegerField(required=False, help_text="筛选操作者ID")
    start_date = serializers.DateField(required=False, help_text="开始日期")
    end_date = serializers.DateField(required=False, help_text="结束日期")
    
    def validate(self, data):
        """验证查询参数"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError('开始日期不能晚于结束日期')
        
        return data