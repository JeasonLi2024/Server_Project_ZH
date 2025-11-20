from django.urls import re_path
from django.conf import settings
from . import consumers

_prefix = (getattr(settings, 'PROXY_PATH_PREFIX', '') or '').strip('/')
if _prefix:
    websocket_urlpatterns = [
        re_path(rf'{_prefix}/ws/notification/(?P<user_id>\d+)/$', consumers.NotificationConsumer.as_asgi()),
        re_path(rf'{_prefix}/ws/notification/broadcast/$', consumers.NotificationBroadcastConsumer.as_asgi()),
        re_path(r'ws/notification/(?P<user_id>\d+)/$', consumers.NotificationConsumer.as_asgi()),
        re_path(r'ws/notification/broadcast/$', consumers.NotificationBroadcastConsumer.as_asgi()),
    ]
else:
    websocket_urlpatterns = [
        re_path(r'ws/notification/(?P<user_id>\d+)/$', consumers.NotificationConsumer.as_asgi()),
        re_path(r'ws/notification/broadcast/$', consumers.NotificationBroadcastConsumer.as_asgi()),
    ]