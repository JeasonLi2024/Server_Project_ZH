from django.db import models
from django.contrib.auth import get_user_model
from project.models import Requirement
from organization.models import Organization

User = get_user_model()


class RequirementAuditLog(models.Model):
    """需求审核历史日志模型"""
    
    # 审核操作类型
    AUDIT_ACTION_CHOICES = [
        ('submit', '提交审核'),
        ('approve', '审核通过'),
        ('reject', '审核拒绝'),
        ('resubmit', '重新提交'),
        ('withdraw', '撤回申请'),
        ('auto_approve', '自动通过'),
        ('batch_approve', '批量通过'),
        ('batch_reject', '批量拒绝'),
    ]
    
    # 状态变更记录
    STATUS_TRANSITION_CHOICES = [
        ('pending_to_under_review', '待审核 → 审核中'),
        ('under_review_to_approved', '审核中 → 通过'),
        ('under_review_to_rejected', '审核中 → 拒绝'),
        ('rejected_to_under_review', '拒绝 → 重新审核'),
        ('approved_to_in_progress', '通过 → 进行中'),
        ('in_progress_to_completed', '进行中 → 已完成'),
        ('in_progress_to_paused', '进行中 → 已暂停'),
        ('paused_to_in_progress', '已暂停 → 进行中'),
    ]
    
    # 基础字段
    id = models.AutoField(primary_key=True)
    requirement = models.ForeignKey(
        Requirement, 
        on_delete=models.CASCADE, 
        related_name='audit_logs', 
        verbose_name='关联需求'
    )
    
    # 操作信息
    action = models.CharField(
        '审核操作', 
        max_length=20, 
        choices=AUDIT_ACTION_CHOICES
    )
    status_transition = models.CharField(
        '状态变更', 
        max_length=30, 
        choices=STATUS_TRANSITION_CHOICES,
        blank=True,
        null=True
    )
    
    # 状态记录
    old_status = models.CharField(
        '原状态', 
        max_length=20, 
        blank=True,
        help_text='变更前的需求状态'
    )
    new_status = models.CharField(
        '新状态', 
        max_length=20,
        help_text='变更后的需求状态'
    )
    
    # 操作人员
    operator = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='requirement_audit_operations', 
        verbose_name='操作者'
    )
    operator_role = models.CharField(
        '操作者角色',
        max_length=20,
        choices=[
            ('admin', '系统管理员'),
            ('org_owner', '组织所有者'),
            ('org_admin', '组织管理员'),
            ('publisher', '需求发布者'),
            ('system', '系统自动'),
        ],
        help_text='操作者在此次审核中的角色'
    )
    
    # 审核详情
    comment = models.TextField(
        '审核意见', 
        blank=True,
        help_text='审核时的具体意见或理由'
    )
    review_details = models.JSONField(
        '审核详情', 
        default=dict, 
        blank=True,
        help_text='存储审核的详细信息，如修改的字段、附加数据等'
    )
    
    # 技术信息
    ip_address = models.GenericIPAddressField(
        'IP地址', 
        null=True, 
        blank=True
    )
    user_agent = models.TextField(
        '用户代理', 
        blank=True
    )
    
    # 时间戳
    created_at = models.DateTimeField(
        '操作时间', 
        auto_now_add=True
    )
    
    class Meta:
        db_table = 'requirement_audit_log'
        verbose_name = '需求审核历史日志'
        verbose_name_plural = '需求审核历史日志'
        indexes = [
            models.Index(fields=['requirement', 'created_at']),
            models.Index(fields=['operator', 'created_at']),
            models.Index(fields=['action']),
            models.Index(fields=['new_status']),
            models.Index(fields=['requirement', 'action']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.requirement.title} - {self.get_action_display()} - {self.operator.username}"
    
    @classmethod
    def log_status_change(cls, requirement, old_status, new_status, operator, 
                         action='submit', comment='', operator_role='publisher', 
                         ip_address=None, user_agent='', **extra_details):
        """记录需求状态变更日志"""
        
        # 确定状态转换类型
        status_transition = None
        if old_status and new_status:
            transition_key = f"{old_status}_to_{new_status}"
            for choice_key, _ in cls.STATUS_TRANSITION_CHOICES:
                if choice_key == transition_key:
                    status_transition = choice_key
                    break
        
        # 创建审核日志
        audit_log = cls.objects.create(
            requirement=requirement,
            action=action,
            status_transition=status_transition,
            old_status=old_status or '',
            new_status=new_status,
            operator=operator,
            operator_role=operator_role,
            comment=comment,
            review_details=extra_details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return audit_log
    
    @classmethod
    def get_requirement_audit_history(cls, requirement_id, limit=None):
        """获取需求的完整审核历史"""
        queryset = cls.objects.filter(
            requirement_id=requirement_id
        ).select_related('operator', 'requirement').order_by('-created_at')
        
        if limit:
            queryset = queryset[:limit]
            
        return queryset
    
    def get_status_display_info(self):
        """获取状态显示信息"""
        return {
            'old_status': self.old_status,
            'new_status': self.new_status,
            'transition': self.get_status_transition_display() if self.status_transition else None,
            'action': self.get_action_display()
        }


class OrganizationAuditLog(models.Model):
    """组织认证审核历史日志模型"""
    
    # 审核操作类型
    AUDIT_ACTION_CHOICES = [
        ('submit', '提交认证'),
        ('approve', '认证通过'),
        ('reject', '认证拒绝'),
        ('resubmit', '重新提交'),
        ('update_materials', '更新材料'),
        ('withdraw', '撤回申请'),
        ('auto_approve', '自动通过'),
        ('batch_approve', '批量通过'),
        ('batch_reject', '批量拒绝'),
        ('suspend', '暂停认证'),
        ('restore', '恢复认证'),
    ]
    
    # 状态变更记录
    STATUS_TRANSITION_CHOICES = [
        ('pending_to_under_review', '待认证 → 审核中'),
        ('under_review_to_verified', '审核中 → 已认证'),
        ('under_review_to_rejected', '审核中 → 认证被拒'),
        ('rejected_to_under_review', '认证被拒 → 重新审核'),
        ('verified_to_closed', '已认证 → 已关闭'),
        ('closed_to_verified', '已关闭 → 已认证'),
    ]
    
    # 基础字段
    id = models.AutoField(primary_key=True)
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name='audit_logs', 
        verbose_name='关联组织'
    )
    
    # 操作信息
    action = models.CharField(
        '审核操作', 
        max_length=20, 
        choices=AUDIT_ACTION_CHOICES
    )
    status_transition = models.CharField(
        '状态变更', 
        max_length=30, 
        choices=STATUS_TRANSITION_CHOICES,
        blank=True,
        null=True
    )
    
    # 状态记录
    old_status = models.CharField(
        '原状态', 
        max_length=20, 
        blank=True,
        help_text='变更前的组织认证状态'
    )
    new_status = models.CharField(
        '新状态', 
        max_length=20,
        help_text='变更后的组织认证状态'
    )
    
    # 操作人员
    operator = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='organization_audit_operations', 
        verbose_name='操作者'
    )
    operator_role = models.CharField(
        '操作者角色',
        max_length=20,
        choices=[
            ('admin', '系统管理员'),
            ('org_owner', '组织所有者'),
            ('org_admin', '组织管理员'),
            ('applicant', '申请人'),
            ('system', '系统自动'),
        ],
        help_text='操作者在此次审核中的角色'
    )
    
    # 审核详情
    comment = models.TextField(
        '审核意见', 
        blank=True,
        help_text='审核时的具体意见或理由'
    )
    review_details = models.JSONField(
        '审核详情', 
        default=dict, 
        blank=True,
        help_text='存储审核的详细信息，如修改的字段、提交的材料等'
    )
    
    # 材料信息
    submitted_materials = models.JSONField(
        '提交材料', 
        default=list, 
        blank=True,
        help_text='本次提交或更新的认证材料信息'
    )
    
    # 技术信息
    ip_address = models.GenericIPAddressField(
        'IP地址', 
        null=True, 
        blank=True
    )
    user_agent = models.TextField(
        '用户代理', 
        blank=True
    )
    
    # 时间戳
    created_at = models.DateTimeField(
        '操作时间', 
        auto_now_add=True
    )
    
    class Meta:
        db_table = 'organization_audit_log'
        verbose_name = '组织认证审核历史日志'
        verbose_name_plural = '组织认证审核历史日志'
        indexes = [
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['operator', 'created_at']),
            models.Index(fields=['action']),
            models.Index(fields=['new_status']),
            models.Index(fields=['organization', 'action']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.organization.name} - {self.get_action_display()} - {self.operator.username}"
    
    @classmethod
    def log_status_change(cls, organization, old_status, new_status, operator, 
                         action='submit', comment='', operator_role='applicant', 
                         submitted_materials=None, ip_address=None, user_agent='', 
                         **extra_details):
        """记录组织认证状态变更日志"""
        
        # 确定状态转换类型
        status_transition = None
        if old_status and new_status:
            transition_key = f"{old_status}_to_{new_status}"
            for choice_key, _ in cls.STATUS_TRANSITION_CHOICES:
                if choice_key == transition_key:
                    status_transition = choice_key
                    break
        
        # 创建审核日志
        audit_log = cls.objects.create(
            organization=organization,
            action=action,
            status_transition=status_transition,
            old_status=old_status or '',
            new_status=new_status,
            operator=operator,
            operator_role=operator_role,
            comment=comment,
            review_details=extra_details,
            submitted_materials=submitted_materials or [],
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return audit_log
    
    @classmethod
    def get_organization_audit_history(cls, organization_id, limit=None):
        """获取组织的完整认证审核历史"""
        queryset = cls.objects.filter(
            organization_id=organization_id
        ).select_related('operator', 'organization').order_by('-created_at')
        
        if limit:
            queryset = queryset[:limit]
            
        return queryset
    
    def get_status_display_info(self):
        """获取状态显示信息"""
        return {
            'old_status': self.old_status,
            'new_status': self.new_status,
            'transition': self.get_status_transition_display() if self.status_transition else None,
            'action': self.get_action_display()
        }