from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    EvaluationCriteria,
    EvaluationIndicator,
    ProjectEvaluation,
    IndicatorScore,
    ProjectRanking
)


class EvaluationIndicatorInline(admin.TabularInline):
    """评分指标内联编辑"""
    model = EvaluationIndicator
    extra = 1
    fields = ('name', 'description', 'weight', 'max_score', 'order', 'is_required')
    ordering = ('order',)


@admin.register(EvaluationCriteria)
class EvaluationCriteriaAdmin(admin.ModelAdmin):
    """评分标准管理"""
    list_display = (
    'id', 'name', 'template_display', 'status', 'creator', 'weight_status', 'related_requirements_count',
    'clone_count_display', 'created_at')
    list_filter = ('status', 'is_template', 'created_at', 'creator', 'organization')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'get_related_requirements_info')
    inlines = [EvaluationIndicatorInline]
    actions = ['mark_as_template_action', 'clone_from_template_action']

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description')
        }),
        ('状态信息', {
            'fields': ('status', 'creator')
        }),
        ('模板信息', {
            'fields': ('is_template', 'template_source', 'organization'),
            'classes': ('collapse',)
        }),
        ('关联信息', {
            'fields': ('get_related_requirements_info',),
            'classes': ('collapse',)
        }),

        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        """获取查询集"""
        qs = super().get_queryset(request)
        return qs

    def template_display(self, obj):
        """显示模板信息"""
        if obj.is_template:
            return format_html('<span style="color: green;">✓ 模板</span>')
        elif obj.template_source:
            return format_html('<span style="color: blue;">基于: {}</span>', obj.template_source.name)
        else:
            return format_html('<span style="color: gray;">独立创建</span>')

    template_display.short_description = '模板状态'

    def clone_count_display(self, obj):
        """显示克隆次数"""
        if obj.is_template:
            count = obj.get_clone_count()
            if count > 0:
                return format_html('<span style="color: blue;">{} 次</span>', count)
            else:
                return format_html('<span style="color: gray;">未被使用</span>')
        return '-'

    clone_count_display.short_description = '克隆次数'

    def related_requirements_count(self, obj):
        """显示关联需求数量"""
        from django.urls import reverse
        count = obj.get_related_requirements().count()
        if count > 0:
            # 创建跳转到需求列表页的链接，并过滤显示使用此评分标准的需求
            requirements_url = reverse(
                'admin:project_requirement_changelist') + f'?evaluation_criteria__id__exact={obj.id}'
            return format_html(
                '<a href="{}" style="color: blue; text-decoration: none;" title="点击查看关联需求列表">{} 个</a>',
                requirements_url,
                count
            )
        else:
            return format_html('<span style="color: gray;">无关联</span>')

    related_requirements_count.short_description = '关联需求'

    def get_related_requirements_info(self, obj):
        """获取关联需求详细信息"""
        requirements = obj.get_related_requirements()[:10]  # 最多显示10个
        if requirements:
            info_list = []
            for req in requirements:
                status_display = req.get_status_display()
                org_name = req.organization.name if req.organization else '无组织'
                info_list.append(f"• [{req.id}] {req.title} ({status_display}) - {org_name}")

            total_count = obj.get_related_requirements().count()
            if total_count > 10:
                info_list.append(f"... 还有 {total_count - 10} 个需求")

            return "\n".join(info_list)
        return '暂无关联需求'

    get_related_requirements_info.short_description = '关联需求详情'

    def weight_status(self, obj):
        """显示权重状态"""
        total_weight = obj.get_total_weight()
        if total_weight == 100:
            return format_html('<span style="color: green;">✓ 完整(100%)</span>')
        elif total_weight > 100:
            return format_html('<span style="color: red;">✗ 超出({}%)</span>', total_weight)
        else:
            return format_html('<span style="color: orange;">⚠ 不足({}%)</span>', total_weight)

    weight_status.short_description = '权重状态'

    def mark_as_template_action(self, request, queryset):
        """标记为模板"""
        count = 0
        for obj in queryset:
            if not obj.is_template and obj.can_be_modified():
                obj.mark_as_template()
                count += 1
            elif obj.is_template:
                self.message_user(request, f'{obj.name} 已经是模板', level='warning')
            else:
                self.message_user(request, f'{obj.name} 正在使用中，无法标记为模板', level='warning')

        if count > 0:
            self.message_user(request, f'成功标记 {count} 个标准为模板')

    mark_as_template_action.short_description = '标记为模板'

    def clone_from_template_action(self, request, queryset):
        """基于模板创建新标准"""
        if queryset.count() != 1:
            self.message_user(request, '请选择一个模板来创建新标准', level='error')
            return

        obj = queryset.first()
        if not obj.is_template:
            self.message_user(request, '只能基于模板创建新标准', level='error')
            return

        try:
            new_name = f"{obj.name} - 副本 ({timezone.now().strftime('%Y%m%d%H%M')})"
            new_criteria = EvaluationCriteria.clone_from_template(
                template_id=obj.id,
                new_name=new_name,
                creator=request.user,
                organization=obj.organization
            )
            self.message_user(request, f'成功基于模板创建新标准：{new_criteria.name}')
        except Exception as e:
            self.message_user(request, f'创建新标准失败：{str(e)}', level='error')

    clone_from_template_action.short_description = '基于模板创建新标准'

    def save_model(self, request, obj, form, change):
        if not change:  # 新建时
            obj.creator = request.user
        super().save_model(request, obj, form, change)


