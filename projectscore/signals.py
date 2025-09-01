from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal
from .models import (
    IndicatorScore,
    ProjectEvaluation,
    ProjectRanking,
    EvaluationCriteria
)


@receiver([post_save, post_delete], sender=IndicatorScore)
def update_evaluation_scores(sender, instance, **kwargs):
    """当指标评分变化时，自动更新项目评分的总分和加权总分"""
    evaluation = instance.evaluation
    evaluation.calculate_scores()
    evaluation.save(update_fields=['total_score', 'weighted_score'])


@receiver(post_save, sender=ProjectEvaluation)
def update_project_ranking(sender, instance, **kwargs):
    """更新项目排名"""
    if instance.status == 'published':
        # 获取或创建排名记录
        ranking, created = ProjectRanking.objects.get_or_create(
            project=instance.project,
            criteria=instance.criteria,
            defaults={'final_score': instance.weighted_score, 'rank': 1}
        )

        if not created:
            ranking.final_score = instance.weighted_score
            ranking.save()

        # 重新计算所有排名
        rankings = ProjectRanking.objects.filter(
            criteria=instance.criteria
        ).order_by('-final_score')

        for index, rank_obj in enumerate(rankings, 1):
            if rank_obj.rank != index:
                rank_obj.rank = index
                rank_obj.save(update_fields=['rank'])
