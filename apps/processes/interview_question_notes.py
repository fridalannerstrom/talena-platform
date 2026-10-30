from __future__ import annotations

import hashlib
import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
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

from .interview_note_privacy import contains_interview_note_personal_data
from .access_control import process_edit_access_required, process_view_access_required
from .interview_question_models import (
    InterviewQuestionNote,
    ManagerReportTextEdit,
    ManagerReportTextEditEvent,
)
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

MANAGER_REPORT_TEXT_MAX_LENGTH = 30000
MANAGER_REPORT_PERSONALITY_THEMES = {
    "leading_and_working_with_others",
    "organising_and_thinking_patterns",
    "interaction_and_emotion_management",
}
MANAGER_REPORT_PERSONALITY_PARTS = {"testbild", "candidate_describes"}


def manager_report_edit_block_is_allowed(block_key: str) -> bool:
    if block_key == "wellbeing_tips":
        return True

    parts = str(block_key or "").split(":")
    return (
        len(parts) == 3
        and parts[0] == "personality"
        and parts[1] in MANAGER_REPORT_PERSONALITY_THEMES
        and parts[2] in MANAGER_REPORT_PERSONALITY_PARTS
    )


def _manager_report_ai_text(owner, block_key: str) -> str:
    if block_key == "wellbeing_tips":
        result = owner.ai_post_interview_decision_support or {}
        return str(
            ((result.get("content_blocks") or {}).get("wellbeing_tips")) or ""
        )

    _prefix, theme, part = block_key.split(":")
    result = owner.ai_personality_interpretation or {}
    report = result.get("manager_report_personality") or {}
    return str(((report.get(theme) or {}).get(part)) or "")


def _manager_report_source_generated_at(owner, block_key: str):
    if block_key == "wellbeing_tips":
        return owner.ai_post_interview_decision_support_generated_at
    return owner.ai_personality_interpretation_generated_at


def _serialize_manager_report_text_edit(edit: ManagerReportTextEdit) -> dict:
    return {
        "block_key": edit.block_key,
        "text": edit.text,
        "version": edit.version,
        "updated_at": edit.updated_at.isoformat(),
    }


