from django.apps import AppConfig


class ProjectscoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projectscore"
    verbose_name = "学生项目评分管理"

    def ready(self):
        import projectscore.signals
