"""
自定义密码验证器
使用项目中的 check_password_strength 函数进行密码验证
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from .utils import check_password_strength


class CustomPasswordStrengthValidator:
    """
    自定义密码强度验证器
    使用项目中的 check_password_strength 函数进行验证
    """
    
    def validate(self, password, user=None):
        """验证密码强度"""
        is_valid, message = check_password_strength(password)
        if not is_valid:
            raise ValidationError(
                _(message),
                code='password_too_weak',
            )
    
    def get_help_text(self):
        """返回密码要求的帮助文本"""
        return _(
            "密码必须至少8位，且包含大写字母、小写字母、数字、特殊字符中的至少两种。"
        )