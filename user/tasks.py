from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import EmailVerificationCode
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_task(self, subject, message, recipient_list):
    """异步发送邮件任务"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info(f"邮件发送成功: {recipient_list}")
        return True
        
    except Exception as e:
        logger.error(f"邮件发送失败: {recipient_list} - {str(e)}")
        
        # 重试机制
        if self.request.retries < self.max_retries:
            # 指数退避：2^retry_count * 60秒
            countdown = 2 ** self.request.retries * 60
            raise self.retry(countdown=countdown, exc=e)
        
        return False


@shared_task
def clean_expired_verification_codes():
    """定期清理过期的验证码"""
    try:
        from django.conf import settings
        from authentication.verification_utils import clean_expired_codes
        
        # 检查是否使用Redis模式
        use_redis = getattr(settings, 'USE_REDIS_FOR_VERIFICATION_CODE', True)
        
        if use_redis:
            logger.info("使用Redis模式，验证码自动过期，跳过清理任务")
            return 0
        else:
            count = clean_expired_codes()
            logger.info(f"数据库模式：定期清理过期验证码任务完成，清理了 {count} 条记录")
            return count
            
    except Exception as e:
        logger.error(f"清理过期验证码任务失败: {str(e)}")
        return 0


@shared_task
def send_welcome_email(user_id):
    """发送欢迎邮件"""
    try:
        from .models import User
        user = User.objects.get(id=user_id)
        
        subject = '欢迎加入校企对接平台！'
        message = f"""
亲爱的 {user.real_name or user.username}，

欢迎您加入校企对接平台！

您的账户信息：
- 用户名：{user.username}
- 邮箱：{user.email}
- 用户类型：{user.get_user_type_display()}

感谢您的注册，祝您使用愉快！

校企对接平台团队
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"欢迎邮件发送成功: {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"欢迎邮件发送失败: {str(e)}")
        return False


@shared_task
def send_password_reset_email(user_id, reset_code):
    """发送密码重置邮件"""
    try:
        from .models import User
        user = User.objects.get(id=user_id)
        
        subject = '【校企对接平台】密码重置验证码'
        message = f"""
亲爱的 {user.real_name or user.username}，

您正在重置密码，验证码为：{reset_code}

验证码有效期为5分钟，请及时使用。
如果这不是您的操作，请忽略此邮件。

校企对接平台团队
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"密码重置邮件发送成功: {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"密码重置邮件发送失败: {str(e)}")
        return False


@shared_task
def generate_user_statistics():
    """生成用户统计数据"""
    try:
        from .models import User, LoginLog
        from django.db.models import Count
        
        # 用户类型统计
        user_type_stats = User.objects.values('user_type').annotate(
            count=Count('id')
        )
        
        # 今日注册用户数
        today = timezone.now().date()
        today_registrations = User.objects.filter(
            date_joined__date=today
        ).count()
        
        # 今日登录用户数
        today_logins = LoginLog.objects.filter(
            created_at__date=today,
            is_success=True
        ).values('user').distinct().count()
        
        stats = {
            'user_type_stats': list(user_type_stats),
            'today_registrations': today_registrations,
            'today_logins': today_logins,
            'generated_at': timezone.now().isoformat()
        }
        
        logger.info(f"用户统计数据生成完成: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"生成用户统计数据失败: {str(e)}")
        return None