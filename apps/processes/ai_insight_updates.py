from django.utils.translation import gettext_lazy as _

from .purpose_utils import normalize_purpose_key


# This registry is the single source for stale-state checks and regeneration
# routes. Add or remove a customer-facing AI insight here when its lifecycle
# changes; admin-only legacy candidate summaries are intentionally excluded.
CANDIDATE_AI_UPDATE_SECTION_CONFIG = (
    {
        "key": "personality_interpretation",
        "label": _("Personality interpretation"),
        "result_field": "ai_personality_interpretation",
        "status_field": "ai_personality_interpretation_status",
        "generated_at_field": "ai_personality_interpretation_generated_at",
        "purpose_field": "ai_personality_interpretation_purpose",
        "route_name": "process_candidate_personality_interpretation_regenerate",
    },
    {
        "key": "manager_report_personality",
        "label": _("Manager-report personality texts"),
        "result_field": "ai_manager_report_personality",
        "status_field": "ai_manager_report_personality_status",
        "generated_at_field": "ai_manager_report_personality_generated_at",
        "purpose_field": "ai_manager_report_personality_purpose",
        "route_name": "process_candidate_manager_report_personality_regenerate",
    },
    {
        "key": "personality_questions",
        "label": _("Personality questions"),
        "result_field": "ai_personality_questions",
        "status_field": "ai_personality_questions_status",
        "generated_at_field": "ai_personality_questions_generated_at",
        "purpose_field": "ai_personality_questions_purpose",
        "route_name": "process_candidate_personality_questions_regenerate",
    },
    {
        "key": "motivation_interpretation",
        "label": _("Motivation interpretation"),
        "result_field": "ai_motivation_interpretation",
        "status_field": "ai_motivation_interpretation_status",
        "generated_at_field": "ai_motivation_interpretation_generated_at",
        "purpose_field": "ai_motivation_interpretation_purpose",
        "route_name": "process_candidate_motivation_interpretation_regenerate",
    },
    {
        "key": "motivation_questions",
        "label": _("Motivation questions"),
        "result_field": "ai_motivation_questions",
        "status_field": "ai_motivation_questions_status",
        "generated_at_field": "ai_motivation_questions_generated_at",
        "purpose_field": "ai_motivation_questions_purpose",
        "route_name": "process_candidate_motivation_questions_regenerate",
    },
    {
        "key": "cognitive_interpretation",
        "label": _("Cognitive interpretation"),
        "result_field": "ai_cognitive_interpretation",
        "status_field": "ai_cognitive_interpretation_status",
        "generated_at_field": "ai_cognitive_interpretation_generated_at",
        "purpose_field": "ai_cognitive_interpretation_purpose",
        "route_name": "process_candidate_cognitive_interpretation_regenerate",
    },
    {
        "key": "cognitive_questions",
        "label": _("Cognitive questions"),
        "result_field": "ai_cognitive_questions",
        "status_field": "ai_cognitive_questions_status",
        "generated_at_field": "ai_cognitive_questions_generated_at",
        "purpose_field": "ai_cognitive_questions_purpose",
        "route_name": "process_candidate_cognitive_questions_regenerate",
    },
    {
        "key": "pre_interview_decision_support",
        "label": _("Pre-interview decision support"),
        "result_field": "ai_pre_interview_decision_support",
        "status_field": "ai_pre_interview_decision_support_status",
        "generated_at_field": "ai_pre_interview_decision_support_generated_at",
        "purpose_field": "ai_pre_interview_decision_support_purpose",
        "route_name": "process_candidate_pre_interview_decision_support_regenerate",
    },
    {
        "key": "post_interview_decision_support",
        "label": _("Post-interview decision support"),
        "result_field": "ai_post_interview_decision_support",
        "status_field": "ai_post_interview_decision_support_status",
        "generated_at_field": "ai_post_interview_decision_support_generated_at",
        "purpose_field": "ai_post_interview_decision_support_purpose",
        "route_name": "process_candidate_post_interview_decision_support_regenerate",
    },
)


def build_candidate_ai_update_state(*, invitation, process, purpose_context=None):
    empty_state = {
        "has_outdated_insights": False,
        "sections": [],
        "section_count": 0,
        "purpose_changed": False,
        "context_changed": False,
    }
    if getattr(process, "is_historical", False):
        return empty_state

    current_purpose = normalize_purpose_key(
        getattr(process, "purpose", "") or ""
    )
    context_updated_at = getattr(purpose_context, "updated_at", None)
    analysed_sections = []
    purpose_changed_any = False
    context_changed_any = False

    for config in CANDIDATE_AI_UPDATE_SECTION_CONFIG:
        saved_result = getattr(invitation, config["result_field"], None)
        if not saved_result:
            continue

        status = str(getattr(invitation, config["status_field"], "") or "").strip().lower()
        generated_at = getattr(invitation, config["generated_at_field"], None)
        saved_purpose = normalize_purpose_key(
            getattr(invitation, config["purpose_field"], "") or ""
        )
        purpose_changed = bool(saved_purpose and current_purpose and saved_purpose != current_purpose)
        context_changed = bool(context_updated_at and generated_at and context_updated_at > generated_at)
        purpose_changed_any = purpose_changed_any or purpose_changed
        context_changed_any = context_changed_any or context_changed

        analysed_sections.append({
            **config,
            "status": status,
            "purpose_changed": purpose_changed,
            "context_changed": context_changed,
        })

    has_process_change = purpose_changed_any or context_changed_any
    if not has_process_change and not any(
        section["status"] in {"outdated", "failed"} for section in analysed_sections
    ):
        return empty_state

    outdated_sections = []
    for section in analysed_sections:
        needs_update = (
            section["status"] in {"outdated", "failed"}
            or section["purpose_changed"]
            or section["context_changed"]
        )
        if not needs_update:
            continue

        reasons = []
        if section["purpose_changed"]:
            reasons.append("purpose")
        if section["context_changed"]:
            reasons.append("context")
        if section["status"] in {"outdated", "failed"} and not reasons:
            reasons.append("status")

        outdated_sections.append({
            "key": section["key"],
            "label": section["label"],
            "route_name": section["route_name"],
            "status": section["status"],
            "reasons": reasons,
        })

    return {
        "has_outdated_insights": bool(outdated_sections),
        "sections": outdated_sections,
        "section_count": len(outdated_sections),
        "purpose_changed": purpose_changed_any,
        "context_changed": context_changed_any,
    }
