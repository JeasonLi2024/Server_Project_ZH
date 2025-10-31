"""
ASGI config for Project_Zhihui project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from authentication.jwt_middleware import JWTAuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Project_Zhihui.settings")

print("[ASGI] 正在加载ASGI应用...")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from notification.routing import websocket_urlpatterns

print("[ASGI] 正在创建WebSocket路由...")
print(f"[ASGI] WebSocket URL模式: {websocket_urlpatterns}")

# 创建JWT中间件栈
print("[ASGI] 正在创建JWT中间件栈...")
jwt_middleware_stack = JWTAuthMiddlewareStack(
    URLRouter(
        websocket_urlpatterns
    )
)
print("[ASGI] JWT中间件栈创建完成")

# 临时移除AllowedHostsOriginValidator进行测试
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": jwt_middleware_stack,
})

print("[ASGI] 已移除AllowedHostsOriginValidator进行调试")

print("[ASGI] ASGI应用创建完成")
