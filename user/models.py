from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator


def user_avatar_upload_path(instance, filename):
    """
    自定义头像上传路径，按用户ID创建文件夹
    """
    # 获取文件扩展名
    ext = filename.split('.')[-1]
    # 按用户ID创建文件夹，文件名为avatar.扩展名
    return f'avatars/{instance.id}/avatar.{ext}'


class UserManager(BaseUserManager):
    """自定义用户管理器"""
    
    def create_user(self, username, email, password=None, **extra_fields):
        """创建普通用户"""
        if not email:
            raise ValueError('用户必须有邮箱地址')
        if not username:
            raise ValueError('用户必须有用户名')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        """创建超级用户"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('超级用户必须设置is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('超级用户必须设置is_superuser=True')
        
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """基础用户模型"""
    
    USER_TYPE_CHOICES = [
        ('student', '学生'),
        ('organization', '组织用户'),
        ('admin', '管理员'),
    ]
    
    GENDER_CHOICES = [
        ('male', '男'),
        ('female', '女'),
        ('other', '其他'),
    ]
    
    # 基本信息
    id = models.AutoField(primary_key=True)
    username = models.CharField('用户名', max_length=30, unique=True, default='user')
    email = models.EmailField('邮箱', unique=True)
    phone = models.CharField('手机号', max_length=11, blank=True, null=True,
                            validators=[RegexValidator(r'^1[3-9]\d{9}$', '请输入正确的手机号')])
    
    # 个人信息
    real_name = models.CharField('真实姓名', max_length=50, blank=True)
    avatar = models.FileField('头像', upload_to=user_avatar_upload_path, blank=True, null=True)
    gender = models.CharField('性别', max_length=10, choices=GENDER_CHOICES, blank=True)
    age = models.PositiveIntegerField('年龄', blank=True, null=True)
    bio = models.TextField('个人简介', max_length=500, blank=True)
    
    # 用户类型和状态
    user_type = models.CharField('用户类型', max_length=20, choices=USER_TYPE_CHOICES)
    is_active = models.BooleanField('是否激活', default=True)
    is_staff = models.BooleanField('是否为员工', default=False)
    
    # 时间戳
    date_joined = models.DateTimeField('注册时间', default=timezone.now)
    last_login = models.DateTimeField('最后登录', blank=True, null=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    
    class Meta:
        db_table = 'user'
        verbose_name = '01-用户总览'
        verbose_name_plural = '01-用户总览'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['phone']),
            models.Index(fields=['user_type']),
            models.Index(fields=['date_joined']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    def get_full_name(self):
        return self.real_name or self.username
    
    def get_short_name(self):
        return self.username


class Student(models.Model):
    """学生模型"""
    
    GRADE_CHOICES = [
        ('2021', '2021级'),
        ('2022', '2022级'),
        ('2023', '2023级'),
        ('2024', '2024级'),
        ('2025', '2025级'),
        ('2026', '2026级'),
        ('2027', '2027级'),
        ('2028', '2028级'),
    ]
    
    EDUCATION_LEVEL_CHOICES = [
        ('undergraduate', '本科'),
        ('master', '硕士'),
        ('doctor', '博士'),
        ('college', '专科'),
    ]
    
    STATUS_CHOICES = [
        ('studying', '在读'),
        ('graduated', '已毕业'),
        ('suspended', '休学'),
        ('dropped', '退学'),
    ]
    
    # 关联用户
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    # 学籍信息
    student_id = models.CharField('学号', max_length=20, unique=True)
    school = models.ForeignKey('organization.University', on_delete=models.CASCADE, verbose_name='学校')
    major = models.CharField('专业', max_length=100)
    grade = models.CharField('年级', max_length=10, choices=GRADE_CHOICES)
    education_level = models.CharField('学历层次', max_length=20, choices=EDUCATION_LEVEL_CHOICES, default='undergraduate')
    
    # 学业信息
    status = models.CharField('学籍状态', max_length=20, choices=STATUS_CHOICES, default='studying')
    expected_graduation = models.DateField('预计毕业时间', blank=True, null=True)
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'student'
        verbose_name = '02-学生用户'
        verbose_name_plural = '02-学生用户'
        indexes = [
            # 优化复合索引，基于常见查询模式
            models.Index(fields=['school', 'status'], name='student_school_status_idx'),
            models.Index(fields=['school', 'grade'], name='student_school_grade_idx'),
            models.Index(fields=['major', 'grade'], name='student_major_grade_idx'),
            models.Index(fields=['student_id']),  # 保留唯一字段索引
        ]
    
    def __str__(self):
        return f"{self.user.real_name or self.user.username} - {self.student_id}"
    
    @property
    def interests(self):
        """获取学生的兴趣标签"""
        return Tag1.objects.filter(tag1stumatch__student=self)
    
    @property
    def skills(self):
        """获取学生的技能标签"""
        return Tag2.objects.filter(tag2stumatch__student=self)
    
    def add_interest(self, tag1):
        """添加兴趣标签"""
        Tag1StuMatch.objects.get_or_create(student=self, tag1=tag1)
    
    def remove_interest(self, tag1):
        """移除兴趣标签"""
        Tag1StuMatch.objects.filter(student=self, tag1=tag1).delete()
    
    def add_skill(self, tag2):
        """添加技能标签"""
        Tag2StuMatch.objects.get_or_create(student=self, tag2=tag2)
    
    def remove_skill(self, tag2):
        """移除技能标签"""
        Tag2StuMatch.objects.filter(student=self, tag2=tag2).delete()
    
    def get_participated_projects(self):
        """获取参与的项目列表"""
        from studentproject.models import ProjectParticipant
        return ProjectParticipant.objects.filter(
            student=self,
            status__in=['approved', 'active']
        ).select_related('project')
    
    def get_created_projects(self):
        """获取创建的项目列表"""
        from studentproject.models import StudentProject
        return StudentProject.objects.filter(creator=self)
    
    def get_project_count(self):
        """获取参与项目总数"""
        return self.get_participated_projects().count() + self.get_created_projects().count()
    
    def is_project_member(self, project):
        """检查是否为某个项目的成员"""
        from studentproject.models import ProjectParticipant
        return ProjectParticipant.objects.filter(
            student=self,
            project=project,
            status__in=['approved', 'active']
        ).exists() or project.creator == self



class OrganizationUser(models.Model):
    """组织用户模型 - 企业员工/大学人员信息"""
    
    PERMISSION_CHOICES = [
        ('owner', '所有者'),
        ('admin', '管理员'),
        ('member', '成员'),
        ('pending', '待审核'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '未通过'),
    ]
    
    # 关联用户和组织
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='organization_profile')
    organization = models.ForeignKey('organization.Organization', on_delete=models.CASCADE, related_name='members', verbose_name='所属组织')
    
    # 组织用户字段
    position = models.CharField('职位/职务', max_length=100, blank=True,
                               help_text='企业：职位；大学：职务（如教授、副教授、讲师等）')
    department = models.CharField('部门/院系', max_length=100, blank=True,
                                 help_text='企业：部门；大学：院系')
    permission = models.CharField('权限', max_length=10, choices=PERMISSION_CHOICES, default='pending')
    status = models.CharField('认证状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # CAS认证相关字段（精简版）
    employee_id = models.CharField('工号', max_length=50, blank=True, null=True,
                                  help_text='教师工号，用于CAS统一认证')
    cas_user_id = models.CharField('CAS用户ID', max_length=100, blank=True, null=True, 
                                  help_text='CAS系统返回的用户唯一标识')
    auth_source = models.CharField('认证来源', max_length=20, default='manual',
                                  choices=[('manual', '手动注册'), ('cas', 'CAS认证')],
                                  help_text='用户认证来源')
    last_cas_login = models.DateTimeField('最后CAS登录时间', blank=True, null=True)

    
    # 时间戳字段
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'organization_user'
        verbose_name = '03-组织用户'
        verbose_name_plural = '03-组织用户'
        indexes = [
            # 保留有效的复合索引，移除被覆盖的单字段索引
            models.Index(fields=['organization', 'permission'], name='org_user_org_perm_idx'),
            models.Index(fields=['organization', 'status'], name='org_user_org_status_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.get_permission_display()})"
    
    @property
    def is_enterprise_user(self):
        """是否为企业用户"""
        return self.organization.organization_type == 'enterprise'
    
    @property
    def is_university_user(self):
        """是否为大学用户"""
        return self.organization.organization_type == 'university'
        
    @property
    def is_other_organization_user(self):
        """是否为其他组织用户"""
        return self.organization.organization_type == 'other'


class StudentKeyword(models.Model):
    """学生关键词表"""
    
    TAG_TYPE_CHOICES = [
        ('1', '兴趣'),
        ('2', '能力'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='keywords', verbose_name='学生')
    tag = models.CharField('关键词ID', max_length=50, help_text='关键词在对应表中的ID')
    tag_type = models.CharField('标签类型', max_length=1, choices=TAG_TYPE_CHOICES, help_text='1为兴趣，2为能力')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'student_keyword'
        verbose_name = '06-学生关键词'
        verbose_name_plural = '06-学生关键词'
        indexes = [
            models.Index(fields=['student', 'tag_type']),
            models.Index(fields=['tag_type']),
        ]
    
    def __str__(self):
        return f"{self.student.username} - {self.get_tag_type_display()} - {self.tag}"


class Tag1(models.Model):
    """兴趣标签表"""
    
    value = models.CharField('标签内容', max_length=100, unique=True, help_text='如：大模型、人工智能等')
    frequency = models.CharField('频率', max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'tag_1'
        verbose_name = '04-兴趣标签'
        verbose_name_plural = '04-兴趣标签'
        indexes = [
            models.Index(fields=['value'], name='tag1_value_idx'),
        ]
    
    def __str__(self):
        return self.value


class Tag2(models.Model):
    """能力标签表 - 层次化技能分类系统"""
    
    # 基本字段
    post = models.CharField('岗位描述', max_length=200, help_text='完整的岗位描述，如：互联网-java-前端')
    category = models.CharField('行业分类', max_length=100, help_text='第一级分类，如：互联网、设计')
    subcategory = models.CharField('技术分类', max_length=100, help_text='第二级分类，如：java、UI设计')
    specialty = models.CharField('专业方向', max_length=100, blank=True, null=True, help_text='第三级分类，如：前端、后端')
    frequency = models.CharField('频率', max_length=255, blank=True, null=True)
    
    # 层次结构字段
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='children', verbose_name='父级标签',
                              help_text='指向父级标签，用于构建层次结构',
                              db_index=False)  # 移除单字段索引，已被复合索引覆盖
    level = models.PositiveSmallIntegerField('层级', default=1, 
                                           help_text='标签层级：1=行业-技术，2=行业-技术-岗位')
    

    
    class Meta:
        db_table = 'tag_2'
        verbose_name = '05-能力标签'
        verbose_name_plural = '05-能力标签'
        indexes = [
            # 优化复合索引设计，基于查询模式
            models.Index(fields=['category', 'subcategory', 'specialty'], name='tag2_full_path_idx'),
            models.Index(fields=['level', 'category'], name='tag2_level_category_idx'),
            models.Index(fields=['parent', 'level'], name='tag2_parent_level_idx'),
        ]
        unique_together = [
            ('category', 'subcategory', 'specialty'),
        ]
    
    def __str__(self):
        if self.specialty:
            return f"{self.category}-{self.subcategory}-{self.specialty}"
        return f"{self.category}-{self.subcategory}"
    
    def get_children(self):
        """获取直接子标签"""
        return self.children.all()
    
    def get_descendants(self):
        """获取所有后代标签"""
        descendants = []
        for child in self.get_children():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    def get_root(self):
        """获取根标签"""
        if self.parent is None:
            return self
        return self.parent.get_root()
    
    @property
    def full_path(self):
        """获取完整路径"""
        if self.parent:
            return f"{self.parent.full_path} > {self}"
        return str(self)
    
    @property
    def is_leaf(self):
        """是否为叶子节点"""
        return not self.children.exists()


class Tag1StuMatch(models.Model):
    """兴趣标签与学生关联表"""
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name='学生')
    tag1 = models.ForeignKey(Tag1, on_delete=models.CASCADE, verbose_name='兴趣标签')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'tag1_stu_match'
        unique_together = ['student', 'tag1']
        verbose_name = '07-学生兴趣标签关联'
        verbose_name_plural = '07-学生兴趣标签关联'
        indexes = [
            # 保留复合索引，移除冗余的单字段索引
            models.Index(fields=['tag1', 'student'], name='tag1_stu_tag1_student_idx'),
        ]
    
    def __str__(self):
        return f"学生ID:{self.student.id} - {self.tag1.value}"


class Tag2StuMatch(models.Model):
    """能力标签与学生关联表"""
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name='学生')
    tag2 = models.ForeignKey(Tag2, on_delete=models.CASCADE, verbose_name='能力标签')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'tag2_stu_match'
        unique_together = ['student', 'tag2']
        verbose_name = '08-学生能力标签关联'
        verbose_name_plural = '08-学生能力标签关联'
        indexes = [
            # 保留复合索引，移除冗余的单字段索引
            models.Index(fields=['tag2', 'student'], name='tag2_stu_tag2_student_idx'),
        ]
    
    def __str__(self):
        return f"学生ID:{self.student.id} - {self.tag2}"
