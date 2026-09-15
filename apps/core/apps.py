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
        from .ai.candidate_question_fingerprint_policy import (
            install_candidate_question_fingerprint_policy,
        )
        from .ai.personality_question_precision_policy import (
            install_personality_question_precision_policy,
        )
        from .ai.personality_question_definition_grounding_policy import (
            install_personality_question_definition_grounding_policy,
        )
        from .ai.personality_dynamics_structure_policy import (
            install_personality_dynamics_structure_policy,
        )
        from .ai.motivation_question_precision_policy import (
            install_motivation_question_precision_policy,
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
        from .ai.post_interview_question_evidence_policy import (
            install_post_interview_question_evidence_policy,
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

        # Apply the final candidate-fingerprint quality bar after the normal
        # grounding policy. This prevents role/context wording from replacing
        # the actual assessment evidence as the reason for a question and makes
        # the visible why field traceable to this candidate's result pattern.
        install_candidate_question_fingerprint_policy()

        # Keep personality questions semantically faithful to the selected
        # construct and require the visible why text to explain the candidate's
        # qualitative profile direction, not only why a topic matters for the role.
        install_personality_question_precision_policy()

        # Ground parent-trait personality questions in Talena's approved pole
        # definitions and score-specific indicator interpretations. Install this
        # after the other personality prompt policies so the final runtime prompt
        # always receives the same authoritative definition layer.
        install_personality_question_definition_grounding_policy()

        # Combined trait dynamics are generated as exactly two separate items,
        # then normalised back to Talena's existing saved string field so old
        # results and downstream consumers stay backwards compatible.
        install_personality_dynamics_structure_policy()

        # Keep motivation questions faithful to factor definitions and make the
        # supplied role/process context shape each scenario without replacing
        # the candidate's actual motivation pattern as the basis for the question.
        install_motivation_question_precision_policy()

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

        # Question-level interview notes are structured evidence. Install this
        # after the other post-interview prompt policies so the final runtime
        # prompt always receives the exact question together with its saved
        # answer/note, even when no separate free-text interview note exists.
        install_post_interview_question_evidence_policy()
