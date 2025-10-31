Supervisor常用命令：
supervisorctl restart django_project_zhihui django_project_zhihui_test 
supervisorctl restart celery_worker
supervisorctl restart celery_beat

# 查看状态
supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf status

# 重启应用
supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf restart django_project_zhihui

# 查看日志
supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf tail django_project_zhihui

# 启动应用
supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf start django_project_zhihui

# 停止应用
supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf stop django_project_zhihui

# 重启所有应用
supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf restart all


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
supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf status

# 重启测试环境
supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf restart django_project_zhihui_test

# 查看测试环境日志
supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf tail django_project_zhihui_test

# 停止测试环境
supervisorctl -c /home/undergraduate/Workspace/bupt_zh/supervisord.conf stop django_project_zhihui_test


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
   supervisorctl -c /home/
   undergraduate/Workspace/bupt_zh/
   supervisord.conf restart 
   django_project_zhihui 
   django_project_zhihui_test
   ```
## 当前状态
- ✅ django_project_zhihui : RUNNING (正常运行)
- ✅ django_project_zhihui_test : RUNNING (正常运行)
- ❌ celery_beat : FATAL (需要单独排查)
- ❌ celery_worker : FATAL (需要单独排查)
## 使用建议
今后使用supervisorctl时，请记得指定项目配置文件：

```
supervisorctl -c /home/
undergraduate/Workspace/bupt_zh/
supervisord.conf [command]
```
或者可以设置环境变量简化命令：

```
export SUPERVISOR_CONFIG=/home/
undergraduate/Workspace/bupt_zh/
supervisord.conf
supervisorctl [command]
```
Django项目现在已经正常运行，之前实现的密码重置邮件功能也已生效。