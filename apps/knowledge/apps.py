from django.apps import AppConfig

class KnowledgeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.knowledge"

    def ready(self):
        import apps.knowledge.signals  # noqa