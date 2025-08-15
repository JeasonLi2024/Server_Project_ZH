import os
from celery import Celery
from django.conf import settings

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')

app = Celery('Project_Zhihui')

# 使用Django设置配置Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()

# 定时任务配置
from celery.schedules import crontab

app.conf.beat_schedule = {
    # 每日零点检查待删除账户
    'process-scheduled-account-deletions': {
        'task': 'authentication.tasks.process_scheduled_account_deletions',
        'schedule': crontab(hour=0, minute=0),  # 每日零点执行
    },
    # 每天上午9点发送删除提醒邮件
    'send-deletion-reminder-emails': {
        'task': 'authentication.tasks.send_deletion_reminder_emails',
        'schedule': crontab(hour=9, minute=0),  # 每日上午9点执行
    },
    # 每周日凌晨2点清理旧的删除日志
    'cleanup-old-deletion-logs': {
        'task': 'authentication.tasks.cleanup_old_deletion_logs',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # 每周日凌晨2点执行
    },
    # 每天凌晨3点清理过期验证码
    'clean-expired-verification-codes': {
        'task': 'user.tasks.clean_expired_verification_codes',
        'schedule': crontab(hour=3, minute=0),  # 每日凌晨3点执行
    },
}

app.conf.timezone = settings.TIME_ZONE

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')