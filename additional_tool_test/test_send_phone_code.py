import os
import sys

# 纯函数路径测试：不初始化Django，直接替换依赖为本地桩

from authentication import phone_verification as pv

class _Body:
    def __init__(self):
        self.success = True
        self.request_id = 'TEST_REQUEST_ID'
        self.message = 'OK'

class _Resp:
    def __init__(self):
        self.body = _Body()

class _Client:
    def send_sms_verify_code_with_options(self, req, runtime):
        return _Resp()

pv.create_client = lambda: _Client()
pv._code_length = lambda: 6
pv._code_expire_seconds = lambda: 300
pv._interval_seconds = lambda: 60
pv._sign_name = lambda: '速通互联验证码'

class _Settings:
    PHONE_VERIFICATION_CODE_LENGTH = 6
    PHONE_VERIFICATION_CODE_EXPIRE = 300
    PHONE_CODE_INTERVAL_SECONDS = 60
    ALIYUN_SMS_SIGN_NAME = '速通互联验证码'

pv.settings = _Settings()

import datetime as _dt
class _TZ:
    @staticmethod
    def now():
        return _dt.datetime.now()

pv.timezone = _TZ()

class _Cache:
    def __init__(self):
        self.store = {}
    def get(self, k):
        return self.store.get(k)
    def set(self, k, v, timeout=None):
        self.store[k] = v

pv.cache = _Cache()

def main():
    phone = '17209063396'
    code_type = 'login'
    ok, result = pv.send_phone_verification_code(phone, code_type)
    print({'ok': ok, 'result': result})

if __name__ == '__main__':
    main()