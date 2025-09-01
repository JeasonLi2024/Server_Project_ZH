#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import django

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from project.models import Requirement

def update_recruiting_status():
    """
    将数据库中状态为'recruiting'的需求记录更新为'in_progress'
    """
    try:
        # 查找所有状态为'recruiting'的需求
        recruiting_reqs = Requirement.objects.filter(status='recruiting')
        count = recruiting_reqs.count()
        
        print(f"找到 {count} 个状态为'recruiting'的需求记录")
        
        if count > 0:
            print("\n准备更新的需求:")
            for req in recruiting_reqs:
                print(f"  ID:{req.id} - {req.title[:50]}... - 组织:{req.organization.name}")
            
            # 批量更新状态为'in_progress'
            updated_count = recruiting_reqs.update(status='in_progress')
            print(f"\n✅ 成功更新 {updated_count} 个需求的状态从'recruiting'改为'in_progress'")
            
            # 验证更新结果
            remaining_recruiting = Requirement.objects.filter(status='recruiting').count()
            new_in_progress = Requirement.objects.filter(status='in_progress').count()
            
            print(f"\n验证结果:")
            print(f"  剩余'recruiting'状态的需求: {remaining_recruiting}")
            print(f"  当前'in_progress'状态的需求: {new_in_progress}")
            
            if remaining_recruiting == 0:
                print("\n🎉 所有'recruiting'状态的需求已成功更新！")
                return True
            else:
                print("\n❌ 仍有需求状态为'recruiting'，请检查")
                return False
        else:
            print("\n没有找到状态为'recruiting'的需求记录")
            return True
            
    except Exception as e:
        print(f"更新过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = update_recruiting_status()
    if success:
        print("\n✅ 数据库状态更新完成，可以安全删除'recruiting'状态选项")
    else:
        print("\n❌ 数据库状态更新失败，请检查错误")