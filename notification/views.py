from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

import logging

from .models import (
    Notification,
    NotificationType,
    NotificationTemplate,
    NotificationPreference,
    NotificationLog
)
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    NotificationUpdateSerializer,
    NotificationTypeSerializer,
    NotificationTemplateSerializer,
    NotificationPreferenceSerializer,
    NotificationLogSerializer,
    NotificationStatsSerializer,
    BulkNotificationSerializer
)
from .services import notification_service, org_notification_service
from .filters import NotificationFilter
from common_utils import CustomPaginator, APIResponse

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.ModelViewSet):
    """通知视图集"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = NotificationFilter
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """获取当前用户的通知"""
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related(
            'notification_type', 'sender', 'content_type'
        ).prefetch_related('logs')
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'create':
            return NotificationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NotificationUpdateSerializer
        return NotificationSerializer
    
    def list(self, request, *args, **kwargs):
        """获取通知列表（带分页）"""
        try:
            # 获取过滤后的查询集
            queryset = self.filter_queryset(self.get_queryset())
            
            # 获取分页参数
            try:
                page = int(request.GET.get('page', 1))
            except (ValueError, TypeError):
                page = 1
            
            try:
                page_size = int(request.GET.get('page_size', 20))
            except (ValueError, TypeError):
                page_size = 20
            
            # 使用自定义分页器
            paginator = CustomPaginator(queryset, page, page_size)
            page_data = paginator.get_page_data()
            
            # 序列化数据
            serializer = self.get_serializer(page_data, many=True)
            
            # 构建响应数据
            response_data = paginator.get_paginated_response_data(
                serializer.data, 
                request
            )
            
            return APIResponse.success(
                data=response_data,
                message="获取通知列表成功"
            )
            
        except Exception as e:
            logger.error(f"获取通知列表失败: {str(e)}")
            return APIResponse.server_error(
                message="获取通知列表失败",
                errors={"detail": str(e)}
            )
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """标记通知为已读"""
        try:
            notification = self.get_object()
            notification.mark_as_read()
            
            serializer = self.get_serializer(notification)
            return APIResponse.success(
                data=serializer.data,
                message="通知已标记为已读"
            )
        except Exception as e:
            logger.error(f"标记通知为已读失败: {str(e)}")
            return APIResponse.server_error(
                message="标记通知为已读失败",
                errors={"detail": str(e)}
            )
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """获取未读通知数量"""
        try:
            count = self.get_queryset().filter(is_read=False).count()
            return APIResponse.success(
                data={'unread_count': count},
                message="获取未读通知数量成功"
            )
        except Exception as e:
            logger.error(f"获取未读通知数量失败: {str(e)}")
            return APIResponse.server_error(
                message="获取未读通知数量失败",
                errors={"detail": str(e)}
            )
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """标记所有通知为已读"""
        try:
            updated_count = self.get_queryset().filter(is_read=False).update(
                is_read=True,
                read_at=timezone.now()
            )
            return APIResponse.success(
                data={'updated_count': updated_count},
                message=f"已标记 {updated_count} 条通知为已读"
            )
        except Exception as e:
            logger.error(f"标记所有通知为已读失败: {str(e)}")
            return APIResponse.server_error(
                message="标记所有通知为已读失败",
                errors={"detail": str(e)}
            )


class NotificationPreferenceViewSet(viewsets.GenericViewSet):
    """通知偏好设置视图集"""
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """获取或创建当前用户的通知偏好设置"""
        preference, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        
        # 如果是新创建的偏好设置，初始化所有通知类型的默认偏好
        if created or not preference.type_preferences:
            # 获取所有激活的通知类型
            active_types = NotificationType.objects.filter(is_active=True)
            
            # 初始化所有通知类型为启用状态（默认值为True）
            type_preferences = {}
            for notification_type in active_types:
                type_preferences[notification_type.code] = True
            
            # 更新偏好设置
            preference.type_preferences = type_preferences
            preference.save()
        
        return preference
    
    @action(detail=False, methods=['get'])
    def get_preferences(self, request):
        """获取用户通知偏好设置"""
        try:
            preference = self.get_object()
            serializer = self.get_serializer(preference)
            return APIResponse.success(
                data=serializer.data,
                message="获取通知偏好设置成功"
            )
        except Exception as e:
            logger.error(f"获取通知偏好设置失败: {str(e)}")
            return APIResponse.server_error(
                message="获取通知偏好设置失败",
                errors={"detail": str(e)}
            )
    
    @action(detail=False, methods=['patch'])
    def update_preferences(self, request):
        """更新用户通知偏好设置"""
        try:
            preference = self.get_object()
            
            # 处理type_preferences的合并逻辑
            data = request.data.copy()
            if 'type_preferences' in data:
                # 合并现有的type_preferences和新的设置
                current_type_preferences = preference.type_preferences.copy()
                new_type_preferences = data['type_preferences']
                current_type_preferences.update(new_type_preferences)
                data['type_preferences'] = current_type_preferences
            
            serializer = self.get_serializer(
                preference, 
                data=data, 
                partial=True
            )
            
            if serializer.is_valid():
                serializer.save()
                return APIResponse.success(
                    data=serializer.data,
                    message="通知偏好设置更新成功"
                )
            else:
                return APIResponse.validation_error(
                    message="数据验证失败",
                    errors=serializer.errors
                )
        except Exception as e:
            logger.error(f"更新通知偏好设置失败: {str(e)}")
            return APIResponse.server_error(
                message="更新通知偏好设置失败",
                errors={"detail": str(e)}
            )
    
    @action(detail=False, methods=['post'])
    def reset_to_default(self, request):
        """重置为默认设置"""
        try:
            preference = self.get_object()
            
            # 重置为默认值
            preference.enable_websocket = True
            preference.enable_email = False
            preference.enable_sms = False
            preference.type_preferences = {}
            preference.quiet_start_time = None
            preference.quiet_end_time = None
            preference.do_not_disturb = False
            preference.save()
            
            serializer = self.get_serializer(preference)
            return APIResponse.success(
                data=serializer.data,
                message="通知偏好设置已重置为默认值"
            )
        except Exception as e:
            logger.error(f"重置通知偏好设置失败: {str(e)}")
            return APIResponse.server_error(
                message="重置通知偏好设置失败",
                errors={"detail": str(e)}
            )
    
    @action(detail=False, methods=['get'])
    def get_notification_types(self, request):
        """获取所有可用的通知类型（带分页）"""
        try:
            # 获取查询集
            queryset = NotificationType.objects.filter(
                is_active=True
            ).order_by('category', 'name')
            
            # 获取分页参数
            try:
                page = int(request.GET.get('page', 1))
            except (ValueError, TypeError):
                page = 1
            
            try:
                page_size = int(request.GET.get('page_size', 20))
            except (ValueError, TypeError):
                page_size = 20
            
            # 使用自定义分页器
            paginator = CustomPaginator(queryset, page, page_size)
            page_data = paginator.get_page_data()
            
            # 序列化数据
            serializer = NotificationTypeSerializer(page_data, many=True)
            
            # 构建响应数据
            response_data = paginator.get_paginated_response_data(
                serializer.data, 
                request
            )
            
            return APIResponse.success(
                data=response_data,
                message="获取通知类型列表成功"
            )
        except Exception as e:
            logger.error(f"获取通知类型列表失败: {str(e)}")
            return APIResponse.server_error(
                message="获取通知类型列表失败",
                errors={"detail": str(e)}
            )


class NotificationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """通知类型视图集"""
    serializer_class = NotificationTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """获取所有激活的通知类型"""
        return NotificationType.objects.filter(
            is_active=True
        ).order_by('category', 'name')
    
    def list(self, request, *args, **kwargs):
        """获取通知类型列表（带分页）"""
        try:
            # 获取过滤后的查询集
            queryset = self.get_queryset()
            
            # 获取分页参数
            try:
                page = int(request.GET.get('page', 1))
            except (ValueError, TypeError):
                page = 1
            
            try:
                page_size = int(request.GET.get('page_size', 20))
            except (ValueError, TypeError):
                page_size = 20
            
            # 使用自定义分页器
            paginator = CustomPaginator(queryset, page, page_size)
            page_data = paginator.get_page_data()
            
            # 序列化数据
            serializer = self.get_serializer(page_data, many=True)
            
            # 构建响应数据
            response_data = paginator.get_paginated_response_data(
                serializer.data, 
                request
            )
            
            return APIResponse.success(
                data=response_data,
                message="获取通知类型列表成功"
            )
        except Exception as e:
            logger.error(f"获取通知类型列表失败: {str(e)}")
            return APIResponse.server_error(
                message="获取通知类型列表失败",
                errors={"detail": str(e)}
            )


class OrganizationNotificationViewSet(viewsets.GenericViewSet):
    """企业端组织用户通知视图集"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def send_registration_audit(self, request):
        """发送用户注册审核通知"""
        admin_id = request.data.get('admin_id')
        applicant_id = request.data.get('applicant_id')
        organization_name = request.data.get('organization_name')
        
        if not all([admin_id, applicant_id, organization_name]):
            return Response(
                {'error': '缺少必要参数'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            admin = User.objects.get(id=admin_id)
            applicant = User.objects.get(id=applicant_id)
            
            notification = org_notification_service.send_user_registration_audit_notification(
                organization_admin=admin,
                applicant=applicant,
                organization_name=organization_name
            )
            
            if notification:
                serializer = NotificationSerializer(notification)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'error': '发送通知失败'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except User.DoesNotExist:
            return Response(
                {'error': '用户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"发送注册审核通知失败: {str(e)}")
            return Response(
                {'error': '发送通知失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
