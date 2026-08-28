from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from .ai.question_count_policy import install_question_count_policy

        install_question_count_policy()
