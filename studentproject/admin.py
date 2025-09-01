from django.contrib import admin
from .models import (
    StudentProject,
    ProjectParticipant,
    ProjectDeliverable,
    ProjectComment,
)


class ProjectParticipantInline(admin.TabularInline):
    """项目参与者内联显示"""
    model = ProjectParticipant
    extra = 0
    readonly_fields = ['applied_at', 'reviewed_at']
    raw_id_fields = ['student', 'reviewed_by']
    
    def get_student_name(self, obj):
        """获取学生姓名"""
        return obj.student.user.real_name if obj.student else '-'
    get_student_name.short_description = '学生姓名'
    
    def get_student_number(self, obj):
        """获取学号"""
        return obj.student.student_number if obj.student else '-'
    get_student_number.short_description = '学号'
    
    def get_student_email(self, obj):
        """获取学生邮箱"""
        return obj.student.user.email if obj.student else '-'
    get_student_email.short_description = '邮箱'
    
    def get_student_phone(self, obj):
        """获取学生手机号"""
        return obj.student.user.phone if obj.student else '-'
    get_student_phone.short_description = '手机号'
    
    fields = [
        'student', 'role', 'status', 'application_message',
        'reviewed_by', 'review_message', 'applied_at', 'reviewed_at'
    ]


@admin.register(StudentProject)
class StudentProjectAdmin(admin.ModelAdmin):
    """学生项目管理"""
    list_display = [
        'id', 'title', 'requirement', 'status', 'get_leader_name', 
        'get_participant_count', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['title', 'description', 'requirement__title']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['requirement']
    inlines = [ProjectParticipantInline]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'description', 'requirement', 'status')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_leader_name(self, obj):
        """获取项目负责人姓名"""
        leader = obj.get_leader()
        return leader.user.real_name if leader else '无负责人'
    get_leader_name.short_description = '项目负责人'
    
    def get_participant_count(self, obj):
        """获取参与者数量"""
        return obj.get_active_participants().count()
    get_participant_count.short_description = '参与人数'
    
    def get_leader_info(self, obj):
        """获取项目负责人详细信息"""
        leader = obj.get_leader()
        if leader:
            return f"{leader.user.real_name} ({leader.student_number}) - {leader.user.email}"
        return '无负责人'
    get_leader_info.short_description = '负责人详情'


@admin.register(ProjectParticipant)
class ProjectParticipantAdmin(admin.ModelAdmin):
    """项目参与者管理"""
    list_display = [
        'project', 'get_student_name', 'role', 'status', 
        'applied_at', 'reviewed_at'
    ]
    list_filter = ['role', 'status', 'applied_at', 'reviewed_at']
    search_fields = [
        'project__title', 'student__user__real_name', 
        'student__student_number'
    ]
    readonly_fields = ['applied_at', 'reviewed_at']
    raw_id_fields = ['project', 'student', 'reviewed_by']
    
    def get_student_name(self, obj):
        """获取学生姓名"""
        return obj.student.user.real_name
    get_student_name.short_description = '学生姓名'


@admin.register(ProjectDeliverable)
class ProjectDeliverableAdmin(admin.ModelAdmin):
    """项目成果管理"""
    list_display = [
        'id', 'title', 'project', 'stage_version', 'stage_type', 
        'is_milestone', 'get_submitter_name', 'created_at'
    ]
    list_filter = [
        'stage_type', 'is_milestone', 'created_at', 'updated_at'
    ]
    search_fields = [
        'title', 'description', 'project__title', 
        'submitter__user__real_name'
    ]
    readonly_fields = ['stage_version', 'created_at', 'updated_at']
    raw_id_fields = ['project', 'submitter']
    filter_horizontal = ['files']
    
    def get_submitter_name(self, obj):
        """获取提交人姓名"""
        return obj.submitter.user.real_name
    get_submitter_name.short_description = '提交人'


@admin.register(ProjectComment)
class ProjectCommentAdmin(admin.ModelAdmin):
    """项目评价管理"""
    list_display = [
        'id', 'project', 'get_deliverable_info', 'get_author_name', 
        'is_reply', 'created_at'
    ]
    list_filter = ['created_at', 'updated_at']
    search_fields = [
        'content', 'project__title', 'author__real_name',
        'deliverable__title'
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['project', 'deliverable', 'author', 'parent_comment']
    
    def get_author_name(self, obj):
        """获取评论作者姓名"""
        return obj.author.real_name
    get_author_name.short_description = '评论作者'
    
    def get_deliverable_info(self, obj):
        """获取关联成果信息"""
        return obj.deliverable.stage_version if obj.deliverable else '项目评论'
    get_deliverable_info.short_description = '关联成果'