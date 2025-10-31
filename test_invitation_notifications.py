#!/usr/bin/env python
"""
邀请码通知功能测试脚本
测试三种邀请码通知类型和防重复机制
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from django.contrib.auth import get_user_model
from authentication.models import OrganizationInvitationCode
from organization.models import Organization
from authentication.tasks import (
    send_invitation_code_expiry_notification,
    send_invitation_code_expired_notification,
    send_invitation_code_used_notification
)
from authentication.invitation_utils import use_invitation_code
from notification.models import NotificationLog

User = get_user_model()


def create_test_data():
    """创建测试数据"""
    print("🔧 创建测试数据...")
    
    # 创建测试用户
    test_user, created = User.objects.get_or_create(
        username='test_invitation_creator',
        defaults={
            'email': 'creator@test.com',
            'user_type': 'organization',
            'real_name': '测试创建者'
        }
    )
    if created:
        test_user.set_password('testpass123')
        test_user.save()
    
    # 创建使用者用户
    test_user2, created = User.objects.get_or_create(
        username='test_invitation_user',
        defaults={
            'email': 'user@test.com',
            'user_type': 'organization',
            'real_name': '测试使用者'
        }
    )
    if created:
        test_user2.set_password('testpass123')
        test_user2.save()
    
    # 创建测试组织
    test_org, created = Organization.objects.get_or_create(
        name='测试组织',
        defaults={
            'organization_type': 'enterprise',
            'enterprise_type': 'private',  # 添加企业类型
            'industry_or_discipline': '软件开发',
            'status': 'verified'
        }
    )
    
    return test_user, test_user2, test_org


def test_expiring_soon_notification():
    """测试即将过期通知"""
    print("\n📅 测试邀请码即将过期通知...")
    
    creator, user, org = create_test_data()
    
    # 创建即将过期的邀请码（23小时后过期）
    expiring_code = OrganizationInvitationCode.objects.create(
        organization=org,
        code='TEST_EXPIRING_001',
        created_by=creator,
        expires_at=timezone.now() + timedelta(hours=23),
        max_uses=10,
        expiry_notification_sent=False  # 确保未发送过通知
    )
    
    print(f"   创建即将过期的邀请码: {expiring_code.code}")
    print(f"   过期时间: {expiring_code.expires_at}")
    
    # 执行即将过期通知任务
    result = send_invitation_code_expiry_notification()
    print(f"   任务执行结果: {result}")
    
    # 检查通知状态
    expiring_code.refresh_from_db()
    print(f"   通知发送状态: {expiring_code.expiry_notification_sent}")
    
    # 检查通知记录
    notifications = NotificationLog.objects.filter(
        notification__recipient=creator,
        notification__notification_type__code='org_invitation_code_expiring_soon'
    ).order_by('-created_at')
    
    print(f"   通知记录数量: {notifications.count()}")
    if notifications.exists():
        latest = notifications.first()
        print(f"   最新通知时间: {latest.created_at}")
        print(f"   通知内容: {latest.notification.content[:100]}...")
    
    # 测试防重复机制 - 再次执行任务
    print("   测试防重复机制...")
    result2 = send_invitation_code_expiry_notification()
    print(f"   第二次执行结果: {result2}")
    
    # 检查是否产生重复通知
    notifications_after = NotificationLog.objects.filter(
        notification__recipient=creator,
        notification__notification_type__code='org_invitation_code_expiring_soon'
    ).count()
    print(f"   防重复测试 - 通知总数: {notifications_after}")
    
    return expiring_code


def test_expired_notification():
    """测试已过期通知"""
    print("\n⏰ 测试邀请码已过期通知...")
    
    creator, user, org = create_test_data()
    
    # 创建已过期的邀请码
    expired_code = OrganizationInvitationCode.objects.create(
        organization=org,
        code='TEST_EXPIRED_001',
        created_by=creator,
        expires_at=timezone.now() - timedelta(hours=1),  # 1小时前过期
        max_uses=10,
        expired_notification_sent=False  # 确保未发送过通知
    )
    
    print(f"   创建已过期的邀请码: {expired_code.code}")
    print(f"   过期时间: {expired_code.expires_at}")
    
    # 执行已过期通知任务
    result = send_invitation_code_expired_notification()
    print(f"   任务执行结果: {result}")
    
    # 检查通知状态
    expired_code.refresh_from_db()
    print(f"   通知发送状态: {expired_code.expired_notification_sent}")
    
    # 检查通知记录
    notifications = NotificationLog.objects.filter(
        notification__recipient=creator,
        notification__notification_type__code='org_invitation_code_expired'
    ).order_by('-created_at')
    
    print(f"   通知记录数量: {notifications.count()}")
    if notifications.exists():
        latest = notifications.first()
        print(f"   最新通知时间: {latest.created_at}")
        print(f"   通知内容: {latest.notification.content[:100]}...")
    
    # 测试防重复机制
    print("   测试防重复机制...")
    result2 = send_invitation_code_expired_notification()
    print(f"   第二次执行结果: {result2}")
    
    notifications_after = NotificationLog.objects.filter(
        notification__recipient=creator,
        notification__notification_type__code='org_invitation_code_expired'
    ).count()
    print(f"   防重复测试 - 通知总数: {notifications_after}")
    
    return expired_code


def test_used_notification():
    """测试邀请码使用通知"""
    print("\n🎯 测试邀请码使用通知...")
    
    creator, user, org = create_test_data()
    
    # 创建有效的邀请码
    valid_code = OrganizationInvitationCode.objects.create(
        organization=org,
        code='TEST_VALID_001',
        created_by=creator,
        expires_at=timezone.now() + timedelta(days=30),
        max_uses=10,
        used_count=0
    )
    
    print(f"   创建有效邀请码: {valid_code.code}")
    print(f"   过期时间: {valid_code.expires_at}")
    
    # 使用邀请码（这会触发使用通知）
    print("   使用邀请码...")
    success, organization, message = use_invitation_code(valid_code.code, user)
    print(f"   使用结果: {success}, 消息: {message}")
    
    # 检查邀请码状态
    valid_code.refresh_from_db()
    print(f"   使用次数: {valid_code.used_count}")
    print(f"   最后通知时间: {valid_code.last_used_notification_at}")
    
    # 等待一下让异步任务执行
    import time
    print("   等待异步通知任务执行...")
    time.sleep(3)
    
    # 检查通知记录
    notifications = NotificationLog.objects.filter(
        notification__recipient=creator,
        notification__notification_type__code='org_invitation_code_used'
    ).order_by('-created_at')
    
    print(f"   通知记录数量: {notifications.count()}")
    if notifications.exists():
        latest = notifications.first()
        print(f"   最新通知时间: {latest.created_at}")
        print(f"   通知内容: {latest.notification.content[:100]}...")
    
    # 测试防重复机制 - 短时间内再次使用
    print("   测试防重复机制（短时间内再次使用）...")
    success2, organization2, message2 = use_invitation_code(valid_code.code, user)
    print(f"   第二次使用结果: {success2}, 消息: {message2}")
    
    time.sleep(2)
    
    notifications_after = NotificationLog.objects.filter(
        notification__recipient=creator,
        notification__notification_type__code='org_invitation_code_used'
    ).count()
    print(f"   防重复测试 - 通知总数: {notifications_after}")
    
    return valid_code


def test_direct_notification_tasks():
    """直接测试通知任务"""
    print("\n🔧 直接测试通知任务...")
    
    creator, user, org = create_test_data()
    
    # 创建测试邀请码
    test_code = OrganizationInvitationCode.objects.create(
        organization=org,
        code='TEST_DIRECT_001',
        created_by=creator,
        expires_at=timezone.now() + timedelta(days=1),
        max_uses=5,
        used_count=1
    )
    
    print(f"   创建测试邀请码: {test_code.code}")
    
    # 直接测试使用通知任务
    print("   直接测试使用通知任务...")
    result = send_invitation_code_used_notification(test_code.id, user.id)
    print(f"   任务执行结果: {result}")
    
    # 检查通知记录
    notifications = NotificationLog.objects.filter(
        notification__recipient=creator,
        notification__notification_type__code='org_invitation_code_used'
    ).order_by('-created_at')
    
    print(f"   通知记录数量: {notifications.count()}")
    if notifications.exists():
        latest = notifications.first()
        print(f"   通知时间: {latest.created_at}")
        print(f"   通知标题: {latest.notification.title}")
    
    return test_code


def cleanup_test_data():
    """清理测试数据"""
    print("\n🧹 清理测试数据...")
    
    # 删除测试邀请码
    deleted_codes = OrganizationInvitationCode.objects.filter(
        code__startswith='TEST_'
    ).delete()
    print(f"   删除邀请码: {deleted_codes}")
    
    # 删除测试通知记录
    deleted_notifications = NotificationLog.objects.filter(
        notification__notification_type__code__in=[
            'org_invitation_code_expiring_soon',
            'org_invitation_code_expired',
            'org_invitation_code_used'
        ]
    ).delete()
    print(f"   删除通知记录: {deleted_notifications}")


def main():
    """主测试函数"""
    print("🚀 开始邀请码通知功能测试")
    print("=" * 50)
    
    try:
        # 清理之前的测试数据
        cleanup_test_data()
        
        # 执行各项测试
        test_expiring_soon_notification()
        test_expired_notification()
        test_used_notification()
        test_direct_notification_tasks()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试完成！")
        
        # 显示最终统计
        print("\n📊 最终统计:")
        total_codes = OrganizationInvitationCode.objects.filter(code__startswith='TEST_').count()
        total_notifications = NotificationLog.objects.filter(
            notification__notification_type__code__in=[
                'org_invitation_code_expiring_soon',
                'org_invitation_code_expired',
                'org_invitation_code_used'
            ]
        ).count()
        
        print(f"   测试邀请码数量: {total_codes}")
        print(f"   生成通知数量: {total_notifications}")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 询问是否清理测试数据
        response = input("\n是否清理测试数据？(y/n): ").lower().strip()
        if response in ['y', 'yes', '是']:
            cleanup_test_data()
            print("✅ 测试数据已清理")
        else:
            print("ℹ️  测试数据保留，可手动清理")


if __name__ == '__main__':
    main()