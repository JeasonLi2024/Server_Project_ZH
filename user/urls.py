from django.urls import path
from . import views

app_name = 'user'

urlpatterns = [
    # 用户资料管理
    path('profile/', views.profile, name='profile'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('upload-avatar/', views.upload_avatar, name='upload_avatar'),
    
    # 标签管理
    path('tags/interests/', views.get_interest_tags, name='get_interest_tags'),
    path('tags/abilities/', views.get_ability_tags, name='get_ability_tags'),
    path('tags/search/', views.search_tags, name='search_tags'),
    
    # 浏览历史
    path('history/', views.get_view_history, name='get_view_history'),
    
]