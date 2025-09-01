import logging
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.db import transaction
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Q

from .models import Organization, OrganizationOperationLog, OrganizationConfig
from user.models import OrganizationUser
from .serializers import (
    OrganizationSerializer, OrganizationMemberSerializer, OrganizationMemberUpdateSerializer,
    OrganizationMemberListSerializer, OrganizationOperationLogSerializer,
    OrganizationUpdateSerializer, OrganizationLogoUploadSerializer, OrganizationConfigSerializer,
    OrganizationVerificationMaterialsSerializer
)
from .utils import (
    check_organization_permission, log_organization_operation,
    can_manage_organization_member,
    get_organization_member_display_data,
    validate_organization_member_update
)
from user.utils import get_organization_user_role
from common_utils import APIResponse, format_validation_errors, build_media_url, build_media_urls_list

logger = logging.getLogger(__name__)





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_organizations(request):
    """搜索组织（支持分页）"""
    try:
        from common_utils import paginate_queryset
        
        query = request.GET.get('search', '').strip()  # 支持search参数
        if not query:
            query = request.GET.get('q', '').strip()  # 兼容q参数
        
        organization_type = request.GET.get('organization_type', '')  # 支持organization_type参数
        if not organization_type:
            organization_type = request.GET.get('type', '')  # 兼容type参数
        
        status = request.GET.get('status', '')  # 支持状态过滤
        
        # 如果没有查询关键词，返回所有组织
        if query and len(query) < 2:
            return APIResponse.error('搜索关键词至少需要2个字符', code=400)
        
        # 构建查询条件 - 返回所有组织，不再限制只有已认证的组织
        queryset = Organization.objects.all()
        
        # 按组织类型过滤
        if organization_type in ['enterprise', 'university', 'other']:
            queryset = queryset.filter(organization_type=organization_type)
        
        # 按状态过滤
        if status in ['pending', 'verified', 'rejected', 'suspended']:
            queryset = queryset.filter(status=status)
        
        # 如果有搜索关键词，按名称、代码、行业/学科搜索
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(code__icontains=query) |
                Q(industry_or_discipline__icontains=query)
            )
        
        # 按ID排序
        queryset = queryset.order_by('id')
        
        # 使用分页功能
        paginated_data = paginate_queryset(request, queryset, default_page_size=20)
        page_data = paginated_data['page_data']
        pagination_info = paginated_data['pagination_info']
        
        # 构建返回数据
        results = []
        for org in page_data:
            results.append({
                'id': str(org.id),
                'name': org.name,
                'organization_type': org.organization_type,
                'organization_type_display': org.get_organization_type_display(),
                'type_display': org.type_display,
                'industry_or_discipline': org.industry_or_discipline,
                'scale': org.scale,
                'address': org.address,
                'status': org.status,
                'status_display': org.get_status_display(),
                'logo': build_media_url(org.logo, request)
            })
        
        # 返回分页数据
        response_data = {
            'results': results,
            'pagination': pagination_info,
            'query': query,  # 添加查询关键词到响应中
            'filters': {
                'organization_type': organization_type,
                'status': status
            }
        }
        
        return APIResponse.success(response_data)
        
    except Exception as e:
        logger.error(f"搜索组织失败: {str(e)}")
        return APIResponse.server_error('搜索失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organization_detail(request, organization_id):
    """获取组织详细信息"""
    try:
        # 获取组织信息
        try:
            organization = Organization.objects.get(
                id=organization_id,
                # status='verified'  # 只显示已认证的组织
            )
        except Organization.DoesNotExist:
            return APIResponse.not_found('组织不存在')
        
        # 构建基础信息
        org_data = {
            'id': str(organization.id),
            'name': organization.name,
            'code': organization.code,
            'organization_type': organization.organization_type,
            'organization_type_display': organization.get_organization_type_display(),
            'type_display': organization.type_display,
            'industry_or_discipline': organization.industry_or_discipline,
            'scale': organization.scale,
            'address': organization.address,
            'postal_code': organization.postal_code,
            'description': organization.description,
            'website': organization.website,
            'established_date': organization.established_date,
            'logo': build_media_url(organization.logo, request),
            'verification_image': build_media_urls_list(organization.verification_image, request),
            'status': organization.status,
            'status_display': organization.get_status_display(),
            'created_at': organization.created_at,
            'updated_at': organization.updated_at,
            'verified_at': organization.verified_at,
        }
        
        # 添加联系信息（公开信息）
        contact_info = {
            'contact_person': organization.contact_person,
            'contact_position': organization.contact_position,
            'contact_phone': organization.contact_phone,
            'contact_email': organization.contact_email,
        }
        
        # 添加领导信息
        leader_info = {
            'leader_name': organization.leader_name,
            'leader_title': organization.leader_title,
        }
        
        # 根据组织类型添加特定信息
        if organization.organization_type == 'enterprise':
            org_data['enterprise_type'] = organization.enterprise_type
            org_data['enterprise_type_display'] = organization.get_enterprise_type_display() if organization.enterprise_type else None
        elif organization.organization_type == 'university':
            org_data['university_type'] = organization.university_type
            org_data['university_type_display'] = organization.get_university_type_display() if organization.university_type else None
        elif organization.organization_type == 'other':
            org_data['other_type'] = organization.other_type
            org_data['other_type_display'] = organization.get_other_type_display() if organization.other_type else None
            org_data['organization_nature'] = organization.organization_nature
            org_data['organization_nature_display'] = organization.get_organization_nature_display() if organization.organization_nature else None
            org_data['business_scope'] = organization.business_scope
            org_data['regulatory_authority'] = organization.regulatory_authority
            org_data['license_info'] = organization.license_info
            org_data['service_target'] = organization.service_target
            org_data['service_target_display'] = organization.get_service_target_display() if organization.service_target else None
        
        # 获取成员统计信息（如果用户有权限）
        member_stats = None
        if request.user.is_authenticated:
            try:
                # 检查当前用户是否是该组织成员
                org_user = OrganizationUser.objects.get(
                    user=request.user, 
                    organization=organization,
                    status='approved'
                )
                
                # 如果是成员，提供成员统计信息
                total_members = OrganizationUser.objects.filter(
                    organization=organization,
                    status='approved'
                ).count()
                
                pending_members = OrganizationUser.objects.filter(
                    organization=organization,
                    status='pending'
                ).count()
                
                # 统计管理员人数（包括创建者和管理员）
                admins = OrganizationUser.objects.filter(
                    organization=organization,
                    permission__in=['owner', 'admin'],
                    status='approved'
                ).count()
                
                member_stats = {
                    'total_members': total_members,
                    'pending_members': pending_members,
                    'admins': admins,
                    'user_role': org_user.permission,
                    'user_role_display': org_user.get_permission_display(),
                    'user_status': org_user.status,
                    'user_status_display': org_user.get_status_display(),
                    'user_position': org_user.position,
                    'user_department': org_user.department,
                }
                
            except OrganizationUser.DoesNotExist:
                # 用户不是该组织成员，不提供内部统计信息
                pass
        
        # 组装返回数据
        response_data = {
            'organization': org_data,
            'contact_info': contact_info,
            'leader_info': leader_info,
        }
        
        if member_stats:
            response_data['member_stats'] = member_stats
        
        return APIResponse.success(response_data)
        
    except Exception as e:
        logger.error(f"获取组织详细信息失败: {str(e)}")
        return APIResponse.server_error('获取组织信息失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organization_members(request):
    """获取组织成员列表"""
    try:
        user = request.user
        
        # 检查用户是否属于某个组织
        try:
            org_user = OrganizationUser.objects.select_related('organization').get(
                user=user, status='approved'
            )
            organization = org_user.organization
        except OrganizationUser.DoesNotExist:
            return APIResponse.error('您不属于任何组织', code=403)
        
        # 检查权限 - 至少需要是成员
        if not check_organization_permission(user, organization, 'member'):
            return APIResponse.error('没有权限查看成员列表', code=403)
        
        # 获取查询参数
        status_filter = request.GET.get('status', '')
        permission_filter = request.GET.get('permission', '')
        search = request.GET.get('search', '')
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        # 构建查询
        queryset = OrganizationUser.objects.filter(
            organization=organization
        ).select_related('user').order_by('-created_at')
        
        # 应用过滤器
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if permission_filter:
            queryset = queryset.filter(permission=permission_filter)
        
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(user__real_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(position__icontains=search) |
                Q(department__icontains=search)
            )
        
        # 分页
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        # 序列化数据
        serializer = OrganizationMemberListSerializer(
            page_obj.object_list, 
            many=True, 
            context={'request': request}
        )
        
        return APIResponse.success({
            'members': serializer.data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'page_size': page_size,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        })
        
    except Exception as e:
        logger.error(f"获取组织成员列表失败: {str(e)}")
        return APIResponse.server_error('获取成员列表失败，请稍后重试')


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_member(request, member_id):
    """更新组织成员信息"""
    try:
        user = request.user
        
        # 获取目标成员
        try:
            target_member = OrganizationUser.objects.select_related(
                'user', 'organization'
            ).get(id=member_id)
        except OrganizationUser.DoesNotExist:
            return APIResponse.not_found('成员不存在')
        
        organization = target_member.organization
        
        # 检查当前用户是否有管理权限
        if not can_manage_organization_member(user, target_member.user, organization):
            return APIResponse.error('没有权限管理该成员', code=403)
        
        # 序列化和验证数据
        serializer = OrganizationMemberUpdateSerializer(
            target_member, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return APIResponse.validation_error(
                format_validation_errors(serializer.errors)
            )
        
        # 保存更新（日志记录在serializer中处理）
        updated_member = serializer.save()
        
        # 返回更新后的成员信息
        response_serializer = OrganizationMemberListSerializer(
            updated_member, 
            context={'request': request}
        )
        
        return APIResponse.success(
            response_serializer.data, 
            '成员信息更新成功'
        )
        
    except Exception as e:
        logger.error(f"更新成员信息失败: {str(e)}")
        return APIResponse.server_error('更新成员信息失败，请稍后重试')


def _get_operation_by_permission_change(old_permission, new_permission):
    """
    根据权限变化自动确定操作日志类型
    
    Args:
        old_permission: 原权限
        new_permission: 新权限
        
    Returns:
        str: 操作类型
    """
    # 权限变化映射表
    permission_change_map = {
        ('pending', 'member'): 'permission_grant_member',
        ('pending', 'admin'): 'permission_grant_admin',
        ('member', 'admin'): 'permission_grant_admin',
        ('member', 'pending'): 'permission_revoke_member',
        ('admin', 'member'): 'permission_revoke_admin',
        ('admin', 'pending'): 'permission_revoke_admin',
    }
    
    # 获取对应的操作类型，如果没有匹配则使用通用的权限更新
    return permission_change_map.get((old_permission, new_permission), 'permission_grant_member')


def _get_operation_by_status_change(old_status, new_status):
    """
    根据状态变化自动确定操作日志类型
    
    Args:
        old_status: 原状态
        new_status: 新状态
        
    Returns:
        str: 操作类型
    """
    # 状态变化映射表
    status_change_map = {
        ('pending', 'approved'): 'member_approve',      # 待审核 -> 已通过 = 审核通过
        ('pending', 'rejected'): 'member_reject',       # 待审核 -> 已拒绝 = 审核拒绝
        ('approved', 'pending'): 'member_suspend',      # 已通过 -> 待审核 = 暂停/冻结
        ('approved', 'rejected'): 'member_reject',      # 已通过 -> 已拒绝 = 拒绝
        ('rejected', 'approved'): 'member_approve',     # 已拒绝 -> 已通过 = 重新审核通过
        ('rejected', 'pending'): 'member_reactivate',   # 已拒绝 -> 待审核 = 重新激活待审核
    }
    
    # 获取对应的操作类型，如果没有匹配则使用通用的状态更新
    return status_change_map.get((old_status, new_status), 'member_status_update')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_update_members(request):
    """批量更新成员状态、权限、职位和部门"""
    try:
        user = request.user
        member_ids = request.data.get('member_ids', [])
        
        # 支持的更新字段
        status = request.data.get('status', '')  # 状态：pending, approved, rejected
        permission = request.data.get('permission', '')  # 权限：pending, member, admin, owner
        position = request.data.get('position')  # 职位
        department = request.data.get('department')  # 部门
        
        if not member_ids:
            return APIResponse.error('请提供成员ID列表', code=400)
        
        if not any([status, permission, position is not None, department is not None]):
            return APIResponse.error('请提供至少一个要更新的字段（status、permission、position、department）', code=400)
        
        # 验证状态和权限值
        if status:
            valid_statuses = ['pending', 'approved', 'rejected']
            if status not in valid_statuses:
                return APIResponse.error(f'无效的状态值: {status}', code=400)
        
        if permission:
            valid_permissions = ['pending', 'member', 'admin', 'owner']
            if permission not in valid_permissions:
                return APIResponse.error(f'无效的权限值: {permission}', code=400)
        
        # 获取成员列表
        members = OrganizationUser.objects.filter(
            id__in=member_ids
        ).select_related('user', 'organization')
        
        if not members.exists():
            return APIResponse.error('未找到指定的成员', code=404)
        
        # 检查权限（所有成员必须属于同一组织，且当前用户有管理权限）
        organization = members.first().organization
        for member in members:
            if member.organization != organization:
                return APIResponse.error('成员不属于同一组织', code=400)
            
            # 只对状态和权限变更进行权限检查
            if status or permission:
                if not can_manage_organization_member(user, member.user, organization):
                    return APIResponse.error(f'没有权限管理成员 {member.user.username}', code=403)
        
        # 执行批量操作
        updated_count = 0
        
        for member in members:
            old_status = member.status
            old_permission = member.permission
            status_changed = False
            permission_changed = False
            other_fields_changed = False
            
            # 更新状态
            if status and member.status != status:
                member.status = status
                status_changed = True
            
            # 更新权限
            if permission and member.permission != permission:
                member.permission = permission
                permission_changed = True
            
            # 更新职位
            if position is not None and member.position != position:
                member.position = position
                other_fields_changed = True
            
            # 更新部门
            if department is not None and member.department != department:
                member.department = department
                other_fields_changed = True
            
            # 如果有变化则保存
            if status_changed or permission_changed or other_fields_changed:
                member.save()
                updated_count += 1
                
                # 记录状态变化日志
                if status_changed:
                    operation_type = _get_operation_by_status_change(old_status, member.status)
                    
                    log_organization_operation(
                        user=user,
                        organization=organization,
                        operation=operation_type,
                        target_user=member.user,
                        details={
                            'old_status': old_status,
                            'new_status': member.status,
                            'batch_operation': True
                        }
                    )
                
                # 记录权限变化日志
                if permission_changed:
                    operation_type = _get_operation_by_permission_change(old_permission, member.permission)
                    
                    log_organization_operation(
                        user=user,
                        organization=organization,
                        operation=operation_type,
                        target_user=member.user,
                        details={
                            'old_permission': old_permission,
                            'new_permission': member.permission,
                            'batch_operation': True
                        }
                    )
        
        return APIResponse.success({
            'updated_count': updated_count,
            'total_count': len(member_ids)
        }, f'批量更新操作完成，共更新{updated_count}个成员')
        
    except Exception as e:
        logger.error(f"批量更新成员失败: {str(e)}")
        return APIResponse.server_error('批量操作失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organization_operation_logs(request):
    """获取组织操作日志"""
    try:
        user = request.user
        
        # 检查用户是否属于某个组织且有管理权限
        try:
            org_user = OrganizationUser.objects.select_related('organization').get(
                user=user, status='approved'
            )
            organization = org_user.organization
        except OrganizationUser.DoesNotExist:
            return APIResponse.error('您不属于任何组织', code=403)
        
        if not check_organization_permission(user, organization, 'admin'):
            return APIResponse.error('没有权限查看操作日志', code=403)
        
        # 获取查询参数
        operation_filter = request.GET.get('operation', '')
        operator_filter = request.GET.get('operator', '')
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        # 构建查询
        queryset = OrganizationOperationLog.objects.filter(
            organization=organization
        ).select_related('operator', 'target_user').order_by('-created_at')
        
        # 应用过滤器
        if operation_filter:
            queryset = queryset.filter(operation=operation_filter)
        
        if operator_filter:
            queryset = queryset.filter(operator__username__icontains=operator_filter)
        
        # 分页
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        # 序列化数据
        serializer = OrganizationOperationLogSerializer(
            page_obj.object_list, 
            many=True
        )
        
        return APIResponse.success({
            'logs': serializer.data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'page_size': page_size,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        })
        
    except Exception as e:
        logger.error(f"获取操作日志失败: {str(e)}")
        return APIResponse.server_error('获取操作日志失败，请稍后重试')


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def organization_config(request):
    """获取或更新组织配置"""
    try:
        user = request.user
        
        # 检查用户是否属于某个组织且有所有者权限
        try:
            org_user = OrganizationUser.objects.select_related('organization').get(
                user=user, status='approved'
            )
            organization = org_user.organization
        except OrganizationUser.DoesNotExist:
            return APIResponse.error('您不属于任何组织', code=403)
        
        if not check_organization_permission(user, organization, 'owner'):
            return APIResponse.error('只有组织所有者可以管理配置', code=403)
        
        # 获取或创建配置
        config, created = OrganizationConfig.objects.get_or_create(
            organization=organization
        )
        
        if request.method == 'GET':
            # 获取配置
            serializer = OrganizationConfigSerializer(config)
            return APIResponse.success(serializer.data)
        
        elif request.method == 'PUT':
            # 更新配置
            serializer = OrganizationConfigSerializer(
                config, 
                data=request.data, 
                partial=True
            )
            
            if not serializer.is_valid():
                return APIResponse.validation_error(
                    format_validation_errors(serializer.errors)
                )
            
            updated_config = serializer.save()
            
            # 记录操作日志
            log_organization_operation(
                user=user,
                organization=organization,
                operation='organization_config_update',
                details={'config_updated': request.data}
            )
            
            return APIResponse.success(
                OrganizationConfigSerializer(updated_config).data,
                '组织配置更新成功'
            )
        
    except Exception as e:
        logger.error(f"组织配置操作失败: {str(e)}")
        return APIResponse.server_error('操作失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verification_status(request):
    """组织认证状态查询接口"""
    try:
        user = request.user
        
        if user.user_type != 'organization':
            return APIResponse.success({
                'user_type': user.user_type,
                'needs_verification': False,
                'message': '非组织用户无需认证'
            })
        
        try:
            org_user = user.organization_profile
            organization = org_user.organization
            
            needs_verification = org_user.status == 'pending'
            
            return APIResponse.success({
                'user_type': user.user_type,
                'needs_verification': needs_verification,
                'user_status': org_user.status,
                'user_status_display': org_user.get_status_display(),
                'organization_status': organization.status,
                'organization_status_display': organization.get_status_display(),
                'organization_name': organization.name,
                'organization_type': organization.organization_type,
                'organization_id': organization.id,
                'is_admin': org_user.permission == 'admin',
                'verification_progress': {
                    'basic_info_completed': bool(organization.name and organization.organization_type),
                    'contact_info_completed': bool(organization.contact_phone and organization.contact_email),
                    'address_completed': bool(organization.address),
                    'leader_info_completed': bool(organization.leader_name),
                    'code_completed': bool(organization.code)
                }
            })
            
        except AttributeError:
            return APIResponse.error('用户没有组织资料', code=400)
        
    except Exception as e:
        logger.error(f"获取认证状态失败: {str(e)}")
        return APIResponse.server_error('获取认证状态失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_status(request):
    """组织用户状态查询接口"""
    try:
        user = request.user
        
        # 获取用户基本状态
        user_status = 'active' if user.is_active else 'inactive'
        user_status_display = '正常' if user.is_active else '已停用'
        
        # 获取组织相关信息
        organization_info = None
        organization_membership = None
        
        if user.user_type == 'organization':
            try:
                # 获取用户所属的组织
                org_user = user.organization_profile
                organization_info = {
                    'id': org_user.organization.id,
                    'name': org_user.organization.name,
                    'status': org_user.organization.status,
                    'status_display': org_user.organization.get_status_display(),
                    'type': org_user.organization.organization_type,
                }
                organization_membership = {
                    'permission': org_user.permission,
                    'permission_display': org_user.get_permission_display(),
                    'status': org_user.status,
                    'status_display': org_user.get_status_display(),
                    'position': org_user.position,
                    'department': org_user.department,
                    'joined_at': org_user.created_at,
                }
            except AttributeError:
                pass
        
        data = {
            'user_id': user.id,
            'username': user.username,
            'user_type': user.user_type,
            'user_type_display': user.get_user_type_display(),
            'user_status': user_status,
            'user_status_display': user_status_display,
            'is_active': user.is_active,
            'organization_info': organization_info,
            'organization_membership': organization_membership,
        }
        
        return APIResponse.success(data)
        
    except Exception as e:
        logger.error(f"获取用户状态失败: {str(e)}")
        return APIResponse.server_error('获取用户状态失败，请稍后重试')


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_organization(request):
    """更新组织信息"""
    try:
        user = request.user
        
        # 检查用户是否属于组织
        try:
            org_user = OrganizationUser.objects.select_related('organization').get(
                user=user, 
                status='approved'
            )
            organization = org_user.organization
        except OrganizationUser.DoesNotExist:
            return APIResponse.error('您不属于任何组织', code=403)
        
        # 检查权限 - 只有创建者和管理员可以修改组织信息
        if org_user.permission not in ['owner', 'admin']:
            return APIResponse.error('只有组织创建者和管理员可以修改组织信息', code=403)
        
        # 序列化和验证数据
        serializer = OrganizationUpdateSerializer(
            organization, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return APIResponse.validation_error(
                format_validation_errors(serializer.errors)
            )
        
        # 保存更新
        old_data = {
            'name': organization.name,
            'leader_name': organization.leader_name,
            'contact_phone': organization.contact_phone,
            'contact_email': organization.contact_email,
            'address': organization.address,
            'description': organization.description,
        }
        
        updated_organization = serializer.save()
        
        # 记录操作日志
        changes = {}
        for field in serializer.validated_data:
            old_value = old_data.get(field)
            new_value = getattr(updated_organization, field)
            if old_value != new_value:
                changes[field] = {'old': old_value, 'new': new_value}
        
        if changes:
            log_organization_operation(
                user=user,
                organization=organization,
                operation='organization_update',
                details={'changes': changes}
            )
        
        # 返回更新后的组织信息
        response_serializer = OrganizationSerializer(
            updated_organization, 
            context={'request': request}
        )
        
        return APIResponse.success(
            response_serializer.data, 
            '组织信息更新成功'
        )
        
    except Exception as e:
        logger.error(f"更新组织信息失败: {str(e)}")
        return APIResponse.server_error('更新组织信息失败，请稍后重试')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_organization_logo(request):
    """上传组织logo"""
    try:
        user = request.user
        
        # 检查用户是否属于组织
        try:
            org_user = OrganizationUser.objects.select_related('organization').get(
                user=user, 
                status='approved'
            )
            organization = org_user.organization
        except OrganizationUser.DoesNotExist:
            return APIResponse.error('您不属于任何组织', code=403)
        
        # 检查权限 - 只有创建者和管理员可以上传logo
        if org_user.permission not in ['owner', 'admin']:
            return APIResponse.error('只有组织创建者和管理员可以上传组织logo', code=403)
        
        # 检查是否有文件上传
        if 'logo' not in request.FILES:
            return APIResponse.error('请选择要上传的logo文件', code=400)
        
        # 序列化和验证数据
        serializer = OrganizationLogoUploadSerializer(
            organization, 
            data=request.FILES, 
            partial=True,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return APIResponse.validation_error(
                format_validation_errors(serializer.errors)
            )
        
        # 保存旧logo路径（用于删除旧文件）
        old_logo = organization.logo
        
        # 保存新logo
        updated_organization = serializer.save()
        
        # 删除旧logo文件
        if old_logo and old_logo != updated_organization.logo:
            try:
                import os
                if os.path.exists(old_logo.path):
                    os.remove(old_logo.path)
            except Exception as e:
                logger.warning(f"删除旧logo文件失败: {str(e)}")
        
        # 记录操作日志
        log_organization_operation(
            user=user,
            organization=organization,
            operation='organization_update',
            details={
                'action': 'logo_upload',
                'logo': updated_organization.logo.url if updated_organization.logo else None
            }
        )
        
        # 返回新logo信息
        return APIResponse.success({
            'logo': build_media_url(updated_organization.logo, request),
            'message': '组织logo上传成功'
        })
        
    except Exception as e:
        logger.error(f"上传组织logo失败: {str(e)}")
        return APIResponse.server_error('上传组织logo失败，请稍后重试')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_verification_materials_with_images(request):
    """提交组织认证材料（包含文本信息和图片） - 支持form-data格式"""
    try:
        user = request.user
        logger.info(f"用户 {user.username} 开始提交认证材料和图片")
        
        # 检查用户类型
        if user.user_type != 'organization':
            logger.warning(f"用户 {user.username} 不是组织用户，类型: {user.user_type}")
            return APIResponse.error('只有组织用户可以提交认证材料', code=403)
        
        # 获取用户的组织资料
        try:
            org_user = user.organization_profile
            logger.info(f"找到组织资料: {org_user}")
        except AttributeError as e:
            logger.error(f"用户 {user.username} 没有组织资料: {e}")
            return APIResponse.error('用户没有组织资料', code=400)
        
        # 检查用户权限，只有owner可以提交认证材料
        if org_user.permission != 'owner':
            return APIResponse.error('只有组织所有者可以提交认证材料', code=403)
               
        organization = org_user.organization
        
        # 检查是否有认证图片上传
        has_files = any(f'verification_image_{i}' in request.FILES for i in range(1, 6))
        if not has_files:
            return APIResponse.error('请至少上传一张认证图片', code=400)
        
        # 合并文本数据和文件数据
        combined_data = request.data.copy()
        combined_data.update(request.FILES)
        
        # 序列化和验证数据
        serializer = OrganizationVerificationMaterialsSerializer(
            organization,
            data=combined_data,
            partial=True,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return APIResponse.validation_error(
                format_validation_errors(serializer.errors)
            )
        
        # 保存认证材料和图片
        with transaction.atomic():
            updated_organization = serializer.save()
                      
            # 记录操作日志
            # 过滤掉文件对象，只保留可序列化的数据
            serializable_data = {}
            for key, value in request.data.items():
                if not hasattr(value, 'read'):  # 排除文件对象
                    serializable_data[key] = value
            
            log_organization_operation(
                user=user,
                organization=organization,
                operation='verification_materials_submit',
                details={
                    'action': 'verification_materials_and_images_submitted',
                    'verification_materials_submitted': serializable_data,
                    'image_count': len(updated_organization.verification_image) if updated_organization.verification_image else 0,
                    'images': updated_organization.verification_image
                }
            )
        
        # 构建完整的图片URL
        verification_images_urls = build_media_urls_list(updated_organization.verification_image, request)
        
        return APIResponse.success({
            'message': '认证材料和图片提交成功，请等待审核',
            'organization_status': updated_organization.status,
            'verification_image': verification_images_urls,
            'image_count': len(verification_images_urls)
        })
        
    except Exception as e:
        logger.error(f"提交认证材料失败: {str(e)}")
        return APIResponse.server_error('认证材料提交失败，请稍后重试')
