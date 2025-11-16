# 虚拟环境配置指南

## 当前环境状态

✅ **项目已配置虚拟环境并正常运行**

- **虚拟环境名称**: TraeAI-5
- **Python版本**: Python 3.13.2
- **状态**: 所有依赖已安装，环境健康

## 项目依赖

### 核心框架
- Django 5.1.7 - Web框架
- djangorestframework 3.15.2 - REST API框架
- djangorestframework-simplejwt 5.5.0 - JWT认证

### 数据库相关
- PyMySQL 1.1.1 - MySQL数据库连接器
- mysqlclient 2.2.7 - MySQL客户端
- django-redis 5.4.0 - Redis缓存支持
- redis 5.2.1 - Redis客户端

### 其他工具
- django-cors-headers 4.7.0 - CORS支持
- argon2-cffi 23.1.0 - 密码哈希
- python-dotenv 1.0.1 - 环境变量管理
- celery 5.5.1 - 异步任务队列

## 虚拟环境管理

### 使用提供的管理脚本

```powershell
# 检查当前环境状态
.\venv_setup.ps1 check

# 创建新的虚拟环境（如需要）
.\venv_setup.ps1 create

# 激活虚拟环境
.\venv_setup.ps1 activate

# 安装依赖
.\venv_setup.ps1 install

# 导出当前包列表
.\venv_setup.ps1 freeze

# 显示帮助
.\venv_setup.ps1 help
```

### 手动管理虚拟环境

#### 创建新的虚拟环境
```powershell
# 创建虚拟环境
python -m venv zhihui_venv

# 激活虚拟环境
.\zhihui_venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

#### 激活现有虚拟环境
```powershell
# 如果虚拟环境在项目目录下
.\zhihui_venv\Scripts\Activate.ps1

# 或者使用conda（如果使用conda）
conda activate your_env_name
```

#### 退出虚拟环境
```powershell
deactivate
```

## 环境验证

### 检查虚拟环境状态
```powershell
# 检查是否在虚拟环境中
echo $env:VIRTUAL_ENV

# 检查Python版本
python --version

# 检查已安装的包
pip list

# 检查依赖完整性
pip check
```

### 运行项目
```powershell
# 启动Django开发服务器
python manage.py runserver

# 运行数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser
```

## 常见问题解决

### 1. 虚拟环境激活失败
```powershell
# 设置执行策略（管理员权限）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. 包安装失败
```powershell
# 更新pip
python -m pip install --upgrade pip

# 清理缓存重新安装
pip cache purge
pip install -r requirements.txt --no-cache-dir
```

### 3. MySQL连接问题
- 确保MySQL服务正在运行
- 检查数据库配置文件
- 验证数据库用户权限

### 4. Redis连接问题
- 确保Redis服务正在运行
- 检查Redis配置
- 验证连接参数

## 最佳实践

1. **始终在虚拟环境中开发**
2. **定期更新依赖包**
3. **保持requirements.txt最新**
4. **使用.env文件管理环境变量**
5. **定期备份虚拟环境配置**

## 环境变量配置

创建 `.env` 文件（基于 `.env.example`）：
```bash
# 数据库配置
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=3306

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Django配置
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

## 部署注意事项

1. **生产环境使用固定版本的依赖**
2. **设置DEBUG=False**
3. **配置正确的ALLOWED_HOSTS**
4. **使用环境变量管理敏感信息**
5. **配置静态文件服务**