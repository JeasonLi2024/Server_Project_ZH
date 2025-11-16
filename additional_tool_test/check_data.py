import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from project.models import Requirement
from user.models import OrganizationUser

print(f'当前需求总数: {Requirement.objects.count()}')
print(f'活跃组织用户数: {OrganizationUser.objects.filter(status="active").count()}')
print(f'总组织用户数: {OrganizationUser.objects.count()}')

# 检查权限分布
from collections import Counter
permissions = OrganizationUser.objects.values_list('permission', flat=True)
permission_counts = Counter(permissions)
print(f'\n权限分布: {dict(permission_counts)}')

# 检查生成脚本使用的用户
admin_owner_users = OrganizationUser.objects.filter(permission__in=['admin', 'owner'])
print(f'\nadmin/owner用户数: {admin_owner_users.count()}')
for i, org_user in enumerate(admin_owner_users[:10]):
    print(f'{i+1}. {org_user.user.username} - {org_user.organization.name} - {org_user.permission}')

# 检查所有用户
all_users = OrganizationUser.objects.all()
print(f'\n所有组织用户前10个:')
for i, org_user in enumerate(all_users[:10]):
    print(f'{i+1}. {org_user.user.username} - {org_user.organization.name} - {org_user.permission}')