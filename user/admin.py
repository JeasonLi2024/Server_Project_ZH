from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    User, Student, StudentKeyword, Tag1, Tag2, Tag1StuMatch, Tag2StuMatch,
    OrganizationUser
)


class StudentInline(admin.StackedInline):
    """学生资料内联编辑"""
    model = Student
    can_delete = False
    verbose_name_plural = '学生资料'
    extra = 0
    fields = [
        ('student_id', 'school'),
        ('major', 'grade', 'education_level'),
        ('status', 'expected_graduation')
    ]


class OrganizationUserInline(admin.StackedInline):
    """组织用户资料内联编辑"""
    model = OrganizationUser
    can_delete = False
    verbose_name_plural = '组织用户资料'
    extra = 0
    fields = [
        'organization',
        ('position', 'department', 'permission', 'status'),
        ('created_at', 'updated_at')
    ]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """用户管理"""
    
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


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """学生管理"""
    
    list_display = [
        'id', 'get_username', 'get_real_name', 'student_id', 'school', 
        'major', 'grade', 'status', 'created_at'
    ]
    list_filter = [
        'school', 'major', 'grade', 'education_level', 'status', 'created_at'
    ]
    search_fields = [
        'user__username', 'user__real_name', 'student_id', 
        'school', 'major'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('关联用户', {
            'fields': ('user',)
        }),
        ('学籍信息', {
            'fields': (
                ('student_id', 'school'),
                ('major', 'grade', 'education_level'),
                ('status', 'expected_graduation')
            )
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = '用户名'
    
    def get_real_name(self, obj):
        return obj.user.real_name or '-'
    get_real_name.short_description = '真实姓名'



@admin.register(StudentKeyword)
class StudentKeywordAdmin(admin.ModelAdmin):
    """学生关键词管理"""
    
    list_display = ['id', 'get_username', 'tag', 'tag_type', 'created_at']
    list_filter = ['tag_type', 'created_at']
    search_fields = ['student__username', 'student__real_name', 'tag']
    ordering = ['-created_at']
    
    fieldsets = (
        ('关键词信息', {
            'fields': ('student', 'tag', 'tag_type')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_username(self, obj):
        return obj.student.username
    get_username.short_description = '学生用户名'


@admin.register(Tag1)
class Tag1Admin(admin.ModelAdmin):
    """兴趣标签管理"""
    
    list_display = ['id', 'value', 'created_at', 'get_student_count']
    search_fields = ['value']
    ordering = ['value']
    
    fieldsets = (
        ('标签信息', {
            'fields': ('value',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_student_count(self, obj):
        return obj.tag1stumatch_set.count()
    get_student_count.short_description = '关联学生数'


@admin.register(Tag2)
class Tag2Admin(admin.ModelAdmin):
    """能力标签管理"""
    
    list_display = ['id', 'post', 'subclasses', 'subdivision', 'required_number', 'created_at', 'get_student_count']
    list_filter = ['post', 'subclasses', 'created_at']
    search_fields = ['post', 'subclasses', 'subdivision']
    ordering = ['post', 'subclasses', 'subdivision']
    
    fieldsets = (
        ('标签信息', {
            'fields': (
                'post',
                ('subclasses', 'subdivision'),
                ('zhuisu_id', 'required_number')
            )
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_student_count(self, obj):
        return obj.tag2stumatch_set.count()
    get_student_count.short_description = '关联学生数'


@admin.register(Tag1StuMatch)
class Tag1StuMatchAdmin(admin.ModelAdmin):
    """学生兴趣标签关联管理"""
    
    list_display = ['id', 'get_username', 'get_tag_value', 'created_at']
    list_filter = ['created_at']
    search_fields = ['student__username', 'student__real_name', 'tag1__value']
    ordering = ['-created_at']
    
    fieldsets = (
        ('关联信息', {
            'fields': ('student', 'tag1')
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_username(self, obj):
        return obj.student.username
    get_username.short_description = '学生用户名'
    
    def get_tag_value(self, obj):
        return obj.tag1.value
    get_tag_value.short_description = '兴趣标签'


@admin.register(Tag2StuMatch)
class Tag2StuMatchAdmin(admin.ModelAdmin):
    """学生能力标签关联管理"""
    
    list_display = ['id', 'get_username', 'get_tag_info', 'created_at']
    list_filter = ['tag2__post', 'created_at']
    search_fields = ['student__username', 'student__real_name', 'tag2__post', 'tag2__subdivision']
    ordering = ['-created_at']
    
    fieldsets = (
        ('关联信息', {
            'fields': ('student', 'tag2')
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_username(self, obj):
        return obj.student.username
    get_username.short_description = '学生用户名'
    
    def get_tag_info(self, obj):
        return f"{obj.tag2.post} - {obj.tag2.subdivision}"
    get_tag_info.short_description = '能力标签'








@admin.register(OrganizationUser)
class OrganizationUserAdmin(admin.ModelAdmin):
    """组织用户管理"""
    
    list_display = [
        'id', 'get_username', 'get_real_name', 'get_organization_name', 'position', 
        'department', 'permission', 'status', 'created_at'
    ]
    list_filter = [
        'organization__organization_type', 'permission', 'status', 'created_at'
    ]
    search_fields = [
        'user__username', 'user__real_name', 
        'position', 'department', 'organization__name'
    ]
    ordering = ['-created_at']
    
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
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = '用户名'
    
    def get_real_name(self, obj):
        return obj.user.real_name or '-'
    get_real_name.short_description = '真实姓名'
    
    def get_organization_name(self, obj):
        return obj.organization.name
    get_organization_name.short_description = '组织名称'





# 自定义管理后台标题
admin.site.site_header = '校企对接平台管理后台'
admin.site.site_title = '校企对接平台'
admin.site.index_title = '欢迎使用校企对接平台管理后台'
