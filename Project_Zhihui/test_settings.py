# test_settings.py
# JMeter 压力测试专用设置文件

from .settings import *

# ==================== 邮件配置 ====================
# 使用控制台邮件后端，不发送真实邮件
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 或者使用虚拟邮件后端（完全不发送）
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

# 或者使用文件邮件后端（保存到文件）
# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = BASE_DIR / 'test_emails'

# ==================== 验证码配置 ====================
# 启用固定验证码模式（用于压力测试）
USE_FIXED_VERIFICATION_CODE = True
FIXED_VERIFICATION_CODE = '123456'

# 禁用邮件发送频率限制（测试用）
EMAIL_RATE_LIMIT_DISABLED = True

# 缩短验证码有效期（加快测试速度）
EMAIL_VERIFICATION_CODE_EXPIRE = 600  # 10分钟

# ==================== 缓存配置 ====================
# 使用独立的Redis数据库进行测试
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/2"),  # 使用数据库2
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# ==================== 数据库配置 ====================
# 使用独立的测试数据库
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "bupt_zh_showDB",  # 测试数据库
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ==================== JWT配置 ====================
# 延长Token有效期（减少刷新频率）
SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
})

# ==================== 日志配置 ====================
# 简化日志输出
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'WARNING',  # 只记录警告和错误
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'test.log',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# ==================== 性能优化 ====================
# 禁用一些中间件以提高性能
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",  # 测试时可以禁用CSRF
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # "django.middleware.clickjacking.XFrameOptionsMiddleware",  # 测试时可以禁用
]

# 允许所有来源（测试用）
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ==================== 测试标识 ====================
TEST_MODE = True
print("\n" + "="*50)
print("🧪 测试模式已启用")
print("📧 邮件后端: 控制台输出")
print("🔑 固定验证码: 123456")
print("🚀 性能优化: 已启用")
print("="*50 + "\n")