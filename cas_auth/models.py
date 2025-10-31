from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class CASAuthLog(models.Model):
    """CAS认证日志模型"""
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失败'),
        ('pending', '处理中'),
    ]
    
    ACTION_CHOICES = [
        ('login', '登录'),
        ('logout', '登出'),
        ('validate', '票据验证'),
    ]
    
    # 基本信息
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                            verbose_name='关联用户', help_text='认证成功后关联的用户')
    cas_user_id = models.CharField('CAS用户ID', max_length=100, blank=True, null=True)
    
    # 认证信息
    action = models.CharField('操作类型', max_length=20, choices=ACTION_CHOICES)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES)
    ticket = models.CharField('CAS票据', max_length=500, blank=True, null=True)
    service_url = models.URLField('服务URL', max_length=500, blank=True, null=True)
    
    # 请求信息
    ip_address = models.GenericIPAddressField('IP地址', blank=True, null=True)
    user_agent = models.TextField('用户代理', blank=True, null=True)
    
    # 结果信息
    error_message = models.TextField('错误信息', blank=True, null=True)
    response_data = models.JSONField('响应数据', blank=True, null=True, 
                                   help_text='CAS服务器返回的原始数据')
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'cas_auth_log'
        verbose_name = 'CAS认证日志'
        verbose_name_plural = 'CAS认证日志'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['cas_user_id', 'created_at']),
            models.Index(fields=['status', 'action']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.get_status_display()} - {self.created_at}"
