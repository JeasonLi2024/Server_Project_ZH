import logging
from user.models import OrganizationUser

logger = logging.getLogger(__name__)


def mask_email(email):
    """脱敏邮箱地址"""
    if not email or '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = local[0] + '*' * (len(local) - 1)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_phone(phone):
    """脱敏手机号"""
    if not phone or len(phone) < 7:
        return phone
    
    return phone[:3] + '*' * (len(phone) - 6) + phone[-3:]


def mask_name(name):
    """脱敏姓名"""
    if not name:
        return name
    
    if len(name) == 1:
        return name
    elif len(name) == 2:
        return name[0] + '*'
    else:
        return name[0] + '*' * (len(name) - 2) + name[-1]


def check_organization_permission(user, organization, required_permission='member'):
    """
    检查用户在组织中的权限
    
    Args:
        user: 用户对象
        organization: 组织对象
        required_permission: 所需权限级别 ('owner', 'admin', 'member')
    
    Returns:
        bool: 是否有权限
    """
    try:
        org_user = OrganizationUser.objects.get(
            user=user,
            organization=organization,
            status='approved'
        )
        
        # 权限级别定义
        permission_hierarchy = {
            'owner': 3,
            'admin': 2,
            'member': 1
        }
        
        user_level = permission_hierarchy.get(org_user.permission, 0)
        required_level = permission_hierarchy.get(required_permission, 0)
        
        return user_level >= required_level
        
    except OrganizationUser.DoesNotExist:
        return False


def can_manage_organization_member(manager_user, target_user, organization):
    """
    检查管理员是否可以管理目标用户
    
    Args:
        manager_user: 管理员用户
        target_user: 目标用户
        organization: 组织对象
    
    Returns:
        bool: 是否可以管理
    """
    try:
        # 获取管理员权限
        manager_org_user = OrganizationUser.objects.get(
            user=manager_user,
            organization=organization,
            status='approved'
        )
        
        # 获取目标用户权限
        target_org_user = OrganizationUser.objects.get(
            user=target_user,
            organization=organization
        )
        
        # 权限级别定义
        permission_hierarchy = {
            'owner': 4,
            'admin': 3,
            'member': 2
        }
        
        manager_level = permission_hierarchy.get(manager_org_user.permission, 0)
        target_level = permission_hierarchy.get(target_org_user.permission, 0)
        
        # 管理员权限必须高于目标用户，且至少是admin级别
        return manager_level > target_level and manager_level >= 3
        
    except OrganizationUser.DoesNotExist:
        return False


def log_organization_operation(user, organization, operation, target_user=None, details=None):
    """
    记录组织操作日志
    
    Args:
        user: 操作用户
        organization: 组织对象
        operation: 操作类型
        target_user: 目标用户（可选）
        details: 操作详情（可选）
    """
    try:
        from .models import OrganizationOperationLog
        
        OrganizationOperationLog.objects.create(
            operator=user,
            organization=organization,
            operation=operation,
            target_user=target_user,
            details=details or {},
            ip_address=getattr(user, '_current_ip', ''),
            user_agent=getattr(user, '_current_user_agent', '')
        )
        
    except Exception as e:
        logger.error(f"记录组织操作日志失败: {str(e)}")


def get_organization_member_display_data(org_user, mask_sensitive=True):
    """
    获取组织成员的显示数据
    
    Args:
        org_user: OrganizationUser 对象
        mask_sensitive: 是否脱敏敏感信息
    
    Returns:
        dict: 成员显示数据
    """
    user = org_user.user
    
    # 基本用户信息
    user_info = {
        'id': user.id,
        'username': user.username,
        'real_name': mask_name(user.real_name) if mask_sensitive and user.real_name else user.real_name,
        'email': mask_email(user.email) if mask_sensitive else user.email,
        'phone': mask_phone(user.phone) if mask_sensitive and user.phone else user.phone,
        'avatar': user.avatar.url if user.avatar else None,
        'user_type': user.user_type,
        'is_active': user.is_active,
        'date_joined': user.date_joined,
        'last_login': user.last_login,
    }
    
    # 组织用户信息
    org_info = {
        'organization_permission': org_user.permission,
        'organization_status': org_user.status,
        'position': org_user.position,
        'department': org_user.department,
        'joined_at': org_user.created_at,
        'updated_at': org_user.updated_at,
    }
    
    return {
        'user_info': user_info,
        'org_info': org_info
    }


def validate_organization_member_update(data, current_user, target_org_user, organization):
    """
    验证组织成员更新数据
    
    Args:
        data: 更新数据
        current_user: 当前操作用户
        target_org_user: 目标组织用户对象
        organization: 组织对象
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # 检查操作权限
    if not can_manage_organization_member(current_user, target_org_user.user, organization):
        return False, "没有权限管理该用户"
    
    # 验证权限变更
    if 'permission' in data:
        new_permission = data['permission']
        
        # 不能将用户权限设置为比自己更高的级别
        from user.utils import get_organization_user_role
        current_user_role = get_organization_user_role(current_user, organization)
        if not current_user_role:
            return False, "当前用户不在该组织中"
        
        permission_hierarchy = {
            'owner': 4,
            'admin': 3,
            'member': 2,
            'pending': 1
        }
        
        current_level = permission_hierarchy.get(current_user_role['permission'], 0)
        new_level = permission_hierarchy.get(new_permission, 0)
        
        if new_level >= current_level:
            return False, "不能设置比自己更高或相等的权限级别"
        
        # owner 权限只能由 owner 设置
        if new_permission == 'owner' and current_user_role['permission'] != 'owner':
            return False, "只有组织所有者可以设置所有者权限"
    
    # 验证状态变更
    if 'status' in data:
        new_status = data['status']
        valid_statuses = ['pending', 'approved', 'rejected']
        
        if new_status not in valid_statuses:
            return False, f"无效的状态值: {new_status}"
    
    return True, ""