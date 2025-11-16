#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成测试学生项目数据的脚本

使用方法：
1. 确保已有测试用户数据（运行 python manage.py create_test_users）
2. 确保已有需求数据（运行 python generate_requirement_data.py）
3. 运行此脚本：python generate_student_project_data.py
"""

import os
import sys
import django
import random
from datetime import datetime, timedelta

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from django.utils import timezone
from django.db import transaction
from studentproject.models import StudentProject, ProjectParticipant
from project.models import Requirement
from user.models import Student


def clear_existing_data():
    """清除现有的学生项目数据"""
    print("正在清除现有学生项目数据...")
    ProjectParticipant.objects.all().delete()
    StudentProject.objects.all().delete()
    print("清除完成")


def get_test_students():
    """获取测试学生用户"""
    students = Student.objects.filter(
        user__username__startswith='test_student_'
    )
    if not students.exists():
        print("错误：未找到测试学生用户，请先运行 'python manage.py create_test_users'")
        sys.exit(1)
    return list(students)


def get_test_requirements():
    """获取测试需求数据"""
    # 查找进行中的需求
    requirements = Requirement.objects.filter(status='in_progress')
    if not requirements.exists():
        print("错误：未找到进行中的需求，请先运行 'python generate_requirement_data.py'")
        sys.exit(1)
    return list(requirements)


def create_student_projects():
    """创建测试学生项目，创建时间分布在2025年1月至7月"""
    students = get_test_students()
    requirements = get_test_requirements()
    
    if len(students) == 0:
        print("没有可用的测试学生")
        return []
    
    if len(requirements) == 0:
        print("没有可用的需求")
        return []
    
    # 按组织分组需求
    org_requirements = {}
    for req in requirements:
        org_id = req.organization.id
        if org_id not in org_requirements:
            org_requirements[org_id] = []
        org_requirements[org_id].append(req)
    
    print(f"需求分布在 {len(org_requirements)} 个组织中")
    
    # 生成2025年1月至7月的时间范围
    start_date = timezone.make_aware(datetime(2025, 1, 1, 0, 0, 0))
    end_date = timezone.make_aware(datetime(2025, 7, 31, 23, 59, 59))
    
    # 项目模板数据 (35个项目)
    project_templates = [
        {
            'title': '智能校园导航系统',
            'description': '基于AI技术的校园室内外导航系统，支持语音导航、实时路况、无障碍路线规划等功能。采用深度学习算法优化路径规划，提供个性化导航服务。',
            'status': 'recruiting'
        },
        {
            'title': '在线学习平台开发',
            'description': '构建现代化的在线学习平台，支持视频直播、互动讨论、作业提交、成绩管理等功能。采用微服务架构，支持大规模并发访问。',
            'status': 'in_progress'
        },
        {
            'title': '企业数据分析系统',
            'description': '为企业提供全方位的数据分析解决方案，包括数据采集、清洗、分析、可视化展示。支持实时数据处理和预测分析。',
            'status': 'recruiting'
        },
        {
            'title': '移动端健康管理App',
            'description': '开发跨平台的健康管理应用，集成运动监测、饮食记录、健康提醒、医疗咨询等功能。采用React Native技术栈。',
            'status': 'draft'
        },
        {
            'title': '区块链供应链追溯系统',
            'description': '基于区块链技术的供应链管理系统，实现商品从生产到销售全流程的透明化追溯，保障食品安全和产品质量。',
            'status': 'recruiting'
        },
        {
            'title': '智能客服机器人',
            'description': '开发基于自然语言处理的智能客服系统，支持多轮对话、情感分析、知识图谱查询等功能，提升客户服务效率。',
            'status': 'in_progress'
        },
        {
            'title': '物联网环境监测系统',
            'description': '构建基于物联网的环境监测网络，实时监测空气质量、温湿度、噪音等环境指标，提供数据分析和预警服务。',
            'status': 'recruiting'
        },
        {
            'title': '虚拟现实教育平台',
            'description': '开发VR教育应用，为学生提供沉浸式学习体验。涵盖历史、地理、生物等多个学科的虚拟场景和交互式学习内容。',
            'status': 'draft'
        },
        {
            'title': '智能交通管理系统',
            'description': '基于计算机视觉和机器学习的智能交通管理平台，实现车流量统计、违章检测、信号灯优化等功能。',
            'status': 'recruiting'
        },
        {
            'title': '云原生微服务架构',
            'description': '设计和实现基于Kubernetes的云原生微服务架构，包括服务发现、负载均衡、监控告警、自动扩缩容等功能。',
            'status': 'in_progress'
        },
        {
            'title': '人工智能写作助手',
            'description': '开发基于大语言模型的智能写作助手，支持文章生成、语法检查、风格优化、多语言翻译等功能。',
            'status': 'recruiting'
        },
        {
            'title': '数字化图书馆系统',
            'description': '构建现代化的数字图书馆管理系统，支持图书检索、在线阅读、借阅管理、推荐算法等功能。',
            'status': 'draft'
        },
        {
            'title': '企业级CRM系统',
            'description': '开发功能完善的客户关系管理系统，包括客户信息管理、销售流程跟踪、数据分析报表、营销自动化等模块。',
            'status': 'recruiting'
        },
        {
            'title': '智能家居控制平台',
            'description': '基于物联网技术的智能家居控制系统，支持设备联动、语音控制、远程监控、节能优化等功能。',
            'status': 'in_progress'
        },
        {
            'title': '在线协作办公平台',
            'description': '开发支持远程办公的协作平台，集成文档编辑、视频会议、项目管理、即时通讯等功能，提升团队协作效率。',
            'status': 'recruiting'
        },
        {
            'title': '电商平台后端系统',
            'description': '构建高并发的电商平台后端系统，包括商品管理、订单处理、支付集成、库存管理、用户系统等核心功能。',
            'status': 'recruiting'
        },
        {
            'title': '社交媒体分析工具',
            'description': '开发社交媒体数据分析平台，支持多平台数据采集、情感分析、趋势预测、用户画像分析等功能。',
            'status': 'draft'
        },
        {
            'title': '智能推荐系统',
            'description': '基于机器学习的个性化推荐系统，支持协同过滤、内容推荐、深度学习推荐算法，提供精准的个性化服务。',
            'status': 'recruiting'
        },
        {
            'title': '在线考试系统',
            'description': '开发功能完善的在线考试平台，支持题库管理、自动组卷、防作弊监控、成绩统计分析等功能。',
            'status': 'in_progress'
        },
        {
            'title': '智能停车管理系统',
            'description': '基于物联网和AI技术的智能停车解决方案，包括车位检测、自动计费、导航引导、移动支付等功能。',
            'status': 'recruiting'
        },
        {
            'title': '企业知识管理平台',
            'description': '构建企业级知识管理系统，支持文档管理、知识图谱、智能搜索、协作编辑、版本控制等功能。',
            'status': 'draft'
        },
        {
            'title': '智能农业监控系统',
            'description': '开发基于IoT的智能农业监控平台，实现土壤监测、气象预警、自动灌溉、病虫害识别等功能。',
            'status': 'recruiting'
        },
        {
            'title': '区块链投票系统',
            'description': '基于区块链技术的去中心化投票平台，确保投票过程的透明性、不可篡改性和匿名性。',
            'status': 'in_progress'
        },
        {
            'title': '智能语音助手',
            'description': '开发多功能智能语音助手，支持语音识别、自然语言理解、任务执行、多轮对话等功能。',
            'status': 'recruiting'
        },
        {
            'title': '在线医疗咨询平台',
            'description': '构建在线医疗服务平台，包括医生预约、视频问诊、电子病历、药品配送、健康档案管理等功能。',
            'status': 'draft'
        },
        {
            'title': '智能财务管理系统',
            'description': '开发企业级财务管理软件，支持账务处理、报表生成、预算管理、风险控制、税务计算等功能。',
            'status': 'recruiting'
        },
        {
            'title': '虚拟试衣间系统',
            'description': '基于AR技术的虚拟试衣解决方案，支持3D建模、实时渲染、尺寸匹配、效果预览等功能。',
            'status': 'in_progress'
        },
        {
            'title': '智能能源管理平台',
            'description': '构建智能电网管理系统，实现能源监控、负载预测、优化调度、节能分析等功能。',
            'status': 'recruiting'
        },
        {
            'title': '在线直播教育平台',
            'description': '开发专业的在线教育直播平台，支持高清直播、互动白板、录播回放、作业批改、学习分析等功能。',
            'status': 'draft'
        },
        {
            'title': '智能安防监控系统',
            'description': '基于计算机视觉的智能安防平台，支持人脸识别、行为分析、异常检测、实时报警等功能。',
            'status': 'recruiting'
        },
        {
            'title': '区块链数字身份系统',
            'description': '开发基于区块链的数字身份认证平台，实现身份验证、隐私保护、去中心化认证等功能。',
            'status': 'in_progress'
        },
        {
            'title': '智能物流配送系统',
            'description': '构建智能物流管理平台，包括路径优化、实时跟踪、智能调度、配送预测、成本分析等功能。',
            'status': 'recruiting'
        },
        {
            'title': '在线音乐创作平台',
            'description': '开发音乐创作和分享平台，支持在线编曲、音频处理、协作创作、版权保护、社区互动等功能。',
            'status': 'draft'
        },
        {
            'title': '智能制造执行系统',
            'description': '构建工业4.0智能制造平台，实现生产计划、质量控制、设备监控、数据分析、预测维护等功能。',
            'status': 'recruiting'
        },
        {
            'title': '虚拟现实培训系统',
            'description': '开发VR职业培训平台，提供沉浸式培训体验，支持技能评估、进度跟踪、多场景模拟等功能。',
            'status': 'in_progress'
        }
    ]
    
    created_projects = []
    
    with transaction.atomic():
        # 为每个项目模板创建项目
        for i, template in enumerate(project_templates):
            # 随机选择一个需求
            requirement = random.choice(requirements)
            
            # 随机选择一个学生作为项目负责人
            leader = random.choice(students)
            
            # 创建项目
            project = StudentProject.objects.create(
                title=template['title'],
                description=template['description'],
                requirement=requirement,
                status=template['status']
            )
            
            # 生成随机的创建时间（2025年1月至7月）
            random_timestamp = start_date + timedelta(
                seconds=random.randint(0, int((end_date - start_date).total_seconds()))
            )
            
            # 手动更新created_at和updated_at字段
            # 由于模型使用auto_now_add=True和auto_now=True，需要使用update()方法
            StudentProject.objects.filter(id=project.id).update(
                created_at=random_timestamp,
                updated_at=random_timestamp
            )
            
            # 重新获取项目对象以获得更新后的时间戳
            project.refresh_from_db()
            
            # 创建项目负责人记录
            ProjectParticipant.objects.create(
                project=project,
                student=leader,
                role='leader',
                status='approved',
                application_message='项目创建者自动成为leader',
                applied_at=timezone.now(),
                reviewed_at=timezone.now(),
                reviewed_by=leader
            )
            
            # 为部分项目添加成员
            if template['status'] in ['recruiting', 'in_progress'] and len(students) > 1:
                # 随机选择1-3个其他学生作为成员
                available_students = [s for s in students if s != leader]
                num_members = random.randint(1, min(3, len(available_students)))
                members = random.sample(available_students, num_members)
                
                for member in members:
                    # 随机决定成员状态
                    if template['status'] == 'in_progress':
                        member_status = 'approved'
                    else:
                        member_status = random.choice(['pending', 'approved'])
                    
                    ProjectParticipant.objects.create(
                        project=project,
                        student=member,
                        role='member',
                        status=member_status,
                        application_message=f'申请加入项目：{template["title"]}',
                        applied_at=timezone.now() - timedelta(days=random.randint(1, 7)),
                        reviewed_at=timezone.now() - timedelta(days=random.randint(0, 3)) if member_status == 'approved' else None,
                        reviewed_by=leader if member_status == 'approved' else None
                    )
            
            created_projects.append(project)
            print(f"创建项目: {project.title} (负责人: {leader.user.real_name}) (创建时间: {project.created_at.strftime('%Y-%m-%d %H:%M')})")
    
    return created_projects


def print_summary(projects):
    """打印创建结果摘要"""
    print("\n" + "="*50)
    print("学生项目数据生成完成")
    print("="*50)
    print(f"总项目数: {len(projects)}")
    
    # 按状态统计
    status_count = {}
    for project in projects:
        status = project.get_status_display()
        status_count[status] = status_count.get(status, 0) + 1
    
    print("\n项目状态分布:")
    for status, count in status_count.items():
        print(f"  {status}: {count}个")
    
    # 统计参与者
    total_participants = ProjectParticipant.objects.count()
    leaders = ProjectParticipant.objects.filter(role='leader').count()
    members = ProjectParticipant.objects.filter(role='member').count()
    
    print(f"\n参与者统计:")
    print(f"  总参与者: {total_participants}人次")
    print(f"  项目负责人: {leaders}人")
    print(f"  项目成员: {members}人")
    
    # 按月份统计创建时间分布
    month_count = {}
    for project in projects:
        month_key = project.created_at.strftime('%Y-%m')
        month_count[month_key] = month_count.get(month_key, 0) + 1
    
    print("\n按月份分布:")
    for month, count in sorted(month_count.items()):
        print(f"  {month}: {count} 个项目")
    
    # 时间范围统计
    if projects:
        earliest = min(project.created_at for project in projects)
        latest = max(project.created_at for project in projects)
        print(f"\n创建时间范围:")
        print(f"  最早: {earliest.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  最晚: {latest.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n项目列表:")
    for project in projects:
        participants_count = project.project_participants.count()
        print(f"  {project.title} ({project.get_status_display()}) - {participants_count}人参与")


def main():
    """主函数"""
    print("开始生成学生项目测试数据...")
    
    # 清除现有数据
    clear_existing_data()
    
    # 创建项目数据
    projects = create_student_projects()
    
    # 打印摘要
    print_summary(projects)
    
    print("\n数据生成完成！")
    print("\n使用说明:")
    print("1. 可以通过Django Admin查看创建的项目数据")
    print("2. 可以通过API接口测试项目相关功能")
    print("3. 测试用户密码统一为: test123456")


if __name__ == '__main__':
    main()