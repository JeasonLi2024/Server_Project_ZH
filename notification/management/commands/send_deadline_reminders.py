from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from project.models import Requirement
from notification.services import notification_service
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '发送需求截止日期提醒通知'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days-before',
            type=int,
            default=1,
            help='提前多少天发送提醒（默认1天）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要发送的通知，不实际发送'
        )
    
    def handle(self, *args, **options):
        days_before = options['days_before']
        dry_run = options['dry_run']
        
        # 计算目标日期范围
        now = timezone.now()
        target_date = now + timedelta(days=days_before)
        
        # 查找即将到期的需求
        upcoming_deadlines = Requirement.objects.filter(
            deadline__date=target_date.date(),
            status='published'
        ).select_related('organization')
        
        if not upcoming_deadlines.exists():
            self.stdout.write(
                self.style.SUCCESS(f'没有找到{days_before}天后到期的需求')
            )
            return
        
        sent_count = 0
        error_count = 0
        
        for requirement in upcoming_deadlines:
            try:
                if dry_run:
                    self.stdout.write(
                        f'[DRY RUN] 将向需求创建者发送截止提醒: {requirement.title}'
                    )
                else:
                    notification_service.send_requirement_deadline_reminder(
                        requirement=requirement
                    )
                    self.stdout.write(
                        f'已发送截止提醒: {requirement.title}'
                    )
                sent_count += 1
                
            except Exception as e:
                error_count += 1
                logger.error(f'发送需求截止提醒失败 (需求ID: {requirement.id}): {str(e)}')
                self.stdout.write(
                    self.style.ERROR(f'发送失败: {requirement.title} - {str(e)}')
                )
        
        # 输出统计信息
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'[DRY RUN] 共找到 {sent_count} 个即将到期的需求')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'截止提醒发送完成: 成功 {sent_count} 个，失败 {error_count} 个'
                )
            )