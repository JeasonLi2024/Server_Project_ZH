"""Dashboard统计数据Celery定时任务"""
import json
from datetime import date
from celery import shared_task
from django.db.models import Count, Q
from user.models import Tag1, Tag2, Tag1StuMatch, Tag2StuMatch
from organization.models import Organization
from studentproject.models import StudentProject
from project.models import Requirement
from dashboard.views import get_redis_client


@shared_task(bind=True, max_retries=3)
def update_tag1_student_stats(self):
    """
    更新Tag1学生标签统计数据
    """
    try:
        # 统计每个Tag1标签关联的学生数量
        tag1_stats = Tag1.objects.annotate(
            student_count=Count('tag1stumatch__student', distinct=True)
        ).filter(
            student_count__gt=0
        ).order_by('-student_count')[:5]
        
        # 计算总学生数（有Tag1标签的学生）
        total_students = Tag1StuMatch.objects.values('student').distinct().count()
        
        # 构建返回数据
        stats_data = []
        for tag in tag1_stats:
            percentage = round((tag.student_count / total_students * 100), 2) if total_students > 0 else 0
            stats_data.append({
                'tag_id': tag.id,
                'tag_name': tag.value,
                'student_count': tag.student_count,
                'percentage': percentage
            })
        
        result_data = {
            'top_tags': stats_data,
            'total_students_with_tags': total_students,
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 存入Redis缓存
        redis_client = get_redis_client()
        cache_key = f"dashboard:tag1_students:{date.today().strftime('%Y%m%d')}"
        redis_client.setex(cache_key, 86400, json.dumps(result_data))  # 24小时过期
        
        return f"Tag1学生标签统计更新成功，共{len(stats_data)}个标签"
        
    except Exception as exc:
        # 重试机制
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        raise exc


@shared_task(bind=True, max_retries=3)
def update_tag2_student_stats(self):
    """
    更新Tag2学生标签统计数据
    """
    try:
        # 统计每个Tag2标签关联的学生数量
        tag2_stats = Tag2.objects.annotate(
            student_count=Count('tag2stumatch__student', distinct=True)
        ).filter(
            student_count__gt=0
        ).order_by('-student_count')[:5]
        
        # 计算总学生数（有Tag2标签的学生）
        total_students = Tag2StuMatch.objects.values('student').distinct().count()
        
        # 构建返回数据
        stats_data = []
        for tag in tag2_stats:
            percentage = round((tag.student_count / total_students * 100), 2) if total_students > 0 else 0
            stats_data.append({
                'tag_id': tag.id,
                'tag_name': tag.post,
                'student_count': tag.student_count,
                'percentage': percentage
            })
        
        result_data = {
            'top_tags': stats_data,
            'total_students_with_tags': total_students,
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 存入Redis缓存
        redis_client = get_redis_client()
        cache_key = f"dashboard:tag2_students:{date.today().strftime('%Y%m%d')}"
        redis_client.setex(cache_key, 86400, json.dumps(result_data))  # 24小时过期
        
        return f"Tag2学生标签统计更新成功，共{len(stats_data)}个标签"
        
    except Exception as exc:
        # 重试机制
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        raise exc


@shared_task(bind=True, max_retries=3)
def update_project_status_stats(self):
    """
    更新项目状态统计数据
    """
    try:
        # 排除草稿状态，统计其他状态的项目数量
        project_stats = StudentProject.objects.exclude(
            status='draft'
        ).values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 获取状态选择项的显示名称
        status_choices = dict(StudentProject.STATUS_CHOICES)
        
        # 计算总项目数（排除草稿）
        total_projects = StudentProject.objects.exclude(status='draft').count()
        
        # 构建返回数据
        stats_data = []
        for stat in project_stats:
            status_code = stat['status']
            count = stat['count']
            percentage = round((count / total_projects * 100), 2) if total_projects > 0 else 0
            
            stats_data.append({
                'status_code': status_code,
                'status_name': status_choices.get(status_code, status_code),
                'project_count': count,
                'percentage': percentage
            })
        
        result_data = {
            'status_stats': stats_data,
            'total_projects': total_projects,
            'excluded_status': 'draft',
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 存入Redis缓存
        redis_client = get_redis_client()
        cache_key = f"dashboard:project_status:{date.today().strftime('%Y%m%d')}"
        redis_client.setex(cache_key, 86400, json.dumps(result_data))  # 24小时过期
        
        return f"项目状态统计更新成功，总项目数{total_projects}"
        
    except Exception as exc:
        # 重试机制
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        raise exc


@shared_task(bind=True, max_retries=3)
def update_organization_status_stats(self):
    """
    更新组织认证状态统计数据
    """
    try:
        # 统计各种认证状态的组织数量
        org_stats = Organization.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 获取状态选择项的显示名称
        status_choices = dict(Organization.STATUS_CHOICES)
        
        # 计算总组织数
        total_organizations = Organization.objects.count()
        
        # 构建返回数据
        stats_data = []
        for stat in org_stats:
            status_code = stat['status']
            count = stat['count']
            percentage = round((count / total_organizations * 100), 2) if total_organizations > 0 else 0
            
            stats_data.append({
                'status_code': status_code,
                'status_name': status_choices.get(status_code, status_code),
                'organization_count': count,
                'percentage': percentage
            })
        
        # 特别统计关键状态
        key_statuses = ['certified', 'under_review', 'pending', 'closed']
        key_stats = {}
        for status_code in key_statuses:
            count = Organization.objects.filter(status=status_code).count()
            key_stats[status_code] = {
                'count': count,
                'name': status_choices.get(status_code, status_code),
                'percentage': round((count / total_organizations * 100), 2) if total_organizations > 0 else 0
            }
        
        result_data = {
            'all_status_stats': stats_data,
            'key_status_stats': key_stats,
            'total_organizations': total_organizations,
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 存入Redis缓存
        redis_client = get_redis_client()
        cache_key = f"dashboard:org_status:{date.today().strftime('%Y%m%d')}"
        redis_client.setex(cache_key, 86400, json.dumps(result_data))  # 24小时过期
        
        return f"组织状态统计更新成功，总组织数{total_organizations}"
        
    except Exception as exc:
        # 重试机制
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        raise exc


@shared_task(bind=True, max_retries=3)
def update_project_tag1_stats(self):
    """
    更新项目Tag1标签统计数据
    """
    try:
        # 统计每个Tag1标签关联的项目数量（通过Requirement关联）
        tag1_stats = Tag1.objects.annotate(
            project_count=Count('requirement__student_projects', distinct=True)
        ).filter(
            project_count__gt=0
        ).order_by('-project_count')[:5]
        
        # 计算总项目数（有Tag1标签的项目）
        total_projects = StudentProject.objects.filter(
            requirement__tag1__isnull=False
        ).distinct().count()
        
        # 构建返回数据
        stats_data = []
        for tag in tag1_stats:
            percentage = round((tag.project_count / total_projects * 100), 2) if total_projects > 0 else 0
            stats_data.append({
                'tag_id': tag.id,
                'tag_name': tag.value,
                'project_count': tag.project_count,
                'percentage': percentage
            })
        
        result_data = {
            'top_tags': stats_data,
            'total_projects_with_tags': total_projects,
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 存入Redis缓存
        redis_client = get_redis_client()
        cache_key = f"dashboard:project_tag1:{date.today().strftime('%Y%m%d')}"
        redis_client.setex(cache_key, 86400, json.dumps(result_data))  # 24小时过期
        
        return f"项目Tag1标签统计更新成功，共{len(stats_data)}个标签"
        
    except Exception as exc:
        # 重试机制
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        raise exc


@shared_task(bind=True)
def update_all_dashboard_stats(self):
    """
    更新所有Dashboard统计数据的主任务
    """
    try:
        results = []
        
        # 执行所有统计任务
        tasks = [
            update_tag1_student_stats,
            update_tag2_student_stats,
            update_project_status_stats,
            update_organization_status_stats,
            update_project_tag1_stats
        ]
        
        for task in tasks:
            try:
                result = task.apply()
                results.append(f"{task.__name__}: {result.result}")
            except Exception as e:
                results.append(f"{task.__name__}: 失败 - {str(e)}")
        
        return f"Dashboard统计数据更新完成。结果: {'; '.join(results)}"
        
    except Exception as exc:
        return f"Dashboard统计数据更新失败: {str(exc)}"