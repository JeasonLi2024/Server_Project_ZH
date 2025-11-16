#!/usr/bin/env python3
"""
从 pip freeze 输出生成 requirements.txt
过滤掉 conda 安装的包，只保留通过 pip 安装的项目依赖

使用方法:
1. python freeze_to_requirements.py
2. python freeze_to_requirements.py --output requirements.txt
3. python freeze_to_requirements.py --filter-conda
"""

import argparse
import subprocess
import sys
import re
from pathlib import Path
from typing import List, Set


def get_pip_freeze_output() -> List[str]:
    """获取 pip freeze 输出"""
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        print(f"❌ 获取 pip freeze 输出失败: {e}")
        return []


def get_conda_packages() -> Set[str]:
    """获取通过 conda 安装的包名"""
    conda_packages = set()
    try:
        result = subprocess.run(['conda', 'list', '--json'], 
                              capture_output=True, text=True, check=True)
        import json
        packages = json.loads(result.stdout)
        for pkg in packages:
            if pkg.get('channel') != 'pypi':
                conda_packages.add(pkg['name'].lower())
    except (subprocess.CalledProcessError, json.JSONDecodeError, ImportError):
        # 如果无法获取 conda 信息，使用常见的 conda 包列表
        conda_packages.update({
            'numpy', 'pandas', 'matplotlib', 'pillow', 'pyside6', 'shiboken6',
            'tornado', 'packaging', 'pyparsing', 'python-dateutil', 'six',
            'fonttools', 'kiwisolver', 'munkres', 'unicodedata2', 'tzdata',
            'mysql-connector-python'
        })
    
    return conda_packages


def filter_packages(freeze_lines: List[str], filter_conda: bool = True) -> List[str]:
    """过滤包列表"""
    filtered_packages = []
    conda_packages = get_conda_packages() if filter_conda else set()
    
    # 项目核心依赖（即使通过conda安装也要保留）
    core_dependencies = {
        'django', 'djangorestframework', 'djangorestframework-simplejwt',
        'django-cors-headers', 'mysqlclient', 'django-redis', 'redis',
        'celery', 'python-dotenv', 'argon2-cffi', 'pytz', 'pytest',
        'pytest-cov', 'bandit', 'colorama', 'requests', 'openpyxl', 'gunicorn'
    }
    
    for line in freeze_lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # 跳过本地安装的包（包含 @ file:// 的）
        if '@ file://' in line:
            # 但如果是核心依赖，提取包名和版本
            package_name = line.split('==')[0].split('@')[0].strip().lower()
            if package_name in core_dependencies:
                # 尝试从 pip list 获取版本
                try:
                    result = subprocess.run([sys.executable, '-m', 'pip', 'show', package_name], 
                                          capture_output=True, text=True, check=True)
                    for show_line in result.stdout.split('\n'):
                        if show_line.startswith('Version:'):
                            version = show_line.split(':', 1)[1].strip()
                            filtered_packages.append(f"{package_name}=={version}")
                            break
                except subprocess.CalledProcessError:
                    pass
            continue
        
        # 解析包名
        if '==' in line:
            package_name = line.split('==')[0].lower()
        elif '>=' in line:
            package_name = line.split('>=')[0].lower()
        elif '<=' in line:
            package_name = line.split('<=')[0].lower()
        else:
            package_name = line.lower()
        
        # 跳过系统包
        if package_name in ['pip', 'setuptools', 'wheel']:
            continue
        
        # 如果启用conda过滤且不是核心依赖，跳过conda包
        if filter_conda and package_name in conda_packages and package_name not in core_dependencies:
            continue
        
        filtered_packages.append(line)
    
    return sorted(filtered_packages)


def read_existing_requirements() -> List[str]:
    """读取现有的 requirements.in 文件以保留注释"""
    requirements_file = Path('requirements.in')
    if not requirements_file.exists():
        return []
    
    with open(requirements_file, 'r', encoding='utf-8') as f:
        return f.readlines()


def merge_with_existing(new_packages: List[str], existing_lines: List[str]) -> List[str]:
    """将新包与现有文件合并，保留注释结构"""
    if not existing_lines:
        return new_packages
    
    # 提取现有包名
    existing_packages = {}
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            package_name = stripped.split('==')[0].lower()
            existing_packages[package_name] = stripped
    
    # 创建新包的映射
    new_package_map = {}
    for pkg in new_packages:
        package_name = pkg.split('==')[0].lower()
        new_package_map[package_name] = pkg
    
    # 构建结果
    result_lines = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith('#') or not stripped:
            # 保留注释和空行
            result_lines.append(line.rstrip() + '\n')
        else:
            # 更新包版本
            package_name = stripped.split('==')[0].lower()
            if package_name in new_package_map:
                result_lines.append(new_package_map[package_name] + '\n')
                del new_package_map[package_name]  # 标记为已处理
            else:
                result_lines.append(line)
    
    # 添加新包
    if new_package_map:
        result_lines.append('\n# 新添加的依赖\n')
        for pkg in sorted(new_package_map.values()):
            result_lines.append(pkg + '\n')
    
    return result_lines


def main():
    parser = argparse.ArgumentParser(description='从 pip freeze 生成 requirements 文件')
    parser.add_argument('--output', '-o', default='requirements.txt', 
                       help='输出文件名 (默认: requirements.txt)')
    parser.add_argument('--filter-conda', action='store_true', default=True,
                       help='过滤 conda 安装的包 (默认: True)')
    parser.add_argument('--no-filter-conda', action='store_false', dest='filter_conda',
                       help='不过滤 conda 包')
    parser.add_argument('--merge', action='store_true',
                       help='与现有 requirements.in 合并')
    
    args = parser.parse_args()
    
    print("🔄 获取当前环境的包列表...")
    freeze_lines = get_pip_freeze_output()
    
    if not freeze_lines:
        print("❌ 无法获取包列表")
        return
    
    print(f"📦 找到 {len(freeze_lines)} 个包")
    
    # 过滤包
    filtered_packages = filter_packages(freeze_lines, args.filter_conda)
    print(f"✅ 过滤后剩余 {len(filtered_packages)} 个项目依赖")
    
    # 处理输出
    if args.merge and Path('requirements.in').exists():
        print("🔀 与现有 requirements.in 合并...")
        existing_lines = read_existing_requirements()
        output_lines = merge_with_existing(filtered_packages, existing_lines)
        output_content = ''.join(output_lines)
    else:
        output_content = '\n'.join(filtered_packages) + '\n'
    
    # 写入文件
    output_file = Path(args.output)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    print(f"✅ 依赖已写入 {output_file}")
    
    # 显示包列表
    print("\n📋 生成的依赖列表:")
    for pkg in filtered_packages:
        print(f"  - {pkg}")
    
    # 提示后续操作
    print("\n💡 后续操作建议:")
    print(f"   1. 检查 {output_file} 内容")
    print("   2. 运行 python sync_dependencies.py 同步到 environment.yml")
    print("   3. 测试环境: ./conda_setup.sh create")


if __name__ == '__main__':
    main()