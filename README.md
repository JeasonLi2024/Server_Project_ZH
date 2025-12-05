# BUPT-智汇项目说明

## 项目简介
- 基于 Django 的”智汇“项目后端系统，提供 REST API、WebSocket 实时通知、异步与定时任务。
- 覆盖账号认证与授权、组织与用户管理、项目与成绩、审核与仪表盘、通知中心、PDF 处理与检索、CAS 登录集成、向量检索。

## 技术栈
- 后端框架：Django 5.x、Django REST framework、djangorestframework-simplejwt。
- 实时通信：Django Channels（ASGI，`daphne` 启动）。
- 任务队列：Celery + django-celery-beat（Redis 作为 broker 和 result）。
- 数据与缓存：MySQL、Redis、Milvus（向量检索）。
- 其他：Whitenoise（静态）、PyMuPDF/pandas/openpyxl（文档与表格）、pytest（测试）。

## 目录结构
```
Project_Zhihui/
  asgi.py
  wsgi.py
  settings.py
  celery.py
  test_settings.py
apps（部分）：
  authentication/
  user/
  organization/
  project/
  studentproject/
  projectscore/
  notification/
  dashboard/
  audit/
  cas_auth/
  process_pdf/
  read_search/
  tag_db_writer/
根目录：
  manage.py
  requirements.txt
  supervisord.conf
  supervisor_config.conf
  .env.example / .env
```

## 环境与依赖
- 运行环境：Python 3.10+；可用的 MySQL、Redis、Milvus 实例。
- 安装依赖：`pip install -r requirements.txt`
- 环境变量（示例）：
  - 数据库：`DB_NAME`、`DB_USER`、`DB_PASSWORD`、`DB_HOST`、`DB_PORT`
  - Redis：`REDIS_URL`
  - JWT/安全：`SECRET_KEY`、`SIMPLE_JWT_*`
  - 邮件：`EMAIL_HOST`、`EMAIL_HOST_USER`、`EMAIL_HOST_PASSWORD`
  - CAS：`BUPT_CAS_*`
  - Milvus：`MILVUS_HOST`、`MILVUS_PORT`
  - 嵌入/检索：`EMBEDDING_URL`、`EMBEDDING_MODEL`、`EMBEDDING_DIM`

## 快速开始（开发）
- 初始化配置：复制 `.env.example` 为 `.env` 并填充必需变量。
- 虚拟环境启动：`source /home/bupt/Server_Project_ZH/venv/bin/activate`
- 清除旧迁移数据文件：`find . -path "*/migrations/*.py" -not -name "__init__.py" -delete`
- 生成新迁移文件：`python manage.py makemigrations`，若出现`ModuleNotFoundError: No module named 'django.db.migrations.migration' `错误，强制重新安装Django：`pip install --force-reinstall django`
- 迁移数据库：`python manage.py migrate`
- 启动后端（简易）：`python manage.py runserver 0.0.0.0:8000`
- 启动 ASGI + WebSocket（推荐）：`daphne -b 0.0.0.0 -p 8000 Project_Zhihui.asgi:application`
- 启动任务：`celery -A Project_Zhihui worker -l info`
- 启动定时：`celery -A Project_Zhihui beat -l info`

## 配置说明
- Django Settings：数据库与缓存（`django-redis`）、Channels layer、JWT、静态与媒体、邮件配置。
- Channels：使用 `channels_redis.core.RedisChannelLayer` 提供 WebSocket 通道层。
- Celery：以 Redis 作为 broker/result；定时任务在 `Project_Zhihui/celery.py` 的 `beat_schedule`。
- 测试设置：`Project_Zhihui.test_settings` 提供压测/测试环境（独立库与 Redis、固定验证码、精简中间件与日志）。

## 服务与运行
- 主服务：`Project_Zhihui.asgi:application` 由 `daphne` 提供 HTTP + WebSocket。
- 任务服务：`celery -A Project_Zhihui worker` 执行异步任务；`celery -A Project_Zhihui beat` 调度定时任务。
- 外部依赖：确保 MySQL/Redis/Milvus 连通且凭据正确。

