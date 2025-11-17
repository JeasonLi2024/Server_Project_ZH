from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from user.models import User, Student as StudentProfile, OrganizationUser
from organization.models import Organization
from .models import EmailVerificationCode, LoginLog, AccountDeletionLog, OrganizationInvitationCode
from .utils import check_password_strength, assign_random_avatar
from .verification_utils import validate_email_code
from .invitation_utils import validate_invitation_code


class RegisterSerializer(serializers.Serializer):
    """用户注册序列化器"""
    username = serializers.CharField(
        max_length=30,
        help_text="用户名"
    )
    email = serializers.EmailField(help_text="邮箱地址")
    phone = serializers.CharField(required=False, max_length=11, help_text="手机号")
    password = serializers.CharField(
        min_length=6,
        max_length=128,
        write_only=True,
        help_text="密码，至少8位，需包含大写字母、小写字母、数字、特殊字符中的至少两种"
    )
    confirm_password = serializers.CharField(
        min_length=6,
        max_length=128,
        write_only=True,
        help_text="确认密码"
    )
    email_code = serializers.CharField(max_length=10, required=False, help_text="邮箱验证码")
    phone_code = serializers.CharField(max_length=10, required=False, help_text="手机验证码")
    
    # 用户类型
    user_type = serializers.ChoiceField(
        choices=[('student', '学生'), ('organization', '组织用户')],
        help_text="用户类型：student-学生，organization-组织用户"
    )
    
    # 学生特有字段
    student_id = serializers.CharField(max_length=20, required=False, help_text="学号")
    school_id = serializers.IntegerField(required=False, help_text="学校ID")
    major = serializers.CharField(max_length=100, required=False, help_text="专业")
    education = serializers.CharField(max_length=20, required=False, help_text="学历层次")
    grade = serializers.CharField(max_length=10, required=False, help_text="年级")
    
    # 组织用户特有字段
    registration_choice = serializers.ChoiceField(
        choices=[('existing', '加入现有组织'), ('new', '创建新组织'), ('invitation', '邀请码注册')],
        required=False,
        help_text="注册选择：existing-加入现有组织，new-创建新组织，invitation-邀请码注册"
    )
    organization_id = serializers.IntegerField(required=False, help_text="选择的组织ID（当registration_choice为existing时必填）")
    invitation_code = serializers.CharField(max_length=32, required=False, help_text="邀请码（当registration_choice为invitation时必填）")
    
    # 新组织创建字段（当registration_choice为new时必填）
    organization_name = serializers.CharField(max_length=200, required=False, help_text="组织名称")
    organization_type = serializers.ChoiceField(
        choices=[('enterprise', '企业'), ('university', '大学'), ('other', '其他组织')],
        required=False, 
        help_text="组织类型"
    )
    industry_or_discipline = serializers.CharField(max_length=100, required=False, help_text="行业/学科领域")
    
    # 用户在组织中的信息
    position = serializers.CharField(max_length=100, required=False, help_text="职位/职务")
    department = serializers.CharField(max_length=100, required=False, help_text="部门/院系")
    
    def create(self, validated_data):
        # 移除确认密码字段
        validated_data.pop('confirm_password', None)
        validated_data.pop('email_code', None)
        validated_data.pop('phone_code', None)
        
        # 提取用户类型
        user_type = validated_data.pop('user_type')
        
        # 提取用户基本信息
        user_data = {
            'username': validated_data.pop('username'),
            'email': validated_data.pop('email'),
            'password': validated_data.pop('password'),
            'user_type': user_type
        }
        if 'phone' in validated_data:
            user_data['phone'] = validated_data.pop('phone')
        
        # 创建用户
        user = User.objects.create_user(**user_data)
        
        # 为新用户分配随机头像
        assign_random_avatar(user)
        
        # 根据用户类型创建对应的profile
        if user_type == 'student':
            from organization.models import University
            school_id = validated_data.get('school_id')
            school_instance = None
            if school_id:
                try:
                    school_instance = University.objects.get(id=school_id)
                except University.DoesNotExist:
                    pass
            
            StudentProfile.objects.create(
                user=user,
                student_id=validated_data.get('student_id'),
                school=school_instance,
                major=validated_data.get('major'),
                education_level=validated_data.get('education'),
                grade=validated_data.get('grade')
            )
        elif user_type == 'organization':
            # 处理组织用户注册
            registration_choice = validated_data.get('registration_choice')
            organization_id = validated_data.get('organization_id')
            invitation_code = validated_data.get('invitation_code')
            
            if registration_choice == 'new':
                # 创建新组织
                org_data = {
                    'name': validated_data.get('organization_name'),
                    'organization_type': validated_data.get('organization_type'),
                    'industry_or_discipline': validated_data.get('industry_or_discipline', ''),
                    'scale': 'small',  # 默认值，后续可完善
                    'contact_person': user.username,  # 默认联系人为注册用户
                    'contact_phone': '',  # 待完善
                    'address': '待完善',  # 待完善
                    'status': 'pending'  # 待认证状态
                }
                
                # 根据组织类型添加必要字段
                if validated_data.get('organization_type') == 'enterprise':
                    org_data['enterprise_type'] = 'private'  # 默认为民营企业
                elif validated_data.get('organization_type') == 'university':
                    org_data['university_type'] = 'ordinary'  # 默认为普通本科
                elif validated_data.get('organization_type') == 'other':
                    org_data['other_type'] = 'other_unspecified'  # 默认为其他未分类
                
                organization = Organization.objects.create(**org_data)
            elif registration_choice == 'existing' and organization_id:
                # 选择已有组织
                try:
                    organization = Organization.objects.get(id=organization_id, status='verified')
                except Organization.DoesNotExist:
                    raise serializers.ValidationError("选择的组织不存在或未通过认证")
            elif registration_choice == 'invitation' and invitation_code:
                # 邀请码注册
                organization = validated_data.get('_invitation_organization')
                if not organization:
                    raise serializers.ValidationError("邀请码对应的组织信息获取失败")
                
                # 使用邀请码（增加使用次数）
                from .invitation_utils import use_invitation_code
                success, organization, message = use_invitation_code(invitation_code, user)
                if not success:
                    raise serializers.ValidationError(f"邀请码使用失败：{message}")
            else:
                raise serializers.ValidationError("必须选择注册方式并提供相应信息")
            
            # 创建组织用户资料
            OrganizationUser.objects.create(
                user=user,
                organization=organization,
                position=validated_data.get('position', '成员'),  # 邀请码注册默认为成员
                department=validated_data.get('department', ''),
                permission='owner' if registration_choice == 'new' else 'member',  # 创建组织的用户为所有者，其他为成员
                status='approved' if registration_choice in ['new', 'invitation'] else 'pending'  # 创建组织和邀请码注册直接通过审核
            )
        
        return user
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱已被注册")
        return value

    def validate_phone(self, value):
        from django.core.validators import RegexValidator
        RegexValidator(r'^1[3-9]\d{9}$')(value)
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("该手机号已被注册")
        return value
    
    def validate_school_id(self, value):
        """验证学校ID"""
        if value:
            from organization.models import University
            if not University.objects.filter(id=value).exists():
                raise serializers.ValidationError("无效的学校ID")
        return value
    
    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')
        
        if password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "两次输入的密码不一致"})
        
        # 验证密码强度
        is_strong, message = check_password_strength(password)
        if not is_strong:
            raise serializers.ValidationError({"password": message})
        
        # 验证邮箱验证码
        email = attrs.get('email')
        email_code = attrs.get('email_code')
        phone = attrs.get('phone')
        phone_code = attrs.get('phone_code')
        if email_code:
            is_valid, message = validate_email_code(email, email_code, 'register')
            if not is_valid:
                raise serializers.ValidationError({"email_code": f"邮箱验证码{message}"})
        elif phone and phone_code:
            from .phone_verification import validate_phone_code
            ok, msg = validate_phone_code(phone, phone_code, 'register')
            if not ok:
                raise serializers.ValidationError({"phone_code": f"手机验证码{msg}"})
        else:
            raise serializers.ValidationError({"verification": ["必须提供邮箱验证码或手机验证码"]})
        
        # 根据用户类型验证必填字段
        user_type = attrs.get('user_type')
        
        if user_type == 'student':
            # 学生用户必填字段验证
            required_fields = ['student_id', 'school_id', 'major', 'education', 'grade']
            for field in required_fields:
                if not attrs.get(field):
                    raise serializers.ValidationError({field: [f"学生用户必须填写{field}"]})
        
        elif user_type == 'organization':
            # 组织用户必填字段验证
            registration_choice = attrs.get('registration_choice')
            organization_id = attrs.get('organization_id')
            invitation_code = attrs.get('invitation_code')
            
            if not registration_choice:
                raise serializers.ValidationError({'registration_choice': ['组织用户必须选择注册方式']})
            
            if registration_choice == 'existing':
                # 加入现有组织时必须提供organization_id
                if not organization_id:
                    raise serializers.ValidationError({'organization_id': ['加入现有组织时必须提供组织ID']})
            elif registration_choice == 'new':
                # 创建新组织时的必填字段
                required_fields = ['organization_name', 'organization_type', 'industry_or_discipline']
                for field in required_fields:
                    if not attrs.get(field):
                        raise serializers.ValidationError({field: [f"创建新组织时必须填写{field}"]})
            elif registration_choice == 'invitation':
                # 邀请码注册时必须提供invitation_code
                if not invitation_code:
                    raise serializers.ValidationError({'invitation_code': ['邀请码注册时必须提供邀请码']})
                
                # 验证邀请码
                is_valid, message, organization = validate_invitation_code(invitation_code)
                if not is_valid:
                    raise serializers.ValidationError({'invitation_code': message})
                
                # 将组织信息存储到attrs中，供create方法使用
                attrs['_invitation_organization'] = organization
            else:
                raise serializers.ValidationError({'registration_choice': ['无效的注册选择']})
            
            # 职位是必填的（邀请码注册除外，因为可能由组织预设）
            if registration_choice != 'invitation' and not attrs.get('position'):
                raise serializers.ValidationError({'position': ['组织用户必须填写职位']})
        
        return attrs


