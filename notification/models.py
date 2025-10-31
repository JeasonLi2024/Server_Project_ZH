from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

User = get_user_model()


class NotificationType(models.Model):
    """通知类型模型"""
    
    # 通知分类
    CATEGORY_CHOICES = [
        ('system', '系统通知'),
        ('project', '项目通知'),
        ('organization', '组织通知'),
        ('user', '用户通知'),
    ]
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='类型代码'
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='类型名称'
    )
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name='通知分类'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='类型描述'
    )
    
    default_template = models.TextField(
        blank=True,
        verbose_name='默认消息模板'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否启用'
    )
    

    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'notification_type'
        verbose_name = '02-通知类型'
        verbose_name_plural = '02-通知类型'
        ordering = ['category', 'code']
    
    def __str__(self):
        return f'{self.name} ({self.code})'


class Notification(models.Model):
    """通知模型"""
    
    # 通知优先级
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('normal', '普通'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]
    
    # 通知状态
    STATUS_CHOICES = [
        ('pending', '待发送'),
        ('sent', '已发送'),
        ('read', '已读'),
        ('failed', '发送失败'),
    ]
    
    # 通知接收者
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='new_notifications',
        verbose_name='接收者'
    )
    
    # 通知发送者（可选）
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='new_sent_notifications',
        verbose_name='发送者'
    )
    
    # 通知类型
    notification_type = models.ForeignKey(
        NotificationType,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='通知类型'
    )
    
    # 通知标题和内容
    title = models.CharField(
        max_length=200,
        verbose_name='通知标题'
    )
    
    content = models.TextField(
        verbose_name='通知内容'
    )
    
    # 关联对象（使用GenericForeignKey支持任意模型）
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='关联对象类型'
    )
    
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='关联对象ID'
    )
    
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # 通知优先级
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name='优先级'
    )
    
    # 通知状态
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态'
    )
    
    # 是否已读
    is_read = models.BooleanField(
        default=False,
        verbose_name='是否已读'
    )
    
    # 额外数据（JSON格式）
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='额外数据'
    )
    
    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='发送时间'
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='阅读时间'
    )
    
    # 过期时间（可选）
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='过期时间'
    )
    
    class Meta:
        db_table = 'notification'
        verbose_name = '01-通知详情'
        verbose_name_plural = '01-通知详情'
        ordering = ['-created_at']
        
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f'{self.title} -> {self.recipient.username}'
    
    def mark_as_read(self):
        """标记为已读"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.status = 'read'
            self.save(update_fields=['is_read', 'read_at', 'status'])
    
    def mark_as_sent(self):
        """标记为已发送"""
        if self.status == 'pending':
            self.status = 'sent'
            self.sent_at = timezone.now()
            self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_failed(self):
        """标记为发送失败"""
        self.status = 'failed'
        self.save(update_fields=['status'])
    
    @property
    def is_expired(self):
        """检查是否已过期"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class NotificationTemplate(models.Model):
    """通知模板模型"""
    
    notification_type = models.OneToOneField(
        NotificationType,
        on_delete=models.CASCADE,
        related_name='notification_template',
        verbose_name='通知类型'
    )
    
    title_template = models.CharField(
        max_length=200,
        verbose_name='标题模板'
    )
    
    content_template = models.TextField(
        verbose_name='内容模板'
    )
    
    # 邮件模板字段
    email_subject = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='邮件主题模板'
    )
    
    email_content = models.TextField(
        blank=True,
        verbose_name='邮件内容模板'
    )
    
    # 短信模板字段
    sms_content = models.TextField(
        blank=True,
        verbose_name='短信内容模板'
    )
    
    # 模板变量说明
    variables = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='模板变量'
    )
    

    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        db_table = 'notification_template'
        verbose_name = '03-通知模板'
        verbose_name_plural = '03-通知模板'
    
    def __str__(self):
        return f'{self.notification_type.name} 模板'


class NotificationPreference(models.Model):
    """用户通知偏好设置"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preference',
        verbose_name='用户'
    )
    
    # 通知方式偏好
    enable_websocket = models.BooleanField(
        default=True,
        verbose_name='启用实时通知'
    )
    
    enable_email = models.BooleanField(
        default=False,
        verbose_name='启用邮件通知'
    )
    
    enable_sms = models.BooleanField(
        default=False,
        verbose_name='启用短信通知'
    )
    
    # 通知类型偏好（JSON格式存储各类型的开关状态）
    type_preferences = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='类型偏好设置'
    )
    
    # 免打扰时间段
    quiet_start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='免打扰开始时间'
    )
    
    quiet_end_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='免打扰结束时间'
    )
    
    # 一键免打扰功能
    do_not_disturb = models.BooleanField(
        default=False,
        verbose_name='一键免打扰'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        db_table = 'notification_preference'
        verbose_name = '04-通知偏好设置'
        verbose_name_plural = '04-通知偏好设置'
    
    def __str__(self):
        return f'{self.user.username} 的通知偏好'
    
    def is_type_enabled(self, notification_type_code):
        """检查指定类型的通知是否启用"""
        return self.type_preferences.get(notification_type_code, True)
    
    def is_in_quiet_time(self):
        """检查当前是否在免打扰时间段"""
        # 检查一键免打扰功能
        if self.do_not_disturb:
            return True
        
        # 检查时间段免打扰
        if not self.quiet_start_time or not self.quiet_end_time:
            return False
        
        now_time = timezone.now().time()
        
        if self.quiet_start_time <= self.quiet_end_time:
            # 同一天内的时间段
            return self.quiet_start_time <= now_time <= self.quiet_end_time
        else:
            # 跨天的时间段
            return now_time >= self.quiet_start_time or now_time <= self.quiet_end_time


class NotificationLog(models.Model):
    """通知发送日志"""
    
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='通知'
    )
    
    action = models.CharField(
        max_length=50,
        verbose_name='操作类型'
    )
    
    result = models.CharField(
        max_length=20,
        choices=[
            ('success', '成功'),
            ('failed', '失败'),
            ('skipped', '跳过'),
        ],
        verbose_name='操作结果'
    )
    
    message = models.TextField(
        blank=True,
        verbose_name='日志消息'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'notification_log'
        verbose_name = '05-通知日志'
        verbose_name_plural = '05-通知日志'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.notification.title} - {self.action} - {self.result}'
