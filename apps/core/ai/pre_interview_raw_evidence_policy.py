from __future__ import annotations

from functools import wraps
from typing import Any


_INSTALLED = False
RAW_ASSESSMENT_SOURCE_LABEL = "Assessment results"


def augment_pre_interview_evidence(
    evidence: dict[str, Any],
    *,
    raw_assessment_text: str,
    assessment_type_count: int,
) -> dict[str, Any]:
    """
    Add normalized raw assessment results to the evidence used by
    pre-interview decision support.

    The existing saved Talena interpretations remain available. Raw results are
    added alongside them so the final synthesis can reason from the candidate's
    actual profile instead of only summarising earlier AI summaries.
    """

    result = dict(evidence or {})
    raw_text = str(raw_assessment_text or "").strip()

    if not raw_text or assessment_type_count <= 0:
        return result

    existing_text = str(result.get("evidence_text") or "").strip()

    raw_section = "\n".join(
        [
            f"SOURCE: {RAW_ASSESSMENT_SOURCE_LABEL}",
            "STATUS: completed",
            "Normalized raw assessment results:",
            raw_text,
        ]
    )

    result["evidence_text"] = (
        f"{raw_section}\n\n{existing_text}"
        if existing_text
        else raw_section
    )

    source_names = list(result.get("source_names") or [])
    if RAW_ASSESSMENT_SOURCE_LABEL not in source_names:
        source_names.insert(0, RAW_ASSESSMENT_SOURCE_LABEL)

    result["source_names"] = source_names
    result["source_count"] = len(source_names)
    result["has_evidence"] = True
    result["raw_assessment_text"] = raw_text
    result["raw_assessment_type_count"] = assessment_type_count

    return result


def install_pre_interview_raw_evidence_policy() -> None:
    """Feed real assessment results into production pre-interview synthesis."""

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import decision_support

    original_builder = decision_support.build_pre_interview_evidence

    @wraps(original_builder)
    def evidence_with_raw_results(owner, *, language_code=None):
        evidence = original_builder(
            owner,
            language_code=language_code,
        )

        # Import lazily to avoid widening the AI module import graph at startup.
        from apps.core.ai.purpose_fit import build_assessment_evidence

        raw_text, assessment_type_count = build_assessment_evidence(owner)

        return augment_pre_interview_evidence(
            evidence,
            raw_assessment_text=raw_text,
            assessment_type_count=assessment_type_count,
        )

    decision_support.build_pre_interview_evidence = evidence_with_raw_results
    _INSTALLED = True
