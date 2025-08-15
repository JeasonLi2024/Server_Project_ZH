"""
Django管理命令：检查和修复企业端用户的OrganizationUser记录
使用方法：
  python manage.py check_organization_users --check  # 仅检查
  python manage.py check_organization_users --fix    # 检查并修复
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from user.models import User, OrganizationUser
from organization.models import Organization


class Command(BaseCommand):
    help = '检查和修复企业端用户的OrganizationUser记录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='仅检查数据一致性，不进行修复',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='检查并修复数据一致性问题',
        )

    def handle(self, *args, **options):
        if not options['check'] and not options['fix']:
            raise CommandError('请指定 --check 或 --fix 参数')

        self.stdout.write(
            self.style.SUCCESS('=== 企业端用户数据一致性检查 ===\n')
        )

        # 获取所有organization类型的用户
        org_users = User.objects.filter(user_type='organization')
        org_profiles = OrganizationUser.objects.all()

        self.stdout.write(f'数据库中organization类型用户总数: {org_users.count()}')
        self.stdout.write(f'OrganizationUser表记录总数: {org_profiles.count()}\n')

        # 检查缺少OrganizationUser记录的用户
        missing_users = []
        existing_users = []

        for user in org_users:
            try:
                org_profile = OrganizationUser.objects.get(user=user)
                existing_users.append((user, org_profile))
            except OrganizationUser.DoesNotExist:
                missing_users.append(user)

        # 显示检查结果
        self.stdout.write(
            self.style.SUCCESS(f'✅ 有OrganizationUser记录的用户: {len(existing_users)}')
        )
        
        if missing_users:
            self.stdout.write(
                self.style.ERROR(f'❌ 缺少OrganizationUser记录的用户: {len(missing_users)}')
            )
            for user in missing_users:
                self.stdout.write(f'   - ID: {user.id}, 用户名: {user.username}, 邮箱: {user.email}')
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ 所有企业端用户都有OrganizationUser记录')
            )

        # 检查孤立记录
        orphaned_profiles = []
        for profile in org_profiles:
            if not User.objects.filter(id=profile.user.id, user_type='organization').exists():
                orphaned_profiles.append(profile)

        if orphaned_profiles:
            self.stdout.write(
                self.style.ERROR(f'❌ 发现 {len(orphaned_profiles)} 个孤立的OrganizationUser记录')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ 没有发现孤立的OrganizationUser记录')
            )

        # 统计信息
        self.stdout.write('\n📊 统计信息:')
        self.stdout.write(f'   - 企业端用户总数: {len(org_users)}')
        self.stdout.write(f'   - 有OrganizationUser记录的用户数: {len(existing_users)}')
        self.stdout.write(f'   - 缺少OrganizationUser记录的用户数: {len(missing_users)}')
        if org_users:
            integrity = len(existing_users) / len(org_users) * 100
            self.stdout.write(f'   - 数据完整性: {len(existing_users)}/{len(org_users)} ({integrity:.1f}%)')

        # 如果指定了修复选项且有问题需要修复
        if options['fix'] and (missing_users or orphaned_profiles):
            self.stdout.write('\n开始修复数据一致性问题...')
            
            fixed_count = 0
            
            # 修复缺少OrganizationUser记录的用户
            if missing_users:
                # 创建或获取默认组织
                default_org, created = Organization.objects.get_or_create(
                    name='待分配组织',
                    defaults={
                        'organization_type': 'enterprise',
                        'enterprise_type': 'private',
                        'industry_or_discipline': '待完善',
                        'scale': 'small',
                        'contact_person': '系统管理员',
                        'contact_phone': '待完善',
                        'address': '待完善',
                        'status': 'pending'
                    }
                )
                
                if created:
                    self.stdout.write(f'✅ 创建了默认组织: {default_org.name}')
                
                with transaction.atomic():
                    for user in missing_users:
                        try:
                            org_user = OrganizationUser.objects.create(
                                user=user,
                                organization=default_org,
                                position='待完善',
                                department='待完善',
                                permission='member',
                                status='pending'
                            )
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✅ 为用户 {user.username} 创建了OrganizationUser记录'
                                )
                            )
                            fixed_count += 1
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'❌ 为用户 {user.username} 创建记录失败: {str(e)}'
                                )
                            )
            
            # 清理孤立记录
            if orphaned_profiles:
                with transaction.atomic():
                    for profile in orphaned_profiles:
                        try:
                            profile.delete()
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✅ 删除了孤立的OrganizationUser记录 (ID: {profile.id})'
                                )
                            )
                            fixed_count += 1
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'❌ 删除孤立记录失败: {str(e)}'
                                )
                            )
            
            self.stdout.write(f'\n修复完成！共处理了 {fixed_count} 个问题')
            
            # 重新检查
            self.stdout.write('\n重新检查数据一致性...')
            org_users_after = User.objects.filter(user_type='organization')
            missing_after = []
            for user in org_users_after:
                try:
                    OrganizationUser.objects.get(user=user)
                except OrganizationUser.DoesNotExist:
                    missing_after.append(user)
            
            if missing_after:
                self.stdout.write(
                    self.style.ERROR(f'❌ 仍有 {len(missing_after)} 个用户缺少记录')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ 所有企业端用户现在都有OrganizationUser记录了！')
                )

        elif options['fix'] and not missing_users and not orphaned_profiles:
            self.stdout.write(
                self.style.SUCCESS('\n✅ 数据一致性良好，无需修复')
            )

        self.stdout.write(
            self.style.SUCCESS('\n=== 检查完成 ===')
        )