class AccountDeletionRequestSerializer(serializers.Serializer):
    """账户注销申请序列化器"""
    
    password = serializers.CharField(
        required=True, 
        write_only=True,
        help_text="当前账户密码，用于身份验证"
    )
    reason = serializers.CharField(
        required=False, 
        max_length=500,
        help_text="注销原因（可选）"
    )
    email_code = serializers.CharField(
        max_length=10, 
        required=True,
        help_text="邮箱验证码，用于二次验证"
    )
    confirm_deletion = serializers.BooleanField(
        required=True,
        help_text="确认删除账户，必须为true"
    )
    
    def validate_password(self, value):
        """验证当前密码"""
        user = self.context['user']
        if not user.check_password(value):
            raise serializers.ValidationError("密码错误")
        return value
    
    def validate_confirm_deletion(self, value):
        """验证确认删除"""
        if not value:
            raise serializers.ValidationError("必须确认删除账户")
        return value
    
    def validate(self, attrs):
        """验证邮箱验证码"""
        user = self.context['user']
        email_code = attrs.get('email_code')
        
        # 验证邮箱验证码
        is_valid, message = validate_email_code(user.email, email_code, 'delete_account')
        if not is_valid:
            raise serializers.ValidationError({"email_code": f"邮箱验证码{message}"})
        
        return attrs


