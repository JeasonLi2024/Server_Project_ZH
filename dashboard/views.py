import redis
import time
import json
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from dateutil.relativedelta import relativedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from common_utils import APIResponse
from user.models import Tag1, Tag2, Tag1StuMatch, Tag2StuMatch, User
from organization.models import Organization
from studentproject.models import StudentProject
from project.models import Requirement


# Redis连接配置
def get_redis_client():
    """获取Redis客户端"""
    return redis.Redis(
        host=getattr(settings, 'REDIS_HOST', 'localhost'),
        port=getattr(settings, 'REDIS_PORT', 6379),
        db=getattr(settings, 'REDIS_DB', 0),
        decode_responses=True
    )


def get_cached_stats(stats_type):
    """从Redis获取缓存的统计数据"""
    try:
        redis_client = get_redis_client()
        cache_key = f"dashboard:{stats_type}:{date.today().strftime('%Y%m%d')}"
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            cache_obj = json.loads(cached_data)
            # 检查是否为新格式（包含cache_info）
            if isinstance(cache_obj, dict) and 'data' in cache_obj and 'cache_info' in cache_obj:
                return cache_obj
            else:
                # 兼容旧格式，直接返回数据
                return {'data': cache_obj, 'cache_info': None}
        return None
    except Exception:
        return None


