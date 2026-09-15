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


def augment_assessment_text_with_personality_grounding(
    assessment_text: str,
    owner,
    *,
    language_code: str = "en",
) -> str:
    """Append compact candidate-specific personality summaries to raw evidence."""

    grounding = build_owner_personality_ai_evidence_text(
        owner,
        language_code=_language(language_code),
        include_indicator_details=False,
    )

    if not grounding:
        return str(assessment_text or "").strip()

    existing = str(assessment_text or "").rstrip()
    return f"{existing}\n\n{grounding}" if existing else grounding


def augment_owner_prompt_with_personality_grounding(
    prompt: str,
    owner,
    *,
    language_code: str,
    marker: str,
    include_indicator_details: bool = False,
) -> str:
    grounding = build_owner_personality_ai_evidence_text(
        owner,
        language_code=_language(language_code),
        include_indicator_details=include_indicator_details,
    )
    return _insert_before_marker(prompt, grounding, marker)


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


def augment_general_insights_prompt_with_personality_grounding(
    prompt: str,
    insight_input: dict[str, Any],
    *,
    language_code: str,
) -> str:
    grounding = build_personality_ai_evidence_text(
        _general_insight_personality_rows(insight_input),
        language_code=_language(language_code),
        include_indicator_details=False,
    )
    return _insert_before_marker(
        prompt,
        grounding,
        "\n\nReturn valid JSON only.",
    )


def _install_assessment_evidence_grounding(purpose_fit) -> None:
    original_builder = purpose_fit.build_assessment_evidence

    if getattr(original_builder, "_talena_shared_personality_grounding", False):
        return

    @wraps(original_builder)
    def grounded_assessment_evidence(invitation):
        assessment_text, assessment_type_count = original_builder(invitation)

        assessment_text = augment_assessment_text_with_personality_grounding(
            assessment_text,
            invitation,
            language_code=_PERSONALITY_GROUNDING_LANGUAGE.get(),
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

        # Personality Interpretation is the most detailed whole-profile consumer.
        # Give it indicator-level nuance as well as the parent-trait summaries.
        return augment_owner_prompt_with_personality_grounding(
            prompt,
            owner,
            language_code=language_code,
            marker="\n\nADMINISTRATOR AI GUIDANCE",
            include_indicator_details=True,
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

        return augment_owner_prompt_with_personality_grounding(
            prompt,
            owner,
            language_code=language_code,
            marker="\n\nINTERPRETATION INSTRUCTION",
            include_indicator_details=False,
        )

    grounded_prompt._talena_shared_personality_grounding = True
    candidate_summary.build_candidate_prompt = grounded_prompt


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

        return augment_general_insights_prompt_with_personality_grounding(
            prompt,
            insight_input,
            language_code=language_code,
        )

    grounded_prompt._talena_shared_personality_grounding = True
    candidate_insights.build_general_insights_prompt = grounded_prompt


def install_shared_personality_grounding_policy() -> None:
    """
    Reuse Talena's candidate-specific Result Summary semantics across AI flows.

    AI Overview and pre-interview decision support share purpose_fit's normalized
    raw assessment evidence. Personality Interpretation, Candidate Summary and
    Flexible / General Insights receive the same shared evidence at their prompt
    boundary. No saved-result/output schema changes are required.
    """

    global _INSTALLED

    if _INSTALLED:
        return

    from apps.core.ai import candidate_summary
    from apps.core.ai import decision_support
    from apps.core.ai import personality_interpretation
    from apps.core.ai import purpose_fit
    from apps.reports.services import candidate_insights

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