class AccountDeletionLogSerializer(serializers.ModelSerializer):
    """账户注销日志序列化器"""
    
    deletion_type_display = serializers.CharField(source='get_deletion_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AccountDeletionLog
        fields = [
            'id', 'user_id', 'username', 'email', 'user_type',
            'deletion_type', 'deletion_type_display', 'reason', 
            'status', 'status_display', 'requested_by', 'processed_by',
            'ip_address', 'is_data_anonymized',
            'requested_at', 'processed_at', 'scheduled_deletion_at', 'actual_deletion_at'
        ]
        read_only_fields = [
            'id', 'user_id', 'username', 'email', 'user_type',
            'requested_by', 'processed_by', 'ip_address', 'is_data_anonymized',
            'requested_at', 'processed_at', 'scheduled_deletion_at', 'actual_deletion_at'
        ]


class AccountDeletionCancelSerializer(serializers.Serializer):
    """取消账户注销序列化器"""
    
    password = serializers.CharField(
        required=True, 
        write_only=True,
        help_text="当前账户密码，用于身份验证"
    )
    
    def validate_password(self, value):
        """验证当前密码"""
        user = self.context['user']
        if not user.check_password(value):
            raise serializers.ValidationError("密码错误")
        return value





class LoginSerializer(serializers.Serializer):
    """统一登录序列化器"""
    type = serializers.ChoiceField(
        choices=[('password', '密码登录'), ('email-verification', '邮箱验证码登录'), ('phone-verification', '手机验证码登录')],
        required=True,
        help_text="登录类型：password、email-verification、phone-verification"
    )
    
    # 密码登录字段
    username_or_email_or_phone = serializers.CharField(
        required=False,
        help_text="用户名、邮箱或手机号"
    )
    password = serializers.CharField(
        required=False,
        write_only=True,
        help_text="密码"
    )
    
    # 邮箱验证码登录字段
    email = serializers.EmailField(
        required=False,
        help_text="邮箱地址"
    )
    email_code = serializers.CharField(
        max_length=6,
        required=False,
        help_text="邮箱验证码"
    )

    # 手机验证码登录字段
    phone = serializers.CharField(
        required=False,
        max_length=11,
        help_text="手机号"
    )
    phone_code = serializers.CharField(
        max_length=6,
        required=False,
        help_text="手机验证码"
    )
    
    def validate(self, attrs):
        login_type = attrs.get('type')
        
        if login_type == 'password':
            # 密码登录验证
            username_or_email_or_phone = attrs.get('username_or_email_or_phone')
            password = attrs.get('password')
            
            if not username_or_email_or_phone:
                raise serializers.ValidationError({"username_or_email_or_phone": "用户名、邮箱或手机号不能为空"})
            if not password:
                raise serializers.ValidationError({"password": "密码不能为空"})
                
        elif login_type == 'email-verification':
            # 邮箱验证码登录验证
            email = attrs.get('email')
            email_code = attrs.get('email_code')
            
            if not email:
                raise serializers.ValidationError({"email": "邮箱不能为空"})
            if not email_code:
                raise serializers.ValidationError({"email_code": "验证码不能为空"})

        elif login_type == 'phone-verification':
            phone = attrs.get('phone')
            phone_code = attrs.get('phone_code')
            if not phone:
                raise serializers.ValidationError({"phone": "手机号不能为空"})
            if not phone_code:
                raise serializers.ValidationError({"phone_code": "验证码不能为空"})
            # 手机验证码登录无需验证邮箱验证码
        
        return attrs

class PhoneCodeSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11)
    code_type = serializers.ChoiceField(choices=[
        ('register', '注册'),
        ('login', '登录'),
        ('reset_password', '重置密码'),
        ('change_phone', '更换手机号'),
        ('bind_new_phone', '绑定新手机号'),
        ('verify_phone', '验证绑定手机号')
    ])





