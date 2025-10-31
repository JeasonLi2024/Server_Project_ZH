from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Requirement, Resource, File
from notification.services import notification_service


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'status_display', 'organization', 'publish_people', 'evaluation_criteria_display', 'views', 'created_at']
    list_filter = ['status', 'created_at', 'organization', 'publish_people', 'evaluation_criteria']
    search_fields = ['title', 'brief', 'description', 'organization__name', 'publish_people__user__username', 'publish_people__user__real_name', 'evaluation_criteria__name']
    readonly_fields = ['id', 'created_at', 'updated_at',  'get_student_projects_count', 'get_total_participants_count', 'get_evaluation_criteria_info']
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
    
    def status_display(self, obj):
        """显示需求状态（彩色）"""
        status_colors = {
            'under_review': '#ffc107',    # 黄色 - 审核中
            'review_failed': '#dc3545',   # 红色 - 审核失败
            'in_progress': '#28a745',     # 绿色 - 进行中
            'completed': '#17a2b8',       # 蓝色 - 已完成
            'paused': '#6c757d',          # 灰色 - 已暂停
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = '状态'
    
    def evaluation_criteria_display(self, obj):
        """显示评分标准信息"""
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
        ('审核信息', {
            'fields': ('review_comment',),
            'description': '需求审核相关信息。审核意见：审核通过填写"通过"即可，审核不通过需注明具体原因'
        }),
        ('项目信息', {
            'fields': ('budget', 'finish_time', 'support_provided', 'get_student_projects_count', 'get_total_participants_count')
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
    
    def save_model(self, request, obj, form, change):
        """重写save_model方法，处理需求状态变更通知"""
        # 获取原始状态（如果是更新操作）
        old_status = None
        if change and obj.pk:
            try:
                old_obj = Requirement.objects.get(pk=obj.pk)
                old_status = old_obj.status
            except Requirement.DoesNotExist:
                old_status = None
        
        # 保存对象
        super().save_model(request, obj, form, change)
        
        # 检查状态变更并发送通知
        if change and old_status and old_status != obj.status:
            self._send_status_change_notification(obj, old_status, obj.status, request.user)
    
    def _send_status_change_notification(self, requirement, old_status, new_status, reviewer):
        """发送需求状态变更通知"""
        try:
            # 获取需求发布者
            recipient = requirement.publish_people.user
            
            # 准备通知模板变量
            template_vars = {
                'publisher_name': recipient.real_name or recipient.username,
                'requirement_title': requirement.title,
                'organization_name': requirement.organization.name,
                'review_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'reviewer_name': reviewer.real_name or reviewer.username,
                'review_comment': requirement.review_comment or '无',
                'requirement_url': f'/admin/project/requirement/{requirement.id}/change/'
            }
            
            # 根据状态变更发送相应通知
            if old_status == 'under_review' and new_status == 'in_progress':
                # 审核通过通知
                notification_service.create_and_send_notification(
                    recipient=recipient,
                    notification_type_code='requirement_review_approved',
                    related_object=requirement,
                    template_vars=template_vars,
                    sender=reviewer
                )
            elif old_status == 'under_review' and new_status == 'review_failed':
                # 审核失败通知
                notification_service.create_and_send_notification(
                    recipient=recipient,
                    notification_type_code='requirement_review_failed',
                    related_object=requirement,
                    template_vars=template_vars,
                    sender=reviewer
                )
        except Exception as e:
            # 记录错误但不影响保存操作
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'发送需求状态变更通知失败: {str(e)}')


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'type', 'status', 'create_person', 'get_organization', 'downloads', 'views']
    list_filter = ['type', 'status', 'create_person', 'create_person__organization']
    search_fields = ['title', 'description', 'create_person__user__username', 'create_person__user__real_name', 'create_person__organization__name']
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
    list_display = ['id', 'name', 'file_type_display', 'cloud_link_display', 'size_display', 'created_at', 'get_related_requirements', 'get_related_resources', 'get_related_deliverables']
    list_filter = ['created_at', 'is_folder', 'is_cloud_link']
    search_fields = ['name', 'path', 'url']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def file_type_display(self, obj):
        """显示文件类型"""
        from django.utils.html import format_html
        if obj.is_folder:
            return format_html(
                '<span style="color: #0066cc; font-weight: bold;">文件夹</span>'
            )
        elif obj.is_cloud_link:
            return format_html(
                '<span style="color: #ff6600; font-weight: bold;">网盘链接</span>'
            )
        else:
            return format_html(
                '<span style="color: #009900; font-weight: bold;">普通文件</span>'
            )
    file_type_display.short_description = '文件类型'
    
    def cloud_link_display(self, obj):
        """显示网盘链接信息"""
        from django.utils.html import format_html
        if obj.is_cloud_link:
            if obj.url:
                # 截取URL显示前50个字符
                url_display = obj.url[:50] + '...' if len(obj.url) > 50 else obj.url
                password_info = f"密码: {obj.cloud_password}" if obj.cloud_password else "无密码"
                return format_html(
                    '<div style="font-size: 12px;">'
                    '<div><strong>链接:</strong> <a href="{}" target="_blank" style="color: #0066cc;">{}</a></div>'
                    '<div><strong>{}</strong></div>'
                    '</div>',
                    obj.url,
                    url_display,
                    password_info
                )
            else:
                return format_html('<span style="color: #ff0000;">❌ 无链接地址</span>')
        else:
            return format_html('<span style="color: #999999;">-</span>')
    cloud_link_display.short_description = '网盘链接信息'
    
    def size_display(self, obj):
        """格式化显示文件大小"""
        from django.utils.html import format_html
        if obj.is_folder:
            return format_html('<span style="color: #999999;">-</span>')
        
        # 确保size是数字类型，处理可能的SafeString情况
        try:
            # 如果obj.size是SafeString，先转换为字符串再转换为数字
            size_value = str(obj.size) if obj.size is not None else "0"
            size = float(size_value)
        except (ValueError, TypeError):
            return format_html('<span style="color: #ff0000;">无效大小</span>')
            
        if size == 0:
            return format_html('<span style="color: #999999;">0 B</span>')
        elif size < 1024:
            return format_html('<span>{} B</span>', int(size))
        elif size < 1024 * 1024:
            kb_value = float(round(size / 1024, 1))
            return format_html('<span>{} KB</span>', kb_value)
        elif size < 1024 * 1024 * 1024:
            mb_value = float(round(size / (1024 * 1024), 1))
            return format_html('<span>{} MB</span>', mb_value)
        else:
            gb_value = float(round(size / (1024 * 1024 * 1024), 1))
            return format_html('<span>{} GB</span>', gb_value)
    size_display.short_description = '文件大小'
    
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
        from django.urls import reverse, NoReverseMatch
        try:
            deliverables = obj.deliverables.all()
            if deliverables:
                links = []
                for deliverable in deliverables:
                    try:
                        # 创建成果详情链接
                        deliverable_url = reverse('admin:studentproject_projectdeliverable_change', args=[deliverable.id])
                        project_info = f"{deliverable.project.id}-{deliverable.project.title}" if deliverable.project else '未知项目'
                        
                        # 如果有项目信息，也创建项目链接
                        if deliverable.project:
                            try:
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
                            except NoReverseMatch:
                                links.append(format_html(
                                    '<a href="{}" style="color: blue; text-decoration: none;" title="点击查看成果详情">{}</a>(项目:{}-{})',
                                    deliverable_url,
                                    deliverable.id,
                                    deliverable.project.id,
                                    deliverable.project.title
                                ))
                        else:
                            links.append(format_html(
                                '<a href="{}" style="color: blue; text-decoration: none;" title="点击查看成果详情">{}</a>(未知项目)',
                                deliverable_url,
                                deliverable.id
                            ))
                    except (NoReverseMatch, AttributeError) as e:
                        # 如果URL反向解析失败，显示简单的ID信息
                        links.append(f"成果ID:{deliverable.id}")
                return format_html(', '.join(links))
            return '无关联成果'
        except Exception as e:
            return f'获取关联成果时出错: {str(e)[:50]}'
    get_related_deliverables.short_description = '关联成果(项目)'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'is_folder', 'size')
        }),
        ('文件路径', {
            'fields': ('path', 'real_path', 'parent_path'),
            'description': '虚拟文件系统路径信息'
        }),
        ('网盘链接信息', {
            'fields': ('is_cloud_link', 'url', 'cloud_password'),
            'description': '网盘链接相关配置，仅当文件类型为网盘链接时有效'
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