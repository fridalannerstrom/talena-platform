from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from .ai.question_count_policy import install_question_count_policy
        from .ai.personality_competency_questions_policy import (
            install_personality_competency_questions_policy,
        )

        # Install the product-level 3 / 3 / 8 count contract first so the
        # competency extension inherits the same protected question count.
        install_question_count_policy()
        install_personality_competency_questions_policy()
