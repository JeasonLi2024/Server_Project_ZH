from django.urls import path
from . import views
from . import test_views

app_name = 'auth'

urlpatterns = [
    # 发送验证码
    path('send-email-code/', views.send_email_code, name='send_email_code'),
    
    # 认证相关接口
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),  # 统一登录接口
    path('logout/', views.logout, name='logout'),
    path('verify/', views.verify, name='verify'),
    path('refresh/', views.refresh, name='refresh'),
    
    # 密码相关
    path('password/', views.change_password, name='change_password'),
    path('reset/', views.reset_password_request, name='reset_password_request'),
    path('reset/confirm/', views.reset_password, name='reset_password'),
    
    # 邮箱相关
    path('change_email/', views.change_email, name='change_email'),
    
    # 登录日志
    path('login-logs/', views.login_logs, name='login_logs'),
    
    # 验证码验证
    path('verify-code/', views.verify_email_code_view, name='verify_email_code'),
    
    # 用户存在性检查
    path('check-email/', views.check_email_exists, name='check_email_exists'),
    path('check-username/', views.check_username_exists, name='check_username_exists'),
    
    # 账户注销相关
    path('delete-account/request/', views.request_account_deletion, name='request_account_deletion'),
    path('delete-account/cancel/', views.cancel_account_deletion, name='cancel_account_deletion'),
    path('delete-account/status/', views.account_deletion_status, name='account_deletion_status'),
    
    # 测试API（仅DEBUG模式）
    path('test/create-code/', test_views.create_test_verification_code, name='create_test_verification_code'),
    path('test/get-code/', test_views.get_test_verification_code, name='get_test_verification_code'),
    path('test/batch-create-codes/', test_views.batch_create_test_codes, name='batch_create_test_codes'),
    path('test/clear-codes/', test_views.clear_test_verification_codes, name='clear_test_verification_codes'),
    path('test/status/', test_views.test_api_status, name='test_api_status'),
]