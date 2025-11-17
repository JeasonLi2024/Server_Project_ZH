import os
import json
import logging
from datetime import timedelta
from datetime import datetime

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _code_length():
    try:
        return int(getattr(settings, 'PHONE_VERIFICATION_CODE_LENGTH', getattr(settings, 'EMAIL_VERIFICATION_CODE_LENGTH', 6)))
    except Exception:
        return 6


def _code_expire_seconds():
    try:
        return int(getattr(settings, 'PHONE_VERIFICATION_CODE_EXPIRE', getattr(settings, 'EMAIL_VERIFICATION_CODE_EXPIRE', 300)))
    except Exception:
        return 300


def _interval_seconds():
    try:
        return int(getattr(settings, 'PHONE_CODE_INTERVAL_SECONDS', 60))
    except Exception:
        return 60


def _sign_name():
    try:
        return getattr(settings, 'ALIYUN_SMS_SIGN_NAME', '速通互联验证码')
    except Exception:
        return '速通互联验证码'


def _template_code_for(code_type: str) -> str:
    mapping = {
        'register': getattr(settings, 'ALIYUN_SMS_TEMPLATE_REGISTER', '100001'),
        'login': getattr(settings, 'ALIYUN_SMS_TEMPLATE_LOGIN', '100001'),
        'reset_password': getattr(settings, 'ALIYUN_SMS_TEMPLATE_RESET_PASSWORD', '100003'),
        'change_phone': getattr(settings, 'ALIYUN_SMS_TEMPLATE_CHANGE_PHONE', '100002'),
        'bind_new_phone': getattr(settings, 'ALIYUN_SMS_TEMPLATE_BIND_NEW_PHONE', '100004'),
        'verify_phone': getattr(settings, 'ALIYUN_SMS_TEMPLATE_VERIFY_PHONE', '100005'),
    }
    return mapping.get(code_type, '100001')


def create_client():
    from alibabacloud_dypnsapi20170525.client import Client as Dypnsapi20170525Client
    from alibabacloud_tea_openapi import models as open_api_models
    ak = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
    sk = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    if not ak or not sk:
        raise ImportError('缺少阿里云AK环境变量(ALIBABA_CLOUD_ACCESS_KEY_ID/ALIBABA_CLOUD_ACCESS_KEY_SECRET)')
    config = open_api_models.Config(access_key_id=ak, access_key_secret=sk)
    config.endpoint = 'dypnsapi.aliyuncs.com'
    return Dypnsapi20170525Client(config)


def _get_cache():
    try:
        from django.core.cache import cache as dj_cache
        try:
            dj_cache.get('__probe__')
            return dj_cache
        except Exception:
            pass
    except Exception:
        class _LocalCache:
            def __init__(self):
                self.s = {}
            def get(self, k):
                return self.s.get(k)
            def set(self, k, v, timeout=None):
                self.s[k] = v
        return _LocalCache()
    class _LocalCache:
        def __init__(self):
            self.s = {}
        def get(self, k):
            return self.s.get(k)
        def set(self, k, v, timeout=None):
            self.s[k] = v
    return _LocalCache()

def _now():
    try:
        return timezone.now()
    except Exception:
        return datetime.now()


def _generate_code(length: int) -> str:
    try:
        from .verification_utils import generate_verification_code
        return generate_verification_code(length)
    except Exception:
        import random
        return ''.join(random.choices('0123456789', k=length))


def send_phone_verification_code(phone: str, code_type: str):
    try:
        limit_key = f"phone_code_limit:{phone}:{code_type}"
        c = _get_cache()
        if c.get(limit_key):
            return False, {'message': '发送过于频繁'}

        code = _generate_code(_code_length())
        client = create_client()
        template_param = json.dumps({
            'code': code,
            'min': str(max(1, _code_expire_seconds() // 60))
        })

        from alibabacloud_dypnsapi20170525 import models as dypnsapi_20170525_models
        from alibabacloud_tea_util import models as util_models

        req = dypnsapi_20170525_models.SendSmsVerifyCodeRequest(
            phone_number=phone,
            sign_name=_sign_name(),
            template_code=_template_code_for(code_type),
            template_param=template_param,
            code_length=_code_length(),
            valid_time=_code_expire_seconds(),
            duplicate_policy=1,
            interval=_interval_seconds(),
            code_type=1,
            return_verify_code=False,
            auto_retry=1,
        )
        runtime = util_models.RuntimeOptions()

        resp = client.send_sms_verify_code_with_options(req, runtime)
        body = resp.body
        success = bool(getattr(body, 'success', False) or getattr(body, 'Success', False))
        if success:
            data = {
                'code': code,
                'phone': phone,
                'code_type': code_type,
                'created_at': _now().isoformat(),
                'is_used': False,
            }
            code_key = f"phone_verification_code:{phone}:{code_type}"
            c.set(code_key, json.dumps(data), timeout=_code_expire_seconds())
            c.set(limit_key, True, _interval_seconds())
            request_id = (
                getattr(body, 'request_id', None)
                or getattr(body, 'RequestId', None)
                or getattr(body, 'requestId', None)
            )
            try:
                if not request_id and hasattr(body, 'to_map'):
                    m = body.to_map()
                    request_id = m.get('RequestId') or m.get('request_id') or m.get('requestId')
            except Exception:
                pass
            try:
                if not request_id and hasattr(resp, 'headers') and isinstance(resp.headers, dict):
                    request_id = resp.headers.get('x-acs-request-id') or resp.headers.get('X-Acs-Request-Id')
            except Exception:
                pass
            return True, {'request_id': request_id or ''}
        else:
            message = getattr(body, 'message', None) or getattr(body, 'Message', None) or '发送失败'
            req_id = getattr(body, 'request_id', None) or getattr(body, 'RequestId', None) or getattr(body, 'requestId', None)
            return False, {'message': message, 'request_id': req_id or ''}
    except ImportError as e:
        logger.error(str(e))
        return False, {'message': '短信SDK未安装或未配置'}
    except Exception as e:
        logger.exception(str(e))
        return False, {'message': str(e)}


def validate_phone_code(phone: str, code: str, code_type: str):
    try:
        c = _get_cache()
        key = f"phone_verification_code:{phone}:{code_type}"
        raw = c.get(key)
        if not raw:
            return False, '无效或已过期'
        data = json.loads(raw)
        if data.get('is_used'):
            return False, '已使用'
        if data.get('code') != code:
            return False, '错误'
        data['is_used'] = True
        c.set(key, json.dumps(data), timeout=_code_expire_seconds())
        return True, '验证成功'
    except Exception as e:
        logger.error(f"验证短信验证码异常: {e}")
        return False, '验证失败'


def verify_phone_code(phone: str, code: str, code_type: str):
    try:
        c = _get_cache()
        key = f"phone_verification_code:{phone}:{code_type}"
        raw = c.get(key)
        if not raw:
            return False, '无效或已过期'
        data = json.loads(raw)
        if data.get('is_used'):
            return False, '已使用'
        if data.get('code') != code:
            return False, '错误'
        return True, '验证成功'
    except Exception as e:
        logger.error(f"校验短信验证码异常: {e}")
        return False, '校验失败'