from django.utils import timezone
from django.conf import settings
from django.core.files import File
import logging
import os
import random
import shutil

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """获取用户代理信息"""
    return request.META.get('HTTP_USER_AGENT', '')


def create_login_log(user, request, login_type, is_success=True, failure_reason=''):
    """创建登录日志"""
    from authentication.models import LoginLog
    
    try:
        LoginLog.objects.create(
            user=user,
            login_type=login_type,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            is_success=is_success,
            failure_reason=failure_reason
        )
    except Exception as e:
        logger.error(f"创建登录日志失败: {str(e)}")

 # 暂未使用 
def generate_username_from_email(email):
    """从邮箱生成用户名"""
    base_username = email.split('@')[0]
    username = base_username
    
    # 如果用户名已存在，添加随机数字
    from .models import User
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    return username

# 暂未使用
def format_user_type_display(user_type):
    """格式化用户类型显示"""
    type_map = {
        'student': '学生',
        'company': '企业',
        'admin': '管理员',
    }
    return type_map.get(user_type, user_type)


def check_password_strength(password):
    """检查密码强度"""
    if len(password) < 8:
        return False, "密码长度至少8位"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    strength_count = sum([has_upper, has_lower, has_digit, has_special])
    
    if strength_count < 2:
        return False, "密码必须包含大写字母、小写字母、数字、特殊字符中的至少两种"
    
    return True, "密码强度合格"


def assign_random_avatar(user):
    """为用户分配随机头像（仅分配路径，不复制文件）"""
    try:
        # 默认头像文件列表
        avatar_files = ['avatar_1.svg', 'avatar_2.svg', 'avatar_3.svg', 'avatar_4.svg', 'avatar_5.svg']
        
        # 随机选择一个头像
        selected_avatar = random.choice(avatar_files)
        
        # 设置默认头像路径（不复制文件）
        relative_path = f"avatars/default/{selected_avatar}"
        user.avatar = relative_path
        user.save(update_fields=['avatar'])
        
        logger.info(f"为用户 {user.username} 分配了默认头像: {relative_path}")
        return relative_path
        
    except Exception as e:
        logger.error(f"为用户 {user.username} 分配默认头像失败: {str(e)}")
        return None


def get_default_avatar_url():
    """获取默认头像URL"""
    return getattr(settings, 'DEFAULT_AVATAR_URL', '/media/avatars/default/avatar_1.svg')