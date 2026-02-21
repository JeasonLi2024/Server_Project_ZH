from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout as django_logout
from django.utils import timezone
import logging

from .models import User, Tag1, Tag2
from .serializers import UserProfileSerializer, UserUpdateSerializer, AvatarUploadSerializer, Tag1Serializer, Tag2Serializer
from .services import UserHistoryService
from common_utils import APIResponse, format_validation_errors, build_media_url, paginate_queryset
from project.serializers import RequirementSerializer

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """获取用户资料"""
    try:
        # 使用select_related优化查询
        user = User.objects.select_related(
            'student_profile',
            'organization_profile__organization'
        ).get(id=request.user.id)
        
        serializer = UserProfileSerializer(user, context={'request': request})
        
        return APIResponse.success(serializer.data)
        
    except User.DoesNotExist:
        return APIResponse.not_found('用户不存在')
    except Exception as e:
        logger.error(f"获取用户资料失败: {str(e)}")
        return APIResponse.server_error('获取用户资料失败，请稍后重试')


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """更新用户资料"""
    try:
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return APIResponse.validation_error(
                format_validation_errors(serializer.errors)
            )
        
        # 保存更新
        updated_user = serializer.save()
        
        # 重新获取用户数据，使用select_related优化查询
        updated_user = User.objects.select_related(
            'student_profile',
            'organization_profile__organization'
        ).get(id=updated_user.id)
        
        # 使用UserProfileSerializer返回完整的用户资料格式
        profile_serializer = UserProfileSerializer(updated_user, context={'request': request})
        
        return APIResponse.success(profile_serializer.data, '资料更新成功')
        
    except Exception as e:
        logger.error(f"更新用户资料失败: {str(e)}")
        return APIResponse.server_error('更新用户资料失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_view_history(request):
    """
    获取用户的浏览历史
    
    Query Params:
    - page: 页码 (默认1)
    - page_size: 每页数量 (默认20)
    - type: 浏览类型 (requirement/project, 默认 requirement)
    """
    try:
        user_id = request.user.id
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        item_type = request.GET.get('type', 'requirement')
        
        # 1. 从 Redis 获取历史 ID 列表
        page = max(1, page)
        item_ids, total_count = UserHistoryService.get_history(user_id, item_type, page, page_size)
        
        if not item_ids:
            return APIResponse.success({
                'results': [],
                'pagination': {
                    'current_page': page,
                    'total_pages': 0,
                    'total_count': 0,
                    'page_size': page_size,
                    'previous_url': None,
                    'next_url': None
                }
            })
            
        # 2. 根据 ID 回查详情
        if item_type == 'requirement':
            from project.models import Requirement
            # 保持顺序：Redis 返回的是按时间倒序的，MySQL filter(id__in) 不保证顺序
            # 必须手动重排
            objects = Requirement.objects.filter(id__in=item_ids).select_related(
                'organization', 'publish_people__user'
            ).prefetch_related(
                'tag1', 'tag2'
            )
            
            # 构建 ID -> Object 映射
            obj_map = {obj.id: obj for obj in objects}
            
            # 按 Redis 顺序重组
            sorted_objects = []
            for iid in item_ids:
                if iid in obj_map:
                    sorted_objects.append(obj_map[iid])
            
            # 序列化
            serializer = RequirementSerializer(sorted_objects, many=True, context={'request': request})
            data = serializer.data
            
        else:
            # 获取项目类型的浏览历史
            from studentproject.models import StudentProject
            from studentproject.serializers import StudentProjectListSerializer
            
            # 保持顺序：Redis 返回的是按时间倒序的，MySQL filter(id__in) 不保证顺序
            objects = StudentProject.objects.filter(id__in=item_ids).select_related(
                'requirement', 'requirement__organization'
            )
            
            # 构建 ID -> Object 映射
            obj_map = {obj.id: obj for obj in objects}
            
            # 按 Redis 顺序重组
            sorted_objects = []
            for iid in item_ids:
                if iid in obj_map:
                    sorted_objects.append(obj_map[iid])
            
            # 序列化
            serializer = StudentProjectListSerializer(sorted_objects, many=True, context={'request': request})
            data = serializer.data
            
        # 构建分页信息
        total_pages = (total_count + page_size - 1) // page_size
        
        previous_url = None
        next_url = None
        
        base_url = request.build_absolute_uri().split('?')[0]
        query_params = request.GET.copy()
        
        if page > 1:
            query_params['page'] = page - 1
            previous_url = f"{base_url}?{query_params.urlencode()}"
            
        if page < total_pages:
            query_params['page'] = page + 1
            next_url = f"{base_url}?{query_params.urlencode()}"

        return APIResponse.success({
            'results': data,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_count': total_count,
                'page_size': page_size,
                'previous_url': previous_url,
                'next_url': next_url
            }
        })
        
    except Exception as e:
        logger.error(f"获取浏览历史失败: {str(e)}")
        return APIResponse.server_error('获取浏览历史失败，请稍后重试')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_avatar(request):
    """上传用户头像"""
    user = request.user
    
    # 检查是否有文件上传
    if 'avatar' not in request.FILES:
        return APIResponse.error('请选择要上传的头像文件', code=400)
    
    # 使用序列化器验证和处理文件
    serializer = AvatarUploadSerializer(user, data=request.data, partial=True)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    try:
        # 保存头像
        updated_user = serializer.save()
        
        # 构建头像URL
        return APIResponse.success({
            'avatar': build_media_url(updated_user.avatar, request),
            'message': '头像上传成功'
        }, '头像上传成功')
        
    except Exception as e:
        logger.error(f"头像上传失败: {str(e)}")
        return APIResponse.error('头像上传失败，请稍后重试', code=500)


