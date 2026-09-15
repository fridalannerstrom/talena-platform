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
        from .ai.personality_question_situational_language_policy import (
            install_personality_question_situational_language_policy,
        )
        from .ai.personality_question_label_policy import (
            install_personality_question_label_policy,
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
        from .ai.shared_personality_grounding_policy import (
            install_shared_personality_grounding_policy,
        )

        # Install product-level prompt and question policies at startup so
        # admin metadata, protected defaults and runtime behaviour stay in
        # sync across the application.
        install_question_count_policy()
        install_personality_competency_questions_policy()

        # Popup selections determine what to explore. Candidate assessment
        # evidence then determines the angle of every generated question.
        install_candidate_question_grounding_policy()

        # Require a candidate-specific fingerprint and construct fidelity.
        install_candidate_question_fingerprint_policy()
        install_personality_question_precision_policy()

        # STEN 4-7 is situationsbaserat / situational, never a middle or average
        # level. Keep this terminology guard before the final result-summary
        # grounding so fallback and visible why wording stay consistent.
        install_personality_question_situational_language_policy()

        # Every personality question must keep a visible focus label. This also
        # raises manual/AI parent-trait selection to eight.
        install_personality_question_label_policy()

        # #230/#231 refinement: apply the candidate's Result Summary LAST in the
        # Personality Questions prompt chain. The wrapper removes the older raw
        # STEN/direction payloads for parent-trait questions and exposes only the
        # finished candidate summary, process context and admin-controlled
        # question behaviour. Competency mode keeps its separate evidence path.
        install_personality_question_definition_grounding_policy()

        # Combined trait dynamics are generated as exactly two separate items,
        # then normalised back to Talena's existing saved string field.
        install_personality_dynamics_structure_policy()

        # Keep motivation questions faithful to factor definitions and process
        # context without replacing the candidate's motivation pattern.
        install_motivation_question_precision_policy()

        # Production pre-interview support sees raw normalized assessment results
        # as well as Talena's saved AI interpretations.
        install_pre_interview_raw_evidence_policy()
        install_pre_interview_grounding_policy()

        install_personality_motivation_interaction_policy()
        install_post_interview_role_context_policy()
        install_post_interview_role_context_policy_v2()

        # Question-level interview notes are structured evidence.
        install_post_interview_question_evidence_policy()

        # #231: other active AI consumers that interpret parent personality traits
        # reuse one candidate-specific evidence layer backed by the same approved
        # score-band texts used in Talena's Result Summary. These broader flows
        # may still receive structured score metadata where it adds value.
        install_shared_personality_grounding_policy()
