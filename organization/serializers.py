import logging
from rest_framework import serializers
from django.conf import settings
from django.db import transaction
from common_utils import build_media_url, build_media_urls_list
from .models import Organization, OrganizationOperationLog, OrganizationConfig
from user.models import OrganizationUser
from django.contrib.auth import get_user_model
from .utils import log_organization_operation
from audit.utils import AuditLogMixin, log_organization_audit

logger = logging.getLogger(__name__)



class OrganizationSerializer(serializers.ModelSerializer):
    """组织序列化器 - 用于详情展示"""
    verification_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'code', 'leader_name', 'leader_title',
            'organization_type', 'enterprise_type', 'university_type',
            'other_type', 'organization_nature', 'business_scope', 'regulatory_authority',
            'license_info', 'service_target', 'industry_or_discipline', 'scale',
            'contact_person', 'contact_position', 'contact_phone', 'contact_email',
            'address', 'postal_code', 'description', 'website', 'logo',
            'status', 'verified_at', 'verification_image', 'established_date', 
            'created_at', 'updated_at'
        ]
    
    def get_verification_image(self, obj):
        """将认证图片的相对路径转换为完整URL"""
        return build_media_urls_list(obj.verification_image)


class OrganizationMemberSerializer(serializers.ModelSerializer):
    """组织成员序列化器 - 用于管理界面显示"""
    user_info = serializers.SerializerMethodField()
    permission_display = serializers.CharField(source='get_permission_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = OrganizationUser
        fields = [
            'id', 'user_info', 'position', 'department', 'permission', 'permission_display',
            'status', 'status_display', 'created_at', 'updated_at'
        ]
    
    def get_user_info(self, obj):
        """获取用户基本信息（脱敏处理）"""
        from .utils import get_organization_member_display_data
        
        # 检查当前用户权限，决定是否脱敏
        request = self.context.get('request')
        mask_sensitive = True
        
        if request and request.user:
            from .utils import check_organization_permission
            # 管理员及以上权限可以查看完整信息
            if check_organization_permission(request.user, obj.organization, 'admin'):
                mask_sensitive = False
        
        return get_organization_member_display_data(obj, mask_sensitive)['user_info'] if hasattr(obj, 'user') else None


class OrganizationMemberUpdateSerializer(serializers.ModelSerializer):
    """组织成员更新序列化器 - 允许修改权限、状态、职位和部门"""
    
    class Meta:
        model = OrganizationUser
        fields = ['permission', 'status', 'position', 'department']
    
    def validate(self, data):
        """验证更新数据"""
        from .utils import validate_organization_member_update
        
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("无法获取当前用户信息")
        
        organization = self.instance.organization
        
        # 只对权限和状态变更进行权限验证
        permission_status_data = {k: v for k, v in data.items() if k in ['permission', 'status']}
        if permission_status_data:
            is_valid, error_message = validate_organization_member_update(
                permission_status_data, request.user, self.instance, organization
            )
            
            if not is_valid:
                raise serializers.ValidationError(error_message)
        
        return data
    
    def update(self, instance, validated_data):
        """更新组织成员信息并记录日志"""
        from .utils import log_organization_operation
        from notification.services import org_notification_service
        
        request = self.context.get('request')
        old_data = {
            'permission': instance.permission,
            'status': instance.status,
            'position': instance.position,
            'department': instance.department,
        }
        
        # 更新实例
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 记录操作日志和发送通知
        if request and request.user:
            permission_changed = 'permission' in validated_data and old_data['permission'] != validated_data['permission']
            status_changed = 'status' in validated_data and old_data['status'] != validated_data['status']
            
            # 情况1：只修改权限
            if permission_changed and not status_changed:
                from .views import _get_operation_by_permission_change
                operation = _get_operation_by_permission_change(old_data['permission'], validated_data['permission'])
                
                log_organization_operation(
                    user=request.user,
                    organization=instance.organization,
                    operation=operation,
                    target_user=instance.user,
                    details={
                        'old_permission': old_data['permission'],
                        'new_permission': validated_data['permission'],
                        'single_member_update': True
                    }
                )
                
                # 发送权限变更通知
                try:
                    org_notification_service.send_organization_permission_change_notification(
                        target_user=instance.user,
                        operator=request.user,
                        organization_name=instance.organization.name,
                        old_permission=old_data['permission'],
                        new_permission=validated_data['permission']
                    )
                except Exception as e:
                    logger.error(f"发送权限变更通知失败: {str(e)}")
            
            # 情况2：只修改状态
            elif status_changed and not permission_changed:
                from .views import _get_operation_by_status_change
                operation = _get_operation_by_status_change(old_data['status'], validated_data['status'])
                
                log_organization_operation(
                    user=request.user,
                    organization=instance.organization,
                    operation=operation,
                    target_user=instance.user,
                    details={
                        'old_status': old_data['status'],
                        'new_status': validated_data['status'],
                        'single_member_update': True
                    }
                )
                
                # 发送状态变更通知
                try:
                    # 特殊处理：注册审核拒绝（permission保持pending，只修改status从pending到rejected）
                    if (old_data['status'] == 'pending' and validated_data['status'] == 'rejected' and 
                        old_data['permission'] == 'pending'):
                        org_notification_service.send_user_registration_review_result(
                            user=instance.user,
                            organization=instance.organization,
                            approved=False,
                            reviewer=request.user
                        )
                    else:
                        # 一般状态变更通知
                        org_notification_service.send_organization_status_change_notification(
                            target_user=instance.user,
                            operator=request.user,
                            organization_name=instance.organization.name,
                            old_status=old_data['status'],
                            new_status=validated_data['status']
                        )
                except Exception as e:
                    logger.error(f"发送状态变更通知失败: {str(e)}")
            
            # 情况3：同时修改权限和状态
            elif permission_changed and status_changed:
                # 记录权限变更日志
                from .views import _get_operation_by_permission_change
                permission_operation = _get_operation_by_permission_change(old_data['permission'], validated_data['permission'])
                
                log_organization_operation(
                    user=request.user,
                    organization=instance.organization,
                    operation=permission_operation,
                    target_user=instance.user,
                    details={
                        'old_permission': old_data['permission'],
                        'new_permission': validated_data['permission'],
                        'single_member_update': True
                    }
                )
                
                # 记录状态变更日志
                from .views import _get_operation_by_status_change
                status_operation = _get_operation_by_status_change(old_data['status'], validated_data['status'])
                
                log_organization_operation(
                    user=request.user,
                    organization=instance.organization,
                    operation=status_operation,
                    target_user=instance.user,
                    details={
                        'old_status': old_data['status'],
                        'new_status': validated_data['status'],
                        'single_member_update': True
                    }
                )
                
                # 发送通知
                try:
                    # 特殊处理：注册审核通过（permission从pending改为member且status从pending改为approved）
                    if (old_data['permission'] == 'pending' and validated_data['permission'] == 'member' and
                        old_data['status'] == 'pending' and validated_data['status'] == 'approved'):
                        org_notification_service.send_user_registration_review_result(
                            user=instance.user,
                            organization=instance.organization,
                            approved=True,
                            reviewer=request.user
                        )
                    else:
                        # 一般权限和状态同时变更通知
                        org_notification_service.send_organization_permission_and_status_change_notification(
                            target_user=instance.user,
                            operator=request.user,
                            organization_name=instance.organization.name,
                            old_permission=old_data['permission'],
                            new_permission=validated_data['permission'],
                            old_status=old_data['status'],
                            new_status=validated_data['status']
                        )
                except Exception as e:
                    logger.error(f"发送权限和状态变更通知失败: {str(e)}")
        
        return instance


class OrganizationMemberListSerializer(serializers.ModelSerializer):
    """组织成员列表序列化器 - 只包含必要字段"""
    username = serializers.CharField(source='user.username', read_only=True)
    real_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = OrganizationUser
        fields = [
            'id', 'username', 'real_name', 'phone', 'email', 'avatar',
            'department', 'position', 'permission', 'status', 'created_at'
        ]
    
    def get_real_name(self, obj):
        """获取真实姓名"""
        from .utils import mask_name
        
        user = obj.user
        request = self.context.get('request')
        
        # 检查是否需要脱敏
        mask_sensitive = True
        if request and request.user:
            from .utils import check_organization_permission
            if check_organization_permission(request.user, obj.organization, 'admin'):
                mask_sensitive = False
        
        return mask_name(user.real_name) if mask_sensitive and user.real_name else user.real_name
    
    def get_phone(self, obj):
        """获取电话号码"""
        from .utils import mask_phone
        
        user = obj.user
        request = self.context.get('request')
        
        # 检查是否需要脱敏
        mask_sensitive = True
        if request and request.user:
            from .utils import check_organization_permission
            if check_organization_permission(request.user, obj.organization, 'admin'):
                mask_sensitive = False
        
        return mask_phone(user.phone) if mask_sensitive and user.phone else user.phone
    
    def get_email(self, obj):
        """获取邮箱地址"""
        from .utils import mask_email
        
        user = obj.user
        request = self.context.get('request')
        
        # 检查是否需要脱敏
        mask_sensitive = True
        if request and request.user:
            from .utils import check_organization_permission
            if check_organization_permission(request.user, obj.organization, 'admin'):
                mask_sensitive = False
        
        return mask_email(user.email) if mask_sensitive else user.email
    
    def get_avatar(self, obj):
        """获取用户头像"""
        user = obj.user
        request = self.context.get('request')
        
        if user.avatar:
            return build_media_url(user.avatar, request)
        return None


class OrganizationUpdateSerializer(AuditLogMixin, serializers.ModelSerializer):
    """组织信息更新序列化器"""
    
    class Meta:
        model = Organization
        fields = [
            'name', 'leader_name', 'leader_title', 
            'enterprise_type', 'university_type', 'other_type', 'organization_nature',
            'business_scope', 'regulatory_authority', 'service_target',
            'industry_or_discipline', 'scale',
            'contact_person', 'contact_position', 'contact_phone', 'contact_email',
            'address', 'postal_code', 'description', 'website', 'established_date'
        ]
    
    def validate(self, data):
        """验证组织信息更新数据"""
        organization = self.instance
        
        # 根据组织类型验证特定字段
        if organization.organization_type == 'enterprise':
            if 'university_type' in data and data['university_type']:
                raise serializers.ValidationError('企业不能设置大学类型')
        elif organization.organization_type == 'university':
            if 'enterprise_type' in data and data['enterprise_type']:
                raise serializers.ValidationError('大学不能设置企业类型')
        
        # 不允许在更新组织信息时修改认证图片
        if 'verification_image' in data:
            raise serializers.ValidationError('更新组织信息时不允许修改认证图片，请使用专门的认证图片上传接口')
        
        return data
    
    def update(self, instance, validated_data):
        """更新组织信息并记录审核历史"""
        # 记录原始状态
        original_status = instance.status
        
        # 更新实例
        updated_instance = super().update(instance, validated_data)
        
        # 如果状态发生变更，记录审核历史
        if original_status != updated_instance.status:
            log_organization_audit(
                organization=updated_instance,
                action='status_change',
                old_status=original_status,
                new_status=updated_instance.status,
                comment='组织信息更新导致状态变更',
                request=self.context.get('request')
            )
        
        return updated_instance


class OrganizationLogoUploadSerializer(serializers.ModelSerializer):
    """组织logo上传序列化器"""
    
    class Meta:
        model = Organization
        fields = ['logo']
    
    def validate_logo(self, value):
        """验证logo文件"""
        if value:
            # 检查文件大小（限制为5MB）
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError('文件大小不能超过5MB')
            
            # 检查文件类型
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError('只支持JPEG、PNG、GIF、WebP格式的图片')
        
        return value


class OrganizationOperationLogSerializer(serializers.ModelSerializer):
    """组织操作日志序列化器"""
    operator = serializers.SerializerMethodField()
    target_user = serializers.SerializerMethodField()
    operation_display = serializers.CharField(source='get_operation_display', read_only=True)
    
    class Meta:
        model = OrganizationOperationLog
        fields = [
            'id', 'operator', 'target_user', 'operation', 'operation_display',
            'details', 'ip_address', 'created_at'
        ]
    
    def get_operator(self, obj):
        """获取操作者信息"""
        if obj.operator:
            return {
                'id': str(obj.operator.id),
                'username': obj.operator.username,
                'real_name': obj.operator.real_name or obj.operator.username
            }
        return None
    
    def get_target_user(self, obj):
        """获取目标用户信息"""
        if obj.target_user:
            return {
                'id': str(obj.target_user.id),
                'username': obj.target_user.username,
                'real_name': obj.target_user.real_name or obj.target_user.username
            }
        return None


class OrganizationVerificationMaterialsSerializer(serializers.ModelSerializer):
    """组织认证材料提交序列化器 - 合并文本信息和图片上传"""
    # 认证图片字段
    verification_image_1 = serializers.ImageField(required=True, help_text="认证图片1（必填）")
    verification_image_2 = serializers.ImageField(required=False, help_text="认证图片2（可选）")
    verification_image_3 = serializers.ImageField(required=False, help_text="认证图片3（可选）")
    verification_image_4 = serializers.ImageField(required=False, help_text="认证图片4（可选）")
    verification_image_5 = serializers.ImageField(required=False, help_text="认证图片5（可选）")
    
    class Meta:
        model = Organization
        fields = [
            # 基本信息
            'code', 'leader_name', 'leader_title',
            'contact_person', 'contact_position', 'contact_phone', 'contact_email',
            'address', 'postal_code', 'description', 'website', 'established_date',
            # 企业特定字段
            'enterprise_type',
            # 学校特定字段
            'university_type',
            # 其他组织特定字段
            'other_type', 'organization_nature', 'business_scope', 'regulatory_authority',
            'license_info', 'service_target',
            # 认证图片
            'verification_image_1', 'verification_image_2', 'verification_image_3',
            'verification_image_4', 'verification_image_5'
        ]
    
    def validate_verification_image_1(self, value):
        """验证第一张认证图片（必填）"""
        return self._validate_image_file(value, "第一张认证图片")
    
    def validate_verification_image_2(self, value):
        """验证第二张认证图片"""
        if value:
            return self._validate_image_file(value, "第二张认证图片")
        return value
    
    def validate_verification_image_3(self, value):
        """验证第三张认证图片"""
        if value:
            return self._validate_image_file(value, "第三张认证图片")
        return value
    
    def validate_verification_image_4(self, value):
        """验证第四张认证图片"""
        if value:
            return self._validate_image_file(value, "第四张认证图片")
        return value
    
    def validate_verification_image_5(self, value):
        """验证第五张认证图片"""
        if value:
            return self._validate_image_file(value, "第五张认证图片")
        return value
    
    def _validate_image_file(self, value, field_name):
        """验证图片文件"""
        if value:
            # 检查文件大小（限制为10MB）
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError(f'{field_name}文件大小不能超过10MB')
            
            # 检查文件类型
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/jpg']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(f'{field_name}只支持JPEG、PNG、GIF、WebP格式的图片')
        
        return value
    
    def validate(self, data):
        """验证整体数据"""
        # 验证必填字段
        organization = self.instance
        if organization:
            required_fields = organization.get_required_fields_for_verification()
            missing_fields = []
            
            for field in required_fields:
                value = data.get(field, '').strip() if isinstance(data.get(field), str) else data.get(field)
                if not value:
                    missing_fields.append(field)
            
            if missing_fields:
                field_display_names = organization.get_field_display_names()
                missing_field_names = []
                for field in missing_fields:
                    display_name = field_display_names.get(field, field)
                    missing_field_names.append(display_name)
                
                raise serializers.ValidationError({
                    'missing_fields': missing_fields,
                    'message': f'请填写必填字段: {", ".join(missing_field_names)}'
                })
        
        return data
    
    def save(self, **kwargs):
        """保存认证材料和图片"""
        from django.db import transaction
        
        instance = self.instance
        original_status = instance.status
        
        # 使用数据库事务确保操作原子性
        with transaction.atomic():
            image_urls = []
            
            # 处理上传的图片文件
            for i in range(1, 6):
                field_name = f'verification_image_{i}'
                image_file = self.validated_data.pop(field_name, None)
                
                if image_file:
                    # 保存图片文件并获取URL
                    image_url = self._save_image_file(image_file, f'verification_{instance.id}_{i}')
                    if image_url:
                        image_urls.append(image_url)
            
            # 更新组织信息
            for field, value in self.validated_data.items():
                if hasattr(instance, field):
                    setattr(instance, field, value)
            
            # 更新认证图片
            instance.verification_image = image_urls
            
            # 状态判断逻辑：当前状态为审核失败时重置为待审核
            if instance.status == 'rejected':
                instance.status = 'under_review'
            elif instance.status not in ['under_review', 'verified']:
                # 其他状态（如pending）也设置为under_review
                instance.status = 'under_review'
            
            instance.save()
            
            # 记录审核历史
            if original_status != instance.status:
                log_organization_audit(
                    organization=instance,
                    action='status_change',
                    old_status=original_status,
                    new_status=instance.status,
                    comment='重新提交认证材料，状态自动更新',
                    request=self.context.get('request')
                )
        
        return instance
    
    def _save_image_file(self, image_file, filename_prefix):
        """保存图片文件并返回URL"""
        import os
        from django.conf import settings
        from django.core.files.storage import default_storage
        
        try:
            # 生成文件名
            file_extension = os.path.splitext(image_file.name)[1]
            filename = f'{filename_prefix}{file_extension}'
            # 以组织ID命名的文件夹
            file_path = f'organization/verification_images/{self.instance.id}/{filename}'
            
            # 保存文件
            saved_path = default_storage.save(file_path, image_file)
            
            # 返回文件URL
            return default_storage.url(saved_path)
        except Exception as e:
            raise serializers.ValidationError(f'图片保存失败: {str(e)}')


class OrganizationConfigSerializer(serializers.ModelSerializer):
    """组织配置序列化器"""
    
    class Meta:
        model = OrganizationConfig
        fields = [
            'auto_approve_members', 'require_email_verification', 'allow_member_invite',
            'admin_can_manage_admins', 'member_can_view_all', 'max_members', 'welcome_message'
        ]