#!/bin/bash
# Conda环境设置脚本 - 适用于远程服务器部署

set -e  # 遇到错误立即退出

ENV_NAME="project_zhihui"
PYTHON_VERSION="3.11"

echo "=== Django项目Conda环境设置 ==="

# 检查conda是否安装
if ! command -v conda &> /dev/null; then
    echo "❌ Conda未安装，请先安装Miniconda或Anaconda"
    exit 1
fi

echo "✅ Conda已安装: $(conda --version)"

# 函数：创建conda环境
create_env() {
    echo "📦 创建conda环境: $ENV_NAME"
    
    # 检查环境是否已存在
    if conda env list | grep -q "^$ENV_NAME "; then
        echo "⚠️  环境 $ENV_NAME 已存在"
        read -p "是否删除并重新创建? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🗑️  删除现有环境..."
            conda env remove -n $ENV_NAME -y
        else
            echo "❌ 取消操作"
            exit 1
        fi
    fi
    
    # 使用environment.yml创建环境（如果存在）
    if [ -f "environment.yml" ]; then
        echo "📋 使用environment.yml创建环境..."
        conda env create -f environment.yml
    else
        echo "🐍 创建基础Python环境..."
        conda create -n $ENV_NAME python=$PYTHON_VERSION -y
        
        # 激活环境并安装依赖
        echo "🔄 激活环境并安装依赖..."
        source $(conda info --base)/etc/profile.d/conda.sh
        conda activate $ENV_NAME
        
        # 安装系统级依赖（通过conda）
        echo "📦 安装conda包..."
        conda install -c conda-forge mysql-connector-python redis-py pillow numpy pandas matplotlib -y
        
        # 安装Python依赖
        if [ -f "requirements.txt" ]; then
            echo "📋 安装requirements.txt中的依赖..."
            pip install -r requirements.txt
        elif [ -f "requirements.in" ]; then
            echo "📋 安装requirements.in中的依赖..."
            pip install -r requirements.in
        else
            echo "❌ 未找到依赖文件"
            exit 1
        fi
    fi
    
    echo "✅ 环境创建完成!"
}

# 函数：验证环境
verify_env() {
    echo "🔍 验证环境..."
    
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate $ENV_NAME
    
    echo "Python版本: $(python --version)"
    echo "Pip版本: $(pip --version)"
    
    # 检查关键依赖
    echo "🔍 检查关键依赖..."
    python -c "import django; print(f'Django: {django.get_version()}')" || echo "❌ Django导入失败"
    python -c "import rest_framework; print('✅ DRF导入成功')" || echo "❌ DRF导入失败"
    python -c "import MySQLdb; print('✅ MySQLdb导入成功')" || echo "⚠️  MySQLdb导入失败，尝试mysqlclient"
    python -c "import redis; print('✅ Redis导入成功')" || echo "❌ Redis导入失败"
    python -c "import celery; print('✅ Celery导入成功')" || echo "❌ Celery导入失败"
    
    # Django项目检查
    if [ -f "manage.py" ]; then
        echo "🔍 Django项目检查..."
        python manage.py check --deploy || echo "⚠️  Django检查发现问题"
    fi
    
    echo "✅ 环境验证完成!"
}

# 函数：显示使用说明
show_usage() {
    echo "📖 使用说明:"
    echo "  激活环境: conda activate $ENV_NAME"
    echo "  退出环境: conda deactivate"
    echo "  删除环境: conda env remove -n $ENV_NAME"
    echo "  查看环境: conda env list"
    echo ""
    echo "🚀 启动Django项目:"
    echo "  conda activate $ENV_NAME"
    echo "  python manage.py runserver 0.0.0.0:8000"
    echo ""
    echo "📝 环境管理:"
    echo "  导出环境: conda env export -n $ENV_NAME > environment.yml"
    echo "  更新依赖: pip install -r requirements.txt"
}

# 主要执行逻辑
case "${1:-create}" in
    "create")
        create_env
        verify_env
        show_usage
        ;;
    "verify")
        verify_env
        ;;
    "usage"|"help")
        show_usage
        ;;
    "clean")
        echo "🗑️  删除环境: $ENV_NAME"
        conda env remove -n $ENV_NAME -y
        echo "✅ 环境已删除"
        ;;
    *)
        echo "❌ 未知参数: $1"
        echo "可用参数: create, verify, usage, clean"
        exit 1
        ;;
esac

echo ""
echo "🎉 脚本执行完成!"