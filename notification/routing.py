from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 通知WebSocket路由
    re_path(r'ws/notification/(?P<user_id>\d+)/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/notification/broadcast/$', consumers.NotificationBroadcastConsumer.as_asgi()),

]