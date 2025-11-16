#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为指定需求批量创建学生项目的脚本

功能：
1. 为requirement_id为23、155和165的三个需求各自关联5-6个学生项目
2. 每个项目中要有不少于5名学生用户且状态为申请中或已通过，其中有且仅有一个负责人
3. 所有项目的状态默认都是招募中或者进行中
4. 创建项目的时间严格位于对应需求的发布时间created_at和完成时间finish_time之间
5. 创建的项目中信息要完整，包括项目标题和项目描述
"""

import os
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from project.models import Requirement
from studentproject.models import StudentProject, ProjectParticipant
from user.models import Student
from organization.models import University

# 项目模板数据
PROJECT_TEMPLATES = {
    23: [  # 高校就业困难毕业生就业现状、瓶颈及对策研究
        {
            'title': '就业困难毕业生调研分析项目',
            'description': '通过问卷调查、深度访谈等方式，深入了解高校就业困难毕业生的现状，分析就业瓶颈的根本原因，为制定针对性的就业帮扶政策提供数据支撑。需要具备数据分析、社会调研、统计学等相关技能的团队成员。'
        },
        {
            'title': '毕业生就业支持体系构建研究',
            'description': '基于现有就业困难毕业生的实际情况，设计并构建一套完整的就业支持体系，包括心理辅导、技能培训、就业指导等多个维度。需要教育学、心理学、人力资源管理等专业背景的成员参与。'
        },
        {
            'title': '就业困难群体画像与精准帮扶策略',
            'description': '运用大数据分析技术，构建就业困难毕业生的多维度画像，识别不同类型困难群体的特征，制定个性化的精准帮扶策略。需要数据挖掘、机器学习、统计分析等技术能力。'
        },
        {
            'title': '高校就业服务模式创新实践',
            'description': '探索和实践新型的高校就业服务模式，包括线上线下结合的就业指导、校企合作的实习实训、创业孵化等创新举措。需要具备项目管理、教育创新、产业分析等能力的团队。'
        },
        {
            'title': '就业困难毕业生心理健康干预研究',
            'description': '针对就业困难对毕业生心理健康的影响，开展心理健康状况调研，设计有效的心理干预方案，提升毕业生的就业信心和心理韧性。需要心理学、社会工作、健康管理等专业背景。'
        }
    ],
    155: [  # 在线教育平台开发 - 重点
        {
            'title': '智能化在线学习平台开发',
            'description': '开发一个集成AI技术的在线教育平台，支持个性化学习路径推荐、智能答疑、学习效果评估等功能。采用微服务架构，支持大规模并发访问。需要前端开发、后端开发、AI算法、数据库设计等技术人才。'
        },
        {
            'title': '移动端教育APP设计与实现',
            'description': '基于React Native或Flutter技术栈，开发跨平台的移动教育应用，支持离线学习、实时互动、进度同步等功能。注重用户体验设计和性能优化。需要移动开发、UI/UX设计、后端接口等技能。'
        },
        {
            'title': '在线教育内容管理系统',
            'description': '构建功能完善的教育内容管理系统，支持多媒体课件制作、课程编排、版本控制、权限管理等功能。需要具备全栈开发能力，熟悉内容管理系统架构设计。'
        },
        {
            'title': '教育数据分析与可视化平台',
            'description': '开发教育大数据分析平台，对学习行为、成绩表现、课程效果等进行深度分析，提供直观的数据可视化展示。需要数据分析、机器学习、前端可视化等技术能力。'
        },
        {
            'title': '虚拟现实教育应用开发',
            'description': '利用VR/AR技术开发沉浸式教育应用，为理工科实验、历史文化体验、语言学习等提供创新的教学方式。需要VR/AR开发、3D建模、交互设计等专业技能。'
        },
        {
            'title': '在线考试与评测系统',
            'description': '开发安全可靠的在线考试系统，支持多种题型、防作弊监控、自动阅卷、成绩分析等功能。需要系统安全、算法设计、数据库优化等技术能力。'
        }
    ],
    165: [  # 电商网站开发
        {
            'title': '全栈电商平台开发',
            'description': '开发完整的B2C电商平台，包括商品展示、购物车、订单管理、支付集成、用户系统等核心功能。采用现代化的技术栈，确保系统的可扩展性和安全性。需要前端、后端、数据库、支付接口等全栈开发能力。'
        },
        {
            'title': '电商移动端应用开发',
            'description': '基于主流移动开发框架，开发功能完善的电商移动应用，支持商品浏览、在线支付、物流跟踪、用户评价等功能。注重移动端用户体验和性能优化。需要移动开发、UI设计、后端接口等技能。'
        },
        {
            'title': '电商数据分析与推荐系统',
            'description': '构建电商平台的数据分析体系，开发智能推荐算法，提升用户购物体验和平台转化率。包括用户行为分析、商品推荐、价格优化等功能。需要数据挖掘、机器学习、算法优化等技术能力。'
        },
        {
            'title': '电商供应链管理系统',
            'description': '开发电商平台的供应链管理系统，包括库存管理、采购管理、供应商管理、物流配送等功能模块。需要系统架构设计、业务流程分析、数据库设计等能力。'
        },
        {
            'title': '电商客服与营销自动化平台',
            'description': '基于AI技术开发智能客服系统和营销自动化平台，支持自动回复、订单查询、营销活动管理、用户画像分析等功能。需要自然语言处理、机器学习、系统集成等技术。'
        }
    ]
}

# 项目状态选择
PROJECT_STATUS_CHOICES = ['recruiting', 'in_progress']

# 参与者状态选择
PARTICIPANT_STATUS_CHOICES = ['pending', 'approved']

def get_random_time_between(start_time, end_time):
    """在两个时间之间生成随机时间"""
    if isinstance(start_time, datetime) and isinstance(end_time, datetime):
        time_diff = end_time - start_time
        random_seconds = random.randint(0, int(time_diff.total_seconds()))
        return start_time + timedelta(seconds=random_seconds)
    else:
        # 如果是date类型，转换为datetime
        if hasattr(start_time, 'date'):
            start_dt = start_time
        else:
            start_dt = datetime.combine(start_time, datetime.min.time())
            if timezone.is_naive(start_dt):
                start_dt = timezone.make_aware(start_dt)
        
        if hasattr(end_time, 'date'):
            end_dt = end_time
        else:
            end_dt = datetime.combine(end_time, datetime.max.time())
            if timezone.is_naive(end_dt):
                end_dt = timezone.make_aware(end_dt)
        
        time_diff = end_dt - start_dt
        random_seconds = random.randint(0, int(time_diff.total_seconds()))
        return start_dt + timedelta(seconds=random_seconds)

def create_projects_for_requirements():
    """为指定需求创建项目"""
    target_requirement_ids = [23, 155, 165]
    
    print("开始为指定需求创建学生项目...")
    print("="*50)
    
    # 获取北京邮电大学
    bupt = University.objects.filter(school='北京邮电大学').first()
    if not bupt:
        print("错误：未找到北京邮电大学")
        return
    
    # 获取所有学生，优先选择北京邮电大学的学生
    bupt_students = list(Student.objects.filter(school=bupt, status='studying'))
    other_students = list(Student.objects.exclude(school=bupt).filter(status='studying'))
    
    print(f"北京邮电大学学生数量: {len(bupt_students)}")
    print(f"其他大学学生数量: {len(other_students)}")
    
    if len(bupt_students) < 10:
        print("警告：北京邮电大学学生数量不足，可能影响项目创建")
    
    created_projects = []
    
    with transaction.atomic():
        for req_id in target_requirement_ids:
            try:
                # 获取需求信息
                requirement = Requirement.objects.get(id=req_id)
                print(f"\n处理需求 ID {req_id}: {requirement.title}")
                print(f"需求创建时间: {requirement.created_at}")
                print(f"需求完成时间: {requirement.finish_time}")
                
                # 获取该需求的项目模板
                templates = PROJECT_TEMPLATES.get(req_id, [])
                if not templates:
                    print(f"警告：需求 {req_id} 没有对应的项目模板")
                    continue
                
                # 为该需求创建5-6个项目
                num_projects = random.randint(5, 6)
                selected_templates = random.sample(templates, min(num_projects, len(templates)))
                
                print(f"将为需求 {req_id} 创建 {len(selected_templates)} 个项目")
                
                for i, template in enumerate(selected_templates, 1):
                    # 生成项目创建时间（在需求创建时间和完成时间之间）
                    project_created_time = get_random_time_between(
                        requirement.created_at,
                        datetime.combine(requirement.finish_time, datetime.max.time()).replace(tzinfo=timezone.get_current_timezone())
                    )
                    
                    # 创建项目
                    project = StudentProject.objects.create(
                        title=template['title'],
                        description=template['description'],
                        requirement=requirement,
                        status=random.choice(PROJECT_STATUS_CHOICES)
                    )
                    
                    # 手动更新创建时间
                    StudentProject.objects.filter(id=project.id).update(
                        created_at=project_created_time,
                        updated_at=project_created_time
                    )
                    
                    # 重新获取项目对象
                    project.refresh_from_db()
                    
                    print(f"  创建项目 {i}: {project.title} (状态: {project.get_status_display()})")
                    print(f"    创建时间: {project.created_at}")
                    
                    # 为项目添加参与者
                    create_project_participants(project, bupt_students, other_students)
                    
                    created_projects.append(project)
                    
            except Requirement.DoesNotExist:
                print(f"错误：需求 ID {req_id} 不存在")
                continue
            except Exception as e:
                print(f"创建需求 {req_id} 的项目时出错: {e}")
                continue
    
    print(f"\n项目创建完成！共创建 {len(created_projects)} 个项目")
    return created_projects

def create_project_participants(project, bupt_students, other_students):
    """为项目创建参与者"""
    # 确定参与者数量（5-8人）
    num_participants = random.randint(5, 8)
    
    # 优先选择北京邮电大学的学生（占70-80%）
    num_bupt = int(num_participants * random.uniform(0.7, 0.8))
    num_others = num_participants - num_bupt
    
    # 确保有足够的学生
    if len(bupt_students) < num_bupt:
        num_bupt = len(bupt_students)
        num_others = num_participants - num_bupt
    
    if len(other_students) < num_others:
        num_others = min(len(other_students), num_participants - num_bupt)
    
    # 选择参与者
    selected_bupt = random.sample(bupt_students, num_bupt) if num_bupt > 0 else []
    selected_others = random.sample(other_students, num_others) if num_others > 0 else []
    
    all_participants = selected_bupt + selected_others
    random.shuffle(all_participants)  # 随机打乱顺序
    
    if not all_participants:
        print(f"    警告：项目 {project.title} 没有可用的参与者")
        return
    
    # 第一个学生作为负责人
    leader = all_participants[0]
    members = all_participants[1:]
    
    # 创建负责人记录
    ProjectParticipant.objects.create(
        project=project,
        student=leader,
        role='leader',
        status='approved',
        application_message='项目负责人',
        applied_at=project.created_at,
        reviewed_at=project.created_at,
        reviewed_by=leader
    )
    
    print(f"    负责人: {leader.user.real_name} ({leader.school.school})")
    
    # 创建成员记录
    approved_count = 0
    pending_count = 0
    
    for member in members:
        # 随机决定成员状态（申请中或已通过）
        status = random.choice(PARTICIPANT_STATUS_CHOICES)
        
        # 确保至少有4个成员是已通过状态（加上负责人总共至少5人）
        remaining_members = len(members) - (approved_count + pending_count)
        min_approved_needed = max(0, 4 - approved_count)
        
        if remaining_members <= min_approved_needed:
            status = 'approved'
        
        if status == 'approved':
            approved_count += 1
        else:
            pending_count += 1
        
        # 生成申请时间（项目创建后的几天内）
        apply_time = project.created_at + timedelta(
            hours=random.randint(1, 72)  # 1-72小时内申请
        )
        
        # 如果是已通过状态，生成审核时间
        review_time = None
        reviewer = None
        if status == 'approved':
            review_time = apply_time + timedelta(
                hours=random.randint(1, 24)  # 申请后1-24小时内审核
            )
            reviewer = leader
        
        ProjectParticipant.objects.create(
            project=project,
            student=member,
            role='member',
            status=status,
            application_message=f'申请加入项目：{project.title}',
            applied_at=apply_time,
            reviewed_at=review_time,
            reviewed_by=reviewer
        )
    
    print(f"    成员: {len(members)}人 (已通过: {approved_count}, 申请中: {pending_count})")
    print(f"    北京邮电大学学生: {len(selected_bupt)}人, 其他大学学生: {len(selected_others)}人")

def print_summary(projects):
    """打印创建结果摘要"""
    print("\n" + "="*50)
    print("项目创建结果摘要")
    print("="*50)
    
    # 按需求分组统计
    req_stats = {}
    for project in projects:
        req_id = project.requirement.id
        if req_id not in req_stats:
            req_stats[req_id] = {
                'requirement_title': project.requirement.title,
                'projects': [],
                'total_participants': 0
            }
        req_stats[req_id]['projects'].append(project)
    
    for req_id, stats in req_stats.items():
        print(f"\n需求 {req_id}: {stats['requirement_title']}")
        print(f"  创建项目数: {len(stats['projects'])}")
        
        for project in stats['projects']:
            participants = ProjectParticipant.objects.filter(project=project)
            leader_count = participants.filter(role='leader').count()
            approved_count = participants.filter(status='approved').count()
            pending_count = participants.filter(status='pending').count()
            
            print(f"    - {project.title}")
            print(f"      状态: {project.get_status_display()}")
            print(f"      参与者: {participants.count()}人 (负责人: {leader_count}, 已通过: {approved_count}, 申请中: {pending_count})")
            print(f"      创建时间: {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 总体统计
    total_participants = ProjectParticipant.objects.filter(
        project__in=projects
    ).count()
    
    bupt_participants = ProjectParticipant.objects.filter(
        project__in=projects,
        student__school__school='北京邮电大学'
    ).count()
    
    print(f"\n总体统计:")
    print(f"  总项目数: {len(projects)}")
    print(f"  总参与人次: {total_participants}")
    print(f"  北京邮电大学学生参与人次: {bupt_participants} ({bupt_participants/total_participants*100:.1f}%)")

if __name__ == '__main__':
    print("学生项目批量创建脚本")
    print("目标需求: 23, 155, 165")
    print("="*50)
    
    # 检查目标需求是否存在
    target_ids = [23, 155, 165]
    existing_reqs = Requirement.objects.filter(id__in=target_ids)
    
    print("需求检查结果:")
    for req in existing_reqs:
        print(f"  需求 {req.id}: {req.title} (状态: {req.get_status_display()})")
        print(f"    创建时间: {req.created_at}")
        print(f"    完成时间: {req.finish_time}")
    
    missing_ids = set(target_ids) - set(req.id for req in existing_reqs)
    if missing_ids:
        print(f"  缺失需求: {list(missing_ids)}")
    
    if len(existing_reqs) == 0:
        print("错误：没有找到任何目标需求，脚本退出")
        exit(1)
    
    print("\n开始创建项目...")
    created_projects = create_projects_for_requirements()
    
    if created_projects:
        print_summary(created_projects)
        print("\n脚本执行完成！")
    else:
        print("\n没有创建任何项目")