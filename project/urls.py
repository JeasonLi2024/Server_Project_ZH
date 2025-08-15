from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet

# 创建路由器
router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')

app_name = 'project'

urlpatterns = [
    path('api/', include(router.urls)),
]