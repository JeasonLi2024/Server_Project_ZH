Supervisor常用命令：
supervisorctl restart django_project_zhihui django_project_zhihui_test 

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