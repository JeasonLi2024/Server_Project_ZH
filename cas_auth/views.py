from django.shortcuts import redirect
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
import logging

from common_utils import APIResponse
from user.models import OrganizationUser
from organization.models import Organization
from user.serializers import UserProfileSerializer
from authentication.utils import get_client_ip, get_user_agent
from .services import BUPTCASService
from .models import CASAuthLog

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def cas_login(request):
    """CAS登录入口 - 重定向到CAS服务器"""
    cas_service = BUPTCASService()
    
    if not cas_service.is_cas_enabled():
        return APIResponse.error('CAS认证未启用', 503)
    
    # 获取回调URL
    service_url = request.GET.get('service', cas_service.service_url)
    
    # 生成CAS登录URL
    login_url = cas_service.get_login_url(service_url)
    
    # 记录登录重定向日志
    request_info = {
        'ip_address': get_client_ip(request),
        'user_agent': get_user_agent(request),
    }
    
    CASAuthLog.objects.create(
        action='login',
        status='pending',
        service_url=service_url,
        **request_info
    )
    
    # 返回重定向URL给前端
    return APIResponse.success({
        'login_url': login_url,
        'service_url': service_url
    }, '请重定向到CAS登录页面')


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def cas_callback(request):
    """CAS认证回调处理"""
    cas_service = BUPTCASService()
    
    if not cas_service.is_cas_enabled():
        return APIResponse.error('CAS认证未启用', 503)
    
    # 获取票据
    ticket = request.GET.get('ticket')
    service_url = request.GET.get('service', cas_service.service_url)
    
    if not ticket:
        return APIResponse.error('缺少CAS票据', 400)
    
    # 获取请求信息
    request_info = {
        'ip_address': get_client_ip(request),
        'user_agent': get_user_agent(request),
    }
    
    try:
        # 验证票据
        success, cas_data = cas_service.validate_ticket(ticket, service_url, request_info)
        
        if not success:
            error_msg = cas_data.get('error', '票据验证失败')
            return APIResponse.error(f'CAS认证失败: {error_msg}', 401)
        
        # 同步用户数据
        with transaction.atomic():
            user, created = cas_service.sync_cas_user(cas_data, request_info)
            
            # 确保用户有组织关联（这里需要根据实际业务逻辑调整）
            org_user = user.organization_profile
            if not org_user.organization_id:
                # 如果没有组织关联，可以设置默认组织或要求用户选择
                # 这里暂时跳过，实际部署时需要处理
                pass
            
            # 生成JWT Token
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # 更新最后登录时间
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # 序列化用户信息
            user_serializer = UserProfileSerializer(user, context={'request': request})
            
            # 构建响应数据
            response_data = {
                'user': user_serializer.data,
                'auth': {
                    'access': str(access_token),
                    'refresh': str(refresh)
                },
                'cas_info': {
                    'user_id': cas_data.get('user_id'),
                    'is_new_user': created,
                    'auth_source': 'cas'
                }
            }
            
            # 如果是新用户，添加提示信息
            message = "CAS认证成功，欢迎新用户！" if created else "CAS认证成功"
            
            return APIResponse.success(response_data, message)
            
    except ValueError as e:
        logger.error(f"CAS用户同步失败: {str(e)}")
        return APIResponse.error(f'用户信息同步失败: {str(e)}', 400)
    
    except Exception as e:
        logger.error(f"CAS认证回调处理异常: {str(e)}")
        return APIResponse.server_error('CAS认证处理失败，请稍后重试')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def cas_logout(request):
    """CAS登出处理 - 包含JWT token黑名单化"""
    cas_service = BUPTCASService()
    
    if not cas_service.is_cas_enabled():
        return APIResponse.error('CAS认证未启用', 503)
    
    # 获取回调URL
    service_url = request.GET.get('service') or request.POST.get('service')
    if not service_url:
        service_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    
    # 生成CAS登出URL
    logout_url = cas_service.get_logout_url(service_url)
    
    # 记录登出日志
    request_info = {
        'ip_address': get_client_ip(request),
        'user_agent': get_user_agent(request),
    }
    
    # 如果用户已认证，记录用户信息并处理JWT token黑名单化
    user = None
    cas_user_id = None
    if hasattr(request, 'user') and request.user.is_authenticated:
        user = request.user
        try:
            org_user = user.organization_profile
            if org_user.auth_source == 'cas':
                cas_user_id = org_user.cas_user_id
            else:
                cas_user_id = None
        except:
            cas_user_id = None
        
        # JWT Token黑名单化处理（复用普通登出逻辑）
        try:
            # 获取refresh_token（支持多种传递方式）
            refresh_token = None
            
            # 优先从请求体获取
            if hasattr(request, 'data') and request.data:
                refresh_token = request.data.get('refresh_token')
            
            # 如果请求体没有，尝试从Cookie获取
            if not refresh_token:
                refresh_token = request.COOKIES.get('refresh_token')
            
            # 如果请求体和Cookie都没有，尝试从请求头获取
            if not refresh_token:
                refresh_header = request.META.get('HTTP_X_REFRESH_TOKEN')
                if refresh_header:
                    refresh_token = refresh_header
            
            # 处理refresh_token
            if refresh_token:
                try:
                    from rest_framework_simplejwt.exceptions import TokenError
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                    logger.info(f"CAS登出: Refresh token已加入黑名单: 用户{user.username}")
                except TokenError as e:
                    logger.warning(f"CAS登出: Refresh token黑名单化失败: {str(e)}")
            else:
                # 如果没有找到refresh_token，黑名单化当前用户的所有有效token
                from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
                
                outstanding_tokens = OutstandingToken.objects.filter(
                    user=user,
                    blacklistedtoken__isnull=True  # 只获取未被黑名单的token
                )
                
                blacklisted_count = 0
                for outstanding_token in outstanding_tokens:
                    try:
                        token = RefreshToken(outstanding_token.token)
                        token.blacklist()
                        blacklisted_count += 1
                    except Exception as e:
                        logger.warning(f"CAS登出: Token黑名单化失败: {str(e)}")
                        continue
                
                logger.info(f"CAS登出: 已黑名单化用户{user.username}的{blacklisted_count}个token")
                
        except Exception as e:
            # 即使token处理失败，也不影响CAS登出流程
            logger.warning(f"CAS登出时处理JWT token异常: {str(e)}")
    
    CASAuthLog.objects.create(
        user=user,
        cas_user_id=cas_user_id,
        action='logout',
        status='success',
        service_url=service_url,
        **request_info
    )
    
    # 返回登出URL给前端
    return APIResponse.success({
        'logout_url': logout_url,
        'service_url': service_url
    }, '请重定向到CAS登出页面')


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def cas_status(request):
    """CAS配置状态检查"""
    cas_service = BUPTCASService()
    
    status_info = {
        'cas_enabled': cas_service.is_cas_enabled(),
        'cas_server_url': cas_service.cas_server_url if cas_service.is_cas_enabled() else None,
        'cas_version': cas_service.cas_version,
        'service_url': cas_service.service_url if cas_service.is_cas_enabled() else None,
    }
    
    # 如果用户已认证，添加用户CAS信息
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            org_user = request.user.organization_profile
            status_info.update({
                'user_cas_info': {
                    'cas_user_id': org_user.cas_user_id,
                    'auth_source': org_user.auth_source,
                    'last_cas_login': org_user.last_cas_login.isoformat() if org_user.last_cas_login else None,
                }
            })
        except:
            status_info['user_cas_info'] = None
    
    return APIResponse.success(status_info, 'CAS状态信息')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cas_user_info(request):
    """获取当前用户的CAS认证信息"""
    try:
        org_user = request.user.organization_profile
        
        user_info = {
            'cas_user_id': org_user.cas_user_id,
            'auth_source': org_user.auth_source,
            'last_cas_login': org_user.last_cas_login.isoformat() if org_user.last_cas_login else None,
            'is_cas_user': org_user.auth_source == 'cas',
        }
        
        # 获取最近的CAS认证日志
        recent_logs = CASAuthLog.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
        
        user_info['recent_auth_logs'] = [
            {
                'action': log.get_action_display(),
                'status': log.get_status_display(),
                'created_at': log.created_at.isoformat(),
                'ip_address': log.ip_address,
            }
            for log in recent_logs
        ]
        
        return APIResponse.success(user_info, '用户CAS信息')
        
    except OrganizationUser.DoesNotExist:
        return APIResponse.error('用户组织信息不存在', 404)
    except Exception as e:
        logger.error(f"获取用户CAS信息失败: {str(e)}")
        return APIResponse.server_error('获取用户信息失败')
