from __future__ import annotations

import hashlib
import json
import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import (
    HttpResponseForbidden,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .interview_question_models import InterviewQuestionNote
from .models import (
    HistoricalProcessCandidate,
    TestInvitation,
    TestProcess,
)


logger = logging.getLogger(__name__)


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


def normalize_question_text(value) -> str:
    """Use one stable representation for rendered and saved questions."""

    return " ".join(str(value or "").split())


def interview_question_key(source: str, question: str) -> str:
    normalized_source = str(source or "").strip().lower()
    normalized_question = normalize_question_text(question)
    value = f"{normalized_source}\x00{normalized_question}".encode("utf-8")
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
            text = normalize_question_text(item)
        elif isinstance(item, dict):
            text = normalize_question_text(item.get("question"))
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
    question = normalize_question_text(payload.get("question"))
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
    question_key = interview_question_key(source, question)
    existing_note = InterviewQuestionNote.objects.filter(
        process=process,
        candidate=owner.candidate,
        source=source,
        question_key=question_key,
    ).first()

    # A saved note remains editable/removable even when the interview
    # questions were regenerated afterwards. New notes still require a
    # question from the candidate's current generated question set.
    if question not in current_questions and existing_note is None:
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


def _post_interview_evidence_state(
    request,
    process_id,
    candidate_id,
):
    """Resolve the owner and the two valid forms of interview evidence."""

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    # Keep the canonical process-access rule from views.py without importing
    # views during URL-module initialisation.
    from .views import user_can_access_process

    if not user_can_access_process(
        request.user,
        process,
    ):
        return process, None, None, HttpResponseForbidden(
            "You do not have access to this process."
        )

    owner = get_candidate_question_owner(
        process,
        candidate_id,
    )

    from apps.core.ai.post_interview_question_evidence_policy import (
        get_post_interview_note_evidence,
    )

    evidence = get_post_interview_note_evidence(
        owner
    )

    if not evidence["has_evidence"]:
        return process, owner, evidence, JsonResponse(
            {
                "error": (
                    "Add and save interview evidence before generating "
                    "post-interview decision support. Interview evidence "
                    "may be general interview notes, saved answers or notes "
                    "on interview questions, or both."
                )
            },
            status=400,
        )

    return process, owner, evidence, None


@login_required
@require_GET
def process_candidate_post_interview_decision_support_stream_with_evidence(
    request,
    process_id,
    candidate_id,
):
    """Generate one After interview section, or all sections as separate calls."""

    process, owner, _evidence, error_response = (
        _post_interview_evidence_state(request, process_id, candidate_id)
    )
    if error_response is not None:
        return error_response
    if owner.status != "completed":
        return JsonResponse(
            {"error": "The candidate has not completed the assessments yet."},
            status=400,
        )

    from apps.core.ai.decision_support import (
        POST_INTERVIEW_CONTENT_BLOCK_KEYS,
        save_post_interview_content_block,
        set_post_interview_content_block_status,
        stream_post_interview_content_block,
    )
    from apps.core.ai.language import (
        ai_content_language_matches,
        get_request_ai_language,
        mark_ai_content_outdated_if_language_changed,
    )
    from .purpose_utils import normalize_purpose_key

    language_code = get_request_ai_language(request)
    block_key = str(request.GET.get("block") or "").strip()
    if block_key and block_key not in POST_INTERVIEW_CONTENT_BLOCK_KEYS:
        return JsonResponse({"error": "Unknown After interview section."}, status=400)

    mark_ai_content_outdated_if_language_changed(
        owner,
        content_key="post_interview_decision_support",
        result_field="ai_post_interview_decision_support",
        status_field="ai_post_interview_decision_support_status",
        language_code=language_code,
    )

    current_status = owner.ai_post_interview_decision_support_status or "not_started"
    saved_result = owner.ai_post_interview_decision_support or {}
    saved_blocks = saved_result.get("content_blocks") or {}
    current_purpose = normalize_purpose_key(process.purpose)
    saved_purpose = normalize_purpose_key(
        owner.ai_post_interview_decision_support_purpose
    )
    current_notes_version = owner.interview_notes_updated_at
    saved_notes_version = owner.ai_post_interview_decision_support_notes_version
    latest_question_note = (
        InterviewQuestionNote.objects
        .filter(process=process, candidate=owner.candidate)
        .exclude(note="")
        .aggregate(latest=Max("updated_at"))
        .get("latest")
    )
    generated_at = owner.ai_post_interview_decision_support_generated_at

    evidence_changed = (
        saved_purpose != current_purpose
        or bool(
            current_notes_version
            and (
                not saved_notes_version
                or current_notes_version > saved_notes_version
            )
        )
        or bool(
            latest_question_note
            and saved_result
            and (not generated_at or latest_question_note > generated_at)
        )
    )
    if saved_result and evidence_changed and current_status == "completed":
        current_status = "outdated"
        owner.ai_post_interview_decision_support_status = "outdated"
        saved_result = dict(saved_result)
        statuses = dict(saved_result.get("content_block_statuses") or {})
        for key in POST_INTERVIEW_CONTENT_BLOCK_KEYS:
            if str(saved_blocks.get(key) or "").strip():
                statuses[key] = "outdated"
        saved_result["content_block_statuses"] = statuses
        owner.ai_post_interview_decision_support = saved_result
        owner.save(update_fields=[
            "ai_post_interview_decision_support",
            "ai_post_interview_decision_support_status",
        ])

    if current_status == "outdated" and saved_result:
        statuses = dict(saved_result.get("content_block_statuses") or {})
        changed = False
        for key in POST_INTERVIEW_CONTENT_BLOCK_KEYS:
            if str(saved_blocks.get(key) or "").strip() and statuses.get(key) != "outdated":
                statuses[key] = "outdated"
                changed = True
        if changed:
            saved_result = dict(saved_result)
            saved_result["content_block_statuses"] = statuses
            owner.ai_post_interview_decision_support = saved_result
            owner.save(update_fields=["ai_post_interview_decision_support"])

    force = request.GET.get("force") == "1"
    selected_keys = [block_key] if block_key else list(POST_INTERVIEW_CONTENT_BLOCK_KEYS)
    blocks_ready = all(str(saved_blocks.get(key) or "").strip() for key in selected_keys)
    if (
        not force
        and current_status == "completed"
        and blocks_ready
        and ai_content_language_matches(
            owner, "post_interview_decision_support", language_code
        )
    ):
        def existing_generator():
            yield json.dumps(
                {"type": "saved_result", "data": saved_result, "status": current_status},
                ensure_ascii=False,
            ) + "\n"
        response = StreamingHttpResponse(
            existing_generator(),
            content_type="application/x-ndjson; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    if current_status == "generating":
        return JsonResponse(
            {"error": "After interview content is already being generated."},
            status=409,
        )

    if not saved_result or not str(saved_result.get("overall_synthesis") or "").strip():
        owner.ai_post_interview_decision_support_status = "generating"
        owner.save(update_fields=["ai_post_interview_decision_support_status"])

    result_holder = {
        "completed_blocks": [],
        "failed_blocks": [],
    }

    def generator():
        nonlocal saved_result
        errors = []
        try:
            for key in selected_keys:
                current_blocks = (
                    (owner.ai_post_interview_decision_support or {}).get("content_blocks")
                    or {}
                )
                current_statuses = (
                    (owner.ai_post_interview_decision_support or {}).get(
                        "content_block_statuses"
                    )
                    or {}
                )
                already_ready = (
                    str(current_blocks.get(key) or "").strip()
                    and current_statuses.get(
                        key,
                        "completed" if current_status == "completed" else "not_started",
                    ) == "completed"
                    and current_status != "outdated"
                )
                if already_ready and not force:
                    result_holder["completed_blocks"].append(key)
                    yield json.dumps(
                        {"type": "content_block_skipped", "block": key},
                        ensure_ascii=False,
                    ) + "\n"
                    continue

                yield json.dumps(
                    {"type": "content_block_started", "block": key},
                    ensure_ascii=False,
                ) + "\n"
                chunks = []
                try:
                    for event in stream_post_interview_content_block(
                        owner=owner,
                        block_key=key,
                        language_code=language_code,
                    ):
                        if event.get("type") == "content_block_delta":
                            chunks.append(str(event.get("text") or ""))
                        yield json.dumps(event, ensure_ascii=False) + "\n"

                    generated_text = "".join(chunks).strip()
                    save_post_interview_content_block(
                        owner=owner,
                        block_key=key,
                        text=generated_text,
                        language_code=language_code,
                    )
                    result_holder["completed_blocks"].append(key)
                    yield json.dumps(
                        {"type": "content_block_complete", "block": key},
                        ensure_ascii=False,
                    ) + "\n"
                except Exception as block_error:
                    logger.exception(
                        "After interview section failed (process_id=%s, candidate_id=%s, block=%s)",
                        process.id,
                        candidate_id,
                        key,
                    )
                    errors.append((key, str(block_error)))
                    set_post_interview_content_block_status(
                        owner=owner,
                        block_key=key,
                        status="failed",
                    )
                    result_holder["failed_blocks"].append(key)
                    yield json.dumps(
                        {
                            "type": "content_block_error",
                            "block": key,
                            "message": str(block_error),
                        },
                        ensure_ascii=False,
                    ) + "\n"

            stored_owner = type(owner).objects.get(pk=owner.pk)
            final_result = stored_owner.ai_post_interview_decision_support or {}
            final_blocks = final_result.get("content_blocks") or {}
            final_statuses = final_result.get("content_block_statuses") or {}
            all_complete = all(
                str(final_blocks.get(key) or "").strip()
                and final_statuses.get(
                    key,
                    "completed" if current_status == "completed" else "not_started",
                ) == "completed"
                for key in POST_INTERVIEW_CONTENT_BLOCK_KEYS
            )
            if all_complete:
                stored_owner.ai_post_interview_decision_support_status = "completed"
                stored_owner.ai_post_interview_decision_support_generated_at = timezone.now()
                stored_owner.ai_post_interview_decision_support_purpose = current_purpose
                stored_owner.ai_post_interview_decision_support_notes_version = (
                    stored_owner.interview_notes_updated_at or timezone.now()
                )
                stored_owner.save(update_fields=[
                    "ai_post_interview_decision_support_status",
                    "ai_post_interview_decision_support_generated_at",
                    "ai_post_interview_decision_support_purpose",
                    "ai_post_interview_decision_support_notes_version",
                ])
            elif errors:
                stored_owner.ai_post_interview_decision_support_status = "failed"
                stored_owner.save(update_fields=[
                    "ai_post_interview_decision_support_status",
                ])
            yield json.dumps(
                {
                    "type": "generation_complete",
                    "completed_blocks": result_holder["completed_blocks"],
                    "failed_blocks": result_holder["failed_blocks"],
                    "all_complete": all_complete,
                },
                ensure_ascii=False,
            ) + "\n"
            if errors:
                yield json.dumps(
                    {
                        "type": "generation_partial_error",
                        "message": "One or more After interview sections could not be generated.",
                    },
                    ensure_ascii=False,
                ) + "\n"
        except Exception as error:
            logger.exception(
                "After interview generation failed (process_id=%s, candidate_id=%s)",
                process.id,
                candidate_id,
            )
            owner.ai_post_interview_decision_support_status = "failed"
            owner.save(update_fields=["ai_post_interview_decision_support_status"])
            yield json.dumps(
                {"type": "error", "message": str(error)},
                ensure_ascii=False,
            ) + "\n"

    response = StreamingHttpResponse(
        generator(),
        content_type="application/x-ndjson; charset=utf-8",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response

@login_required
@require_POST
def process_candidate_post_interview_decision_support_regenerate_with_evidence(
    request,
    process_id,
    candidate_id,
):
    """Reset After interview when free text, question notes or both exist."""

    process, owner, _evidence, error_response = (
        _post_interview_evidence_state(
            request,
            process_id,
            candidate_id,
        )
    )

    if error_response is not None:
        return error_response

    from apps.core.ai.decision_support import POST_INTERVIEW_CONTENT_BLOCK_KEYS

    block_key = str(request.GET.get("block") or "").strip()
    if block_key and block_key not in POST_INTERVIEW_CONTENT_BLOCK_KEYS:
        return JsonResponse({"error": "Unknown After interview section."}, status=400)

    if block_key:
        from apps.core.ai.decision_support import (
            set_post_interview_content_block_status,
        )
        set_post_interview_content_block_status(
            owner=owner,
            block_key=block_key,
            status="generating",
        )
    else:
        owner.ai_post_interview_decision_support_status = "not_started"
        owner.ai_post_interview_decision_support_generated_at = None
        owner.ai_post_interview_decision_support_purpose = ""
        owner.ai_post_interview_decision_support_notes_version = None
        owner.save(
            update_fields=[
                "ai_post_interview_decision_support_status",
                "ai_post_interview_decision_support_generated_at",
                "ai_post_interview_decision_support_purpose",
                "ai_post_interview_decision_support_notes_version",
            ]
        )

    stream_url = reverse(
        (
            "processes:"
            "process_candidate_post_interview_"
            "decision_support_stream"
        ),
        kwargs={
            "process_id": process.id,
            "candidate_id": candidate_id,
        },
    )
    if block_key:
        stream_url += f"?block={block_key}&force=1"
    else:
        stream_url += "?force=1"

    return JsonResponse({"ok": True, "stream_url": stream_url})
