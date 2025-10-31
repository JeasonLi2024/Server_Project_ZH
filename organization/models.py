from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


def organization_logo_upload_path(instance, filename):
    """
    组织logo上传路径，按组织ID创建文件夹
    """
    # 获取文件扩展名
    ext = filename.split('.')[-1]
    # 按组织ID创建文件夹，文件名为logo.扩展名
    return f'organization_logos/{instance.id}/logo.{ext}'


class Organization(models.Model):
    """组织模型 - 统一管理企业、大学、其他组织"""

    
    ORGANIZATION_TYPE_CHOICES = [
        ('enterprise', '企业'),
        ('university', '大学'),
        ('other', '其他组织'),
    ]
    
    # 企业类型选择
    ENTERPRISE_TYPE_CHOICES = [
        ('state_owned', '国有企业'),
        ('private', '民营企业'),
        ('foreign', '外资企业'),
        ('joint_venture', '合资企业'),
        ('startup', '创业公司'),
        ('listed', '上市公司'),
        ('other', '其他'),
    ]
    
    # 大学类型选择
    UNIVERSITY_TYPE_CHOICES = [
        ('985', '985工程'),
        ('211', '211工程'),
        ('double_first_class', '双一流'),
        ('ordinary', '普通本科'),
        ('vocational', '高职专科'),
        ('independent', '独立学院'),
        ('private_university', '民办大学'),
    ]
    
    # 其他组织类型选择
    OTHER_TYPE_CHOICES = [
        ('government', '政府机构'),
        ('ngo', '非营利组织'),
        ('foundation', '基金会'),
        ('association', '行业协会'),
        ('research_institute', '科研院所'),
        ('hospital', '医疗机构'),
        ('media', '媒体机构'),
        ('cultural', '文化机构'),
        ('sports', '体育组织'),
        ('religious', '宗教组织'),
        ('international', '国际组织'),
        ('community', '社区组织'),
        ('cooperative', '合作社'),
        ('union', '工会组织'),
        ('chamber', '商会'),
        ('other', '其他未分类'),
    ]
    
    # 组织性质选择（适用于其他类型）
    NATURE_CHOICES = [
        ('public', '公立/公办'),
        ('private', '私立/民办'),
        ('joint', '公私合营'),
        ('international', '国际性'),
        ('regional', '地区性'),
        ('national', '全国性'),
    ]
    
    # 服务对象选择（适用于服务型组织）
    SERVICE_TARGET_CHOICES = [
        ('public', '面向公众'),
        ('members', '面向会员'),
        ('industry', '面向行业'),
        ('government', '面向政府'),
        ('enterprises', '面向企业'),
        ('students', '面向学生'),
        ('patients', '面向患者'),
        ('community', '面向社区'),
        ('other', '其他'),
    ]
    
    # 规模选择（通用）
    SCALE_CHOICES = [
        ('small', '小型（1-500人）'),
        ('medium', '中型（501-2000人）'),
        ('large', '大型（2001-10000人）'),
        ('giant', '超大型（10000人以上）'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待认证'),      # 用户注册时创建的组织
        ('under_review', '审核中'),  # 用户提交认证材料后
        ('verified', '已认证'),     # 认证通过
        ('rejected', '认证被拒'),   # 认证失败
        ('closed', '已关闭'),
    ]
    
    # 基础字段（通用）
    id = models.AutoField(primary_key=True)
    organization_type = models.CharField('组织类型', max_length=20, choices=ORGANIZATION_TYPE_CHOICES)
    name = models.CharField('组织名称', max_length=200)
    code = models.CharField('组织代码', max_length=50, unique=True, blank=True, null=True, 
                           help_text='企业：统一社会信用代码；大学：教育部代码；其他：相关证照编号')
    
    # 领导信息（通用）
    leader_name = models.CharField('负责人姓名', max_length=50, blank=True,
                                  help_text='企业：法定代表人；大学：校长；其他：主要负责人')
    leader_title = models.CharField('负责人职务', max_length=50, blank=True)
    
    # 分类信息（条件字段）
    enterprise_type = models.CharField('企业类型', max_length=20, 
                                     choices=ENTERPRISE_TYPE_CHOICES, blank=True, null=True)
    university_type = models.CharField('大学类型', max_length=20, 
                                     choices=UNIVERSITY_TYPE_CHOICES, blank=True, null=True)
    other_type = models.CharField('其他组织类型', max_length=30, 
                                choices=OTHER_TYPE_CHOICES, blank=True, null=True)
    
    # 组织性质（适用于其他类型）
    organization_nature = models.CharField('组织性质', max_length=20, 
                                         choices=NATURE_CHOICES, blank=True, null=True)
    
    # 行业/学科信息
    industry_or_discipline = models.CharField('行业/学科领域', max_length=100,
                                            help_text='企业：所属行业；大学：主要学科门类；其他：业务领域')
    scale = models.CharField('规模', max_length=20, choices=SCALE_CHOICES)
    
    # 业务范围/服务领域（适用于其他类型）
    business_scope = models.CharField('业务范围/服务领域', max_length=200, blank=True,
                                    help_text='描述组织的主要业务范围或服务领域')
    
    # 监管机构（适用于需要特殊监管的组织）
    regulatory_authority = models.CharField('监管机构', max_length=100, blank=True,
                                          help_text='如：民政部、卫健委、教育部等')
    
    # 许可证/资质信息
    license_info = models.TextField('许可证/资质信息', blank=True,
                                   help_text='相关的许可证号、资质证书等信息')
    
    # 服务对象（适用于服务型组织）
    service_target = models.CharField('主要服务对象', max_length=20, 
                                    choices=SERVICE_TARGET_CHOICES, blank=True, null=True)
    
    # 联系信息（通用）
    contact_person = models.CharField('联系人', max_length=50)
    contact_position = models.CharField('联系人职位', max_length=50, blank=True)
    contact_phone = models.CharField('联系电话', max_length=20)
    contact_email = models.EmailField('联系邮箱', blank=True)
    
    # 地址信息（通用）
    address = models.TextField('详细地址')
    postal_code = models.CharField('邮政编码', max_length=10, blank=True)
    
    # 描述信息（通用）
    description = models.TextField('组织简介', blank=True)
    website = models.URLField('官方网站', blank=True)
    logo = models.ImageField('组织标识', upload_to=organization_logo_upload_path, blank=True, null=True)
    
    # 状态信息（通用）
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    verified_at = models.DateTimeField('认证时间', blank=True, null=True)
    verification_comment = models.TextField('认证意见', blank=True, 
                                          help_text='管理员审核时的意见，通过时可填写"通过"，拒绝时需注明具体原因')
    verification_image = models.JSONField(
        '认证图片',
        default=list,
        blank=True,
        help_text='组织认证时提交的图片证明材料，最多5张，至少1张'
    )
    
    # 时间信息
    established_date = models.DateField('成立时间', blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'organization'
        verbose_name = '01-组织'
        verbose_name_plural = '01-组织'
        indexes = [
            models.Index(fields=['organization_type']),
            models.Index(fields=['name']),
            models.Index(fields=['code']),
            models.Index(fields=['industry_or_discipline']),
            models.Index(fields=['scale']),
            models.Index(fields=['status']),
        ]
    
    def clean(self):
        """模型验证"""
        from django.core.exceptions import ValidationError
        
        # 验证认证图片数量
        if self.verification_image:
            if len(self.verification_image) > 5:
                raise ValidationError('认证图片最多只能上传5张')
            if len(self.verification_image) < 1:
                raise ValidationError('认证图片至少需要上传1张')
        
        # 确保只有一个类型字段被设置
        type_fields = [self.enterprise_type, self.university_type, self.other_type]
        set_fields = [field for field in type_fields if field]
        
        if len(set_fields) > 1:
            raise ValidationError('只能选择一种组织类型的具体分类')
        
        # 根据组织类型验证对应的子类型字段
        if self.organization_type == 'enterprise' and not self.enterprise_type:
            raise ValidationError('企业类型必须选择具体的企业分类')
        elif self.organization_type == 'university' and not self.university_type:
            raise ValidationError('大学类型必须选择具体的大学分类')
        elif self.organization_type == 'other' and not self.other_type:
            raise ValidationError('其他组织类型必须选择具体的组织分类')
        
        # 清理不相关的字段
        if self.organization_type != 'enterprise':
            self.enterprise_type = None
        if self.organization_type != 'university':
            self.university_type = None
        if self.organization_type != 'other':
            self.other_type = None
            self.organization_nature = None
            self.business_scope = ''
            self.regulatory_authority = ''
            self.license_info = ''
            self.service_target = None
    
    def get_required_fields_for_verification(self):
        """根据组织类型返回认证时的必填字段"""
        base_fields = ['code', 'leader_name', 'contact_phone', 'contact_email', 'address']
        
        if self.organization_type == 'other':
            # 根据其他组织的具体类型调整必填字段
            if self.other_type in ['government', 'ngo', 'foundation']:
                # 政府机构、社会团体、基金会：需要额外提供监管机构
                base_fields.extend(['regulatory_authority'])
            elif self.other_type in ['hospital', 'research_institute']:
                # 医院、研究机构：需要额外提供许可证信息
                base_fields.extend(['license_info'])
            elif self.other_type in ['association', 'chamber', 'union']:
                # 协会、商会、工会：需要额外提供服务对象
                base_fields.extend(['service_target'])
        
        return base_fields
    
    def get_field_display_names(self):
        """根据组织类型返回字段的显示名称"""
        display_names = {
            'code': self._get_code_display_name(),
            'leader_name': self._get_leader_display_name(),

            'contact_phone': '联系电话',
            'contact_email': '联系邮箱',
            'address': '详细地址',
            'regulatory_authority': '监管机构',
            'license_info': '许可证信息',
            'service_target': '服务对象',
        }
        return display_names
    
    def _get_code_display_name(self):
        """根据组织类型返回代码字段的显示名称"""
        if self.organization_type == 'enterprise':
            return '统一社会信用代码'
        elif self.organization_type == 'university':
            return '教育部代码'
        elif self.organization_type == 'other':
            if self.other_type == 'government':
                return '机构代码'
            elif self.other_type in ['ngo', 'foundation']:
                return '社会组织统一信用代码'
            elif self.other_type == 'hospital':
                return '医疗机构执业许可证号'
            else:
                return '相关证照编号'
        return '组织代码'
    
    def _get_leader_display_name(self):
        """根据组织类型返回负责人字段的显示名称"""
        if self.organization_type == 'enterprise':
            return '法定代表人'
        elif self.organization_type == 'university':
            return '校长'
        elif self.organization_type == 'other':
            if self.other_type == 'government':
                return '主要负责人'
            elif self.other_type in ['ngo', 'foundation']:
                return '法定代表人'
            elif self.other_type == 'hospital':
                return '院长/主任'
            else:
                return '主要负责人'
        return '负责人'
    

    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.get_organization_type_display()})"
    
    @property
    def type_display(self):
        """获取具体类型显示"""
        if self.organization_type == 'enterprise' and self.enterprise_type:
            return self.get_enterprise_type_display()
        elif self.organization_type == 'university' and self.university_type:
            return self.get_university_type_display()
        return self.get_organization_type_display()


