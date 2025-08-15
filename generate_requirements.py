#!/usr/bin/env python3
"""
生成干净的 requirements.txt 文件
只包含项目的直接依赖，排除子依赖

使用方法:
1. python generate_requirements.py
2. python generate_requirements.py --include-sub-deps  # 包含所有依赖
3. python generate_requirements.py --from-freeze      # 从 pip freeze 生成
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Set, Dict


# 项目的直接依赖（顶级依赖）
DIRECT_DEPENDENCIES = {
    'Django',
    'djangorestframework', 
    'djangorestframework-simplejwt',
    'django-cors-headers',
    'mysqlclient',
    'django-redis',
    'redis',
    'celery',
    'python-dotenv',
    'argon2-cffi',
    'pytz',
    'Pillow',
    'pytest',
    'pytest-cov',
    'bandit',
    'colorama',
    'requests',
    'openpyxl',
    'pandas',
    'gunicorn'
}


def get_installed_packages() -> Dict[str, str]:
    """获取已安装包的版本信息"""
    packages = {}
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=freeze'], 
                              capture_output=True, text=True, check=True)
        for line in result.stdout.strip().split('\n'):
            if '==' in line and '@ file://' not in line:
                name, version = line.split('==', 1)
                packages[name.lower()] = f"{name}=={version}"
    except subprocess.CalledProcessError:
        print("❌ 无法获取已安装包列表")
    return packages


def get_package_dependencies(package_name: str) -> Set[str]:
    """获取包的直接依赖"""
    dependencies = set()
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'show', package_name], 
                              capture_output=True, text=True, check=True)
        for line in result.stdout.split('\n'):
            if line.startswith('Requires:'):
                deps = line.split(':', 1)[1].strip()
                if deps and deps != 'None':
                    for dep in deps.split(', '):
                        dependencies.add(dep.strip().lower())
                break
    except subprocess.CalledProcessError:
        pass
    return dependencies


def generate_direct_requirements() -> List[str]:
    """生成只包含直接依赖的requirements"""
    installed_packages = get_installed_packages()
    requirements = []
    
    print("🔍 检查直接依赖...")
    for dep in sorted(DIRECT_DEPENDENCIES):
        dep_lower = dep.lower()
        if dep_lower in installed_packages:
            requirements.append(installed_packages[dep_lower])
            print(f"  ✅ {installed_packages[dep_lower]}")
        else:
            print(f"  ❌ {dep} 未安装")
    
    return requirements


def generate_from_freeze(include_sub_deps: bool = False) -> List[str]:
    """从 pip freeze 生成requirements"""
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], 
                              capture_output=True, text=True, check=True)
        freeze_lines = result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        print("❌ 无法执行 pip freeze")
        return []
    
    if include_sub_deps:
        # 包含所有依赖，但过滤掉一些不需要的
        filtered = []
        skip_packages = {'pip', 'setuptools', 'wheel'}
        
        for line in freeze_lines:
            if '@ file://' in line:
                continue
            if '==' in line:
                package_name = line.split('==')[0].lower()
                if package_name not in skip_packages:
                    filtered.append(line)
        return sorted(filtered)
    else:
        # 只包含直接依赖
        installed_packages = {}
        for line in freeze_lines:
            if '==' in line and '@ file://' not in line:
                name, version = line.split('==', 1)
                installed_packages[name.lower()] = f"{name}=={version}"
        
        requirements = []
        for dep in sorted(DIRECT_DEPENDENCIES):
            dep_lower = dep.lower()
            if dep_lower in installed_packages:
                requirements.append(installed_packages[dep_lower])
        
        return requirements


def write_requirements_file(requirements: List[str], filename: str = 'requirements.txt'):
    """写入requirements文件"""
    output_file = Path(filename)
    
    content = []
    content.append("# Django项目依赖文件")
    content.append(f"# 生成时间: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}")
    content.append("# 使用方法: pip install -r requirements.txt")
    content.append("")
    
    # 按类别组织依赖
    web_frameworks = []
    databases = []
    async_tools = []
    dev_tools = []
    others = []
    
    for req in requirements:
        package_name = req.split('==')[0].lower()
        if package_name in ['django', 'djangorestframework', 'djangorestframework-simplejwt', 'django-cors-headers']:
            web_frameworks.append(req)
        elif package_name in ['mysqlclient', 'django-redis', 'redis']:
            databases.append(req)
        elif package_name in ['celery']:
            async_tools.append(req)
        elif package_name in ['pytest', 'pytest-cov', 'bandit']:
            dev_tools.append(req)
        else:
            others.append(req)
    
    if web_frameworks:
        content.append("# Web框架")
        content.extend(web_frameworks)
        content.append("")
    
    if databases:
        content.append("# 数据库和缓存")
        content.extend(databases)
        content.append("")
    
    if async_tools:
        content.append("# 异步任务")
        content.extend(async_tools)
        content.append("")
    
    if others:
        content.append("# 其他依赖")
        content.extend(others)
        content.append("")
    
    if dev_tools:
        content.append("# 开发工具")
        content.extend(dev_tools)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))
    
    print(f"✅ Requirements已写入 {output_file}")


def main():
    parser = argparse.ArgumentParser(description='生成项目requirements文件')
    parser.add_argument('--from-freeze', action='store_true',
                       help='从 pip freeze 输出生成')
    parser.add_argument('--include-sub-deps', action='store_true',
                       help='包含子依赖（仅在 --from-freeze 时有效）')
    parser.add_argument('--output', '-o', default='requirements.txt',
                       help='输出文件名')
    
    args = parser.parse_args()
    
    if args.from_freeze:
        print("📦 从 pip freeze 生成requirements...")
        requirements = generate_from_freeze(args.include_sub_deps)
        if args.include_sub_deps:
            print(f"✅ 包含所有依赖，共 {len(requirements)} 个包")
        else:
            print(f"✅ 只包含直接依赖，共 {len(requirements)} 个包")
    else:
        print("📋 生成直接依赖requirements...")
        requirements = generate_direct_requirements()
        print(f"✅ 共 {len(requirements)} 个直接依赖")
    
    if requirements:
        write_requirements_file(requirements, args.output)
        
        print("\n📋 生成的依赖:")
        for req in requirements:
            print(f"  - {req}")
        
        print("\n💡 使用建议:")
        print(f"   pip install -r {args.output}")
        print("   python sync_dependencies.py  # 同步到 environment.yml")
    else:
        print("❌ 没有找到任何依赖")


if __name__ == '__main__':
    main()