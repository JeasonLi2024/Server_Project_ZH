#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import django
from datetime import datetime, timedelta
import random

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from django.utils import timezone
from project.models import Requirement
from organization.models import Organization
from user.models import OrganizationUser, Tag1, Tag2

def generate_today_requirements():
    """
    生成今天创建的需求数据用于测试
    """
    print("=== 生成今天创建的需求数据 ===")
    
    try:
        # 获取测试组织
        org = Organization.objects.get(name="阿里巴巴测试分公司")
        print(f"目标组织: {org.name}")
        
        # 获取该组织的用户
        org_users = list(OrganizationUser.objects.filter(
            organization=org,
            permission__in=['admin', 'owner']
        ))
        
        if not org_users:
            print("该组织没有管理员用户，无法创建需求")
            return
        
        print(f"可用组织用户数量: {len(org_users)}")
        
        # 获取标签数据 - 优化选择策略
        # 优先选择已分类的Tag1标签
        tech_tag1 = list(Tag1.objects.filter(value__icontains='技术')[:5])
        business_tag1 = list(Tag1.objects.filter(value__icontains='商业')[:5])
        other_tag1 = list(Tag1.objects.exclude(value__icontains='技术').exclude(value__icontains='商业')[:10])
        tag1_list = tech_tag1 + business_tag1 + other_tag1
        
        # 优先选择有明确分类的Tag2标签
        internet_tag2 = list(Tag2.objects.filter(category='互联网')[:5])
        tech_tag2 = list(Tag2.objects.filter(category__icontains='技术')[:5])
        other_tag2 = list(Tag2.objects.exclude(category='互联网').exclude(category__icontains='技术')[:10])
        tag2_list = internet_tag2 + tech_tag2 + other_tag2
        
        print(f"可用标签数量 - Tag1: {len(tag1_list)}, Tag2: {len(tag2_list)}")
        
        # 需求模板
        requirement_templates = [
            {
                'title': '今日AI智能客服系统开发需求',
                'brief': '基于大语言模型的智能客服系统，支持多轮对话',
                'description': '我们需要开发一个基于大语言模型的智能客服系统，能够处理用户的多轮对话，支持知识库检索和问答。',
                'field': 'ai',
                'budget': '500000-1000000',
                'people_count': '5-8人',
                'finish_time': '6个月'
            },
            {
                'title': '今日移动端APP开发项目',
                'brief': '开发一款企业级移动应用',
                'description': '开发一款面向企业用户的移动应用，需要支持iOS和Android双平台，具备完整的用户管理和业务功能。',
                'field': 'mobile_dev',
                'budget': '300000-600000',
                'people_count': '3-5人',
                'finish_time': '4个月'
            },
            {
                'title': '今日数据分析平台建设',
                'brief': '构建企业级数据分析平台',
                'description': '构建一个企业级的数据分析平台，支持多数据源接入、实时数据处理和可视化展示。',
                'field': 'big_data',
                'budget': '800000-1200000',
                'people_count': '6-10人',
                'finish_time': '8个月'
            },
            {
                'title': '今日区块链应用开发',
                'brief': '开发基于区块链的应用系统',
                'description': '开发一个基于区块链技术的应用系统，需要具备智能合约、数字资产管理等功能。',
                'field': 'blockchain',
                'budget': '1000000-2000000',
                'people_count': '8-12人',
                'finish_time': '12个月'
            },
            {
                'title': '今日云计算平台搭建',
                'brief': '搭建企业级云计算平台',
                'description': '搭建一个企业级的云计算平台，支持弹性扩展、资源调度和服务管理。',
                'field': 'cloud_computing',
                'budget': '600000-1000000',
                'people_count': '5-8人',
                'finish_time': '6个月'
            }
        ]
        
        # 获取今天的不同时间点
        today = timezone.now().date()
        created_requirements = []
        
        # 生成5个今天创建的需求，分布在不同时间点
        for i, template in enumerate(requirement_templates):
            # 生成今天的随机时间（从早上8点到晚上8点）
            hour = random.randint(8, 20)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            
            created_at = timezone.make_aware(
                datetime.combine(today, datetime.min.time().replace(
                    hour=hour, minute=minute, second=second
                ))
            )
            
            # 随机选择发布人
            publish_person = random.choice(org_users)
            
            # 解析finish_time
            if '个月' in template['finish_time']:
                months = int(template['finish_time'].replace('个月', ''))
                finish_time = (created_at + timedelta(days=months * 30)).date()
            else:
                finish_time = None
            
            # 创建需求
            requirement = Requirement.objects.create(
                title=template['title'],
                brief=template['brief'],
                description=template['description'],
                status=random.choice(['under_review', 'in_progress']),
                organization=org,
                publish_people=publish_person,
                finish_time=finish_time,
                budget=template['budget'],
                people_count=template['people_count'],
                applications=random.randint(0, 20),
                joined_count=random.randint(0, 5),
                views=random.randint(10, 500)
            )
            
            # 设置自定义创建时间
            Requirement.objects.filter(id=requirement.id).update(
                created_at=created_at,
                updated_at=created_at
            )
            
            # 智能添加标签 - 根据需求类型选择相关标签
            if tag1_list:
                # 根据需求标题选择合适的兴趣标签
                if any(keyword in template['title'] for keyword in ['技术', '开发', '系统', '平台']):
                    available_tag1 = [tag for tag in tag1_list if '技术' in tag.value or '互联网' in tag.value] or tag1_list
                elif any(keyword in template['title'] for keyword in ['管理', '运营', '市场']):
                    available_tag1 = [tag for tag in tag1_list if '商业' in tag.value or '管理' in tag.value] or tag1_list
                else:
                    available_tag1 = tag1_list
                
                tag1_count = min(random.randint(1, 2), len(available_tag1))
                selected_tag1s = random.sample(available_tag1, tag1_count)
                requirement.tag1.set(selected_tag1s)  # 使用set方法更安全
            
            if tag2_list:
                # 根据需求类型选择合适的能力标签
                if any(keyword in template['title'] for keyword in ['技术', '开发', '系统', '平台']):
                    available_tag2 = [tag for tag in tag2_list if '互联网' in tag.category or '技术' in tag.category] or tag2_list
                elif any(keyword in template['title'] for keyword in ['管理', '运营', '市场']):
                    available_tag2 = [tag for tag in tag2_list if '管理' in tag.category or '市场' in tag.category] or tag2_list
                else:
                    available_tag2 = tag2_list
                
                tag2_count = min(random.randint(1, 3), len(available_tag2))
                selected_tag2s = random.sample(available_tag2, tag2_count)
                requirement.tag2.set(selected_tag2s)  # 使用set方法更安全
            
            created_requirements.append(requirement)
            print(f"创建需求 {i+1}: {requirement.title} (创建时间: {created_at})")
        
        print(f"\n✅ 成功创建 {len(created_requirements)} 个今天的需求")
        
        # 验证创建结果
        today_count = Requirement.objects.filter(
            organization=org,
            created_at__date=today
        ).count()
        print(f"该组织今天创建的需求总数: {today_count}")
        
        return created_requirements
        
    except Organization.DoesNotExist:
        print("未找到阿里巴巴测试分公司")
        return []
    except Exception as e:
        print(f"生成需求数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == '__main__':
    generate_today_requirements()