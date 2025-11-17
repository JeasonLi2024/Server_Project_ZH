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

## 测试
- 运行：`pytest` 或 `python manage.py test`
- 覆盖率：`pytest --cov`
- 压力测试：使用 `DJANGO_SETTINGS_MODULE=Project_Zhihui.test_settings` 或 Supervisor 中的 `django_project_zhihui_test`（默认端口 8002）。

## 部署（Supervisor）
- 启动守护：`supervisord -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf`
- 控制服务：`supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf status|start|stop|restart <program>`
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

Supervisor常用命令：
supervisorctl restart django_project_zhihui django_project_zhihui_test 
supervisorctl restart celery_worker
supervisorctl restart celery_beat

# 查看状态
supervisorctl -c /etc/supervisor/supervisord.conf status

# 重启应用
supervisorctl -c /etc/supervisor/supervisord.conf restart django_project_zhihui

# 查看日志
supervisorctl -c /etc/supervisor/supervisord.conf tail django_project_zhihui

# 启动应用
supervisorctl -c /etc/supervisor/supervisord.conf start django_project_zhihui

# 停止应用
supervisorctl -c /etc/supervisor/supervisord.conf stop django_project_zhihui

# 重启所有应用
supervisorctl -c /etc/supervisor/supervisord.conf restart all


生产环境下需要替换系统配置文件
# 备份原配置
sudo cp /etc/supervisor/supervisord.conf /etc/supervisor/supervisord.conf.backup

# 使用新配置
sudo cp /home/undergraduate/Workspace/bupt_zh/supervisord.conf /etc/supervisor/supervisord.conf

# 重启系统服务
sudo systemctl restart supervisor
sudo systemctl enable supervisor  # 开机自启


管理测试环境
# 查看所有服务状态
supervisorctl -c /etc/supervisor/supervisord.conf status

# 重启测试环境
supervisorctl -c /etc/supervisor/supervisord.conf restart django_project_zhihui_test

# 查看测试环境日志
supervisorctl -c /etc/supervisor/supervisord.conf tail django_project_zhihui_test

# 停止测试环境
supervisorctl -c /etc/supervisor/supervisord.conf stop django_project_zhihui_test


## 问题分析
错误原因 ： unix:///tmp/supervisor.sock no such file 表示supervisorctl无法找到supervisor的socket文件，这是因为：

1. 1.
   系统级的supervisor正在运行，但使用的是 /etc/supervisor/supervisord.conf 配置
2. 2.
   项目需要使用自己的supervisor配置文件 /home/undergraduate/Workspace/bupt_zh/supervisord.conf
3. 3.
   项目特定的supervisor实例没有启动
## 解决步骤
1. 1.
   启动项目supervisor ：使用项目配置文件启动supervisor守护进程
   
   ```
   supervisord -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf
   ```
2. 2.
   重启Django服务 ：使用正确的配置文件重启Django项目
   
   ```
   supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf restart django_project_zhihui 
   ```
