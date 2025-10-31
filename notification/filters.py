import django_filters
from django.db.models import Q
from .models import Notification, NotificationType


class NotificationFilter(django_filters.FilterSet):
    """通知过滤器"""
    
    # 支持通过notification_type的code进行过滤
    notification_type = django_filters.CharFilter(
        method='filter_notification_type',
        help_text='通知类型代码或ID'
    )
    
    # 支持通过notification_type的code进行过滤（别名）
    notification_type_code = django_filters.CharFilter(
        method='filter_notification_type',
        help_text='通知类型代码'
    )
    
    class Meta:
        model = Notification
        fields = {
            'is_read': ['exact'],
            'priority': ['exact', 'in'],
            'status': ['exact', 'in'],
            'created_at': ['gte', 'lte', 'date'],
            'sender': ['exact'],
            'recipient': ['exact'],
        }
    
    def filter_notification_type(self, queryset, name, value):
        """过滤通知类型
        
        支持两种方式：
        1. 直接传递NotificationType的ID
        2. 传递NotificationType的code
        """
        if not value:
            return queryset
        
        # 尝试将value转换为整数（ID）
        try:
            notification_type_id = int(value)
            return queryset.filter(notification_type_id=notification_type_id)
        except ValueError:
            # 如果不是整数，则按code查询
            return queryset.filter(notification_type__code=value)