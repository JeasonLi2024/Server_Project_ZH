#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成测试资源数据的脚本
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
from project.models import Resource
from user.models import Tag1, Tag2, OrganizationUser
from organization.models import Organization

def generate_resource_data(count=120):
    """
    生成测试资源数据
    """
    
    # 获取现有数据
    org_users = list(OrganizationUser.objects.filter(permission__in=['admin', 'owner', 'member']))
    tag1_list = list(Tag1.objects.all())
    tag2_list = list(Tag2.objects.all())
    
    print(f"可用组织用户数量: {len(org_users)}")
    print(f"可用兴趣标签数量: {len(tag1_list)}")
    print(f"可用能力标签数量: {len(tag2_list)}")
    print(f"计划生成资源数量: {count}")
    
    # 资源模板数据
    resource_templates = [
        # 代码类资源
        {
            'title': 'Python机器学习项目源码',
            'description': '基于scikit-learn和pandas的机器学习项目完整源码，包含数据预处理、模型训练、评估和可视化功能。适合初学者学习机器学习算法的实际应用。',
            'type': 'code',
            'tag1_keywords': ['机器学习', '数据科学', 'Python'],
            'tag2_keywords': ['Python', '机器学习', '数据分析']
        },
        {
            'title': 'React前端组件库',
            'description': '基于React和TypeScript开发的UI组件库，包含常用的按钮、表单、表格、弹窗等组件，支持主题定制和响应式设计。',
            'type': 'code',
            'tag1_keywords': ['前端开发', 'React', 'UI设计'],
            'tag2_keywords': ['JavaScript', 'React开发', '前端开发']
        },
        {
            'title': 'Spring Boot微服务架构',
            'description': '基于Spring Boot和Spring Cloud的微服务架构示例项目，包含用户服务、订单服务、网关服务等，展示了服务注册发现、配置中心、链路追踪等功能。',
            'type': 'code',
            'tag1_keywords': ['后端开发', '微服务', 'Java'],
            'tag2_keywords': ['java', '后端', '微服务开发']
        },
        {
            'title': 'Vue.js电商前端项目',
            'description': '基于Vue3和Element Plus的电商前端项目，包含商品展示、购物车、订单管理、用户中心等功能模块。',
            'type': 'code',
            'tag1_keywords': ['前端开发', '电子商务', 'Vue'],
            'tag2_keywords': ['JavaScript', 'Vue开发', '前端开发']
        },
        {
            'title': 'Go语言API服务',
            'description': '使用Go语言和Gin框架开发的RESTful API服务，包含JWT认证、数据库操作、日志记录、错误处理等功能。',
            'type': 'code',
            'tag1_keywords': ['后端开发', 'API开发', 'Go'],
            'tag2_keywords': ['Go', '后端开发', 'API开发']
        },
        
        # 数据集类资源
        {
            'title': '中文文本分类数据集',
            'description': '包含10万条中文新闻文本的分类数据集，涵盖科技、体育、娱乐、财经等多个类别，已完成数据清洗和标注。',
            'type': 'dataset',
            'tag1_keywords': ['自然语言处理', '文本分类', '中文数据'],
            'tag2_keywords': ['自然语言处理', '机器学习', '数据分析']
        },
        {
            'title': '图像识别训练数据集',
            'description': '包含5万张高质量图像的分类数据集，涵盖动物、植物、建筑、交通工具等20个类别，适用于计算机视觉模型训练。',
            'type': 'dataset',
            'tag1_keywords': ['计算机视觉', '图像识别', '深度学习'],
            'tag2_keywords': ['计算机视觉', '深度学习', '机器学习']
        },
        {
            'title': '电商用户行为数据集',
            'description': '真实电商平台的用户行为数据，包含用户浏览、点击、购买等行为记录，适用于推荐系统和用户画像分析。',
            'type': 'dataset',
            'tag1_keywords': ['推荐系统', '用户行为', '数据挖掘'],
            'tag2_keywords': ['数据分析', '推荐系统', '机器学习']
        },
        {
            'title': '股票价格历史数据',
            'description': '包含A股主要股票近10年的日K线数据，包括开盘价、收盘价、最高价、最低价、成交量等信息。',
            'type': 'dataset',
            'tag1_keywords': ['金融数据', '股票分析', '量化交易'],
            'tag2_keywords': ['FinTech', '投资分析', '数据分析']
        },
        
        # 文档类资源
        {
            'title': '深度学习入门教程',
            'description': '从零开始学习深度学习的完整教程，包含理论基础、实践案例和代码示例，适合初学者系统学习。',
            'type': 'document',
            'tag1_keywords': ['深度学习', '人工智能', '教程'],
            'tag2_keywords': ['深度学习', '机器学习', 'Python']
        },
        {
            'title': 'React开发最佳实践指南',
            'description': '总结React开发中的最佳实践，包含组件设计、状态管理、性能优化、测试策略等内容。',
            'type': 'document',
            'tag1_keywords': ['React', '前端开发', '最佳实践'],
            'tag2_keywords': ['JavaScript', 'React开发', '前端开发']
        },
        {
            'title': '微服务架构设计指南',
            'description': '详细介绍微服务架构的设计原则、技术选型、部署策略和运维管理，包含大量实际案例。',
            'type': 'document',
            'tag1_keywords': ['微服务', '系统架构', '后端开发'],
            'tag2_keywords': ['系统架构', '后端开发', '微服务开发']
        },
        {
            'title': 'UI设计规范文档',
            'description': '完整的UI设计规范文档，包含色彩搭配、字体选择、布局原则、组件设计等内容，适用于移动端和Web端。',
            'type': 'document',
            'tag1_keywords': ['UI设计', '设计规范', '用户体验'],
            'tag2_keywords': ['UI设计', 'UX设计', '界面设计']
        },
        
        # 课程类资源
        {
            'title': 'Python数据分析实战课程',
            'description': '通过实际项目学习Python数据分析，包含pandas、numpy、matplotlib等库的使用，以及数据清洗、可视化、统计分析等技能。',
            'type': 'course',
            'tag1_keywords': ['Python', '数据分析', '实战课程'],
            'tag2_keywords': ['Python', '数据分析', '机器学习']
        },
        {
            'title': 'Vue.js全栈开发课程',
            'description': '从前端到后端的Vue.js全栈开发课程，包含Vue3、Node.js、Express、MongoDB等技术栈的学习。',
            'type': 'course',
            'tag1_keywords': ['Vue', '全栈开发', '前端开发'],
            'tag2_keywords': ['JavaScript', 'Vue开发', 'Node.js开发']
        },
        {
            'title': '机器学习算法精讲',
            'description': '深入讲解机器学习核心算法，包含线性回归、决策树、随机森林、SVM、神经网络等算法的原理和实现。',
            'type': 'course',
            'tag1_keywords': ['机器学习', '算法', '人工智能'],
            'tag2_keywords': ['机器学习', '算法工程师', 'Python']
        },
        
        # 视频类资源
        {
            'title': 'Docker容器化部署实战',
            'description': '详细演示如何使用Docker进行应用容器化部署，包含Dockerfile编写、镜像构建、容器编排等内容。',
            'type': 'video',
            'tag1_keywords': ['Docker', '容器化', '运维'],
            'tag2_keywords': ['Docker容器', 'Linux运维', '运维']
        },
        {
            'title': 'Kubernetes集群管理教程',
            'description': '从零开始学习Kubernetes集群的搭建和管理，包含Pod、Service、Deployment等核心概念的讲解。',
            'type': 'video',
            'tag1_keywords': ['Kubernetes', '集群管理', '云原生'],
            'tag2_keywords': ['Kubernetes', '云原生开发', 'Linux运维']
        },
        {
            'title': 'Photoshop设计技巧分享',
            'description': '分享Photoshop在UI设计、平面设计中的实用技巧，包含图层管理、滤镜使用、色彩调整等内容。',
            'type': 'video',
            'tag1_keywords': ['Photoshop', '设计技巧', '平面设计'],
            'tag2_keywords': ['平面设计', 'UI设计', '视觉设计']
        },
        
        # 工具类资源
        {
            'title': '代码质量检测工具',
            'description': '基于静态代码分析的代码质量检测工具，支持多种编程语言，能够检测代码规范、潜在bug、安全漏洞等问题。',
            'type': 'tool',
            'tag1_keywords': ['代码质量', '静态分析', '开发工具'],
            'tag2_keywords': ['后端开发', '前端开发', '代码质量']
        },
        {
            'title': 'API文档生成器',
            'description': '自动生成API文档的工具，支持多种框架，能够根据代码注释自动生成美观的API文档，支持在线测试。',
            'type': 'tool',
            'tag1_keywords': ['API文档', '开发工具', '自动化'],
            'tag2_keywords': ['API开发', '后端开发', '文档工具']
        },
        {
            'title': '数据可视化工具包',
            'description': '基于D3.js开发的数据可视化工具包，提供丰富的图表类型和交互功能，支持大数据量的实时渲染。',
            'type': 'tool',
            'tag1_keywords': ['数据可视化', 'D3.js', '图表'],
            'tag2_keywords': ['数据分析', '前端开发', '可视化']
        }
    ]
    
    # 状态选项
    status_options = ['published', 'draft']
    status_weights = [0.8, 0.2]  # 80%发布，20%草稿
    
    created_count = 0
    
    for i in range(count):
        # 随机选择模板
        template = random.choice(resource_templates)
        
        try:
            # 随机选择创建者和更新者
            create_person = random.choice(org_users)
            update_person = random.choice([u for u in org_users if u.organization == create_person.organization])
            
            # 生成创建时间（过去1-365天内的随机时间）
            days_ago = random.randint(1, 365)
            created_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(0,23), minutes=random.randint(0,59))
            
            # 生成更新时间（创建时间之后）
            update_days = random.randint(0, min(days_ago, 30))
            updated_at = created_at + timedelta(days=update_days, hours=random.randint(0,23), minutes=random.randint(0,59))
            
            # 添加序号使标题唯一
            title = f"{template['title']} v{i+1:03d}"
            
            # 随机选择状态
            status = random.choices(status_options, weights=status_weights)[0]
            
            # 生成下载数和浏览数
            if status == 'published':
                downloads = random.randint(0, 1000)
                views = random.randint(downloads, downloads + 2000)
            else:
                downloads = 0
                views = random.randint(0, 50)
            
            # 创建资源
            resource = Resource.objects.create(
                title=title,
                description=template['description'],
                type=template['type'],
                status=status,
                create_person=create_person,
                update_person=update_person,
                downloads=downloads,
                views=views,
                created_at=created_at,
                updated_at=updated_at
            )
            
            # 添加兴趣标签
            if template['tag1_keywords']:
                matching_tag1 = [tag for tag in tag1_list 
                                if any(keyword.lower() in tag.value.lower() 
                                      for keyword in template['tag1_keywords'])]
                if matching_tag1:
                    selected_tag1 = random.sample(matching_tag1, min(3, len(matching_tag1)))
                    for tag in selected_tag1:
                        resource.tag1.add(tag)
                else:
                    # 如果没有匹配的标签，随机选择一些
                    random_tag1 = random.sample(tag1_list, min(2, len(tag1_list)))
                    for tag in random_tag1:
                        resource.tag1.add(tag)
            
            # 添加能力标签
            if template['tag2_keywords']:
                matching_tag2 = [tag for tag in tag2_list 
                                if any(keyword.lower() in tag.category.lower() or 
                                      keyword.lower() in tag.subcategory.lower() or 
                                      (tag.specialty and keyword.lower() in tag.specialty.lower())
                                      for keyword in template['tag2_keywords'])]
                if matching_tag2:
                    selected_tag2 = random.sample(matching_tag2, min(3, len(matching_tag2)))
                    for tag in selected_tag2:
                        resource.tag2.add(tag)
                else:
                    # 如果没有匹配的标签，随机选择一些
                    random_tag2 = random.sample(tag2_list, min(2, len(tag2_list)))
                    for tag in random_tag2:
                        resource.tag2.add(tag)
            
            created_count += 1
            print(f"创建资源 {created_count}: {resource.title} (类型: {resource.type}, 状态: {resource.status}, 组织: {create_person.organization.name})")
            
        except Exception as e:
            print(f"创建资源时出错: {e}")
            continue
    
    print(f"\n资源生成完成！")
    print(f"成功创建: {created_count} 个资源")
    
    # 显示统计信息
    total_resources = Resource.objects.count()
    published_count = Resource.objects.filter(status='published').count()
    draft_count = Resource.objects.filter(status='draft').count()
    
    print(f"\n当前数据库中:")
    print(f"资源总数: {total_resources} 个")
    print(f"已发布: {published_count} 个")
    print(f"草稿: {draft_count} 个")
    
    # 按类型统计
    from django.db.models import Count
    type_stats = Resource.objects.values('type').annotate(count=Count('id'))
    print(f"\n按类型统计:")
    for stat in type_stats:
        print(f"  {stat['type']}: {stat['count']} 个")
    
    return created_count

def main():
    """主函数"""
    print("开始生成测试资源数据...\n")
    
    # 检查现有资源数量
    existing_count = Resource.objects.count()
    print(f"当前资源数量: {existing_count}")
    
    if existing_count > 0:
        response = input("数据库中已有资源数据，是否继续添加？(y/n): ")
        if response.lower() != 'y':
            print("操作已取消")
            return
    
    # 生成资源数据
    generate_resource_data(120)
    
    print("\n" + "="*50)
    print("测试资源数据生成完成！")

if __name__ == '__main__':
    main()