"""
企业邀请码管理工具模块
包含邀请码的生成、验证、管理等功能
"""
import random
import string
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from .models import OrganizationInvitationCode
from organization.models import Organization
import logging

logger = logging.getLogger(__name__)

# 邀请码默认有效期（30天）
INVITATION_CODE_EXPIRE_DAYS = 30


def generate_invitation_code(length=16):
    """生成邀请码
    
    Args:
        length (int): 邀请码长度，默认16位
        
    Returns:
        str: 生成的邀请码
    """
    # 使用大小写字母和数字，避免容易混淆的字符
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    chars = chars.replace('0', '').replace('O', '').replace('l', '').replace('I', '').replace('1', '')
    
    while True:
        code = ''.join(random.choices(chars, k=length))
        # 确保生成的邀请码不重复
        if not OrganizationInvitationCode.objects.filter(code=code).exists():
            return code


def create_invitation_code(organization_id, created_by_user, expire_days=None, max_uses=None):
    """为组织创建邀请码
    
    Args:
        organization_id (int): 组织ID
        created_by_user (User): 创建者用户对象
        expire_days (int): 过期天数，默认30天
        max_uses (int): 最大使用次数，默认100次
        
    Returns:
        tuple: (success: bool, invitation_code: OrganizationInvitationCode or None, message: str)
    """
    try:
        with transaction.atomic():
            # 获取组织
            try:
                organization = Organization.objects.get(id=organization_id)
            except Organization.DoesNotExist:
                return False, None, "组织不存在"
            
            # 检查用户权限（只有创建者和管理员可以生成邀请码）
            org_user = getattr(created_by_user, 'organization_profile', None)
            if not org_user or org_user.organization_id != organization_id:
                return False, None, "您不属于该组织"
            
            if org_user.permission not in ['owner', 'admin']:
                return False, None, "权限不足，只有组织创建者和管理员可以生成邀请码"
            
            # 过期现有的有效邀请码（确保一个组织同时只有一个有效邀请码）
            existing_codes = OrganizationInvitationCode.objects.filter(
                organization=organization,
                status='active'
            )
            for code in existing_codes:
                code.expire_code()
                logger.info(f"过期旧邀请码: {code.code}")
            
            # 生成新邀请码
            code = generate_invitation_code()
            expire_days = expire_days or INVITATION_CODE_EXPIRE_DAYS
            max_uses = max_uses or 100  # 默认100次
            expires_at = timezone.now() + timedelta(days=expire_days)
            
            invitation_code = OrganizationInvitationCode.objects.create(
                organization=organization,
                code=code,
                created_by=created_by_user,
                expires_at=expires_at,
                max_uses=max_uses
            )
            
            logger.info(f"创建邀请码成功: {organization.name} - {code} - 创建者: {created_by_user.username}")
            return True, invitation_code, "邀请码创建成功"
            
    except Exception as e:
        logger.error(f"创建邀请码失败: {organization_id} - {created_by_user.username} - {str(e)}")
        return False, None, f"创建邀请码失败: {str(e)}"


def validate_invitation_code(code):
    """验证邀请码
    
    Args:
        code (str): 邀请码
        
    Returns:
        tuple: (is_valid: bool, invitation_code: OrganizationInvitationCode or None, message: str)
    """
    try:
        invitation_code = OrganizationInvitationCode.objects.select_related('organization').get(code=code)
        
        if not invitation_code.can_be_used():
            if invitation_code.is_expired():
                return False, invitation_code, "邀请码已过期"
            elif invitation_code.status != 'active':
                return False, invitation_code, f"邀请码状态异常: {invitation_code.get_status_display()}"
            elif invitation_code.max_uses > 0 and invitation_code.used_count >= invitation_code.max_uses:
                return False, invitation_code, "邀请码使用次数已达上限"
            else:
                return False, invitation_code, "邀请码无效"
        
        return True, invitation_code, "邀请码有效"
        
    except OrganizationInvitationCode.DoesNotExist:
        return False, None, "邀请码不存在"
    except Exception as e:
        logger.error(f"验证邀请码失败: {code} - {str(e)}")
        return False, None, f"验证邀请码失败: {str(e)}"


def use_invitation_code(code, user=None):
    """使用邀请码（消费）
    
    Args:
        code (str): 邀请码
        user (User, optional): 使用邀请码的用户，用于发送通知
        
    Returns:
        tuple: (success: bool, organization: Organization or None, message: str)
    """
    try:
        with transaction.atomic():
            is_valid, invitation_code, message = validate_invitation_code(code)
            
            if not is_valid:
                return False, None, message
            
            # 使用邀请码
            if invitation_code.use_code():
                logger.info(f"使用邀请码成功: {code} - 组织: {invitation_code.organization.name}")
                
                # 如果提供了用户信息，同步发送使用通知
                if user:
                    try:
                        _send_invitation_code_used_notification_sync(invitation_code, user)
                        logger.info(f"邀请码使用通知已发送: {code} -> 创建者: {invitation_code.created_by.username}, 用户: {user.username}")
                    except Exception as e:
                        logger.error(f"发送邀请码使用通知失败: {str(e)}")
                        # 通知发送失败不影响邀请码使用成功
                
                return True, invitation_code.organization, "邀请码使用成功"
            else:
                return False, None, "邀请码使用失败"
                
    except Exception as e:
        logger.error(f"使用邀请码失败: {code} - {str(e)}")
        return False, None, f"使用邀请码失败: {str(e)}"


