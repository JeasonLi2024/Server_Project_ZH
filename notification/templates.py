from django.template import Template, Context
from django.utils import timezone
from typing import Dict, Any
import json


class NotificationTemplateManager:
    """通知模板管理器"""
    
    # 默认模板定义
    DEFAULT_TEMPLATES = {
        # 企业端组织用户通知模板
        'org_user_registration_audit': {
            'title': '新用户注册审核',
            'content': '用户 {{ applicant_name }} 申请加入组织 {{ organization_name }}，请及时审核。',
            'email_subject': '【{{ organization_name }}】新用户注册审核通知',
            'email_content': '''
尊敬的管理员，

用户 {{ applicant_name }}（{{ applicant_email }}）申请加入组织 {{ organization_name }}。

申请时间：{{ application_time }}
用户信息：
- 用户名：{{ applicant_name }}
- 邮箱：{{ applicant_email }}
- 申请理由：{{ application_reason }}

请登录系统进行审核：{{ review_url }}

此致
{{ organization_name }} 系统
''',
            'sms_content': '用户{{ applicant_name }}申请加入{{ organization_name }}，请及时审核。详情请登录系统查看。'
        },
        
        'org_user_permission_change': {
            'title': '组织用户权限变更通知',
            'content': '您在组织 {{ organization_name }} 的权限已由 {{ old_permission }} 变更为 {{ new_permission }}。您在组织中的权限已被更新，新权限为：{{ new_permission_display }}',
            'email_subject': '【{{ organization_name }}】权限变更通知',
            'email_content': '''
尊敬的 {{ user_name }}，

您在组织 {{ organization_name }} 的权限已发生变更：

变更详情：
- 原权限：{{ old_permission_display }}
- 新权限：{{ new_permission_display }}
- 操作人：{{ operator_name }}

您在组织中的权限已被更新，新权限为：{{ new_permission_display }}

如有疑问，请联系组织管理员。

此致
{{ organization_name }} 系统
''',
            'sms_content': '您在{{ organization_name }}的权限已变更为{{ new_permission_display }}，详情请登录系统查看。'
        },
        

        
        'org_deliverable_submitted': {
            'title': '项目成果提交通知',
            'content': '学生 {{ student_name }} 提交了项目 "{{ project_title }}" 的成果 "{{ deliverable_title }}"。',
            'email_subject': '【项目成果】成果提交通知',
            'email_content': '''
尊敬的需求创建者，

学生 {{ student_name }} 已提交项目成果：

成果信息：
- 项目标题：{{ project_title }}
- 成果标题：{{ deliverable_title }}
- 成果描述：{{ deliverable_description }}
- 文件数量：{{ file_count }}

请登录系统查看和评审成果：{{ deliverable_url }}

此致
项目管理系统
''',
            'sms_content': '学生{{ student_name }}提交项目"{{ project_title }}"成果，请登录系统查看。'
        },
        
        'org_deliverable_updated': {
            'title': '项目成果更新通知',
            'content': '学生 {{ student_name }} 更新了项目 "{{ project_title }}" 的成果 "{{ deliverable_title }}"。',
            'email_subject': '【项目成果】成果更新通知',
            'email_content': '''
尊敬的需求创建者，

学生 {{ student_name }} 已更新项目成果：

成果信息：
- 项目标题：{{ project_title }}
- 成果标题：{{ deliverable_title }}
- 成果描述：{{ deliverable_description }}
- 文件数量：{{ file_count }}

请登录系统查看更新后的成果：{{ deliverable_url }}

此致
项目管理系统
''',
            'sms_content': '学生{{ student_name }}更新项目"{{ project_title }}"成果，请登录系统查看。'
        },
        
        'org_project_status_changed': {
            'title': '项目状态变更通知',
            'content': '项目 "{{ project_title }}" 状态已从 {{ old_status }} 变更为 {{ new_status }}。',
            'email_subject': '【项目状态】项目状态变更通知',
            'email_content': '''
尊敬的需求创建者，

您关注的项目状态已发生变更：

项目信息：
- 项目标题：{{ project_title }}
- 原状态：{{ old_status_display }}
- 新状态：{{ new_status_display }}
- 项目负责人：{{ student_name }}

请登录系统查看项目详情：{{ project_url }}

此致
项目管理系统
''',
            'sms_content': '项目"{{ project_title }}"状态已变更为{{ new_status_display }}，请登录系统查看。'
        },
        
        'org_requirement_deadline_reminder': {
            'title': '需求截止评分提醒',
            'content': '您的需求 {{ requirement_title }} 已截止，可以为已完成项目评分。',
            'email_subject': '【评分提醒】需求已截止，可为已完成项目评分',
            'email_content': '''
尊敬的需求创建者，

您的需求已截止，可以为已完成项目评分：

需求信息：
- 需求标题：{{ requirement_title }}
- 当前状态：{{ requirement_status }}
- 已完成项目数：{{ completed_project_count }}
- 待评分项目数：{{ pending_score_count }}

请登录系统为已完成项目评分：{{ requirement_url }}

您的评分将帮助学生改进和成长，感谢您的参与！

此致
需求管理系统
''',
            'sms_content': '需求{{ requirement_title }}已截止，请为已完成项目评分。'
        },
        
        'org_user_permission_and_status_change': {
            'title': '用户权限和状态变更通知',
            'content': '您在组织 {{ organization_name }} 的权限和状态已发生变更。',
            'email_subject': '【{{ organization_name }}】权限和状态变更通知',
            'email_content': '''
尊敬的 {{ user_name }}，

您在组织 {{ organization_name }} 的权限和状态已发生变更：

变更详情：
- 原权限：{{ old_permission_display }}
- 新权限：{{ new_permission_display }}
- 操作人：{{ operator_name }}

如有疑问，请联系组织管理员。

此致
{{ organization_name }} 系统
''',
            'sms_content': '您在组织{{ organization_name }}的权限和状态已变更。'
        },
        
        'org_user_status_change': {
            'title': '用户状态变更通知',
            'content': '您在组织 {{ organization_name }} 的状态已变更。',
            'email_subject': '【{{ organization_name }}】状态变更通知',
            'email_content': '''
尊敬的 {{ user_name }}，

您在组织 {{ organization_name }} 的状态已发生变更：

变更详情：
- 原状态：{{ old_status_display }}
- 新状态：{{ new_status_display }}
- 操作人：{{ operator_name }}

如有疑问，请联系组织管理员。

此致
{{ organization_name }} 系统
''',
            'sms_content': '您在组织{{ organization_name }}的状态已变更。'
        },
        
        'org_user_registration_approved': {
            'title': '注册申请已通过',
            'content': '您的注册申请已通过审核，欢迎加入组织 {{ organization_name }}。',
            'email_subject': '【{{ organization_name }}】注册申请通过通知',
            'email_content': '''
尊敬的 {{ applicant_name }}，

恭喜您！您的注册申请已通过审核。

组织信息：
- 组织名称：{{ organization_name }}
- 审核时间：{{ approval_time }}

您现在可以登录系统开始使用各项功能。

此致
{{ organization_name }} 系统
''',
            'sms_content': '您的注册申请已通过，欢迎加入{{ organization_name }}。'
        },
        
        'org_user_registration_rejected': {
            'title': '注册申请未通过',
            'content': '很遗憾，您的注册申请未通过审核。',
            'email_subject': '【{{ organization_name }}】注册申请结果通知',
            'email_content': '''
尊敬的 {{ applicant_name }}，

很遗憾，您的注册申请未通过审核。

组织信息：
- 组织名称：{{ organization_name }}
- 审核时间：{{ rejection_time }}
- 拒绝理由：{{ rejection_reason }}

如有疑问，请联系组织管理员。

此致
{{ organization_name }} 系统
''',
            'sms_content': '您的注册申请未通过审核，详情请查看邮件。'
        },
        
        'organization_verification_success': {
            'title': '组织认证通过通知',
            'content': '恭喜！您的组织 {{ organization_name }} 已通过认证审核。认证时间：{{ verification_time }}。您现在可以享受认证组织的所有权益。',
            'email_subject': '🎉 恭喜！您的组织「{{ organization_name }}」认证已通过',
            'email_content': '''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #28a745; margin: 0;">🎉 认证通过通知</h1>
    </div>
    
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <p style="margin: 0 0 15px 0; font-size: 16px;">尊敬的 <strong>{{ creator_name }}</strong>：</p>
        <p style="margin: 0 0 15px 0; font-size: 16px;">恭喜您！您申请的组织 <strong style="color: #007bff;">{{ organization_name }}</strong> 已通过认证审核。</p>
    </div>
    
    <div style="background: #e9ecef; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #495057;">审核信息：</h3>
        <ul style="margin: 0; padding-left: 20px; color: #6c757d;">
            <li>审核人员：{{ operator_name }}</li>
            <li>认证时间：{{ verification_time }}</li>
        </ul>
    </div>
    
    <p style="margin: 0 0 15px 0; color: #495057;">现在您可以享受认证组织的所有权益和功能。如有任何问题，请联系我们的客服团队。</p>
    
    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        <p style="margin: 0; color: #6c757d; font-size: 14px;">感谢您的耐心等待！</p>
        <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 12px;">系统管理团队</p>
    </div>
</div>''',
            'sms_content': '恭喜！您的组织{{ organization_name }}认证已通过，详情请查看邮件。'
        },
        
        'organization_verification_rejected': {
            'title': '组织认证被拒绝通知',
            'content': '很遗憾，您的组织 {{ organization_name }} 认证申请未通过审核。拒绝原因：{{ verification_comment }}。如有疑问，请联系系统管理员。',
            'email_subject': '❌ 您的组织「{{ organization_name }}」认证申请未通过',
            'email_content': '''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #dc3545; margin: 0;">❌ 认证未通过通知</h1>
    </div>
    
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <p style="margin: 0 0 15px 0; font-size: 16px;">尊敬的 <strong>{{ creator_name }}</strong>：</p>
        <p style="margin: 0 0 15px 0; font-size: 16px;">很遗憾，您申请的组织 <strong style="color: #007bff;">{{ organization_name }}</strong> 认证申请未通过审核。</p>
    </div>
    
    <div style="background: #f8d7da; padding: 15px; border-radius: 6px; margin-bottom: 20px; border-left: 4px solid #dc3545;">
        <h3 style="margin: 0 0 10px 0; color: #721c24;">拒绝原因：</h3>
        <p style="margin: 0; color: #721c24; font-size: 14px;">{{ verification_comment }}</p>
    </div>
    
    <div style="background: #e9ecef; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #495057;">审核信息：</h3>
        <ul style="margin: 0; padding-left: 20px; color: #6c757d;">
            <li>审核人员：{{ operator_name }}</li>
            <li>审核时间：{{ verification_time }}</li>
        </ul>
    </div>
    
    <div style="background: #d1ecf1; padding: 15px; border-radius: 6px; margin-bottom: 20px; border-left: 4px solid #bee5eb;">
        <h3 style="margin: 0 0 10px 0; color: #0c5460;">下一步操作：</h3>
        <p style="margin: 0; color: #0c5460; font-size: 14px;">请根据拒绝原因完善组织信息后重新申请认证，或联系系统管理员了解详细情况。</p>
    </div>
    
    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        <p style="margin: 0; color: #6c757d; font-size: 12px;">此邮件由系统自动发送，请勿直接回复</p>
    </div>
</div>''',
            'sms_content': '您的组织{{ organization_name }}认证申请未通过，详情请查看邮件。'
        },
        
        # 学生端通知模板
        'student_project_application': {
            'title': '项目申请审核',
            'content': '学生 {{ applicant_name }} 申请加入您的项目 "{{ project_title }}"，请及时审核。',
            'email_subject': '【项目申请】{{ project_title }} - 新成员申请',
            'email_content': '''
尊敬的 {{ leader_name }}，

学生 {{ applicant_name }} 申请加入您的项目：

项目信息：
- 项目标题：{{ project_title }}
- 申请人：{{ applicant_name }}
- 申请留言：{{ application_message }}

请登录系统进行审核：{{ project_url }}

此致
项目管理系统
''',
            'sms_content': '学生{{ applicant_name }}申请加入项目{{ project_title }}，请及时审核。'
        },
        
        'student_application_result': {
            'title': '项目申请结果',
            'content': '您申请加入项目 "{{ project_title }}" 的审核结果：{{ result_display }}。',
            'email_subject': '【申请结果】{{ project_title }} - 申请审核结果',
            'email_content': '''
尊敬的 {{ applicant_name }}，

您申请加入项目的审核结果如下：

项目信息：
- 项目标题：{{ project_title }}
- 审核结果：{{ result_display }}
- 审核留言：{{ review_message }}

{% if result == "approved" %}
恭喜您成功加入项目！请登录系统查看项目详情：{{ project_url }}
{% else %}
很遗憾您的申请未通过，欢迎申请其他项目。
{% endif %}

此致
项目管理系统
''',
            'sms_content': '您申请加入项目{{ project_title }}的审核结果：{{ result_display }}。'
        },
        

        
        'student_project_invitation': {
            'title': '项目邀请',
            'content': '{{ inviter_name }} 邀请您加入项目 "{{ project_title }}"。{% if invitation_message %}邀请留言：{{ invitation_message }}{% endif %}',
            'email_subject': '【项目邀请】{{ project_title }} - 邀请加入',
            'email_content': '''
尊敬的 {{ invitee_name }}，

{{ inviter_name }} 邀请您加入项目：

项目信息：
- 项目标题：{{ project_title }}
- 邀请人：{{ inviter_name }}
- 邀请留言：{{ invitation_message }}

请登录系统查看邀请详情并回复。

此致
项目管理系统
''',
            'sms_content': '{{ inviter_name }}邀请您加入项目{{ project_title }}，请及时回复。'
        },
        
        'student_invitation_expiry_reminder': {
            'title': '邀请即将过期',
            'content': '您收到的项目 "{{ project_title }}" 邀请将于明天过期，请及时处理。',
            'email_subject': '【邀请提醒】{{ project_title }} - 邀请即将过期',
            'email_content': '''
尊敬的 {{ invitee_name }}，

您收到的项目邀请即将过期：

项目信息：
- 项目标题：{{ project_title }}
- 邀请人：{{ inviter_name }}
- 剩余时间：不足24小时

请尽快登录系统处理邀请。

此致
项目管理系统
''',
            'sms_content': '项目{{ project_title }}的邀请将于明天过期，请及时处理。'
        },
        
        'student_invitation_response': {
            'title': '邀请回复',
            'content': '{{ invitee_name }} {{ response_display }}了您的项目邀请。',
            'email_subject': '【邀请回复】{{ project_title }} - 邀请处理结果',
            'email_content': '''
尊敬的 {{ inviter_name }}，

您发送的项目邀请已收到回复：

项目信息：
- 项目标题：{{ project_title }}
- 被邀请人：{{ invitee_name }}
- 回复结果：{{ response_display }}
- 回复留言：{{ response_message }}

{% if response == "accepted" %}
恭喜！{{ invitee_name }} 已加入您的项目。
{% else %}
很遗憾，{{ invitee_name }} 拒绝了您的邀请。
{% endif %}

请登录系统查看项目详情：{{ project_url }}

此致
项目管理系统
''',
            'sms_content': '{{ invitee_name }}{{ response_display }}了您的项目邀请。'
        },
        
        'student_project_status_change': {
            'title': '项目状态变更',
            'content': '项目 "{{ project_title }}" 的状态已由 {{ old_status_display }} 变更为 {{ new_status_display }}。',
            'email_subject': '【项目状态】{{ project_title }} - 状态更新',
            'email_content': '''
尊敬的项目成员，

项目状态已发生变更：

项目信息：
- 项目标题：{{ project_title }}
- 原状态：{{ old_status_display }}
- 新状态：{{ new_status_display }}
- 操作人：{{ operator_name }}

{% if new_status == "cancelled" and members_removed %}
注意：由于项目已取消，所有成员已被移出项目。
{% endif %}

{% if new_status != "cancelled" %}
请登录系统查看项目详情：{{ project_url }}
{% endif %}

此致
项目管理系统
''',
            'sms_content': '项目{{ project_title }}状态已变更为{{ new_status_display }}。'
        },
        
        'student_member_left': {
            'title': '成员退出项目',
            'content': '{{ member_name }} 已退出项目 "{{ project_title }}"。',
            'email_subject': '【成员变动】{{ project_title }} - 成员退出',
            'email_content': '''
尊敬的 {{ leader_name }}，

项目成员发生变动：

项目信息：
- 项目标题：{{ project_title }}
- 退出成员：{{ member_name }}
- 原角色：{{ member_role_display }}

请登录系统查看项目详情：{{ project_url }}

此致
项目管理系统
''',
            'sms_content': '{{ member_name }}已退出项目{{ project_title }}。'
        },
        
        'student_project_commented': {
            'title': '项目收到评价',
            'content': '您的项目 "{{ project_title }}" 收到了来自 {{ commenter_name }} 的评价。',
            'email_subject': '【项目评价】{{ project_title }} - 新评价',
            'email_content': '''
尊敬的项目成员，

您的项目收到了新的评价：

项目信息：
- 项目标题：{{ project_title }}
- 评价人：{{ commenter_name }}
- 评价内容：{{ comment_content }}

请登录系统查看完整评价：{{ comment_url }}

此致
项目管理系统
''',
            'sms_content': '您的项目{{ project_title }}收到了来自{{ commenter_name }}的评价。'
        },
        
        'student_project_score_published': {
            'title': '项目评分公示',
            'content': '您参与的项目"{{ project_title }}"的评分结果已公示，快去查看项目分数和排名吧！',
            'email_subject': '【评分公示】{{ project_title }} - 评分结果',
            'email_content': '''
尊敬的项目成员，

您参与的项目"{{ project_title }}"的评分结果已公示，快去查看项目分数和排名吧！

项目信息：
- 项目标题：{{ project_title }}
- 评分人：{{ evaluator_name }}
- 公示时间：{{ publish_time }}

请登录系统查看详细评分：{{ score_url }}

此致
项目评分系统
''',
            'sms_content': '您参与的项目{{ project_title }}的评分结果已公示，快去查看项目分数和排名吧！'
        },
        
        'student_project_comment': {
            'title': '项目收到新评语',
            'content': '{{ commenter_name }} 对项目 "{{ project_title }}" 发布了评语：{{ comment_content }}',
            'email_subject': '【项目评语】{{ project_title }} - 收到新评语',
            'email_content': '''
尊敬的项目成员，

您参与的项目收到了新的评语：

项目信息：
- 项目标题：{{ project_title }}
- 评语发布者：{{ commenter_name }}

评语内容：
{{ comment_content }}

请登录系统查看完整评语：{{ comment_url }}

此致
项目管理系统
''',
            'sms_content': '{{ commenter_name }}对项目"{{ project_title }}"发布了评语：{{ comment_content }}'
        },
        
        'student_deliverable_comment': {
            'title': '成果收到新评语',
            'content': '{{ commenter_name }} 对项目 "{{ project_title }}" 下的成果 "{{ deliverable_title }}" 发布了评语：{{ comment_content }}',
            'email_subject': '【成果评语】{{ deliverable_title }} - 收到新评语',
            'email_content': '''
尊敬的项目成员，

您项目的成果收到了新的评语：

成果信息：
- 项目标题：{{ project_title }}
- 成果标题：{{ deliverable_title }}
- 评语发布者：{{ commenter_name }}

评语内容：
{{ comment_content }}

请登录系统查看完整评语：{{ comment_url }}

此致
项目管理系统
''',
            'sms_content': '{{ commenter_name }}对成果"{{ deliverable_title }}"发布了评语：{{ comment_content }}'
        },
        
        'org_project_comment_reply': {
            'title': '项目评语收到回复',
            'content': '{{ replier_name }} 回复了您在项目 "{{ project_title }}" 中的评语：{{ reply_content }}',
            'email_subject': '【评语回复】{{ project_title }} - 您的评语收到回复',
            'email_content': '''
尊敬的评语发布者，

您在项目中发布的评语收到了新的回复：

项目信息：
- 项目标题：{{ project_title }}
- 回复人：{{ replier_name }}

原评语内容：
{{ original_comment_content }}

回复内容：
{{ reply_content }}

请登录系统查看完整对话：{{ comment_url }}

此致
项目管理系统
''',
            'sms_content': '{{ replier_name }}回复了您在项目"{{ project_title }}"中的评语：{{ reply_content }}'
        },
        
        'org_deliverable_comment_reply': {
            'title': '成果评语收到回复',
            'content': '{{ replier_name }} 回复了您在项目 "{{ project_title }}" 中对成果 "{{ deliverable_title }}" 的评语：{{ reply_content }}',
            'email_subject': '【评语回复】{{ deliverable_title }} - 您的评语收到回复',
            'email_content': '''
尊敬的评语发布者，

您对成果发布的评语收到了新的回复：

成果信息：
- 项目标题：{{ project_title }}
- 成果标题：{{ deliverable_title }}
- 回复人：{{ replier_name }}

原评语内容：
{{ original_comment_content }}

回复内容：
{{ reply_content }}

请登录系统查看完整对话：{{ comment_url }}

此致
项目管理系统
''',
            'sms_content': '{{ replier_name }}回复了您对成果"{{ deliverable_title }}"的评语：{{ reply_content }}'
        },
        
        'student_project_status_changed': {
            'title': '项目状态变更通知',
            'content': '您参与的项目"{{ project_title }}"状态已从{{ old_status_display }}变更为{{ new_status_display }}。',
            'email_subject': '【项目管理系统】项目状态变更通知',
            'email_content': '''
尊敬的项目成员，

您参与的项目状态已发生变更：

项目信息：
- 项目标题：{{ project_title }}
- 原状态：{{ old_status_display }}
- 新状态：{{ new_status_display }}
- 操作人：{{ operator_name }}

{% if new_status == "cancelled" %}
注意：由于项目已取消，您已被移出项目。
{% else %}
请登录系统查看项目详情：{{ project_url }}
{% endif %}

此致
项目管理系统
''',
            'sms_content': '项目"{{ project_title }}"状态已变更为{{ new_status_display }}'
        },
        
        'org_project_requirement_created': {
            'title': '新需求发布通知',
            'content': '组织{{ organization_name }}发布了新需求"{{ requirement_title }}"，截止时间：{{ deadline }}。',
            'email_subject': '【{{ organization_name }}】新需求发布通知',
            'email_content': '''
尊敬的学生，

组织{{ organization_name }}发布了新的项目需求：

需求信息：
- 需求标题：{{ requirement_title }}
- 创建者：{{ creator_name }}
- 发布时间：{{ creation_time }}
- 截止时间：{{ deadline }}
- 需求描述：{{ requirement_description }}

请登录系统查看详细需求并申请项目：{{ requirement_url }}

此致
{{ organization_name }}
''',
            'sms_content': '新需求"{{ requirement_title }}"已发布，截止{{ deadline }}'
        },
        
        'org_project_completed': {
            'title': '项目完成通知',
            'content': '学生{{ student_name }}已完成项目"{{ project_title }}"，请及时查看和评分。',
            'email_subject': '【项目管理系统】项目完成通知',
            'email_content': '''
尊敬的需求创建者，

学生{{ student_name }}已完成项目：

项目信息：
- 项目标题：{{ project_title }}
- 学生姓名：{{ student_name }}
- 完成时间：{{ completion_time }}
- 项目描述：{{ project_description }}

请登录系统查看项目详情并进行评分：{{ project_url }}

此致
项目管理系统
''',
            'sms_content': '学生{{ student_name }}已完成项目"{{ project_title }}"'
        },
        
        'student_member_kicked': {
            'title': '项目成员移除通知',
            'content': '您已被移出项目"{{ project_title }}"。',
            'email_subject': '【项目管理系统】项目成员移除通知',
            'email_content': '''
尊敬的{{ member_name }}，

您已被移出项目：

项目信息：
- 项目标题：{{ project_title }}
- 操作人：{{ operator_name }}
- 移除时间：{{ removal_time }}
- 移除原因：{{ removal_reason }}

如有疑问，请联系项目负责人。

此致
项目管理系统
''',
            'sms_content': '您已被移出项目"{{ project_title }}"'
        },
        
        'student_leadership_transfer': {
            'title': '项目负责人变更通知',
            'content': '项目"{{ project_title }}"的负责人已从{{ old_leader_name }}变更为{{ new_leader_name }}。',
            'email_subject': '【项目管理系统】项目负责人变更通知',
            'email_content': '''
尊敬的项目成员，

项目负责人已发生变更：

项目信息：
- 项目标题：{{ project_title }}
- 原负责人：{{ old_leader_name }}
- 新负责人：{{ new_leader_name }}
- 变更时间：{{ transfer_time }}
- 操作人：{{ operator_name }}

请登录系统查看项目详情：{{ project_url }}

此致
项目管理系统
''',
            'sms_content': '项目"{{ project_title }}"负责人已变更为{{ new_leader_name }}'
        },
        
        'student_leadership_change_notification': {
            'title': '项目领导权变更通知',
            'content': '您在项目"{{ project_title }}"中的角色已变更为{{ new_role_display }}。',
            'email_subject': '【项目管理系统】项目角色变更通知',
            'email_content': '''
尊敬的{{ member_name }}，

您在项目中的角色已发生变更：

项目信息：
- 项目标题：{{ project_title }}
- 原角色：{{ old_role_display }}
- 新角色：{{ new_role_display }}
- 变更时间：{{ change_time }}
- 操作人：{{ operator_name }}

请登录系统查看项目详情：{{ project_url }}

此致
项目管理系统
''',
            'sms_content': '您在项目"{{ project_title }}"中的角色已变更为{{ new_role_display }}'
        },
        
        # 邀请码相关通知模板
        'org_invitation_code_expiring_soon': {
            'title': '邀请码即将过期提醒',
            'content': '您的邀请码 {{ invitation_code }} 将在 {{ hours_left }} 小时后过期，请及时使用。',
            'email_subject': '【{{ organization_name }}】邀请码即将过期提醒',
            'email_content': '''
尊敬的用户，

您的组织邀请码即将过期：

邀请码信息：
- 邀请码：{{ invitation_code }}
- 组织名称：{{ organization_name }}
- 过期时间：{{ expires_at }}
- 剩余时间：{{ hours_left }} 小时

请尽快使用邀请码加入组织：{{ organization_url }}

如有疑问，请联系组织管理员。

此致
{{ organization_name }} 系统
''',
            'sms_content': '您的邀请码{{ invitation_code }}将在{{ hours_left }}小时后过期，请及时使用。'
        },
        
        'org_invitation_code_expired': {
            'title': '邀请码已过期通知',
            'content': '您的邀请码 {{ invitation_code }} 已过期，如需重新获取，请联系组织管理员。',
            'email_subject': '【{{ organization_name }}】邀请码已过期通知',
            'email_content': '''
尊敬的用户，

您的组织邀请码已过期：

邀请码信息：
- 邀请码：{{ invitation_code }}
- 组织名称：{{ organization_name }}
- 过期时间：{{ expires_at }}
- 创建者：{{ created_by_name }}

如需重新获取邀请码，请联系组织管理员或邀请码创建者。

此致
{{ organization_name }} 系统
''',
            'sms_content': '您的邀请码{{ invitation_code }}已过期，如需重新获取请联系组织管理员。'
        },
        
        'org_invitation_code_used': {
            'title': '邀请码使用通知',
            'content': '用户 {{ user_name }} 使用了您创建的邀请码（尾号{{ invitation_code_last_4 }}）加入组织 {{ organization_name }}。',
            'email_subject': '【{{ organization_name }}】邀请码使用通知',
            'email_content': '''
尊敬的 {{ created_by_name }}，

您创建的邀请码已被使用：

使用信息：
- 邀请码尾号：...{{ invitation_code_last_4 }}
- 使用者：{{ user_name }}（{{ user_email }}）
- 使用时间：{{ used_at }}
- 组织名称：{{ organization_name }}
- 已使用次数：{{ used_count }} / {{ max_uses }}

{% if used_count >= max_uses %}
该邀请码已达到最大使用次数，无法再次使用。
{% else %}
该邀请码还可以使用 {{ remaining_uses }} 次。
{% endif %}

感谢您为组织发展做出的贡献！

此致
{{ organization_name }} 系统
''',
            'sms_content': '用户{{ user_name }}使用了您的邀请码{{ invitation_code }}加入组织。'
        }
    }
    
    @classmethod
    def render_template(cls, template_type: str, channel: str, context_data: Dict[str, Any]) -> str:
        """
        渲染通知模板
        
        Args:
            template_type: 模板类型
            channel: 渠道类型 (title, content, email_subject, email_content, sms_content)
            context_data: 模板上下文数据
        
        Returns:
            渲染后的内容
        """
        template_config = cls.DEFAULT_TEMPLATES.get(template_type)
        if not template_config:
            return f"未找到模板类型: {template_type}"
        
        template_content = template_config.get(channel)
        if not template_content:
            return f"未找到渠道模板: {template_type}.{channel}"
        
        try:
            template = Template(template_content)
            context = Context(context_data)
            return template.render(context)
        except Exception as e:
            return f"模板渲染失败: {str(e)}"
    
    @classmethod
    def get_template_variables(cls, template_type: str) -> Dict[str, str]:
        """
        获取模板变量说明
        
        Args:
            template_type: 模板类型
        
        Returns:
            变量说明字典
        """
        variable_descriptions = {
            'org_user_registration_audit': {
                'applicant_name': '申请人姓名',
                'applicant_email': '申请人邮箱',
                'organization_name': '组织名称',
                'application_time': '申请时间',
                'application_reason': '申请理由',
                'review_url': '审核链接'
            },
            'org_user_permission_change': {
                'user_name': '用户姓名',
                'organization_name': '组织名称',
                'old_permission': '原权限代码',
                'new_permission': '新权限代码',
                'old_permission_display': '原权限显示名',
                'new_permission_display': '新权限显示名',
                'operator_name': '操作人姓名',
                'change_time': '变更时间'
            },

            'org_deliverable_submitted': {
                'student_name': '学生姓名',
                'project_title': '项目标题',
                'deliverable_title': '成果标题',
                'submission_time': '提交时间',
                'deliverable_description': '成果描述',
                'file_count': '文件数量',
                'deliverable_url': '成果链接'
            },
            'org_deliverable_updated': {
                'student_name': '学生姓名',
                'project_title': '项目标题',
                'deliverable_title': '成果标题',
                'submission_time': '提交时间',
                'deliverable_description': '成果描述',
                'file_count': '文件数量',
                'deliverable_url': '成果链接'
            },
            'org_project_status_changed': {
                'project_title': '项目标题',
                'old_status': '原状态代码',
                'new_status': '新状态代码',
                'old_status_display': '原状态显示名',
                'new_status_display': '新状态显示名',
                'change_time': '变更时间',
                'student_name': '学生姓名',
                'project_url': '项目链接'
            },

            'org_requirement_deadline_reminder': {
                'requirement_title': '需求标题',
                'deadline': '截止时间',
                'days_left': '剩余天数',
                'requirement_status': '需求状态',
                'application_count': '申请项目数',
                'requirement_url': '需求链接'
            },


            'student_project_application': {
                'applicant_name': '申请人姓名',
                'leader_name': '项目负责人姓名',
                'project_title': '项目标题',
                'application_time': '申请时间',
                'application_message': '申请留言',
                'project_url': '项目链接'
            },
            'student_application_result': {
                'applicant_name': '申请人姓名',
                'project_title': '项目标题',
                'result': '审核结果代码',
                'result_display': '审核结果显示名',
                'review_time': '审核时间',
                'review_message': '审核留言',
                'project_url': '项目链接'
            },


            'student_project_invitation': {
                'inviter_name': '邀请人姓名',
                'invitee_name': '被邀请人姓名',
                'project_title': '项目标题',
                'invitation_time': '邀请时间',
                'invitation_message': '邀请留言',
                'expires_at': '过期时间',
                'invitation_url': '邀请链接'
            },
            'student_invitation_expiry_reminder': {
                'invitee_name': '被邀请人姓名',
                'inviter_name': '邀请人姓名',
                'project_title': '项目标题',
                'expires_at': '过期时间',
                'invitation_url': '邀请链接'
            },
            'student_invitation_response': {
                'inviter_name': '邀请人姓名',
                'invitee_name': '被邀请人姓名',
                'project_title': '项目标题',
                'response': '回复结果代码',
                'response_display': '回复结果显示名',
                'response_time': '回复时间',
                'response_message': '回复留言',
                'project_url': '项目链接'
            },
            'student_project_status_changed': {
                'project_title': '项目标题',
                'old_status': '原状态代码',
                'new_status': '新状态代码',
                'old_status_display': '原状态显示名',
                'new_status_display': '新状态显示名',
                'change_time': '变更时间',
                'operator_name': '操作人姓名',
                'members_removed': '是否移除成员',
                'project_url': '项目链接'
            },
            'student_member_left': {
                'leader_name': '项目负责人姓名',
                'member_name': '退出成员姓名',
                'project_title': '项目标题',
                'left_time': '退出时间',
                'member_role_display': '成员角色显示名',
                'project_url': '项目链接'
            },
            'student_leadership_transfer': {
                'new_leader_name': '新负责人姓名',
                'original_leader': '原负责人姓名',
                'project_title': '项目标题',
                'transfer_message': '转移说明',
                'project_url': '项目链接'
            },
            'student_leadership_change_notification': {
                'new_leader_name': '新负责人姓名',
                'new_leader_contact': '新负责人联系方式',
                'original_leader': '原负责人姓名',
                'project_title': '项目标题',
                'transfer_message': '变更说明',
                'project_url': '项目链接'
            },
            'student_member_kicked': {
                'member_name': '被移出成员姓名',
                'project_title': '项目标题',
                'operator_name': '操作人姓名',
                'reason': '移出理由'
            },

            'student_project_score_published': {
                'project_title': '项目标题',
                'total_score': '总分',
                'weighted_score': '加权分',
                'evaluator_name': '评分人姓名',
                'publish_time': '公示时间',
                'score_url': '评分链接'
            },
            'org_project_comment_reply': {
                'project_title': '项目标题',
                'replier_name': '回复人姓名',
                'reply_time': '回复时间',
                'reply_content': '回复内容',
                'original_comment_content': '原评语内容',
                'comment_url': '评语链接'
            },
            'org_deliverable_comment_reply': {
                'project_title': '项目标题',
                'deliverable_title': '成果标题',
                'replier_name': '回复人姓名',
                'reply_time': '回复时间',
                'reply_content': '回复内容',
                'original_comment_content': '原评语内容',
                'comment_url': '评语链接'
            },
            'student_project_status_changed': {
                'project_title': '项目标题',
                'old_status_display': '原状态显示名',
                'new_status_display': '新状态显示名',
                'operator_name': '操作人姓名',
                'project_url': '项目链接',
                'new_status': '新状态代码'
            },
            'org_project_requirement_created': {
                'requirement_title': '需求标题',
                'creator_name': '创建者姓名',
                'organization_name': '组织名称',
                'creation_time': '创建时间',
                'requirement_description': '需求描述',
                'deadline': '截止时间',
                'requirement_url': '需求链接'
            },
            'org_project_completed': {
                'project_title': '项目标题',
                'student_name': '学生姓名',
                'completion_time': '完成时间',
                'project_description': '项目描述',
                'project_url': '项目链接'
            },
            'organization_verification_success': {
                'organization_name': '组织名称',
                'creator_name': '创建者姓名',
                'operator_name': '操作员姓名',
                'verification_time': '认证时间'
            },
            'organization_verification_rejected': {
                'organization_name': '组织名称',
                'creator_name': '创建者姓名',
                'operator_name': '操作员姓名',
                'verification_time': '认证时间',
                'verification_comment': '认证意见'
            },
            'student_member_kicked': {
                'member_name': '成员姓名',
                'project_title': '项目标题',
                'operator_name': '操作人姓名',
                'removal_time': '移除时间',
                'removal_reason': '移除原因'
            },
            'student_leadership_transfer': {
                'project_title': '项目标题',
                'old_leader_name': '原负责人姓名',
                'new_leader_name': '新负责人姓名',
                'transfer_time': '变更时间',
                'operator_name': '操作人姓名',
                'project_url': '项目链接'
            },
            'student_leadership_change_notification': {
                'member_name': '成员姓名',
                'project_title': '项目标题',
                'old_role_display': '原角色显示名',
                'new_role_display': '新角色显示名',
                'change_time': '变更时间',
                'operator_name': '操作人姓名',
                'project_url': '项目链接'
            },
            
            # 邀请码相关通知变量说明
            'org_invitation_code_expiring_soon': {
                'invitation_code': '邀请码',
                'organization_name': '组织名称',
                'expires_at': '过期时间',
                'hours_left': '剩余小时数',
                'organization_url': '组织链接'
            },
            'org_invitation_code_expired': {
                'invitation_code': '邀请码',
                'organization_name': '组织名称',
                'expires_at': '过期时间',
                'created_by_name': '创建者姓名'
            },
            'org_invitation_code_used': {
                'invitation_code': '邀请码（已弃用，使用invitation_code_last_4）',
                'invitation_code_last_4': '邀请码后4位',
                'user_name': '使用者姓名',
                'user_email': '使用者邮箱',
                'used_at': '使用时间',
                'organization_name': '组织名称',
                'created_by_name': '创建者姓名',
                'used_count': '已使用次数',
                'max_uses': '最大使用次数',
                'remaining_uses': '剩余使用次数'
            }
        }
        
        return variable_descriptions.get(template_type, {})
    
    @classmethod
    def validate_template_context(cls, template_type: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和补充模板上下文数据
        
        Args:
            template_type: 模板类型
            context_data: 原始上下文数据
        
        Returns:
            验证后的上下文数据
        """
        validated_context = context_data.copy()
        
        # 添加通用变量
        validated_context.setdefault('current_time', timezone.now().strftime('%Y-%m-%d %H:%M:%S'))
        validated_context.setdefault('platform_name', '智慧项目管理平台')
        validated_context.setdefault('platform_url', 'http://localhost:8000')
        
        # 格式化时间字段
        time_fields = ['application_time', 'change_time', 'creation_time', 'submission_time', 
                      'completion_date', 'reply_time', 'deadline', 'maintenance_time']
        
        for field in time_fields:
            if field in validated_context and hasattr(validated_context[field], 'strftime'):
                validated_context[field] = validated_context[field].strftime('%Y-%m-%d %H:%M:%S')
        
        # 处理权限显示名
        permission_mapping = {
            'member': '普通成员',
            'admin': '管理员',
            'super_admin': '超级管理员'
        }
        
        if 'old_permission' in validated_context:
            validated_context['old_permission_display'] = permission_mapping.get(
                validated_context['old_permission'], validated_context['old_permission']
            )
        
        if 'new_permission' in validated_context:
            validated_context['new_permission_display'] = permission_mapping.get(
                validated_context['new_permission'], validated_context['new_permission']
            )
        
        # 处理状态显示名
        status_mapping = {
            'draft': '草稿',
            'active': '进行中',
            'completed': '已完成',
            'cancelled': '已取消',
            'pending': '待审核'
        }
        
        if 'old_status' in validated_context:
            validated_context['old_status_display'] = status_mapping.get(
                validated_context['old_status'], validated_context['old_status']
            )
        
        if 'new_status' in validated_context:
            validated_context['new_status_display'] = status_mapping.get(
                validated_context['new_status'], validated_context['new_status']
            )
        
        return validated_context
    
    @classmethod
    def preview_template(cls, template_type: str, channel: str = 'content') -> str:
        """
        预览模板（使用示例数据）
        
        Args:
            template_type: 模板类型
            channel: 渠道类型
        
        Returns:
            预览内容
        """
        # 示例数据
        sample_data = {
            'user_name': '张三',
            'username': 'zhangsan',
            'email': 'zhangsan@example.com',
            'applicant_name': '李四',
            'applicant_email': 'lisi@example.com',
            'organization_name': '示例科技公司',
            'student_name': '王五',
            'student_email': 'wangwu@example.com',
            'project_title': '智能推荐系统开发',
            'requirement_title': '电商推荐算法优化',
            'deliverable_title': '推荐算法实现文档',
            'replier_name': '赵六',
            'old_permission': 'member',
            'new_permission': 'admin',
            'old_status': 'active',
            'new_status': 'completed',
            'days_left': 3,
            'duration_hours': 4,
            'comment_content': '这个方案很不错，建议进一步优化算法效率。',
            'application_time': timezone.now(),
            'deadline': timezone.now() + timezone.timedelta(days=3),
            'maintenance_time': timezone.now() + timezone.timedelta(hours=2)
        }
        
        validated_data = cls.validate_template_context(template_type, sample_data)
        return cls.render_template(template_type, channel, validated_data)
    
    @classmethod
    def validate_template_context(cls, template_type: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和补充模板上下文数据
        
        Args:
            template_type: 模板类型
            context_data: 原始上下文数据
        
        Returns:
            验证后的上下文数据
        """
        validated_context = context_data.copy()
        
        # 添加通用变量
        validated_context.setdefault('current_time', timezone.now().strftime('%Y-%m-%d %H:%M:%S'))
        validated_context.setdefault('platform_name', '智慧项目管理平台')
        validated_context.setdefault('platform_url', 'http://localhost:8000')
        
        # 格式化时间字段
        time_fields = ['application_time', 'change_time', 'creation_time', 'submission_time', 
                      'completion_date', 'reply_time', 'deadline', 'maintenance_time']
        
        for field in time_fields:
            if field in validated_context and hasattr(validated_context[field], 'strftime'):
                validated_context[field] = validated_context[field].strftime('%Y-%m-%d %H:%M:%S')
        
        # 处理权限显示名
        permission_mapping = {
            'member': '普通成员',
            'admin': '管理员',
            'super_admin': '超级管理员'
        }
        
        if 'old_permission' in validated_context:
            validated_context['old_permission_display'] = permission_mapping.get(
                validated_context['old_permission'], validated_context['old_permission']
            )
        
        if 'new_permission' in validated_context:
            validated_context['new_permission_display'] = permission_mapping.get(
                validated_context['new_permission'], validated_context['new_permission']
            )
        
        # 处理状态显示名
        status_mapping = {
            'draft': '草稿',
            'active': '进行中',
            'completed': '已完成',
            'cancelled': '已取消',
            'pending': '待审核'
        }
        
        if 'old_status' in validated_context:
            validated_context['old_status_display'] = status_mapping.get(
                validated_context['old_status'], validated_context['old_status']
            )
        
        if 'new_status' in validated_context:
            validated_context['new_status_display'] = status_mapping.get(
                validated_context['new_status'], validated_context['new_status']
            )
        
        return validated_context
    
    @classmethod
    def preview_template(cls, template_type: str, channel: str = 'content') -> str:
        """
        预览模板（使用示例数据）
        
        Args:
            template_type: 模板类型
            channel: 渠道类型
        
        Returns:
            预览内容
        """
        # 示例数据
        sample_data = {
            'user_name': '张三',
            'username': 'zhangsan',
            'email': 'zhangsan@example.com',
            'applicant_name': '李四',
            'applicant_email': 'lisi@example.com',
            'organization_name': '示例科技公司',
            'student_name': '王五',
            'student_email': 'wangwu@example.com',
            'project_title': '智能推荐系统开发',
            'requirement_title': '电商推荐算法优化',
            'deliverable_title': '推荐算法实现文档',
            'replier_name': '赵六',
            'old_permission': 'member',
            'new_permission': 'admin',
            'old_status': 'active',
            'new_status': 'completed',
            'days_left': 3,
            'duration_hours': 4,
            'comment_content': '这个方案很不错，建议进一步优化算法效率。',
            'application_time': timezone.now(),
            'deadline': timezone.now() + timezone.timedelta(days=3),
            'maintenance_time': timezone.now() + timezone.timedelta(hours=2)
        }
        
        validated_data = cls.validate_template_context(template_type, sample_data)
        return cls.render_template(template_type, channel, validated_data)