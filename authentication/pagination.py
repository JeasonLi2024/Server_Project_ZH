"""
通用分页工具
提供可复用的分页功能，支持自定义每页数量和默认值
"""

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