class OrganizationOperationLog(models.Model):
    """组织操作日志"""
    
    # 操作类型分类
    OPERATION_CHOICES = [
        # 成员管理操作
        ('member_approve', '审核通过成员'),
        ('member_reject', '拒绝成员申请'),
        ('member_invite', '邀请成员'),
        ('member_suspend', '暂停成员'),
        ('member_activate', '激活成员'),
        ('member_reactivate', '重新激活成员'),
        ('member_remove', '移除成员'),
        ('member_status_update', '更新成员状态'),
        ('member_leave', '成员退出组织'),
        
        # 权限管理操作
        ('permission_grant_admin', '授予管理员权限'),
        ('permission_revoke_admin', '撤销管理员权限'),
        ('permission_grant_member', '授予成员权限'),
        ('permission_revoke_member', '撤销成员权限'),
        
        # 组织管理操作
        ('organization_update', '更新组织信息'),
        ('organization_config_update', '更新组织配置'),
        ('verification_materials_submit', '提交认证材料'),
        
        # 组织切换操作
        ('join_application_submit', '提交加入申请'),
        ('join_application_approve', '批准加入申请'),
        ('join_application_reject', '拒绝加入申请'),
        ('join_application_cancel', '取消加入申请'),
        ('invitation_code_join', '通过邀请码加入'),
    ]
    
    operator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organization_operations', verbose_name='操作者')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='operation_logs', verbose_name='组织')
    operation = models.CharField('操作类型', max_length=30, choices=OPERATION_CHOICES)
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, 
                                   related_name='organization_operation_targets', verbose_name='目标用户')
    details = models.JSONField('操作详情', default=dict, blank=True, help_text='存储操作的详细信息')
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    user_agent = models.TextField('用户代理', blank=True)
    created_at = models.DateTimeField('操作时间', auto_now_add=True)
    
    class Meta:
        db_table = 'organization_operation_log'
        verbose_name = '02-组织操作日志'
        verbose_name_plural = '02-组织操作日志'
        indexes = [
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['operator', 'created_at']),
            models.Index(fields=['operation']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.operator.username} - {self.get_operation_display()} - {self.organization.name}"


