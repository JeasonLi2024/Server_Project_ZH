from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone


class StudentProject(models.Model):
    """学生项目模型"""
    
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('recruiting', '招募中'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('suspended', '已暂停'),
        ('cancelled', '已取消'),
    ]
    
    # 基本信息
    title = models.CharField(
        max_length=200, 
        verbose_name='项目标题'
    )
    
    description = models.TextField(
        verbose_name='项目描述'
    )
    
    # 关联需求
    requirement = models.ForeignKey(
        'project.Requirement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_projects',
        verbose_name='关联需求',
        db_index=False  # 移除单字段索引，已被复合索引覆盖
    )
    
    # 项目状态
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='项目状态'
    )
    
    # 评分状态
    is_evaluated = models.BooleanField(
        default=False,
        verbose_name='是否已评分',
        help_text='标识该项目是否已有评分记录'
    )
    
    # 参与学生（通过中间表管理）
    participants = models.ManyToManyField(
        'user.Student',
        through='ProjectParticipant',
        through_fields=('project', 'student'),
        related_name='joined_projects',
        verbose_name='参与学生'
    )
    
    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        db_table = 'student_project'
        verbose_name = '01-学生项目'
        verbose_name_plural = '01-学生项目'
        ordering = ['-created_at']
        
        indexes = [
            # 优化复合索引，基于查询模式
            models.Index(fields=['requirement', 'status'], name='sp_req_status_idx'),
            models.Index(fields=['status', 'is_evaluated'], name='sp_status_eval_idx'),
            models.Index(fields=['created_at']),
        ]
    
    def get_leader(self):
        """获取项目负责人"""
        try:
            return self.project_participants.get(role='leader').student
        except ProjectParticipant.DoesNotExist:
            return None
    
    def get_members(self):
        """获取项目成员（不包括负责人）"""
        return self.project_participants.filter(
            role='member',
            status='approved'
        ).select_related('student')
    
    def get_active_participants(self):
        """获取所有活跃参与者"""
        return self.project_participants.filter(
            status='approved'
        ).select_related('student')
    
    def __str__(self):
        return self.title


class ProjectParticipant(models.Model):
    """项目参与者关系模型"""
    
    ROLE_CHOICES = [
        ('leader', '负责人'),
        ('member', '成员'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '申请中'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
        ('left', '已退出'),
    ]
    
    # 关联关系
    project = models.ForeignKey(
        StudentProject,
        on_delete=models.CASCADE,
        related_name='project_participants',
        verbose_name='项目',
        db_index=False  # 移除单字段索引，已被复合索引覆盖
    )
    
    student = models.ForeignKey(
        'user.Student',
        on_delete=models.CASCADE,
        related_name='project_participations',
        verbose_name='学生',
        db_index=False  # 移除单字段索引，已被复合索引覆盖
    )
    
    # 角色和状态
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name='角色'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态'
    )
    
    # 申请信息
    application_message = models.TextField(
        blank=True,
        verbose_name='申请留言'
    )
    
    # 审核信息
    reviewed_by = models.ForeignKey(
        'user.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_participations',
        verbose_name='审核人'
    )
    
    review_message = models.TextField(
        blank=True,
        verbose_name='审核留言'
    )
    
    # 时间信息
    applied_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='申请时间'
    )
    
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='审核时间'
    )
    
    class Meta:
        db_table = 'student_project_participant'
        verbose_name = '02-项目参与者'
        verbose_name_plural = '02-项目参与者'
        unique_together = ['project', 'student']
        ordering = ['-applied_at']
        
        indexes = [
            # 优化复合索引设计
            models.Index(fields=['project', 'role', 'status'], name='pp_proj_role_status_idx'),
            models.Index(fields=['student', 'status'], name='pp_student_status_idx'),
        ]
    
    def __str__(self):
        return f"{self.project.title} - {self.student.user.real_name} ({self.get_role_display()})"


