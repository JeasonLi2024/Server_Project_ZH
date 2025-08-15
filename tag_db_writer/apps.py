from django.apps import AppConfig


class TagDbWriterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tag_db_writer'
    verbose_name = '标签数据库写入器'