def set_cached_stats(stats_type, data, expire_seconds=60):
    """将统计数据存入Redis缓存"""
    try:
        import datetime
        redis_client = get_redis_client()
        cache_key = f"dashboard:{stats_type}:{date.today().strftime('%Y%m%d')}"
        
        # 添加缓存元数据
        cache_data = {
            'data': data,
            'cache_info': {
                'created_at': datetime.datetime.now().isoformat(),
                'expires_at': (datetime.datetime.now() + datetime.timedelta(seconds=expire_seconds)).isoformat(),
                'expire_seconds': expire_seconds,
                'cache_key': cache_key
            }
        }
        
        redis_client.setex(cache_key, expire_seconds, json.dumps(cache_data))
        return True
    except Exception:
        return False


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_online_count(request):
    """
    获取实时在线人数统计
    
    Returns:
        JSON: 包含在线人数的响应
    """
    try:
        # 连接Redis
        redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0),
            decode_responses=True
        )
        
        # 获取在线用户数量
        online_users_key = 'online_users'
        online_count = redis_client.scard(online_users_key)
        
        return APIResponse.success(
            data={
                'online_count': online_count,
                'message': f'当前在线人数: {online_count}',
                'timestamp': int(time.time()),
                'cache_info': {
                    'is_cached': False,
                    'data_source': 'redis',
                    'query_time': time.time()
                }
            },
            message='操作成功'
        )
        
    except redis.ConnectionError:
        return APIResponse.server_error(
            message='Redis连接失败',
            code=503
        )
        
    except Exception as e:
        return APIResponse.server_error(
            message=f'获取在线人数失败: {str(e)}'
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_tag1_student_stats(request):
    """
    获取Tag1学生标签统计（关联学生数最多的前5个标签，用百分比表示）
    
    Returns:
        JSON: 包含Tag1标签统计数据的响应
    """
    try:
        # 尝试从缓存获取数据
        cached_result = get_cached_stats('tag1_students')
        if cached_result:
            # 构建返回数据，包含缓存信息
            response_data = cached_result['data'].copy()
            if cached_result['cache_info']:
                response_data['cache_info'] = cached_result['cache_info']
                response_data['cache_info']['is_cached'] = True
                response_data['cache_info']['data_source'] = 'cache'
            
            return APIResponse.success(
                data=response_data,
                message='获取Tag1学生标签统计成功（缓存）'
            )
        
        # 缓存未命中，执行数据库查询
        # 统计每个Tag1标签关联的学生数量
        tag1_stats = Tag1.objects.select_related().annotate(
            student_count=Count('tag1stumatch__student', distinct=True)
        ).filter(
            student_count__gt=0
        ).order_by('-student_count')[:5]
        
        # 计算总学生数（有Tag1标签的学生）
        total_students = Tag1StuMatch.objects.values('student').distinct().count()
        
        # 构建返回数据
        stats_data = []
        top5_total_count = 0
        for tag in tag1_stats:
            percentage = round((tag.student_count / total_students * 100), 2) if total_students > 0 else 0
            stats_data.append({
                'tag_id': tag.id,
                'tag_name': tag.value,
                'student_count': tag.student_count,
                'percentage': percentage
            })
            top5_total_count += tag.student_count
        
        # 计算其他标签的统计信息
        other_count = total_students - top5_total_count if total_students > top5_total_count else 0
        other_percentage = round((other_count / total_students * 100), 2) if total_students > 0 else 0
        
        result_data = {
            'top_tags': stats_data,
            'other': {
                'student_count': other_count,
                'percentage': other_percentage
            },
            'total_students_with_tags': total_students,
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 将结果存入缓存
        set_cached_stats('tag1_students', result_data)
        
        # 为实时查询的数据添加缓存信息标识
        result_data['cache_info'] = {
            'is_cached': False,
            'data_source': 'database',
            'query_time': time.time()
        }
        
        return APIResponse.success(
            data=result_data,
            message='获取Tag1学生标签统计成功'
        )
        
    except Exception as e:
        return APIResponse.server_error(
            message=f'获取Tag1学生标签统计失败: {str(e)}'
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_tag2_student_stats(request):
    """
    获取Tag2学生标签统计（关联学生数最多的前5个标签，用百分比表示）
    
    Returns:
        JSON: 包含Tag2标签统计数据的响应
    """
    try:
        # 尝试从缓存获取数据
        cached_result = get_cached_stats('tag2_students')
        if cached_result:
            # 构建返回数据，包含缓存信息
            response_data = cached_result['data'].copy()
            if cached_result['cache_info']:
                response_data['cache_info'] = cached_result['cache_info']
                response_data['cache_info']['is_cached'] = True
                response_data['cache_info']['data_source'] = 'cache'
            
            return APIResponse.success(
                data=response_data,
                message='获取Tag2学生标签统计成功（缓存）'
            )
        
        # 缓存未命中，执行数据库查询
        # 统计每个Tag2标签关联的学生数量
        tag2_stats = Tag2.objects.select_related().annotate(
            student_count=Count('tag2stumatch__student', distinct=True)
        ).filter(
            student_count__gt=0
        ).order_by('-student_count')[:5]
        
        # 计算总学生数（有Tag2标签的学生）
        total_students = Tag2StuMatch.objects.values('student').distinct().count()
        
        # 构建返回数据
        stats_data = []
        top5_total_count = 0
        for tag in tag2_stats:
            percentage = round((tag.student_count / total_students * 100), 2) if total_students > 0 else 0
            stats_data.append({
                'tag_id': tag.id,
                'tag_name': tag.post,
                'student_count': tag.student_count,
                'percentage': percentage
            })
            top5_total_count += tag.student_count
        
        # 计算其他标签的统计信息
        other_count = total_students - top5_total_count if total_students > top5_total_count else 0
        other_percentage = round((other_count / total_students * 100), 2) if total_students > 0 else 0
        
        result_data = {
            'top_tags': stats_data,
            'other': {
                'student_count': other_count,
                'percentage': other_percentage
            },
            'total_students_with_tags': total_students,
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 将结果存入缓存
        set_cached_stats('tag2_students', result_data)
        
        # 为实时查询的数据添加缓存信息标识
        result_data['cache_info'] = {
            'is_cached': False,
            'data_source': 'database',
            'query_time': time.time()
        }
        
        return APIResponse.success(
            data=result_data,
            message='获取Tag2学生标签统计成功'
        )
        
    except Exception as e:
        return APIResponse.server_error(
            message=f'获取Tag2学生标签统计失败: {str(e)}'
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_project_status_stats(request):
    """
    获取项目状态统计（排除草稿状态，按状态统计项目数）
    
    Returns:
        JSON: 包含项目状态统计数据的响应
    """
    try:
        # 尝试从缓存获取数据
        cached_result = get_cached_stats('project_status')
        if cached_result:
            # 构建返回数据，包含缓存信息
            response_data = cached_result['data'].copy()
            if cached_result['cache_info']:
                response_data['cache_info'] = cached_result['cache_info']
                response_data['cache_info']['is_cached'] = True
                response_data['cache_info']['data_source'] = 'cache'
            
            return APIResponse.success(
                data=response_data,
                message='获取项目状态统计成功（缓存）'
            )
        
        # 缓存未命中，执行数据库查询
        # 排除草稿状态，统计其他状态的项目数量
        project_stats = StudentProject.objects.select_related('requirement', 'requirement__organization').exclude(
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
        
        # 将结果存入缓存
        set_cached_stats('project_status', result_data)
        
        # 为实时查询的数据添加缓存信息标识
        result_data['cache_info'] = {
            'is_cached': False,
            'data_source': 'database',
            'query_time': time.time()
        }
        
        return APIResponse.success(
            data=result_data,
            message='获取项目状态统计成功'
        )
        
    except Exception as e:
        return APIResponse.server_error(
            message=f'获取项目状态统计失败: {str(e)}'
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_organization_status_stats(request):
    """
    获取组织认证状态统计（已认证、审核中、待认证、已关闭的组织数）
    
    Returns:
        JSON: 包含组织状态统计数据的响应
    """
    try:
        # 尝试从缓存获取数据
        cached_result = get_cached_stats('org_status')
        if cached_result:
            # 构建返回数据，包含缓存信息
            response_data = cached_result['data'].copy()
            if cached_result['cache_info']:
                response_data['cache_info'] = cached_result['cache_info']
                response_data['cache_info']['is_cached'] = True
                response_data['cache_info']['data_source'] = 'cache'
            
            return APIResponse.success(
                data=response_data,
                message='获取组织状态统计成功（缓存）'
            )
        
        # 缓存未命中，执行数据库查询
        # 获取状态选择项的显示名称
        status_choices = dict(Organization.STATUS_CHOICES)
        
        # 计算总组织数
        total_organizations = Organization.objects.count()
        
        # 统计5个预定义状态的组织数量
        predefined_statuses = ['pending', 'under_review', 'verified', 'rejected', 'closed']
        status_stats = []
        
        for status_code in predefined_statuses:
            count = Organization.objects.filter(status=status_code).count()
            percentage = round((count / total_organizations * 100), 2) if total_organizations > 0 else 0
            
            status_stats.append({
                'status_code': status_code,
                'status_name': status_choices.get(status_code, status_code),
                'organization_count': count,
                'percentage': percentage
            })
        
        result_data = {
            'status_stats': status_stats,
            'total_organizations': total_organizations,
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 将结果存入缓存
        set_cached_stats('org_status', result_data)
        
        # 为实时查询的数据添加缓存信息标识
        result_data['cache_info'] = {
            'is_cached': False,
            'data_source': 'database',
            'query_time': time.time()
        }
        
        return APIResponse.success(
            data=result_data,
            message='获取组织状态统计成功'
        )
        
    except Exception as e:
        return APIResponse.server_error(
            message=f'获取组织状态统计失败: {str(e)}'
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_project_tag1_stats(request):
    """
    获取项目Tag1标签统计（关联项目数最多的前5个tag1标签，用数量和百分比表示）
    
    Returns:
        JSON: 包含项目Tag1标签统计数据的响应
    """
    try:
        # 尝试从缓存获取数据
        cached_result = get_cached_stats('project_tag1')
        if cached_result:
            # 构建返回数据，包含缓存信息
            response_data = cached_result['data'].copy()
            if cached_result['cache_info']:
                response_data['cache_info'] = cached_result['cache_info']
                response_data['cache_info']['is_cached'] = True
                response_data['cache_info']['data_source'] = 'cache'
            
            return APIResponse.success(
                data=response_data,
                message='获取项目Tag1标签统计成功（缓存）'
            )
        
        # 缓存未命中，执行数据库查询
        # 统计每个Tag1标签关联的项目数量（通过Requirement关联）
        tag1_stats = Tag1.objects.select_related().prefetch_related('requirement_set__student_projects').annotate(
            project_count=Count('requirement__student_projects', distinct=True)
        ).filter(
            project_count__gt=0
        ).order_by('-project_count')[:5]
        
        # 计算总项目数（有Tag1标签的项目）
        total_projects = StudentProject.objects.select_related('requirement').filter(
            requirement__tag1__isnull=False
        ).distinct().count()
        
        # 构建返回数据
        stats_data = []
        top5_total_count = 0
        for tag in tag1_stats:
            percentage = round((tag.project_count / total_projects * 100), 2) if total_projects > 0 else 0
            stats_data.append({
                'tag_id': tag.id,
                'tag_name': tag.value,
                'project_count': tag.project_count,
                'percentage': percentage
            })
            top5_total_count += tag.project_count
        
        # 计算其他标签的统计信息
        other_count = total_projects - top5_total_count if total_projects > top5_total_count else 0
        other_percentage = round((other_count / total_projects * 100), 2) if total_projects > 0 else 0
        
        result_data = {
            'top_tags': stats_data,
            'other': {
                'project_count': other_count,
                'percentage': other_percentage
            },
            'total_projects_with_tags': total_projects,
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 将结果存入缓存
        set_cached_stats('project_tag1', result_data)
        
        # 为实时查询的数据添加缓存信息标识
        result_data['cache_info'] = {
            'is_cached': False,
            'data_source': 'database',
            'query_time': time.time()
        }
        
        return APIResponse.success(
            data=result_data,
            message='获取项目Tag1标签统计成功'
        )
        
    except Exception as e:
        return APIResponse.server_error(
            message=f'获取项目Tag1标签统计失败: {str(e)}'
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_user_registration_stats(request):
    """
    获取平台总注册人数随时间变化统计（前4个月，按月统计）
    
    Returns:
        JSON: 包含注册人数统计数据的响应
    """
    try:
        # 尝试从缓存获取数据
        cached_result = get_cached_stats('user_registration')
        if cached_result:
            # 构建返回数据，包含缓存信息
            response_data = cached_result['data'].copy()
            if cached_result['cache_info']:
                response_data['cache_info'] = cached_result['cache_info']
                response_data['cache_info']['is_cached'] = True
                response_data['cache_info']['data_source'] = 'cache'
            
            return APIResponse.success(
                data=response_data,
                message='获取注册人数统计成功（缓存）'
            )
        
        # 缓存未命中，执行数据库查询
        # 获取当前时间（使用Django时区设置）
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 计算前4个月的数据
        monthly_stats = []
        
        for i in range(3, -1, -1):  # 从3个月前到当前月
            # 计算目标月份的开始时间
            target_month = current_month_start - relativedelta(months=i)
            
            # 计算截止到该月末的累计注册人数
            if i == 0:  # 当前月，截止到现在
                end_time = now
            else:
                # 其他月份，截止到该月末
                next_month = target_month + relativedelta(months=1)
                end_time = next_month - timedelta(seconds=1)
            
            # 查询截止到该时间点的累计注册人数
            cumulative_count = User.objects.filter(
                date_joined__lte=end_time
            ).count()
            
            # 查询该月新增注册人数
            if i == 0:  # 当前月
                month_new_count = User.objects.filter(
                    date_joined__gte=target_month,
                    date_joined__lte=now
                ).count()
            else:
                next_month_start = target_month + relativedelta(months=1)
                month_new_count = User.objects.filter(
                    date_joined__gte=target_month,
                    date_joined__lt=next_month_start
                ).count()
            
            monthly_stats.append({
                'month': target_month.strftime('%Y-%m'),
                'month_display': target_month.strftime('%Y年%m月'),
                'cumulative_count': cumulative_count,
                'month_new_count': month_new_count,
                'is_current_month': i == 0
            })
        
        # 计算总注册人数
        total_users = User.objects.count()
        
        # 计算4个月内新增用户数
        three_months_ago = current_month_start - relativedelta(months=3)
        new_users_in_period = User.objects.filter(
            date_joined__gte=three_months_ago
        ).count()
        
        result_data = {
            'monthly_stats': monthly_stats,
            'summary': {
                'total_users': total_users,
                'new_users_in_4_months': new_users_in_period,
                'stats_period': f"{three_months_ago.strftime('%Y-%m')} 至 {current_month_start.strftime('%Y-%m')}",
                'current_time': now.strftime('%Y-%m-%d %H:%M:%S')
            },
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 将结果存入缓存（缓存1小时）
        set_cached_stats('user_registration', result_data, expire_seconds=60)
        
        # 为实时查询的数据添加缓存信息标识
        result_data['cache_info'] = {
            'is_cached': False,
            'data_source': 'database',
            'query_time': time.time()
        }
        
        return APIResponse.success(
            data=result_data,
            message='获取注册人数统计成功'
        )
        
    except Exception as e:
        return APIResponse.server_error(
            message=f'获取注册人数统计失败: {str(e)}'
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_student_tag_stats(request):
    """
    获取学生标签统计（Tag1和Tag2的综合统计）
    
    Returns:
        JSON: 包含学生标签统计数据的响应
    """
    try:
        # 尝试从缓存获取数据
        cached_result = get_cached_stats('student_tag_stats')
        if cached_result:
            # 构建返回数据，包含缓存信息
            response_data = cached_result['data'].copy()
            if cached_result['cache_info']:
                response_data['cache_info'] = cached_result['cache_info']
                response_data['cache_info']['is_cached'] = True
                response_data['cache_info']['data_source'] = 'cache'
            
            return APIResponse.success(
                data=response_data,
                message='获取学生标签统计成功（缓存）'
            )
        
        # 缓存未命中，执行数据库查询
        from user.models import Student
        
        # 统计有Tag1标签的学生数
        students_with_tag1 = Student.objects.filter(
            tag1stumatch__isnull=False
        ).distinct().count()
        
        # 统计有Tag2标签的学生数
        students_with_tag2 = Student.objects.filter(
            tag2stumatch__isnull=False
        ).distinct().count()
        
        # 统计同时有Tag1和Tag2标签的学生数
        students_with_both_tags = Student.objects.filter(
            tag1stumatch__isnull=False,
            tag2stumatch__isnull=False
        ).distinct().count()
        
        # 统计没有任何标签的学生数
        students_without_tags = Student.objects.filter(
            tag1stumatch__isnull=True,
            tag2stumatch__isnull=True
        ).count()
        
        # 统计总学生数
        total_students = Student.objects.count()
        
        # 计算百分比
        tag1_percentage = round((students_with_tag1 / total_students * 100), 2) if total_students > 0 else 0
        tag2_percentage = round((students_with_tag2 / total_students * 100), 2) if total_students > 0 else 0
        both_tags_percentage = round((students_with_both_tags / total_students * 100), 2) if total_students > 0 else 0
        no_tags_percentage = round((students_without_tags / total_students * 100), 2) if total_students > 0 else 0
        
        result_data = {
            'tag_statistics': {
                'students_with_tag1': {
                    'count': students_with_tag1,
                    'percentage': tag1_percentage
                },
                'students_with_tag2': {
                    'count': students_with_tag2,
                    'percentage': tag2_percentage
                },
                'students_with_both_tags': {
                    'count': students_with_both_tags,
                    'percentage': both_tags_percentage
                },
                'students_without_tags': {
                    'count': students_without_tags,
                    'percentage': no_tags_percentage
                }
            },
            'total_students': total_students,
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 将结果存入缓存
        set_cached_stats('student_tag_stats', result_data)
        
        # 为实时查询的数据添加缓存信息标识
        result_data['cache_info'] = {
            'is_cached': False,
            'data_source': 'database',
            'query_time': time.time()
        }
        
        return APIResponse.success(
            data=result_data,
            message='获取学生标签统计成功'
        )
        
    except Exception as e:
        return APIResponse.server_error(
            message=f'获取学生标签统计失败: {str(e)}'
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_project_completion_stats(request):
    """
    获取项目完成度统计（按项目状态分析完成情况）
    
    Returns:
        JSON: 包含项目完成度统计数据的响应
    """
    try:
        # 尝试从缓存获取数据
        cached_result = get_cached_stats('project_completion')
        if cached_result:
            # 构建返回数据，包含缓存信息
            response_data = cached_result['data'].copy()
            if cached_result['cache_info']:
                response_data['cache_info'] = cached_result['cache_info']
                response_data['cache_info']['is_cached'] = True
                response_data['cache_info']['data_source'] = 'cache'
            
            return APIResponse.success(
                data=response_data,
                message='获取项目完成度统计成功（缓存）'
            )
        
        # 缓存未命中，执行数据库查询
        # 定义完成度分类
        completed_statuses = ['completed', 'finished']  # 已完成状态
        in_progress_statuses = ['in_progress', 'ongoing', 'active']  # 进行中状态
        pending_statuses = ['pending', 'waiting', 'approved']  # 待开始状态
        cancelled_statuses = ['cancelled', 'terminated', 'rejected']  # 已取消状态
        
        # 统计各类状态的项目数
        completed_count = StudentProject.objects.filter(
            status__in=completed_statuses
        ).count()
        
        in_progress_count = StudentProject.objects.filter(
            status__in=in_progress_statuses
        ).count()
        
        pending_count = StudentProject.objects.filter(
            status__in=pending_statuses
        ).count()
        
        cancelled_count = StudentProject.objects.filter(
            status__in=cancelled_statuses
        ).count()
        
        # 统计其他状态的项目数（排除草稿）
        other_count = StudentProject.objects.exclude(
            Q(status__in=completed_statuses) |
            Q(status__in=in_progress_statuses) |
            Q(status__in=pending_statuses) |
            Q(status__in=cancelled_statuses) |
            Q(status='draft')
        ).count()
        
        # 计算总项目数（排除草稿）
        total_projects = StudentProject.objects.exclude(status='draft').count()
        
        # 计算百分比
        completed_percentage = round((completed_count / total_projects * 100), 2) if total_projects > 0 else 0
        in_progress_percentage = round((in_progress_count / total_projects * 100), 2) if total_projects > 0 else 0
        pending_percentage = round((pending_count / total_projects * 100), 2) if total_projects > 0 else 0
        cancelled_percentage = round((cancelled_count / total_projects * 100), 2) if total_projects > 0 else 0
        other_percentage = round((other_count / total_projects * 100), 2) if total_projects > 0 else 0
        
        # 计算完成率（已完成项目占总项目的比例）
        completion_rate = completed_percentage
        
        result_data = {
            'completion_stats': {
                'completed': {
                    'count': completed_count,
                    'percentage': completed_percentage,
                    'statuses': completed_statuses
                },
                'in_progress': {
                    'count': in_progress_count,
                    'percentage': in_progress_percentage,
                    'statuses': in_progress_statuses
                },
                'pending': {
                    'count': pending_count,
                    'percentage': pending_percentage,
                    'statuses': pending_statuses
                },
                'cancelled': {
                    'count': cancelled_count,
                    'percentage': cancelled_percentage,
                    'statuses': cancelled_statuses
                },
                'other': {
                    'count': other_count,
                    'percentage': other_percentage
                }
            },
            'summary': {
                'total_projects': total_projects,
                'completion_rate': completion_rate,
                'active_projects': completed_count + in_progress_count + pending_count
            },
            'excluded_status': 'draft',
            'stats_date': date.today().strftime('%Y-%m-%d')
        }
        
        # 将结果存入缓存
        set_cached_stats('project_completion', result_data)
        
        # 为实时查询的数据添加缓存信息标识
        result_data['cache_info'] = {
            'is_cached': False,
            'data_source': 'database',
            'query_time': time.time()
        }
        
        return APIResponse.success(
            data=result_data,
            message='获取项目完成度统计成功'
        )
        
    except Exception as e:
        return APIResponse.server_error(
             message=f'获取项目完成度统计失败: {str(e)}'
         )


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_qianduan_answer_number(request):
    """
    获取QianDuan_data表中的answer_number
    
    Returns:
        JSON: 包含answer_number数据的响应
    """
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT answer_number FROM QianDuan_data")
            results = cursor.fetchall()
            
        # 提取单个answer_number值（表只有1行，取第1行第1列）
        answer_number = results[0][0] if results else 0  # 表为空时默认返回0
        
        result_data = {
            'answer_number': answer_number,
            'query_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return APIResponse.success(
            data=result_data,
            message='获取answer_number数据成功'
        )
        
    except Exception as e:
        return APIResponse.server_error(
            message=f'获取answer_number数据失败: {str(e)}'
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_top_tags_by_frequency(request):
    """
    返回tag1中根据frequency由高到低给出前15个标签值
    
    Returns:
        JSON: 包含前15个标签的tag_id、value和frequency
    """
    try:
        # 查询Tag1表，按frequency降序排列，取前15个
        # 注意：frequency字段是CharField，需要转换为数值进行排序
        from django.db.models import Case, When, IntegerField
        from django.db.models.functions import Cast
        
        top_tags = Tag1.objects.exclude(
            frequency__isnull=True
        ).exclude(
            frequency=''
        ).annotate(
            frequency_int=Cast('frequency', IntegerField())
        ).order_by('-frequency_int')[:15]
        
        # 构建返回数据
        tags_data = []
        for tag in top_tags:
            tags_data.append({
                'tag_id': tag.id,
                'value': tag.value,
                'frequency': tag.frequency
            })
        
        result_data = {
            'top_tags': tags_data,
            'total_returned': len(tags_data),
            'query_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return APIResponse.success(
            data=result_data,
            message='获取前15个高频标签成功'
        )
        
    except Exception as e:
        return APIResponse.server_error(
            message=f'获取高频标签失败: {str(e)}'
        )
