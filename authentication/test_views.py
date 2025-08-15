# authentication/test_views.py
# 测试专用API视图

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.contrib.auth import get_user_model
import json
import random
import string
from datetime import datetime, timedelta

User = get_user_model()

# 只在DEBUG模式下启用测试API
def test_api_required(func):
    def wrapper(request, *args, **kwargs):
        if not settings.DEBUG:
            return JsonResponse({
                'success': False,
                'message': '测试API仅在DEBUG模式下可用'
            }, status=403)
        return func(request, *args, **kwargs)
    return wrapper

@csrf_exempt
@require_http_methods(["POST"])
@test_api_required
def create_test_verification_code(request):
    """
    创建测试用验证码
    POST /api/v1/auth/test/create-code/
    {
        "email": "test@example.com",
        "code": "123456",  # 可选，不提供则自动生成
        "expire_seconds": 300  # 可选，默认300秒
    }
    """
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({
                'success': False,
                'message': '邮箱地址不能为空'
            }, status=400)
        
        # 生成或使用提供的验证码
        code = data.get('code')
        if not code:
            if hasattr(settings, 'USE_FIXED_VERIFICATION_CODE') and settings.USE_FIXED_VERIFICATION_CODE:
                code = getattr(settings, 'FIXED_VERIFICATION_CODE', '123456')
            else:
                code = ''.join(random.choices(string.digits, k=6))
        
        # 设置过期时间
        expire_seconds = data.get('expire_seconds', 300)
        
        # 存储到缓存
        cache_key = f"email_verification_code:{email}"
        cache.set(cache_key, code, expire_seconds)
        
        return JsonResponse({
            'success': True,
            'message': '测试验证码创建成功',
            'data': {
                'email': email,
                'code': code,
                'expire_seconds': expire_seconds,
                'cache_key': cache_key
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'创建验证码失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET", "POST"])
@test_api_required
def get_test_verification_code(request):
    """
    获取测试用验证码
    GET /api/v1/auth/test/get-code/?email=test@example.com
    POST /api/v1/auth/test/get-code/
    {
        "email": "test@example.com"
    }
    """
    try:
        if request.method == 'GET':
            email = request.GET.get('email')
        else:
            data = json.loads(request.body)
            email = data.get('email')
        
        if not email:
            return JsonResponse({
                'success': False,
                'message': '邮箱地址不能为空'
            }, status=400)
        
        # 从缓存获取验证码
        cache_key = f"email_verification_code:{email}"
        code = cache.get(cache_key)
        
        if code:
            # 获取剩余过期时间
            ttl = cache.ttl(cache_key) if hasattr(cache, 'ttl') else None
            
            return JsonResponse({
                'success': True,
                'message': '验证码获取成功',
                'data': {
                    'email': email,
                    'code': code,
                    'ttl_seconds': ttl,
                    'cache_key': cache_key
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '验证码不存在或已过期',
                'data': {
                    'email': email,
                    'cache_key': cache_key
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'获取验证码失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@test_api_required
def batch_create_test_codes(request):
    """
    批量创建测试验证码（用于压力测试数据准备）
    POST /api/v1/auth/test/batch-create-codes/
    {
        "email_prefix": "test",
        "email_domain": "example.com",
        "count": 100,
        "code": "123456",  # 可选，统一验证码
        "expire_seconds": 300
    }
    """
    try:
        data = json.loads(request.body)
        email_prefix = data.get('email_prefix', 'test')
        email_domain = data.get('email_domain', 'example.com')
        count = min(data.get('count', 10), 1000)  # 限制最大1000个
        expire_seconds = data.get('expire_seconds', 300)
        
        # 生成统一验证码或随机验证码
        fixed_code = data.get('code')
        if not fixed_code and hasattr(settings, 'USE_FIXED_VERIFICATION_CODE') and settings.USE_FIXED_VERIFICATION_CODE:
            fixed_code = getattr(settings, 'FIXED_VERIFICATION_CODE', '123456')
        
        created_codes = []
        
        for i in range(count):
            email = f"{email_prefix}{i+1}@{email_domain}"
            code = fixed_code if fixed_code else ''.join(random.choices(string.digits, k=6))
            
            cache_key = f"email_verification_code:{email}"
            cache.set(cache_key, code, expire_seconds)
            
            created_codes.append({
                'email': email,
                'code': code,
                'cache_key': cache_key
            })
        
        return JsonResponse({
            'success': True,
            'message': f'批量创建 {count} 个测试验证码成功',
            'data': {
                'count': count,
                'expire_seconds': expire_seconds,
                'codes': created_codes[:10],  # 只返回前10个，避免响应过大
                'total_created': len(created_codes)
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'批量创建验证码失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
@test_api_required
def clear_test_verification_codes(request):
    """
    清理测试验证码
    DELETE /api/v1/auth/test/clear-codes/
    {
        "email_pattern": "test*@example.com"  # 可选，匹配模式
    }
    """
    try:
        # 这里简化实现，实际可以根据需要扩展
        return JsonResponse({
            'success': True,
            'message': '测试验证码清理功能需要根据具体缓存实现',
            'note': '可以重启Redis或等待验证码自然过期'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'清理验证码失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@test_api_required
def test_api_status(request):
    """
    测试API状态检查
    GET /api/v1/auth/test/status/
    """
    return JsonResponse({
        'success': True,
        'message': '测试API正常运行',
        'data': {
            'debug_mode': settings.DEBUG,
            'test_mode': getattr(settings, 'TEST_MODE', False),
            'email_backend': settings.EMAIL_BACKEND,
            'use_fixed_code': getattr(settings, 'USE_FIXED_VERIFICATION_CODE', False),
            'fixed_code': getattr(settings, 'FIXED_VERIFICATION_CODE', None),
            'cache_backend': settings.CACHES['default']['BACKEND'],
            'timestamp': datetime.now().isoformat()
        }
    })