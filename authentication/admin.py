from django.contrib import admin
from django.utils.html import format_html
from .models import EmailVerificationCode, LoginLog, AccountDeletionLog, OrganizationInvitationCode


# @admin.register(EmailVerificationCode)
# class EmailVerificationCodeAdmin(admin.ModelAdmin):
#     """邮箱验证码管理"""
    
#     list_display = [
#         'email', 'code', 'code_type', 'is_used', 
#         'is_expired_status', 'created_at', 'expires_at'
#     ]
#     list_filter = ['code_type', 'is_used', 'created_at']
#     search_fields = ['email', 'code']
#     ordering = ['-created_at']
#     readonly_fields = ['created_at']
    
#     def has_add_permission(self, request):
#         """禁止手动添加验证码"""
#         return False
    
#     def is_expired_status(self, obj):
#         """显示是否过期"""
#         if obj.is_expired():
#             return format_html('<span style="color: red;">已过期</span>')
#         return format_html('<span style="color: green;">有效</span>')
#     is_expired_status.short_description = '状态'


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    """账户登录日志管理"""
    
    list_display = [
        'get_username', 'login_type', 'ip_address', 
        'is_success', 'created_at'
    ]
    list_filter = [
        'login_type', 'is_success', 'created_at',
        'user__user_type'
    ]
    search_fields = [
        'user__username', 'user__email', 'ip_address'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        """禁止手动添加日志"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改日志"""
        return False
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = '用户名'


@admin.register(AccountDeletionLog)
class AccountDeletionLogAdmin(admin.ModelAdmin):
    """账户注销日志管理"""
    
    list_display = [
        'user_id', 'username', 'email', 'user_type',
        'deletion_type', 'status', 'requested_at', 'processed_at'
    ]
    list_filter = [
        'deletion_type', 'status', 'user_type',
        'requested_at', 'processed_at'
    ]
    search_fields = [
        'username', 'email', 'user_id', 'reason'
    ]
    ordering = ['-requested_at']
    readonly_fields = [
        'user_id', 'username', 'email', 'user_type',
        'requested_at', 'ip_address', 'user_agent'
    ]
    
    def has_add_permission(self, request):
        """禁止手动添加注销日志"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """禁止删除注销日志"""
        return False


@admin.register(OrganizationInvitationCode)
class OrganizationInvitationCodeAdmin(admin.ModelAdmin):
    """企业邀请码管理"""
    
    list_display = [
        'code', 'get_organization_name', 'get_creator_name', 'status',
        'is_expired_status', 'used_count', 'max_uses', 'created_at', 'expires_at'
    ]
    list_filter = [
        'status', 'created_at', 'expires_at',
        'organization', 'created_by'
    ]
    search_fields = [
        'code', 'organization__name', 'created_by__username'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'code', 'created_at', 'updated_at', 'used_count',
        'expiry_notification_sent', 'expired_notification_sent',
        'last_used_notification_at'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('code', 'organization', 'created_by', 'status')
        }),
        ('时间设置', {
            'fields': ('created_at', 'expires_at', 'updated_at')
        }),
        ('使用限制', {
            'fields': ('used_count', 'max_uses')
        }),
        ('通知状态', {
            'fields': (
                'expiry_notification_sent', 'expired_notification_sent',
                'last_used_notification_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_organization_name(self, obj):
        """获取组织名称"""
        return obj.organization.name
    get_organization_name.short_description = '所属组织'
    
    def get_creator_name(self, obj):
        """获取创建者名称"""
        return obj.created_by.username
    get_creator_name.short_description = '创建者'
    
    def is_expired_status(self, obj):
        """显示是否过期"""
        if obj.is_expired():
            return format_html('<span style="color: red;">已过期</span>')
        elif obj.status == 'active':
            return format_html('<span style="color: green;">有效</span>')
        elif obj.status == 'disabled':
            return format_html('<span style="color: orange;">已禁用</span>')
        else:
            return format_html('<span style="color: gray;">{}</span>', obj.get_status_display())
    is_expired_status.short_description = '实际状态'
    
    def has_add_permission(self, request):
        """允许管理员手动创建邀请码"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """允许修改邀请码状态和过期时间"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """允许删除邀请码"""
        return request.user.is_superuser
