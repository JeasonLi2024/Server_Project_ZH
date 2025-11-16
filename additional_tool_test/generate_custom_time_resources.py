#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成带有自定义创建时间的测试资源数据
规避auto_now_add和auto_now的影响
"""

import os
import sys
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import connection

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from project.models import Resource
from user.models import Tag1, Tag2, OrganizationUser

def generate_random_datetime(start_date, end_date):
    """生成指定日期范围内的随机时间"""
    time_between = end_date - start_date
    total_seconds = int(time_between.total_seconds())
    
    # 确保至少有1秒的时间差
    if total_seconds <= 0:
        return start_date
    
    # 生成随机秒数
    random_seconds = random.randrange(total_seconds)
    return start_date + timedelta(seconds=random_seconds)

def create_resources_with_custom_time():
    """创建带有自定义时间的资源"""
    
    # 获取现有数据
    tag1_list = list(Tag1.objects.all())
    tag2_list = list(Tag2.objects.all())
    org_users = list(OrganizationUser.objects.all())
    
    if not tag1_list or not tag2_list or not org_users:
        print("错误：缺少必要的基础数据（Tag1、Tag2或OrganizationUser）")
        return
    
    # 按类别分组Tag1（兴趣标签）
    tech_tag1 = [tag for tag in tag1_list if any(keyword in tag.value for keyword in ['技术', '互联网', '软件', '计算机', '信息'])]
    business_tag1 = [tag for tag in tag1_list if any(keyword in tag.value for keyword in ['商业', '管理', '金融', '经济', '市场'])]
    design_tag1 = [tag for tag in tag1_list if any(keyword in tag.value for keyword in ['设计', '创意', '艺术', '文化'])]
    other_tag1 = [tag for tag in tag1_list if tag not in tech_tag1 and tag not in business_tag1 and tag not in design_tag1]
    
    # 按行业分组Tag2（能力标签）
    internet_tag2 = [tag for tag in tag2_list if '互联网' in tag.category]
    tech_tag2 = [tag for tag in tag2_list if any(keyword in tag.category for keyword in ['电子', '通信', '科研', '技术'])]
    business_tag2 = [tag for tag in tag2_list if any(keyword in tag.category for keyword in ['金融', '市场', '管理', '财务'])]
    design_tag2 = [tag for tag in tag2_list if '设计' in tag.category]
    other_tag2 = [tag for tag in tag2_list if tag not in internet_tag2 and tag not in tech_tag2 and tag not in business_tag2 and tag not in design_tag2]
    
    print(f"标签分组统计:")
    print(f"Tag1 - 技术类: {len(tech_tag1)}, 商业类: {len(business_tag1)}, 设计类: {len(design_tag1)}, 其他: {len(other_tag1)}")
    print(f"Tag2 - 互联网: {len(internet_tag2)}, 技术类: {len(tech_tag2)}, 商业类: {len(business_tag2)}, 设计类: {len(design_tag2)}, 其他: {len(other_tag2)}")
    
    # 定义时间范围：2025年4月1日至今
    start_date = timezone.make_aware(datetime(2025, 4, 1))
    end_date = timezone.now()
    
    print(f"\n时间范围设置:")
    print(f"开始时间: {start_date}")
    print(f"结束时间: {end_date}")
    print(f"时间差: {(end_date - start_date).days} 天")
    print(f"总秒数: {int((end_date - start_date).total_seconds())} 秒")
    
    # 资源类型和模板
    resource_types = ['code', 'dataset', 'document', 'course', 'video', 'tool']
    
    resource_templates = {
        'code': [
            'Python机器学习算法实现',
            'React前端组件库',
            'Django REST API框架',
            'Vue.js数据可视化工具',
            'Node.js微服务架构',
            'Java Spring Boot项目',
            'Go语言并发编程示例',
            'C++高性能计算库',
            'JavaScript工具函数集',
            'TypeScript类型定义库'
        ],
        'dataset': [
            '电商用户行为数据集',
            '金融市场历史数据',
            '医疗影像标注数据',
            '自然语言处理语料库',
            '交通流量监测数据',
            '社交媒体情感分析数据',
            '图像识别训练集',
            '语音识别音频数据',
            '推荐系统评分数据',
            '时间序列预测数据'
        ],
        'document': [
            '深度学习技术白皮书',
            '云计算架构设计指南',
            '数据科学实践手册',
            '人工智能伦理报告',
            '区块链技术研究',
            '物联网安全规范',
            '大数据治理方案',
            '软件工程最佳实践',
            '用户体验设计指南',
            '项目管理方法论'
        ],
        'course': [
            'Python数据分析实战课程',
            '机器学习算法详解',
            '前端开发进阶教程',
            '数据库设计与优化',
            '云原生应用开发',
            '人工智能基础入门',
            '网络安全防护实践',
            '移动应用开发指南',
            'DevOps工程实践',
            '产品经理技能培训'
        ],
        'video': [
            'Docker容器化部署实战',
            'Kubernetes集群管理',
             'TensorFlow深度学习',
            'React Native移动开发',
            'Spring Cloud微服务',
            'Vue3.0新特性解析',
            'MySQL性能调优',
            'Redis缓存策略',
            'Nginx负载均衡配置',
            'Git版本控制进阶'
        ],
        'tool': [
            '代码质量检测工具',
            '自动化测试框架',
            '性能监控平台',
            '日志分析系统',
            'API文档生成器',
            '数据可视化工具',
            '项目管理平台',
            '持续集成工具',
            '安全扫描工具',
            '数据备份工具'
        ]
    }
    
    print("开始生成100个带有自定义时间的测试资源...")
    
    created_resources = []
    
    for i in range(100):
        # 随机选择资源类型
        resource_type = random.choice(resource_types)
        
        # 随机选择模板标题
        title_template = random.choice(resource_templates[resource_type])
        title = f"{title_template} v{i+200}"  # 避免与现有资源重复
        
        # 生成描述
        description = f"这是一个关于{title_template}的优质资源，包含详细的实现方案和最佳实践指导。适合相关领域的学习者和从业者使用。"
        
        # 随机选择创建者
        creator = random.choice(org_users)
        
        # 随机选择状态
        status = random.choices(['published', 'draft'], weights=[0.8, 0.2])[0]
        
        # 生成随机统计数据
        if status == 'published':
            downloads = random.randint(0, 1000)
            views = random.randint(downloads, downloads + 2000)
        else:
            downloads = 0
            views = random.randint(0, 50)
        
        # 生成自定义时间
        created_time = generate_random_datetime(start_date, end_date)
        updated_time = created_time + timedelta(hours=random.randint(0, 72))
        
        # 创建资源对象（不保存）
        resource = Resource(
            title=title,
            description=description,
            type=resource_type,
            status=status,
            create_person=creator,
            update_person=creator,
            downloads=downloads,
            views=views
        )
        
        # 保存资源
        resource.save()
        
        # 智能关联Tag1（兴趣标签）- 根据资源类型选择相关标签
        if resource_type in ['code', 'tool']:
            # 技术类资源优先选择技术标签
            available_tag1 = tech_tag1 + other_tag1 if tech_tag1 else tag1_list
        elif resource_type in ['document', 'course']:
            # 文档和课程类资源选择商业或技术标签
            available_tag1 = business_tag1 + tech_tag1 + other_tag1 if business_tag1 or tech_tag1 else tag1_list
        elif resource_type == 'video':
            # 视频资源选择设计或其他标签
            available_tag1 = design_tag1 + other_tag1 if design_tag1 else tag1_list
        else:
            available_tag1 = tag1_list
        
        tag1_count = random.randint(1, min(3, len(available_tag1)))
        selected_tag1 = random.sample(available_tag1, tag1_count) if available_tag1 else []
        if selected_tag1:
            resource.tag1.set(selected_tag1)
        
        # 智能关联Tag2（能力标签）- 根据资源类型选择相关标签
        if resource_type in ['code', 'tool']:
            # 技术类资源优先选择互联网和技术标签
            available_tag2 = internet_tag2 + tech_tag2 + other_tag2 if internet_tag2 or tech_tag2 else tag2_list
        elif resource_type in ['document', 'course']:
            # 文档和课程类资源选择商业或技术标签
            available_tag2 = business_tag2 + tech_tag2 + other_tag2 if business_tag2 or tech_tag2 else tag2_list
        elif resource_type == 'video':
            # 视频资源选择设计或其他标签
            available_tag2 = design_tag2 + other_tag2 if design_tag2 else tag2_list
        else:
            available_tag2 = tag2_list
        
        tag2_count = random.randint(1, min(4, len(available_tag2)))
        selected_tag2 = random.sample(available_tag2, tag2_count) if available_tag2 else []
        if selected_tag2:
            resource.tag2.set(selected_tag2)
        
        # 使用原生SQL更新时间戳，绕过auto_now限制
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE project_resource SET created_at = %s, updated_at = %s WHERE id = %s",
                [created_time, updated_time, resource.id]
            )
        
        # 重新加载资源对象以获取更新后的时间戳
        resource.refresh_from_db()
        
        created_resources.append(resource)
        
        if (i + 1) % 20 == 0:
            print(f"已生成 {i + 1} 个资源...")
    
    print(f"\n成功生成 {len(created_resources)} 个测试资源！")
    
    # 统计信息
    total_resources = Resource.objects.count()
    published_count = Resource.objects.filter(status='published').count()
    draft_count = Resource.objects.filter(status='draft').count()
    
    print(f"\n=== 数据库统计 ===")
    print(f"总资源数: {total_resources}")
    print(f"已发布: {published_count}")
    print(f"草稿: {draft_count}")
    
    # 按类型统计
    print(f"\n=== 按类型统计（新生成的100个） ===")
    type_counts = {}
    for resource in created_resources:
        type_counts[resource.type] = type_counts.get(resource.type, 0) + 1
    
    for resource_type, count in type_counts.items():
        print(f"{resource_type}: {count} 个")
    
    # 时间范围验证
    print(f"\n=== 时间范围验证 ===")
    earliest = min(r.created_at for r in created_resources)
    latest = max(r.created_at for r in created_resources)
    print(f"最早创建时间: {earliest}")
    print(f"最晚创建时间: {latest}")
    print(f"时间跨度: {(latest - earliest).days} 天")

if __name__ == '__main__':
    create_resources_with_custom_time()