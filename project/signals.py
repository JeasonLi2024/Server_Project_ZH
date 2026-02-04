from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from .models import Requirement
from .tasks import sync_requirement_vectors_task, sync_raw_docs_auto_task, delete_requirement_vectors_task
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Requirement)
def handle_requirement_save(sender, instance, created, **kwargs):
    """
    监听需求保存事件：
    1. 如果状态是 draft，不处理（或清理已有向量）
    2. 如果状态是有效状态，触发向量同步
    3. 自动同步 Raw Docs (有文件则用文件，无文件则用文本)
    """
    logger.info(f"Requirement saved: {instance.id}, status: {instance.status}")
    
    # 使用 Celery 异步任务 + on_commit 确保事务提交后执行
    transaction.on_commit(lambda: sync_requirement_vectors_task.delay(instance.id))
    transaction.on_commit(lambda: sync_raw_docs_auto_task.delay(instance.id))

@receiver(post_delete, sender=Requirement)
def handle_requirement_delete(sender, instance, **kwargs):
    """
    监听需求删除事件：
    同步删除 Milvus 中的向量
    """
    logger.info(f"Requirement deleted: {instance.id}")
    # 删除操作异步执行
    delete_requirement_vectors_task.delay(instance.id)

# 监听 M2M 字段变化 (Tags)
@receiver(m2m_changed, sender=Requirement.tag1.through)
@receiver(m2m_changed, sender=Requirement.tag2.through)
def handle_tags_change(sender, instance, **kwargs):
    """
    当标签发生变化时，也需要重新生成 Semantic 向量 (Tags 参与了 Semantic Embedding)
    """
    # instance 是 Requirement 对象
    if kwargs.get('action') in ['post_add', 'post_remove', 'post_clear']:
        logger.info(f"Requirement tags changed: {instance.id}")
        transaction.on_commit(lambda: sync_requirement_vectors_task.delay(instance.id))
        # Tags 变化也可能影响 fallback text (如果无文件模式下)
        transaction.on_commit(lambda: sync_raw_docs_auto_task.delay(instance.id))

# 监听 M2M 字段变化 (Files)
@receiver(m2m_changed, sender=Requirement.files.through)
def handle_files_change(sender, instance, **kwargs):
    """
    当关联文件发生变化时，重新同步 Raw Docs
    """
    if kwargs.get('action') in ['post_add', 'post_remove', 'post_clear']:
        logger.info(f"Requirement files changed: {instance.id}")
        transaction.on_commit(lambda: sync_raw_docs_auto_task.delay(instance.id))
