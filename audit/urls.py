from django.urls import path
from . import views

urlpatterns = [
    # 需求审核历史接口
    path('requirements/<int:requirement_id>/history/', views.get_requirement_audit_history, name='requirement_audit_history'),
    
    # 组织认证审核历史接口
    path('organizations/<int:organization_id>/history/', views.get_organization_audit_history, name='organization_audit_history'),
    
    # 当前用户所属组织的审核历史接口
    path('organizations/my/history/', views.get_organization_audit_history, name='my_organization_audit_history'),
    
    # 审核统计信息接口
    path('statistics/', views.get_audit_statistics, name='audit_statistics'),
]