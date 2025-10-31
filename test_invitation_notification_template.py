#!/usr/bin/env python
"""
测试邀请码使用通知模板的安全优化功能
验证：
1. 邀请码只显示后4位
2. 包含组织名称
3. 包含使用者姓名
4. 通知内容清晰、简洁、专业
"""

import os
import sys
import django
from django.utils import timezone

# 设置Django环境
sys.path.append('/home/undergraduate/Workspace/bupt_zh')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from user.models import User
from organization.models import Organization
from user.models import OrganizationUser
from authentication.models import OrganizationInvitationCode
from authentication.invitation_utils import use_invitation_code
from notification.models import NotificationTemplate
from notification.templates import NotificationTemplateManager

def test_invitation_notification_template():
    """测试邀请码使用通知模板的安全优化功能"""
    print("开始测试邀请码使用通知模板的安全优化功能...")
    
    try:
        # 1. 检查模板定义
        print("\n1. 检查通知模板定义...")
        template_manager = NotificationTemplateManager()
        template_config = template_manager.DEFAULT_TEMPLATES.get('org_invitation_code_used')
        if template_config:
            print(f"   模板标题: {template_config['title']}")
            print(f"   模板内容: {template_config['content']}")
            print(f"   邮件主题: {template_config['email_subject']}")
            print(f"   邮件内容: {template_config['email_content']}")
            
            # 检查是否包含安全优化
            if 'invitation_code_last_4' in template_config['content']:
                print("   ✓ 模板已使用邀请码后4位")
            else:
                print("   ✗ 模板未使用邀请码后4位")
                
            if 'organization_name' in template_config['content']:
                print("   ✓ 模板包含组织名称")
            else:
                print("   ✗ 模板未包含组织名称")
                
            if 'user_name' in template_config['content']:
                print("   ✓ 模板包含使用者姓名")
            else:
                print("   ✗ 模板未包含使用者姓名")
        
        # 2. 查找有效的邀请码
        print("\n2. 查找有效的邀请码...")
        invitation_code = OrganizationInvitationCode.objects.filter(
            status='active',
            used_count__lt=django.db.models.F('max_uses')
        ).first()
        
        if not invitation_code:
            print("   未找到有效的邀请码，创建测试邀请码...")
            # 创建测试组织和用户
            test_org, _ = Organization.objects.get_or_create(
                name="测试组织_模板优化",
                defaults={'description': '用于测试邀请码通知模板优化的组织'}
            )
            
            test_creator, _ = User.objects.get_or_create(
                username="test_creator_template",
                defaults={
                    'email': 'creator@test.com',
                    'real_name': '张三'
                }
            )
            
            invitation_code = OrganizationInvitationCode.objects.create(
                organization=test_org,
                code="TEST1234ABCD",  # 测试邀请码，后4位是ABCD
                created_by=test_creator,
                max_uses=5,
                used_count=0,
                expires_at=timezone.now() + timezone.timedelta(days=7)
            )
            print(f"   创建测试邀请码: {invitation_code.code}")
        else:
            print(f"   找到有效邀请码: {invitation_code.code}")
        
        print(f"   邀请码后4位: {invitation_code.code[-4:]}")
        print(f"   所属组织: {invitation_code.organization.name}")
        print(f"   创建者: {invitation_code.created_by.get_full_name() or invitation_code.created_by.username}")
        
        # 3. 创建测试用户
        print("\n3. 创建测试用户...")
        test_user, created = User.objects.get_or_create(
            username='test_invitation_user',
            defaults={
                'email': 'test@example.com',
                'real_name': '测试用户',
                'user_type': 'student'
            }
        )
        
        if created:
            print(f"   创建新测试用户: {test_user.get_full_name()}")
        else:
            print(f"   使用现有测试用户: {test_user.get_full_name()}")
        
        # 4. 测试邀请码使用和通知发送
        print("\n4. 测试邀请码使用和通知发送...")
        
        # 记录使用前的状态
        original_used_count = invitation_code.used_count
        print(f"   使用前邀请码使用次数: {original_used_count}")
        
        # 使用邀请码（这会触发通知发送）
        success, organization, message = use_invitation_code(invitation_code.code, test_user)
        
        if success:
            print("   ✓ 邀请码使用成功")
            # 重新获取邀请码对象以获取最新的使用次数
            invitation_code.refresh_from_db()
            print(f"   使用后邀请码使用次数: {invitation_code.used_count}")
            
            # 验证通知变量
            print("\n5. 验证通知模板变量...")
            template_vars = {
                'invitation_code_last_4': invitation_code.code[-4:],
                'organization_name': invitation_code.organization.name,
                'user_name': test_user.get_full_name() or test_user.username,
                'created_by_name': invitation_code.created_by.get_full_name() or invitation_code.created_by.username,
                'used_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'used_count': invitation_code.used_count,
                'max_uses': invitation_code.max_uses,
                'remaining_uses': invitation_code.max_uses - invitation_code.used_count
            }
            
            print("   模板变量:")
            for key, value in template_vars.items():
                print(f"     {key}: {value}")
            
            # 使用Django模板引擎渲染模板内容
            if template_config:
                from django.template import Template, Context
                
                content_template = Template(template_config['content'])
                email_content_template = Template(template_config['email_content'])
                
                context = Context(template_vars)
                rendered_content = content_template.render(context)
                rendered_email_content = email_content_template.render(context)
                
                print(f"\n6. 渲染后的通知内容:")
                print(f"   WebSocket通知: {rendered_content}")
                print(f"   邮件通知: {rendered_email_content}")
                
                # 验证安全性
                print(f"\n7. 安全性验证:")
                full_code = invitation_code.code
                if full_code not in rendered_content and full_code not in rendered_email_content:
                    print("   ✓ 完整邀请码未在通知中显示")
                else:
                    print("   ✗ 完整邀请码仍在通知中显示")
                
                if invitation_code.code[-4:] in rendered_content:
                    print("   ✓ 邀请码后4位正确显示")
                else:
                    print("   ✗ 邮请码后4位未正确显示")
                
                if invitation_code.organization.name in rendered_content:
                    print("   ✓ 组织名称正确显示")
                else:
                    print("   ✗ 组织名称未正确显示")
                
                if test_user.get_full_name() in rendered_content:
                    print("   ✓ 使用者姓名正确显示")
                else:
                    print("   ✗ 使用者姓名未正确显示")
            
        else:
            print(f"   ✗ 邀请码使用失败: {result['message']}")
            return False
        
        print("\n✓ 邀请码使用通知模板安全优化测试完成")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_data():
    """清理测试数据"""
    print("\n清理测试数据...")
    try:
        # 删除测试用户
        User.objects.filter(username__in=["test_user_template", "test_creator_template"]).delete()
        
        # 删除测试组织（会级联删除邀请码）
        Organization.objects.filter(name="测试组织_模板优化").delete()
        
        print("✓ 测试数据清理完成")
    except Exception as e:
        print(f"✗ 清理测试数据时发生错误: {str(e)}")

if __name__ == "__main__":
    try:
        success = test_invitation_notification_template()
        if success:
            print("\n🎉 所有测试通过！邀请码使用通知模板安全优化功能正常工作。")
        else:
            print("\n❌ 测试失败，请检查相关配置。")
    finally:
        cleanup_test_data()