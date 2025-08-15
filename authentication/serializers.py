from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from user.models import User, Student as StudentProfile, OrganizationUser
from organization.models import Organization
from .models import EmailVerificationCode, LoginLog, AccountDeletionLog
from .utils import check_password_strength, assign_random_avatar
from .verification_utils import validate_email_code


class RegisterSerializer(serializers.Serializer):
    """用户注册序列化器"""
    username = serializers.CharField(
        max_length=30,
        help_text="用户名"
    )
    email = serializers.EmailField(help_text="邮箱地址")
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
    email_code = serializers.CharField(
        max_length=10,
        help_text="邮箱验证码"
    )
    
    # 用户类型
    user_type = serializers.ChoiceField(
        choices=[('student', '学生'), ('organization', '组织用户')],
        help_text="用户类型：student-学生，organization-组织用户"
    )
    
    # 学生特有字段
    student_id = serializers.CharField(max_length=20, required=False, help_text="学号")
    school = serializers.CharField(max_length=100, required=False, help_text="学校")
    major = serializers.CharField(max_length=100, required=False, help_text="专业")
    education = serializers.CharField(max_length=20, required=False, help_text="学历层次")
    grade = serializers.CharField(max_length=10, required=False, help_text="年级")
    
    # 组织用户特有字段
    registration_choice = serializers.ChoiceField(
        choices=[('existing', '加入现有组织'), ('new', '创建新组织')],
        required=False,
        help_text="注册选择：existing-加入现有组织，new-创建新组织"
    )
    organization_id = serializers.IntegerField(required=False, help_text="选择的组织ID（当registration_choice为existing时必填）")
    
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
        
        # 提取用户类型
        user_type = validated_data.pop('user_type')
        
        # 提取用户基本信息
        user_data = {
            'username': validated_data.pop('username'),
            'email': validated_data.pop('email'),
            'password': validated_data.pop('password'),
            'user_type': user_type
        }
        
        # 创建用户
        user = User.objects.create_user(**user_data)
        
        # 为新用户分配随机头像
        assign_random_avatar(user)
        
        # 根据用户类型创建对应的profile
        if user_type == 'student':
            StudentProfile.objects.create(
                user=user,
                student_id=validated_data.get('student_id'),
                school=validated_data.get('school'),
                major=validated_data.get('major'),
                education_level=validated_data.get('education'),
                grade=validated_data.get('grade')
            )
        elif user_type == 'organization':
            # 处理组织用户注册
            registration_choice = validated_data.get('registration_choice')
            organization_id = validated_data.get('organization_id')
            
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
            else:
                raise serializers.ValidationError("必须选择注册方式并提供相应信息")
            
            # 创建组织用户资料
            OrganizationUser.objects.create(
                user=user,
                organization=organization,
                position=validated_data.get('position', ''),
                department=validated_data.get('department', ''),
                permission='owner' if registration_choice == 'new' else 'pending',  # 创建组织的用户为所有者，加入现有组织的用户为待审核
                status='approved' if registration_choice == 'new' else 'pending'  # 创建组织的用户直接通过审核，加入现有组织的用户待审核
            )
        
        return user
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱已被注册")
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
        is_valid, message = validate_email_code(email, email_code, 'register')
        if not is_valid:
            raise serializers.ValidationError({"email_code": f"邮箱验证码{message}"})
        
        # 根据用户类型验证必填字段
        user_type = attrs.get('user_type')
        
        if user_type == 'student':
            # 学生用户必填字段验证
            required_fields = ['student_id', 'school', 'major', 'education', 'grade']
            for field in required_fields:
                if not attrs.get(field):
                    raise serializers.ValidationError({field: [f"学生用户必须填写{field}"]})
        
        elif user_type == 'organization':
            # 组织用户必填字段验证
            registration_choice = attrs.get('registration_choice')
            organization_id = attrs.get('organization_id')
            
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
            else:
                raise serializers.ValidationError({'registration_choice': ['无效的注册选择']})
            
            # 职位是必填的
            if not attrs.get('position'):
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
        choices=[('password', '密码登录'), ('email-verification', '邮箱验证码登录')],
        required=True,
        help_text="登录类型：password-密码登录，email-verification-邮箱验证码登录"
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
            
            # 验证邮箱验证码
            is_valid, message = validate_email_code(email, email_code, 'login')
            if not is_valid:
                raise serializers.ValidationError({"email_code": f"邮箱验证码{message}"})
        
        return attrs


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
        is_valid, message = validate_email_code(email, email_code, 'reset')
        if not is_valid:
            raise serializers.ValidationError({"email_code": f"邮箱验证码{message}"})
        
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
        choices=['register', 'login', 'reset', 'change_email', 'delete_account'], 
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