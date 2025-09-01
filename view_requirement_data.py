#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from project.models import Requirement
from user.models import Tag1, Tag2
from collections import Counter

def view_requirement_data():
    """查看需求数据统计信息"""
    
    print("=== 需求数据统计 ===")
    total_reqs = Requirement.objects.count()
    print(f"需求总数: {total_reqs}")
    
    # 按状态统计
    print("\n=== 按状态统计 ===")
    status_counts = Counter()
    for req in Requirement.objects.all():
        status_counts[req.get_status_display()] += 1
    
    for status, count in status_counts.items():
        print(f"{status}: {count}个")
    
    # 按领域统计
    print("\n=== 按领域统计 ===")
    field_counts = Counter()
    for req in Requirement.objects.all():
        field_counts[req.get_field_display()] += 1
    
    for field, count in field_counts.items():
        print(f"{field}: {count}个")
    
    # 按组织统计
    print("\n=== 按组织统计 ===")
    org_counts = Counter()
    for req in Requirement.objects.all():
        org_counts[req.organization.name] += 1
    
    for org, count in org_counts.most_common(10):
        print(f"{org}: {count}个")
    
    # 预算统计
    print("\n=== 预算统计 ===")
    budgets = [float(req.budget) for req in Requirement.objects.all() if req.budget and str(req.budget).replace('.', '').isdigit()]
    if budgets:
        print(f"平均预算: {sum(budgets)/len(budgets):.2f}元")
        print(f"最高预算: {max(budgets):.2f}元")
        print(f"最低预算: {min(budgets):.2f}元")
    
    # 最新需求详情
    print("\n=== 最新需求详情 ===")
    latest_reqs = Requirement.objects.all().order_by('-id')[:5]
    
    for req in latest_reqs:
        print(f"\n需求ID: {req.id}")
        print(f"标题: {req.title}")
        print(f"描述: {req.description[:100]}..." if len(req.description) > 100 else f"描述: {req.description}")
        print(f"领域: {req.get_field_display()}")
        print(f"状态: {req.get_status_display()}")
        print(f"组织: {req.organization.name}")
        print(f"发布人: {req.publish_people.user.username}")
        print(f"创建时间: {req.created_at}")
        print(f"更新时间: {req.updated_at}")
        print(f"预算: {req.budget}元" if req.budget else "预算: 未设置")
        
        
        # 关联标签
        tag1_list = list(req.tag1.all())
        tag2_list = list(req.tag2.all())
        
        if tag1_list:
            print(f"兴趣标签: {', '.join([t.value for t in tag1_list])}")
        
        if tag2_list:
            tag2_strs = []
            for t in tag2_list:
                tag_str = t.category
                if t.subcategory:
                    tag_str += f"-{t.subcategory}"
                if t.specialty:
                    tag_str += f"-{t.specialty}"
                tag2_strs.append(tag_str)
            print(f"能力标签: {', '.join(tag2_strs)}")
        
        print("-" * 50)
    
    # 标签使用统计
    print("\n=== 标签使用统计 ===")
    
    # 兴趣标签使用统计
    tag1_usage = Counter()
    for req in Requirement.objects.all():
        for tag in req.tag1.all():
            tag1_usage[tag.value] += 1
    
    print("\n最常用的兴趣标签:")
    for tag, count in tag1_usage.most_common(10):
        print(f"{tag}: {count}次")
    
    # 能力标签使用统计
    tag2_usage = Counter()
    for req in Requirement.objects.all():
        for tag in req.tag2.all():
            tag_str = tag.category
            if tag.subcategory:
                tag_str += f"-{tag.subcategory}"
            if tag.specialty:
                tag_str += f"-{tag.specialty}"
            tag2_usage[tag_str] += 1
    
    print("\n最常用的能力标签:")
    for tag, count in tag2_usage.most_common(10):
        print(f"{tag}: {count}次")

if __name__ == '__main__':
    view_requirement_data()