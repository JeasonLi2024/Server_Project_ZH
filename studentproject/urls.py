from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'studentproject'

# 创建DRF路由器
router = DefaultRouter()


urlpatterns = [
    # 项目管理接口
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/<int:project_id>/update/', views.update_project, name='update_project'),
    path('projects/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    path('projects/', views.get_project_list, name='project_list'),
    path('projects/<int:project_id>/', views.get_project_detail, name='project_detail'),
    
    # 项目参与者管理接口
    path('projects/<int:project_id>/apply/', views.apply_to_join_project, name='apply_to_join_project'),
    path('projects/<int:project_id>/applications/handle/', views.handle_applications, name='handle_applications'),
    path('projects/<int:project_id>/participants/', views.get_project_participants, name='get_project_participants'),
    path('projects/<int:project_id>/participants/<int:participant_id>/', views.get_participant_detail, name='get_participant_detail'),
    path('projects/<int:project_id>/participants/<int:participant_id>/status/', views.update_participant_status, name='update_participant_status'),
    path('projects/<int:project_id>/transfer-leadership/', views.transfer_leadership, name='transfer_leadership'),
    
    # 项目邀请相关接口
    path('projects/<int:project_id>/send-invitation/', views.send_invitation, name='send_invitation'),
    path('invitations/<int:invitation_id>/respond/', views.respond_to_invitation, name='respond_to_invitation'),
    path('invitations/', views.get_invitations, name='get_invitations'),
    
    # 项目成果管理接口
    path('projects/<int:project_id>/deliverables/submit/', views.submit_deliverable, name='submit_deliverable'),
    path('projects/<int:project_id>/deliverables/<int:deliverable_id>/update/', views.update_deliverable, name='update_deliverable'),
    path('projects/<int:project_id>/deliverables/', views.get_deliverable_list, name='get_deliverable_list'),
    path('projects/<int:project_id>/deliverables/<int:deliverable_id>/', views.get_deliverable_detail, name='get_deliverable_detail'),
    
    # 数据统计接口
    path('organization/overview/', views.get_organization_overview, name='organization_overview'),
    
    # 评论系统接口
    path('projects/<int:project_id>/comments/', views.get_comment_list, name='get_comment_list'),
    path('projects/<int:project_id>/comments/create/', views.create_comment, name='create_comment'),
    path('projects/<int:project_id>/comments/<int:comment_id>/update/', views.update_comment, name='update_comment'),
    path('projects/<int:project_id>/comments/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('projects/<int:project_id>/comments/<int:comment_id>/replies/', views.get_comment_replies, name='get_comment_replies'),
    
    # 包含DRF路由器的URL
    path('', include(router.urls)),
]