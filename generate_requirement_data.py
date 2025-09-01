#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成测试需求数据的脚本
"""

import os
import sys
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from project.models import Requirement
from user.models import Tag1, Tag2, OrganizationUser
from organization.models import Organization

def generate_requirement_data(count=100):
    """生成需求数据"""
    
    # 获取现有数据
    organizations = list(Organization.objects.all())
    org_users = list(OrganizationUser.objects.filter(permission__in=['admin', 'owner']))
    tag1_list = list(Tag1.objects.all())
    tag2_list = list(Tag2.objects.all())
    
    print(f"可用组织数量: {len(organizations)}")
    print(f"可用组织用户数量: {len(org_users)}")
    print(f"可用兴趣标签数量: {len(tag1_list)}")
    print(f"可用能力标签数量: {len(tag2_list)}")
    print(f"计划生成需求数量: {count}")
    
    # 扩展的需求模板数据
    requirement_templates = [
        {
            'title': 'AI智能客服系统开发',
            'brief': '基于大语言模型的智能客服系统，支持多轮对话和知识库问答',
            'description': '我们需要开发一个基于大语言模型的智能客服系统，能够处理用户的多轮对话，支持知识库检索和问答。系统需要具备自然语言理解、意图识别、实体抽取等功能，并能够与现有的CRM系统集成。',
            'budget': '500-1000',
            'people_count': '5-8',
            'finish_time': '6个月',
            'tag1_keywords': ['人工智能', '大模型', '自然语言处理'],
            'tag2_keywords': ['Python', 'AI', '后端开发']
        },
        {
            'title': '智能图像识别系统',
            'brief': '构建基于深度学习的图像识别和分析系统',
            'description': '开发基于深度学习的图像识别系统，支持人脸识别、物体检测、场景分析等功能。系统需要具备高精度识别能力和实时处理性能，可应用于安防、零售、医疗等多个领域。',
            'budget': '800-1500',
            'people_count': '6-10',
            'finish_time': '8个月',
            'tag1_keywords': ['计算机视觉', '深度学习', '图像处理'],
            'tag2_keywords': ['Python', 'TensorFlow', 'OpenCV']
        },
        {
            'title': '电商平台数据分析系统',
            'brief': '构建实时数据分析平台，支持用户行为分析和商品推荐',
            'description': '需要构建一个实时的电商数据分析平台，能够分析用户行为、商品销售趋势、库存管理等。系统需要支持实时数据处理、可视化展示和智能推荐算法。',
            'budget': '300-500',
            'people_count': '4-6',
            'finish_time': '4个月',
            'tag1_keywords': ['数据分析', '机器学习', '数据挖掘'],
            'tag2_keywords': ['Python', '大数据', '数据分析']
        },
        {
            'title': '实时数据流处理平台',
            'brief': '构建高性能的实时数据流处理和分析平台',
            'description': '开发企业级实时数据流处理平台，支持海量数据的实时采集、清洗、分析和存储。平台需要支持多种数据源接入，提供灵活的数据处理规则配置和实时监控功能。',
            'budget': '100-200',
            'people_count': '8-12',
            'finish_time': '10个月',
            'tag1_keywords': ['大数据', '实时计算', '数据工程'],
            'tag2_keywords': ['Kafka', 'Spark', 'Hadoop']
        },
        {
            'title': '移动端社交应用开发',
            'brief': '开发一款面向年轻用户的移动社交应用，支持短视频分享',
            'description': '开发一款创新的移动社交应用，主要面向18-30岁的年轻用户群体。应用需要支持短视频拍摄、编辑、分享，实时聊天，动态发布等功能。需要同时支持iOS和Android平台。',
            'budget': '800-1200',
            'people_count': '8-12',
            'finish_time': '8个月',
            'tag1_keywords': ['移动开发', '社交媒体', '短视频制作'],
            'tag2_keywords': ['移动开发', 'iOS', 'Android']
        },
        {
            'title': '在线教育移动应用',
            'brief': '开发功能完善的在线教育移动学习平台',
            'description': '构建全功能的在线教育移动应用，支持视频课程播放、在线考试、作业提交、师生互动等功能。应用需要支持离线下载、多终端同步，提供个性化学习推荐。',
            'budget': '600-1000',
            'people_count': '6-10',
            'finish_time': '7个月',
            'tag1_keywords': ['在线教育', '移动开发', '视频播放'],
            'tag2_keywords': ['移动开发', 'React Native', 'Flutter']
        },
        {
            'title': '区块链供应链管理系统',
            'brief': '基于区块链技术的供应链溯源和管理系统',
            'description': '构建基于区块链技术的供应链管理系统，实现商品从生产到销售的全链路溯源。系统需要支持多方参与、数据不可篡改、智能合约执行等功能。',
            'budget': '100-150',
            'people_count': '6-10',
            'finish_time': '10个月',
            'tag1_keywords': ['区块链', '供应链管理', '智能合约'],
            'tag2_keywords': ['区块链', '后端开发', 'Solidity']
        },
        {
            'title': '数字身份认证系统',
            'brief': '构建基于区块链的去中心化数字身份认证平台',
            'description': '开发基于区块链的数字身份认证系统，支持去中心化身份管理、隐私保护、多平台互认等功能。系统需要符合国际标准，具备高安全性和可扩展性。',
            'budget': '120-200',
            'people_count': '8-12',
            'finish_time': '12个月',
            'tag1_keywords': ['区块链', '数字身份', '隐私保护'],
            'tag2_keywords': ['区块链', '密码学', 'Go']
        },
        {
            'title': '企业级云原生应用平台',
            'brief': '构建支持微服务架构的云原生应用开发和部署平台',
            'description': '开发企业级的云原生应用平台，支持微服务架构、容器化部署、自动扩缩容、服务网格等功能。平台需要提供完整的DevOps工具链和监控体系。',
            'budget': '200-300',
            'people_count': '10-15',
            'finish_time': '12个月',
            'tag1_keywords': ['云计算', '微服务', 'DevOps'],
            'tag2_keywords': ['云计算', 'Kubernetes', '后端开发']
        },
        {
            'title': '多云管理平台',
            'brief': '开发统一的多云资源管理和优化平台',
            'description': '构建企业级多云管理平台，支持AWS、Azure、阿里云等多个云服务商的资源统一管理、成本优化、安全监控等功能。平台需要提供直观的管理界面和智能化运维能力。',
            'budget': '150-250',
            'people_count': '8-12',
            'finish_time': '10个月',
            'tag1_keywords': ['云计算', '多云管理', '成本优化'],
            'tag2_keywords': ['云计算', 'DevOps', 'Python']
        },
        {
            'title': '智能家居IoT控制系统',
            'brief': '开发智能家居设备的统一控制和管理系统',
            'description': '开发一套完整的智能家居IoT控制系统，能够统一管理各种智能设备，支持语音控制、场景联动、远程监控等功能。系统需要具备良好的扩展性和安全性。',
            'budget': '60-90',
            'people_count': '6-8',
            'finish_time': '7个月',
            'tag1_keywords': ['物联网', '智能家居', '嵌入式开发'],
            'tag2_keywords': ['物联网', '嵌入式', 'C++']
        },
        {
            'title': '工业物联网监控系统',
            'brief': '构建工业级设备监控和预测维护系统',
            'description': '开发工业物联网监控系统，实现设备状态实时监测、预测性维护、生产数据采集分析等功能。系统需要支持多种工业协议，具备边缘计算能力和高可靠性。',
            'budget': '100-180',
            'people_count': '8-12',
            'finish_time': '9个月',
            'tag1_keywords': ['工业物联网', '边缘计算', '预测维护'],
            'tag2_keywords': ['物联网', 'C++', '嵌入式']
        },
        {
            'title': '在线教育平台开发',
            'brief': '构建支持直播、录播、互动的在线教育平台',
            'description': '开发一个功能完善的在线教育平台，支持直播授课、录播回放、在线作业、考试系统、学习进度跟踪等功能。平台需要支持大并发访问和多终端适配。',
            'budget': '120-180',
            'people_count': '12-18',
            'finish_time': '10个月',
            'tag1_keywords': ['在线教育', 'Web开发', '直播技术'],
            'tag2_keywords': ['Web开发', '前端开发', '后端开发']
        },
        {
            'title': '跨境电商平台开发',
            'brief': '构建功能完善的跨境电商交易平台',
            'description': '开发跨境电商平台，支持多语言、多货币、国际物流、海关对接等功能。平台需要具备高可用性、安全性，支持大规模并发交易处理。',
            'budget': '200-350',
            'people_count': '15-20',
            'finish_time': '14个月',
            'tag1_keywords': ['电商', '跨境贸易', '多语言'],
            'tag2_keywords': ['Web开发', 'Java', 'Spring']
        },
        {
            'title': '网络安全态势感知系统',
            'brief': '构建企业级网络安全监控和威胁检测系统',
            'description': '开发企业级的网络安全态势感知系统，能够实时监控网络流量、检测安全威胁、分析攻击行为。系统需要支持多种安全设备接入和智能告警功能。',
            'budget': '150-200',
            'people_count': '8-12',
            'finish_time': '9个月',
            'tag1_keywords': ['网络安全', '威胁检测', '安全分析'],
            'tag2_keywords': ['网络安全', '后端开发', 'Python']
        },
        {
            'title': '数据加密与权限管理系统',
            'brief': '构建企业级数据安全和权限控制系统',
            'description': '开发企业级数据加密和权限管理系统，支持细粒度权限控制、数据脱敏、审计日志等安全功能。系统需要符合合规要求，具备高性能和易用性。',
            'budget': '80-150',
            'people_count': '6-10',
            'finish_time': '8个月',
            'tag1_keywords': ['数据安全', '权限管理', '加密'],
            'tag2_keywords': ['安全开发', 'Java', '密码学']
        },
        {
            'title': '高性能数据库集群系统',
            'brief': '构建支持海量数据存储和高并发访问的数据库集群',
            'description': '开发高性能的分布式数据库集群系统，支持海量数据存储、高并发读写、自动分片、故障恢复等功能。系统需要具备良好的扩展性和可靠性。',
            'budget': '100-150',
            'people_count': '6-10',
            'finish_time': '8个月',
            'tag1_keywords': ['数据库', '分布式系统', '高并发'],
            'tag2_keywords': ['数据库', '后端开发', 'Java']
        },
        {
            'title': '数据仓库ETL系统',
            'brief': '构建企业级数据仓库和ETL处理系统',
            'description': '开发企业级数据仓库ETL系统，支持多源数据抽取、转换、加载，提供数据质量监控和元数据管理功能。系统需要支持大数据量处理和实时同步。',
            'budget': '80-120',
            'people_count': '6-8',
            'finish_time': '7个月',
            'tag1_keywords': ['数据仓库', 'ETL', '数据治理'],
            'tag2_keywords': ['数据库', 'SQL', 'Python']
        },
        {
            'title': '游戏引擎优化项目',
            'brief': '优化现有游戏引擎的渲染性能和内存管理',
            'description': '对现有的3D游戏引擎进行性能优化，主要包括渲染管线优化、内存管理改进、多线程处理优化等。项目需要在保证画质的前提下显著提升游戏性能。',
            'budget': '80-120',
            'people_count': '5-8',
            'finish_time': '6个月',
            'tag1_keywords': ['游戏开发', '性能优化', '图形渲染'],
            'tag2_keywords': ['游戏开发', 'C++', '图形学']
        },
        {
            'title': '多人在线游戏开发',
            'brief': '开发大型多人在线角色扮演游戏',
            'description': '开发大型多人在线角色扮演游戏，支持实时战斗、公会系统、交易系统等核心玩法。游戏需要支持高并发、低延迟，提供丰富的社交和竞技功能。',
            'budget': '300-500',
            'people_count': '20-30',
            'finish_time': '18个月',
            'tag1_keywords': ['游戏开发', '多人在线', '实时战斗'],
            'tag2_keywords': ['游戏开发', 'Unity', 'C#']
        }
    ]
    
    # 状态选项
    status_options = ['under_review', 'in_progress', 'completed', 'paused']
    
    created_count = 0
    
    # 选择一个特殊组织，用于创建过去7周每周至少两个需求
    special_org = random.choice(organizations)
    print(f"特殊组织: {special_org.name}")
    
    # 定义每周需求数量，确保不同且>=2
    week_nums = list(range(2,9))
    random.shuffle(week_nums)
    
    # 假设今天是2025-08-17
    today = timezone.make_aware(datetime(2025, 8, 17, 0, 0, 0))
    
    # 为特殊组织创建过去7周的需求
    for week in range(7):
        num = week_nums[week]
        week_start = today - timedelta(weeks=week + 1)
        for _ in range(num):
            template = random.choice(requirement_templates)
            try:
                publish_person = random.choice([u for u in org_users if u.organization == special_org])
                day_offset = random.randint(0,6)
                time_offset = timedelta(days=day_offset, hours=random.randint(0,23), minutes=random.randint(0,59))
                created_at = week_start + time_offset
                
                if '个月' in template['finish_time']:
                    months = int(template['finish_time'].replace('个月', ''))
                    finish_time = (created_at + timedelta(days=months * 30)).date()
                else:
                    finish_time = None
                
                requirement = Requirement.objects.create(
                    title=template['title'],
                    brief=template['brief'],
                    description=template['description'],
                    field=template['field'],
                    status=random.choice(status_options),
                    organization=special_org,
                    publish_people=publish_person,
                    finish_time=finish_time,
                    budget=template['budget'],
                    people_count=template['people_count'],
                    applications=random.randint(0, 50),
                    joined_count=random.randint(0, 10),
                    views=random.randint(10, 1000)
                )
                # 设置自定义创建时间（绕过auto_now_add）
                Requirement.objects.filter(id=requirement.id).update(created_at=created_at, updated_at=created_at)
                
                for keyword in template['tag1_keywords']:
                    matching_tags = [tag for tag in tag1_list if keyword.lower() in tag.value.lower()]
                    if matching_tags:
                        selected_tags = random.sample(matching_tags, min(2, len(matching_tags)))
                        for tag in selected_tags:
                            requirement.tag1.add(tag)
                
                for keyword in template['tag2_keywords']:
                    matching_tags = [tag for tag in tag2_list if 
                                   keyword.lower() in tag.category.lower() or 
                                   keyword.lower() in tag.subcategory.lower() or 
                                   (tag.specialty and keyword.lower() in tag.specialty.lower())]
                    if matching_tags:
                        selected_tags = random.sample(matching_tags, min(3, len(matching_tags)))
                        for tag in selected_tags:
                            requirement.tag2.add(tag)
                
                created_count += 1
                print(f"创建特殊需求 {created_count}: {requirement.title} (组织: {special_org.name}, 创建时间: {created_at})")
            except Exception as e:
                print(f"创建特殊需求时出错: {e}")
                continue
    
    # 生成剩余需求
    remaining = count - created_count
    i = 0
    while created_count < count:
        template = requirement_templates[i % len(requirement_templates)]
        i += 1
        
        try:
            # 随机选择发布人（从所有admin/owner用户中选择）
            publish_person = random.choice(org_users)
            org = publish_person.organization
            
            # 生成创建时间（过去1-180天内的随机时间）
            days_ago = random.randint(1, 180)
            created_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(0,23), minutes=random.randint(0,59))
            
            # 解析finish_time字符串（假设格式为'X个月'）
            if '个月' in template['finish_time']:
                months = int(template['finish_time'].replace('个月', ''))
                finish_time = (created_at + timedelta(days=months * 30)).date()  # 近似计算
            else:
                finish_time = None
            
            # 创建需求
            requirement = Requirement.objects.create(
                title=template['title'],
                brief=template['brief'],
                description=template['description'],
                status=random.choice(status_options),
                organization=org,
                publish_people=publish_person,
                finish_time=finish_time,
                budget=template['budget'],
                people_count=template['people_count'],
                applications=random.randint(0, 50),
                joined_count=random.randint(0, 10),
                views=random.randint(10, 1000)
            )
            # 设置自定义创建时间（绕过auto_now_add）
            Requirement.objects.filter(id=requirement.id).update(created_at=created_at, updated_at=created_at)
            
            # 添加兴趣标签
            for keyword in template['tag1_keywords']:
                matching_tags = [tag for tag in tag1_list if keyword.lower() in tag.value.lower()]
                if matching_tags:
                    selected_tags = random.sample(matching_tags, min(2, len(matching_tags)))
                    for tag in selected_tags:
                        requirement.tag1.add(tag)
            
            # 添加能力标签
            for keyword in template['tag2_keywords']:
                matching_tags = [tag for tag in tag2_list if 
                               keyword.lower() in tag.category.lower() or 
                               keyword.lower() in tag.subcategory.lower() or 
                               (tag.specialty and keyword.lower() in tag.specialty.lower())]
                if matching_tags:
                    selected_tags = random.sample(matching_tags, min(3, len(matching_tags)))
                    for tag in selected_tags:
                        requirement.tag2.add(tag)
            
            created_count += 1
            print(f"创建需求 {created_count}: {requirement.title} (组织: {org.name})")
            
        except Exception as e:
            print(f"创建需求时出错: {e}")
            continue
    
    print(f"\n=== 需求数据生成完成 ===")
    print(f"成功创建需求数量: {created_count}")
    print(f"数据库中需求总数: {Requirement.objects.count()}")
    
    # 显示各状态的需求数量
    print("\n=== 各状态需求统计 ===")
    for status, status_name in Requirement.STATUS_CHOICES:
        count = Requirement.objects.filter(status=status).count()
        print(f"{status_name}: {count}个")
    
    # 显示各领域的需求数量
    print("\n=== 各领域需求统计 ===")
    for field, field_name in Requirement.FIELD_CHOICES:
        count = Requirement.objects.filter(field=field).count()
        if count > 0:
            print(f"{field_name}: {count}个")

if __name__ == '__main__':
    generate_requirement_data(55)  # 生成55个需求