class ProjectDeliverable(models.Model):
    """项目成果模型"""
    
    STAGE_CHOICES = [
        ('early', '前期'),
        ('middle', '中期'),
        ('final', '末期'),
    ]
    
    # 基本信息
    project = models.ForeignKey(
        StudentProject,
        on_delete=models.CASCADE,
        related_name='deliverables',
        verbose_name='关联项目',
        db_index=False  # 移除单字段索引，已被复合索引覆盖
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='成果标题'
    )
    
    description = models.TextField(
        verbose_name='成果描述'
    )
    
    # 版本控制信息
    stage_type = models.CharField(
        max_length=50,
        choices=STAGE_CHOICES,
        verbose_name='项目阶段'
    )
    
    version_number = models.PositiveIntegerField(
        default=1,
        verbose_name='阶段内版本号'
    )
    
    stage_version = models.CharField(
        max_length=100,
        verbose_name='阶段版本标识',
        help_text='自动生成的易读版本标识，如：前期v1、中期v2、末期v1'
    )
    

    
    # 里程碑标记
    is_milestone = models.BooleanField(
        default=False,
        verbose_name='是否为里程碑版本'
    )
    
    # 进展描述
    progress_description = models.TextField(
        blank=True,
        verbose_name='进展描述',
        help_text='描述本次提交相比上一版本的改进和进展'
    )
    
    # 文件关联
    files = models.ManyToManyField(
        'project.File',
        blank=True,
        related_name='deliverables',
        verbose_name='关联文件'
    )
    
    # 提交信息
    submitter = models.ForeignKey(
        'user.Student',
        on_delete=models.CASCADE,
        related_name='submitted_deliverables',
        verbose_name='提交人',
        db_index=False  # 移除单字段索引，已被复合索引覆盖
    )
    
    # 最新修改人信息
    last_modifier = models.ForeignKey(
        'user.Student',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='modified_deliverables',
        verbose_name='最新修改人',
        help_text='记录最后一次修改成果的用户，初次提交时为空'
    )
    
    # 是否被更新过
    is_updated = models.BooleanField(
        default=False,
        verbose_name='是否被更新过',
        help_text='标识该成果是否在初次提交后被修改过'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    # 备注信息
    notes = models.TextField(
        blank=True,
        verbose_name='备注',
        help_text='其他需要说明的信息'
    )
    
    # 是否已弃用
    is_deprecated = models.BooleanField(
        default=False,
        verbose_name='是否已弃用',
        help_text='标识该成果是否已被弃用，弃用的成果不会被删除但会被标记'
    )
    
    class Meta:
        db_table = 'student_project_deliverable'
        verbose_name = '03-项目成果'
        verbose_name_plural = '03-项目成果'
        ordering = ['-created_at']
        
        # 确保同一项目同一阶段的版本号唯一
        unique_together = ['project', 'stage_type', 'version_number']
        
        indexes = [
            # 优化复合索引，减少单字段索引
            models.Index(fields=['project', 'stage_type', 'is_milestone'], name='pd_proj_stage_milestone_idx'),
            models.Index(fields=['submitter', 'created_at'], name='pd_submitter_created_idx'),
        ]
    
    def save(self, *args, **kwargs):
        """保存时自动生成阶段版本标识"""
        if not self.stage_version:
            stage_name = dict(self.STAGE_CHOICES).get(self.stage_type, self.stage_type)
            self.stage_version = f"{stage_name}v{self.version_number}"
        super().save(*args, **kwargs)
    
    def get_next_version_number(self):
        """获取同阶段下一个版本号"""
        last_version = ProjectDeliverable.objects.filter(
            project=self.project,
            stage_type=self.stage_type
        ).aggregate(max_version=models.Max('version_number'))['max_version']
        
        return (last_version or 0) + 1
    
    def get_version_history(self):
        """获取同一项目同一阶段的版本历史（按版本号排序）"""
        return ProjectDeliverable.objects.filter(
            project=self.project,
            stage_type=self.stage_type
        ).order_by('version_number')
    
    def get_previous_version(self):
        """获取前一个版本"""
        return ProjectDeliverable.objects.filter(
            project=self.project,
            stage_type=self.stage_type,
            version_number__lt=self.version_number
        ).order_by('-version_number').first()
    
    def get_next_version(self):
        """获取下一个版本"""
        return ProjectDeliverable.objects.filter(
            project=self.project,
            stage_type=self.stage_type,
            version_number__gt=self.version_number
        ).order_by('version_number').first()
    
    def __str__(self):
        return f"{self.project.title} - {self.stage_version}"


class ProjectComment(models.Model):
    """项目评论模型"""
    
    # 关联项目
    project = models.ForeignKey(
        StudentProject,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='关联项目',
        db_index=False  # 移除单字段索引，已被复合索引覆盖
    )
    
    # 关联成果（可选）
    deliverable = models.ForeignKey(
        ProjectDeliverable,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comments',
        verbose_name='关联成果'
    )
    
    # 评论内容
    content = models.TextField(
        verbose_name='评论内容'
    )
    
    # 评论作者（支持学生和组织用户）
    author = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name='project_comments',
        verbose_name='评论作者',
        db_index=False  # 移除单字段索引，已被复合索引覆盖
    )
    
    # 父评论（支持回复）
    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='父评论'
    )
    
    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        db_table = 'student_project_comment'
        verbose_name = '04-项目评价'
        verbose_name_plural = '04-项目评价'
        ordering = ['-created_at']
        
        indexes = [
            # 优化复合索引设计
            models.Index(fields=['project', 'deliverable'], name='pc_proj_deliverable_idx'),
            models.Index(fields=['author', 'created_at'], name='pc_author_created_idx'),
            models.Index(fields=['parent_comment'], name='pc_parent_idx'),
        ]
    
    def get_reply_count(self):
        """获取回复数量"""
        return self.replies.count()
    
    def is_reply(self):
        """判断是否为回复"""
        return self.parent_comment is not None
    
    def __str__(self):
        if self.deliverable:
            return f"{self.project.title} - {self.deliverable.stage_version} - 评论"
        return f"{self.project.title} - 评论"


