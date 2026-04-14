from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.crypto import get_random_string
import logging
from .models import (
    User, Student, StudentKeyword, Tag1, Tag2, Tag1StuMatch, Tag2StuMatch,
    OrganizationUser
)

logger = logging.getLogger(__name__)


class StudentInline(admin.StackedInline):
    """学生资料内联"""
    model = Student
    can_delete = False
    verbose_name_plural = '学生资料'
    extra = 0
    fields = [
        ('student_id', 'school'),
        ('major', 'grade', 'education_level'),
        ('status', 'verification'),
        ('edu_email', 'expected_graduation')
    ]


class Tag1StuMatchInline(admin.TabularInline):
    """学生兴趣标签内联"""
    model = Tag1StuMatch
    extra = 0
    verbose_name_plural = '兴趣标签'
    fields = ['tag1']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "tag1":
            kwargs["queryset"] = Tag1.objects.all().order_by('value')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class Tag2StuMatchInline(admin.TabularInline):
    """学生能力标签内联"""
    model = Tag2StuMatch
    extra = 0
    verbose_name_plural = '能力标签'
    fields = ['tag2']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "tag2":
            kwargs["queryset"] = Tag2.objects.filter(level=2).order_by('category', 'subcategory', 'specialty')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class OrganizationUserInline(admin.StackedInline):
    """组织用户资料内联编辑"""
    model = OrganizationUser
    can_delete = False
    verbose_name_plural = '组织用户资料'
    extra = 0
    fields = [
        'organization',
        ('position', 'department', 'permission', 'status')
    ]


