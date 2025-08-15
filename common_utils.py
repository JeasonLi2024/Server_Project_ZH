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
    # 处理None值
    if not file_path_or_field:
        if default_url:
            if request:
                return request.build_absolute_uri(default_url)
            return default_url
        return None
    
    # 处理Django FileField对象
    if hasattr(file_path_or_field, 'url'):
        try:
            file_url = file_path_or_field.url
            if request:
                return request.build_absolute_uri(file_url)
            return file_url
        except ValueError:
            # FileField没有文件时会抛出ValueError
            if default_url:
                if request:
                    return request.build_absolute_uri(default_url)
                return default_url
            return None
    
    # 处理字符串路径
    if isinstance(file_path_or_field, str):
        # 如果已经是完整URL，直接返回
        if file_path_or_field.startswith(('http://', 'https://')):
            return file_path_or_field
        
        # 构建完整URL
        if not file_path_or_field.startswith('/'):
            file_url = f"{settings.MEDIA_URL.rstrip('/')}/{file_path_or_field.lstrip('/')}"
        else:
            file_url = file_path_or_field
        
        if request:
            return request.build_absolute_uri(file_url)
        return file_url
    
    # 其他情况返回默认值
    if default_url:
        if request:
            return request.build_absolute_uri(default_url)
        return default_url
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