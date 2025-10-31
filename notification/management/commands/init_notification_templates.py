from django.core.management.base import BaseCommand
from notification.models import NotificationType, NotificationTemplate
from notification.templates import NotificationTemplateManager


class Command(BaseCommand):
    help = '初始化通知类型和模板数据'
    
    def handle(self, *args, **options):
        """执行初始化命令"""
        self.stdout.write('开始初始化通知类型和模板...')
        
        # 获取默认模板配置
        default_templates = NotificationTemplateManager.DEFAULT_TEMPLATES
        
        # 定义需要初始化的通知类型配置（只保留27个正在使用的通知类型）
        notification_configs = {
            'org_deliverable_comment_reply': {
                'name': '成果评语回复通知',
                'category': 'project',
                'description': '当有人回复成果评语时发送给原评语发布者的通知',
                'variables': {
                    'project_title': '项目标题',
                    'deliverable_title': '成果标题',
                    'replier_name': '回复人姓名',
                    'reply_time': '回复时间',
                    'reply_content': '回复内容',
                    'original_comment_content': '原评语内容',
                    'comment_url': '评语链接'
                }
            },
            'student_project_application': {
                'name': '项目申请通知',
                'category': 'project',
                'description': '当学生申请加入项目时发送给项目负责人的通知',
                'variables': {
                    'applicant_name': '申请人姓名',
                    'project_title': '项目标题',
                    'application_time': '申请时间',
                    'application_message': '申请留言',
                    'applicant_profile_url': '申请人资料链接'
                }
            },
            'student_application_result': {
                'name': '申请处理结果通知',
                'category': 'project',
                'description': '当项目负责人处理项目申请时发送给申请人的通知',
                'variables': {
                    'applicant_name': '申请人姓名',
                    'project_title': '项目标题',
                    'result': '处理结果代码',
                    'result_display': '处理结果显示名',
                    'review_time': '处理时间',
                    'review_message': '处理留言',
                    'project_url': '项目链接'
                }
            },

            'student_project_status_changed': {
                'name': '项目状态变更通知',
                'category': 'project',
                'description': '当项目状态发生变更时发送给项目成员的通知',
                'variables': {
                    'project_title': '项目标题',
                    'old_status_display': '原状态',
                    'new_status_display': '新状态',
                    'change_time': '变更时间',
                    'change_reason': '变更原因',
                    'project_url': '项目链接'
                }
            },




             'org_user_registration_audit': {
                'name': '用户注册审核通知',
                'category': 'user',
                'description': '当有新用户申请注册时发送给管理员的审核通知',
                'variables': {
                    'applicant_name': '申请人姓名',
                    'applicant_email': '申请人邮箱',
                    'organization_name': '组织名称',
                    'application_time': '申请时间',
                    'application_reason': '申请理由',
                    'review_url': '审核链接'
                }
            },
            'org_user_permission_change': {
                'name': '用户权限变更通知',
                'category': 'user',
                'description': '当用户权限发生变更时发送的通知',
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
            },
            'org_project_requirement_created': {
                'name': '项目需求创建通知',
                'category': 'project',
                'description': '当项目需求被创建时发送的通知',
                'variables': {
                    'student_name': '学生姓名',
                    'student_email': '学生邮箱',
                    'project_title': '项目标题',
                    'requirement_title': '需求标题',
                    'creation_time': '创建时间',
                    'project_description': '项目描述',
                    'project_url': '项目链接'
                }
            },
            'org_project_status_changed': {
                'name': '项目状态变更通知',
                'category': 'project',
                'description': '当项目状态发生变更时发送的通知',
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
            },
            'org_user_permission_and_status_change': {
                'name': '用户权限和状态变更通知',
                'category': 'user',
                'description': '当用户权限和状态同时发生变更时发送的通知',
                'variables': {
                    'user_name': '用户姓名',
                    'organization_name': '组织名称',
                    'change_time': '变更时间'
                }
            },
            'org_user_status_change': {
                'name': '用户状态变更通知',
                'category': 'user',
                'description': '当用户状态发生变更时发送的通知',
                'variables': {
                    'user_name': '用户姓名',
                    'organization_name': '组织名称',
                    'change_time': '变更时间'
                }
            },
            'org_user_registration_approved': {
                'name': '注册申请通过通知',
                'category': 'user',
                'description': '当用户注册申请通过时发送的通知',
                'variables': {
                    'user_name': '用户姓名',
                    'organization_name': '组织名称',
                    'approval_time': '通过时间'
                }
            },
            'org_user_registration_rejected': {
                'name': '注册申请拒绝通知',
                'category': 'user',
                'description': '当用户注册申请被拒绝时发送的通知',
                'variables': {
                    'user_name': '用户姓名',
                    'organization_name': '组织名称',
                    'rejection_time': '拒绝时间',
                    'rejection_reason': '拒绝理由'
                }
            },
            'org_deliverable_submitted': {
                'name': '项目交付物提交通知',
                'category': 'project',
                'description': '当项目交付物被提交时发送的通知',
                'variables': {
                    'student_name': '学生姓名',
                    'project_title': '项目标题',
                    'deliverable_title': '成果标题',
                    'submission_time': '提交时间',
                    'deliverable_description': '成果描述',
                    'file_count': '文件数量',
                    'deliverable_url': '成果链接'
                }
            },
            'org_deliverable_updated': {
                'name': '项目成果更新通知',
                'category': 'project',
                'description': '当项目成果被更新时发送的通知',
                'variables': {
                    'student_name': '学生姓名',
                    'project_title': '项目标题',
                    'deliverable_title': '成果标题',
                    'update_time': '更新时间',
                    'deliverable_description': '成果描述',
                    'file_count': '文件数量',
                    'deliverable_url': '成果链接'
                }
            },
            'student_project_comment': {
                'name': '组织项目评语通知',
                'category': 'project',
                'description': '当组织用户对项目发布评语时发送的通知',
                'variables': {
                    'commenter_name': '评语发布者姓名',
                    'project_title': '项目标题',
                    'comment_content': '评语内容',
                    'comment_time': '评语发布时间',
                    'project_url': '项目链接'
                }
            },
            'student_deliverable_comment': {
                'name': '组织成果评语通知',
                'category': 'project',
                'description': '当组织用户对成果发布评语时发送的通知',
                'variables': {
                    'commenter_name': '评语发布者姓名',
                    'project_title': '项目标题',
                    'deliverable_title': '成果标题',
                    'comment_content': '评语内容',
                    'comment_time': '评语发布时间',
                    'deliverable_url': '成果链接'
                }
            },
            'org_project_comment_reply': {
                'name': '项目评语回复通知',
                'category': 'project',
                'description': '当有人回复项目评语时发送给原评语发布者的通知',
                'variables': {
                    'project_title': '项目标题',
                    'replier_name': '回复人姓名',
                    'reply_time': '回复时间',
                    'reply_content': '回复内容',
                    'original_comment_content': '原评语内容',
                    'comment_url': '评语链接'
                }
            },
            'org_deliverable_comment_reply': {
                'name': '成果评语回复通知',
                'category': 'project',
                'description': '当有人回复成果评语时发送给原评语发布者的通知',
                'variables': {
                    'project_title': '项目标题',
                    'deliverable_title': '成果标题',
                    'replier_name': '回复人姓名',
                    'reply_time': '回复时间',
                    'reply_content': '回复内容',
                    'original_comment_content': '原评语内容',
                    'comment_url': '评语链接'
                }
            },
            'org_requirement_deadline_reminder': {
                'name': '需求截止评分提醒',
                'category': 'requirement',
                'description': '当需求截止后有已完成项目待评分时发送的定时提醒通知',
                'variables': {
                    'requirement_title': '需求标题',
                    'deadline': '截止时间',
                    'requirement_status': '需求状态',
                    'completed_project_count': '已完成项目数',
                    'pending_score_count': '待评分项目数'
                }
            },
            'org_project_completed': {
                'name': '项目完成通知',
                'category': 'project',
                'description': '当项目完成时发送的通知',
                'variables': {
                    'project_title': '项目标题',
                    'completion_time': '完成时间'
                }
            },
            'student_member_left': {
                'name': '成员退出项目',
                'category': 'project',
                'description': '当项目成员退出项目时发送给项目负责人的通知',
                'variables': {
                    'leader_name': '项目负责人姓名',
                    'member_name': '退出成员姓名',
                    'project_title': '项目标题',
                    'left_time': '退出时间',
                    'member_role_display': '成员原角色',
                    'project_url': '项目链接'
                }
            },
            'student_member_kicked': {
                'name': '成员被移出项目',
                'category': 'project',
                'description': '当项目成员被项目负责人移出项目时发送的通知',
                'variables': {
                    'member_name': '成员姓名',
                    'project_title': '项目标题',
                    'change_time': '移出时间',
                    'operator_name': '操作人姓名',
                    'reason': '移出理由'
                }
            },
            'student_leadership_transfer': {
                'name': '项目负责人身份转移',
                'category': 'project',
                'description': '当项目负责人身份转移时发送给新负责人的通知',
                'variables': {
                    'new_leader_name': '新负责人姓名',
                    'project_title': '项目标题',
                    'original_leader': '原负责人姓名',
                    'transfer_time': '转移时间',
                    'transfer_message': '转移说明',
                    'project_url': '项目链接'
                }
            },
            'student_leadership_change_notification': {
                'name': '项目负责人变更通知',
                'category': 'project',
                'description': '当项目负责人变更时发送给除新旧负责人外的所有成员的通知',
                'variables': {
                    'project_title': '项目标题',
                    'new_leader_name': '新负责人姓名',
                    'new_leader_contact': '新负责人联系方式',
                    'original_leader': '原负责人姓名',
                    'transfer_time': '变更时间',
                    'transfer_message': '变更说明',
                    'project_url': '项目链接'
                }
            },
            'student_project_invitation': {
                'name': '项目邀请通知',
                'category': 'project',
                'description': '当项目负责人邀请学生加入项目时发送的通知',
                'variables': {
                    'inviter_name': '邀请人姓名',
                    'invitee_name': '被邀请人姓名',
                    'project_title': '项目标题',
                    'invitation_time': '邀请时间',
                    'invitation_message': '邀请留言',
                    'expires_at': '过期时间'
                }
            },
            'student_invitation_response': {
                'name': '邀请处理结果通知',
                'category': 'project',
                'description': '当被邀请人回复项目邀请时发送给邀请人的通知',
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
            },
            'student_invitation_expiry_reminder': {
                'name': '邀请过期提醒通知',
                'category': 'project',
                'description': '当项目邀请即将过期时发送的提醒通知',
                'variables': {
                    'invitee_name': '被邀请人姓名',
                    'inviter_name': '邀请人姓名',
                    'project_title': '项目标题',
                    'expires_at': '过期时间'
                }
            },
            'student_project_score_published': {
                'name': '项目评分公示通知',
                'category': 'project',
                'description': '当项目评分结果公示时发送给项目所有成员的通知',
                'variables': {
                    'project_title': '项目标题',
                    'total_score': '总分',
                    'weighted_score': '加权分',
                    'evaluator_name': '评分人姓名',
                    'publish_time': '公示时间',
                    'score_url': '评分详情链接'
                }
            },
            'org_invitation_code_expiring_soon': {
                'name': '邀请码即将过期通知',
                'category': 'organization',
                'description': '当组织邀请码即将在24小时内过期时发送给创建者的通知',
                'variables': {
                    'organization_name': '组织名称',
                    'invitation_code': '邀请码',
                    'creator_name': '创建者姓名',
                    'expires_at': '过期时间',
                    'remaining_hours': '剩余小时数',
                    'used_count': '已使用次数',
                    'max_uses': '最大使用次数'
                }
            },
            'org_invitation_code_expired': {
                'name': '邀请码已过期通知',
                'category': 'organization',
                'description': '当组织邀请码过期时发送给创建者的通知',
                'variables': {
                    'organization_name': '组织名称',
                    'invitation_code': '邀请码',
                    'creator_name': '创建者姓名',
                    'expired_at': '过期时间',
                    'used_count': '已使用次数',
                    'max_uses': '最大使用次数'
                }
            },
            'org_invitation_code_used': {
                'name': '邀请码使用通知',
                'category': 'organization',
                'description': '当有人使用组织邀请码加入时发送给创建者的通知',
                'variables': {
                    'organization_name': '组织名称',
                    'invitation_code_last_4': '邀请码后4位',
                    'creator_name': '创建者姓名',
                    'user_name': '使用者姓名',
                    'user_email': '使用者邮箱',
                    'used_at': '使用时间',
                    'used_count': '已使用次数',
                    'max_uses': '最大使用次数',
                    'remaining_uses': '剩余使用次数'
                }
            }
        }
        
        # 遍历所有配置进行初始化
        for code, config in notification_configs.items():
            template_config = default_templates.get(code)
            if template_config:
                # 创建或获取通知类型
                notification_type, created = NotificationType.objects.get_or_create(
                    code=code,
                    defaults={
                        'name': config['name'],
                        'category': config['category'],
                        'description': config['description'],
                        'default_template': template_config.get('content', ''),
                        'is_active': True
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 创建通知类型: {notification_type.name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  通知类型已存在: {notification_type.name}')
                    )
                
                # 创建或更新通知模板
                template, template_created = NotificationTemplate.objects.get_or_create(
                    notification_type=notification_type,
                    defaults={
                        'title_template': template_config.get('title', config['name']),
                        'content_template': template_config.get('content', ''),
                        'variables': config['variables']
                    }
                )
                
                if template_created:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 创建通知模板: {template.notification_type.name} 模板')
                    )
                else:
                    # 更新现有模板
                    template.title_template = template_config.get('title', config['name'])
                    template.content_template = template_config.get('content', '')
                    template.variables = config['variables']
                    template.save()
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  更新通知模板: {template.notification_type.name} 模板')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ 未找到通知类型 {code} 的模板配置')
                )
        
        self.stdout.write(
            self.style.SUCCESS('🎉 通知类型和模板初始化完成！')
        )
        
        # 显示统计信息
        total_types = NotificationType.objects.count()
        total_templates = NotificationTemplate.objects.count()
        self.stdout.write(f'📊 当前系统中共有 {total_types} 个通知类型，{total_templates} 个通知模板')