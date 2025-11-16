#!/usr/bin/env python
"""
数据库索引分析脚本
分析当前Django项目中的索引使用情况，识别冗余和优化机会
"""

import os
import sys
import django
from collections import defaultdict, Counter

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from django.db import connection
from django.apps import apps

def analyze_model_indexes():
    """分析Django模型中定义的索引"""
    print("=" * 80)
    print("Django模型索引分析报告")
    print("=" * 80)
    
    index_stats = {
        'total_models': 0,
        'total_indexes': 0,
        'single_field_indexes': 0,
        'composite_indexes': 0,
        'unique_constraints': 0,
        'db_index_fields': 0
    }
    
    potential_issues = []
    
    for app_config in apps.get_app_configs():
        if app_config.name in ['django.contrib.admin', 'django.contrib.auth', 
                              'django.contrib.contenttypes', 'django.contrib.sessions']:
            continue
            
        print(f"\n应用: {app_config.name}")
        print("-" * 40)
        
        for model in app_config.get_models():
            index_stats['total_models'] += 1
            table_name = model._meta.db_table
            print(f"\n模型: {model.__name__} (表: {table_name})")
            
            # 分析字段级别的db_index
            db_index_fields = []
            for field in model._meta.fields:
                if getattr(field, 'db_index', False):
                    db_index_fields.append(field.name)
                    index_stats['db_index_fields'] += 1
            
            if db_index_fields:
                print(f"  字段索引 (db_index=True): {', '.join(db_index_fields)}")
            
            # 分析Meta中定义的索引
            if hasattr(model._meta, 'indexes'):
                for idx in model._meta.indexes:
                    index_stats['total_indexes'] += 1
                    fields = [f.name if hasattr(f, 'name') else str(f) for f in idx.fields]
                    
                    if len(fields) == 1:
                        index_stats['single_field_indexes'] += 1
                        index_type = "单字段索引"
                    else:
                        index_stats['composite_indexes'] += 1
                        index_type = "复合索引"
                    
                    print(f"  {index_type}: {', '.join(fields)} (名称: {getattr(idx, 'name', '未命名')})")
                    
                    # 检查潜在的冗余索引
                    if len(fields) == 1 and fields[0] in db_index_fields:
                        potential_issues.append({
                            'type': '冗余索引',
                            'model': model.__name__,
                            'issue': f"字段 '{fields[0]}' 同时有 db_index=True 和 Meta.indexes 定义"
                        })
            
            # 分析unique_together
            if hasattr(model._meta, 'unique_together') and model._meta.unique_together:
                for constraint in model._meta.unique_together:
                    index_stats['unique_constraints'] += 1
                    print(f"  唯一约束: {', '.join(constraint)}")
            
            # 分析外键字段（自动创建索引）
            fk_fields = []
            for field in model._meta.fields:
                if field.many_to_one:
                    fk_fields.append(field.name)
            
            if fk_fields:
                print(f"  外键字段 (自动索引): {', '.join(fk_fields)}")

    return index_stats, potential_issues

def analyze_database_indexes():
    """分析数据库中实际的索引"""
    print("\n" + "=" * 80)
    print("数据库实际索引分析")
    print("=" * 80)
    
    with connection.cursor() as cursor:
        # 获取所有表的索引信息
        cursor.execute("""
            SELECT 
                TABLE_NAME,
                INDEX_NAME,
                GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as COLUMNS,
                COUNT(*) as COLUMN_COUNT,
                NON_UNIQUE
            FROM information_schema.STATISTICS 
            WHERE TABLE_SCHEMA = DATABASE()
            GROUP BY TABLE_NAME, INDEX_NAME
            ORDER BY TABLE_NAME, INDEX_NAME
        """)
        
        results = cursor.fetchall()
        
        table_indexes = defaultdict(list)
        index_analysis = {
            'total_indexes': len(results),
            'unique_indexes': 0,
            'multi_column_indexes': 0,
            'single_column_indexes': 0
        }
        
        for row in results:
            table_name, index_name, columns, column_count, non_unique = row
            
            index_info = {
                'name': index_name,
                'columns': columns.split(',') if columns else [],
                'column_count': column_count,
                'is_unique': non_unique == 0
            }
            
            table_indexes[table_name].append(index_info)
            
            if index_info['is_unique']:
                index_analysis['unique_indexes'] += 1
            
            if column_count > 1:
                index_analysis['multi_column_indexes'] += 1
            else:
                index_analysis['single_column_indexes'] += 1
        
        # 显示每个表的索引
        for table_name, indexes in table_indexes.items():
            print(f"\n表: {table_name}")
            print("-" * 40)
            for idx in indexes:
                unique_str = " (唯一)" if idx['is_unique'] else ""
                print(f"  {idx['name']}: {', '.join(idx['columns'])}{unique_str}")
        
        return index_analysis, table_indexes

