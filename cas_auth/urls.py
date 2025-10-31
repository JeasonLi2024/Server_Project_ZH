from django.urls import path
from . import views

app_name = 'cas_auth'

urlpatterns = [
    # CAS认证相关路由
    path('login/', views.cas_login, name='cas_login'),
    path('callback/', views.cas_callback, name='cas_callback'),
    path('logout/', views.cas_logout, name='cas_logout'),
    path('status/', views.cas_status, name='cas_status'),
    path('user-info/', views.cas_user_info, name='cas_user_info'),
]