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
    username = models.CharField('用户名', max_length=30, unique=True, default='user',
                               validators=[RegexValidator(r'^[a-zA-Z0-9_]+$', '用户名只能包含字母、数字和下划线')])
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
        verbose_name = '用户'
        verbose_name_plural = '用户'
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
    school = models.CharField('学校', max_length=100)
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
        verbose_name = '学生'
        verbose_name_plural = '学生'
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['school']),
            models.Index(fields=['major']),
            models.Index(fields=['grade']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user.real_name or self.user.username} - {self.student_id}"
    
    @property
    def interests(self):
        """获取学生的兴趣标签"""
        return Tag1.objects.filter(tag1stumatch__student=self.user)
    
    @property
    def skills(self):
        """获取学生的技能标签"""
        return Tag2.objects.filter(tag2stumatch__student=self.user)
    
    def add_interest(self, tag1):
        """添加兴趣标签"""
        Tag1StuMatch.objects.get_or_create(student=self.user, tag1=tag1)
    
    def remove_interest(self, tag1):
        """移除兴趣标签"""
        Tag1StuMatch.objects.filter(student=self.user, tag1=tag1).delete()
    
    def add_skill(self, tag2):
        """添加技能标签"""
        Tag2StuMatch.objects.get_or_create(student=self.user, tag2=tag2)
    
    def remove_skill(self, tag2):
        """移除技能标签"""
        Tag2StuMatch.objects.filter(student=self.user, tag2=tag2).delete()



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
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'organization_user'
        verbose_name = '组织用户'
        verbose_name_plural = '组织用户'
        indexes = [
            models.Index(fields=['permission']),
            models.Index(fields=['status']),
            models.Index(fields=['organization']),
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
        verbose_name = '学生关键词'
        verbose_name_plural = '学生关键词'
        indexes = [
            models.Index(fields=['student', 'tag_type']),
            models.Index(fields=['tag_type']),
        ]
    
    def __str__(self):
        return f"{self.student.username} - {self.get_tag_type_display()} - {self.tag}"


class Tag1(models.Model):
    """兴趣标签表"""
    
    value = models.CharField('标签内容', max_length=100, unique=True, help_text='如：大模型、人工智能等')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'tag_1'
        verbose_name = '兴趣标签'
        verbose_name_plural = '兴趣标签'
        indexes = [
            models.Index(fields=['value']),
        ]
    
    def __str__(self):
        return self.value


class Tag2(models.Model):
    """能力标签表"""
    
    post = models.CharField('岗位名称', max_length=50, help_text='如：前端、后端')
    subclasses = models.CharField('一级分类', max_length=100)
    subdivision = models.CharField('二级分类', max_length=100)
    zhuisu_id = models.BigIntegerField('追溯ID', null=True, blank=True, help_text='二级分类所属一级分类的ID')
    required_number = models.IntegerField('需求人数', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'tag_2'
        verbose_name = '能力标签'
        verbose_name_plural = '能力标签'
        indexes = [
            models.Index(fields=['post']),
            models.Index(fields=['subclasses']),
            models.Index(fields=['zhuisu_id']),
        ]
    
    def __str__(self):
        return f"{self.post} - {self.subclasses} - {self.subdivision}"


class Tag1StuMatch(models.Model):
    """兴趣标签与学生关联表"""
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='学生')
    tag1 = models.ForeignKey(Tag1, on_delete=models.CASCADE, verbose_name='兴趣标签')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'tag1_stu_match'
        unique_together = ['student', 'tag1']
        verbose_name = '学生兴趣标签关联'
        verbose_name_plural = '学生兴趣标签关联'
    
    def __str__(self):
        return f"{self.student.username} - {self.tag1.value}"


class Tag2StuMatch(models.Model):
    """能力标签与学生关联表"""
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='学生')
    tag2 = models.ForeignKey(Tag2, on_delete=models.CASCADE, verbose_name='能力标签')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'tag2_stu_match'
        unique_together = ['student', 'tag2']
        verbose_name = '学生能力标签关联'
        verbose_name_plural = '学生能力标签关联'
    
    def __str__(self):
        return f"{self.student.username} - {self.tag2.post}({self.tag2.subdivision})"
