from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'preferences', views.NotificationPreferenceViewSet, basename='notification-preference')
router.register(r'types', views.NotificationTypeViewSet, basename='notification-type')
router.register(r'organization', views.OrganizationNotificationViewSet, basename='organization-notification')

# URL配置
urlpatterns = [
    # API路由 - 直接包含路由器URL，不需要额外的api/前缀
    path('', include(router.urls)),
    
    # 其他自定义路由可以在这里添加
]

app_name = 'notification'