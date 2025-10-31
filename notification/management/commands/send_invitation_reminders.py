from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging

from notification.tasks import send_invitation_expiry_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '发送邀请过期提醒通知'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='空运行模式，不实际发送通知，只显示统计信息'
        )
        
        parser.add_argument(
            '--days-before',
            type=int,
            default=1,
            help='提前多少天发送提醒（默认1天）'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days_before = options['days_before']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'开始发送邀请过期提醒（提前{days_before}天）...'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('空运行模式：不会实际发送通知')
            )
            
            # 在空运行模式下，只统计数量
            try:
                from studentproject.models import ProjectInvitation
                
                target_date = timezone.now() + timedelta(days=days_before)
                expiring_invitations = ProjectInvitation.objects.filter(
                    expires_at__date=target_date.date(),
                    status='pending'
                ).select_related('invitee', 'inviter', 'project')
                
                count = expiring_invitations.count()
                
                self.stdout.write(
                    f'找到 {count} 个即将过期的邀请：'
                )
                
                for invitation in expiring_invitations:
                    self.stdout.write(
                        f'  - 项目: {invitation.project.title}, '
                        f'被邀请人: {invitation.invitee.username}, '
                        f'过期时间: {invitation.expires_at}'
                    )
                
            except ImportError:
                self.stdout.write(
                    self.style.ERROR('ProjectInvitation模型不可用')
                )
                return
            
        else:
            # 实际发送通知
            try:
                reminder_count = send_invitation_expiry_reminders()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'邀请过期提醒发送完成！共发送 {reminder_count} 条提醒'
                    )
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'发送邀请过期提醒失败: {str(e)}')
                )
                logger.error(f'发送邀请过期提醒失败: {str(e)}')
                raise
        
        self.stdout.write(
            self.style.SUCCESS('邀请过期提醒任务执行完成')
        )