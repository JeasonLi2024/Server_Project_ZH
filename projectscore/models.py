from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Sum, Avg, Count
from decimal import Decimal

User = get_user_model()


class EvaluationCriteria(models.Model):
    """评分标准模型（基于模板复制的独立标准）"""
    
    STATUS_CHOICES = [
        ('active', '启用'),
        ('archived', '归档'),
    ]
    
    # 基本信息
    name = models.CharField(max_length=200, verbose_name='标准名称')  # 移除 db_index=True
    description = models.TextField(verbose_name='标准描述')
    
    # 注意：需求关联通过 project.Requirement.evaluation_criteria 字段实现
    # 一个评分标准可以被多个需求使用，但一个需求只能关联一个评分标准
    
    # 状态
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='状态'
        # 移除 db_index=True，因为Meta.indexes中已有status索引
    )
    
    # 创建者
    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_criteria',
        verbose_name='创建者'
    )
    
    # 模板相关字段
    is_template = models.BooleanField(
        default=False,
        verbose_name='是否为模板',
        help_text='标记为模板的评分标准可供其他需求复制使用'
        # 移除 db_index=True，因为Meta.indexes中已有is_template复合索引
    )
    
    template_source = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cloned_criteria',
        verbose_name='模板来源',
        help_text='基于哪个模板创建的评分标准'
    )
    
    # 组织信息（用于模板共享范围控制）
    organization = models.ForeignKey(
        'organization.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='evaluation_criteria',
        verbose_name='所属组织'
    )
    
    # 删除软删除字段
    
    # 时间信息
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'projectscore_evaluation_criteria'
        verbose_name = '01-评分标准'
        verbose_name_plural = '01-评分标准'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_template', 'organization']),
            models.Index(fields=['template_source', 'created_at']),
            models.Index(fields=['organization', 'status']),
        ]
    
    def clean(self):
        """验证权重总和和业务规则"""
        # 验证权重总和
        if self.pk:
            total_weight = self.indicators.aggregate(total=Sum('weight'))['total'] or 0
            if total_weight > 100:
                raise ValidationError('所有指标权重总和不能超过100%')
        
        # 验证已使用的评分标准不可修改核心规则
        if self.pk and self.status == 'active':
            # 检查是否有已提交或已公示的项目评分
            has_submitted_evaluations = self.project_evaluations.filter(
                status__in=['submitted', 'published']
            ).exists()
            
            if has_submitted_evaluations:
                # 获取原始数据进行比较
                original = EvaluationCriteria.objects.get(pk=self.pk)
                
                # 检查核心字段是否被修改
                core_fields_changed = (
                    self.name != original.name or
                    self.description != original.description
                )
                
                if core_fields_changed:
                    raise ValidationError(
                        '该评分标准已用于项目评选，不可修改核心规则。'
                        '如需修改，请基于此标准创建新的评分标准。'
                    )
    
    def get_total_weight(self):
        """获取总权重"""
        return self.indicators.aggregate(total=Sum('weight'))['total'] or 0
    
    def is_weight_complete(self):
        """检查权重是否完整（总和为100）"""
        return self.get_total_weight() == 100
    
    @classmethod
    def clone_from_template(cls, template_id, new_name, new_description=None, creator=None, organization=None):
        """基于模板创建新的评分标准"""
        try:
            template = cls.objects.get(id=template_id)
        except cls.DoesNotExist:
            raise ValidationError('指定的模板不存在')
        
        # 创建新的评分标准
        new_criteria = cls.objects.create(
            name=new_name,
            description=new_description or template.description,
            status='active',  # 新创建的标准默认为启用状态
            creator=creator,
            template_source=template,
            organization=organization or template.organization,
            is_template=False  # 基于模板创建的标准默认不是模板
        )
        
        # 复制所有指标
        for indicator in template.indicators.all():
            EvaluationIndicator.objects.create(
                criteria=new_criteria,
                name=indicator.name,
                description=indicator.description,
                weight=indicator.weight,
                max_score=indicator.max_score,
                order=indicator.order,
                is_required=indicator.is_required
            )
        
        return new_criteria
    
    def mark_as_template(self):
        """标记为模板"""
        self.is_template = True
        self.save(update_fields=['is_template'])
    
    def get_clone_count(self):
        """获取基于此模板创建的评分标准数量"""
        return self.cloned_criteria.count()
    
    def can_be_modified(self):
        """检查是否可以修改"""
        # 检查是否有已提交的评分
        has_submitted = self.project_evaluations.filter(
            status__in=['submitted', 'published']
        ).exists()
        
        return not has_submitted
    

    
    def is_used_by_requirements(self):
        """检查是否被需求使用"""
        from project.models import Requirement
        return Requirement.objects.filter(evaluation_criteria=self).exists()
    
    def get_related_requirements(self):
        """获取使用此评分标准的需求列表"""
        from project.models import Requirement
        # 直接通过需求模型的evaluation_criteria字段获取相关需求
        return Requirement.objects.filter(
            evaluation_criteria=self
        ).distinct()
    
    @classmethod
    def get_available_templates(cls, organization=None):
        """获取可用的模板列表"""
        queryset = cls.objects.filter(
            is_template=True,
            status='active'
        )
        
        if organization:
            queryset = queryset.filter(organization=organization)
        
        return queryset.order_by('-created_at')
    
    # 移除软删除方法
    
    def __str__(self):
        template_info = " [模板]" if self.is_template else ""
        source_info = f" (基于: {self.template_source.name})" if self.template_source else ""
        return f"{self.name}{template_info}{source_info}"


