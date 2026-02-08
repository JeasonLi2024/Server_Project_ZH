"""统一响应格式工具"""
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings


class APIResponse:
    """统一API响应格式"""
    
    @staticmethod
    def success(data=None, message="操作成功", code=200):
        """成功响应"""
        return Response({
            "status": "success",
            "code": code,
            "message": message,
            "data": data or {},
            "error": {}
        }, status=code)
    
    @staticmethod
    def error(message="操作失败", code=400, errors=None):
        """错误响应"""
        return Response({
            "status": "error",
            "code": code,
            "message": message,
            "data": {},
            "error": errors or {}
        }, status=code)
    
    @staticmethod
    def validation_error(errors, message="验证失败", code=422):
        """验证错误响应"""
        return Response({
            "status": "error",
            "code": code,
            "message": message,
            "data": {},
            "error": errors
        }, status=code)
    
    @staticmethod
    def unauthorized(message="未授权", code=401):
        """未授权响应"""
        return Response({
            "status": "error",
            "code": code,
            "message": message,
            "data": {},
            "error": {}
        }, status=code)
    
    @staticmethod
    def forbidden(message="禁止访问", code=403):
        """禁止访问响应"""
        return Response({
            "status": "error",
            "code": code,
            "message": message,
            "data": {},
            "error": {}
        }, status=code)
    
    @staticmethod
    def not_found(message="资源不存在", code=404):
        """资源不存在响应"""
        return Response({
            "status": "error",
            "code": code,
            "message": message,
            "data": {},
            "error": {}
        }, status=code)
    
    @staticmethod
    def too_many_requests(message="请求过于频繁", code=429):
        """请求过于频繁响应"""
        return Response({
            "status": "error",
            "code": code,
            "message": message,
            "data": {},
            "error": {}
        }, status=code)
    
    @staticmethod
    def server_error(message="服务器内部错误", code=500, errors=None):
        """服务器错误响应"""
        return Response({
            "status": "error",
            "code": code,
            "message": message,
            "data": {},
            "error": errors or {}
        }, status=code)


def format_validation_errors(serializer_errors):
    """格式化序列化器验证错误"""
    formatted_errors = {}
    for field, errors in serializer_errors.items():
        if isinstance(errors, list):
            formatted_errors[field] = errors
        else:
            formatted_errors[field] = [str(errors)]
    return formatted_errors


def build_media_url(file_path_or_field, request=None, default_url=None):
    """
    通用媒体文件URL构建函数
    
    Args:
        file_path_or_field: 文件路径字符串、Django FileField对象或None
        request: Django request对象，用于构建绝对URL（可选）
        default_url: 当文件不存在时的默认URL（可选）
    
    Returns:
        str: 完整的媒体文件URL或None
    """
    def apply_prefix(url: str) -> str:
        prefix = getattr(settings, 'PROXY_PATH_PREFIX', '') or ''
        if not url:
            return url
        if url.startswith(('http://', 'https://')):
            return url
        if prefix:
            clean_prefix = prefix.rstrip('/')
            clean_url = url.lstrip('/')
            # 避免重复前缀
            if clean_url.startswith(clean_prefix.lstrip('/')):
                return f"/{clean_url}"
            return f"{clean_prefix}/{clean_url}"
        return url

    def finalize_url(url):
        if not url:
            return url
            
        # 先应用路径前缀
        url_with_prefix = apply_prefix(url)
        
        # 如果已经是完整URL，直接返回（除了HTTPS强制）
        if url_with_prefix.startswith(('http://', 'https://')):
            final_url = url_with_prefix
        else:
            # 应用域名配置
            media_host = getattr(settings, 'MEDIA_HOST', '')
            if media_host:
                clean_host = media_host.rstrip('/')
                clean_url = url_with_prefix.lstrip('/')
                final_url = f"{clean_host}/{clean_url}"
            elif request:
                final_url = request.build_absolute_uri(url_with_prefix)
            else:
                final_url = url_with_prefix
            
        # 强制HTTPS
        if getattr(settings, 'MEDIA_FORCE_HTTPS', False) and final_url.startswith('http://'):
            final_url = 'https://' + final_url[len('http://'):]
        return final_url

    # 处理None值
    if not file_path_or_field:
        if default_url:
            return finalize_url(default_url)
        return None
    
    # 处理Django FileField对象
    if hasattr(file_path_or_field, 'url'):
        try:
            return finalize_url(file_path_or_field.url)
        except ValueError:
            if default_url:
                return finalize_url(default_url)
            return None
    
    # 处理字符串路径
    if isinstance(file_path_or_field, str):
        if file_path_or_field.startswith(('http://', 'https://')):
            return file_path_or_field
        
        # 构建完整URL
        if not file_path_or_field.startswith('/'):
            file_url = f"{settings.MEDIA_URL.rstrip('/')}/{file_path_or_field.lstrip('/')}"
        else:
            file_url = file_path_or_field
        
        return finalize_url(file_url)
    
    # 其他情况返回默认值
    if default_url:
        return finalize_url(default_url)
    return None