def find_redundant_indexes(table_indexes):
    """查找冗余索引"""
    print("\n" + "=" * 80)
    print("冗余索引分析")
    print("=" * 80)
    
    redundant_indexes = []
    
    for table_name, indexes in table_indexes.items():
        # 按列数排序，短的在前
        sorted_indexes = sorted(indexes, key=lambda x: x['column_count'])
        
        for i, idx1 in enumerate(sorted_indexes):
            for idx2 in sorted_indexes[i+1:]:
                # 检查是否idx1是idx2的前缀
                if (len(idx1['columns']) < len(idx2['columns']) and 
                    idx2['columns'][:len(idx1['columns'])] == idx1['columns']):
                    
                    redundant_indexes.append({
                        'table': table_name,
                        'redundant_index': idx1['name'],
                        'redundant_columns': idx1['columns'],
                        'covered_by': idx2['name'],
                        'covering_columns': idx2['columns']
                    })
    
    if redundant_indexes:
        print("发现以下可能的冗余索引:")
        for redundant in redundant_indexes:
            print(f"\n表: {redundant['table']}")
            print(f"  冗余索引: {redundant['redundant_index']} ({', '.join(redundant['redundant_columns'])})")
            print(f"  被覆盖于: {redundant['covered_by']} ({', '.join(redundant['covering_columns'])})")
    else:
        print("未发现明显的冗余索引")
    
    return redundant_indexes

def generate_optimization_recommendations(index_stats, potential_issues, redundant_indexes):
    """生成优化建议"""
    print("\n" + "=" * 80)
    print("索引优化建议")
    print("=" * 80)
    
    recommendations = []
    
    # 基于统计信息的建议
    if index_stats['single_field_indexes'] > index_stats['composite_indexes'] * 2:
        recommendations.append({
            'priority': 'medium',
            'type': '索引策略',
            'description': f"单字段索引过多 ({index_stats['single_field_indexes']})，考虑合并为复合索引以优化查询性能"
        })
    
    # 基于潜在问题的建议
    for issue in potential_issues:
        recommendations.append({
            'priority': 'high',
            'type': issue['type'],
            'description': f"{issue['model']}: {issue['issue']}"
        })
    
    # 基于冗余索引的建议
    for redundant in redundant_indexes:
        recommendations.append({
            'priority': 'high',
            'type': '冗余索引',
            'description': f"表 {redundant['table']} 中的索引 {redundant['redundant_index']} 可以删除，已被 {redundant['covered_by']} 覆盖"
        })
    
    # 按优先级分组显示建议
    high_priority = [r for r in recommendations if r['priority'] == 'high']
    medium_priority = [r for r in recommendations if r['priority'] == 'medium']
    
    if high_priority:
        print("\n高优先级建议:")
        for i, rec in enumerate(high_priority, 1):
            print(f"{i}. [{rec['type']}] {rec['description']}")
    
    if medium_priority:
        print("\n中优先级建议:")
        for i, rec in enumerate(medium_priority, 1):
            print(f"{i}. [{rec['type']}] {rec['description']}")
    
    if not recommendations:
        print("当前索引配置良好，暂无明显优化建议")
    
    return recommendations

def main():
    """主函数"""
    try:
        # 分析Django模型索引
        model_stats, potential_issues = analyze_model_indexes()
        
        # 分析数据库实际索引
        db_stats, table_indexes = analyze_database_indexes()
        
        # 查找冗余索引
        redundant_indexes = find_redundant_indexes(table_indexes)
        
        # 生成优化建议
        recommendations = generate_optimization_recommendations(
            model_stats, potential_issues, redundant_indexes
        )
        
        # 输出总结
        print("\n" + "=" * 80)
        print("分析总结")
        print("=" * 80)
        print(f"Django模型数量: {model_stats['total_models']}")
        print(f"定义的索引总数: {model_stats['total_indexes']}")
        print(f"数据库实际索引数: {db_stats['total_indexes']}")
        print(f"发现的潜在问题: {len(potential_issues)}")
        print(f"发现的冗余索引: {len(redundant_indexes)}")
        print(f"优化建议数量: {len(recommendations)}")
        
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()