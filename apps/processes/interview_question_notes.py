from __future__ import annotations

import hashlib
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from .interview_question_models import InterviewQuestionNote
from .models import (
    HistoricalProcessCandidate,
    TestInvitation,
    TestProcess,
)


QUESTION_SOURCES = {
    "personality": (
        "ai_personality_questions",
    ),
    "motivation": (
        "ai_motivation_questions",
        "ai_motivation_interpretation",
    ),
    "cognitive": (
        "ai_cognitive_questions",
        "ai_cognitive_interpretation",
    ),
}


def interview_question_key(source: str, question: str) -> str:
    value = f"{source}\x00{question.strip()}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def get_candidate_question_owner(process, candidate_id):
    if process.is_historical:
        return get_object_or_404(
            HistoricalProcessCandidate.objects.select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    return get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )


def _question_texts_from_result(result) -> set[str]:
    if not isinstance(result, dict):
        return set()

    raw_questions = result.get("questions") or []
    if not isinstance(raw_questions, list):
        return set()

    questions = set()

    for item in raw_questions:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = str(item.get("question") or "").strip()
        else:
            text = ""

        if text:
            questions.add(text)

    return questions


def get_current_question_texts(owner, source: str) -> set[str]:
    field_names = QUESTION_SOURCES.get(source) or ()
    questions = set()

    for field_name in field_names:
        result = getattr(owner, field_name, {}) or {}
        questions.update(_question_texts_from_result(result))

    return questions


def serialize_interview_question_note(note: InterviewQuestionNote) -> dict:
    updated_by = ""
    if note.updated_by:
        updated_by = (
            note.updated_by.get_full_name()
            or note.updated_by.get_username()
        )

    return {
        "id": note.id,
        "source": note.source,
        "source_label": note.get_source_display(),
        "question_key": note.question_key,
        "question": note.question_text,
        "note": note.note,
        "updated_at": note.updated_at.isoformat(),
        "updated_by": updated_by,
    }


@login_required
@require_GET
def process_candidate_interview_question_notes(
    request,
    process_id,
    candidate_id,
):
    process = get_object_or_404(TestProcess, pk=process_id)
    owner = get_candidate_question_owner(process, candidate_id)

    notes = (
        InterviewQuestionNote.objects
        .filter(
            process=process,
            candidate=owner.candidate,
        )
        .select_related("updated_by")
        .order_by("source", "created_at", "id")
    )

    return JsonResponse(
        {
            "ok": True,
            "notes": [
                serialize_interview_question_note(note)
                for note in notes
                if (note.note or "").strip()
            ],
        }
    )


@login_required
@require_POST
def process_candidate_interview_question_note_update(
    request,
    process_id,
    candidate_id,
):
    process = get_object_or_404(TestProcess, pk=process_id)
    owner = get_candidate_question_owner(process, candidate_id)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON payload."},
            status=400,
        )

    source = str(payload.get("source") or "").strip().lower()
    question = str(payload.get("question") or "").strip()
    raw_note = payload.get("note", "")

    if source not in QUESTION_SOURCES:
        return JsonResponse(
            {"error": "Unknown interview question source."},
            status=400,
        )

    if not question or len(question) > 6000:
        return JsonResponse(
            {"error": "A valid interview question is required."},
            status=400,
        )

    if raw_note is None:
        raw_note = ""

    if not isinstance(raw_note, str):
        return JsonResponse(
            {"error": "The interview question note must be text."},
            status=400,
        )

    note_text = raw_note.strip()

    if len(note_text) > 5000:
        return JsonResponse(
            {
                "error": (
                    "An interview question note may not exceed "
                    "5,000 characters."
                )
            },
            status=400,
        )

    current_questions = get_current_question_texts(owner, source)

    if question not in current_questions:
        return JsonResponse(
            {
                "error": (
                    "This question is no longer part of the candidate's "
                    "current generated interview questions. Refresh the "
                    "candidate view and try again."
                )
            },
            status=409,
        )

    question_key = interview_question_key(source, question)

    if note_text:
        note, _created = InterviewQuestionNote.objects.update_or_create(
            process=process,
            candidate=owner.candidate,
            source=source,
            question_key=question_key,
            defaults={
                "question_text": question,
                "note": note_text,
                "updated_by": request.user,
            },
        )
        saved_note = serialize_interview_question_note(note)
    else:
        InterviewQuestionNote.objects.filter(
            process=process,
            candidate=owner.candidate,
            source=source,
            question_key=question_key,
        ).delete()
        saved_note = {
            "source": source,
            "question_key": question_key,
            "question": question,
            "note": "",
        }

    # Question-level evidence changes the evidence available to any existing
    # post-interview synthesis, so make that state explicit immediately.
    if owner.ai_post_interview_decision_support:
        post_interview_status = "outdated"
    else:
        post_interview_status = "not_started"

    owner.ai_post_interview_decision_support_status = post_interview_status
    owner.save(
        update_fields=[
            "ai_post_interview_decision_support_status",
        ]
    )

    return JsonResponse(
        {
            "ok": True,
            "note": saved_note,
            "has_note": bool(note_text),
            "post_interview_status": post_interview_status,
        }
    )
