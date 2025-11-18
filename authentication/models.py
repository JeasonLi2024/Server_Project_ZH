from django.db import models
from django.utils import timezone
from django.conf import settings


class EmailVerificationCode(models.Model):
    """邮箱验证码模型"""
    
    CODE_TYPE_CHOICES = [
        ('register', '注册验证码'),
        ('login', '登录验证码'),
        ('reset_password', '重置密码验证码'),
        ('change_email', '更换邮箱验证码'),
        ('delete_account', '账户注销验证码'),
    ]
    
    email = models.EmailField('邮箱')
    code = models.CharField('验证码', max_length=10)
    code_type = models.CharField('验证码类型', max_length=20, choices=CODE_TYPE_CHOICES)
    is_used = models.BooleanField('是否已使用', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    expires_at = models.DateTimeField('过期时间')
    
    class Meta:
        db_table = 'email_verification_code'
        verbose_name = '00-邮箱验证码'
        verbose_name_plural = '00-邮箱验证码'
        indexes = [
            models.Index(fields=['email', 'code_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.email} - {self.code} ({self.get_code_type_display()})"
    
    def is_expired(self):
        """检查验证码是否过期"""
        return timezone.now() > self.expires_at


class LoginLog(models.Model):
    """登录日志模型"""
    
    LOGIN_TYPE_CHOICES = [
        ('password', '密码登录'),
        ('email_code', '邮箱验证码登录'),
        ('phone_code', '手机验证码登录'),
        ('wechat', '微信登录'),
        ('qq', 'QQ登录'),
        ('cas', 'CAS统一认证'),
        ('register', '注册'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='login_logs', verbose_name='用户')
    login_type = models.CharField('登录方式', max_length=20, choices=LOGIN_TYPE_CHOICES)
    ip_address = models.GenericIPAddressField('IP地址', default='127.0.0.1')
    user_agent = models.TextField('用户代理', blank=True)
    is_success = models.BooleanField('是否成功', default=True)
    failure_reason = models.CharField('失败原因', max_length=200, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'login_log'
        verbose_name = '01-账户登录日志'
        verbose_name_plural = '01-账户登录日志'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_login_type_display()} - {self.created_at}"


class AccountDeletionLog(models.Model):
    """账户注销日志模型"""
    
    DELETION_TYPE_CHOICES = [
        ('user_request', '用户主动注销'),
        ('admin_action', '管理员操作'),
        ('system_cleanup', '系统清理'),
        ('violation', '违规处理'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('approved', '已批准'),
        ('rejected', '已拒绝'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    # 用户信息（保留用于审计）
    user_id = models.IntegerField('用户ID')
    username = models.CharField('用户名', max_length=30)
    email = models.CharField('邮箱', max_length=254)
    user_type = models.CharField('用户类型', max_length=20)
    
    # 注销信息
    deletion_type = models.CharField('注销类型', max_length=20, choices=DELETION_TYPE_CHOICES)
    reason = models.TextField('注销原因', blank=True)
    status = models.CharField('处理状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 操作信息
    requested_by = models.IntegerField('申请人ID', null=True, blank=True)
    processed_by = models.IntegerField('处理人ID', null=True, blank=True)
    ip_address = models.GenericIPAddressField('IP地址', default='127.0.0.1')
    user_agent = models.TextField('用户代理', blank=True)
    
    # 数据处理信息
    data_backup_path = models.CharField('数据备份路径', max_length=500, blank=True)
    is_data_anonymized = models.BooleanField('是否已匿名化', default=False)
    
    # 时间戳
    requested_at = models.DateTimeField('申请时间', auto_now_add=True)
    processed_at = models.DateTimeField('处理时间', null=True, blank=True)
    scheduled_deletion_at = models.DateTimeField('计划删除时间', null=True, blank=True)
    actual_deletion_at = models.DateTimeField('实际删除时间', null=True, blank=True)
    
    class Meta:
        db_table = 'account_deletion_log'
        verbose_name = '02-账户注销日志'
        verbose_name_plural = '02-账户注销日志'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['status']),
            models.Index(fields=['requested_at']),
            models.Index(fields=['scheduled_deletion_at']),
        ]
    
    def __str__(self):
        return f"{self.username} - {self.get_deletion_type_display()} - {self.get_status_display()}"


class OrganizationInvitationCode(models.Model):
    """企业邀请码模型"""
    
    STATUS_CHOICES = [
        ('active', '有效'),
        ('expired', '已过期'),
        ('disabled', '已禁用'),
    ]
    
    # 关联组织
    organization = models.ForeignKey(
        'organization.Organization', 
        on_delete=models.CASCADE, 
        related_name='invitation_codes',
        verbose_name='所属组织'
    )
    
    # 邀请码信息
    code = models.CharField('邀请码', max_length=32, unique=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='active')
    
    # 创建者信息
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_invitation_codes',
        verbose_name='创建者'
    )
    
    # 时间信息
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    expires_at = models.DateTimeField('过期时间')
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    # 使用统计
    used_count = models.PositiveIntegerField('使用次数', default=0)
    max_uses = models.PositiveIntegerField('最大使用次数', default=100, help_text='0表示无限制')
    
    # 通知状态字段（防重复通知）
    expiry_notification_sent = models.BooleanField('即将过期通知已发送', default=False)
    expired_notification_sent = models.BooleanField('已过期通知已发送', default=False)
    last_used_notification_at = models.DateTimeField('最后使用通知时间', null=True, blank=True)
    
    class Meta:
        db_table = 'organization_invitation_code'
        verbose_name = '03-企业邀请码'
        verbose_name_plural = '03-企业邀请码'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['code']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
        ]
        # 确保每个组织同时只有一个有效的邀请码
        constraints = [
            models.UniqueConstraint(
                fields=['organization'],
                condition=models.Q(status='active'),
                name='unique_active_invitation_per_org'
            )
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.code} ({self.get_status_display()})"
    
    def is_expired(self):
        """检查邀请码是否过期"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """检查邀请码是否有效（未过期且状态为active）"""
        return self.status == 'active' and not self.is_expired()
    
    def can_be_used(self):
        """检查邀请码是否可以使用（有效且未达到使用上限）"""
        if not self.is_valid():
            return False
        if self.max_uses == 0:  # 无限制
            return True
        return self.used_count < self.max_uses
    
    def use_code(self):
        """使用邀请码（增加使用次数）"""
        if self.can_be_used():
            self.used_count += 1
            self.last_used_notification_at = timezone.now()
            self.save(update_fields=['used_count', 'last_used_notification_at', 'updated_at'])
            return True
        return False
    
    def expire_code(self):
        """手动过期邀请码"""
        self.status = 'expired'
        self.save(update_fields=['status', 'updated_at'])
    
    def disable_code(self):
        """禁用邀请码"""
        self.status = 'disabled'
        self.save(update_fields=['status', 'updated_at'])
