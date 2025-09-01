from django.db import models
from django.contrib.auth import get_user_model
from user.models import Tag1, Tag2, OrganizationUser
from organization.models import Organization

User = get_user_model()

import uuid
import os


def generate_unique_filename(original_filename):
    """生成唯一的文件名，使用UUID避免冲突"""
    file_ext = os.path.splitext(original_filename)[1]
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    return unique_name


def file_upload_path(instance, filename):
    """文件上传路径 - 使用UUID命名避免冲突"""
    unique_filename = generate_unique_filename(filename)
    return f'uploads/files/{unique_filename}'


def get_requirement_file_path(requirement_id, filename):
    """生成需求文件保存路径 - 使用UUID命名"""
    unique_filename = generate_unique_filename(filename)
    return f'uploads/files/requirement/{unique_filename}'


def get_resource_file_path(resource_id, filename):
    """根据资源ID生成文件保存路径 - 使用UUID命名"""
    unique_filename = generate_unique_filename(filename)
    return f'uploads/files/resource/{unique_filename}'


def create_virtual_folder(folder_name, parent_path='', requirement_id=None):
    """创建虚拟文件夹"""
    from .models import File

    # 构建虚拟路径
    if parent_path and not parent_path.endswith('/'):
        parent_path += '/'
    virtual_path = f"{parent_path}{folder_name}"

    # 检查文件夹是否已存在
    if File.objects.filter(path=virtual_path, is_folder=True).exists():
        return File.objects.get(path=virtual_path, is_folder=True)

    # 创建虚拟文件夹
    folder = File.objects.create(
        name=folder_name,
        path=virtual_path,
        parent_path=parent_path.rstrip('/') if parent_path else '',
        is_folder=True,
        size=0
    )
    return folder


def parse_file_path_structure(file_path):
    """解析文件路径结构，返回文件夹层级和文件名"""
    # 标准化路径分隔符
    normalized_path = file_path.replace('\\', '/').strip('/')

    if '/' not in normalized_path:
        return [], normalized_path

    parts = normalized_path.split('/')
    folders = parts[:-1]
    filename = parts[-1]

    return folders, filename


class File(models.Model):
    """文件模型 - 支持虚拟文件系统"""

    id = models.AutoField(primary_key=True)
    url = models.URLField(verbose_name='完整下载地址', blank=True, help_text='文件的完整URL下载地址')
    name = models.CharField(max_length=255, verbose_name='文件/文件夹名称')
    path = models.CharField(max_length=500, verbose_name='虚拟路径', blank=True,
                            help_text='虚拟文件系统中的路径，如：/项目文档/设计图/logo.png')
    real_path = models.CharField(max_length=500, verbose_name='实际存储路径', blank=True, null=True,
                                 help_text='文件在服务器上的实际存储路径，文件夹为null')
    parent_path = models.CharField(max_length=500, verbose_name='父级虚拟路径', blank=True, null=True,
                                   help_text='父级文件夹的虚拟路径')
    is_folder = models.BooleanField(default=False, verbose_name='是否为文件夹',
                                    help_text='True表示文件夹，False表示文件')
    is_cloud_link = models.BooleanField(default=False, verbose_name='是否为网盘链接',
                                        help_text='True表示网盘链接文件，False表示普通文件')
    cloud_password = models.CharField(max_length=100, verbose_name='网盘链接密码', blank=True, null=True,
                                      help_text='网盘链接的提取密码')
    size = models.BigIntegerField(verbose_name='文件大小（字节）', default=0)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间戳')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间戳')

    class Meta:
        verbose_name = '01-文件'
        verbose_name_plural = '01-文件'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({'文件夹' if self.is_folder else '文件'})"

    def get_children(self):
        """获取子文件和文件夹"""
        return File.objects.filter(parent_path=self.path).order_by('-is_folder', 'name')

    def get_full_virtual_path(self):
        """获取完整的虚拟路径"""
        return self.path or f"/{self.name}"


