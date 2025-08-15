from django.utils import timezone
from django.conf import settings
from django.core.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)


def get_organization_user_role(user, organization):
    """
    获取用户在组织中的角色信息
    
    Returns:
        dict: 包含权限、状态、职位、部门等信息
    """
    try:
        from .models import OrganizationUser
        
        org_user = OrganizationUser.objects.get(
            user=user, 
            organization=organization
        )
        
        return {
            'permission': org_user.permission,
            'status': org_user.status,
            'position': org_user.position,
            'department': org_user.department,
            'joined_at': org_user.created_at
        }
        
    except OrganizationUser.DoesNotExist:
        return None