# 按照要求的顺序注册模型：用户总览、学生用户、组织用户、兴趣标签、能力标签、学生关键词、学生兴趣标签关联、学生能力标签关联

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """用户总览管理"""
    
    list_display = [
        'id', 'username', 'email', 'real_name', 'user_type', 
        'is_active', 'is_staff', 'date_joined'
    ]
    list_filter = [
        'user_type', 'is_active', 'is_staff', 'is_superuser',
        'gender', 'date_joined'
    ]
    search_fields = ['username', 'email', 'real_name', 'phone']
    ordering = ['-date_joined']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('username', 'email', 'password')
        }),
        ('个人信息', {
            'fields': ('real_name', 'avatar', 'gender', 'age', 'bio')
        }),
        ('联系方式', {
            'fields': ('phone',)
        }),
        ('权限设置', {
            'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('重要日期', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('创建用户', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']
    
    def get_inlines(self, request, obj):
        """根据用户类型显示不同的内联编辑"""
        if obj:
            if obj.user_type == 'student':
                return [StudentInline]
            elif obj.user_type == 'company':
                return [OrganizationUserInline]
        return []
    
    def save_model(self, request, obj, form, change):
        """保存用户模型"""
        super().save_model(request, obj, form, change)
    
    def user_change_password(self, request, id, form_url=''):
        """重写密码修改方法，添加邮件通知功能"""
        from django.contrib.admin.utils import unquote
        from django.contrib.auth.forms import AdminPasswordChangeForm
        from django.contrib.auth import update_session_auth_hash
        from django.http import HttpResponseRedirect
        from django.shortcuts import get_object_or_404
        from django.template.response import TemplateResponse
        from django.urls import reverse
        from django.utils.translation import gettext as _
        
        user = get_object_or_404(self.get_queryset(request), pk=unquote(id))
        
        if request.method == 'POST':
            form = AdminPasswordChangeForm(user, request.POST)
            if form.is_valid():
                # 使用管理员设定的新密码
                new_password = form.cleaned_data['password1']
                form.save()
                
                # 发送邮件通知
                if user.email:
                    try:
                        self.send_password_reset_email(user, new_password)
                        messages.success(
                            request, 
                            f'用户 {user.username} 的密码已重置，新密码已发送至邮箱 {user.email}'
                        )
                    except Exception as e:
                        logger.error(f'密码重置邮件发送失败: {user.email} - {str(e)}')
                        messages.warning(
                            request, 
                            f'密码已重置，但邮件发送失败。新密码：{new_password}'
                        )
                else:
                    messages.warning(
                        request, 
                        f'用户 {user.username} 的密码已重置，但用户未设置邮箱。新密码：{new_password}'
                    )
                
                # 更新会话认证哈希（如果是当前用户）
                update_session_auth_hash(request, form.user)
                
                return HttpResponseRedirect(
                    reverse(
                        '%s:%s_%s_change' % (
                            self.admin_site.name,
                            user._meta.app_label,
                            user._meta.model_name,
                        ),
                        args=(user.pk,),
                    )
                )
        else:
            form = AdminPasswordChangeForm(user)
        
        fieldsets = [(None, {'fields': list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})
        
        context = {
            'title': _('Change password: %s') % user.get_username(),
            'adminForm': adminForm,
            'form_url': form_url,
            'form': form,
            'is_popup': ('_popup' in request.POST or
                        '_popup' in request.GET),
            'add': True,
            'change': False,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_absolute_url': False,
            'opts': self.model._meta,
            'original': user,
            'save_as': False,
            'show_save': True,
            **self.admin_site.each_context(request),
        }
        
        request.current_app = self.admin_site.name
        
        return TemplateResponse(
            request,
            self.change_user_password_template or
            'admin/auth/user/change_password.html',
            context,
        )
    
    def send_password_reset_email(self, user, new_password):
        """发送密码重置邮件通知"""
        subject = '【校企对接平台】管理员重置密码通知'
        
        # 纯文本内容
        text_content = f'''
您好 {user.real_name or user.username}！

您的账户密码已被管理员重置。

新密码：{new_password}

为了您的账户安全，请尽快登录并修改密码。

登录地址：http://100.116.251.123:8000/login/

如有疑问，请联系管理员。

校企对接平台
        '''
        
        # HTML内容（更美观）
        html_content = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; font-size: 28px;">校企对接平台</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">密码重置通知</p>
            </div>
            
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #e9ecef;">
                <p style="font-size: 16px; color: #333; margin-bottom: 20px;">您好 <strong>{user.real_name or user.username}</strong>！</p>
                
                <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #856404; margin: 0 0 10px 0; font-size: 18px;">⚠️ 密码重置通知</h3>
                    <p style="color: #856404; margin: 0; font-size: 14px;">您的账户密码已被管理员重置，请查看下方新密码。</p>
                </div>
                
                <div style="background: #f8f9fa; border-left: 4px solid #007bff; padding: 20px; margin: 20px 0;">
                    <p style="margin: 0 0 10px 0; color: #333; font-size: 16px;">您的新密码：</p>
                    <div style="background: #fff; border: 2px dashed #007bff; padding: 15px; text-align: center; font-family: 'Courier New', monospace; font-size: 20px; font-weight: bold; color: #007bff; letter-spacing: 2px; border-radius: 5px;">
                        {new_password}
                    </div>
                </div>
                
                <div style="background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <h4 style="color: #0c5460; margin: 0 0 10px 0;">🔒 安全提醒</h4>
                    <ul style="color: #0c5460; margin: 0; padding-left: 20px; font-size: 14px;">
                        <li>请尽快登录并修改密码</li>
                        <li>不要将密码告诉他人</li>
                        <li>建议使用包含字母、数字和特殊字符的强密码</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://100.116.251.123:8000/api/v1/auth/login/" 
                       style="background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block; transition: background 0.3s;">
                        立即登录
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                
                <p style="color: #6c757d; font-size: 12px; text-align: center; margin: 0;">
                    如有疑问，请联系管理员 | 此邮件由系统自动发送，请勿回复
                </p>
            </div>
        </div>
        '''
        
        # 创建邮件对象
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        
        # 发送邮件
        msg.send()
        
        logger.info(f'密码重置邮件发送成功: {user.email} - 用户: {user.username}')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """学生用户管理"""
    
    list_display = [
        'id', 'get_user_id', 'get_username', 'get_real_name', 'student_id', 'school', 
        'major', 'grade', 'status', 'verification', 'edu_email', 'created_at'
    ]
    list_filter = [
        'school', 'major', 'grade', 'education_level', 'status', 'verification', 'created_at'
    ]
    search_fields = [
        'user__username',           # 用户名
        'user__real_name',          # 真实姓名
        'student_id',               # 学号
        'school__school',           # 学校名称
        'major',                    # 专业
        'grade',                    # 年级
        'status'                    # 学籍状态
    ]
    ordering = ['-created_at']
    inlines = [Tag1StuMatchInline, Tag2StuMatchInline]
    
    fieldsets = (
        ('关联用户', {
            'fields': ('user',)
        }),
        ('学籍信息', {
            'fields': (
                ('student_id', 'school'),
                ('major', 'grade', 'education_level'),
                ('status', 'verification'),
                ('edu_email', 'expected_graduation')
            )
        }),
    )
    
    def get_user_id(self, obj):
        return obj.user.id if obj.user else '-'
    get_user_id.short_description = '关联用户ID'
    
    def get_username(self, obj):
        return obj.user.username if obj.user else '-'
    get_username.short_description = '用户名'
    
    def get_real_name(self, obj):
        return obj.user.real_name if obj.user else '-'
    get_real_name.short_description = '真实姓名'


@admin.register(OrganizationUser)
class OrganizationUserAdmin(admin.ModelAdmin):
    """组织用户管理"""
    
    list_display = [
        'id', 'get_user_id', 'get_username', 'get_real_name', 'get_organization_name', 'position', 
        'department', 'permission', 'status'
    ]
    list_filter = [
        'organization__organization_type', 'permission', 'status'
    ]
    search_fields = [
        'user__real_name',          # 真实姓名
        'organization__name',       # 组织名称
        'position',                 # 职位
        'department'                # 部门
    ]
    ordering = ['id']
    
    fieldsets = (
        ('关联用户', {
            'fields': ('user',)
        }),
        ('组织信息', {
            'fields': ('organization',)
        }),
        ('职位信息', {
            'fields': ('position', 'department', 'permission', 'status')
        }),
    )
    
    def get_user_id(self, obj):
        return obj.user.id if obj.user else '-'
    get_user_id.short_description = '关联用户ID'
    
    def get_username(self, obj):
        return obj.user.username if obj.user else '-'
    get_username.short_description = '用户名'
    
    def get_real_name(self, obj):
        return obj.user.real_name if obj.user else '-'
    get_real_name.short_description = '真实姓名'
    
    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else '-'
    get_organization_name.short_description = '组织名称'


@admin.register(Tag1)
class Tag1Admin(admin.ModelAdmin):
    """兴趣标签(tag1)管理"""
    
    list_display = ['id', 'value', 'frequency', 'get_student_count']
    search_fields = ['value']
    ordering = ['value']
    
    fieldsets = (
        ('标签信息', {
            'fields': ('value', 'frequency')
        }),
    )
    
    def get_student_count(self, obj):
        return obj.tag1stumatch_set.count()
    get_student_count.short_description = '关联学生数'


@admin.register(Tag2)
class Tag2Admin(admin.ModelAdmin):
    """能力标签(tag2)管理"""
    
    list_display = ['id', 'post', 'category', 'subcategory', 'specialty', 'level', 'parent', 'frequency', 'get_student_count']
    list_filter = ['category', 'subcategory', 'level']
    search_fields = ['post', 'category', 'subcategory', 'specialty']
    ordering = ['category', 'subcategory', 'specialty']
    
    fieldsets = (
        ('标签信息', {
            'fields': (
                'post',
                ('category', 'subcategory', 'specialty'),
                ('parent', 'level'),
                'frequency'
            )
        }),
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = Tag2.objects.filter(level=1)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_student_count(self, obj):
        return obj.tag2stumatch_set.count()
    get_student_count.short_description = '关联学生数'


# @admin.register(StudentKeyword)
# class StudentKeywordAdmin(admin.ModelAdmin):
#     """学生关键词管理"""
    
#     list_display = ['id', 'get_username', 'tag', 'tag_type', 'created_at']
#     list_filter = ['tag_type', 'created_at']
#     search_fields = ['student__username', 'student__real_name', 'tag']
#     ordering = ['-created_at']
    
#     fieldsets = (
#         ('关键词信息', {
#             'fields': ('student', 'tag', 'tag_type')
#         }),
#     )
    
#     def get_username(self, obj):
#         return obj.student.username
#     get_username.short_description = '学生用户名'


# @admin.register(Tag1StuMatch)
# class Tag1StuMatchAdmin(admin.ModelAdmin):
#     """学生兴趣标签关联管理"""
    
#     list_display = ['id', 'get_username', 'get_tag_value', 'created_at']
#     list_filter = ['created_at']
#     search_fields = ['student__user__username', 'student__user__real_name', 'tag1__value']
#     ordering = ['-created_at']
    
#     fieldsets = (
#         ('关联信息', {
#             'fields': ('student', 'tag1')
#         }),
#         ('时间信息', {
#             'fields': ('created_at',),
#             'classes': ('collapse',)
#         }),
#     )
    
#     readonly_fields = ['created_at']
    
#     def get_username(self, obj):
#         return obj.student.user.username if obj.student and obj.student.user else '-'
#     get_username.short_description = '学生用户名'
    
#     def get_tag_value(self, obj):
#         return obj.tag1.value if obj.tag1 else '-'
#     get_tag_value.short_description = '兴趣标签'


# @admin.register(Tag2StuMatch)
# class Tag2StuMatchAdmin(admin.ModelAdmin):
#     """学生能力标签关联管理"""
    
#     list_display = ['id', 'get_username', 'get_tag_info', 'created_at']
#     list_filter = ['tag2__category', 'tag2__subcategory', 'created_at']
#     search_fields = ['student__user__username', 'student__user__real_name', 'tag2__post', 'tag2__category', 'tag2__subcategory']
#     ordering = ['-created_at']
    
#     fieldsets = (
#         ('关联信息', {
#             'fields': ('student', 'tag2')
#         }),
#         ('时间信息', {
#             'fields': ('created_at',),
#             'classes': ('collapse',)
#         }),
#     )
    
#     readonly_fields = ['created_at']
    
#     def get_username(self, obj):
#         return obj.student.user.username if obj.student and obj.student.user else '-'
#     get_username.short_description = '学生用户名'
    
#     def get_tag_info(self, obj):
#         if obj.tag2:
#             return f"{obj.tag2.category}-{obj.tag2.subcategory}-{obj.tag2.specialty}"
#         return '-'
#     get_tag_info.short_description = '能力标签'


# 自定义管理后台标题
admin.site.site_header = '校企对接平台管理后台'
admin.site.site_title = '校企对接平台'
admin.site.index_title = '欢迎使用校企对接平台管理后台'