@login_required
@process_view_access_required
@require_GET
def process_candidate_manager_report_text_edits(request, process_id, candidate_id):
    process = get_object_or_404(TestProcess, pk=process_id)
    owner = get_candidate_question_owner(process, candidate_id)
    from apps.core.ai.language import get_request_ai_language

    language_code = get_request_ai_language(request)
    edits = (
        ManagerReportTextEdit.objects
        .filter(
            process=process,
            candidate=owner.candidate,
            language_code=language_code,
        )
        .order_by("block_key")
    )
    response = JsonResponse({
        "ok": True,
        "language": language_code,
        "edits": [
            _serialize_manager_report_text_edit(edit)
            for edit in edits
        ],
    })
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@process_edit_access_required
@require_POST
def process_candidate_manager_report_text_edit_update(
    request,
    process_id,
    candidate_id,
):
    process = get_object_or_404(TestProcess, pk=process_id)
    owner = get_candidate_question_owner(process, candidate_id)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    block_key = str(payload.get("block_key") or "").strip()
    if not manager_report_edit_block_is_allowed(block_key):
        return JsonResponse({"error": "This report block cannot be edited."}, status=400)

    from apps.core.ai.language import get_request_ai_language

    language_code = str(payload.get("language") or "").strip().lower()
    if language_code not in {"sv", "en"} or language_code != get_request_ai_language(request):
        return JsonResponse({"error": "The report language does not match this page."}, status=400)

    action = str(payload.get("action") or "save").strip().lower()
    if action not in {"save", "restore_ai"}:
        return JsonResponse({"error": "Unknown edit action."}, status=400)

    expected_version = payload.get("expected_version")
    if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 0:
        return JsonResponse({"error": "A valid edit version is required."}, status=400)

    text = payload.get("text", "")
    if action == "save":
        if not isinstance(text, str):
            return JsonResponse({"error": "Report text must be plain text."}, status=400)
        if len(text) > MANAGER_REPORT_TEXT_MAX_LENGTH:
            return JsonResponse(
                {"error": "Report text may not exceed 30,000 characters."},
                status=400,
            )

    lookup = {
        "process": process,
        "candidate": owner.candidate,
        "block_key": block_key,
        "language_code": language_code,
    }
    with transaction.atomic():
        owner = type(owner).objects.select_for_update().get(pk=owner.pk)
        edit = ManagerReportTextEdit.objects.select_for_update().filter(**lookup).first()
        current_version = edit.version if edit else 0
        if expected_version != current_version:
            response = JsonResponse(
                {
                    "error": "This text was changed in another session. Refresh and try again.",
                    "edit": _serialize_manager_report_text_edit(edit) if edit else None,
                },
                status=409,
            )
            response["Cache-Control"] = "private, no-store"
            return response

        if action == "restore_ai":
            if edit is None:
                response = JsonResponse({"ok": True, "restored": False, "edit": None})
            else:
                ManagerReportTextEditEvent.objects.create(
                    process=process,
                    candidate=owner.candidate,
                    actor=request.user,
                    block_key=block_key,
                    language_code=language_code,
                    action=ManagerReportTextEditEvent.Action.RESTORED_AI,
                    version=edit.version,
                    source_generated_at=_manager_report_source_generated_at(owner, block_key),
                )
                edit.delete()
                response = JsonResponse({"ok": True, "restored": True, "edit": None})
            response["Cache-Control"] = "private, no-store"
            return response

        if edit is None and not _manager_report_ai_text(owner, block_key).strip():
            return JsonResponse(
                {"error": "This report block has no generated text to edit yet."},
                status=409,
            )

        if edit is None:
            edit = ManagerReportTextEdit.objects.create(
                **lookup,
                text=text,
                version=1,
                updated_by=request.user,
            )
        else:
            edit.text = text
            edit.version += 1
            edit.updated_by = request.user
            edit.save(update_fields=["text", "version", "updated_by", "updated_at"])

        ManagerReportTextEditEvent.objects.create(
            process=process,
            candidate=owner.candidate,
            actor=request.user,
            block_key=block_key,
            language_code=language_code,
            action=ManagerReportTextEditEvent.Action.SAVED,
            version=edit.version,
            source_generated_at=_manager_report_source_generated_at(owner, block_key),
        )

    response = JsonResponse({
        "ok": True,
        "edit": _serialize_manager_report_text_edit(edit),
    })
    response["Cache-Control"] = "private, no-store"
    return response


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

    # Inform the customer without blocking legitimate interview documentation.
    # Detection is conservative and only the boolean flag is returned: the
    # user's original note is stored as entered and remains subject to Talena's
    # separate sanitization at the outbound AI boundary.
    possible_personal_data = bool(note_text) and (
        contains_interview_note_personal_data(note_text, owner.candidate)
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
            "possible_personal_data": possible_personal_data,
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


def _manager_report_personality_events(owner, language_code, *, force=False):
    """Generate the manager-report personality content as part of compilation."""
    import time

    from apps.core.ai.language import ai_content_language_matches
    from apps.core.ai.personality_interpretation import (
        PERSONALITY_MANAGER_REPORT_THEMES,
        apply_personality_interpretation_event,
        create_empty_personality_interpretation,
        save_personality_interpretation,
        stream_personality_interpretation,
    )
    from .purpose_utils import normalize_purpose_key
    from .views import build_personality_results_for_ai_owner

    owner = type(owner).objects.get(pk=owner.pk)
    personality_results = build_personality_results_for_ai_owner(owner)
    if not personality_results:
        yield {"type": "manager_report_personality_skipped", "reason": "no_results"}
        return

    # Another view may already be generating this same interpretation (for
    # example, when the Personality tab was opened first). Wait for that
    # request to finish rather than starting a competing AI call.
    if owner.ai_personality_interpretation_status == "generating":
        yield {"type": "manager_report_personality_waiting"}
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            time.sleep(0.5)
            owner = type(owner).objects.get(pk=owner.pk)
            if owner.ai_personality_interpretation_status != "generating":
                break
        if owner.ai_personality_interpretation_status == "generating":
            yield {
                "type": "manager_report_personality_error",
                "message": "Personality content is still being generated.",
            }
            return

    saved = owner.ai_personality_interpretation or {}
    report_texts = saved.get("manager_report_personality") or {}
    expected = {
        (theme["key"], part)
        for theme in PERSONALITY_MANAGER_REPORT_THEMES
        for part in ("testbild", "candidate_describes")
    }
    has_all_report_texts = all(
        str((report_texts.get(theme) or {}).get(part) or "").strip()
        for theme, part in expected
    )
    if (
        not force
        and owner.ai_personality_interpretation_status == "completed"
        and saved.get("manager_report_personality_schema_version") == 1
        and has_all_report_texts
        and ai_content_language_matches(
            owner, "personality_interpretation", language_code
        )
        and normalize_purpose_key(owner.ai_personality_interpretation_purpose)
        == normalize_purpose_key(owner.process.purpose)
    ):
        yield {"type": "manager_report_personality_skipped", "reason": "up_to_date"}
        return

    owner.ai_personality_interpretation_status = "generating"
    owner.save(update_fields=["ai_personality_interpretation_status"])
    interpretation = create_empty_personality_interpretation(
        owner, language_code=language_code
    )
    received_done_event = False
    received_report_texts = set()

    try:
        yield {"type": "manager_report_personality_started"}
        for event in stream_personality_interpretation(
            owner=owner,
            personality_results=personality_results,
            language_code=language_code,
        ):
            interpretation = apply_personality_interpretation_event(
                interpretation, event
            )
            if event.get("type") == "done":
                received_done_event = True
            elif event.get("type") == "personality_report_text":
                received_report_texts.add(
                    (event.get("theme"), event.get("part"))
                )
            yield event

        if received_report_texts != expected:
            raise ValueError(
                "The AI response did not contain all six manager-report personality texts."
            )
        if not str(interpretation.get("interpretation") or "").strip():
            raise ValueError(
                "The AI response did not contain a personality interpretation."
            )
        if not received_done_event:
            yield {"type": "done"}

        save_personality_interpretation(
            owner=owner,
            interpretation=interpretation,
            language_code=language_code,
        )
        yield {"type": "manager_report_personality_complete"}
    except Exception as error:
        logger.exception(
            "Manager report personality generation failed (owner_id=%s)",
            owner.pk,
        )
        owner.ai_personality_interpretation_status = "failed"
        owner.save(update_fields=["ai_personality_interpretation_status"])
        yield {
            "type": "manager_report_personality_error",
            "message": str(error),
        }


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
    structured = request.GET.get("structured") == "1"
    structured_section = str(request.GET.get("section") or "").strip()
    if structured_section and (
        not structured or structured_section not in ("skills", "motivation", "personality", "synthesis")
        or block_key != "overall_picture"
    ):
        return JsonResponse({"error": "Invalid structured report section."}, status=400)
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

    manager_personality_results = []
    manager_personality_ready = block_key != ""
    if not block_key:
        from apps.core.ai.personality_interpretation import (
            PERSONALITY_MANAGER_REPORT_THEMES,
        )
        from .views import build_personality_results_for_ai_owner

        mark_ai_content_outdated_if_language_changed(
            owner,
            content_key="personality_interpretation",
            result_field="ai_personality_interpretation",
            status_field="ai_personality_interpretation_status",
            language_code=language_code,
        )
        manager_personality_results = build_personality_results_for_ai_owner(owner)
        if not manager_personality_results:
            manager_personality_ready = True
        else:
            personality_result = owner.ai_personality_interpretation or {}
            personality_texts = personality_result.get("manager_report_personality") or {}
            manager_personality_ready = (
                owner.ai_personality_interpretation_status == "completed"
                and personality_result.get("manager_report_personality_schema_version") == 1
                and all(
                    str((personality_texts.get(theme["key"]) or {}).get(part) or "").strip()
                    for theme in PERSONALITY_MANAGER_REPORT_THEMES
                    for part in ("testbild", "candidate_describes")
                )
                and ai_content_language_matches(
                    owner, "personality_interpretation", language_code
                )
                and normalize_purpose_key(owner.ai_personality_interpretation_purpose)
                == current_purpose
                and not (
                    owner.ai_personality_interpretation_generated_at
                    and current_notes_version
                    and current_notes_version > owner.ai_personality_interpretation_generated_at
                )
                and not (
                    owner.ai_personality_interpretation_generated_at
                    and latest_question_note
                    and latest_question_note > owner.ai_personality_interpretation_generated_at
                )
            )

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
        from apps.core.ai.structured_overall_picture import mark_structured_sections_outdated
        mark_structured_sections_outdated(saved_result)
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
        from apps.core.ai.structured_overall_picture import mark_structured_sections_outdated
        saved_result = dict(saved_result)
        typed_language = (saved_result.get("overall_picture_structured") or {}).get("language")
        # Partial structured regenerations intentionally keep the global state
        # outdated. Do not invalidate a freshly completed section on every GET.
        if evidence_changed or (typed_language and typed_language != language_code):
            changed = mark_structured_sections_outdated(saved_result) or changed
        if changed:
            saved_result["content_block_statuses"] = statuses
            owner.ai_post_interview_decision_support = saved_result
            owner.save(update_fields=["ai_post_interview_decision_support"])

    force = request.GET.get("force") == "1"
    selected_keys = [block_key] if block_key else list(POST_INTERVIEW_CONTENT_BLOCK_KEYS)
    blocks_ready = all(str(saved_blocks.get(key) or "").strip() for key in selected_keys)
    if structured:
        blocks_ready = False  # Legacy Markdown does not prove the new typed report is current.
    if (
        not force
        and current_status == "completed"
        and blocks_ready
        and ai_content_language_matches(
            owner, "post_interview_decision_support", language_code
        )
        and manager_personality_ready
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

    if current_status == "generating" and not structured:
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
                if key == "overall_picture" and structured:
                    from apps.core.ai.structured_overall_picture import guarded_structured_overall_picture
                    yield json.dumps(
                        {"type": "content_block_started", "block": key},
                        ensure_ascii=False,
                    ) + "\n"
                    structured_failed = False
                    for event in guarded_structured_overall_picture(
                        owner, language_code=language_code,
                        category=structured_section or None, force=force,
                    ):
                        if event.get("type") in ("structured_item_error", "structured_section_error"):
                            structured_failed = True
                        if event.get("type") == "structured_result":
                            report_state = event.get("data") or {}
                            report_sections = report_state.get("sections") or {}
                            report_ready = (
                                report_sections.get("synthesis", {}).get("status") == "completed"
                                and all(
                                    report_sections.get(part, {}).get("status") in ("completed", "not_applicable")
                                    for part in ("skills", "motivation", "personality")
                                )
                            )
                            if report_ready:
                                markdown = str(event.get("markdown") or "").strip()
                                if markdown:
                                    save_post_interview_content_block(
                                        owner=owner, block_key=key,
                                        text=markdown, language_code=language_code,
                                    )
                                    # Keep the old four-block orchestration compatible.
                                    yield json.dumps(
                                        {"type": "content_block_delta", "block": key, "text": markdown},
                                        ensure_ascii=False,
                                    ) + "\n"
                            else:
                                if not structured_section:
                                    structured_failed = True
                                set_post_interview_content_block_status(
                                    owner=owner, block_key=key, status="outdated",
                                )
                                # Record the current input versions even for a partial
                                # structured rebuild. Its other sections stay stale,
                                # without repeatedly invalidating just-updated items.
                                version_owner = type(owner).objects.get(pk=owner.pk)
                                version_owner.ai_post_interview_decision_support_status = "outdated"
                                version_owner.ai_post_interview_decision_support_purpose = current_purpose
                                version_owner.ai_post_interview_decision_support_notes_version = (
                                    owner.interview_notes_updated_at or timezone.now()
                                )
                                version_owner.ai_post_interview_decision_support_generated_at = timezone.now()
                                version_owner.save(update_fields=[
                                    "ai_post_interview_decision_support_status",
                                    "ai_post_interview_decision_support_purpose",
                                    "ai_post_interview_decision_support_notes_version",
                                    "ai_post_interview_decision_support_generated_at",
                                ])
                        yield json.dumps(event, ensure_ascii=False) + "\n"
                    if structured_failed:
                        errors.append((key, "One or more Overall picture items failed."))
                        result_holder["failed_blocks"].append(key)
                    else:
                        result_holder["completed_blocks"].append(key)
                        yield json.dumps(
                            {"type": "content_block_complete", "block": key},
                            ensure_ascii=False,
                        ) + "\n"
                    continue
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

            manager_personality_status = "skipped"
            if not block_key and manager_personality_results:
                for event in _manager_report_personality_events(
                    owner,
                    language_code,
                    force=force,
                ):
                    if event.get("type") == "manager_report_personality_complete":
                        manager_personality_status = "completed"
                    elif event.get("type") == "manager_report_personality_error":
                        manager_personality_status = "failed"
                        errors.append(("manager_report_personality", event.get("message") or ""))
                    yield json.dumps(event, ensure_ascii=False) + "\n"

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
            if structured:
                structured_state = final_result.get("overall_picture_structured") or {}
                structured_sections = structured_state.get("sections") or {}
                all_complete = bool(
                    all_complete
                    and structured_sections.get("synthesis", {}).get("status") == "completed"
                    and all(structured_sections.get(part, {}).get("status") in ("completed", "not_applicable")
                            for part in ("skills", "motivation", "personality"))
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
                    "manager_report_personality_status": manager_personality_status,
                },
                ensure_ascii=False,
            ) + "\n"
            if errors:
                yield json.dumps(
                    {
                        "type": "generation_partial_error",
                        "message": "One or more After interview sections or manager-report sections could not be generated.",
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
    structured = request.GET.get("structured") == "1"
    structured_section = str(request.GET.get("section") or "").strip()
    if structured_section and (
        not structured or structured_section not in ("skills", "motivation", "personality", "synthesis")
        or block_key != "overall_picture"
    ):
        return JsonResponse({"error": "Invalid structured report section."}, status=400)
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
    from urllib.parse import urlencode
    params = {"force": "1"}
    if block_key:
        params["block"] = block_key
    if structured:
        params["structured"] = "1"
        if structured_section:
            params["section"] = structured_section
    stream_url += "?" + urlencode(params)

    return JsonResponse({"ok": True, "stream_url": stream_url})

