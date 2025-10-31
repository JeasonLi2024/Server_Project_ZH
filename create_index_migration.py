#!/usr/bin/env python
"""
创建数据库迁移脚本，用于应用索引优化
"""

import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from django.core.management import execute_from_command_line

def create_migrations():
    """为所有修改的应用创建迁移文件"""
    
    apps_to_migrate = [
        'read_search',
        'user', 
        'studentproject',
        'project',
        'notification',
        'projectscore',
        'organization',
        'audit',
        'authentication'
    ]
    
    print("正在为索引优化创建迁移文件...")
    
    for app in apps_to_migrate:
        print(f"\n创建 {app} 应用的迁移文件...")
        try:
            execute_from_command_line(['manage.py', 'makemigrations', app])
            print(f"✓ {app} 迁移文件创建成功")
        except Exception as e:
            print(f"✗ {app} 迁移文件创建失败: {e}")
    
    print("\n所有迁移文件创建完成！")
    print("\n下一步操作:")
    print("1. 检查生成的迁移文件")
    print("2. 运行 python manage.py migrate 应用迁移")
    print("3. 使用 analyze_indexes.py 验证优化效果")

if __name__ == '__main__':
    create_migrations()