# 标签管理相关视图
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_interest_tags(request):
    """获取所有兴趣标签（支持搜索和分页）"""
    try:
        tags = Tag1.objects.all()
        
        # 支持搜索功能
        search = request.GET.get('search', '').strip()
        if search:
            tags = tags.filter(value__icontains=search)
        
        tags = tags.order_by('value')
        
        # 使用通用分页工具
        # from common_utils import paginate_queryset
        # pagination_result = paginate_queryset(request, tags, default_page_size=20)
        # page_data = pagination_result['page_data']
        # pagination_info = pagination_result['pagination_info']
        
        serializer = Tag1Serializer(tags, many=True)
        return APIResponse.success(serializer.data)
    except Exception as e:
        logger.error(f"获取兴趣标签失败: {str(e)}")
        return APIResponse.server_error('获取兴趣标签失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ability_tags(request):
    """获取所有level=2的能力标签，支持搜索"""
    try:
        # 获取搜索参数
        search = request.GET.get('search', '').strip()
        
        # 基础查询：只返回level=2的标签
        tags = Tag2.objects.filter(level=2)
        
        # 如果有搜索关键词，在category、subcategory、specialty字段中搜索
        if search:
            from django.db.models import Q
            tags = tags.filter(
                Q(category__icontains=search) |
                Q(subcategory__icontains=search) |
                Q(specialty__icontains=search)
            )
        
        # 排序
        tags = tags.order_by('category', 'subcategory', 'specialty')
        
        serializer = Tag2Serializer(tags, many=True)
        return APIResponse.success(serializer.data)
    except Exception as e:
        logger.error(f"获取能力标签失败: {str(e)}")
        return APIResponse.server_error('获取能力标签失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_tags(request):
    """模糊搜索tag1和tag2标签"""
    try:
        # 获取搜索参数
        search = request.GET.get('search', '').strip()
        
        if not search:
            return APIResponse.error('请提供搜索关键词', code=400)
        
        # 搜索tag1（兴趣标签）
        tag1_results = Tag1.objects.filter(value__icontains=search).order_by('value')
        tag1_serializer = Tag1Serializer(tag1_results, many=True)
        
        # 搜索tag2（能力标签）- 在category、subcategory、specialty字段中搜索，只返回level=2的标签
        from django.db.models import Q
        tag2_results = Tag2.objects.filter(
            Q(category__icontains=search) |
            Q(subcategory__icontains=search) |
            Q(specialty__icontains=search)
        ).filter(level=2).order_by('category', 'subcategory', 'specialty')
        tag2_serializer = Tag2Serializer(tag2_results, many=True)
        
        # 组合结果
        result_data = {
            'tag1': tag1_serializer.data,
            'tag2': tag2_serializer.data,
            'total_count': {
                'tag1_count': tag1_results.count(),
                'tag2_count': tag2_results.count(),
                'total': tag1_results.count() + tag2_results.count()
            }
        }
        
        return APIResponse.success(result_data)
    except Exception as e:
        logger.error(f"搜索标签失败: {str(e)}")
        return APIResponse.server_error('搜索标签失败，请稍后重试')
