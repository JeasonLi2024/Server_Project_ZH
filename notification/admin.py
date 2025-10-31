from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django import forms
from .models import (
    NotificationType,
    Notification,
    NotificationTemplate,
    NotificationPreference,
    NotificationLog
)
from .services import notification_service

User = get_user_model()


class SystemBroadcastForm(forms.ModelForm):
    """系统广播表单 - 基于Notification模型"""
    
    class Meta:
        model = Notification
        fields = ['title', 'content', 'priority', 'expires_at']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '请输入通知标题',
                'maxlength': '200'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 6, 
                'placeholder': '请输入通知内容'
            }),
            'priority': forms.Select(attrs={'class': 'form-control', 'style': 'color: #000000; background-color: #ffffff;'}),
            'expires_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }
    
    # 自定义字段
    BROADCAST_TYPE_CHOICES = [
        ('system_announcement', '系统公告'),
        ('maintenance_notice', '维护通知'),
        ('version_update', '版本更新'),
        ('urgent_notice', '紧急通知'),
    ]
    
    broadcast_type = forms.ChoiceField(
        choices=BROADCAST_TYPE_CHOICES,
        initial='system_announcement',
        label='广播类型',
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'color: #000000; background-color: #ffffff;'})
    )
    
    TARGET_USERS_CHOICES = [
        ('all', '所有用户'),
        ('active', '仅活跃用户'),
        ('staff', '仅系统管理员'),
        ('student', '仅学生用户'),
        ('organization', '仅组织用户'),
    ]
    
    target_users = forms.ChoiceField(
        choices=TARGET_USERS_CHOICES,
        initial='all',
        label='目标用户',
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'color: #000000; background-color: #ffffff;'})
    )
    
    send_email = forms.BooleanField(
        required=False,
        initial=False,
        label='同时发送邮件',
        help_text='是否同时通过邮件发送给所有用户',
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 设置默认值
        self.fields['priority'].initial = 'normal'
        self.fields['expires_at'].initial = timezone.now() + timezone.timedelta(hours=24)


@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    """通知类型管理"""
    list_display = ['id', 'name', 'code', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['category', 'name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'code', 'description')
        }),
        ('分类', {
            'fields': ('category',)
        }),
        ('状态', {
            'fields': ('is_active',)
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


class NotificationLogInline(admin.TabularInline):
    """通知日志内联"""
    model = NotificationLog
    extra = 0
    readonly_fields = ['action', 'result', 'message', 'created_at']
    can_delete = False
    
    def has_delete_permission(self, request, obj=None):
        return False



@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """通知管理"""
    list_display = [
        'id', 'title', 'recipient_info', 'sender_info', 'notification_type',
        'priority', 'status', 'is_read', 'created_at'
    ]
    list_filter = [
        'notification_type', 'priority', 'status', 'is_read',
        'created_at', 'expires_at'
    ]
    search_fields = ['title', 'content', 'recipient__username', 'sender__username']
    ordering = ['-created_at']
    readonly_fields = [
        'created_at', 'sent_at', 'read_at',
        'content_type', 'object_id'
    ]
    inlines = [NotificationLogInline]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'content')
        }),
        ('用户信息', {
            'fields': ('recipient', 'sender')
        }),
        ('通知设置', {
            'fields': ('notification_type', 'priority', 'expires_at')
        }),
        ('状态信息', {
            'fields': ('status', 'is_read')
        }),
        ('关联对象', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('扩展数据', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'sent_at', 'read_at'),
            'classes': ('collapse',)
        })
    )
    
    def recipient_info(self, obj):
        """接收者信息"""
        if obj.recipient:
            url = reverse('admin:user_user_change', args=[obj.recipient.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.recipient.username
            )
        return '-'
    recipient_info.short_description = '接收者'
    
    def sender_info(self, obj):
        """发送者信息"""
        if obj.sender:
            url = reverse('admin:user_user_change', args=[obj.sender.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.sender.username
            )
        return '系统'
    sender_info.short_description = '发送者'
    
    def get_queryset(self, request):
        """优化查询"""
        return super().get_queryset(request).select_related(
            'recipient', 'sender', 'notification_type', 'content_type'
        )
    
    actions = ['mark_as_read', 'mark_as_unread', 'delete_read_notifications']
    
    def mark_as_read(self, request, queryset):
        """批量标记为已读"""
        updated = queryset.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        self.message_user(request, f'已标记 {updated} 条通知为已读')
    mark_as_read.short_description = '标记为已读'
    
    def mark_as_unread(self, request, queryset):
        """批量标记为未读"""
        updated = queryset.filter(is_read=True).update(
            is_read=False,
            read_at=None
        )
        self.message_user(request, f'已标记 {updated} 条通知为未读')
    mark_as_unread.short_description = '标记为未读'
    
    def delete_read_notifications(self, request, queryset):
        """删除已读通知"""
        deleted_count = queryset.filter(is_read=True).delete()[0]
        self.message_user(request, f'已删除 {deleted_count} 条已读通知')
    delete_read_notifications.short_description = '删除已读通知'
    
    def changelist_view(self, request, extra_context=None):
        """自定义列表页面，添加系统广播按钮"""
        extra_context = extra_context or {}
        extra_context['show_system_broadcast_button'] = True
        return super().changelist_view(request, extra_context)
    
    def get_urls(self):
        """添加自定义URL"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('system-broadcast/', self.admin_site.admin_view(self.system_broadcast_view), name='system_broadcast'),
            path('get-broadcast-template/', self.admin_site.admin_view(self.get_broadcast_template), name='get_broadcast_template'),
        ]
        return custom_urls + urls
    
    def system_broadcast_view(self, request):
        """系统广播视图"""
        if request.method == 'POST':
            form = SystemBroadcastForm(request.POST)
            if form.is_valid():
                return self._send_system_broadcast(request, form)
            # 表单验证失败时，保留用户输入的值
        else:
            form = SystemBroadcastForm()
        
        context = {
            'title': '发送系统广播通知',
            'form': form,
            'opts': self.model._meta,
            'has_change_permission': True,
        }
        return render(request, 'admin/notification/system_broadcast.html', context)
    
    def get_broadcast_template(self, request):
        """获取广播类型对应的模板"""
        from django.http import JsonResponse
        
        broadcast_type = request.GET.get('type')
        if not broadcast_type:
            return JsonResponse({'error': '缺少type参数'}, status=400)
        
        # 直接使用预设的模板数据，不依赖数据库
        template_data = {
            'system_announcement': {
                'title': '【系统公告】重要通知',
                'content': '尊敬的用户，\n\n这里是系统公告的内容，请根据实际情况修改：\n\n1. 公告的主要内容\n2. 相关说明事项\n3. 注意事项\n\n感谢您的关注！\n\n系统管理团队'
            },
            'maintenance_notice': {
                'title': '【维护通知】系统维护公告',
                'content': '尊敬的用户，\n\n我们将进行系统维护，具体安排如下：\n\n维护时间：[请填写具体时间]\n维护内容：[请填写维护内容]\n影响范围：[请填写影响范围]\n\n维护期间系统可能暂时无法访问，请提前做好相关准备。\n\n如有疑问，请联系技术支持。\n\n系统管理团队'
            },
            'version_update': {
                'title': '【版本更新】系统升级通知',
                'content': '尊敬的用户，\n\n系统已更新至新版本，主要更新内容：\n\n🎉 新功能：\n- [请填写新功能1]\n- [请填写新功能2]\n\n🔧 改进：\n- [请填写改进内容1]\n- [请填写改进内容2]\n\n🐛 修复：\n- [请填写修复内容]\n\n立即体验新功能！\n\n系统管理团队'
            },
            'urgent_notice': {
                'title': '【紧急通知】重要提醒',
                'content': '⚠️ 紧急通知 ⚠️\n\n尊敬的用户，\n\n[请填写紧急通知的具体内容]\n\n请立即关注并采取相应措施：\n1. [请填写需要采取的措施1]\n2. [请填写需要采取的措施2]\n\n如有疑问，请立即联系我们。\n\n系统管理团队'
            }
        }
        
        if broadcast_type in template_data:
            return JsonResponse({
                'success': True,
                'template': template_data[broadcast_type]
            })
        else:
            return JsonResponse({
                'success': True,
                'template': {
                    'title': '【通知】',
                    'content': '请填写通知内容...'
                }
            })
    
    def _send_system_broadcast(self, request, form):
        """执行系统广播发送"""
        try:
            # 获取表单数据
            broadcast_type = form.cleaned_data['broadcast_type']
            title = form.cleaned_data['title']
            content = form.cleaned_data['content']
            priority = form.cleaned_data['priority']
            expires_at = form.cleaned_data['expires_at']
            send_email = form.cleaned_data['send_email']
            target_users = form.cleaned_data['target_users']
            
            # 获取目标用户
            if target_users == 'all':
                recipients = User.objects.filter(is_active=True)
            elif target_users == 'active':
                # 假设最近30天登录的用户为活跃用户
                from datetime import timedelta
                active_since = timezone.now() - timedelta(days=30)
                recipients = User.objects.filter(
                    is_active=True,
                    last_login__gte=active_since
                )
            elif target_users == 'staff':
                recipients = User.objects.filter(is_active=True, is_staff=True)
            elif target_users == 'student':
                recipients = User.objects.filter(is_active=True, user_type='student')
            elif target_users == 'organization':
                recipients = User.objects.filter(is_active=True, user_type='organization')
            else:
                recipients = User.objects.filter(is_active=True)
            
            # 确定发送策略
            strategies = ['websocket']
            if send_email:
                strategies.append('email')
            
            # 批量发送通知
            notifications = notification_service.bulk_create_and_send_notifications(
                recipients=list(recipients),
                notification_type_code=broadcast_type,
                title=title,
                content=content,
                sender=request.user,
                priority=priority,
                expires_at=expires_at,
                strategies=strategies
            )
            
            # 统计发送结果
            success_count = len([n for n in notifications if n is not None])
            total_count = recipients.count()
            
            if success_count > 0:
                messages.success(
                    request,
                    f'系统广播发送成功！共发送给 {success_count}/{total_count} 个用户'
                )
            else:
                messages.error(request, '系统广播发送失败，请检查通知类型配置')
                
        except Exception as e:
            messages.error(request, f'发送系统广播时出错：{str(e)}')
        
        return HttpResponseRedirect('/admin/notification/notification/')


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """通知模板管理"""
    list_display = ['notification_type', 'title_template', 'created_at']
    list_filter = ['notification_type', 'created_at']
    search_fields = ['title_template', 'content_template']
    ordering = ['notification_type']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('notification_type',)
        }),
        ('模板内容', {
            'fields': ('title_template', 'content_template')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """自定义表单"""
        form = super().get_form(request, obj, **kwargs)
        # 为模板字段添加帮助文本
        form.base_fields['title_template'].help_text = (
            '支持Django模板语法，例如：{{ user_name }}'
        )
        form.base_fields['content_template'].help_text = (
            '支持Django模板语法，可以使用HTML标签'
        )
        return form


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """通知偏好设置管理"""
    list_display = [
        'user_info', 'enable_websocket', 'enable_email', 'enable_sms',
        'quiet_start_time', 'quiet_end_time', 'updated_at'
    ]
    list_filter = [
        'enable_websocket', 'enable_email', 'enable_sms',
        'updated_at'
    ]
    search_fields = ['user__username', 'user__email']
    ordering = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('通知方式', {
            'fields': ('enable_websocket', 'enable_email', 'enable_sms')
        }),
        ('免打扰设置', {
            'fields': ('quiet_start_time', 'quiet_end_time')
        }),
        ('类型偏好', {
            'fields': ('type_preferences',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def user_info(self, obj):
        """用户信息"""
        if obj.user:
            url = reverse('admin:user_user_change', args=[obj.user.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.user.username
            )
        return '-'
    user_info.short_description = '用户'
    
    def get_queryset(self, request):
        """优化查询"""
        return super().get_queryset(request).select_related('user')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """通知日志管理"""
    list_display = [
        'notification_info', 'action', 'result', 'message_short', 'created_at'
    ]
    list_filter = ['action', 'result', 'created_at']
    search_fields = ['notification__title', 'message']
    ordering = ['-created_at']
    readonly_fields = ['notification', 'action', 'result', 'message', 'created_at']
    
    def notification_info(self, obj):
        """通知信息"""
        if obj.notification:
            url = reverse('admin:notification_notification_change', args=[obj.notification.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.notification.title[:50] + '...' if len(obj.notification.title) > 50 else obj.notification.title
            )
        return '-'
    notification_info.short_description = '通知'
    
    def message_short(self, obj):
        """消息简短显示"""
        if obj.message:
            return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
        return '-'
    message_short.short_description = '消息'
    
    def get_queryset(self, request):
        """优化查询"""
        return super().get_queryset(request).select_related('notification')
    
    def has_add_permission(self, request):
        """禁止手动添加日志"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改日志"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """允许删除日志"""
        return True
