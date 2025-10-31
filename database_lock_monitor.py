#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库锁监控脚本

该脚本用于监控MySQL数据库的锁等待情况，并在发现异常时发送告警。
可以作为定时任务运行，也可以手动执行检查。

使用方法：
1. 确保Django环境已正确配置
2. 运行: python database_lock_monitor.py
3. 或者设置为定时任务: */5 * * * * /path/to/python database_lock_monitor.py

作者: 系统自动生成
创建时间: 2024
"""

import os
import sys
import django
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from django.db import connection
from django.conf import settings
from django.core.mail import send_mail

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_lock_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabaseLockMonitor:
    """数据库锁监控器"""
    
    def __init__(self):
        self.alert_threshold = 30  # 锁等待超过30秒触发告警
        self.max_lock_count = 10   # 同时存在超过10个锁等待触发告警
        self.admin_emails = ['admin@example.com']  # 管理员邮箱列表
        
    def check_lock_waits(self):
        """检查锁等待情况"""
        try:
            with connection.cursor() as cursor:
                # 查询当前锁等待情况
                cursor.execute("""
                    SELECT 
                        r.trx_id AS waiting_trx_id,
                        r.trx_mysql_thread_id AS waiting_thread,
                        r.trx_query AS waiting_query,
                        b.trx_id AS blocking_trx_id,
                        b.trx_mysql_thread_id AS blocking_thread,
                        b.trx_query AS blocking_query,
                        p.time AS wait_time,
                        p.info AS current_query
                    FROM information_schema.innodb_lock_waits w
                    INNER JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id
                    INNER JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
                    INNER JOIN information_schema.processlist p ON p.id = r.trx_mysql_thread_id
                    ORDER BY p.time DESC
                """)
                
                lock_waits = cursor.fetchall()
                
                if lock_waits:
                    logger.warning(f"发现 {len(lock_waits)} 个锁等待情况")
                    
                    # 检查是否需要告警
                    long_waits = []
                    for wait in lock_waits:
                        wait_time = wait[6] if wait[6] else 0
                        if wait_time > self.alert_threshold:
                            long_waits.append(wait)
                    
                    if long_waits or len(lock_waits) > self.max_lock_count:
                        self.send_alert(lock_waits, long_waits)
                    
                    return lock_waits
                else:
                    logger.info("未发现锁等待情况")
                    return []
                    
        except Exception as e:
            logger.error(f"检查锁等待时发生错误: {str(e)}")
            return None
    
    def check_long_running_queries(self):
        """检查长时间运行的查询"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        user,
                        host,
                        db,
                        command,
                        time,
                        state,
                        info
                    FROM information_schema.processlist 
                    WHERE command != 'Sleep' 
                    AND time > 60
                    AND info IS NOT NULL
                    ORDER BY time DESC
                """)
                
                long_queries = cursor.fetchall()
                
                if long_queries:
                    logger.warning(f"发现 {len(long_queries)} 个长时间运行的查询")
                    for query in long_queries:
                        logger.warning(f"PID: {query[0]}, 运行时间: {query[5]}秒, 查询: {query[7][:100]}...")
                
                return long_queries
                
        except Exception as e:
            logger.error(f"检查长时间运行查询时发生错误: {str(e)}")
            return None
    
    def check_ddl_operations(self):
        """检查DDL操作"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        user,
                        host,
                        db,
                        command,
                        time,
                        state,
                        info
                    FROM information_schema.processlist 
                    WHERE info LIKE '%ALTER%' 
                    OR info LIKE '%CREATE INDEX%'
                    OR info LIKE '%DROP INDEX%'
                    OR info LIKE '%CREATE TABLE%'
                    OR info LIKE '%DROP TABLE%'
                    ORDER BY time DESC
                """)
                
                ddl_operations = cursor.fetchall()
                
                if ddl_operations:
                    logger.info(f"发现 {len(ddl_operations)} 个DDL操作")
                    for ddl in ddl_operations:
                        logger.info(f"PID: {ddl[0]}, 运行时间: {ddl[5]}秒, DDL: {ddl[7][:100]}...")
                
                return ddl_operations
                
        except Exception as e:
            logger.error(f"检查DDL操作时发生错误: {str(e)}")
            return None
    
    def get_database_status(self):
        """获取数据库状态信息"""
        try:
            with connection.cursor() as cursor:
                # 获取连接数
                cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                connections_count = cursor.fetchone()[1]
                
                # 获取锁等待统计
                cursor.execute("SHOW STATUS LIKE 'Innodb_row_lock_waits'")
                lock_waits_count = cursor.fetchone()[1]
                
                # 获取锁等待时间
                cursor.execute("SHOW STATUS LIKE 'Innodb_row_lock_time'")
                lock_wait_time = cursor.fetchone()[1]
                
                status = {
                    'connections': connections_count,
                    'lock_waits': lock_waits_count,
                    'lock_wait_time': lock_wait_time,
                    'timestamp': datetime.now()
                }
                
                logger.info(f"数据库状态 - 连接数: {connections_count}, 锁等待次数: {lock_waits_count}, 锁等待时间: {lock_wait_time}ms")
                
                return status
                
        except Exception as e:
            logger.error(f"获取数据库状态时发生错误: {str(e)}")
            return None
    
    def send_alert(self, lock_waits, long_waits):
        """发送告警邮件"""
        try:
            subject = f"数据库锁等待告警 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            message = f"""
数据库锁等待告警报告

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
总锁等待数: {len(lock_waits)}
长时间等待数: {len(long_waits)}

详细信息:
"""
            
            for i, wait in enumerate(lock_waits[:5], 1):  # 只显示前5个
                message += f"""
锁等待 {i}:
  等待事务ID: {wait[0]}
  等待线程ID: {wait[1]}
  阻塞事务ID: {wait[3]}
  阻塞线程ID: {wait[4]}
  等待时间: {wait[6]}秒
  当前查询: {wait[7][:200] if wait[7] else 'N/A'}...
"""
            
            if len(lock_waits) > 5:
                message += f"\n... 还有 {len(lock_waits) - 5} 个锁等待未显示"
            
            message += f"""

建议处理措施:
1. 检查长时间运行的事务
2. 考虑终止阻塞的查询
3. 优化查询性能
4. 检查索引使用情况

监控脚本: database_lock_monitor.py
"""
            
            # 使用Django的邮件系统发送告警
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=self.admin_emails,
                fail_silently=False,
            )
            
            logger.info("告警邮件发送成功")
            
        except Exception as e:
            logger.error(f"发送告警邮件时发生错误: {str(e)}")
    
    def generate_report(self):
        """生成监控报告"""
        logger.info("开始数据库锁监控检查...")
        
        # 检查锁等待
        lock_waits = self.check_lock_waits()
        
        # 检查长时间运行的查询
        long_queries = self.check_long_running_queries()
        
        # 检查DDL操作
        ddl_operations = self.check_ddl_operations()
        
        # 获取数据库状态
        db_status = self.get_database_status()
        
        report = {
            'timestamp': datetime.now(),
            'lock_waits': lock_waits,
            'long_queries': long_queries,
            'ddl_operations': ddl_operations,
            'database_status': db_status
        }
        
        logger.info("数据库锁监控检查完成")
        
        return report


def main():
    """主函数"""
    try:
        monitor = DatabaseLockMonitor()
        report = monitor.generate_report()
        
        # 可以将报告保存到文件或数据库
        # 这里简单打印到日志
        logger.info("监控报告生成完成")
        
        return report
        
    except Exception as e:
        logger.error(f"监控脚本执行失败: {str(e)}")
        return None


if __name__ == "__main__":
    main()