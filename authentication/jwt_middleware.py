from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
import logging

# 使用authentication记录器以匹配settings.py中的配置
logger = logging.getLogger('authentication')


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT认证中间件，用于WebSocket连接
    从Authorization头部或查询参数中提取JWT token并验证用户身份
    """

    def __init__(self, inner):
        print("[JWT中间件] 初始化中间件")
        super().__init__(inner)

    async def __call__(self, scope, receive, send):
        print(f"[JWT中间件] 收到请求类型: {scope['type']}, 路径: {scope.get('path', 'unknown')}")
        
        # 只处理WebSocket连接
        if scope["type"] != "websocket":
            print(f"[JWT中间件] 跳过非WebSocket请求: {scope['type']}")
            return await super().__call__(scope, receive, send)

        print(f"[JWT中间件] WebSocket连接开始处理: {scope.get('path', 'unknown')}")
        logger.info(f"[JWT中间件] WebSocket连接开始处理: {scope.get('path', 'unknown')}")
        
        # 导入Django模型（避免app registry问题）
        from django.contrib.auth.models import AnonymousUser
        
        # 尝试从不同位置获取token
        token = await self.get_token_from_scope(scope)
        print(f"[JWT中间件] 提取到的token: {'存在' if token else '不存在'}")
        logger.info(f"[JWT中间件] 提取到的token: {'存在' if token else '不存在'}")
        
        if token:
            user = await self.get_user_from_token(token)
            if user:
                scope["user"] = user
                logger.info(f"WebSocket JWT认证成功: 用户ID {user.id}")
            else:
                scope["user"] = AnonymousUser()
                logger.warning("WebSocket JWT认证失败: 无效token")
        else:
            scope["user"] = AnonymousUser()
            logger.warning("WebSocket连接未提供JWT token")

        return await super().__call__(scope, receive, send)

    async def get_token_from_scope(self, scope):
        """
        从WebSocket scope中提取JWT token
        支持从Authorization头部和查询参数中获取
        """
        # 1. 尝试从headers中获取Authorization
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization")
        
        if auth_header:
            try:
                auth_header = auth_header.decode("utf-8")
                if auth_header.startswith("Bearer "):
                    return auth_header.split(" ")[1]
            except (UnicodeDecodeError, IndexError):
                pass

        # 2. 尝试从查询参数中获取token
        query_string = scope.get("query_string", b"").decode("utf-8")
        if query_string:
            from urllib.parse import parse_qs
            query_params = parse_qs(query_string)
            token_list = query_params.get("token")
            if token_list:
                return token_list[0]

        return None

    @database_sync_to_async
    def get_user_from_token(self, token):
        """
        从JWT token中获取用户对象
        """
        try:
            # 导入JWT相关模块（避免app registry问题）
            from rest_framework_simplejwt.tokens import AccessToken
            from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # 验证并解析token
            access_token = AccessToken(token)
            user_id = access_token.get("user_id")
            
            if user_id:
                user = User.objects.get(id=user_id)
                return user
        except (InvalidToken, TokenError, User.DoesNotExist) as e:
            logger.error(f"JWT token验证失败: {str(e)}")
        except Exception as e:
            logger.error(f"获取用户失败: {str(e)}")
        
        return None


def JWTAuthMiddlewareStack(inner):
    """
    JWT认证中间件栈
    """
    return JWTAuthMiddleware(inner)