## 创建超级用户
- 首次运行时，需创建超级用户：`python manage.py createsuperuser`
- 登录 `/admin` 管理控制台，创建组织、用户、项目等。

## 测试
- 运行：`pytest` 或 `python manage.py test`
- 覆盖率：`pytest --cov`
- 压力测试：使用 `DJANGO_SETTINGS_MODULE=Project_Zhihui.test_settings` 或 Supervisor 中的 `django_project_zhihui_test`（默认端口 8002）。

## 部署（Supervisor）
- 安装Supervisor：`sudo apt install supervisor`
- 配置Supervisor：编辑 `/etc/supervisor/supervisord.conf`，在 `[include]` 的 `files` 中添加 `home/bupt/Server_Project_ZH/supervisor_config.conf`。
- 启动守护：`supervisord -c /home/bupt/Server_Project_ZH/supervisord.conf`
- 设置开机自启：`sudo systemctl enable supervisor`
- 控制服务：`supervisorctl -c /home/bupt/Server_Project_ZH/supervisord.conf status|start|stop|restart <program>`
- 程序包括：`django_project_zhihui`、`celery_worker`、`celery_beat`、`django_project_zhihui_test`。
- 如需替换系统配置，可参考文末原始运维说明中的步骤。

## 维护脚本与管理命令
- 示例：
  - `organization/management/commands/init_organization_notifications.py`
  - `user/management/commands/*`
- 执行：`python manage.py <command>`

## 常见问题与排查
- `unix:///tmp/supervisor.sock no such file`：参见文末原始“问题分析/解决步骤”。
- 端口占用：检查 `daphne`/Celery 是否已有进程；`lsof -i:8000`。
- 环境变量缺失：确认 `.env` 已加载，必需键已填写。
- 数据库迁移失败：检查数据库权限与连接；删除无效迁移并重建。
- Redis/Milvus 不可用：检查地址与端口，确认服务状态与凭据。

## 运维说明（Supervisor）
Supervisor常用命令：
### 重启应用
`supervisorctl -c /etc/supervisor/supervisord.conf restart django_project_zhihui django_project_zhihui_test `

### 重启任务服务
`supervisorctl -c /etc/supervisor/supervisord.conf restart celery_worker`

### 重启定时服务
`supervisorctl -c /etc/supervisor/supervisord.conf restart celery_beat`

### 更新配置
更新配置后需要执行指令使配置生效
- 使用系统级 supervisord：
  - `sudo supervisorctl -c /etc/supervisor/supervisord.conf reread`
  - `sudo supervisorctl -c /etc/supervisor/supervisord.conf update`
  - `sudo supervisorctl -c /etc/supervisor/supervisord.conf restart django_project_zhihui`

当提示权限不足时请添加sudo
### 查看状态
`supervisorctl -c /etc/supervisor/supervisord.conf status`

### 重启应用
`supervisorctl -c /etc/supervisor/supervisord.conf restart django_project_zhihui`

### 查看日志
`supervisorctl -c /etc/supervisor/supervisord.conf tail django_project_zhihui`
  
### 启动应用
`supervisorctl -c /etc/supervisor/supervisord.conf start django_project_zhihui`

### 停止应用
`supervisorctl -c /etc/supervisor/supervisord.conf stop django_project_zhihui`

### 重启所有应用
`supervisorctl -c /etc/supervisor/supervisord.conf restart all`


管理测试环境
### 查看所有服务状态
`supervisorctl -c /etc/supervisor/supervisord.conf status`

### 重启测试环境
`supervisorctl -c /etc/supervisor/supervisord.conf restart django_project_zhihui_test`

### 查看测试环境日志
`supervisorctl -c /etc/supervisor/supervisord.conf tail django_project_zhihui_test`
  
