#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查看Tag1和Tag2数据的脚本
"""

import os
import sys
import django
from collections import defaultdict

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from user.models import Tag1, Tag2, Tag1StuMatch, Tag2StuMatch

def view_tag1_data():
    """查看兴趣标签数据"""
    print("=== 兴趣标签(Tag1)数据统计 ===")
    total_count = Tag1.objects.count()
    print(f"总数量: {total_count} 个")
    
    # 按领域分类统计
    tech_keywords = ['开发', '学习', '算法', '数据', '系统', '网络', '安全', '计算', '模型']
    design_keywords = ['设计', 'UI', 'UX']
    business_keywords = ['营销', '管理', '分析', '创业', '投资', '财务']
    media_keywords = ['媒体', '视频', '音频', '摄影', '创作', '文案', '直播']
    education_keywords = ['教育', '培训', '学习', '研究', '知识']
    health_keywords = ['医疗', '健康', '心理', '运动', '营养']
    environment_keywords = ['环境', '能源', '绿色', '可持续']
    culture_keywords = ['文化', '艺术', '音乐', '文学', '戏剧', '美术']
    lifestyle_keywords = ['生活', '旅游', '美食', '时尚', '健身', '宠物', '园艺']
    
    categories = {
        '技术领域': tech_keywords,
        '设计创意': design_keywords,
        '商业管理': business_keywords,
        '媒体传播': media_keywords,
        '教育培训': education_keywords,
        '健康医疗': health_keywords,
        '环境能源': environment_keywords,
        '文化艺术': culture_keywords,
        '生活方式': lifestyle_keywords
    }
    
    category_counts = defaultdict(int)
    uncategorized = []
    
    for tag in Tag1.objects.all():
        categorized = False
        for category, keywords in categories.items():
            if any(keyword in tag.value for keyword in keywords):
                category_counts[category] += 1
                categorized = True
                break
        if not categorized:
            uncategorized.append(tag.value)
    
    print("\n按领域分类统计:")
    for category, count in category_counts.items():
        print(f"  {category}: {count} 个")
    
    if uncategorized:
        print(f"  未分类: {len(uncategorized)} 个")
        print(f"    {', '.join(uncategorized[:5])}{'...' if len(uncategorized) > 5 else ''}")
    
    # 显示前10个标签
    print("\n前10个兴趣标签:")
    latest_tags = Tag1.objects.order_by('id')[:10]
    for i, tag in enumerate(latest_tags, 1):
        print(f"  {i}. {tag.value}")

def view_tag2_data():
    """查看能力标签数据"""
    print("\n=== 能力标签(Tag2)数据统计 ===")
    total_count = Tag2.objects.count()
    level1_count = Tag2.objects.filter(level=1).count()
    level2_count = Tag2.objects.filter(level=2).count()
    
    print(f"总数量: {total_count} 个")
    print(f"一级标签: {level1_count} 个")
    print(f"二级标签: {level2_count} 个")
    
    # 按行业分类统计
    print("\n按行业分类统计:")
    categories = Tag2.objects.values('category').distinct().order_by('category')
    for cat in categories:
        category = cat['category']
        level1_in_cat = Tag2.objects.filter(category=category, level=1).count()
        level2_in_cat = Tag2.objects.filter(category=category, level=2).count()
        print(f"  {category}: {level1_in_cat} 个一级标签, {level2_in_cat} 个二级标签")
        
        # 显示该行业下的技术分类
        subcategories = Tag2.objects.filter(category=category, level=1).values_list('subcategory', flat=True)
        print(f"    技术分类: {', '.join(subcategories)}")
    
    # 显示层次结构示例
    print("\n层次结构示例:")
    for level1_tag in Tag2.objects.filter(level=1)[:3]:
        print(f"  📁 {level1_tag.post}")
        children = Tag2.objects.filter(parent=level1_tag)[:3]
        for child in children:
            print(f"    └── {child.specialty}")
        if Tag2.objects.filter(parent=level1_tag).count() > 3:
            remaining = Tag2.objects.filter(parent=level1_tag).count() - 3
            print(f"    └── ... 还有 {remaining} 个子标签")

def view_tag_usage():
    """查看标签使用情况"""
    print("\n=== 标签使用情况统计 ===")
    
    # Tag1使用情况
    tag1_matches = Tag1StuMatch.objects.count()
    used_tag1_count = Tag1.objects.filter(tag1stumatch__isnull=False).distinct().count()
    unused_tag1_count = Tag1.objects.filter(tag1stumatch__isnull=True).count()
    
    print(f"兴趣标签使用情况:")
    print(f"  总关联数: {tag1_matches} 个")
    print(f"  已使用标签: {used_tag1_count} 个")
    print(f"  未使用标签: {unused_tag1_count} 个")
    
    # Tag2使用情况
    tag2_matches = Tag2StuMatch.objects.count()
    used_tag2_count = Tag2.objects.filter(tag2stumatch__isnull=False).distinct().count()
    unused_tag2_count = Tag2.objects.filter(tag2stumatch__isnull=True).count()
    
    print(f"\n能力标签使用情况:")
    print(f"  总关联数: {tag2_matches} 个")
    print(f"  已使用标签: {used_tag2_count} 个")
    print(f"  未使用标签: {unused_tag2_count} 个")
    
    # 最受欢迎的标签
    if tag1_matches > 0:
        popular_tag1 = Tag1.objects.annotate(
            usage_count=models.Count('tag1stumatch')
        ).filter(usage_count__gt=0).order_by('-usage_count')[:5]
        
        print(f"\n最受欢迎的兴趣标签:")
        for i, tag in enumerate(popular_tag1, 1):
            print(f"  {i}. {tag.value} ({tag.usage_count} 次使用)")
    
    if tag2_matches > 0:
        popular_tag2 = Tag2.objects.annotate(
            usage_count=models.Count('tag2stumatch')
        ).filter(usage_count__gt=0).order_by('-usage_count')[:5]
        
        print(f"\n最受欢迎的能力标签:")
        for i, tag in enumerate(popular_tag2, 1):
            print(f"  {i}. {tag.post} ({tag.usage_count} 次使用)")

def main():
    """主函数"""
    print("Tag数据统计报告")
    print("=" * 60)
    
    view_tag1_data()
    view_tag2_data()
    view_tag_usage()
    
    print("\n" + "=" * 60)
    print("报告生成完成！")

if __name__ == '__main__':
    # 需要导入models用于注解查询
    from django.db import models
    main()