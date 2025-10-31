from django.db import models
from user.models import Student
from project.models import Requirement


class TagMatch(models.Model):
    """标签匹配模型 - 学生与项目需求的标签匹配关系"""
    
    TAG_SOURCE_CHOICES = [
        ('tag1', '兴趣标签'),
        ('tag2', '能力标签'),
    ]
    
    # 主键ID - 自增
    id = models.AutoField(primary_key=True, verbose_name='主键ID')
    
    # 学生ID - 普通整数字段
    student_id = models.PositiveIntegerField(
        verbose_name='学生ID',
        help_text='关联的学生用户ID',
        db_column='Sid',  # 数据库列名
    )
    
    # 项目需求ID - 普通整数字段
    requirement_id = models.PositiveIntegerField(
        verbose_name='项目需求ID',
        help_text='关联的项目需求ID',
        db_column='Pid',  # 数据库列名
    )
    
    # 标签来源 - 优化为选择字段
    tag_source = models.CharField(
        max_length=10, 
        choices=TAG_SOURCE_CHOICES,
        db_column='Msource',  # 保持与数据库字段名一致
        null=True, 
        blank=True,
        verbose_name='标签来源',
        help_text='标签来源类型：tag1为兴趣标签，tag2为能力标签'
    )
    
    # 标签ID - 整数字段
    tag_id = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='标签ID',
        help_text='对应标签表中的ID'
    )
    
    class Meta:
        db_table = 'tag_match'  # 保持与现有数据库表名一致
        verbose_name = '标签匹配'
        verbose_name_plural = '标签匹配'
        
        # 索引优化 - 基于查询模式的复合索引
        indexes = [
            # 复合索引 - 优化常用查询
            models.Index(fields=['student_id', 'tag_source'], name='tag_match_stu_source_idx'),
            models.Index(fields=['requirement_id', 'tag_source'], name='tag_match_req_source_idx'),
            # 移除 tag_match_stu_req_idx，已被唯一约束覆盖
            models.Index(fields=['tag_source', 'tag_id'], name='tag_match_source_tag_idx'),
        ]
        
        # 唯一约束 - 防止重复匹配记录
        unique_together = [
            ('student_id', 'requirement_id', 'tag_source', 'tag_id'),
        ]
    
    def __str__(self):
        return f"学生{self.student_id} - 需求{self.requirement_id} - {self.get_tag_source_display()}"
    
    @property
    def student_id_str(self):
        """获取学生ID字符串 - 兼容原有接口"""
        return str(self.student_id)
    
    @property
    def requirement_id_str(self):
        """获取需求ID字符串 - 兼容原有接口"""
        return str(self.requirement_id)
    
    def get_tag_object(self):
        """根据tag_source和tag_id获取对应的标签对象"""
        if not self.tag_source or not self.tag_id:
            return None
            
        try:
            if self.tag_source == 'tag1':
                from user.models import Tag1
                return Tag1.objects.get(id=self.tag_id)
            elif self.tag_source == 'tag2':
                from user.models import Tag2
                return Tag2.objects.get(id=self.tag_id)
        except (Tag1.DoesNotExist, Tag2.DoesNotExist):
            return None
        
        return None
