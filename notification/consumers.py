import json
import logging
import redis.asyncio as redis
import time
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from .models import Notification
from .serializers import NotificationSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """通知WebSocket消费者"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初始化Redis连接
        try:
            self.redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
        except Exception as e:
            logger.error(f"Redis连接失败: {str(e)}")
            self.redis_client = None
    
    async def connect(self):
        """WebSocket连接"""
        start_time = time.time()
        logger.info(f"Connect start: {start_time}")
        self.user = self.scope["user"]
        
        # 检查用户是否已认证
        if isinstance(self.user, AnonymousUser):
            logger.warning("未认证用户尝试连接WebSocket")
            await self.close()
            return
        
        # 设置房间组名
        self.room_group_name = f'notifications_{self.user.id}'
        
        # 加入房间组
        t1 = time.time()
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"Joined group in {time.time() - t1:.4f}s")
        
        # 接受WebSocket连接
        t2 = time.time()
        await self.accept()
        logger.info(f"Accepted connection in {time.time() - t2:.4f}s")
        
        # 将用户添加到在线用户集合
        t3 = time.time()
        await self.add_user_to_online_set()
        logger.info(f"Added to online set in {time.time() - t3:.4f}s")
        
        logger.info(f"用户 {self.user.id} 连接到通知WebSocket")
        
        # 发送当前未读通知数量
        t4 = time.time()
        await self.send_unread_count()
        logger.info(f"Sent unread count in {time.time() - t4:.4f}s")

        # 启动心跳任务
        # self.heartbeat_task = asyncio.create_task(self.send_heartbeat())
        
        logger.info(f"Connect finished. Total duration: {time.time() - start_time:.4f}s")

    async def disconnect(self, close_code):
        """WebSocket断开连接"""
        # 取消心跳任务
        if hasattr(self, 'heartbeat_task'):
            self.heartbeat_task.cancel()
            try:
                # 使用 wait_for 防止取消任务挂起
                await asyncio.wait_for(self.heartbeat_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.error(f"取消心跳任务出错: {e}")

        try:
            if hasattr(self, 'room_group_name'):
                # 离开房间组，增加超时保护
                await asyncio.wait_for(
                    self.channel_layer.group_discard(
                        self.room_group_name,
                        self.channel_name
                    ),
                    timeout=2.0
                )
        except Exception as e:
            logger.error(f"离开房间组失败: {str(e)}")
        
        # 从在线用户集合中移除用户，增加超时保护
        try:
            await asyncio.wait_for(self.remove_user_from_online_set(), timeout=2.0)
        except Exception as e:
            logger.error(f"移除在线用户失败: {str(e)}")
            
        # 关闭Redis连接
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except Exception as e:
                logger.error(f"关闭Redis连接失败: {str(e)}")
        
        logger.info(f"用户 {self.user.id if hasattr(self, 'user') else 'Unknown'} 断开通知WebSocket连接, code: {close_code}")

    async def send_heartbeat(self):
        """发送应用层心跳包"""
        try:
            while True:
                await asyncio.sleep(20)  # 每20秒发送一次
                await self.send(text_data=json.dumps({
                    'type': 'ping',
                    'message': 'keepalive'
                }, ensure_ascii=False))
                logger.debug(f"已发送心跳包给用户 {self.user.id}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"发送心跳包失败: {str(e)}")

    
    async def receive(self, text_data=None, bytes_data=None):
        """接收WebSocket消息"""
        logger.info(f"Receive called - text_data: {bool(text_data)}, bytes_data: {bool(bytes_data)}")
        if text_data:
            logger.info(f"收到文本数据: {text_data[:100]}")
        
        try:
            if text_data:
                text_data_json = json.loads(text_data)
                message_type = text_data_json.get('type')
                
                if message_type == 'mark_as_read':
                    # 标记通知为已读
                    notification_id = text_data_json.get('notification_id')
                    if notification_id:
                        await self.mark_notification_as_read(notification_id)
                
                elif message_type == 'get_unread_count':
                    # 获取未读通知数量
                    await self.send_unread_count()
                
                elif message_type == 'get_recent_notifications':
                    # 获取最近的通知
                    limit = text_data_json.get('limit', 10)
                    await self.send_recent_notifications(limit)
                
                elif message_type == 'ping':
                    # 处理心跳包
                    logger.info(f"收到心跳包: {self.user.id}")
                    await self.send(text_data=json.dumps({
                        'type': 'pong',
                        'message': 'pong'
                    }, ensure_ascii=False))

                else:
                    logger.warning(f"未知的消息类型: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("接收到无效的JSON数据")
        except Exception as e:
            logger.error(f"处理WebSocket消息时出错: {str(e)}")
    
    async def notification_message(self, event):
        """发送通知消息"""
        notification = event['notification']
        
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': notification
        }, ensure_ascii=False))
    
    async def unread_count_update(self, event):
        """发送未读数量更新"""
        count = event['count']
        
        # 发送未读数量到WebSocket
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': count
        }, ensure_ascii=False))
    
    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """标记通知为已读"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.mark_as_read()
            logger.info(f"通知 {notification_id} 已标记为已读")
            return True
        except Notification.DoesNotExist:
            logger.warning(f"通知 {notification_id} 不存在或不属于当前用户")
            return False
        except Exception as e:
            logger.error(f"标记通知为已读时出错: {str(e)}")
            return False
    
    @database_sync_to_async
    def get_unread_count(self):
        """获取未读通知数量"""
        try:
            return Notification.objects.filter(
                recipient=self.user,
                is_read=False
            ).count()
        except Exception as e:
            logger.error(f"获取未读通知数量时出错: {str(e)}")
            return 0
    
    @database_sync_to_async
    def get_recent_notifications(self, limit=10):
        """获取最近的通知"""
        try:
            notifications = Notification.objects.filter(
                recipient=self.user
            ).select_related(
                'notification_type', 'sender'
            ).order_by('-created_at')[:limit]
            
            serializer = NotificationSerializer(notifications, many=True)
            return serializer.data
        except Exception as e:
            logger.error(f"获取最近通知时出错: {str(e)}")
            return []
    
    async def send_unread_count(self):
        """发送未读通知数量"""
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': count
        }, ensure_ascii=False))
    
    async def send_recent_notifications(self, limit=10):
        """发送最近的通知"""
        notifications = await self.get_recent_notifications(limit)
        await self.send(text_data=json.dumps({
            'type': 'recent_notifications',
            'notifications': notifications
        }, ensure_ascii=False))
    
    async def add_user_to_online_set(self):
        """将用户添加到在线用户集合"""
        if self.redis_client and hasattr(self, 'user') and self.user.is_authenticated:
            try:
                await self.redis_client.sadd('online_users', str(self.user.id))
                logger.debug(f"用户 {self.user.id} 已添加到在线用户集合")
            except Exception as e:
                logger.error(f"添加用户到在线集合时出错: {str(e)}")
    
    async def remove_user_from_online_set(self):
        """从在线用户集合中移除用户"""
        if self.redis_client and hasattr(self, 'user') and self.user.is_authenticated:
            try:
                await self.redis_client.srem('online_users', str(self.user.id))
                logger.debug(f"用户 {self.user.id} 已从在线用户集合中移除")
            except Exception as e:
                logger.error(f"从在线集合移除用户时出错: {str(e)}")


