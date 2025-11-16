#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通知模板数据库初始化脚本

该脚本用于在新建数据库后初始化所有通知模板数据，确保系统拥有完整的通知模板配置。

使用方法：
1. 确保Django环境已正确配置
2. 运行: python init_notification_templates_script.py

作者: 系统自动生成
创建时间: 2024
"""

import os
import sys
import django
from datetime import datetime

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from notification.models import NotificationType, NotificationTemplate


class NotificationTemplateInitializer:
    """通知模板初始化器"""
    
    def __init__(self):
        self.created_types = 0
        self.updated_types = 0
        self.created_templates = 0
        self.updated_templates = 0
        self.errors = []
    
    # 完整的通知模板配置数据
    NOTIFICATION_TEMPLATES_DATA = {
        # 企业端组织用户通知模板
        'org_user_registration_audit': {
            'type_config': {
                'name': '新用户注册审核',
                'category': 'user',
                'description': '当有新用户申请注册时发送给管理员的审核通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '新用户注册审核',
                'content_template': '用户 {{ applicant_name }} 申请加入组织 {{ organization_name }}，请及时审核。',
                'email_subject': '【{{ organization_name }}】新用户注册审核通知',
                'email_content': '''尊敬的管理员，\n\n用户 {{ applicant_name }}（{{ applicant_email }}）申请加入组织 {{ organization_name }}。\n\n申请时间：{{ application_time }}\n用户信息：\n- 用户名：{{ applicant_name }}\n- 邮箱：{{ applicant_email }}\n- 申请理由：{{ application_reason }}\n\n请登录系统进行审核：{{ review_url }}\n\n此致\n{{ organization_name }} 系统''',
                'sms_content': '用户{{ applicant_name }}申请加入{{ organization_name }}，请及时审核。详情请登录系统查看。',
                'variables': {
                    'applicant_name': '申请人姓名',
                    'applicant_email': '申请人邮箱',
                    'organization_name': '组织名称',
                    'application_time': '申请时间',
                    'application_reason': '申请理由',
                    'review_url': '审核链接'
                }
            }
        },
        
        'org_user_permission_change': {
            'type_config': {
                'name': '组织用户权限变更通知',
                'category': 'user',
                'description': '当用户权限发生变更时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '组织用户权限变更通知',
                'content_template': '您在组织 {{ organization_name }} 的权限已由 {{ old_permission }} 变更为 {{ new_permission }}。您在组织中的权限已被更新，新权限为：{{ new_permission_display }}',
                'email_subject': '【{{ organization_name }}】权限变更通知',
                'email_content': '''尊敬的 {{ user_name }}，\n\n您在组织 {{ organization_name }} 的权限已发生变更：\n\n变更详情：\n- 原权限：{{ old_permission_display }}\n- 新权限：{{ new_permission_display }}\n- 操作人：{{ operator_name }}\n\n您在组织中的权限已被更新，新权限为：{{ new_permission_display }}\n\n如有疑问，请联系组织管理员。\n\n此致\n{{ organization_name }} 系统''',
                'sms_content': '您在{{ organization_name }}的权限已变更为{{ new_permission_display }}，详情请登录系统查看。',
                'variables': {
                    'user_name': '用户姓名',
                    'organization_name': '组织名称',
                    'old_permission': '原权限代码',
                    'new_permission': '新权限代码',
                    'old_permission_display': '原权限显示名',
                    'new_permission_display': '新权限显示名',
                    'operator_name': '操作人姓名',
                    'change_time': '变更时间'
                }
            }
        },
        
        'org_deliverable_submitted': {
            'type_config': {
                'name': '项目成果提交通知',
                'category': 'project',
                'description': '当项目成果被提交时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目成果提交通知',
                'content_template': '学生 {{ student_name }} 提交了项目 "{{ project_title }}" 的成果 "{{ deliverable_title }}"。',
                'email_subject': '【项目成果】成果提交通知',
                'email_content': '''尊敬的需求创建者，\n\n学生 {{ student_name }} 已提交项目成果：\n\n成果信息：\n- 项目标题：{{ project_title }}\n- 成果标题：{{ deliverable_title }}\n- 成果描述：{{ deliverable_description }}\n- 文件数量：{{ file_count }}\n\n请登录系统查看和评审成果：{{ deliverable_url }}\n\n此致\n项目管理系统''',
                'sms_content': '学生{{ student_name }}提交项目"{{ project_title }}"成果，请登录系统查看。',
                'variables': {
                    'student_name': '学生姓名',
                    'project_title': '项目标题',
                    'deliverable_title': '成果标题',
                    'submission_time': '提交时间',
                    'deliverable_description': '成果描述',
                    'file_count': '文件数量',
                    'deliverable_url': '成果链接'
                }
            }
        },
        
        'org_deliverable_updated': {
            'type_config': {
                'name': '项目成果更新通知',
                'category': 'project',
                'description': '当项目成果被更新时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目成果更新通知',
                'content_template': '学生 {{ student_name }} 更新了项目 "{{ project_title }}" 的成果 "{{ deliverable_title }}"。',
                'email_subject': '【项目成果】成果更新通知',
                'email_content': '''尊敬的需求创建者，\n\n学生 {{ student_name }} 已更新项目成果：\n\n成果信息：\n- 项目标题：{{ project_title }}\n- 成果标题：{{ deliverable_title }}\n- 成果描述：{{ deliverable_description }}\n- 文件数量：{{ file_count }}\n\n请登录系统查看更新后的成果：{{ deliverable_url }}\n\n此致\n项目管理系统''',
                'sms_content': '学生{{ student_name }}更新项目"{{ project_title }}"成果，请登录系统查看。',
                'variables': {
                    'student_name': '学生姓名',
                    'project_title': '项目标题',
                    'deliverable_title': '成果标题',
                    'update_time': '更新时间',
                    'deliverable_description': '成果描述',
                    'file_count': '文件数量',
                    'deliverable_url': '成果链接'
                }
            }
        },
        
        'org_project_status_changed': {
            'type_config': {
                'name': '项目状态变更通知',
                'category': 'project',
                'description': '当项目状态发生变更时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目状态变更通知',
                'content_template': '项目 "{{ project_title }}" 状态已从 {{ old_status }} 变更为 {{ new_status }}。',
                'email_subject': '【项目状态】项目状态变更通知',
                'email_content': '''尊敬的需求创建者，\n\n您关注的项目状态已发生变更：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 原状态：{{ old_status_display }}\n- 新状态：{{ new_status_display }}\n- 项目负责人：{{ student_name }}\n\n请登录系统查看项目详情：{{ project_url }}\n\n此致\n项目管理系统''',
                'sms_content': '项目"{{ project_title }}"状态已变更为{{ new_status_display }}，请登录系统查看。',
                'variables': {
                    'project_title': '项目标题',
                    'old_status': '原状态代码',
                    'new_status': '新状态代码',
                    'old_status_display': '原状态显示名',
                    'new_status_display': '新状态显示名',
                    'change_time': '变更时间',
                    'student_name': '学生姓名',
                    'project_url': '项目链接'
                }
            }
        },
        
        'org_requirement_deadline_reminder': {
            'type_config': {
                'name': '需求截止评分提醒',
                'category': 'requirement',
                'description': '当需求截止后有已完成项目待评分时发送的定时提醒通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '需求截止评分提醒',
                'content_template': '您的需求 {{ requirement_title }} 已截止，可以为已完成项目评分。',
                'email_subject': '【评分提醒】需求已截止，可为已完成项目评分',
                'email_content': '''尊敬的需求创建者，\n\n您的需求已截止，可以为已完成项目评分：\n\n需求信息：\n- 需求标题：{{ requirement_title }}\n- 当前状态：{{ requirement_status }}\n- 已完成项目数：{{ completed_project_count }}\n- 待评分项目数：{{ pending_score_count }}\n\n请登录系统为已完成项目评分：{{ requirement_url }}\n\n您的评分将帮助学生改进和成长，感谢您的参与！\n\n此致\n需求管理系统''',
                'sms_content': '需求{{ requirement_title }}已截止，请为已完成项目评分。',
                'variables': {
                    'requirement_title': '需求标题',
                    'deadline': '截止时间',
                    'requirement_status': '需求状态',
                    'completed_project_count': '已完成项目数',
                    'pending_score_count': '待评分项目数',
                    'requirement_url': '需求链接'
                }
            }
        },
        
        'org_user_permission_and_status_change': {
            'type_config': {
                'name': '用户权限和状态变更通知',
                'category': 'user',
                'description': '当用户权限和状态同时发生变更时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '用户权限和状态变更通知',
                'content_template': '您在组织 {{ organization_name }} 的权限和状态已发生变更。',
                'email_subject': '【{{ organization_name }}】权限和状态变更通知',
                'email_content': '''尊敬的 {{ user_name }}，\n\n您在组织 {{ organization_name }} 的权限和状态已发生变更：\n\n变更详情：\n- 原权限：{{ old_permission_display }}\n- 新权限：{{ new_permission_display }}\n- 操作人：{{ operator_name }}\n\n如有疑问，请联系组织管理员。\n\n此致\n{{ organization_name }} 系统''',
                'sms_content': '您在组织{{ organization_name }}的权限和状态已变更。',
                'variables': {
                    'user_name': '用户姓名',
                    'organization_name': '组织名称',
                    'change_time': '变更时间',
                    'old_permission_display': '原权限显示名',
                    'new_permission_display': '新权限显示名',
                    'operator_name': '操作人姓名'
                }
            }
        },
        
        'org_user_status_change': {
            'type_config': {
                'name': '用户状态变更通知',
                'category': 'user',
                'description': '当用户状态发生变更时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '用户状态变更通知',
                'content_template': '您在组织 {{ organization_name }} 的状态已变更。',
                'email_subject': '【{{ organization_name }}】状态变更通知',
                'email_content': '''尊敬的 {{ user_name }}，\n\n您在组织 {{ organization_name }} 的状态已发生变更：\n\n变更详情：\n- 原状态：{{ old_status_display }}\n- 新状态：{{ new_status_display }}\n- 操作人：{{ operator_name }}\n\n如有疑问，请联系组织管理员。\n\n此致\n{{ organization_name }} 系统''',
                'sms_content': '您在组织{{ organization_name }}的状态已变更。',
                'variables': {
                    'user_name': '用户姓名',
                    'organization_name': '组织名称',
                    'change_time': '变更时间',
                    'old_status_display': '原状态显示名',
                    'new_status_display': '新状态显示名',
                    'operator_name': '操作人姓名'
                }
            }
        },
        
        'org_user_registration_approved': {
            'type_config': {
                'name': '注册申请已通过',
                'category': 'user',
                'description': '当用户注册申请通过时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '注册申请已通过',
                'content_template': '您的注册申请已通过审核，欢迎加入组织 {{ organization_name }}。',
                'email_subject': '【{{ organization_name }}】注册申请通过通知',
                'email_content': '''尊敬的 {{ applicant_name }}，\n\n恭喜您！您的注册申请已通过审核。\n\n组织信息：\n- 组织名称：{{ organization_name }}\n- 审核时间：{{ approval_time }}\n\n您现在可以登录系统开始使用各项功能。\n\n此致\n{{ organization_name }} 系统''',
                'sms_content': '您的注册申请已通过，欢迎加入{{ organization_name }}。',
                'variables': {
                    'applicant_name': '申请人姓名',
                    'organization_name': '组织名称',
                    'approval_time': '通过时间'
                }
            }
        },
        
        'org_user_registration_rejected': {
            'type_config': {
                'name': '注册申请未通过',
                'category': 'user',
                'description': '当用户注册申请被拒绝时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '注册申请未通过',
                'content_template': '很遗憾，您的注册申请未通过审核。',
                'email_subject': '【{{ organization_name }}】注册申请结果通知',
                'email_content': '''尊敬的 {{ applicant_name }}，\n\n很遗憾，您的注册申请未通过审核。\n\n组织信息：\n- 组织名称：{{ organization_name }}\n- 审核时间：{{ rejection_time }}\n- 拒绝理由：{{ rejection_reason }}\n\n如有疑问，请联系组织管理员。\n\n此致\n{{ organization_name }} 系统''',
                'sms_content': '您的注册申请未通过审核，详情请查看邮件。',
                'variables': {
                    'applicant_name': '申请人姓名',
                    'organization_name': '组织名称',
                    'rejection_time': '拒绝时间',
                    'rejection_reason': '拒绝理由'
                }
            }
        },
        
        'organization_verification_success': {
            'type_config': {
                'name': '组织认证通过通知',
                'category': 'organization',
                'description': '当组织认证通过时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '组织认证通过通知',
                'content_template': '恭喜！您的组织 {{ organization_name }} 已通过认证审核。认证时间：{{ verification_time }}。您现在可以享受认证组织的所有权益。',
                'email_subject': '🎉 恭喜！您的组织「{{ organization_name }}」认证已通过',
                'email_content': '''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">\n    <div style="text-align: center; margin-bottom: 30px;">\n        <h1 style="color: #28a745; margin: 0;">🎉 认证通过通知</h1>\n    </div>\n    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">\n        <p style="margin: 0 0 15px 0; font-size: 16px;">尊敬的 <strong>{{ creator_name }}</strong>：</p>\n        <p style="margin: 0 0 15px 0; font-size: 16px;">恭喜您！您申请的组织 <strong style="color: #007bff;">{{ organization_name }}</strong> 已通过认证审核。</p>\n    </div>\n    <div style="background: #e9ecef; padding: 15px; border-radius: 6px; margin-bottom: 20px;">\n        <h3 style="margin: 0 0 10px 0; color: #495057;">审核信息：</h3>\n        <ul style="margin: 0; padding-left: 20px; color: #6c757d;">\n            <li>审核人员：{{ operator_name }}</li>\n            <li>认证时间：{{ verification_time }}</li>\n        </ul>\n    </div>\n    <p style="margin: 0 0 15px 0; color: #495057;">现在您可以享受认证组织的所有权益和功能。如有任何问题，请联系我们的客服团队。</p>\n    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">\n        <p style="margin: 0; color: #6c757d; font-size: 14px;">感谢您的耐心等待！</p>\n        <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 12px;">系统管理团队</p>\n    </div>\n</div>''',
                'sms_content': '恭喜！您的组织{{ organization_name }}认证已通过，详情请查看邮件。',
                'variables': {
                    'organization_name': '组织名称',
                    'creator_name': '创建者姓名',
                    'operator_name': '操作员姓名',
                    'verification_time': '认证时间'
                }
            }
        },
        
        'organization_verification_rejected': {
            'type_config': {
                'name': '组织认证被拒绝通知',
                'category': 'organization',
                'description': '当组织认证被拒绝时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '组织认证被拒绝通知',
                'content_template': '很遗憾，您的组织 {{ organization_name }} 认证申请未通过审核。拒绝原因：{{ verification_comment }}。如有疑问，请联系系统管理员。',
                'email_subject': '❌ 您的组织「{{ organization_name }}」认证申请未通过',
                'email_content': '''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">\n    <div style="text-align: center; margin-bottom: 30px;">\n        <h1 style="color: #dc3545; margin: 0;">❌ 认证未通过通知</h1>\n    </div>\n    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">\n        <p style="margin: 0 0 15px 0; font-size: 16px;">尊敬的 <strong>{{ creator_name }}</strong>：</p>\n        <p style="margin: 0 0 15px 0; font-size: 16px;">很遗憾，您申请的组织 <strong style="color: #007bff;">{{ organization_name }}</strong> 认证申请未通过审核。</p>\n    </div>\n    <div style="background: #f8d7da; padding: 15px; border-radius: 6px; margin-bottom: 20px; border-left: 4px solid #dc3545;">\n        <h3 style="margin: 0 0 10px 0; color: #721c24;">拒绝原因：</h3>\n        <p style="margin: 0; color: #721c24; font-size: 14px;">{{ verification_comment }}</p>\n    </div>\n    <div style="background: #e9ecef; padding: 15px; border-radius: 6px; margin-bottom: 20px;">\n        <h3 style="margin: 0 0 10px 0; color: #495057;">审核信息：</h3>\n        <ul style="margin: 0; padding-left: 20px; color: #6c757d;">\n            <li>审核人员：{{ operator_name }}</li>\n            <li>审核时间：{{ verification_time }}</li>\n        </ul>\n    </div>\n    <div style="background: #d1ecf1; padding: 15px; border-radius: 6px; margin-bottom: 20px; border-left: 4px solid #bee5eb;">\n        <h3 style="margin: 0 0 10px 0; color: #0c5460;">下一步操作：</h3>\n        <p style="margin: 0; color: #0c5460; font-size: 14px;">请根据拒绝原因完善组织信息后重新申请认证，或联系系统管理员了解详细情况。</p>\n    </div>\n    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">\n        <p style="margin: 0; color: #6c757d; font-size: 12px;">此邮件由系统自动发送，请勿直接回复</p>\n    </div>\n</div>''',
                'sms_content': '您的组织{{ organization_name }}认证申请未通过，详情请查看邮件。',
                'variables': {
                    'organization_name': '组织名称',
                    'creator_name': '创建者姓名',
                    'operator_name': '操作员姓名',
                    'verification_time': '认证时间',
                    'verification_comment': '认证意见'
                }
            }
        },
        
        # 学生端项目通知模板
        'student_project_application': {
            'type_config': {
                'name': '项目申请审核',
                'category': 'project',
                'description': '当学生申请加入项目时发送给项目负责人的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目申请审核',
                'content_template': '学生 {{ applicant_name }} 申请加入您的项目 "{{ project_title }}"，请及时审核。',
                'email_subject': '【项目申请】{{ project_title }} - 新成员申请',
                'email_content': '''尊敬的 {{ leader_name }}，\n\n学生 {{ applicant_name }} 申请加入您的项目：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 申请人：{{ applicant_name }}\n- 申请留言：{{ application_message }}\n\n请登录系统进行审核：{{ project_url }}\n\n此致\n项目管理系统''',
                'sms_content': '学生{{ applicant_name }}申请加入项目"{{ project_title }}"，请登录系统审核。',
                'variables': {
                    'applicant_name': '申请人姓名',
                    'leader_name': '项目负责人姓名',
                    'project_title': '项目标题',
                    'application_time': '申请时间',
                    'application_message': '申请留言',
                    'project_url': '项目链接'
                }
            }
        },
        
        'student_application_result': {
            'type_config': {
                'name': '申请处理结果通知',
                'category': 'project',
                'description': '当项目负责人处理项目申请时发送给申请人的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '申请处理结果通知',
                'content_template': '您申请加入项目 "{{ project_title }}" 的审核结果：{{ result_display }}。',
                'email_subject': '【申请结果】{{ project_title }} - 申请处理结果',
                'email_content': '''尊敬的 {{ applicant_name }}，\n\n您申请加入项目的审核结果如下：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 审核结果：{{ result_display }}\n- 审核留言：{{ review_message }}\n\n{% if result == "approved" %}\n恭喜您成功加入项目！请登录系统查看项目详情：{{ project_url }}\n{% else %}\n很遗憾您的申请未通过，欢迎申请其他项目。\n{% endif %}\n\n此致\n项目管理系统''',
                'sms_content': '您申请加入项目"{{ project_title }}"的结果：{{ result_display }}。',
                'variables': {
                    'applicant_name': '申请人姓名',
                    'project_title': '项目标题',
                    'result': '审核结果代码',
                    'result_display': '审核结果显示名',
                    'review_time': '审核时间',
                    'review_message': '审核留言',
                    'project_url': '项目链接'
                }
            }
        },
        
        'student_project_invitation': {
            'type_config': {
                'name': '项目邀请通知',
                'category': 'project',
                'description': '当项目负责人邀请学生加入项目时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目邀请通知',
                'content_template': '{{ inviter_name }} 邀请您加入项目 "{{ project_title }}"。',
                'email_subject': '【项目邀请】{{ project_title }} - 邀请加入',
                'email_content': '''尊敬的 {{ invitee_name }}，\n\n{{ inviter_name }} 邀请您加入项目：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 邀请人：{{ inviter_name }}\n- 邀请留言：{{ invitation_message }}\n\n请登录系统查看邀请详情并回复。\n\n此致\n项目管理系统''',
                'sms_content': '{{ inviter_name }}邀请您加入项目"{{ project_title }}"，请登录系统查看。',
                'variables': {
                    'inviter_name': '邀请人姓名',
                    'invitee_name': '被邀请人姓名',
                    'project_title': '项目标题',
                    'invitation_time': '邀请时间',
                    'invitation_message': '邀请留言',
                    'expires_at': '过期时间',
                    'invitation_url': '邀请链接'
                }
            }
        },
        
        'student_invitation_expiry_reminder': {
            'type_config': {
                'name': '邀请过期提醒通知',
                'category': 'project',
                'description': '当项目邀请即将过期时发送的提醒通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '邀请过期提醒通知',
                'content_template': '您收到的项目邀请即将过期，请尽快处理。',
                'email_subject': '【邀请提醒】{{ project_title }} - 邀请即将过期',
                'email_content': '''尊敬的 {{ invitee_name }}，\n\n您收到的项目邀请即将过期：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 邀请人：{{ inviter_name }}\n- 剩余时间：不足24小时\n\n请尽快登录系统处理邀请。\n\n此致\n项目管理系统''',
                'sms_content': '您收到的项目"{{ project_title }}"邀请即将过期，请尽快处理。',
                'variables': {
                    'invitee_name': '被邀请人姓名',
                    'inviter_name': '邀请人姓名',
                    'project_title': '项目标题',
                    'expires_at': '过期时间',
                    'invitation_url': '邀请链接'
                }
            }
        },
        
        'student_invitation_response': {
            'type_config': {
                'name': '邀请处理结果通知',
                'category': 'project',
                'description': '当被邀请人回复项目邀请时发送给邀请人的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '邀请处理结果通知',
                'content_template': '{{ invitee_name }} 已回复您的项目邀请：{{ response_display }}。',
                'email_subject': '【邀请回复】{{ project_title }} - 邀请处理结果',
                'email_content': '''尊敬的 {{ inviter_name }}，\n\n您发送的项目邀请已收到回复：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 被邀请人：{{ invitee_name }}\n- 回复结果：{{ response_display }}\n- 回复留言：{{ response_message }}\n\n{% if response == "accepted" %}\n恭喜！{{ invitee_name }} 已加入您的项目。\n{% else %}\n很遗憾，{{ invitee_name }} 拒绝了您的邀请。\n{% endif %}\n\n请登录系统查看项目详情：{{ project_url }}\n\n此致\n项目管理系统''',
                'sms_content': '{{ invitee_name }}已回复您的项目邀请：{{ response_display }}。',
                'variables': {
                    'inviter_name': '邀请人姓名',
                    'invitee_name': '被邀请人姓名',
                    'project_title': '项目标题',
                    'response': '回复结果代码',
                    'response_display': '回复结果显示名',
                    'response_time': '回复时间',
                    'response_message': '回复留言',
                    'project_url': '项目链接'
                }
            }
        },
        
        'student_project_status_changed': {
            'type_config': {
                'name': '项目状态变更通知',
                'category': 'project',
                'description': '当项目状态发生变更时发送给项目成员的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目状态变更通知',
                'content_template': '项目 "{{ project_title }}" 状态已变更为 {{ new_status_display }}。',
                'email_subject': '【项目状态】{{ project_title }} - 状态变更通知',
                'email_content': '''尊敬的项目成员，\n\n项目状态已发生变更：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 原状态：{{ old_status_display }}\n- 新状态：{{ new_status_display }}\n- 操作人：{{ operator_name }}\n\n{% if new_status == "cancelled" and members_removed %}\n注意：由于项目已取消，所有成员已被移出项目。\n{% endif %}\n\n{% if new_status != "cancelled" %}\n请登录系统查看项目详情：{{ project_url }}\n{% endif %}\n\n此致\n项目管理系统''',
                'sms_content': '项目"{{ project_title }}"状态已变更为{{ new_status_display }}。',
                'variables': {
                    'project_title': '项目标题',
                    'old_status': '原状态代码',
                    'new_status': '新状态代码',
                    'old_status_display': '原状态显示名',
                    'new_status_display': '新状态显示名',
                    'change_time': '变更时间',
                    'operator_name': '操作人姓名',
                    'members_removed': '是否移除成员',
                    'project_url': '项目链接'
                }
            }
        },
        
        'student_member_left': {
            'type_config': {
                'name': '成员退出项目',
                'category': 'project',
                'description': '当项目成员退出项目时发送给项目负责人的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '成员退出项目',
                'content_template': '{{ member_name }} 已退出项目 "{{ project_title }}"。',
                'email_subject': '【成员变动】{{ project_title }} - 成员退出',
                'email_content': '''尊敬的 {{ leader_name }}，\n\n项目成员发生变动：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 退出成员：{{ member_name }}\n- 原角色：{{ member_role_display }}\n\n请登录系统查看项目详情：{{ project_url }}\n\n此致\n项目管理系统''',
                'sms_content': '{{ member_name }}已退出项目"{{ project_title }}"。',
                'variables': {
                    'leader_name': '项目负责人姓名',
                    'member_name': '退出成员姓名',
                    'project_title': '项目标题',
                    'left_time': '退出时间',
                    'member_role_display': '成员角色显示名',
                    'project_url': '项目链接'
                }
            }
        },
        
        'student_project_comment': {
            'type_config': {
                'name': '组织项目评语通知',
                'category': 'project',
                'description': '当组织用户对项目发布评语时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '组织项目评语通知',
                'content_template': '您的项目收到了新的评语。',
                'email_subject': '【项目评语】{{ project_title }} - 收到新评语',
                'email_content': '''尊敬的项目成员，\n\n您的项目收到了新的评价：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 评价人：{{ commenter_name }}\n- 评价内容：{{ comment_content }}\n\n请登录系统查看完整评价：{{ comment_url }}\n\n此致\n项目管理系统''',
                'sms_content': '您的项目"{{ project_title }}"收到新评语，请登录系统查看。',
                'variables': {
                    'commenter_name': '评语发布者姓名',
                    'project_title': '项目标题',
                    'comment_content': '评语内容',
                    'comment_time': '评语发布时间',
                    'comment_url': '评语链接'
                }
            }
        },
        
        'student_project_score_published': {
            'type_config': {
                'name': '项目评分公示通知',
                'category': 'project',
                'description': '当项目评分结果公示时发送给项目所有成员的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目评分公示通知',
                'content_template': '您参与的项目 "{{ project_title }}" 的评分结果已公示。',
                'email_subject': '【评分公示】{{ project_title }} - 评分结果公示',
                'email_content': '''尊敬的项目成员，\n\n您参与的项目"{{ project_title }}"的评分结果已公示，快去查看项目分数和排名吧！\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 评分人：{{ evaluator_name }}\n- 公示时间：{{ publish_time }}\n\n请登录系统查看详细评分：{{ score_url }}\n\n此致\n项目评分系统''',
                'sms_content': '项目"{{ project_title }}"评分结果已公示，请登录系统查看。',
                'variables': {
                    'project_title': '项目标题',
                    'total_score': '总分',
                    'weighted_score': '加权分',
                    'evaluator_name': '评分人姓名',
                    'publish_time': '公示时间',
                    'score_url': '评分详情链接'
                }
            }
        },
        
        'student_deliverable_comment': {
            'type_config': {
                'name': '组织成果评语通知',
                'category': 'project',
                'description': '当组织用户对成果发布评语时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '组织成果评语通知',
                'content_template': '您的项目成果收到了新的评语。',
                'email_subject': '【成果评语】{{ deliverable_title }} - 收到新评语',
                'email_content': '''尊敬的项目成员，\n\n您项目的成果收到了新的评语：\n\n成果信息：\n- 项目标题：{{ project_title }}\n- 成果标题：{{ deliverable_title }}\n- 评语发布者：{{ commenter_name }}\n\n评语内容：\n{{ comment_content }}\n\n请登录系统查看完整评语：{{ comment_url }}\n\n此致\n项目管理系统''',
                'sms_content': '您的成果"{{ deliverable_title }}"收到新评语，请登录系统查看。',
                'variables': {
                    'commenter_name': '评语发布者姓名',
                    'project_title': '项目标题',
                    'deliverable_title': '成果标题',
                    'comment_content': '评语内容',
                    'comment_time': '评语发布时间',
                    'comment_url': '评语链接'
                }
            }
        },
        
        'org_project_comment_reply': {
            'type_config': {
                'name': '项目评语回复通知',
                'category': 'project',
                'description': '当有人回复项目评语时发送给原评语发布者的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目评语回复通知',
                'content_template': '您在项目中发布的评语收到了新的回复。',
                'email_subject': '【评语回复】{{ project_title }} - 评语收到回复',
                'email_content': '''尊敬的评语发布者，\n\n您在项目中发布的评语收到了新的回复：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 回复人：{{ replier_name }}\n\n原评语内容：\n{{ original_comment_content }}\n\n回复内容：\n{{ reply_content }}\n\n请登录系统查看完整对话：{{ comment_url }}\n\n此致\n项目管理系统''',
                'sms_content': '您在项目"{{ project_title }}"的评语收到新回复，请登录系统查看。',
                'variables': {
                    'project_title': '项目标题',
                    'replier_name': '回复人姓名',
                    'reply_time': '回复时间',
                    'reply_content': '回复内容',
                    'original_comment_content': '原评语内容',
                    'comment_url': '评语链接'
                }
            }
        },
        
        'org_deliverable_comment_reply': {
            'type_config': {
                'name': '成果评语回复通知',
                'category': 'project',
                'description': '当有人回复成果评语时发送给原评语发布者的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '成果评语回复通知',
                'content_template': '您对成果发布的评语收到了新的回复。',
                'email_subject': '【评语回复】{{ deliverable_title }} - 评语收到回复',
                'email_content': '''尊敬的评语发布者，\n\n您对成果发布的评语收到了新的回复：\n\n成果信息：\n- 项目标题：{{ project_title }}\n- 成果标题：{{ deliverable_title }}\n- 回复人：{{ replier_name }}\n\n原评语内容：\n{{ original_comment_content }}\n\n回复内容：\n{{ reply_content }}\n\n请登录系统查看完整对话：{{ comment_url }}\n\n此致\n项目管理系统''',
                'sms_content': '您对成果"{{ deliverable_title }}"的评语收到新回复，请登录系统查看。',
                'variables': {
                    'project_title': '项目标题',
                    'deliverable_title': '成果标题',
                    'replier_name': '回复人姓名',
                    'reply_time': '回复时间',
                    'reply_content': '回复内容',
                    'original_comment_content': '原评语内容',
                    'comment_url': '评语链接'
                }
            }
        },
        
        'org_project_completed': {
            'type_config': {
                'name': '项目完成通知',
                'category': 'project',
                'description': '当项目完成时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目完成通知',
                'content_template': '项目 "{{ project_title }}" 已完成。完成时间：{{ completion_time }}。',
                'email_subject': '【项目完成】{{ project_title }} - 项目已完成',
                'email_content': '''尊敬的需求创建者，\n\n学生{{ student_name }}已完成项目：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 学生姓名：{{ student_name }}\n- 完成时间：{{ completion_time }}\n- 项目描述：{{ project_description }}\n\n请登录系统查看项目详情并进行评分：{{ project_url }}\n\n此致\n项目管理系统''',
                'sms_content': '项目"{{ project_title }}"已完成，请登录系统查看。',
                'variables': {
                    'project_title': '项目标题',
                    'student_name': '学生姓名',
                    'completion_time': '完成时间',
                    'project_description': '项目描述',
                    'project_url': '项目链接'
                }
            }
        },
        
        'student_member_kicked': {
            'type_config': {
                'name': '成员被移出项目',
                'category': 'project',
                'description': '当项目成员被项目负责人移出项目时发送的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '成员被移出项目',
                'content_template': '您已被移出项目 "{{ project_title }}"。',
                'email_subject': '【项目通知】{{ project_title }} - 您已被移出项目',
                'email_content': '''尊敬的{{ member_name }}，\n\n您已被移出项目：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 操作人：{{ operator_name }}\n- 移除时间：{{ removal_time }}\n- 移除原因：{{ removal_reason }}\n\n如有疑问，请联系项目负责人。\n\n此致\n项目管理系统''',
                'sms_content': '您已被移出项目"{{ project_title }}"，详情请查看邮件。',
                'variables': {
                    'member_name': '成员姓名',
                    'project_title': '项目标题',
                    'operator_name': '操作人姓名',
                    'removal_time': '移除时间',
                    'removal_reason': '移除原因'
                }
            }
        },
        
        'student_leadership_transfer': {
            'type_config': {
                'name': '项目负责人身份转移',
                'category': 'project',
                'description': '当项目负责人身份转移时发送给新负责人的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目负责人身份转移',
                'content_template': '您已成为项目 "{{ project_title }}" 的新负责人。',
                'email_subject': '【负责人变更】{{ project_title }} - 您已成为项目负责人',
                'email_content': '''尊敬的项目成员，\n\n项目负责人已发生变更：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 原负责人：{{ old_leader_name }}\n- 新负责人：{{ new_leader_name }}\n- 变更时间：{{ transfer_time }}\n- 操作人：{{ operator_name }}\n\n请登录系统查看项目详情：{{ project_url }}\n\n此致\n项目管理系统''',
                'sms_content': '您已成为项目"{{ project_title }}"的新负责人。',
                'variables': {
                    'project_title': '项目标题',
                    'old_leader_name': '原负责人姓名',
                    'new_leader_name': '新负责人姓名',
                    'transfer_time': '变更时间',
                    'operator_name': '操作人姓名',
                    'project_url': '项目链接'
                }
            }
        },
        
        'student_leadership_change_notification': {
            'type_config': {
                'name': '项目负责人变更通知',
                'category': 'project',
                'description': '当项目负责人变更时发送给除新旧负责人外的所有成员的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目负责人变更通知',
                'content_template': '项目 "{{ project_title }}" 的负责人已变更。',
                'email_subject': '【负责人变更】{{ project_title }} - 负责人变更通知',
                'email_content': '''尊敬的{{ member_name }}，\n\n您在项目中的角色已发生变更：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 原角色：{{ old_role_display }}\n- 新角色：{{ new_role_display }}\n- 变更时间：{{ change_time }}\n- 操作人：{{ operator_name }}\n\n请登录系统查看项目详情：{{ project_url }}\n\n此致\n项目管理系统''',
                'sms_content': '项目"{{ project_title }}"负责人已变更，请登录系统查看。',
                'variables': {
                    'member_name': '成员姓名',
                    'project_title': '项目标题',
                    'old_role_display': '原角色显示名',
                    'new_role_display': '新角色显示名',
                    'change_time': '变更时间',
                    'operator_name': '操作人姓名',
                    'project_url': '项目链接'
                }
            }
        },
        
        # 系统广播通知模板
        'system_announcement': {
            'type_config': {
                'name': '系统公告',
                'category': 'system',
                'description': '系统重要公告通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '【系统公告】{title}',
                'content_template': '{content}\n\n发布时间：{created_at}\n有效期至：{expires_at}',
                'email_subject': '【系统公告】{title}',
                'email_content': '{content}\n\n发布时间：{created_at}\n有效期至：{expires_at}',
                'sms_content': '系统公告：{title}，请登录查看详情。',
                'variables': {
                    'title': '公告标题',
                    'content': '公告内容',
                    'created_at': '发布时间',
                    'expires_at': '有效期至'
                }
            }
        },
        
        'maintenance_notice': {
            'type_config': {
                'name': '维护通知',
                'category': 'system',
                'description': '系统维护相关通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '【维护通知】{title}',
                'content_template': '{content}\n\n维护时间：{maintenance_time}\n预计影响：{impact}\n\n如有疑问，请联系技术支持。',
                'email_subject': '【维护通知】{title}',
                'email_content': '{content}\n\n维护时间：{maintenance_time}\n预计影响：{impact}\n\n如有疑问，请联系技术支持。',
                'sms_content': '系统维护通知：{title}，请登录查看详情。',
                'variables': {
                    'title': '维护标题',
                    'content': '维护内容',
                    'maintenance_time': '维护时间',
                    'impact': '影响范围'
                }
            }
        },
        
        'version_update': {
            'type_config': {
                'name': '版本更新',
                'category': 'system',
                'description': '系统版本更新通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '【版本更新】{title}',
                'content_template': '{content}\n\n更新版本：{version}\n更新时间：{update_time}\n主要改进：{improvements}',
                'email_subject': '【版本更新】{title}',
                'email_content': '{content}\n\n更新版本：{version}\n更新时间：{update_time}\n主要改进：{improvements}',
                'sms_content': '系统版本更新：{title}，请登录查看详情。',
                'variables': {
                    'title': '更新标题',
                    'content': '更新内容',
                    'version': '版本号',
                    'update_time': '更新时间',
                    'improvements': '改进内容'
                }
            }
        },
        
        'urgent_notice': {
            'type_config': {
                'name': '紧急通知',
                'category': 'system',
                'description': '系统紧急通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '【紧急通知】{title}',
                'content_template': '⚠️ 紧急通知 ⚠️\n\n{content}\n\n请立即关注并采取相应措施。\n\n发布时间：{created_at}',
                'email_subject': '【紧急通知】{title}',
                'email_content': '⚠️ 紧急通知 ⚠️\n\n{content}\n\n请立即关注并采取相应措施。\n\n发布时间：{created_at}',
                'sms_content': '紧急通知：{title}，请立即登录查看。',
                'variables': {
                    'title': '通知标题',
                    'content': '通知内容',
                    'created_at': '发布时间'
                }
            }
        },
        
        'org_project_requirement_created': {
            'type_config': {
                'name': '项目需求创建通知',
                'category': 'project',
                'description': '当项目创建对接需求时发送给相关人员的通知',
                'is_active': True
            },
            'template_config': {
                'title_template': '项目需求创建通知',
                'content_template': '项目 "{{ project_title }}" 已创建新的对接需求。',
                'email_subject': '【需求创建】{{ project_title }} - 新需求通知',
                'email_content': '''尊敬的{{ recipient_name }}，\n\n项目已创建新的对接需求：\n\n项目信息：\n- 项目标题：{{ project_title }}\n- 需求类型：{{ requirement_type }}\n- 创建时间：{{ created_time }}\n- 截止时间：{{ deadline }}\n\n请及时查看并处理相关需求。\n\n查看项目详情：{{ project_url }}''',
                'sms_content': '项目"{{ project_title }}"已创建新需求，请登录查看。',
                'variables': {
                    'recipient_name': '接收人姓名',
                    'project_title': '项目标题',
                    'requirement_type': '需求类型',
                    'created_time': '创建时间',
                    'deadline': '截止时间',
                    'project_url': '项目链接'
                }
            }
        }
    }
    
    def create_notification_type(self, code, type_config):
        """创建或更新通知类型"""
        try:
            notification_type, created = NotificationType.objects.get_or_create(
                code=code,
                defaults={
                    'name': type_config['name'],
                    'category': type_config['category'],
                    'description': type_config['description'],
                    'is_active': type_config.get('is_active', True)
                }
            )
            
            if created:
                self.created_types += 1
                print(f"✅ 创建通知类型: {notification_type.name}")
            else:
                # 更新现有类型
                notification_type.name = type_config['name']
                notification_type.category = type_config['category']
                notification_type.description = type_config['description']
                notification_type.is_active = type_config.get('is_active', True)
                notification_type.save()
                self.updated_types += 1
                print(f"🔄 更新通知类型: {notification_type.name}")
            
            return notification_type
            
        except Exception as e:
            error_msg = f"创建通知类型 {code} 失败: {str(e)}"
            self.errors.append(error_msg)
            print(f"❌ {error_msg}")
            return None
    
    def create_notification_template(self, notification_type, template_config):
        """创建或更新通知模板"""
        try:
            template, created = NotificationTemplate.objects.get_or_create(
                notification_type=notification_type,
                defaults={
                    'title_template': template_config['title_template'],
                    'content_template': template_config['content_template'],
                    'email_subject': template_config.get('email_subject', ''),
                    'email_content': template_config.get('email_content', ''),
                    'sms_content': template_config.get('sms_content', ''),
                    'variables': template_config.get('variables', {})
                }
            )
            
            if created:
                self.created_templates += 1
                print(f"✅ 创建通知模板: {notification_type.name} 模板")
            else:
                # 更新现有模板
                template.title_template = template_config['title_template']
                template.content_template = template_config['content_template']
                template.email_subject = template_config.get('email_subject', '')
                template.email_content = template_config.get('email_content', '')
                template.sms_content = template_config.get('sms_content', '')
                template.variables = template_config.get('variables', {})
                template.save()
                self.updated_templates += 1
                print(f"🔄 更新通知模板: {notification_type.name} 模板")
            
            return template
            
        except Exception as e:
            error_msg = f"创建通知模板 {notification_type.code} 失败: {str(e)}"
            self.errors.append(error_msg)
            print(f"❌ {error_msg}")
            return None
    
    def initialize_all_templates(self):
        """初始化所有通知模板"""
        print("开始初始化通知模板...")
        print("=" * 50)
        
        for code, config in self.NOTIFICATION_TEMPLATES_DATA.items():
            print(f"\n处理通知类型: {code}")
            
            # 创建通知类型
            notification_type = self.create_notification_type(code, config['type_config'])
            
            if notification_type:
                # 创建通知模板
                self.create_notification_template(notification_type, config['template_config'])
        
        # 输出统计信息
        print("\n" + "=" * 50)
        print("初始化完成！")
        print(f"通知类型 - 新建: {self.created_types}, 更新: {self.updated_types}")
        print(f"通知模板 - 新建: {self.created_templates}, 更新: {self.updated_templates}")
        
        if self.errors:
            print(f"\n⚠️  发生 {len(self.errors)} 个错误:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print("\n✅ 所有模板初始化成功！")
    
    def validate_database_connection(self):
        """验证数据库连接"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            print("✅ 数据库连接正常")
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {str(e)}")
            return False
    
    def check_models_exist(self):
        """检查模型是否存在"""
        try:
            # 检查表是否存在
            NotificationType.objects.exists()
            NotificationTemplate.objects.exists()
            print("✅ 数据库表结构正常")
            return True
        except Exception as e:
            print(f"❌ 数据库表结构检查失败: {str(e)}")
            print("请确保已运行 python manage.py migrate")
            return False


def main():
    """主函数"""
    print("通知模板数据库初始化脚本")
    print("=" * 50)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    initializer = NotificationTemplateInitializer()
    
    # 验证环境
    if not initializer.validate_database_connection():
        sys.exit(1)
    
    if not initializer.check_models_exist():
        sys.exit(1)
    
    # 执行初始化
    try:
        initializer.initialize_all_templates()
        print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n🎉 脚本执行完成！")
    except KeyboardInterrupt:
        print("\n⚠️  用户中断执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 脚本执行失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()