class PasswordChangeSerializer(serializers.Serializer):
    """修改密码序列化器"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(min_length=8, max_length=128, write_only=True)
    confirm_password = serializers.CharField(min_length=8, max_length=128, write_only=True)
    
    def validate_old_password(self, value):
        user = self.context['user']
        if not user.check_password(value):
            raise serializers.ValidationError("原密码错误")
        return value
    
    def validate(self, attrs):
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "两次输入的密码不一致"})
        
        # 验证密码强度
        is_strong, message = check_password_strength(new_password)
        if not is_strong:
            raise serializers.ValidationError({"new_password": message})
        
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """密码重置请求序列化器"""
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱未注册")
        return value


class PasswordResetSerializer(serializers.Serializer):
    """密码重置序列化器"""
    email = serializers.EmailField(required=True)
    email_code = serializers.CharField(max_length=6, required=True)
    new_password = serializers.CharField(min_length=8, max_length=128, write_only=True)
    confirm_password = serializers.CharField(min_length=8, max_length=128, write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        email_code = attrs.get('email_code')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        # 验证邮箱验证码
        is_valid, message = validate_email_code(email, email_code, 'reset_password')
        if not is_valid:
            raise serializers.ValidationError({"email_code": f"邮箱验证码{message}"})
        
        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "两次输入的密码不一致"})
        
        # 验证密码强度
        is_strong, message = check_password_strength(new_password)
        if not is_strong:
            raise serializers.ValidationError({"new_password": message})
        
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """忘记密码序列化器 - 完整的忘记密码流程"""
    email = serializers.EmailField(required=True, help_text="注册邮箱地址")
    email_code = serializers.CharField(max_length=10, required=True, help_text="邮箱验证码")
    new_password = serializers.CharField(
        min_length=8, 
        max_length=128, 
        write_only=True, 
        help_text="新密码，至少8位字符"
    )
    confirm_password = serializers.CharField(
        min_length=8, 
        max_length=128, 
        write_only=True, 
        help_text="确认新密码"
    )
    
    def validate_email(self, value):
        """验证邮箱是否已注册"""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱未注册")
        return value
    
    def validate(self, attrs):
        email = attrs.get('email')
        email_code = attrs.get('email_code')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        # 验证邮箱验证码
        is_valid, message = validate_email_code(email, email_code, 'reset_password')
        if not is_valid:
            raise serializers.ValidationError({"email_code": f"邮箱验证码{message}"})
        
        # 验证两次密码是否一致
        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "两次输入的密码不一致"})
        
        # 验证密码强度
        is_strong, message = check_password_strength(new_password)
        if not is_strong:
            raise serializers.ValidationError({"new_password": message})
        
        return attrs


class EmailCodeSerializer(serializers.Serializer):
    """邮箱验证码序列化器"""
    email = serializers.EmailField(required=True)
    code_type = serializers.ChoiceField(
        choices=['register', 'login', 'reset_password', 'change_email', 'delete_account'], 
        default='register'
    )


class TokenVerifySerializer(serializers.Serializer):
    """Token验证序列化器"""
    token = serializers.CharField(required=True)


class RefreshTokenSerializer(serializers.Serializer):
    """刷新令牌序列化器"""
    refresh_token = serializers.CharField(
        required=True, 
        help_text="刷新令牌，用于获取新的访问令牌"
    )


class LogoutSerializer(serializers.Serializer):
    """
    登出序列化器
    
    refresh_token支持多种传递方式：
    1. 请求体中的refresh_token字段（优先级最高）
    2. Cookie中的refresh_token
    3. 请求头中的X-Refresh-Token
    
    如果都没有提供，系统会自动黑名单化用户的所有有效token
    """
    refresh_token = serializers.CharField(
        required=False, 
        help_text="刷新令牌（可选，支持请求体、Cookie、请求头多种方式传递）"
    )


class LoginLogSerializer(serializers.ModelSerializer):
    """登录日志序列化器"""
    
    user_info = serializers.SerializerMethodField()
    login_type_display = serializers.CharField(source='get_login_type_display', read_only=True)
    
    class Meta:
        model = LoginLog
        fields = [
            'id', 'user_info', 'login_type', 'login_type_display',
            'ip_address', 'user_agent', 'is_success', 'failure_reason',
            'created_at'
        ]
    
    def get_user_info(self, obj):
        """获取用户信息"""
        return {
            'username': obj.user.username,
            'real_name': obj.user.real_name,
            'user_type': obj.user.get_user_type_display()
        }


class EmailCodeValidationSerializer(serializers.Serializer):
    """邮箱验证码验证序列化器（不消费）"""
    
    email = serializers.EmailField()
    code = serializers.CharField(max_length=10)
    code_type = serializers.ChoiceField(
        choices=['register', 'login', 'reset_password', 'change_email', 'delete_account'],
        default='register'
    )


class UserExistsCheckSerializer(serializers.Serializer):
    """用户存在性检查序列化器"""
    
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False)
    
    def validate(self, attrs):
        if not attrs.get('email') and not attrs.get('username'):
            raise serializers.ValidationError("必须提供邮箱或用户名中的一个")
        return attrs


class ChangeEmailSerializer(serializers.Serializer):
    """修改邮箱序列化器"""
    email = serializers.EmailField(required=True, help_text="新邮箱地址")
    email_code = serializers.CharField(max_length=10, required=True, help_text="新邮箱验证码")
    
    def validate_email(self, value):
        """验证新邮箱是否已被使用"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱已被其他用户使用")
        return value
    
    def validate(self, attrs):
        """验证邮箱验证码"""
        email = attrs.get('email')
        email_code = attrs.get('email_code')
        
        # 验证邮箱验证码
        is_valid, message = validate_email_code(email, email_code, 'change_email')
        if not is_valid:
            raise serializers.ValidationError({"email_code": f"邮箱验证码{message}"})
        
        return attrs


