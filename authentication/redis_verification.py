"""
Redis验证码工具类
使用Redis存储验证码，提供更好的性能和自动过期功能
"""
import random
import string
import json
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def generate_verification_code(length=6):
    """生成验证码"""
    return ''.join(random.choices(string.digits, k=length))


def send_email_verification_code_redis(email, code_type='register'):
    """
    使用Redis发送邮箱验证码
    
    Args:
        email: 邮箱地址
        code_type: 验证码类型 (register/login/reset_password/change_email/delete_account)
    
    Returns:
        bool: 发送是否成功
    """
    try:
        # 检查发送频率限制
        limit_key = f"email_code_limit:{email}:{code_type}"
        if cache.get(limit_key):
            logger.warning(f"验证码发送过于频繁: {email} - {code_type}")
            return False
        
        # 生成验证码
        code = generate_verification_code(settings.EMAIL_VERIFICATION_CODE_LENGTH)
        
        # 构建Redis存储的数据
        code_data = {
            'code': code,
            'email': email,
            'code_type': code_type,
            'created_at': timezone.now().isoformat(),
            'is_used': False
        }
        
        # 存储到Redis，设置过期时间
        code_key = f"email_verification_code:{email}:{code_type}"
        cache.set(
            code_key, 
            json.dumps(code_data), 
            timeout=settings.EMAIL_VERIFICATION_CODE_EXPIRE
        )
        
        # 准备邮件内容
        subject_map = {
            'register': '【校企对接平台】注册验证码',
            'login': '【校企对接平台】登录验证码',
            'reset_password': '【校企对接平台】重置密码验证码',
            'change_email': '【校企对接平台】更换邮箱验证码',
            'delete_account': '【校企对接平台】账户注销验证码',
        }
        
        message_map = {
            'register': f'您的注册验证码是：{code}，有效期5分钟，请勿泄露给他人。',
            'login': f'您的登录验证码是：{code}，有效期5分钟，请勿泄露给他人。',
            'reset_password': f'您的重置密码验证码是：{code}，有效期5分钟，请勿泄露给他人。',
            'change_email': f'您的更换邮箱验证码是：{code}，有效期5分钟，请勿泄露给他人。',
            'delete_account': f'您的账户注销验证码是：{code}，有效期5分钟，请勿泄露给他人。此操作将永久删除您的账户，请谨慎操作。',
        }
        
        subject = subject_map.get(code_type, '【校企对接平台】验证码')
        message = message_map.get(code_type, f'您的验证码是：{code}，有效期5分钟。')
        
        # 发送邮件
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        # 设置发送频率限制（60秒内不能重复发送）
        cache.set(limit_key, True, 60)
        
        logger.info(f"验证码发送成功(Redis): {email} - {code_type} - {code}")
        return True
        
    except Exception as e:
        logger.error(f"验证码发送失败(Redis): {email} - {code_type} - {str(e)}")
        return False


def validate_email_code_redis(email, code, code_type):
    """
    使用Redis验证邮箱验证码
    
    Args:
        email: 邮箱地址
        code: 验证码
        code_type: 验证码类型
    
    Returns:
        tuple: (是否验证成功, 消息)
    """
    try:
        code_key = f"email_verification_code:{email}:{code_type}"
        code_data_json = cache.get(code_key)
        
        if not code_data_json:
            return False, "验证码无效或已过期"
        
        code_data = json.loads(code_data_json)
        
        # 检查验证码是否已使用
        if code_data.get('is_used', False):
            return False, "验证码已使用"
        
        # 验证验证码
        if code_data.get('code') != code:
            return False, "验证码错误"
        
        # 标记为已使用
        code_data['is_used'] = True
        cache.set(
            code_key, 
            json.dumps(code_data), 
            timeout=settings.EMAIL_VERIFICATION_CODE_EXPIRE
        )
        
        logger.info(f"验证码验证成功(Redis): {email} - {code_type}")
        return True, "验证成功"
        
    except json.JSONDecodeError:
        logger.error(f"验证码数据格式错误(Redis): {email} - {code_type}")
        return False, "验证码数据错误"
    except Exception as e:
        logger.error(f"验证码验证异常(Redis): {email} - {code_type} - {str(e)}")
        return False, "验证码验证失败"


def verify_email_code_redis(email, code, code_type):
    """
    验证邮箱验证码（不消费，仅验证）
    
    Args:
        email: 邮箱地址
        code: 验证码
        code_type: 验证码类型
    
    Returns:
        tuple: (是否验证成功, 消息)
    """
    try:
        code_key = f"email_verification_code:{email}:{code_type}"
        code_data_json = cache.get(code_key)
        
        if not code_data_json:
            return False, "验证码无效或已过期"
        
        code_data = json.loads(code_data_json)
        
        # 检查验证码是否已使用
        if code_data.get('is_used', False):
            return False, "验证码已使用"
        
        # 验证验证码
        if code_data.get('code') != code:
            return False, "验证码错误"
        
        logger.info(f"验证码校验成功(Redis): {email} - {code_type}")
        return True, "验证成功"
        
    except json.JSONDecodeError:
        logger.error(f"验证码数据格式错误(Redis): {email} - {code_type}")
        return False, "验证码数据错误"
    except Exception as e:
        logger.error(f"验证码校验异常(Redis): {email} - {code_type} - {str(e)}")
        return False, "验证码校验失败"


def clean_expired_codes_redis():
    """
    清理过期的验证码（Redis会自动过期，这里主要用于统计）
    
    Returns:
        int: 清理的数量（Redis自动过期，返回0）
    """
    logger.info("Redis验证码自动过期，无需手动清理")
    return 0


def get_verification_code_info_redis(email, code_type):
    """
    获取验证码信息（用于调试）
    
    Args:
        email: 邮箱地址
        code_type: 验证码类型
    
    Returns:
        dict: 验证码信息
    """
    try:
        code_key = f"email_verification_code:{email}:{code_type}"
        code_data_json = cache.get(code_key)
        
        if not code_data_json:
            return None
        
        code_data = json.loads(code_data_json)
        
        # 获取TTL（剩余过期时间）
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        ttl = redis_conn.ttl(f":1:email_verification_code:{email}:{code_type}")
        
        code_data['ttl_seconds'] = ttl
        return code_data
        
    except Exception as e:
        logger.error(f"获取验证码信息失败(Redis): {email} - {code_type} - {str(e)}")
        return None