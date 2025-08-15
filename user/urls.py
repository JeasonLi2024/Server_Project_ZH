from django.urls import path
from . import views

app_name = 'user'

urlpatterns = [
    # 用户资料管理
    path('profile/', views.profile, name='profile'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('upload-avatar/', views.upload_avatar, name='upload_avatar'),
    

    
    # 其他功能已移至authentication应用:
    # - token/refresh/ -> auth:refresh
    # - verify-code/ -> auth:verify_email_code  
    # - change-password/ -> auth:change_password
    # - login-logs/ -> auth:login_logs
    # - check-email/ -> auth:check_email_exists
    # - check-username/ -> auth:check_username_exists
    # - send-email-code/ -> auth:send_email_code
    # - send-code/ -> auth:send_code
    # - organizations/search/ -> auth:search_organizations
    # - organizations/verify/ -> auth:verify_organization
    # - verification-status/ -> auth:verification_status
]