class EvaluationIndicator(models.Model):
    """评分指标模型"""
    
    # 关联评分标准
    criteria = models.ForeignKey(
        EvaluationCriteria,
        on_delete=models.CASCADE,
        related_name='indicators',
        verbose_name='评分标准'
    )
    
    # 指标信息
    name = models.CharField(max_length=100, verbose_name='指标名称')  # 移除 db_index=True
    description = models.TextField(blank=True, verbose_name='指标描述')
    
    # 权重和分值（权重用百分数表示，0-100）
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='权重（%）',
        help_text='权重百分比，0-100之间'
    )
    
    max_score = models.PositiveIntegerField(
        default=100,
        verbose_name='最高分值'
    )
    
    # 排序
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='排序'
    )
    
    # 是否必填
    is_required = models.BooleanField(
        default=True,
        verbose_name='是否必填'
    )
    
    class Meta:
        db_table = 'projectscore_evaluation_indicator'
        verbose_name = '02-评分指标'
        verbose_name_plural = '02-评分指标'
        ordering = ['order', 'id']
        unique_together = ['criteria', 'name']
        indexes = [
            models.Index(fields=['criteria', 'order']),
        ]
    
    def clean(self):
        """验证权重范围和总和"""
        if self.weight < 0 or self.weight > 100:
            raise ValidationError('权重必须在0-100之间')
        
        # 检查同一标准下所有指标权重总和
        if self.criteria_id:
            other_indicators = EvaluationIndicator.objects.filter(
                criteria=self.criteria
            ).exclude(pk=self.pk)
            total_weight = other_indicators.aggregate(total=Sum('weight'))['total'] or 0
            total_weight += self.weight
            
            if total_weight > 100:
                raise ValidationError(f'权重总和不能超过100%，当前总和为{total_weight}%')
    
    def __str__(self):
        return f"{self.criteria.name} - {self.name}"


class ProjectEvaluation(models.Model):
    """项目评分模型"""
    
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('submitted', '已提交'),
        ('published', '已公示'),
    ]
    
    # 关联项目和评分标准
    project = models.ForeignKey(
        'studentproject.StudentProject',
        on_delete=models.CASCADE,
        related_name='evaluations',
        verbose_name='项目'
    )
    
    criteria = models.ForeignKey(
        EvaluationCriteria,
        on_delete=models.CASCADE,
        related_name='project_evaluations',
        verbose_name='评分标准'
    )
    
    # 评分者（软删除支持）
    evaluator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_evaluations',
        verbose_name='评分者'
    )
    
    # 最近修改人
    last_modifier = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_evaluations',
        verbose_name='最近修改人'
    )
    
    # 评分状态
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='评分状态'
        # 移除 db_index=True，因为Meta.indexes中已有status索引
    )
    
    # 总分和加权总分（自动计算，不手动设置）
    total_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name='总分',
        editable=False
    )
    
    weighted_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name='加权总分',
        editable=False
    )
    
    # 总体评语
    overall_comment = models.TextField(
        blank=True,
        verbose_name='总体评语'
    )
    
    # 删除软删除字段
    
    # 时间信息
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='提交时间')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='公示时间')
    
    # 评分截止时间
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='评分截止时间'
    )
    
    class Meta:
        db_table = 'projectscore_project_evaluation'
        verbose_name = '03-项目评分'
        verbose_name_plural = '03-项目评分'
        unique_together = ['project', 'criteria', 'evaluator']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['project', 'criteria']),
            models.Index(fields=['created_at']),
        ]
    
    def calculate_scores(self):
        """计算总分和加权总分"""
        scores = self.indicator_scores.select_related('indicator')
        total = Decimal('0')
        weighted_total = Decimal('0')
        
        for score in scores:
            total += score.score
            weighted_total += score.score * (score.indicator.weight / 100)
        
        self.total_score = total
        self.weighted_score = weighted_total
        return total, weighted_total
    
    def get_completion_percentage(self):
        """获取评分完成度"""
        required_indicators = self.criteria.indicators.filter(is_required=True).count()
        completed_scores = self.indicator_scores.filter(
            indicator__is_required=True
        ).count()
        
        if required_indicators == 0:
            return 100
        return (completed_scores / required_indicators) * 100
    
    # 移除软删除方法
    
    def __str__(self):
        evaluator_name = self.evaluator.username if self.evaluator else '已删除用户'
        return f"{self.project} - {self.criteria.name} - {evaluator_name}"


