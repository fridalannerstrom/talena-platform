from __future__ import annotations

import json
from typing import Any

from .interview_question_models import InterviewQuestionNote


SOURCE_LABELS = {
    "personality": "Personality",
    "motivation": "Motivation",
    "cognitive": "Cognitive",
}


def build_interview_question_evidence(owner) -> dict[str, Any]:
    """
    Build structured interview evidence from notes saved on generated questions.

    Keep the exact saved question together with its answer/note. The post-
    interview AI must never receive a detached note without knowing which
    question it belongs to.
    """

    notes = (
        InterviewQuestionNote.objects
        .filter(
            process=owner.process,
            candidate=owner.candidate,
        )
        .exclude(note="")
        .order_by("source", "created_at", "id")
    )

    items = []

    for saved_note in notes:
        question = str(saved_note.question_text or "").strip()
        note = str(saved_note.note or "").strip()

        if not question or not note:
            continue

        source = str(saved_note.source or "").strip().lower()

        items.append(
            {
                "source": source,
                "source_label": SOURCE_LABELS.get(
                    source,
                    saved_note.get_source_display() or source,
                ),
                "question": question,
                "saved_answer_or_note": note,
            }
        )

    text = (
        json.dumps(
            items,
            ensure_ascii=False,
            indent=2,
        )
        if items
        else ""
    )

    return {
        "items": items,
        "text": text,
        "count": len(items),
        "has_evidence": bool(items),
    }
