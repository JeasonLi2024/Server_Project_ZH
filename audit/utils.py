from django.db import transaction
from django.contrib.auth import get_user_model
from .models import RequirementAuditLog, OrganizationAuditLog
from organization.models import Organization
from project.models import Requirement

User = get_user_model()


def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """获取用户代理信息"""
    return request.META.get('HTTP_USER_AGENT', '')


def determine_operator_role(user, organization=None, requirement=None):
    """确定操作者角色"""
    if user.is_superuser:
        return 'admin'
    
    if organization:
        try:
            from organization.models import OrganizationUser
            org_user = OrganizationUser.objects.get(user=user, organization=organization)
            if org_user.permission == 'owner':
                return 'org_owner'
            elif org_user.permission == 'admin':
                return 'org_admin'
            else:
                return 'applicant'
        except OrganizationUser.DoesNotExist:
            pass
    
    if requirement:
        if requirement.publish_people.user == user:
            return 'publisher'
        try:
            from organization.models import OrganizationUser
            org_user = OrganizationUser.objects.get(
                user=user, 
                organization=requirement.organization
            )
            if org_user.permission == 'owner':
                return 'org_owner'
            elif org_user.permission == 'admin':
                return 'org_admin'
        except OrganizationUser.DoesNotExist:
            pass
    
    return 'applicant'


def log_requirement_audit(requirement, old_status, new_status, operator, 
                         action='submit', comment='', request=None, **extra_details):
    """记录需求审核历史"""
    try:
        # 获取请求信息
        ip_address = None
        user_agent = ''
        if request:
            ip_address = get_client_ip(request)
            user_agent = get_user_agent(request)
        
        # 确定操作者角色
        operator_role = determine_operator_role(operator, requirement=requirement)
        
        # 记录审核日志
        audit_log = RequirementAuditLog.log_status_change(
            requirement=requirement,
            old_status=old_status,
            new_status=new_status,
            operator=operator,
            action=action,
            comment=comment,
            operator_role=operator_role,
            ip_address=ip_address,
            user_agent=user_agent,
            **extra_details
        )
        
        return audit_log
        
    except Exception as e:
        # 记录日志失败不应该影响主要业务逻辑
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"记录需求审核日志失败: {e}")
        return None


def log_organization_audit(organization, old_status, new_status, operator, 
                          action='submit', comment='', submitted_materials=None, 
                          request=None, **extra_details):
    """记录组织认证审核历史"""
    try:
        # 获取请求信息
        ip_address = None
        user_agent = ''
        if request:
            ip_address = get_client_ip(request)
            user_agent = get_user_agent(request)
        
        # 确定操作者角色
        operator_role = determine_operator_role(operator, organization=organization)
        
        # 记录审核日志
        audit_log = OrganizationAuditLog.log_status_change(
            organization=organization,
            old_status=old_status,
            new_status=new_status,
            operator=operator,
            action=action,
            comment=comment,
            operator_role=operator_role,
            submitted_materials=submitted_materials,
            ip_address=ip_address,
            user_agent=user_agent,
            **extra_details
        )
        
        return audit_log
        
    except Exception as e:
        # 记录日志失败不应该影响主要业务逻辑
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"记录组织认证审核日志失败: {e}")
        return None


class AuditLogMixin:
    """审核日志混入类，为序列化器提供自动记录审核历史的功能"""
    
    def get_audit_action_from_status_change(self, old_status, new_status):
        """根据状态变更确定审核操作类型"""
        # 需求状态变更映射
        requirement_status_actions = {
            ('', 'under_review'): 'submit',
            ('under_review', 'in_progress'): 'approve',
            ('under_review', 'review_failed'): 'reject',
            ('review_failed', 'under_review'): 'resubmit',
        }
        
        # 组织状态变更映射
        organization_status_actions = {
            ('pending', 'under_review'): 'submit',
            ('under_review', 'verified'): 'approve',
            ('under_review', 'rejected'): 'reject',
            ('rejected', 'under_review'): 'resubmit',
        }
        
        # 首先尝试需求状态映射
        action = requirement_status_actions.get((old_status or '', new_status))
        if action:
            return action
            
        # 然后尝试组织状态映射
        action = organization_status_actions.get((old_status or '', new_status))
        if action:
            return action
            
        # 默认返回提交操作
        return 'submit'
    
    def log_requirement_status_change(self, requirement, old_status, new_status, 
                                    comment='', **extra_details):
        """记录需求状态变更"""
        if not hasattr(self, 'context') or 'request' not in self.context:
            return None
            
        request = self.context['request']
        operator = request.user
        
        # 确定操作类型
        action = self.get_audit_action_from_status_change(old_status, new_status)
        
        return log_requirement_audit(
            requirement=requirement,
            old_status=old_status,
            new_status=new_status,
            operator=operator,
            action=action,
            comment=comment,
            request=request,
            **extra_details
        )
    
    def log_organization_status_change(self, organization, old_status, new_status, 
                                     comment='', submitted_materials=None, **extra_details):
        """记录组织状态变更"""
        if not hasattr(self, 'context') or 'request' not in self.context:
            return None
            
        request = self.context['request']
        operator = request.user
        
        # 确定操作类型
        action = self.get_audit_action_from_status_change(old_status, new_status)
        
        return log_organization_audit(
            organization=organization,
            old_status=old_status,
            new_status=new_status,
            operator=operator,
            action=action,
            comment=comment,
            submitted_materials=submitted_materials,
            request=request,
            **extra_details
        )


def batch_log_requirement_audit(requirements_data, operator, action='batch_approve', 
                               comment='', request=None):
    """批量记录需求审核历史"""
    audit_logs = []
    
    try:
        with transaction.atomic():
            for req_data in requirements_data:
                requirement = req_data['requirement']
                old_status = req_data.get('old_status', '')
                new_status = req_data.get('new_status', '')
                
                audit_log = log_requirement_audit(
                    requirement=requirement,
                    old_status=old_status,
                    new_status=new_status,
                    operator=operator,
                    action=action,
                    comment=comment,
                    request=request
                )
                
                if audit_log:
                    audit_logs.append(audit_log)
                    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"批量记录需求审核日志失败: {e}")
    
    return audit_logs


def batch_log_organization_audit(organizations_data, operator, action='batch_approve', 
                                comment='', request=None):
    """批量记录组织认证审核历史"""
    audit_logs = []
    
    try:
        with transaction.atomic():
            for org_data in organizations_data:
                organization = org_data['organization']
                old_status = org_data.get('old_status', '')
                new_status = org_data.get('new_status', '')
                
                audit_log = log_organization_audit(
                    organization=organization,
                    old_status=old_status,
                    new_status=new_status,
                    operator=operator,
                    action=action,
                    comment=comment,
                    request=request
                )
                
                if audit_log:
                    audit_logs.append(audit_log)
                    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"批量记录组织认证审核日志失败: {e}")
    
    return audit_logs