from django.contrib import admin
from .models import Project, ProjectMember


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'creator', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'creator__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    # filter_horizontal = ['members']  # 由于使用了through模型，不能使用filter_horizontal
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'creator', 'is_active')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('系统信息', {
            'fields': ('id',),
            'classes': ('collapse',)
        })
    )


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'role', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['project__name', 'user__username']
    readonly_fields = ['id', 'joined_at']
    
    fieldsets = (
        ('成员信息', {
            'fields': ('project', 'user', 'role')
        }),
        ('时间信息', {
            'fields': ('joined_at',),
            'classes': ('collapse',)
        }),
        ('系统信息', {
            'fields': ('id',),
            'classes': ('collapse',)
        })
    )