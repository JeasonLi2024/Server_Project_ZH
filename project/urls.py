from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .virtual_file_views import VirtualFileViewSet

app_name = 'project'

# 创建DRF路由器
router = DefaultRouter()
router.register(r'virtual-files', VirtualFileViewSet, basename='virtual-files')

urlpatterns = [
    # 需求管理接口
    path('requirement/', views.create_requirement, name='create_requirement'),  # POST - 发布需求
    path('requirement/list/', views.list_requirements, name='list_requirements'),  # GET - 获取需求列表
    path('requirement/statistics/', views.get_requirement_statistics, name='get_requirement_statistics'),  # GET - 获取需求统计
    path('requirement/favorite/', views.toggle_requirement_favorite, name='toggle_requirement_favorite'),  # POST - 切换需求收藏状态
    path('requirement/<str:requirement_id>/', views.get_requirement, name='get_requirement'),  # GET - 获取需求详情
    path('requirement/<str:requirement_id>/update/', views.update_requirement, name='update_requirement'),  # PUT/PATCH - 修改需求
    path('requirement/<str:requirement_id>/delete/', views.delete_requirement, name='delete_requirement'),  # DELETE - 删除需求
    path('requirement/<str:requirement_id>/favorite-status/', views.check_requirement_favorite_status, name='check_requirement_favorite_status'),  # GET - 检查需求收藏状态
    
    # 资源管理接口
    path('resource/', views.create_resource, name='create_resource'),  # POST - 发布新资源/资源草稿
    path('resource/list/', views.list_resources, name='list_resources'),  # GET - 获取资源列表
    path('resource/statistics/', views.get_resource_statistics, name='get_resource_statistics'),  # GET - 获取资源统计
    path('resource/<str:resource_id>/', views.get_resource, name='get_resource'),  # GET - 获取资源详情
    path('resource/<str:resource_id>/download/', views.get_resource_download_info, name='get_resource_download_info'),  # GET - 获取资源下载信息
    path('resource/<str:resource_id>/update/', views.update_resource, name='update_resource'),  # PUT/PATCH - 修改资源
    path('resource/<str:resource_id>/delete/', views.delete_resource, name='delete_resource'),  # DELETE - 删除资源
    
    # 收藏功能接口
    path('favorites/requirements/', views.list_favorite_requirements, name='list_favorite_requirements'),  # GET - 获取收藏的需求列表
    
    # 虚拟文件系统接口
    path('', include(router.urls)),
]