from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from .models import (
    Notification,
    NotificationType,
    NotificationTemplate,
    NotificationPreference,
    NotificationLog
)

User = get_user_model()


class NotificationTypeSerializer(serializers.ModelSerializer):
    """通知类型序列化器"""
    
    class Meta:
        model = NotificationType
        fields = [
            'id', 'code', 'name', 'category', 'description',
            'default_template', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at']


class NotificationSerializer(serializers.ModelSerializer):
    """通知序列化器"""
    
    recipient_name = serializers.CharField(source='recipient.real_name', read_only=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    sender_name = serializers.CharField(source='sender.real_name', read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    notification_type_name = serializers.CharField(source='notification_type.name', read_only=True)
    notification_type_code = serializers.CharField(source='notification_type.code', read_only=True)
    
    # 关联对象信息
    related_object_type = serializers.CharField(source='content_type.model', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name', 'recipient_username',
            'sender', 'sender_name', 'sender_username',
            'notification_type', 'notification_type_name', 'notification_type_code',
            'title', 'content', 'priority', 'status', 'is_read',
            'content_type', 'object_id', 'related_object_type',
            'extra_data', 'created_at', 'sent_at', 'read_at', 'expires_at'
        ]
        read_only_fields = [
            'created_at', 'sent_at', 'read_at', 'recipient_name',
            'recipient_username', 'sender_name', 'sender_username',
            'notification_type_name', 'notification_type_code',
            'related_object_type'
        ]
    
    def to_representation(self, instance):
        """自定义序列化输出"""
        data = super().to_representation(instance)
        
        # 添加关联对象的详细信息
        if instance.related_object:
            try:
                if hasattr(instance.related_object, 'title'):
                    data['related_object_title'] = instance.related_object.title
                elif hasattr(instance.related_object, 'name'):
                    data['related_object_title'] = instance.related_object.name
                else:
                    data['related_object_title'] = str(instance.related_object)
            except Exception:
                data['related_object_title'] = None
        
        return data


class NotificationCreateSerializer(serializers.ModelSerializer):
    """通知创建序列化器"""
    
    notification_type_code = serializers.CharField(write_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'recipient', 'sender', 'notification_type_code',
            'title', 'content', 'priority',
            'content_type', 'object_id', 'extra_data', 'expires_at'
        ]
    
    def validate_notification_type_code(self, value):
        """验证通知类型代码"""
        try:
            notification_type = NotificationType.objects.get(code=value, is_active=True)
            return notification_type
        except NotificationType.DoesNotExist:
            raise serializers.ValidationError(f'通知类型 {value} 不存在或未启用')
    
    def create(self, validated_data):
        """创建通知"""
        notification_type = validated_data.pop('notification_type_code')
        validated_data['notification_type'] = notification_type
        return super().create(validated_data)


class NotificationUpdateSerializer(serializers.ModelSerializer):
    """通知更新序列化器"""
    
    class Meta:
        model = Notification
        fields = ['is_read', 'status']
    
    def update(self, instance, validated_data):
        """更新通知状态"""
        if validated_data.get('is_read') and not instance.is_read:
            instance.mark_as_read()
        elif 'status' in validated_data:
            status = validated_data['status']
            if status == 'sent' and instance.status == 'pending':
                instance.mark_as_sent()
            elif status == 'failed':
                instance.mark_as_failed()
        
        return super().update(instance, validated_data)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """通知模板序列化器"""
    
    notification_type_name = serializers.CharField(source='notification_type.name', read_only=True)
    notification_type_code = serializers.CharField(source='notification_type.code', read_only=True)
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'notification_type', 'notification_type_name', 'notification_type_code',
            'title_template', 'content_template', 'variables',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'notification_type_name', 'notification_type_code']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """通知偏好设置序列化器"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'enable_websocket', 'enable_email', 'enable_sms',
            'type_preferences', 'quiet_start_time', 'quiet_end_time',
            'do_not_disturb', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        """验证免打扰时间设置"""
        quiet_start = data.get('quiet_start_time')
        quiet_end = data.get('quiet_end_time')
        
        if (quiet_start and not quiet_end) or (not quiet_start and quiet_end):
            raise serializers.ValidationError('免打扰开始时间和结束时间必须同时设置')
        
        return data
    
    def to_representation(self, instance):
        """自定义序列化输出，确保显示所有通知类型的偏好设置"""
        data = super().to_representation(instance)
        
        # 获取所有活跃的通知类型
        active_notification_types = NotificationType.objects.filter(
            is_active=True
        ).values_list('code', flat=True)
        
        # 构建完整的type_preferences，包含所有通知类型
        complete_type_preferences = {}
        for type_code in active_notification_types:
            # 如果用户已设置该类型的偏好，使用用户设置；否则使用默认值True
            complete_type_preferences[type_code] = instance.type_preferences.get(type_code, True)
        
        data['type_preferences'] = complete_type_preferences
        return data


class NotificationLogSerializer(serializers.ModelSerializer):
    """通知日志序列化器"""
    
    notification_title = serializers.CharField(source='notification.title', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification', 'notification_title',
            'action', 'result', 'message', 'created_at'
        ]
        read_only_fields = ['created_at', 'notification_title']


class NotificationStatsSerializer(serializers.Serializer):
    """通知统计序列化器"""
    
    total_count = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    read_count = serializers.IntegerField()
    today_count = serializers.IntegerField()
    this_week_count = serializers.IntegerField()
    
    # 按类型统计
    type_stats = serializers.DictField()
    
    # 按优先级统计
    priority_stats = serializers.DictField()


class BulkNotificationSerializer(serializers.Serializer):
    """批量通知序列化器"""
    
    recipients = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text='接收者用户ID列表'
    )
    
    notification_type_code = serializers.CharField(
        help_text='通知类型代码'
    )
    
    title = serializers.CharField(
        max_length=200,
        help_text='通知标题'
    )
    
    content = serializers.CharField(
        help_text='通知内容'
    )
    
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        default='normal',
        help_text='优先级'
    )
    
    extra_data = serializers.JSONField(
        required=False,
        default=dict,
        help_text='额外数据'
    )
    
    expires_at = serializers.DateTimeField(
        required=False,
        help_text='过期时间'
    )
    
    def validate_recipients(self, value):
        """验证接收者列表"""
        if len(value) > 1000:  # 限制批量发送数量
            raise serializers.ValidationError('单次批量发送不能超过1000个用户')
        
        # 验证用户是否存在
        existing_users = User.objects.filter(id__in=value).values_list('id', flat=True)
        invalid_users = set(value) - set(existing_users)
        
        if invalid_users:
            raise serializers.ValidationError(f'以下用户ID不存在: {list(invalid_users)}')
        
        return value
    
    def validate_notification_type_code(self, value):
        """验证通知类型代码"""
        try:
            notification_type = NotificationType.objects.get(code=value, is_active=True)
            return notification_type
        except NotificationType.DoesNotExist:
            raise serializers.ValidationError(f'通知类型 {value} 不存在或未启用')