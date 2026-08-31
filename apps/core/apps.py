from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from .ai.question_count_policy import install_question_count_policy
        from .ai.personality_competency_questions_policy import (
            install_personality_competency_questions_policy,
        )
        from .ai.candidate_question_grounding_policy import (
            install_candidate_question_grounding_policy,
        )
        from .ai.pre_interview_raw_evidence_policy import (
            install_pre_interview_raw_evidence_policy,
        )
        from .ai.pre_interview_grounding_policy import (
            install_pre_interview_grounding_policy,
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

        # Popup selections determine what to explore. Candidate assessment
        # evidence then determines the angle of every generated question.
        # Install this after the competency policy so both personality modes
        # receive the same candidate-specific grounding requirement.
        install_candidate_question_grounding_policy()

        # Production pre-interview support should see the candidate's actual
        # normalized assessment results as well as Talena's saved AI
        # interpretations. This keeps production evidence closer to the prompt
        # playground and prevents summaries-of-summaries from losing profile
        # detail.
        install_pre_interview_raw_evidence_policy()

        # Keep Prepare for interview anchored in the individual candidate's
        # evidence even when administrator guidance changes over time.
        install_pre_interview_grounding_policy()

        install_personality_motivation_interaction_policy()
        install_post_interview_role_context_policy()
        install_post_interview_role_context_policy_v2()
