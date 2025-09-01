from django.contrib import admin
from .models import Requirement, Resource, File


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'status', 'organization', 'publish_people', 'evaluation_criteria_display', 'views',
                    'created_at']
    list_filter = ['status', 'created_at', 'organization', 'publish_people', 'evaluation_criteria']
    search_fields = ['title', 'brief', 'description', 'organization__name', 'publish_people__user__username',
                     'publish_people__user__real_name', 'evaluation_criteria__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'get_student_projects_count', 'get_total_participants_count',
                       'get_evaluation_criteria_info']
    filter_horizontal = ['tag1', 'tag2', 'resources', 'files']
    ordering = ['-created_at']

    def get_student_projects_count(self, obj):
        """显示关联的学生项目总数"""
        return obj.student_projects.count()

    get_student_projects_count.short_description = '关联项目总数'

    def get_total_participants_count(self, obj):
        """显示关联项目的总参与人数"""
        from django.db.models import Count
        # 统计所有关联项目的参与人数（状态为approved的）
        total_participants = 0
        for project in obj.student_projects.all():
            total_participants += project.project_participants.filter(status='approved').count()
        return total_participants

    get_total_participants_count.short_description = '总参与人数'

    def evaluation_criteria_display(self, obj):
        """显示评分标准信息"""
        from django.utils.html import format_html
        from django.urls import reverse
        if obj.evaluation_criteria:
            status_color = {
                'active': 'green',
                'inactive': 'orange',
                'draft': 'gray'
            }.get(obj.evaluation_criteria.status, 'black')

            # 创建跳转到评分标准详情页的链接
            criteria_url = reverse('admin:projectscore_evaluationcriteria_change', args=[obj.evaluation_criteria.id])
            return format_html(
                '<a href="{}" style="color: {}; text-decoration: none;" title="点击查看评分标准详情">{}({})</a>',
                criteria_url,
                status_color,
                obj.evaluation_criteria.name,
                obj.evaluation_criteria.get_status_display()
            )
        return format_html('<span style="color: gray;">未设置</span>')

    evaluation_criteria_display.short_description = '评分标准'

    def get_evaluation_criteria_info(self, obj):
        """获取评分标准详细信息"""
        if obj.evaluation_criteria:
            criteria = obj.evaluation_criteria
            indicators_count = criteria.indicators.count()
            total_weight = criteria.get_total_weight()
            info = f"标准名称: {criteria.name}\n"
            info += f"状态: {criteria.get_status_display()}\n"
            info += f"指标数量: {indicators_count}\n"
            info += f"权重总和: {total_weight}%\n"
            info += f"创建时间: {criteria.created_at.strftime('%Y-%m-%d %H:%M')}"

            return info
        return '未设置评分标准'

    get_evaluation_criteria_info.short_description = '评分标准详情'

    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'brief', 'description', 'status')
        }),
        ('组织信息', {
            'fields': ('organization', 'publish_people')
        }),
        ('项目信息', {
            'fields': (
            'budget', 'finish_time', 'support_provided', 'get_student_projects_count', 'get_total_participants_count')
        }),
        ('统计信息', {
            'fields': ('views',)
        }),
        ('标签信息', {
            'fields': ('tag1', 'tag2')
        }),
        ('关联信息', {
            'fields': ('resources', 'files', 'evaluation_criteria', 'get_evaluation_criteria_info')
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


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'type', 'status', 'create_person', 'get_organization', 'downloads', 'views']
    list_filter = ['type', 'status', 'create_person', 'create_person__organization']
    search_fields = ['title', 'description', 'create_person__user__username', 'create_person__user__real_name',
                     'create_person__organization__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    filter_horizontal = ['tag1', 'tag2', 'files']
    ordering = ['-created_at']

    def get_organization(self, obj):
        """获取创建人所属组织"""
        return obj.create_person.organization.name if obj.create_person and obj.create_person.organization else '无组织'

    get_organization.short_description = '所属组织'

    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'description', 'type', 'status')
        }),
        ('标签信息', {
            'fields': ('tag1', 'tag2')
        }),
        ('文件信息', {
            'fields': ('files',)
        }),
        ('统计信息', {
            'fields': ('downloads', 'views')
        }),
        ('创建更新信息', {
            'fields': ('create_person', 'update_person')
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


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'size', 'created_at', 'get_related_requirements', 'get_related_resources',
                    'get_related_deliverables']
    list_filter = ['created_at']
    search_fields = ['name', 'path']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_related_requirements(self, obj):
        """获取关联的需求ID列表"""
        from django.utils.html import format_html
        from django.urls import reverse
        requirements = obj.requirement_set.all()
        if requirements:
            links = []
            for req in requirements:
                req_url = reverse('admin:project_requirement_change', args=[req.id])
                links.append(format_html(
                    '<a href="{}" style="color: blue; text-decoration: none;" title="点击查看需求详情">{}</a>',
                    req_url,
                    req.id
                ))
            return format_html(', '.join(links))
        return '无关联需求'

    get_related_requirements.short_description = '关联需求ID'

    def get_related_resources(self, obj):
        """获取关联的资源ID列表"""
        from django.utils.html import format_html
        from django.urls import reverse
        resources = obj.resource_set.all()
        if resources:
            links = []
            for res in resources:
                res_url = reverse('admin:project_resource_change', args=[res.id])
                links.append(format_html(
                    '<a href="{}" style="color: blue; text-decoration: none;" title="点击查看资源详情">{}</a>',
                    res_url,
                    res.id
                ))
            return format_html(', '.join(links))
        return '无关联资源'

    get_related_resources.short_description = '关联资源ID'

    def get_related_deliverables(self, obj):
        """获取关联的项目成果信息"""
        from django.utils.html import format_html
        from django.urls import reverse
        deliverables = obj.deliverables.all()
        if deliverables:
            links = []
            for deliverable in deliverables:
                # 创建成果详情链接
                deliverable_url = reverse('admin:studentproject_deliverable_change', args=[deliverable.id])
                project_info = f"{deliverable.project.id}-{deliverable.project.title}" if deliverable.project else '未知项目'

                # 如果有项目信息，也创建项目链接
                if deliverable.project:
                    project_url = reverse('admin:studentproject_studentproject_change', args=[deliverable.project.id])
                    project_link = format_html(
                        '<a href="{}" style="color: green; text-decoration: none;" title="点击查看项目详情">{}-{}</a>',
                        project_url,
                        deliverable.project.id,
                        deliverable.project.title
                    )
                    links.append(format_html(
                        '<a href="{}" style="color: blue; text-decoration: none;" title="点击查看成果详情">{}</a>({})',
                        deliverable_url,
                        deliverable.id,
                        project_link
                    ))
                else:
                    links.append(format_html(
                        '<a href="{}" style="color: blue; text-decoration: none;" title="点击查看成果详情">{}</a>(未知项目)',
                        deliverable_url,
                        deliverable.id
                    ))
            return format_html(', '.join(links))
        return '无关联成果'

    get_related_deliverables.short_description = '关联成果(项目)'

    fieldsets = (
        ('文件信息', {
            'fields': ('name', 'url', 'path', 'size')
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