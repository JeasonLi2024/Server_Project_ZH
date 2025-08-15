from django.contrib import admin
from django.utils.html import format_html
from .models import EmailVerificationCode, LoginLog


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    """邮箱验证码管理"""
    
    list_display = [
        'email', 'code', 'code_type', 'is_used', 
        'is_expired_status', 'created_at', 'expires_at'
    ]
    list_filter = ['code_type', 'is_used', 'created_at']
    search_fields = ['email', 'code']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        """禁止手动添加验证码"""
        return False
    
    def is_expired_status(self, obj):
        """显示是否过期"""
        if obj.is_expired():
            return format_html('<span style="color: red;">已过期</span>')
        return format_html('<span style="color: green;">有效</span>')
    is_expired_status.short_description = '状态'


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    """登录日志管理"""
    
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
