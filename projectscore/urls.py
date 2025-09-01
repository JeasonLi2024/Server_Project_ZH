from django.urls import path
from . import views

app_name = 'projectscore'

urlpatterns = [
    # 评分标准基础CRUD接口
    path('criteria/list/', views.list_evaluation_criteria, name='list_criteria'),  # GET - 获取评分标准列表
    path('criteria/create/', views.create_evaluation_criteria, name='create_criteria'),  # POST - 创建评分标准

    # 评分标准详情和操作接口
    path('criteria/<int:criteria_id>/', views.get_evaluation_criteria_detail, name='criteria_detail'),  # GET - 获取评分标准详情
    path('criteria/<int:criteria_id>/update/', views.update_evaluation_criteria, name='update_criteria'),
    # PUT/PATCH - 更新评分标准基础信息
    path('criteria/<int:criteria_id>/delete/', views.delete_evaluation_criteria, name='delete_criteria'),
    # DELETE - 删除评分标准

    # 评分标准特殊操作接口
    path('criteria/<int:criteria_id>/status/', views.update_evaluation_criteria_status, name='update_criteria_status'),
    # PATCH - 切换评分标准状态
    path('criteria/clone/', views.clone_evaluation_criteria, name='clone_criteria'),  # POST - 复制评分标准生成新标准
    # 注意：获取模板列表功能已整合到 criteria/ 接口中，通过 ?is_template=true 参数实现

    # 评分指标CRUD接口
    path('criteria/<int:criteria_id>/indicators/list/', views.list_evaluation_indicators, name='list_indicators'),
    # GET - 获取指标列表
    path('criteria/<int:criteria_id>/indicators/create/', views.create_evaluation_indicator, name='create_indicator'),
    # POST - 创建指标（支持单个或批量）

    # 批量更新指标接口
    path('criteria/<int:criteria_id>/indicators/batch/update/', views.batch_update_evaluation_criteria_indicators,
         name='batch_update_indicators'),  # PATCH - 批量更新多个指标

    # 单个指标操作接口
    path('criteria/<int:criteria_id>/indicators/<int:indicator_id>/update/', views.update_evaluation_indicator,
         name='update_indicator'),  # PUT/PATCH - 更新单个指标
    path('criteria/<int:criteria_id>/indicators/<int:indicator_id>/delete/', views.delete_evaluation_indicator,
         name='delete_indicator'),  # DELETE - 删除指标

    # 批量删除指标接口
    path('criteria/<int:criteria_id>/indicators/batch/delete/', views.batch_delete_evaluation_indicators,
         name='batch_delete_indicators'),  # DELETE - 批量删除指标

    # 项目评分管理接口
    path('evaluations/<int:project_id>/create/', views.create_project_evaluation, name='create_project_evaluation'),
    # POST - 创建项目评分
    path('evaluations/<int:project_id>/', views.get_project_evaluation_detail, name='get_project_evaluation_detail'),
    # GET - 获取项目评分详情
    path('evaluations/<int:project_id>/update/', views.update_project_evaluation, name='update_project_evaluation'),
    # PUT/PATCH - 更新项目评分
    path('evaluations/<int:project_id>/submit/', views.submit_project_evaluation, name='submit_project_evaluation'),
    # POST - 提交项目评分

    # 项目排名接口
    path('requirements/<int:requirement_id>/ranking/', views.get_project_ranking, name='get_project_ranking'),
    # GET - 获取需求下项目排名（公示功能）
    path('requirements/<int:requirement_id>/ranking/view/', views.view_project_ranking, name='view_project_ranking'),
    # GET - 查看需求下项目排名（纯展示功能）
]