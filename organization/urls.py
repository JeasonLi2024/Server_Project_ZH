from django.urls import path
from . import views

app_name = 'organization'

urlpatterns = [
    # 搜索组织
    path('search/', views.search_organizations, name='search_organizations'),
    
    # 组织详情
    path('<int:organization_id>/detail/', views.organization_detail, name='organization_detail'),
    
    # 组织认证相关
    path('verification/submit/', views.submit_verification_materials_with_images, name='submit_verification_materials_with_images'),
    path('verification/status/', views.verification_status, name='verification_status'),
    path('user/status/', views.user_status, name='user_status'),
    
    # 组织成员管理
    path('members/', views.organization_members, name='organization_members'),
    path('members/<int:member_id>/update/', views.update_member, name='update_member'),
    path('members/batch-update/', views.batch_update_members, name='batch_update_members'),
    
    # 组织操作日志
    path('operation-logs/', views.organization_operation_logs, name='organization_operation_logs'),
    
    # 组织配置
    path('config/', views.organization_config, name='organization_config'),
    
    # 组织信息管理
    path('update/', views.update_organization, name='update_organization'),
    path('upload-logo/', views.upload_organization_logo, name='upload_organization_logo'),

]