class Requirement(models.Model):
    """需求模型"""

    STATUS_CHOICES = [
        ('under_review', '审核中'),
        ('review_failed', '审核失败'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('paused', '已暂停'),
    ]

    id = models.AutoField(primary_key=True, verbose_name='ID')
    title = models.CharField(max_length=255, verbose_name='标题')
    brief = models.CharField(max_length=255, verbose_name='简介')
    description = models.TextField(verbose_name='详细描述')
    tag1 = models.ManyToManyField(Tag1, blank=True, verbose_name='兴趣标签')
    tag2 = models.ManyToManyField(Tag2, blank=True, verbose_name='能力标签')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, verbose_name='状态')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, verbose_name='组织')
    publish_people = models.ForeignKey(OrganizationUser, on_delete=models.CASCADE, verbose_name='发布人')
    finish_time = models.DateField(null=True, blank=True, verbose_name='完成时间')
    budget = models.CharField(max_length=255, verbose_name='预算', null=True, blank=True)
    people_count = models.CharField(max_length=255, verbose_name='人数需求', null=True, blank=True)
    support_provided = models.TextField(blank=True, null=True, verbose_name='可提供的支持')
    evaluation_criteria = models.ForeignKey(
        'projectscore.EvaluationCriteria',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requirements_using_criteria',
        verbose_name='评分标准',
        help_text='关联的评分标准，用于项目评分'
    )
    evaluation_published = models.BooleanField(
        default=False,
        verbose_name='评分已公示',
        help_text='标记该需求下的项目评分是否已公示'
    )
    views = models.IntegerField(default=0, verbose_name='浏览数')
    resources = models.ManyToManyField('Resource', blank=True, verbose_name='关联资源')
    files = models.ManyToManyField(File, blank=True, verbose_name='文件信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '02-需求'
        verbose_name_plural = '02-需求'
        ordering = ['-created_at']
        indexes = [
            # 单字段索引
            models.Index(fields=['status'], name='req_status_idx'),
            models.Index(fields=['organization'], name='req_org_idx'),
            models.Index(fields=['created_at'], name='req_created_idx'),
            models.Index(fields=['views'], name='req_views_idx'),
            models.Index(fields=['title'], name='req_title_idx'),
            models.Index(fields=['evaluation_criteria'], name='req_eval_criteria_idx'),

            # 复合索引（按查询频率排序）
            models.Index(fields=['status', 'created_at'], name='req_status_created_idx'),
            models.Index(fields=['organization', 'status'], name='req_org_status_idx'),
            models.Index(fields=['organization', 'created_at'], name='req_org_created_idx'),
            models.Index(fields=['status', 'organization', 'created_at'], name='req_status_org_created_idx'),
            models.Index(fields=['evaluation_criteria', 'status'], name='req_eval_status_idx'),

            # 排序优化索引
            models.Index(fields=['-views'], name='req_views_desc_idx'),
            models.Index(fields=['-created_at'], name='req_created_desc_idx'),
        ]

    def __str__(self):
        return self.title


class RequirementFavorite(models.Model):
    """需求收藏模型"""

    id = models.AutoField(primary_key=True, verbose_name='ID')
    student = models.ForeignKey('user.Student', on_delete=models.CASCADE, verbose_name='学生用户')
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE, verbose_name='需求')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='收藏时间')

    class Meta:
        verbose_name = '04-需求收藏'
        verbose_name_plural = '04-需求收藏'
        unique_together = ['student', 'requirement']  # 确保同一学生不能重复收藏同一需求
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student'], name='req_fav_student_idx'),
            models.Index(fields=['requirement'], name='req_fav_req_idx'),
            models.Index(fields=['student', 'created_at'], name='req_fav_student_created_idx'),
        ]

    def __str__(self):
        return f"{self.student.user.username} 收藏了 {self.requirement.title}"


class Resource(models.Model):
    """资源模型"""
    TYPE_CHOICES = [
        ('code', '代码'),
        ('dataset', '数据集'),
        ('document', '文档'),
        ('course', '课程'),
        ('video', '视频'),
        ('tool', '工具'),
    ]

    STATUS_CHOICES = [
        ('published', '已发布'),
        ('draft', '草稿'),
        ('unpublished', '已下线'),
    ]

    id = models.AutoField(primary_key=True, verbose_name='ID')
    title = models.CharField(max_length=255, verbose_name='标题')
    description = models.TextField(verbose_name='描述')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, verbose_name='类型')
    tag1 = models.ManyToManyField(Tag1, blank=True, verbose_name='兴趣标签')
    tag2 = models.ManyToManyField(Tag2, blank=True, verbose_name='能力标签')
    files = models.ManyToManyField(File, blank=True, verbose_name='文件信息')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, verbose_name='状态')
    create_person = models.ForeignKey(OrganizationUser, on_delete=models.CASCADE, related_name='created_resources',
                                      verbose_name='创建人')
    update_person = models.ForeignKey(OrganizationUser, on_delete=models.CASCADE, related_name='updated_resources',
                                      verbose_name='更新人')
    downloads = models.PositiveIntegerField(default=0, verbose_name='下载数')
    views = models.PositiveIntegerField(default=0, verbose_name='浏览数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间戳')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间戳')

    class Meta:
        verbose_name = '03-资源'
        verbose_name_plural = '03-资源'
        ordering = ['-created_at']
        indexes = [
            # 单字段索引
            models.Index(fields=['status'], name='res_status_idx'),
            models.Index(fields=['type'], name='res_type_idx'),
            models.Index(fields=['create_person'], name='res_creator_idx'),
            models.Index(fields=['created_at'], name='res_created_idx'),
            models.Index(fields=['title'], name='res_title_idx'),
            models.Index(fields=['downloads'], name='res_downloads_idx'),
            models.Index(fields=['views'], name='res_views_idx'),

            # 复合索引
            models.Index(fields=['status', 'created_at'], name='res_status_created_idx'),
            models.Index(fields=['create_person', 'status'], name='res_creator_status_idx'),
            models.Index(fields=['create_person', 'created_at'], name='res_creator_created_idx'),

            # 排序优化索引
            models.Index(fields=['-downloads'], name='res_downloads_desc_idx'),
            models.Index(fields=['-views'], name='res_views_desc_idx'),
            models.Index(fields=['-created_at'], name='res_created_desc_idx'),

            # 统计查询优化索引
            models.Index(fields=['status', 'created_at', 'downloads'], name='res_stat_idx'),
            models.Index(fields=['status', 'created_at', 'views'], name='res_stat_views_idx'),
        ]

    def __str__(self):
        return self.title