### 停止测试环境
`supervisorctl -c /etc/supervisor/supervisord.conf stop django_project_zhihui_test`


## 问题分析
错误原因 ： `unix:///tmp/supervisor.sock no such file` 表示supervisorctl无法找到supervisor的socket文件，这是因为：

1. 系统级的supervisor正在运行，但使用的是 /etc/supervisor/supervisord.conf 配置
2. 项目需要使用自己的supervisor配置文件 /home/bupt/Server_Project_ZH/supervisord.conf
3. 项目特定的supervisor实例没有启动
## 解决步骤
1. 启动项目supervisor ：使用项目配置文件启动supervisor守护进程
   
   ```
   supervisord -c /home/bupt/Server_Project_ZH/supervisord.conf
   ```
2. 重启Django服务 ：使用正确的配置文件重启Django项目
   
   ```
   supervisorctl -c /home/bupt/Server_Project_ZH/supervisord.conf restart django_project_zhihui
   ```

## 安装Milvus

## 安装配置 Ollama Embeddings - bge-m3:567模型
1. 安装Ollama：根据[Ollama官方文档](https://ollama.ai/docs/installation)安装Ollama，Linux环境下可直接使用：
   
   ```
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. 修改Ollama配置文件：
   - 执行`systemctl edit ollama.service`，在`[service]`下添加 `Environment="OLLAMA_HOST=0.0.0.0:11434"`以开启远程访问；`Environment="OLLAMA_MODELS=mnt/data/models/"`以指定模型存储路径。
   - 重启Ollama服务：
     
     ```
     sudo systemctl daemon-reload
     sudo systemctl restart ollama
     ```

3. 在 Linux 系统上使用标准安装程序时，ollama 用户需要对指定目录拥有读写权限。要将该目录分配给 ollama 用户，请运行 `sudo chown -R ollama:ollama <directory>`。或者修改配置文件中的`root`和`group`为`当前操作安装文件目录的用户`。
2. 拉取bge-m3:567模型：
   
   ```
   ollama pull bge-m3:567m
   ```
3. 启动Ollama服务：
   
   ```
   ollama serve
   ```


## 使用Trae IDE 远程 SSH 连接失败（证书问题）修复指南（连接学校虚机时可能出现该问题）

### 一、问题概述

#### 1. 核心错误

Trae IDE 通过 `icube-remote-ssh` 插件连接远程服务器时，触发 `exitCode: 2001` 错误，提示「Download server failed after 3 retry attempts」。

#### 2. 根本原因

远程服务器下载 Trae 组件包时，目标域名 `lf-cdn.trae.com.cn` 使用**自签名 SSL 证书**，系统默认拒绝信任此类未被权威机构认证的证书，导致组件包下载被拦截。

#### 3. 前置成功节点（排除基础问题）

* SSH 连接已建立：密码验证通过（`Authenticated to ``10.160.64.18`` using "password"`）。
* 服务器环境达标：Ubuntu 22.04（x86\_64 架构），GLIBC 2.35，已安装 curl、tar 等必备工具。
* 版本需求明确：远程服务器要求组件版本 `1088648953090_21`，构建版本 `4b3f5ec95a6b90d976fe38c4d0844821c2a284b8`。

### 二、前提准备

#### 1. 本地环境要求

* 操作系统：Windows 10+（已预装 OpenSSH 客户端，日志验证路径：`C:\WINDOWS\System32\OpenSSH\ssh.exe`）。
* 工具：无需额外安装，使用 Windows PowerShell（无需管理员权限）。

#### 2. 必备信息

* 远程服务器：IP、用户名、登录密码。
* 核心参数（从日志提取，以下仅为示例）：
  * 组件版本：`REMOTE_VERSION=1088648953090_21`
  * 构建版本：`DISTRO_COMMIT=4b3f5ec95a6b90d976fe38c4d0844821c2a284b8`
  * 服务器架构：`SERVER_ARCH=x64`
  * 安装目录：`SERVER_DIR=/home/bupt/.trae-server/bin/stable-4b3f5ec95a6b90d976fe38c4d0844821c2a284b8`

### 三、详细修复步骤（全程 PowerShell 操作）

#### Step 1：登录远程服务器

1. 打开 Windows PowerShell（快捷键：Win+X → 选择「Windows PowerShell」）。
2. 执行登录命令，输入密码后回车（密码输入无显式回显，正常输入即可）：

    ```
    ssh bupt@10.xx.xx.1x
    ```
3. 登录成功标识：命令行前缀变为 `bupt@RCXM-2025-025-PYXTc-huizhipingtai-01:~$`。

#### Step 2：定义核心参数（避免手动拼接错误）

在服务器终端执行以下命令，自动设置版本和路径参数：

```
\# 远程组件版本（日志指定，以下仅为示例）

REMOTE\_VERSION="1088648953090\_21"

\# 构建版本（用于拼接下载路径）

DISTRO\_COMMIT="4b3f5ec95a6b90d976fe38c4d0844821c2a284b8"

\# 服务器架构

SERVER\_ARCH="x64"

\# 组件安装目录（与插件默认路径一致）

SERVER\_DIR="/home/bupt/.trae-server/bin/stable-\$DISTRO\_COMMIT"

\# 带版本的下载链接（跳过证书验证专用）

DOWNLOAD\_URL="https://lf-cdn.trae.com.cn/obj/trae-com-cn/pkg/server/releases/stable/\$DISTRO\_COMMIT/linux/Trae-linux-\$SERVER\_ARCH-\$REMOTE\_VERSION.tar.gz"
```

#### Step 3：创建安装目录（避免目录不存在报错）

```
\# -p 参数：父目录不存在时自动创建，无报错

mkdir -p \$SERVER\_DIR
```

### Step 4：下载组件包（跳过 SSL 证书验证）

服务器已自带 curl 工具，执行以下命令下载（核心参数 `--insecure` 跳过证书校验）：

```
\# 进入安装目录

cd \$SERVER\_DIR

\# 下载组件包（--insecure 解决自签名证书问题，-O 保留原文件名）

curl --insecure -O \$DOWNLOAD\_URL
```
* 下载成功标识：终端显示进度条，最终输出 `100%` 且无报错。
* 验证下载文件：执行 `ls` 命令，若能看到 `Trae-linux-x64-1088648953090_21.tar.gz`，说明下载成功。

#### Step 5：解压组件包（与插件解压逻辑一致）

```
\# 解压到当前目录，--strip-components 1 去除压缩包顶层目录（避免多一层文件夹）

tar -xf Trae-linux-x64-\$REMOTE\_VERSION.tar.gz --strip-components 1
```
* 解压成功标识：执行 `ls` 命令，能看到 `index_trae.js`、`product.json` 等核心文件。
* 权限问题处理：若提示「Permission denied」，先执行以下命令赋予目录权限，再重新解压：

  ```
  chmod 755 \$SERVER\_DIR
  ```

#### Step 6：手动创建 version 文件（插件版本校验必需）

解压后默认缺失 `version` 文件，导致插件无法校验版本，需手动创建：

```
\# 写入与日志一致的版本号

echo "\$REMOTE\_VERSION" > version
```
* 验证文件：执行 `cat version`，若输出 `1088648953090_21`，说明创建成功。

#### Step 7：验证安装完整性

执行以下命令，确认核心文件无缺失：

```
\# 检查关键文件是否存在（预期输出4个文件名）

ls | grep -E "index\_trae.js|product.json|node|version"
```
* 预期输出：

```
index\_trae.js

product.json

node

version
```

#### Step 8：退出服务器，重新发起 SSH 连接

1. 执行以下命令退出远程服务器，回到本地 PowerShell：

    ```
    exit
    ```
2. 打开 Trae IDE，再次尝试ssh连接，若能正常登录，说明修复成功。