"""
高并发验证码发送优化方案
使用异步任务和连接池优化性能
"""
import random
import string
import json
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)


def generate_verification_code(length=6):
    """生成验证码"""
    return ''.join(random.choices(string.digits, k=length))


def send_email_verification_code_async(email, code_type='register'):
    """
    异步发送邮箱验证码（高并发优化版本）
    
    Args:
        email: 邮箱地址
        code_type: 验证码类型
    
    Returns:
        bool: 是否成功提交发送任务
    """
    try:
        # 检查发送频率限制（使用Redis原子操作）
        limit_key = f"email_code_limit:{email}:{code_type}"
        
        # 使用Redis的SET NX EX命令实现原子性频率限制
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        
        # 如果key不存在则设置，存在则返回False
        if not redis_conn.set(limit_key, "1", nx=True, ex=60):
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
        
        # 存储到Redis（使用pipeline提高性能）
        code_key = f"email_verification_code:{email}:{code_type}"
        pipe = redis_conn.pipeline()
        pipe.setex(
            code_key, 
            settings.EMAIL_VERIFICATION_CODE_EXPIRE,
            json.dumps(code_data)
        )
        pipe.execute()
        
        # 异步发送邮件
        send_verification_email_task.delay(email, code, code_type)
        
        logger.info(f"验证码发送任务已提交(Async): {email} - {code_type}")
        return True
        
    except Exception as e:
        logger.error(f"验证码发送失败(Async): {email} - {code_type} - {str(e)}")
        return False


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email_task(self, email, code, code_type):
    """
    Celery异步邮件发送任务
    
    Args:
        email: 邮箱地址
        code: 验证码
        code_type: 验证码类型
    """
    try:
        # 邮件主题和内容映射
        subject_map = {
            'register': '【校企对接平台】注册验证码',
            'login': '【校企对接平台】登录验证码',
            'reset_password': '【校企对接平台】重置密码验证码',
            'change_email': '【校企对接平台】更换邮箱验证码',
        }
        
        # 使用HTML模板（可选）
        subject = subject_map.get(code_type, '【校企对接平台】验证码')
        
        # 纯文本内容
        text_content = f'您的{code_type}验证码是：{code}，有效期5分钟，请勿泄露给他人。'
        
        # HTML内容（更美观）
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">校企对接平台</h2>
            <p>您好！</p>
            <p>您的验证码是：</p>
            <div style="background: #f5f5f5; padding: 20px; text-align: center; font-size: 24px; font-weight: bold; color: #007bff; letter-spacing: 5px; margin: 20px 0;">
                {code}
            </div>
            <p style="color: #666;">验证码有效期为5分钟，请及时使用。</p>
            <p style="color: #999; font-size: 12px;">如果您没有申请此验证码，请忽略此邮件。</p>
        </div>
        """
        
        # 创建邮件对象
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        msg.attach_alternative(html_content, "text/html")
        
        # 发送邮件
        msg.send()
        
        logger.info(f"验证码邮件发送成功(Task): {email} - {code_type} - {code}")
        return True
        
    except Exception as e:
        logger.error(f"验证码邮件发送失败(Task): {email} - {code_type} - {str(e)}")
        
        # 重试机制
        if self.request.retries < self.max_retries:
            logger.info(f"邮件发送重试: {email} - 第{self.request.retries + 1}次")
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        return False


def validate_email_code_optimized(email, code, code_type):
    """
    优化的验证码验证（使用Redis Lua脚本保证原子性）
    
    Args:
        email: 邮箱地址
        code: 验证码
        code_type: 验证码类型
    
    Returns:
        tuple: (是否验证成功, 消息)
    """
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        
        code_key = f"email_verification_code:{email}:{code_type}"
        
        # Lua脚本保证原子性验证和标记
        lua_script = """
        local key = KEYS[1]
        local input_code = ARGV[1]
        
        local data = redis.call('GET', key)
        if not data then
            return {0, "验证码无效或已过期"}
        end
        
        local code_data = cjson.decode(data)
        
        if code_data.is_used then
            return {0, "验证码已使用"}
        end
        
        if code_data.code ~= input_code then
            return {0, "验证码错误"}
        end
        
        -- 标记为已使用
        code_data.is_used = true
        local ttl = redis.call('TTL', key)
        redis.call('SETEX', key, ttl, cjson.encode(code_data))
        
        return {1, "验证成功"}
        """
        
        result = redis_conn.eval(lua_script, 1, code_key, code)
        
        success = bool(result[0])
        message = result[1]
        
        if success:
            logger.info(f"验证码验证成功(Optimized): {email} - {code_type}")
        
        return success, message
        
    except Exception as e:
        logger.error(f"验证码验证异常(Optimized): {email} - {code_type} - {str(e)}")
        return False, "验证码验证失败"


# 批量验证码生成（用于压力测试）
def batch_generate_codes(count=1000):
    """
    批量生成验证码（用于性能测试）
    
    Args:
        count: 生成数量
    
    Returns:
        list: 验证码列表
    """
    codes = []
    for i in range(count):
        email = f"test{i}@example.com"
        code = generate_verification_code()
        codes.append({
            'email': email,
            'code': code,
            'code_type': 'register'
        })
    
    return codes


# 性能监控装饰器
def performance_monitor(func):
    """性能监控装饰器"""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            logger.error(f"函数执行异常: {func.__name__} - {str(e)}")
        
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        logger.info(f"性能监控 - {func.__name__}: {execution_time:.2f}ms, 成功: {success}")
        
        return result
    
    return wrapper