def build_media_urls_list(file_paths, request=None):
    """
    构建媒体文件URL列表（用于处理JSON字段存储的文件路径列表）
    
    Args:
        file_paths: 文件路径列表
        request: Django request对象，用于构建绝对URL（可选）
    
    Returns:
        list: 完整的媒体文件URL列表
    """
    if not file_paths:
        return []
    
    urls = []
    for file_path in file_paths:
        url = build_media_url(file_path, request)
        if url:
            urls.append(url)
    return urls


# ==================== 通用分页工具 ====================

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import QuerySet
from typing import Dict, Any, Optional, Union


class CustomPaginator:
    """自定义分页器"""
    
    DEFAULT_PAGE_SIZE = 20  # 默认每页显示数量
    MAX_PAGE_SIZE = 100     # 最大每页显示数量
    
    def __init__(self, queryset: QuerySet, page: int = 1, page_size: Optional[int] = None):
        """
        初始化分页器
        
        Args:
            queryset: Django QuerySet对象
            page: 页码，默认为1
            page_size: 每页显示数量，默认使用DEFAULT_PAGE_SIZE
        """
        self.queryset = queryset
        self.page = max(1, page)  # 确保页码至少为1
        self.page_size = self._validate_page_size(page_size)
        self.paginator = Paginator(queryset, self.page_size)
        self.page_obj = None
        self._paginate()
    
    def _validate_page_size(self, page_size: Optional[int]) -> int:
        """验证并返回有效的页面大小"""
        if page_size is None:
            return self.DEFAULT_PAGE_SIZE
        
        # 确保页面大小在合理范围内
        return max(1, min(page_size, self.MAX_PAGE_SIZE))
    
    def _paginate(self):
        """执行分页操作"""
        try:
            self.page_obj = self.paginator.page(self.page)
        except PageNotAnInteger:
            # 如果页码不是整数，返回第一页
            self.page_obj = self.paginator.page(1)
            self.page = 1
        except EmptyPage:
            # 如果页码超出范围，返回最后一页
            self.page_obj = self.paginator.page(self.paginator.num_pages)
            self.page = self.paginator.num_pages
    
    def get_page_data(self) -> QuerySet:
        """获取当前页的数据"""
        return self.page_obj.object_list if self.page_obj else self.queryset.none()
    
    def get_pagination_info(self, request=None) -> Dict[str, Any]:
        """获取分页信息"""
        if not self.page_obj:
            return {
                'current_page': 1,
                'total_pages': 0,
                'total_count': 0,
                'page_size': self.page_size,
                'previous_url': None,
                'next_url': None
            }
        
        # 构建上/下页URL
        previous_url = None
        next_url = None
        
        if request:
            base_url = request.build_absolute_uri().split('?')[0]
            query_params = request.GET.copy()
            
            if self.page_obj.has_previous():
                query_params['page'] = self.page_obj.previous_page_number()
                previous_url = f"{base_url}?{query_params.urlencode()}"
            
            if self.page_obj.has_next():
                query_params['page'] = self.page_obj.next_page_number()
                next_url = f"{base_url}?{query_params.urlencode()}"
        
        return {
            'current_page': self.page_obj.number,
            'total_pages': self.paginator.num_pages,
            'total_count': self.paginator.count,
            'page_size': self.page_size,
            'previous_url': previous_url,
            'next_url': next_url
        }
    
    def get_paginated_response_data(self, results: list, request=None) -> Dict[str, Any]:
        """
        获取完整的分页响应数据
        
        Args:
            results: 序列化后的结果列表
            request: Django请求对象，用于生成URL
            
        Returns:
            包含结果和分页信息的字典
        """
        pagination_info = self.get_pagination_info(request)
        
        return {
            'results': results,
            'pagination': pagination_info
        }


def paginate_queryset(request, queryset: QuerySet, default_page_size: int = None) -> Dict[str, Any]:
    """
    便捷函数：从请求中提取分页参数并返回分页响应数据
    
    Args:
        request: Django请求对象
        queryset: Django QuerySet对象
        default_page_size: 默认每页大小，如果不提供则使用CustomPaginator.DEFAULT_PAGE_SIZE
        
    Returns:
        包含分页数据的字典，需要配合序列化器使用
    """
    # 从请求参数中获取页码和每页大小
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    
    try:
        page_size = int(request.GET.get('page_size', default_page_size or CustomPaginator.DEFAULT_PAGE_SIZE))
    except (ValueError, TypeError):
        page_size = default_page_size or CustomPaginator.DEFAULT_PAGE_SIZE
    
    paginator = CustomPaginator(queryset, page, page_size)
    
    return {
        'paginator': paginator,
        'page_data': paginator.get_page_data(),
        'pagination_info': paginator.get_pagination_info(request)
    }


def get_page_range(current_page: int, total_pages: int, max_display: int = 5) -> list:
    """
    获取页码范围，用于前端显示页码导航
    
    Args:
        current_page: 当前页码
        total_pages: 总页数
        max_display: 最多显示的页码数量
        
    Returns:
        页码列表
    """
    if total_pages <= max_display:
        return list(range(1, total_pages + 1))
    
    # 计算显示范围
    half_display = max_display // 2
    
    if current_page <= half_display:
        # 当前页在前半部分
        return list(range(1, max_display + 1))
    elif current_page > total_pages - half_display:
        # 当前页在后半部分
        return list(range(total_pages - max_display + 1, total_pages + 1))
    else:
        # 当前页在中间
        return list(range(current_page - half_display, current_page + half_display + 1))