class IndicatorScore(models.Model):
    """指标评分模型"""
    
    # 关联评分和指标
    evaluation = models.ForeignKey(
        ProjectEvaluation,
        on_delete=models.CASCADE,
        related_name='indicator_scores',
        verbose_name='项目评分'
    )
    
    indicator = models.ForeignKey(
        EvaluationIndicator,
        on_delete=models.CASCADE,
        related_name='scores',
        verbose_name='评分指标'
    )
    
    # 分数和评语
    score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name='得分'
    )
    
    comment = models.TextField(
        blank=True,
        verbose_name='评语'
    )
    
    class Meta:
        db_table = 'projectscore_indicator_score'
        verbose_name = '04-指标评分'
        verbose_name_plural = '04-指标评分'
        unique_together = ['evaluation', 'indicator']
        indexes = [
            models.Index(fields=['evaluation', 'indicator']),
        ]
    
    def clean(self):
        """验证分数不超过指标最高分"""
        if self.score < 0:
            raise ValidationError('得分不能为负数')
        
        if self.indicator and self.score > self.indicator.max_score:
            raise ValidationError(
                f'得分不能超过指标最高分值{self.indicator.max_score}'
            )
    
    def get_weighted_score(self):
        """获取加权得分"""
        return self.score * (self.indicator.weight / 100)
    
    def __str__(self):
        return f"{self.evaluation} - {self.indicator.name}: {self.score}"


class ProjectRanking(models.Model):
    """项目排名模型"""
    
    # 关联项目和评分标准
    project = models.ForeignKey(
        'studentproject.StudentProject',
        on_delete=models.CASCADE,
        related_name='rankings',
        verbose_name='项目'
    )
    
    criteria = models.ForeignKey(
        EvaluationCriteria,
        on_delete=models.CASCADE,
        related_name='project_rankings',
        verbose_name='评分标准'
    )
    
    # 排名信息
    rank = models.PositiveIntegerField(verbose_name='排名')  # 移除 db_index=True，因为Meta.indexes中已有rank复合索引
    
    # 最终得分（单人评分）
    final_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='最终得分'
    )
    
    # 公示时间
    published_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='公示时间'
    )
    
    # 更新时间
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'projectscore_project_ranking'
        verbose_name = '05-项目排名'
        verbose_name_plural = '05-项目排名'
        unique_together = ['project', 'criteria']
        ordering = ['rank']
        indexes = [
            models.Index(fields=['criteria', 'rank']),
            models.Index(fields=['final_score']),
        ]
    
    def get_rank_percentage(self):
        """获取排名百分比"""
        total_projects = ProjectRanking.objects.filter(criteria=self.criteria).count()
        if total_projects == 0:
            return 0
        return ((total_projects - self.rank + 1) / total_projects) * 100
    
    def get_rank_level(self):
        """获取排名等级"""
        percentage = self.get_rank_percentage()
        if percentage >= 90:
            return 'A+'
        elif percentage >= 80:
            return 'A'
        elif percentage >= 70:
            return 'B+'
        elif percentage >= 60:
            return 'B'
        elif percentage >= 50:
            return 'C+'
        elif percentage >= 40:
            return 'C'
        else:
            return 'D'
    
    def __str__(self):
        return f"{self.project} - 排名: {self.rank}"
