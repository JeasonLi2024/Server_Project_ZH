#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成Tag1和Tag2数据的脚本
"""

import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from user.models import Tag1, Tag2

def generate_tag1_data():
    """生成兴趣标签数据"""
    tag1_data = [
        # 技术领域
        '机器学习', '深度学习', '自然语言处理', '计算机视觉', '数据挖掘',
        '区块链', '物联网', '云计算', '边缘计算', '量子计算',
        '前端开发', '后端开发', '移动开发', '游戏开发', '嵌入式开发',
        '数据科学', '算法优化', '系统架构', '网络安全', '信息安全',
        
        # 设计领域
        'UI设计', 'UX设计', '平面设计', '产品设计', '交互设计',
        '视觉设计', '品牌设计', '包装设计', '网页设计', '动画设计',
        
        # 商业领域
        '市场营销', '数字营销', '内容营销', '社交媒体', '电子商务',
        '项目管理', '产品管理', '运营管理', '供应链管理', '人力资源',
        '财务分析', '投资理财', '创业创新', '商业分析', '战略规划',
        
        # 媒体传播
        '新媒体运营', '短视频制作', '直播运营', '内容创作', '文案策划',
        '摄影摄像', '视频剪辑', '音频制作', '播客制作', '广告创意',
        
        # 教育培训
        '在线教育', '职业培训', '技能培训', '语言学习', '学术研究',
        '知识管理', '课程设计', '教学方法', '学习心理学', '教育技术',
        
        # 健康医疗
        '医疗健康', '生物医学', '药物研发', '医疗器械', '健康管理',
        '心理健康', '营养学', '运动科学', '康复医学', '公共卫生',
        
        # 环境能源
        '可再生能源', '环境保护', '绿色技术', '节能减排', '循环经济',
        '智慧城市', '可持续发展', '环境监测', '新能源汽车', '储能技术',
        
        # 文化艺术
        '数字艺术', '传统文化', '文化创意', '艺术创作', '音乐制作',
        '文学创作', '戏剧表演', '舞蹈编排', '美术绘画', '手工艺品',
        
        # 生活方式
        '智能家居', '生活美学', '旅游规划', '美食烹饪', '时尚搭配',
        '健身运动', '户外探险', '摄影旅行', '宠物护理', '园艺种植'
    ]
    
    created_count = 0
    for value in tag1_data:
        tag1, created = Tag1.objects.get_or_create(value=value)
        if created:
            created_count += 1
            print(f"创建兴趣标签: {value}")
    
    print(f"\n共创建了 {created_count} 个新的兴趣标签")
    return created_count

def generate_tag2_data():
    """生成能力标签数据"""
    # 定义层次化的能力标签数据
    tag2_data = [
        # 互联网技术
        {
            'category': '互联网',
            'subcategory': 'Python',
            'specialties': ['后端开发', '数据分析', '机器学习', '爬虫开发', '自动化测试']
        },
        {
            'category': '互联网',
            'subcategory': 'JavaScript',
            'specialties': ['前端开发', 'Node.js开发', 'React开发', 'Vue开发', '小程序开发']
        },
        {
            'category': '互联网',
            'subcategory': 'Go',
            'specialties': ['后端开发', '微服务开发', '云原生开发', '区块链开发']
        },
        {
            'category': '互联网',
            'subcategory': 'C++',
            'specialties': ['系统开发', '游戏开发', '嵌入式开发', '算法优化']
        },
        {
            'category': '互联网',
            'subcategory': '数据库',
            'specialties': ['MySQL管理', 'Redis管理', 'MongoDB管理', '数据建模']
        },
        {
            'category': '互联网',
            'subcategory': '运维',
            'specialties': ['Linux运维', 'Docker容器', 'Kubernetes', '监控运维']
        },
        
        # 人工智能
        {
            'category': '人工智能',
            'subcategory': '机器学习',
            'specialties': ['算法工程师', '数据科学家', 'MLOps工程师', '模型优化']
        },
        {
            'category': '人工智能',
            'subcategory': '深度学习',
            'specialties': ['计算机视觉', '自然语言处理', '语音识别', '推荐系统']
        },
        {
            'category': '人工智能',
            'subcategory': '大模型',
            'specialties': ['LLM开发', '模型训练', '模型部署', 'Prompt工程']
        },
        
        # 设计创意
        {
            'category': '设计',
            'subcategory': 'UI设计',
            'specialties': ['移动端设计', 'Web设计', '图标设计', '界面设计']
        },
        {
            'category': '设计',
            'subcategory': 'UX设计',
            'specialties': ['用户研究', '交互设计', '原型设计', '可用性测试']
        },
        {
            'category': '设计',
            'subcategory': '平面设计',
            'specialties': ['品牌设计', '海报设计', '包装设计', '印刷设计']
        },
        {
            'category': '设计',
            'subcategory': '3D设计',
            'specialties': ['建模设计', '动画制作', '渲染技术', '游戏美术']
        },
        
        # 数字营销
        {
            'category': '营销',
            'subcategory': '数字营销',
            'specialties': ['SEM推广', 'SEO优化', '信息流广告', '社交媒体营销']
        },
        {
            'category': '营销',
            'subcategory': '内容营销',
            'specialties': ['文案策划', '短视频制作', '直播运营', '社群运营']
        },
        {
            'category': '营销',
            'subcategory': '电商运营',
            'specialties': ['店铺运营', '商品运营', '活动策划', '数据分析']
        },
        
        # 传媒制作
        {
            'category': '传媒',
            'subcategory': '视频制作',
            'specialties': ['剪辑师', '调色师', '特效制作', '动画制作']
        },
        {
            'category': '传媒',
            'subcategory': '音频制作',
            'specialties': ['录音师', '混音师', '音效设计', '配音制作']
        },
        {
            'category': '传媒',
            'subcategory': '摄影摄像',
            'specialties': ['商业摄影', '婚礼摄影', '产品摄影', '纪录片拍摄']
        },
        
        # 金融科技
        {
            'category': '金融',
            'subcategory': 'FinTech',
            'specialties': ['量化交易', '风控建模', '支付系统', '区块链金融']
        },
        {
            'category': '金融',
            'subcategory': '投资分析',
            'specialties': ['股票分析', '基金分析', '债券分析', '衍生品交易']
        },
        
        # 教育培训
        {
            'category': '教育',
            'subcategory': '在线教育',
            'specialties': ['课程设计', '教学视频制作', '学习平台开发', '教育数据分析']
        },
        {
            'category': '教育',
            'subcategory': '职业培训',
            'specialties': ['技能培训', '认证考试', '企业培训', '职业规划']
        },
        
        # 医疗健康
        {
            'category': '医疗',
            'subcategory': '医疗信息化',
            'specialties': ['HIS系统', '医疗大数据', '远程医疗', '智能诊断']
        },
        {
            'category': '医疗',
            'subcategory': '生物技术',
            'specialties': ['基因检测', '药物研发', '医疗器械', '生物信息学']
        }
    ]
    
    created_count = 0
    
    for category_data in tag2_data:
        category = category_data['category']
        subcategory = category_data['subcategory']
        
        # 创建一级标签（category-subcategory）
        level1_post = f"{category}-{subcategory}"
        level1_tag, created = Tag2.objects.get_or_create(
            category=category,
            subcategory=subcategory,
            specialty=None,
            defaults={
                'post': level1_post,
                'level': 1,
                'parent': None
            }
        )
        if created:
            created_count += 1
            print(f"创建一级能力标签: {level1_post}")
        
        # 创建二级标签（category-subcategory-specialty）
        for specialty in category_data['specialties']:
            level2_post = f"{category}-{subcategory}-{specialty}"
            level2_tag, created = Tag2.objects.get_or_create(
                category=category,
                subcategory=subcategory,
                specialty=specialty,
                defaults={
                    'post': level2_post,
                    'level': 2,
                    'parent': level1_tag
                }
            )
            if created:
                created_count += 1
                print(f"创建二级能力标签: {level2_post}")
    
    print(f"\n共创建了 {created_count} 个新的能力标签")
    return created_count

def main():
    """主函数"""
    print("开始生成Tag数据...\n")
    
    # 生成Tag1数据
    print("=== 生成兴趣标签(Tag1)数据 ===")
    tag1_count = generate_tag1_data()
    
    print("\n" + "="*50 + "\n")
    
    # 生成Tag2数据
    print("=== 生成能力标签(Tag2)数据 ===")
    tag2_count = generate_tag2_data()
    
    print("\n" + "="*50)
    print(f"数据生成完成！")
    print(f"新增兴趣标签: {tag1_count} 个")
    print(f"新增能力标签: {tag2_count} 个")
    print(f"总计新增: {tag1_count + tag2_count} 个标签")
    
    # 显示当前数据统计
    total_tag1 = Tag1.objects.count()
    total_tag2 = Tag2.objects.count()
    print(f"\n当前数据库中:")
    print(f"兴趣标签总数: {total_tag1} 个")
    print(f"能力标签总数: {total_tag2} 个")

if __name__ == '__main__':
    main()