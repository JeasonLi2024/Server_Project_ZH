from django.contrib.auth import authenticate
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
import logging

from user.models import User, Student, OrganizationUser
from organization.models import Organization
from user.serializers import UserProfileSerializer
from .models import EmailVerificationCode, LoginLog, AccountDeletionLog
from .utils import (
    get_client_ip, get_user_agent,
    create_login_log, generate_username_from_email
)
from .verification_utils import (
    send_verification_code, validate_email_code, verify_email_code
)
from .phone_verification import (
    send_phone_verification_code, validate_phone_code
)
from .serializers import (
    EmailCodeSerializer, RegisterSerializer, LoginSerializer,
    PasswordChangeSerializer, PasswordResetRequestSerializer,
    PasswordResetSerializer, ForgotPasswordSerializer, TokenVerifySerializer, RefreshTokenSerializer,
    LogoutSerializer, LoginLogSerializer, EmailCodeValidationSerializer, 
    UserExistsCheckSerializer, ChangeEmailSerializer,
    AccountDeletionRequestSerializer, AccountDeletionLogSerializer,
    AccountDeletionCancelSerializer, PhoneCodeSerializer
)
from common_utils import APIResponse, format_validation_errors

logger = logging.getLogger(__name__)


def get_next_deletion_time():
    """计算7天后的零点时间"""
    from datetime import datetime, time
    
    # 获取当前时间
    now = timezone.now()
    
    # 计算7天后的日期
    target_date = (now + timezone.timedelta(days=7)).date()
    
    # 设置为当天的零点
    target_datetime = timezone.make_aware(
        datetime.combine(target_date, time(0, 0, 0))
    )
    
    return target_datetime


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def send_email_code(request):
    """发送邮箱验证码"""
    serializer = EmailCodeSerializer(data=request.data)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    email = serializer.validated_data['email']
    code_type = serializer.validated_data['code_type']
    
    # 检查发送频率限制
    cache_key = f"email_code_limit:{email}:{code_type}"
    if cache.get(cache_key):
        return APIResponse.error('验证码发送过于频繁，请稍后再试', 429)
    
    # 如果是注册验证码，检查邮箱是否已注册
    if code_type == 'register' and User.objects.filter(email=email).exists():
        return APIResponse.error('该邮箱已注册', 422, {'email': ['该邮箱已注册']})
    
    # 如果是登录或重置验证码，检查邮箱是否已注册
    if code_type in ['login', 'reset_password'] and not User.objects.filter(email=email).exists():
        return APIResponse.error('该邮箱未注册', 422, {'email': ['该邮箱未注册']})
    
    # 如果是修改邮箱验证码，检查邮箱是否已被其他用户使用
    if code_type == 'change_email' and User.objects.filter(email=email).exists():
        return APIResponse.error('该邮箱已被其他用户使用', 422, {'email': ['该邮箱已被其他用户使用']})
    
    # 发送验证码
    try:
        if send_verification_code(email, code_type):
            return APIResponse.success({
                'email': email,
                'code_type': code_type
            }, "验证码发送成功")
        else:
            return APIResponse.server_error('验证码发送失败，请稍后重试', errors={
                'email_service': '邮件服务暂时不可用'
            })
    except Exception as e:
        logger.error(f"验证码发送异常: {str(e)}")
        return APIResponse.server_error('验证码发送失败，请稍后重试', errors={
            'exception_type': type(e).__name__,
            'exception_message': str(e)
        })


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def register(request):
    """用户注册"""
    serializer = RegisterSerializer(data=request.data)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    try:
        with transaction.atomic():
            # 使用序列化器的create方法创建用户（包含头像分配逻辑）
            user = serializer.save()
            
            # 生成JWT Token
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # 记录注册成功日志
            create_login_log(user, request, 'register', True)
            
            # 序列化用户完整信息
            user_serializer = UserProfileSerializer(user, context={'request': request})
            
            return APIResponse.success({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'user_type': user.user_type,
                    'user_type_display': user.get_user_type_display()
                },
                'tokens': {
                    'access_token': str(access_token),
                    'refresh_token': str(refresh)
                }
            }, "注册成功", 201)
            
    except Exception as e:
        logger.error(f"用户注册失败: {str(e)}")
        # 提供具体的错误信息用于调试
        error_details = {
            'exception_type': type(e).__name__,
            'exception_message': str(e)
        }
        return APIResponse.server_error('注册失败，请稍后重试', errors=error_details)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def login(request):
    """用户登录（支持密码登录和邮箱验证码登录）"""
    serializer = LoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    login_type = serializer.validated_data['type']
    
    # 根据登录类型处理
    if login_type == 'password':
        # 密码登录
        login_field = serializer.validated_data['username_or_email_or_phone']
        password = serializer.validated_data['password']
        
        # 查找用户
        user = None
        try:
            # 尝试用户名登录
            if User.objects.filter(username=login_field).exists():
                user = User.objects.get(username=login_field)
            # 尝试邮箱登录
            elif User.objects.filter(email=login_field).exists():
                user = User.objects.get(email=login_field)
            # 尝试手机号登录
            elif User.objects.filter(phone=login_field).exists():
                user = User.objects.get(phone=login_field)
        except User.DoesNotExist:
            pass
        
        if not user:
            return APIResponse.error('验证失败', 422, {'username_or_email_or_phone': ['用户不存在']})
        
        # 检查用户状态
        if not user.is_active:
            create_login_log(user, request, 'password', False, '账户已禁用')
            return APIResponse.error('验证失败', 422, {'username_or_email_or_phone': ['账户已被禁用']})
        
        # 验证密码
        if not user.check_password(password):
            create_login_log(user, request, 'password', False, '密码错误')
            return APIResponse.error('验证失败', 422, {'password': ['密码错误']})
        
        # 记录登录成功日志
        create_login_log(user, request, 'password', True)
        
    elif login_type == 'email-verification':
        # 邮箱验证码登录
        email = serializer.validated_data['email']
        
        # 查找用户
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return APIResponse.error('验证失败', 422, {'email': ['用户不存在']})
        
        # 检查用户状态
        if not user.is_active:
            create_login_log(user, request, 'email_verification', False, '账户已禁用')
            return APIResponse.error('验证失败', 422, {'email': ['账户已被禁用']})
        
        # 记录登录成功日志
        create_login_log(user, request, 'email_verification', True)
    
    elif login_type == 'phone-verification':
        # 手机验证码登录
        phone = serializer.validated_data['phone']
        phone_code = serializer.validated_data['phone_code']
        
        # 查找用户
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return APIResponse.error('验证失败', 422, {'phone': ['用户不存在']})
        
        # 检查用户状态
        if not user.is_active:
            create_login_log(user, request, 'phone_code', False, '账户已禁用')
            return APIResponse.error('验证失败', 422, {'phone': ['账户已被禁用']})
        
        # 校验验证码
        ok, msg = validate_phone_code(phone, phone_code, 'login')
        if not ok:
            create_login_log(user, request, 'phone_code', False, f'验证码{msg}')
            return APIResponse.error('验证失败', 422, {'phone_code': [f'验证码{msg}']})
        
        # 记录登录成功日志
        create_login_log(user, request, 'phone_code', True)
    
    else:
        return APIResponse.error('验证失败', 422, {'type': ['不支持的登录类型']})
    
    # 更新最后登录时间
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])
    
    # 生成JWT Token
    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token
    
    # 序列化用户完整信息
    user_serializer = UserProfileSerializer(user, context={'request': request})
    
    return APIResponse.success({
        'user': user_serializer.data,
        'auth': {
            'access': str(access_token),
            'refresh': str(refresh)
        }
    }, "登录成功")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """用户登出 - 同时黑名单化access_token和refresh_token"""
    serializer = LogoutSerializer(data=request.data)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    try:
        # 1. 记录当前access_token信息（AccessToken本身无法直接黑名单化）
        access_token_str = None
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            access_token_str = auth_header.split(' ')[1]
            try:
                # 验证token有效性
                access_token = AccessToken(access_token_str)
                logger.info(f"当前access token有效: 用户{request.user.username}")
            except Exception as e:
                logger.warning(f"Access token验证失败: {str(e)}")
        
        # 2. 获取refresh_token（支持多种传递方式）
        refresh_token = None
        
        # 优先从请求体获取
        refresh_token = serializer.validated_data.get('refresh_token')
        
        # 如果请求体没有，尝试从Cookie获取
        if not refresh_token:
            refresh_token = request.COOKIES.get('refresh_token')
        
        # 如果请求体和Cookie都没有，尝试从请求头获取
        if not refresh_token:
            refresh_header = request.META.get('HTTP_X_REFRESH_TOKEN')
            if refresh_header:
                refresh_token = refresh_header
        
        # 3. 处理refresh_token
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info(f"Refresh token已加入黑名单: 用户{request.user.username}")
            except TokenError as e:
                logger.warning(f"Refresh token黑名单化失败: {str(e)}")
        else:
            # 如果没有找到refresh_token，黑名单化当前用户的所有有效token
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
            
            outstanding_tokens = OutstandingToken.objects.filter(
                user=request.user,
                blacklistedtoken__isnull=True  # 只获取未被黑名单的token
            )
            
            blacklisted_count = 0
            for outstanding_token in outstanding_tokens:
                try:
                    token = RefreshToken(outstanding_token.token)
                    token.blacklist()
                    blacklisted_count += 1
                except Exception as e:
                    logger.warning(f"Token黑名单化失败: {str(e)}")
                    continue
            
            logger.info(f"已黑名单化用户{request.user.username}的{blacklisted_count}个token")
        
        # 4. 记录登出日志
        create_login_log(request.user, request, 'logout', True)
        
        return APIResponse.success(message="登出成功")
        
    except Exception as e:
        # 即使token处理失败，也返回成功，因为用户意图是登出
        logger.warning(f"登出时处理异常: {str(e)}")
        # 仍然记录登出日志
        try:
            create_login_log(request.user, request, 'logout', True, f"部分失败: {str(e)}")
        except:
            pass
        return APIResponse.success(message="登出成功")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify(request):
    """验证令牌有效性"""
    return APIResponse.success({
        'user_id': request.user.id,
        'username': request.user.username,
        'email': request.user.email,
        'is_active': request.user.is_active
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def refresh(request):
    """刷新访问令牌"""
    serializer = RefreshTokenSerializer(data=request.data)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    try:
        refresh_token = serializer.validated_data['refresh_token']
        token = RefreshToken(refresh_token)
        access_token = token.access_token
        
        return APIResponse.success({
            'access_token': str(access_token),
            'refresh_token': str(token)
        })
    except TokenError:
        return APIResponse.error('验证失败', 422, {'refresh_token': ['刷新令牌无效']})


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def send_phone_code(request):
    """发送短信验证码"""
    serializer = PhoneCodeSerializer(data=request.data)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    phone = serializer.validated_data['phone']
    code_type = serializer.validated_data['code_type']
    
    # 发送频率限制
    cache_key = f"phone_code_limit:{phone}:{code_type}"
    if cache.get(cache_key):
        return APIResponse.error('验证码发送过于频繁，请稍后再试', 429)
    
    # 注册：手机号不得已注册；登录/重置/验证：手机号必须已注册
    if code_type == 'register' and User.objects.filter(phone=phone).exists():
        return APIResponse.error('该手机号已注册', 422, {'phone': ['该手机号已注册']})
    if code_type in ['login', 'reset_password', 'verify_phone'] and not User.objects.filter(phone=phone).exists():
        return APIResponse.error('该手机号未注册', 422, {'phone': ['该手机号未注册']})
    
    try:
        ok, result = send_phone_verification_code(phone, code_type)
        if ok:
            return APIResponse.success({
                'phone': phone,
                'code_type': code_type,
                'request_id': result.get('request_id')
            }, '验证码发送成功')
        else:
            return APIResponse.server_error('验证码发送失败，请稍后重试', errors={
                'sms_service': result.get('message', '短信服务不可用')
            })
    except Exception as e:
        logger.error(f"短信验证码发送异常: {str(e)}")
        return APIResponse.server_error('验证码发送失败，请稍后重试', errors={
            'exception_type': type(e).__name__,
            'exception_message': str(e)
        })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """修改密码"""
    serializer = PasswordChangeSerializer(data=request.data, context={'user': request.user})
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    # 修改密码
    new_password = serializer.validated_data['new_password']
    request.user.set_password(new_password)
    request.user.save()
    
    return APIResponse.success()


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def reset_password_request(request):
    """请求密码重置"""
    serializer = PasswordResetRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    email = serializer.validated_data['email']
    
    # 发送重置验证码
    if send_verification_code(email, 'reset_password'):
        return APIResponse.success({
            'email': email
        })
    else:
        return APIResponse.server_error('验证码发送失败，请稍后重试')


@api_view(['PUT'])
@permission_classes([AllowAny])
@authentication_classes([])
def reset_password(request):
    """重置密码"""
    serializer = PasswordResetSerializer(data=request.data)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    try:
        email = serializer.validated_data['email']
        new_password = serializer.validated_data['new_password']
        
        # 获取用户并重置密码
        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()
        
        return APIResponse.success()
        
    except User.DoesNotExist:
        return APIResponse.error('验证失败', 422, {'email': ['用户不存在']})
    except Exception as e:
        logger.error(f"密码重置失败: {str(e)}")
        return APIResponse.server_error('密码重置失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def login_logs(request):
    """获取登录日志"""
    logs = LoginLog.objects.filter(user=request.user).order_by('-created_at')[:20]
    serializer = LoginLogSerializer(logs, many=True)
    
    return APIResponse.success(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def verify_email_code_view(request):
    """验证邮箱验证码（不消费）"""
    serializer = EmailCodeValidationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    email = serializer.validated_data['email']
    code = serializer.validated_data['code']
    code_type = serializer.validated_data['code_type']
    
    # 使用智能路由函数验证验证码
    is_valid, message = verify_email_code(email, code, code_type)
    
    if is_valid:
        return APIResponse.success({'message': message})
    else:
        return APIResponse.error(message, 422, {'code': [message]})


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def check_email_exists(request):
    """检查邮箱是否已注册"""
    email = request.GET.get('email')
    
    if not email:
        return APIResponse.error('邮箱不能为空', 422, {'email': ['邮箱不能为空']})
    
    exists = User.objects.filter(email=email).exists()
    
    return APIResponse.success({'exists': exists})


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def check_username_exists(request):
    """检查用户名是否已存在"""
    username = request.GET.get('username')
    
    if not username:
        return APIResponse.error('用户名不能为空', 422, {'username': ['用户名不能为空']})
    
    exists = User.objects.filter(username=username).exists()
    
    return APIResponse.success({'exists': exists})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def change_email(request):
    """修改邮箱"""
    serializer = ChangeEmailSerializer(data=request.data)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    try:
        with transaction.atomic():
            new_email = serializer.validated_data['email']
            old_email = request.user.email
            
            # 检查新邮箱是否与当前邮箱相同
            if new_email == old_email:
                return APIResponse.error('新邮箱不能与当前邮箱相同', 422, {'email': ['新邮箱不能与当前邮箱相同']})
            
            # 更新用户邮箱
            request.user.email = new_email
            request.user.save(update_fields=['email'])
            
            
            # 记录操作日志
            create_login_log(request.user, request, 'change_email', True, f'邮箱从 {old_email} 修改为 {new_email}')
            
            return APIResponse.success({
                'email': new_email
            }, "邮箱修改成功")
            
    except Exception as e:
        logger.error(f"邮箱修改失败: {str(e)}")
        return APIResponse.server_error('邮箱修改失败，请稍后重试', errors={
            'exception_type': type(e).__name__,
            'exception_message': str(e)
        })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def change_phone(request):
    code_type = request.data.get('code_type')
    serializer = PhoneCodeSerializer(data={
        'phone': request.data.get('phone'),
        'code_type': code_type
    })
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    new_phone = serializer.validated_data['phone']
    phone_code = request.data.get('phone_code')
    if not phone_code:
        return APIResponse.validation_error({'phone_code': ['验证码不能为空']})
    try:
        with transaction.atomic():
            old_phone = request.user.phone or ''
            if new_phone == old_phone:
                return APIResponse.error('新手机号不能与当前手机号相同', 422, {'phone': ['新手机号不能与当前手机号相同']})
            if code_type == 'bind_new_phone' and old_phone:
                return APIResponse.error('当前已绑定手机号，请使用修改手机号流程', 422, {'code_type': ['不允许在已绑定状态使用bind_new_phone']})
            if code_type == 'change_phone' and not old_phone:
                return APIResponse.error('当前未绑定手机号，请使用绑定手机号流程', 422, {'code_type': ['不允许在未绑定状态使用change_phone']})
            if User.objects.filter(phone=new_phone).exclude(id=request.user.id).exists():
                return APIResponse.error('该手机号已被其他用户使用', 422, {'phone': ['该手机号已被其他用户使用']})
            ok, msg = validate_phone_code(new_phone, phone_code, code_type)
            if not ok:
                return APIResponse.error(f'验证码{msg}', 422, {'phone_code': [f'验证码{msg}']})
            request.user.phone = new_phone
            request.user.save(update_fields=['phone'])
            create_login_log(request.user, request, 'change_phone', True, f'手机号从 {old_phone or "(空)"} 修改为 {new_phone}')
            return APIResponse.success({'phone': new_phone}, '手机号修改成功')
    except Exception as e:
        logger.error(f"手机号修改失败: {str(e)}")
        return APIResponse.server_error('手机号修改失败，请稍后重试', errors={'exception_type': type(e).__name__, 'exception_message': str(e)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_account_deletion(request):
    """申请账户注销"""
    serializer = AccountDeletionRequestSerializer(data=request.data, context={'user': request.user})
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    try:
        with transaction.atomic():
            user = request.user
            
            # 检查是否已有待处理的注销申请
            existing_request = AccountDeletionLog.objects.filter(
                user_id=user.id,
                status__in=['pending', 'approved']
            ).first()
            
            if existing_request:
                return APIResponse.error(
                    '您已有待处理的账户注销申请',
                    422,
                    {'deletion_request': ['已存在待处理的注销申请']}
                )
            
            # 获取客户端信息
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # 创建注销申请记录
            deletion_log = AccountDeletionLog.objects.create(
                user_id=user.id,
                username=user.username,
                email=user.email,
                user_type=user.user_type,
                deletion_type='user_request',
                reason=serializer.validated_data.get('reason', ''),
                status='pending',
                requested_by=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                # 设置7天后零点的计划删除时间
                scheduled_deletion_at=get_next_deletion_time()
            )
            
            # 发送确认邮件
            send_account_deletion_notification(user, deletion_log)
            
            # 记录操作日志
            create_login_log(user, request, 'account_deletion_request', True, '用户申请账户注销')
            
            logger.info(f"用户 {user.username} 申请账户注销，申请ID: {deletion_log.id}")
            
            return APIResponse.success({
                'deletion_id': deletion_log.id,
                'scheduled_deletion_at': deletion_log.scheduled_deletion_at,
                'message': '账户注销申请已提交，将在7天后执行删除操作。在此期间您可以取消注销申请。'
            }, "账户注销申请提交成功")
            
    except Exception as e:
        logger.error(f"账户注销申请失败: {str(e)}")
        return APIResponse.server_error('账户注销申请失败，请稍后重试')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_account_deletion(request):
    """取消账户注销"""
    serializer = AccountDeletionCancelSerializer(data=request.data, context={'user': request.user})
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    try:
        with transaction.atomic():
            user = request.user
            
            # 查找待处理的注销申请
            deletion_request = AccountDeletionLog.objects.filter(
                user_id=user.id,
                status__in=['pending', 'approved']
            ).first()
            
            if not deletion_request:
                return APIResponse.error(
                    '没有找到可取消的注销申请',
                    422,
                    {'deletion_request': ['没有待处理的注销申请']}
                )
            
            # 更新状态为已取消
            deletion_request.status = 'cancelled'
            deletion_request.processed_at = timezone.now()
            deletion_request.processed_by = user.id
            deletion_request.save()
            
            # 发送取消确认邮件
            send_account_deletion_cancel_notification(user, deletion_request)
            
            # 记录操作日志
            create_login_log(user, request, 'account_deletion_cancel', True, '用户取消账户注销申请')
            
            logger.info(f"用户 {user.username} 取消账户注销申请，申请ID: {deletion_request.id}")
            
            return APIResponse.success({
                'deletion_id': deletion_request.id,
                'cancelled_at': deletion_request.processed_at
            }, "账户注销申请已取消")
            
    except Exception as e:
        logger.error(f"取消账户注销失败: {str(e)}")
        return APIResponse.server_error('取消账户注销失败，请稍后重试')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def account_deletion_status(request):
    """查询账户注销状态"""
    try:
        user = request.user
        
        # 查找最新的注销申请
        deletion_request = AccountDeletionLog.objects.filter(
            user_id=user.id
        ).order_by('-requested_at').first()
        
        if not deletion_request:
            return APIResponse.success({
                'has_deletion_request': False,
                'message': '没有账户注销申请记录'
            })
        
        serializer = AccountDeletionLogSerializer(deletion_request)
        
        return APIResponse.success({
            'has_deletion_request': True,
            'deletion_request': serializer.data
        })
        
    except Exception as e:
        logger.error(f"查询账户注销状态失败: {str(e)}")
        return APIResponse.server_error('查询账户注销状态失败，请稍后重试')


def send_account_deletion_notification(user, deletion_log):
    """发送账户注销确认邮件"""
    try:
        subject = '【校企对接平台】账户注销确认'
        message = f'''
尊敬的用户 {user.username}：

您好！您的账户注销申请已收到。

申请详情：
- 申请时间：{deletion_log.requested_at.strftime('%Y-%m-%d %H:%M:%S')}
- 计划删除时间：{deletion_log.scheduled_deletion_at.strftime('%Y-%m-%d')} 00:00:00
- 注销原因：{deletion_log.reason or '未提供'}

重要提醒：
1. 账户将在7天后自动删除，删除后无法恢复
2. 在此期间您可以登录账户取消注销申请
3. 账户删除后，所有相关数据将被永久清除
4. 如需取消注销，请在计划删除时间前登录系统操作

如果这不是您本人的操作，请立即联系客服。

此邮件为系统自动发送，请勿回复。

校企对接平台
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"账户注销确认邮件发送成功: {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"账户注销确认邮件发送失败: {user.email} - {str(e)}")
        return False


def send_account_deletion_cancel_notification(user, deletion_log):
    """发送账户注销取消确认邮件"""
    try:
        subject = '【校企对接平台】账户注销已取消'
        message = f'''
尊敬的用户 {user.username}：

您好！您的账户注销申请已成功取消。

取消详情：
- 原申请时间：{deletion_log.requested_at.strftime('%Y-%m-%d %H:%M:%S')}
- 取消时间：{deletion_log.processed_at.strftime('%Y-%m-%d %H:%M:%S')}

您的账户将继续正常使用，所有数据保持不变。

如果这不是您本人的操作，请立即联系客服。

此邮件为系统自动发送，请勿回复。

校企对接平台
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"账户注销取消确认邮件发送成功: {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"账户注销取消确认邮件发送失败: {user.email} - {str(e)}")
        return False


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def forgot_password(request):
    """忘记密码 - 完整的忘记密码流程"""
    serializer = ForgotPasswordSerializer(data=request.data)
    
    if not serializer.is_valid():
        return APIResponse.validation_error(
            format_validation_errors(serializer.errors)
        )
    
    try:
        email = serializer.validated_data['email']
        new_password = serializer.validated_data['new_password']
        
        # 获取用户并重置密码
        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()
        
        # 记录密码重置日志
        create_login_log(user, request, 'password_reset', True, '通过忘记密码功能重置')
        
        logger.info(f"用户 {user.username} 通过忘记密码功能成功重置密码")
        
        return APIResponse.success({
            'message': '密码重置成功，请使用新密码登录'
        }, "密码重置成功")
        
    except User.DoesNotExist:
        return APIResponse.error('验证失败', 422, {'email': ['用户不存在']})
    except Exception as e:
        logger.error(f"忘记密码重置失败: {str(e)}")
        return APIResponse.server_error('密码重置失败，请稍后重试', errors={
            'exception_type': type(e).__name__,
            'exception_message': str(e)
        })