@admin.register(EvaluationIndicator)
class EvaluationIndicatorAdmin(admin.ModelAdmin):
    """评分指标管理"""
    list_display = ('id', 'name', 'criteria', 'weight_display', 'max_score', 'order', 'is_required')
    list_filter = ('criteria', 'is_required')
    search_fields = ('name', 'description', 'criteria__name')
    ordering = ('criteria', 'order')

    fieldsets = (
        ('基本信息', {
            'fields': ('criteria', 'name', 'description')
        }),
        ('评分设置', {
            'fields': ('weight', 'max_score', 'order', 'is_required'),
            'description': '权重以百分比形式输入，如：25表示25%'
        })
    )

    def weight_display(self, obj):
        """显示权重百分比"""
        return f'{obj.weight}%'

    weight_display.short_description = '权重'

    def get_form(self, request, obj=None, **kwargs):
        """自定义表单，添加权重验证提示"""
        form = super().get_form(request, obj, **kwargs)
        if 'weight' in form.base_fields:
            form.base_fields['weight'].help_text = '权重百分比，0-100之间，同一标准下所有指标权重总和应为100%'
        return form


class IndicatorScoreInline(admin.TabularInline):
    """指标评分内联编辑"""
    model = IndicatorScore
    extra = 0
    fields = ('indicator', 'score', 'comment')
    readonly_fields = ('indicator',)


