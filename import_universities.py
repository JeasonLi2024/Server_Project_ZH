#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
大学数据导入脚本
从大学.xlsx文件中导入大学信息到University模型
"""

import os
import sys
import django
import pandas as pd
from django.db import transaction

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from organization.models import University

def import_universities():
    """
    从Excel文件导入大学数据
    """
    try:
        # 读取Excel文件
        print("正在读取大学.xlsx文件...")
        df = pd.read_excel('大学.xlsx')
        
        print(f"文件包含 {len(df)} 所大学")
        print(f"列名: {df.columns.tolist()}")
        
        # 检查必要的列
        if '学校名称' not in df.columns:
            print("错误: Excel文件中缺少'学校名称'列")
            return False
        
        # 清理数据
        df = df.dropna(subset=['学校名称'])  # 删除学校名称为空的行
        df['学校名称'] = df['学校名称'].str.strip()  # 去除首尾空格
        df = df[df['学校名称'] != '']  # 删除空字符串
        
        print(f"清理后有效数据: {len(df)} 所大学")
        
        # 使用事务确保数据一致性
        with transaction.atomic():
            # 清空现有数据（可选，根据需要决定是否保留）
            existing_count = University.objects.count()
            if existing_count > 0:
                print(f"数据库中已存在 {existing_count} 所大学")
                choice = input("是否清空现有数据？(y/N): ").lower()
                if choice == 'y':
                    University.objects.all().delete()
                    print("已清空现有数据")
            
            # 批量创建大学记录
            universities_to_create = []
            created_count = 0
            skipped_count = 0
            
            for index, row in df.iterrows():
                school_name = row['学校名称']
                
                # 检查是否已存在
                if University.objects.filter(school=school_name).exists():
                    print(f"跳过已存在的大学: {school_name}")
                    skipped_count += 1
                    continue
                
                universities_to_create.append(
                    University(school=school_name)
                )
                created_count += 1
                
                # 每100条批量插入一次
                if len(universities_to_create) >= 100:
                    University.objects.bulk_create(universities_to_create)
                    print(f"已导入 {created_count} 所大学...")
                    universities_to_create = []
            
            # 插入剩余的记录
            if universities_to_create:
                University.objects.bulk_create(universities_to_create)
            
            print(f"\n导入完成!")
            print(f"成功导入: {created_count} 所大学")
            print(f"跳过重复: {skipped_count} 所大学")
            print(f"数据库中总计: {University.objects.count()} 所大学")
            
            # 显示前10所大学作为验证
            print("\n前10所大学:")
            for i, university in enumerate(University.objects.all()[:10], 1):
                print(f"{i}. {university.school}")
            
            return True
            
    except FileNotFoundError:
        print("错误: 找不到大学.xlsx文件")
        return False
    except Exception as e:
        print(f"导入过程中发生错误: {str(e)}")
        return False

if __name__ == '__main__':
    print("=== 大学数据导入脚本 ===")
    print("此脚本将从大学.xlsx文件导入大学信息到数据库")
    print()
    
    success = import_universities()
    
    if success:
        print("\n✅ 大学数据导入成功!")
    else:
        print("\n❌ 大学数据导入失败!")
        sys.exit(1)