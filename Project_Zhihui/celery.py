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
    # 每天凌晨4点自动更新过期需求状态
    'auto-complete-expired-requirements': {
        'task': 'notification.tasks.auto_complete_expired_requirements',
        'schedule': crontab(hour=4, minute=0),  # 每日凌晨4点执行
    },
    # 每天上午10点发送需求截止提醒
    'send-requirement-deadline-reminders': {
        'task': 'notification.tasks.send_requirement_deadline_reminders',
        'schedule': crontab(hour=10, minute=0),  # 每日上午10点执行
    },
    # 每天上午9点发送邀请过期提醒
    'send-invitation-expiry-reminders': {
        'task': 'notification.tasks.send_invitation_expiry_reminders',
        'schedule': crontab(hour=9, minute=0),  # 每日上午9点执行
    },
    # 每天凌晨1点清理过期通知
    'cleanup-old-notifications': {
        'task': 'notification.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=1, minute=0),  # 每日凌晨1点执行
    },
    # 每天凌晨2点清理旧的通知日志
    'cleanup-old-notification-logs': {
        'task': 'notification.tasks.cleanup_old_notification_logs',
        'schedule': crontab(hour=2, minute=30),  # 每日凌晨2点30分执行
    },
    
    # Dashboard统计数据定时任务
    # 每日6点更新所有Dashboard统计数据
    'update-dashboard-stats-daily': {
        'task': 'dashboard.tasks.update_all_dashboard_stats',
        'schedule': crontab(hour=6, minute=0),  # 每天早上6点执行
        'options': {
            'expires': 3600,  # 任务1小时后过期
        }
    },
    # 每4小时更新一次Tag1学生标签统计（热点数据）
    'update-tag1-student-stats-frequent': {
        'task': 'dashboard.tasks.update_tag1_student_stats',
        'schedule': crontab(minute=0, hour='*/4'),  # 每4小时执行一次
        'options': {
            'expires': 1800,  # 任务30分钟后过期
        }
    },
    # 每4小时更新一次Tag2学生标签统计（热点数据）
    'update-tag2-student-stats-frequent': {
        'task': 'dashboard.tasks.update_tag2_student_stats',
        'schedule': crontab(minute=0, hour='*/4'),  # 每4小时执行一次
        'options': {
            'expires': 1800,  # 任务30分钟后过期
        }
    },
    # 每2小时更新一次项目状态统计（变化较频繁）
    'update-project-status-stats-frequent': {
        'task': 'dashboard.tasks.update_project_status_stats',
        'schedule': crontab(minute=0, hour='*/2'),  # 每2小时执行一次
        'options': {
            'expires': 1800,  # 任务30分钟后过期
        }
    },
    # 每日6点30分更新组织状态统计
    'update-organization-status-stats-daily': {
        'task': 'dashboard.tasks.update_organization_status_stats',
        'schedule': crontab(hour=6, minute=30),  # 每天早上6点30分执行
        'options': {
            'expires': 3600,  # 任务1小时后过期
        }
    },
    # 每日7点更新项目Tag1标签统计
    'update-project-tag1-stats-daily': {
        'task': 'dashboard.tasks.update_project_tag1_stats',
        'schedule': crontab(hour=7, minute=0),  # 每天早上7点执行
        'options': {
            'expires': 3600,  # 任务1小时后过期
        }
    },
    
    # 邀请码相关定时任务
    # 每天凌晨3点清理过期的邀请码
    'cleanup-expired-invitation-codes': {
        'task': 'authentication.tasks.cleanup_expired_invitation_codes_task',
        'schedule': crontab(hour=3, minute=0),  # 每日凌晨3点执行
    },
    # 每周日凌晨4点清理老旧的邀请码数据
    'cleanup-old-invitation-codes': {
        'task': 'authentication.tasks.cleanup_old_invitation_codes_task',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),  # 每周日凌晨4点执行
    },
    # 每天上午8点发送邀请码即将过期通知
    'send-invitation-code-expiry-notifications': {
        'task': 'authentication.tasks.send_invitation_code_expiry_notification',
        'schedule': crontab(hour=8, minute=0),  # 每日上午8点执行
    },
    # 每天上午8点30分发送邀请码已过期通知
    'send-invitation-code-expired-notifications': {
        'task': 'authentication.tasks.send_invitation_code_expired_notification',
        'schedule': crontab(hour=8, minute=30),  # 每日上午8点30分执行
    },

}

app.conf.timezone = settings.TIME_ZONE

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')