def _send_invitation_code_used_notification_sync(invitation_code, user):
    """
    同步发送邀请码使用通知
    
    Args:
        invitation_code: 邀请码对象
        user: 使用邀请码的用户对象
    """
    try:
        from notification.services import notification_service
        
        # 计算剩余使用次数
        remaining_uses = invitation_code.max_uses - invitation_code.used_count if invitation_code.max_uses else None
        
        # 准备模板变量
        template_vars = {
            'invitation_code_last_4': invitation_code.code[-4:],  # 只保留后4位
            'organization_name': invitation_code.organization.name,
            'created_by_name': invitation_code.created_by.get_full_name() or invitation_code.created_by.username,
            'user_name': user.get_full_name() or user.username,
            'user_email': user.email,
            'used_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'used_count': invitation_code.used_count,
            'max_uses': invitation_code.max_uses,
            'remaining_uses': remaining_uses
        }
        
        # 发送通知给邀请码创建者
        notification = notification_service.create_and_send_notification(
            recipient=invitation_code.created_by,
            notification_type_code='org_invitation_code_used',
            template_vars=template_vars,
            strategies=['websocket', 'email']  # 同时发送WebSocket和邮件通知
        )
        
        if notification:
            logger.info(
                f"邀请码使用通知已发送: {invitation_code.code} -> {invitation_code.created_by.username} (用户: {user.username})"
            )
            return True
        else:
            logger.warning(f"邀请码使用通知发送失败: {invitation_code.code}")
            return False
        
    except Exception as e:
        logger.error(f"发送邀请码使用通知时发生错误: {str(e)}")
        raise e


def get_organization_invitation_code(organization_id):
    """获取组织的当前有效邀请码
    
    Args:
        organization_id (int): 组织ID
        
    Returns:
        OrganizationInvitationCode or None: 有效的邀请码对象，如果没有则返回None
    """
    try:
        return OrganizationInvitationCode.objects.filter(
            organization_id=organization_id,
            status='active'
        ).first()
    except Exception as e:
        logger.error(f"获取组织邀请码失败: {organization_id} - {str(e)}")
        return None


def get_invitation_code_info(code):
    """获取邀请码详细信息
    
    Args:
        code (str): 邀请码
        
    Returns:
        dict or None: 邀请码信息字典，如果不存在则返回None
    """
    try:
        invitation_code = OrganizationInvitationCode.objects.select_related(
            'organization', 'created_by'
        ).get(code=code)
        
        return {
            'code': invitation_code.code,
            'organization': {
                'id': invitation_code.organization.id,
                'name': invitation_code.organization.name,
                'type': invitation_code.organization.organization_type,
                'type_display': invitation_code.organization.get_organization_type_display(),
            },
            'status': invitation_code.status,
            'status_display': invitation_code.get_status_display(),
            'created_by': {
                'id': invitation_code.created_by.id,
                'username': invitation_code.created_by.username,
                'real_name': invitation_code.created_by.real_name,
            },
            'created_at': invitation_code.created_at.isoformat(),
            'expires_at': invitation_code.expires_at.isoformat(),
            'used_count': invitation_code.used_count,
            'max_uses': invitation_code.max_uses,
            'is_expired': invitation_code.is_expired(),
            'is_valid': invitation_code.is_valid(),
            'can_be_used': invitation_code.can_be_used(),
            'ttl_seconds': int((invitation_code.expires_at - timezone.now()).total_seconds()) if not invitation_code.is_expired() else 0
        }
        
    except OrganizationInvitationCode.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"获取邀请码信息失败: {code} - {str(e)}")
        return None


def clean_expired_invitation_codes():
    """清理过期的邀请码
    
    Returns:
        int: 清理的邀请码数量
    """
    try:
        # 将过期但状态仍为active的邀请码标记为expired
        expired_count = OrganizationInvitationCode.objects.filter(
            status='active',
            expires_at__lt=timezone.now()
        ).update(status='expired')
        
        logger.info(f"清理过期邀请码: {expired_count} 条")
        return expired_count
        
    except Exception as e:
        logger.error(f"清理过期邀请码失败: {str(e)}")
        return 0


def get_organization_invitation_history(organization_id, limit=10):
    """获取组织的邀请码历史记录
    
    Args:
        organization_id (int): 组织ID
        limit (int): 返回记录数量限制
        
    Returns:
        list: 邀请码历史记录列表
    """
    try:
        invitation_codes = OrganizationInvitationCode.objects.filter(
            organization_id=organization_id
        ).select_related('created_by').order_by('-created_at')[:limit]
        
        return [
            {
                'id': code.id,
                'code': code.code,
                'status': code.status,
                'status_display': code.get_status_display(),
                'created_by': {
                    'id': code.created_by.id,
                    'username': code.created_by.username,
                    'real_name': code.created_by.real_name,
                },
                'created_at': code.created_at.isoformat(),
                'expires_at': code.expires_at.isoformat(),
                'used_count': code.used_count,
                'max_uses': code.max_uses,
                'is_expired': code.is_expired(),
            }
            for code in invitation_codes
        ]
        
    except Exception as e:
        logger.error(f"获取组织邀请码历史失败: {organization_id} - {str(e)}")
        return []