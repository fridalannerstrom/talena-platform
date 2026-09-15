from __future__ import annotations

from contextvars import ContextVar
from functools import wraps
from typing import Any

from .language import normalize_ai_language
from .personality_ai_evidence import (
    build_owner_personality_ai_evidence_text,
    build_personality_ai_evidence_text,
)


_INSTALLED = False
_PERSONALITY_GROUNDING_LANGUAGE: ContextVar[str] = ContextVar(
    "talena_shared_personality_grounding_language",
    default="en",
)


def _insert_before_marker(
    prompt: str,
    section: str,
    marker: str,
) -> str:
    prompt = str(prompt or "").rstrip()
    section = str(section or "").strip()

    if not section:
        return prompt

    marker_index = prompt.find(marker)

    if marker_index < 0:
        return f"{prompt}\n\n{section}".strip()

    before = prompt[:marker_index].rstrip()
    after = prompt[marker_index:].lstrip("\n")

    return f"{before}\n\n{section}\n\n{after}".strip()


def _language(value: str | None) -> str:
    return normalize_ai_language(value or "en")


def _install_assessment_evidence_grounding(purpose_fit) -> None:
    original_builder = purpose_fit.build_assessment_evidence

    if getattr(original_builder, "_talena_shared_personality_grounding", False):
        return

    @wraps(original_builder)
    def grounded_assessment_evidence(invitation):
        assessment_text, assessment_type_count = original_builder(invitation)

        grounding = build_owner_personality_ai_evidence_text(
            invitation,
            language_code=_PERSONALITY_GROUNDING_LANGUAGE.get(),
        )

        if grounding:
            assessment_text = (
                f"{str(assessment_text or '').rstrip()}\n\n{grounding}"
                if str(assessment_text or "").strip()
                else grounding
            )

        return assessment_text, assessment_type_count

    grounded_assessment_evidence._talena_shared_personality_grounding = True
    purpose_fit.build_assessment_evidence = grounded_assessment_evidence


def _install_language_context_wrapper(module, function_name: str) -> None:
    original = getattr(module, function_name)

    if getattr(original, "_talena_shared_personality_language_context", False):
        return

    @wraps(original)
    def wrapped(owner, *, language_code=None):
        language_code = _language(language_code)
        token = _PERSONALITY_GROUNDING_LANGUAGE.set(language_code)

        try:
            return original(
                owner,
                language_code=language_code,
            )
        finally:
            _PERSONALITY_GROUNDING_LANGUAGE.reset(token)

    wrapped._talena_shared_personality_language_context = True
    setattr(module, function_name, wrapped)


def _install_personality_interpretation_grounding(personality_interpretation) -> None:
    original = personality_interpretation.build_personality_interpretation_prompt

    if getattr(original, "_talena_shared_personality_grounding", False):
        return

    @wraps(original)
    def grounded_prompt(
        owner,
        personality_results,
        *,
        motivation_results=None,
        language_code="en",
    ):
        language_code = _language(language_code)
        prompt = original(
            owner,
            personality_results,
            motivation_results=motivation_results,
            language_code=language_code,
        )
        grounding = build_personality_ai_evidence_text(
            personality_results,
            language_code=language_code,
        )

        return _insert_before_marker(
            prompt,
            grounding,
            "\n\nADMINISTRATOR AI GUIDANCE",
        )

    grounded_prompt._talena_shared_personality_grounding = True
    personality_interpretation.build_personality_interpretation_prompt = grounded_prompt


def _install_candidate_summary_grounding(candidate_summary) -> None:
    original = candidate_summary.build_candidate_prompt

    if getattr(original, "_talena_shared_personality_grounding", False):
        return

    @wraps(original)
    def grounded_prompt(owner, *, language_code="en"):
        language_code = _language(language_code)
        prompt = original(
            owner,
            language_code=language_code,
        )
        grounding = build_owner_personality_ai_evidence_text(
            owner,
            language_code=language_code,
        )

        return _insert_before_marker(
            prompt,
            grounding,
            "\n\nINTERPRETATION INSTRUCTION",
        )

    grounded_prompt._talena_shared_personality_grounding = True
    candidate_summary.build_candidate_prompt = grounded_prompt


def _general_insight_personality_rows(
    insight_input: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(insight_input, dict):
        return []

    personality = insight_input.get("personality")
    if not isinstance(personality, dict):
        return []

    rows = personality.get("all_scores")
    return rows if isinstance(rows, list) else []


def _install_general_insights_grounding(candidate_insights) -> None:
    original = candidate_insights.build_general_insights_prompt

    if getattr(original, "_talena_shared_personality_grounding", False):
        return

    @wraps(original)
    def grounded_prompt(
        *,
        candidate_name: str,
        insight_input: dict[str, Any],
        language_code: str = "en",
    ):
        language_code = _language(language_code)
        prompt = original(
            candidate_name=candidate_name,
            insight_input=insight_input,
            language_code=language_code,
        )
        grounding = build_personality_ai_evidence_text(
            _general_insight_personality_rows(insight_input),
            language_code=language_code,
        )

        return _insert_before_marker(
            prompt,
            grounding,
            "\n\nReturn valid JSON only.",
        )

    grounded_prompt._talena_shared_personality_grounding = True
    candidate_insights.build_general_insights_prompt = grounded_prompt


def install_shared_personality_grounding_policy() -> None:
    """
    Use one approved personality-definition evidence layer across active AI flows.

    AI Overview and pre-interview decision support share purpose_fit's normalized
    raw assessment evidence. The other consumers have independent prompt inputs,
    so the same shared builder is inserted at their prompt boundary without
    changing any saved-result/output schema.
    """

    global _INSTALLED

    if _INSTALLED:
        return

    from apps.core.ai import candidate_summary
    from apps.core.ai import decision_support
    from apps.core.ai import personality_interpretation
    from apps.core.ai import purpose_fit
    from apps.reports.services import candidate_insights

    # Shared raw evidence path used by AI Overview and by the pre-interview raw
    # assessment policy. A language context keeps the definitions localized for
    # the actual AI call without changing the legacy builder signature.
    _install_assessment_evidence_grounding(purpose_fit)
    _install_language_context_wrapper(
        purpose_fit,
        "build_purpose_fit_prompt",
    )
    _install_language_context_wrapper(
        decision_support,
        "build_pre_interview_decision_support_prompt",
    )

    _install_personality_interpretation_grounding(
        personality_interpretation
    )
    _install_candidate_summary_grounding(candidate_summary)
    _install_general_insights_grounding(candidate_insights)

    _INSTALLED = True