@admin.register(ProjectEvaluation)
class ProjectEvaluationAdmin(admin.ModelAdmin):
    """项目评分管理"""
    list_display = (
    'id', 'project_display', 'criteria_display', 'evaluator_display', 'status', 'completion_percentage', 'total_score',
    'weighted_score', 'created_at')
    list_filter = ('status', 'criteria', 'created_at', 'submitted_at')
    search_fields = ('project__title', 'criteria__name', 'evaluator__username')
    readonly_fields = ('total_score', 'weighted_score', 'created_at', 'updated_at', 'submitted_at')
    inlines = [IndicatorScoreInline]
    actions = ['recalculate_scores']

    fieldsets = (
        ('基本信息', {
            'fields': ('project', 'criteria', 'evaluator')
        }),
        ('评分信息', {
            'fields': ('status', 'total_score', 'weighted_score', 'overall_comment'),
            'description': '总分和加权总分由系统自动计算'
        }),

        ('时间信息', {
            'fields': ('deadline', 'created_at', 'updated_at', 'submitted_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        """优化查询"""
        qs = super().get_queryset(request).select_related('project', 'criteria', 'evaluator')
        return qs

    def project_display(self, obj):
        """显示项目信息"""
        from django.urls import reverse
        if obj.project:
            project_url = reverse('admin:studentproject_studentproject_change', args=[obj.project.id])
            return format_html(
                '<a href="{}" style="color: blue; text-decoration: none;" title="点击查看项目详情">{}</a>',
                project_url,
                obj.project.title
            )
        return '已删除项目'

    project_display.short_description = '项目'

    def criteria_display(self, obj):
        """显示评分标准信息"""
        from django.urls import reverse
        if obj.criteria:
            criteria_url = reverse('admin:projectscore_evaluationcriteria_change', args=[obj.criteria.id])
            return format_html(
                '<a href="{}" style="color: green; text-decoration: none;" title="点击查看评分标准详情">{}</a>',
                criteria_url,
                obj.criteria.name
            )
        return '已删除标准'

    criteria_display.short_description = '评分标准'

    def evaluator_display(self, obj):
        """显示评分者信息"""
        if obj.evaluator:
            return obj.evaluator.username
        return '已删除用户'

    evaluator_display.short_description = '评分者'

    def completion_percentage(self, obj):
        """显示评分完成度"""
        percentage = obj.get_completion_percentage()
        if percentage == 100:
            return format_html('<span style="color: green;">✓ {}%</span>', percentage)
        else:
            return format_html('<span style="color: orange;">⚠ {}%</span>', percentage)

    completion_percentage.short_description = '完成度'

    def recalculate_scores(self, request, queryset):
        """重新计算分数"""
        count = 0
        for obj in queryset:
            obj.calculate_scores()
            obj.save(update_fields=['total_score', 'weighted_score'])
            count += 1
        self.message_user(request, f'成功重新计算 {count} 条记录的分数')

    recalculate_scores.short_description = '重新计算选中记录的分数'


@admin.register(IndicatorScore)
class IndicatorScoreAdmin(admin.ModelAdmin):
    """指标评分管理"""
    list_display = (
    'evaluation_display', 'indicator_display', 'score_display', 'weighted_score_display', 'comment_preview',
    'get_evaluator', 'get_project')
    list_filter = ('indicator__criteria', 'evaluation__status')
    search_fields = ('evaluation__project__title', 'indicator__name', 'evaluation__evaluator__username')

    fieldsets = (
        ('评分信息', {
            'fields': ('evaluation', 'indicator')
        }),
        ('分数信息', {
            'fields': ('score', 'comment'),
            'description': '得分不能超过指标的最高分值'
        })
    )

    def evaluation_display(self, obj):
        """显示项目评分信息"""
        from django.urls import reverse
        if obj.evaluation:
            evaluation_url = reverse('admin:projectscore_projectevaluation_change', args=[obj.evaluation.id])
            return format_html(
                '<a href="{}" style="color: blue; text-decoration: none;" title="点击查看项目评分详情">评分#{}</a>',
                evaluation_url,
                obj.evaluation.id
            )
        return '已删除评分'

    evaluation_display.short_description = '项目评分'

    def indicator_display(self, obj):
        """显示评分指标信息"""
        from django.urls import reverse
        if obj.indicator:
            indicator_url = reverse('admin:projectscore_evaluationindicator_change', args=[obj.indicator.id])
            return format_html(
                '<a href="{}" style="color: green; text-decoration: none;" title="点击查看指标详情">{}</a>',
                indicator_url,
                obj.indicator.name
            )
        return '已删除指标'

    indicator_display.short_description = '评分指标'

    def get_evaluator(self, obj):
        return obj.evaluation.evaluator.username

    get_evaluator.short_description = '评分者'

    def get_project(self, obj):
        from django.urls import reverse
        if obj.evaluation and obj.evaluation.project:
            project_url = reverse('admin:studentproject_studentproject_change', args=[obj.evaluation.project.id])
            return format_html(
                '<a href="{}" style="color: blue; text-decoration: none;" title="点击查看项目详情">{}</a>',
                project_url,
                obj.evaluation.project.title
            )
        return '已删除项目'

    get_project.short_description = '项目'

    def score_display(self, obj):
        """显示得分和最高分"""
        return f'{obj.score}/{obj.indicator.max_score}'

    score_display.short_description = '得分/满分'

    def weighted_score_display(self, obj):
        """显示加权得分"""
        weighted = obj.get_weighted_score()
        return f'{weighted:.2f} ({obj.indicator.weight}%)'

    weighted_score_display.short_description = '加权得分(权重)'

    def comment_preview(self, obj):
        """显示评语预览"""
        if obj.comment:
            return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
        return '-'

    comment_preview.short_description = '评语预览'

    def get_form(self, request, obj=None, **kwargs):
        """自定义表单，添加分数验证提示"""
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.indicator:
            if 'score' in form.base_fields:
                form.base_fields['score'].help_text = f'最高分值：{obj.indicator.max_score}'
        return form

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'evaluation__project',
            'evaluation__evaluator',
            'indicator__criteria'
        )


@admin.register(ProjectRanking)
class ProjectRankingAdmin(admin.ModelAdmin):
    """项目排名管理"""
    list_display = (
    'project_display', 'criteria_display', 'rank', 'final_score', 'rank_percentage_display', 'rank_level_display',
    'published_at')
    list_filter = ('criteria', 'published_at')
    search_fields = ('project__title', 'criteria__name')
    ordering = ('criteria', 'rank')
    readonly_fields = ('published_at',)

    fieldsets = (
        ('基本信息', {
            'fields': ('project', 'criteria', 'rank')
        }),
        ('评分统计', {
            'fields': ('final_score',)
        }),
        ('时间信息', {
            'fields': ('published_at',),
            'classes': ('collapse',)
        })
    )

    def project_display(self, obj):
        """显示项目信息"""
        from django.urls import reverse
        if obj.project:
            project_url = reverse('admin:studentproject_studentproject_change', args=[obj.project.id])
            return format_html(
                '<a href="{}" style="color: blue; text-decoration: none;" title="点击查看项目详情">{}</a>',
                project_url,
                obj.project.title
            )
        return '已删除项目'

    project_display.short_description = '项目'

    def criteria_display(self, obj):
        """显示评分标准信息"""
        from django.urls import reverse
        if obj.criteria:
            criteria_url = reverse('admin:projectscore_evaluationcriteria_change', args=[obj.criteria.id])
            return format_html(
                '<a href="{}" style="color: green; text-decoration: none;" title="点击查看评分标准详情">{}</a>',
                criteria_url,
                obj.criteria.name
            )
        return '已删除标准'

    criteria_display.short_description = '评分标准'

    def rank_percentage_display(self, obj):
        """显示排名百分比"""
        percentage = obj.get_rank_percentage()
        return f'{percentage:.1f}%'

    rank_percentage_display.short_description = '排名百分比'

    def rank_level_display(self, obj):
        """显示排名等级"""
        level = obj.get_rank_level()
        colors = {
            'A+': 'green', 'A': 'green',
            'B+': 'blue', 'B': 'blue',
            'C+': 'orange', 'C': 'orange',
            'D': 'red'
        }
        color = colors.get(level, 'black')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, level)

    rank_level_display.short_description = '等级'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project', 'criteria')
