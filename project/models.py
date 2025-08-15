from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Project(models.Model):
    """项目模型"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name='项目名称')
    description = models.TextField(blank=True, verbose_name='项目描述')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects', verbose_name='创建者')
    members = models.ManyToManyField(User, through='ProjectMember', related_name='joined_projects', verbose_name='项目成员')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    
    class Meta:
        verbose_name = '项目'
        verbose_name_plural = '项目'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class ProjectMember(models.Model):
    """项目成员关系模型"""
    ROLE_CHOICES = [
        ('owner', '项目所有者'),
        ('admin', '管理员'),
        ('member', '普通成员'),
        ('viewer', '查看者'),
    ]
    
    id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='项目')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member', verbose_name='角色')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')
    
    class Meta:
        verbose_name = '项目成员'
        verbose_name_plural = '项目成员'
        unique_together = ['project', 'user']
    
    def __str__(self):
        return f'{self.user.username} - {self.project.name} ({self.get_role_display()})'