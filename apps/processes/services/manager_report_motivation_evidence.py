"""Source-faithful interview evidence for the manager report's Motivation section.

The report must not infer motivational preferences from unrelated notes, from
an assessment score, or from the wording of an unsorted legacy note. Only
explicitly categorised Motivation interview notes and saved answers to
Motivation questions are displayed. No AI call is made by this helper.
"""
from __future__ import annotations

import re

from apps.processes.interview_question_evidence import build_interview_question_evidence

# These headings are the persisted format used by interview-note-areas.js.
_SECTION_HEADING = re.compile(
    r"^### Intervjuunderlag: (Personlighet|Motivation|Färdighet)[ \t]*$",
    re.MULTILINE,
)


def _motivation_notes(notes: str) -> str:
    text = str(notes or "")
    headings = list(_SECTION_HEADING.finditer(text))
    if not headings:
        # Old free-form notes have no trustworthy category; never guess.
        return ""
    pieces: list[str] = []
    for index, match in enumerate(headings):
        if match.group(1) != "Motivation":
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        value = text[match.end():end].strip()
        if value:
            pieces.append(value)
    return "\n\n".join(pieces)


def build_manager_motivation_interview_evidence(owner) -> dict:
    """Return verbatim source notes and explicitly sourced question answers.

    The question remains attached to its saved answer. Missing source input
    yields an empty object so the report can render a neutral empty state.
    """
    notes = _motivation_notes(getattr(owner, "interview_notes", ""))
    answers = [
        {
            "question": item["question"],
            "answer": item["saved_answer_or_note"],
        }
        for item in build_interview_question_evidence(owner)["items"]
        if item.get("source") == "motivation"
        and str(item.get("question") or "").strip()
        and str(item.get("saved_answer_or_note") or "").strip()
    ]
    return {"notes": notes, "answers": answers}