class OrganizationConfig(models.Model):
    """组织配置"""
    
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='config', verbose_name='组织')
    
    # 成员管理配置
    auto_approve_members = models.BooleanField('自动审核成员', default=False, help_text='是否自动审核新成员申请')
    require_email_verification = models.BooleanField('需要邮箱验证', default=True, help_text='新成员是否需要邮箱验证')
    allow_member_invite = models.BooleanField('允许成员邀请', default=False, help_text='普通成员是否可以邀请新成员')
    
    # 权限配置
    admin_can_manage_admins = models.BooleanField('管理员可管理管理员', default=False, help_text='管理员是否可以管理其他管理员')
    member_can_view_all = models.BooleanField('成员可查看全部', default=True, help_text='普通成员是否可以查看所有成员信息')
    
    # 其他配置
    max_members = models.PositiveIntegerField('最大成员数', default=1000, help_text='组织最大成员数量限制')
    welcome_message = models.TextField('欢迎消息', blank=True, help_text='新成员加入时的欢迎消息')
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'organization_config'
        verbose_name = '03-组织配置'
        verbose_name_plural = '03-组织配置'
    
    def __str__(self):
        return f"{self.organization.name} - 配置"


class University(models.Model):
    """高等学校模型"""
    
    id = models.AutoField(primary_key=True)
    school = models.CharField('学校名称', max_length=100, unique=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'university'
        verbose_name = '04-高等学校'
        verbose_name_plural = '04-高等学校'
        indexes = [
            models.Index(fields=['school']),
        ]
    
    def __str__(self):
        return self.school


class OrganizationJoinApplication(models.Model):
    """组织加入申请模型"""
    
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
        ('cancelled', '已取消'),
    ]
    
    # 基本信息
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='join_applications', verbose_name='申请人')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='join_applications', verbose_name='目标组织')
    
    # 申请信息
    application_reason = models.TextField('申请理由', help_text='用户申请加入组织的理由说明')
    status = models.CharField('申请状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 审核信息
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                related_name='reviewed_applications', verbose_name='审核人')
    review_comment = models.TextField('审核意见', blank=True, help_text='审核人的意见或拒绝理由')
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)
    
    # 时间戳
    created_at = models.DateTimeField('申请时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'organization_join_application'
        verbose_name = '05-组织加入申请'
        verbose_name_plural = '05-组织加入申请'
        indexes = [
            models.Index(fields=['applicant', 'status']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        # 确保同一用户对同一组织只能有一个待审核的申请
        unique_together = [('applicant', 'organization', 'status')]
    
    def __str__(self):
        return f"{self.applicant.username} 申请加入 {self.organization.name}"
    
    def approve(self, reviewer, comment=''):
        """批准申请"""
        from django.utils import timezone
        
        self.status = 'approved'
        self.reviewer = reviewer
        self.review_comment = comment
        self.reviewed_at = timezone.now()
        self.save()
        
        # 创建组织用户关系
        from user.models import OrganizationUser
        OrganizationUser.objects.create(
            user=self.applicant,
            organization=self.organization,
            permission='member',
            status='approved'
        )
    
    def reject(self, reviewer, comment=''):
        """拒绝申请"""
        from django.utils import timezone
        
        self.status = 'rejected'
        self.reviewer = reviewer
        self.review_comment = comment
        self.reviewed_at = timezone.now()
        self.save()
    
    def cancel(self):
        """取消申请"""
        self.status = 'cancelled'
        self.save()
    
    @property
    def is_pending(self):
        """是否为待审核状态"""
        return self.status == 'pending'
    
    @property
    def is_approved(self):
        """是否已通过"""
        return self.status == 'approved'
    
    @property
    def is_rejected(self):
        """是否已拒绝"""
        return self.status == 'rejected'