class NotificationBroadcastConsumer(AsyncWebsocketConsumer):
    """通知广播消费者（用于管理员广播）"""
    
    async def connect(self):
        """WebSocket连接"""
        self.user = self.scope["user"]
        
        # 检查用户是否为管理员
        if isinstance(self.user, AnonymousUser) or not self.user.is_staff:
            logger.warning("非管理员用户尝试连接广播WebSocket")
            await self.close()
            return
        
        # 设置广播组名
        self.broadcast_group_name = 'notification_broadcast'
        
        # 加入广播组
        await self.channel_layer.group_add(
            self.broadcast_group_name,
            self.channel_name
        )
        
        # 接受WebSocket连接
        await self.accept()
        
        logger.info(f"管理员 {self.user.id} 连接到广播WebSocket")
    
    async def disconnect(self, close_code):
        """WebSocket断开连接"""
        if hasattr(self, 'broadcast_group_name'):
            # 离开广播组
            await self.channel_layer.group_discard(
                self.broadcast_group_name,
                self.channel_name
            )
            
            logger.info(f"管理员 {self.user.id if hasattr(self, 'user') else 'Unknown'} 断开广播WebSocket连接")
    
    async def receive(self, text_data):
        """接收WebSocket消息"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'broadcast_notification':
                # 广播通知
                notification_data = text_data_json.get('notification')
                target_users = text_data_json.get('target_users', [])
                
                if notification_data:
                    await self.broadcast_notification(notification_data, target_users)
            
            else:
                logger.warning(f"未知的广播消息类型: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("接收到无效的JSON数据")
        except Exception as e:
            logger.error(f"处理广播WebSocket消息时出错: {str(e)}")
    
    async def broadcast_notification(self, notification_data, target_users=None):
        """广播通知"""
        try:
            if target_users:
                # 向指定用户广播
                for user_id in target_users:
                    room_group_name = f'notifications_{user_id}'
                    await self.channel_layer.group_send(
                        room_group_name,
                        {
                            'type': 'notification_message',
                            'notification': notification_data
                        }
                    )
            else:
                # 向所有在线用户广播（需要实现全局广播机制）
                logger.info("执行全局通知广播")
                # TODO: 实现全局广播逻辑
            
            # 向广播组发送确认消息
            await self.send(text_data=json.dumps({
                'type': 'broadcast_success',
                'message': '广播发送成功',
                'target_count': len(target_users) if target_users else 'all'
            }))
            
        except Exception as e:
            logger.error(f"广播通知时出错: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'broadcast_error',
                'message': f'广播发送失败: {str(e)}'
            }))
    
    async def broadcast_message(self, event):
        """接收广播消息"""
        message = event['message']
        
        # 发送消息到WebSocket
        await self.send(text_data=json.dumps({
            'type': 'broadcast',
            'message': message
        }, ensure_ascii=False))