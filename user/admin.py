from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    User, Student, StudentKeyword, Tag1, Tag2, Tag1StuMatch, Tag2StuMatch,
    OrganizationUser
)


class StudentInline(admin.StackedInline):
    """学生资料内联"""
    model = Student
    can_delete = False
    verbose_name_plural = '学生资料'
    extra = 0
    fields = [
        ('student_id', 'school'),
        ('major', 'grade', 'education_level'),
        ('status', 'expected_graduation')
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


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """学生用户管理"""
    
    list_display = [
        'id', 'get_user_id', 'get_username', 'get_real_name', 'student_id', 'school', 
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
    inlines = [Tag1StuMatchInline, Tag2StuMatchInline]
    
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
        'user__username', 'user__real_name', 
        'position', 'department', 'organization__name'
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
    
    list_display = ['id', 'value', 'get_student_count']
    search_fields = ['value']
    ordering = ['value']
    
    fieldsets = (
        ('标签信息', {
            'fields': ('value',)
        }),
    )
    
    def get_student_count(self, obj):
        return obj.tag1stumatch_set.count()
    get_student_count.short_description = '关联学生数'


@admin.register(Tag2)
class Tag2Admin(admin.ModelAdmin):
    """能力标签(tag2)管理"""
    
    list_display = ['id', 'post', 'category', 'subcategory', 'specialty', 'level', 'parent', 'get_student_count']
    list_filter = ['category', 'subcategory', 'level']
    search_fields = ['post', 'category', 'subcategory', 'specialty']
    ordering = ['category', 'subcategory', 'specialty']
    
    fieldsets = (
        ('标签信息', {
            'fields': (
                'post',
                ('category', 'subcategory', 'specialty'),
                ('parent', 'level')
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
    )
    
    def get_username(self, obj):
        return obj.student.username
    get_username.short_description = '学生用户名'


@admin.register(Tag1StuMatch)
class Tag1StuMatchAdmin(admin.ModelAdmin):
    """学生兴趣标签关联管理"""
    
    list_display = ['id', 'get_username', 'get_tag_value', 'created_at']
    list_filter = ['created_at']
    search_fields = ['student__user__username', 'student__user__real_name', 'tag1__value']
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
        return obj.student.user.username if obj.student and obj.student.user else '-'
    get_username.short_description = '学生用户名'
    
    def get_tag_value(self, obj):
        return obj.tag1.value if obj.tag1 else '-'
    get_tag_value.short_description = '兴趣标签'


@admin.register(Tag2StuMatch)
class Tag2StuMatchAdmin(admin.ModelAdmin):
    """学生能力标签关联管理"""
    
    list_display = ['id', 'get_username', 'get_tag_info', 'created_at']
    list_filter = ['tag2__category', 'tag2__subcategory', 'created_at']
    search_fields = ['student__user__username', 'student__user__real_name', 'tag2__post', 'tag2__category', 'tag2__subcategory']
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
        return obj.student.user.username if obj.student and obj.student.user else '-'
    get_username.short_description = '学生用户名'
    
    def get_tag_info(self, obj):
        if obj.tag2:
            return f"{obj.tag2.category}-{obj.tag2.subcategory}-{obj.tag2.specialty}"
        return '-'
    get_tag_info.short_description = '能力标签'


# 自定义管理后台标题
admin.site.site_header = '校企对接平台管理后台'
admin.site.site_title = '校企对接平台'
admin.site.index_title = '欢迎使用校企对接平台管理后台'
