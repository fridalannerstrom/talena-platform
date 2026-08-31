from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from .ai.question_count_policy import install_question_count_policy
        from .ai.personality_competency_questions_policy import (
            install_personality_competency_questions_policy,
        )
        from .ai.personality_motivation_interaction_policy import (
            install_personality_motivation_interaction_policy,
        )
        from .ai.post_interview_role_context_policy import (
            install_post_interview_role_context_policy,
        )
        from .ai.post_interview_role_context_policy_v2 import (
            install_post_interview_role_context_policy_v2,
        )

        # Install product-level prompt and question policies at startup so
        # admin metadata, protected defaults and runtime behaviour stay in
        # sync across the application.
        install_question_count_policy()
        install_personality_competency_questions_policy()
        install_personality_motivation_interaction_policy()
        install_post_interview_role_context_policy()
        install_post_interview_role_context_policy_v2()