class ProjectInvitation(models.Model):
    """项目邀请模型"""
    
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('accepted', '已接受'),
        ('rejected', '已拒绝'),
        ('expired', '已过期'),
    ]
    
    # 关联项目
    project = models.ForeignKey(
        StudentProject,
        on_delete=models.CASCADE,
        related_name='invitations',
        verbose_name='项目',
        db_index=False  # 移除单字段索引，已被复合索引覆盖
    )
    
    # 邀请者（项目负责人）
    inviter = models.ForeignKey(
        'user.Student',
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        verbose_name='邀请者',
        db_index=False  # 移除单字段索引，已被复合索引覆盖
    )
    
    # 被邀请者
    invitee = models.ForeignKey(
        'user.Student',
        on_delete=models.CASCADE,
        related_name='received_invitations',
        verbose_name='被邀请者',
        db_index=False  # 移除单字段索引，已被复合索引覆盖
    )
    
    # 邀请状态
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='邀请状态'
    )
    
    # 邀请留言
    invitation_message = models.TextField(
        blank=True,
        verbose_name='邀请留言'
    )
    
    # 响应留言
    response_message = models.TextField(
        blank=True,
        verbose_name='响应留言'
    )
    
    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='邀请时间'
    )
    
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='响应时间'
    )
    
    # 过期时间（可选，默认7天后过期）
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='过期时间'
    )
    
    class Meta:
        db_table = 'student_project_invitation'
        verbose_name = '06-项目邀请'
        verbose_name_plural = '06-项目邀请'
        unique_together = ['project', 'invitee']  # 同一项目不能重复邀请同一人
        ordering = ['-created_at']
        
        indexes = [
            # 优化复合索引设计
            models.Index(fields=['project', 'status'], name='pi_proj_status_idx'),
            models.Index(fields=['invitee', 'status'], name='pi_invitee_status_idx'),
            models.Index(fields=['inviter', 'created_at'], name='pi_inviter_created_idx'),
        ]
    
    def save(self, *args, **kwargs):
        # 如果没有设置过期时间，默认7天后过期
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """检查邀请是否已过期"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def can_respond(self):
        """检查是否可以响应邀请"""
        return self.status == 'pending' and not self.is_expired()
    
    def __str__(self):
        return f'{self.inviter.user.real_name} 邀请 {self.invitee.user.real_name} 加入 {self.project.title}'