class OrganizationInvitationCodeSerializer(serializers.ModelSerializer):
    """组织邀请码序列化器"""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = OrganizationInvitationCode
        fields = [
            'id', 'code', 'organization', 'organization_name', 
            'status', 'status_display', 'created_by', 'created_by_username',
            'created_at', 'expires_at', 'updated_at', 'used_count', 'max_uses'
        ]
        read_only_fields = [
            'id', 'code', 'organization', 'organization_name',
            'created_by', 'created_by_username', 'created_at', 'expires_at', 'updated_at'
        ]


class InvitationCodeGenerateSerializer(serializers.Serializer):
    """生成邀请码序列化器"""
    expire_days = serializers.IntegerField(
        default=30,
        min_value=1,
        max_value=365,
        help_text="邀请码有效期天数，默认30天"
    )
    max_uses = serializers.IntegerField(
        default=100, 
        min_value=1, 
        max_value=1000,
        help_text="邀请码最大使用次数，默认100次"
    )


class InvitationCodeValidateSerializer(serializers.Serializer):
    """验证邀请码序列化器"""
    code = serializers.CharField(max_length=32, help_text="邀请码")
    
    def validate_code(self, value):
        from .invitation_utils import validate_invitation_code
        is_valid, message, organization = validate_invitation_code(value)
        if not is_valid:
            raise serializers.ValidationError(message)
        return value