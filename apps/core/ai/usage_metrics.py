"""Opt-in, metadata-only OpenAI metering for Talena (#435).

Never store user inputs, outputs, exception messages, candidate identifiers,
prompt versions or provider request IDs. Features are code-owned allowlisted
identifiers. The existing ActivityEvent table is the shared audit source.
"""
import logging
import os
import re

logger = logging.getLogger(__name__)

# Only static, code-owned feature identifiers can be persisted.
FEATURES = {
    "assistant_chat": "AI-chatt",
    "rag_embedding": "RAG-sökning",
    "team_insights": "Teamrapport",
    "purpose_fit": "Rollmatchning",
    "motivation_questions": "Motivationsfrågor",
    "candidate_summary": "Kandidatsammanfattning",
    "pre_interview": "Inför intervju",
    "post_interview": "Efter intervju",
    "prompt_playground": "Promptförhandsgranskning",
    "cognitive_questions": "Färdighetsfrågor",
    "response_styles": "Svarsstilar",
    "personality_questions": "Personlighetsfrågor",
    "cognitive_interpretation": "Färdighetstolkning",
    "manager_interview_comments": "Chefsrapport: intervju",
    "motivation_interpretation": "Motivationstolkning",
    "manager_personality": "Chefsrapport: personlighet",
    "general_candidate_insights": "Kandidatinsikter",
    "personality_interpretation": "Personlighetstolkning",
    "overall_picture": "Helhetsbild",
    "role_trait_selection": "Val av personlighetsdrag",
    "question_quality": "Frågekvalitetskontroll",
}
OPERATIONS = frozenset({"chat", "embeddings", "responses"})
OUTCOMES = {
    "succeeded": "ai_call_succeeded",
    "failed": "ai_call_failed",
    "incomplete": "ai_call_incomplete",
}


def usage_logging_enabled():
    # GDPR retention/notice approval is pending (#310/#433).
    # Explicit opt-in avoids silently introducing broad production tracking.
    return os.environ.get("TALENA_AI_USAGE_LOGGING_ENABLED", "0") == "1"


def _token_number(value):
    # bool, floats, fake Mock objects and strings must not become token counts.
    return value if type(value) is int and 0 <= value <= 1_000_000_000 else None


def _usage_dict(usage):
    if usage is None:
        return None
    if isinstance(usage, dict):
        get = usage.get
    else:
        get = lambda key: getattr(usage, key, None)
    prompt = _token_number(get("prompt_tokens"))
    if prompt is None:
        prompt = _token_number(get("input_tokens"))
    completion = _token_number(get("completion_tokens"))
    if completion is None:
        completion = _token_number(get("output_tokens"))
    total = _token_number(get("total_tokens"))
    if prompt is None and completion is None and total is None:
        return None
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }


def record_ai_call(*, feature, operation, model, outcome, usage=None,
                   owner=None, process=None, company=None):
    """Best-effort provider-call metric, never a candidate/report-success claim.

    A feature is a static code string. Tenant derives only from known ORM objects,
    never client-supplied company IDs. No actor/candidate references are stored.
    """
    if not usage_logging_enabled():
        return
    if feature not in FEATURES or operation not in OPERATIONS or outcome not in OUTCOMES:
        return
    # Model may come from env/SDK. Persist only a conservative, short identifier.
    model = model if type(model) is str and re.fullmatch(r"[A-Za-z0-9._/-]{1,80}", model) else "unidentified"
    usage_values = _usage_dict(usage)
    meta = {
        "schema": 1,
        "feature": feature,
        "operation": operation,
        "model": model,
        "usage_available": usage_values is not None,
    }
    if usage_values:
        meta.update(usage_values)
    try:
        from apps.activity.models import ActivityEvent
        related_process = process or getattr(owner, "process", None)
        related_company = (
            getattr(related_process, "company", None)
            if related_process is not None
            else company
        )
        ActivityEvent.objects.create(
            verb=OUTCOMES[outcome],
            company=related_company,
            process=related_process,
            meta=meta,
        )
    except Exception:
        # Never transform a successful/failed OpenAI call into a different
        # result because analytics storage is temporarily unavailable.
        # No exception payload, request data or SQL parameters in logs.
        logger.warning("Talena AI metering storage unavailable")
