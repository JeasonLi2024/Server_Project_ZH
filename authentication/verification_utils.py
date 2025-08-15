"""
验证码处理工具模块
包含验证码的生成、发送、验证等功能
"""
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from .models import EmailVerificationCode
from .redis_verification import (
    send_email_verification_code_redis,
    validate_email_code_redis,
    verify_email_code_redis,
    clean_expired_codes_redis,
    get_verification_code_info_redis
)
import logging

logger = logging.getLogger(__name__)

# 配置是否使用Redis存储验证码
USE_REDIS_FOR_VERIFICATION_CODE = getattr(settings, 'USE_REDIS_FOR_VERIFICATION_CODE', True)


def generate_verification_code(length=6):
    """生成验证码"""
    return ''.join(random.choices(string.digits, k=length))


def send_verification_code(email, code_type='register'):
    """发送验证码（测试模式支持固定验证码）"""
    from django.conf import settings
    
    # 测试模式：使用固定验证码
    if getattr(settings, 'USE_FIXED_VERIFICATION_CODE', False):
        fixed_code = getattr(settings, 'FIXED_VERIFICATION_CODE', '123456')
        return create_fixed_verification_code(email, code_type, fixed_code)
    
    # 正常模式
    if USE_REDIS_FOR_VERIFICATION_CODE:
        return send_email_verification_code_redis(email, code_type)
    else:
        return send_email_verification_code_db(email, code_type)

def create_fixed_verification_code(email, code_type, code):
    """创建固定验证码（测试用）"""
    try:
        from django.core.cache import cache
        from django.utils import timezone
        import json
        
        code_data = {
            'code': code,
            'email': email,
            'code_type': code_type,
            'created_at': timezone.now().isoformat(),
            'is_used': False
        }
        
        code_key = f"email_verification_code:{email}:{code_type}"
        cache.set(
            code_key, 
            json.dumps(code_data), 
            timeout=settings.EMAIL_VERIFICATION_CODE_EXPIRE
        )
        
        logger.info(f"固定验证码创建成功: {email} - {code_type} - {code}")
        return True
        
    except Exception as e:
        logger.error(f"固定验证码创建失败: {email} - {code_type} - {str(e)}")
        return False


def send_email_verification_code_db(email, code_type='register'):
    """使用数据库发送邮箱验证码"""
    try:
        # 检查发送频率限制
        cache_key = f"email_code_limit:{email}:{code_type}"
        if cache.get(cache_key):
            logger.warning(f"验证码发送过于频繁: {email} - {code_type}")
            return False
        
        # 生成验证码
        code = generate_verification_code(settings.EMAIL_VERIFICATION_CODE_LENGTH)
        
        # 设置过期时间
        expires_at = timezone.now() + timedelta(seconds=settings.EMAIL_VERIFICATION_CODE_EXPIRE)
        
        # 保存验证码到数据库
        EmailVerificationCode.objects.create(
            email=email,
            code=code,
            code_type=code_type,
            expires_at=expires_at
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
        cache.set(cache_key, True, 60)
        
        logger.info(f"验证码发送成功(DB): {email} - {code_type} - {code}")
        return True
        
    except Exception as e:
        logger.error(f"验证码发送失败(DB): {email} - {code_type} - {str(e)}")
        return False


def validate_email_code(email, code, code_type):
    """验证邮箱验证码（智能路由函数）"""
    if USE_REDIS_FOR_VERIFICATION_CODE:
        return validate_email_code_redis(email, code, code_type)
    else:
        return validate_email_code_db(email, code, code_type)


def validate_email_code_db(email, code, code_type):
    """使用数据库验证邮箱验证码"""
    try:
        code_obj = EmailVerificationCode.objects.get(
            email=email,
            code=code,
            code_type=code_type,
            is_used=False
        )
        
        if code_obj.is_expired():
            return False, "验证码已过期"
        
        # 标记为已使用
        code_obj.is_used = True
        code_obj.save()
        
        logger.info(f"验证码验证成功(DB): {email} - {code_type}")
        return True, "验证成功"
        
    except EmailVerificationCode.DoesNotExist:
        return False, "验证码无效"


def verify_email_code(email, code, code_type):
    """验证邮箱验证码（不消费，仅验证）"""
    if USE_REDIS_FOR_VERIFICATION_CODE:
        return verify_email_code_redis(email, code, code_type)
    else:
        return verify_email_code_db(email, code, code_type)


def verify_email_code_db(email, code, code_type):
    """使用数据库验证邮箱验证码（不消费）"""
    try:
        code_obj = EmailVerificationCode.objects.get(
            email=email,
            code=code,
            code_type=code_type,
            is_used=False
        )
        
        if code_obj.is_expired():
            return False, "验证码已过期"
        
        logger.info(f"验证码校验成功(DB): {email} - {code_type}")
        return True, "验证成功"
        
    except EmailVerificationCode.DoesNotExist:
        return False, "验证码无效"


def clean_expired_codes():
    """清理过期的验证码（智能路由函数）"""
    if USE_REDIS_FOR_VERIFICATION_CODE:
        return clean_expired_codes_redis()
    else:
        return clean_expired_codes_db()


def clean_expired_codes_db():
    """使用数据库清理过期的验证码"""
    try:
        expired_count = EmailVerificationCode.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]
        
        logger.info(f"清理过期验证码(DB): {expired_count} 条")
        return expired_count
        
    except Exception as e:
        logger.error(f"清理过期验证码失败(DB): {str(e)}")
        return 0


def get_verification_code_info(email, code_type):
    """获取验证码信息（用于调试和管理）"""
    if USE_REDIS_FOR_VERIFICATION_CODE:
        return get_verification_code_info_redis(email, code_type)
    else:
        return get_verification_code_info_db(email, code_type)


def get_verification_code_info_db(email, code_type):
    """使用数据库获取验证码信息"""
    try:
        code_obj = EmailVerificationCode.objects.filter(
            email=email,
            code_type=code_type,
            is_used=False
        ).first()
        
        if not code_obj:
            return None
        
        return {
            'code': code_obj.code,
            'email': code_obj.email,
            'code_type': code_obj.code_type,
            'created_at': code_obj.created_at.isoformat(),
            'expires_at': code_obj.expires_at.isoformat(),
            'is_used': code_obj.is_used,
            'is_expired': code_obj.is_expired(),
            'ttl_seconds': int((code_obj.expires_at - timezone.now()).total_seconds()) if not code_obj.is_expired() else 0
        }
        
    except Exception as e:
        logger.error(f"获取验证码信息失败(DB): {email} - {code_type} - {str(e)}")
        return None