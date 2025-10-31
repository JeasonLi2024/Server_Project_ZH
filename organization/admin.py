from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Organization, OrganizationOperationLog, OrganizationConfig


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """组织管理"""
    list_display = ['id', 'name', 'organization_type', 'type_display', 'verification_status_display', 'created_at']
    list_filter = ['organization_type', 'status', 'enterprise_type', 'university_type', 'other_type', 'organization_nature', 'scale']
    search_fields = ['name', 'code', 'contact_person', 'contact_email', 'business_scope', 'regulatory_authority']
    readonly_fields = ['created_at', 'updated_at', 'verification_images_display']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('organization_type', 'name', 'code', 'status')
        }),
        ('认证信息', {
            'fields': ('verified_at', 'verification_comment', 'verification_images_display'),
            'description': '组织认证相关信息和材料。认证意见：审核通过填写"通过"即可，审核不通过需注明具体原因'
        }),
        ('领导信息', {
            'fields': ('leader_name', 'leader_title')
        }),
        ('分类信息', {
            'fields': ('enterprise_type', 'university_type', 'other_type', 'organization_nature', 'industry_or_discipline', 'scale')
        }),
        ('其他组织特有信息', {
            'fields': ('business_scope', 'regulatory_authority', 'license_info', 'service_target'),
            'classes': ('collapse',),
            'description': '仅适用于"其他"组织类型'
        }),
        ('联系信息', {
            'fields': ('contact_person', 'contact_position', 'contact_phone', 'contact_email')
        }),
        ('地址信息', {
            'fields': ('address', 'postal_code')
        }),
        ('其他信息', {
            'fields': ('description', 'website', 'logo', 'established_date')
        }),
        ('系统信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def type_display(self, obj):
        """显示组织类型的详细信息"""
        if obj.organization_type == 'enterprise':
            return f"企业 - {obj.get_enterprise_type_display()}" if obj.enterprise_type else "企业"
        elif obj.organization_type == 'university':
            return f"大学 - {obj.get_university_type_display()}" if obj.university_type else "大学"
        elif obj.organization_type == 'other':
            other_display = obj.get_other_type_display() if obj.other_type else "未指定"
            nature_display = obj.get_organization_nature_display() if obj.organization_nature else ""
            if nature_display:
                return f"其他组织 - {other_display} ({nature_display})"
            else:
                return f"其他组织 - {other_display}"
        return obj.get_organization_type_display()
    
    type_display.short_description = '组织类型详情'
    
    def verification_status_display(self, obj):
        """显示认证状态"""
        status_colors = {
            'pending': '#ffc107',      # 黄色
            'under_review': '#17a2b8', # 蓝色
            'verified': '#28a745',     # 绿色
            'rejected': '#dc3545',     # 红色
            'closed': '#6c757d',       # 灰色
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    verification_status_display.short_description = '认证状态'
    
    def verification_images_display(self, obj):
        """显示认证图片"""
        if not obj.verification_image:
            return "暂无认证图片"
        
        images_html = []
        for i, image_path in enumerate(obj.verification_image, 1):
            if image_path:
                # 构建完整的图片URL
                image_url = f"/media/{image_path}"
                images_html.append(
                    f'<div style="margin-bottom: 10px;">'
                    f'<p><strong>认证图片 {i}:</strong></p>'
                    f'<a href="{image_url}" target="_blank">'
                    f'<img src="{image_url}" style="max-width: 200px; max-height: 150px; border: 1px solid #ddd; border-radius: 4px; margin-right: 10px;" />'
                    f'</a>'
                    f'<br><small style="color: #666;">点击查看大图</small>'
                    f'</div>'
                )
        
        if images_html:
            return mark_safe(''.join(images_html))
        else:
            return "暂无有效认证图片"
    
    verification_images_display.short_description = '认证图片材料'


@admin.register(OrganizationOperationLog)
class OrganizationOperationLogAdmin(admin.ModelAdmin):
    """组织操作日志管理"""
    list_display = ['operator', 'organization', 'operation', 'target_user', 'created_at']
    list_filter = ['operation', 'created_at']
    search_fields = ['operator__username', 'organization__name', 'target_user__username']
    readonly_fields = ['operator', 'organization', 'operation', 'target_user', 'details', 'ip_address', 'user_agent', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


# @admin.register(OrganizationConfig)
# class OrganizationConfigAdmin(admin.ModelAdmin):
#     """组织配置管理"""
#     list_display = ['organization', 'auto_approve_members', 'require_email_verification', 'max_members']
#     list_filter = ['auto_approve_members', 'require_email_verification', 'allow_member_invite']
#     search_fields = ['organization__name']
#     readonly_fields = ['created_at', 'updated_at']
