from django.core.management.base import BaseCommand
from django.utils import timezone
from authentication.tasks import process_scheduled_account_deletions
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '处理计划中的账户删除任务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要删除的账户，不执行实际删除',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制执行删除，跳过确认',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f'开始处理账户删除任务 - {timezone.now()}')
        )

        if options['dry_run']:
            self.dry_run()
        else:
            if not options['force']:
                confirm = input('确认执行账户删除任务？这将永久删除用户数据 (y/N): ')
                if confirm.lower() != 'y':
                    self.stdout.write(self.style.WARNING('任务已取消'))
                    return

            result = process_scheduled_account_deletions()
            
            if 'error' in result:
                self.stdout.write(
                    self.style.ERROR(f'任务执行失败: {result["error"]}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'任务执行完成 - 成功: {result["processed"]}, '
                        f'失败: {result["failed"]}, 总计: {result["total"]}'
                    )
                )

    def dry_run(self):
        """预览模式，显示将要删除的账户"""
        from authentication.models import AccountDeletionLog
        
        current_time = timezone.now()
        pending_deletions = AccountDeletionLog.objects.filter(
            status__in=['pending', 'approved'],
            scheduled_deletion_at__lte=current_time
        )

        if not pending_deletions.exists():
            self.stdout.write(
                self.style.SUCCESS('没有需要处理的账户删除申请')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'找到 {pending_deletions.count()} 个待删除账户:')
        )

        for deletion_log in pending_deletions:
            self.stdout.write(
                f'- 用户ID: {deletion_log.user_id}, '
                f'用户名: {deletion_log.username}, '
                f'计划删除时间: {deletion_log.scheduled_deletion_at}, '
                f'状态: {deletion_log.status}'
            )