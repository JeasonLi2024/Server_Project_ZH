from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # 在线人数统计
    path('online-count/', views.get_online_count, name='online_count'),
    
    # 学生标签统计
    path('study-direction/', views.get_tag1_student_stats, name='tag1_student_stats'),
    path('target-job/', views.get_tag2_student_stats, name='tag2_student_stats'),
    
    # 项目状态统计
    path('total-projects/', views.get_project_status_stats, name='project_status_stats'),
    
    # 组织状态统计
    path('organization-count/', views.get_organization_status_stats, name='organization_status_stats'),
    
    # 项目标签统计
    path('project-fields/', views.get_project_tag1_stats, name='project_tag1_stats'),
    
    # 用户注册统计
    path('user-registration/', views.get_user_registration_stats, name='user_registration_stats'),
    
    # 新增接口
    path('model-qa-count/', views.get_qianduan_answer_number, name='qianduan_answer_number'),
    path('high-freq-tags/', views.get_top_tags_by_frequency, name='top_tags_frequency'),
]