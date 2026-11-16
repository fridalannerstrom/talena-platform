"""Compare actual interview evidence with the inputs used for generated reports.

A content digest, rather than a timestamp or a sticky "outdated" flag, lets
an unchanged or restored answer remain current. Only the digest is persisted,
never a second copy of sensitive candidate interview notes.
"""
from __future__ import annotations

import hashlib
import json

from django.db.models import Max

from .interview_question_models import InterviewQuestionNote

EVIDENCE_DIGESTS_KEY = "interview_evidence_digests"


def interview_evidence_digest(owner, process=None) -> str:
    """Stable hash of general notes and non-empty saved question answers."""
    process = process or owner.process
    answers = list(
        InterviewQuestionNote.objects.filter(
            process=process, candidate=owner.candidate
        )
        .exclude(note="")
        .order_by("source", "question_key", "note")
        .values_list("source", "question_key", "note")
    )
    evidence = {
        "notes": (owner.interview_notes or "").strip(),
        "answers": answers,
    }
    serialized = json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def stamp_report_evidence(result: dict, owner, part: str) -> dict:
    """Record the inputs of one successfully generated, independent part."""
    if part not in {"overall_picture", "wellbeing_tips", "manager_personality"}:
        raise ValueError("Unknown post-interview report part.")
    result = dict(result)
    digests = dict(result.get(EVIDENCE_DIGESTS_KEY) or {})
    digests[part] = interview_evidence_digest(owner)
    result[EVIDENCE_DIGESTS_KEY] = digests
    return result


def _report_parts(owner, result: dict) -> list[str]:
    blocks = result.get("content_blocks") or {}
    parts = []
    if str(blocks.get("overall_picture") or result.get("overall_synthesis") or "").strip():
        parts.append("overall_picture")
    if str(blocks.get("wellbeing_tips") or "").strip():
        parts.append("wellbeing_tips")
    personality = owner.ai_manager_report_personality or {}
    if any(
        str(value or "").strip()
        for theme in personality.values()
        if isinstance(theme, dict)
        for value in theme.values()
    ):
        parts.append("manager_personality")
    return parts


def post_interview_evidence_changed(owner, process=None) -> bool:
    """True only if evidence differs from an existing report part's inputs.

    Reports predating the digest feature retain timestamp-based fallback
    until that particular part is regenerated.
    """
    result = owner.ai_post_interview_decision_support or {}
    parts = _report_parts(owner, result)
    if not parts:
        return False

    digests = result.get(EVIDENCE_DIGESTS_KEY) or {}
    current_digest = interview_evidence_digest(owner, process)
    legacy_parts = False
    for part in parts:
        original_digest = digests.get(part)
        if original_digest:
            if original_digest != current_digest:
                return True
        else:
            legacy_parts = True

    # A legacy status bit is not authoritative for any part that now has a
    # content snapshot. Once all parts have snapshots, only content can warn.
    if not legacy_parts:
        return False
    if result.get("interview_evidence_changed_since_compilation") is True:
        return True

    if (
        owner.interview_notes_updated_at
        and (
            not owner.ai_post_interview_decision_support_notes_version
            or owner.interview_notes_updated_at
            > owner.ai_post_interview_decision_support_notes_version
        )
    ):
        return True

    latest_question_note = (
        InterviewQuestionNote.objects.filter(
            process=process or owner.process, candidate=owner.candidate
        )
        .aggregate(latest=Max("updated_at"))
        .get("latest")
    )
    generated_at = owner.ai_post_interview_decision_support_generated_at
    return bool(
        latest_question_note
        and (not generated_at or latest_question_note > generated_at)
    )
