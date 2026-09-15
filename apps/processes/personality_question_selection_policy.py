from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.core.ai.language import (
    ai_content_language_matches,
    get_request_ai_language,
    mark_ai_content_outdated_if_language_changed,
)

from .models import (
    HistoricalProcessCandidate,
    TestInvitation,
    TestProcess,
)


MAX_PERSONALITY_TRAITS = 8
MAX_PERSONALITY_COMPETENCIES = 6
_INSTALLED = False


def _selection_limit(selected_traits: list[str]) -> int:
    is_competency_mode = any(
        str(item or "").strip().casefold().startswith("competency::")
        for item in selected_traits or []
    )
    return (
        MAX_PERSONALITY_COMPETENCIES
        if is_competency_mode
        else MAX_PERSONALITY_TRAITS
    )


def _owner_for_process_candidate(process, candidate_id):
    if process.is_historical:
        return get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
            )
            .prefetch_related(
                "assessment_results__scores",
                "assessment_results__import_file",
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


def _normalise_saved_question_labels(saved_result, owner):
    """Keep old saved results display-safe when a model omitted trait metadata."""

    from apps.core.ai import personality_questions as personality_ai

    if not isinstance(saved_result, dict):
        return saved_result

    questions = saved_result.get("questions")
    if not isinstance(questions, list) or not questions:
        return saved_result

    selected_traits = (
        saved_result.get("selected_traits")
        or getattr(owner, "selected_personality_traits", None)
        or []
    )

    if not selected_traits:
        return saved_result

    normalised = personality_ai._normalise_personality_questions(
        questions,
        selected_traits,
    )

    return {
        **saved_result,
        "questions": normalised,
    }


def _stream_event_from_result(event, result):
    """Send the frontend the same normalized metadata that Talena saves."""

    if not isinstance(event, dict):
        return event

    event_type = str(event.get("type") or "").strip().lower()

    if event_type == "questions":
        return {
            **event,
            "items": result.get("questions") or [],
        }

    if event_type == "selected_traits":
        return {
            **event,
            "items": result.get("selected_traits") or [],
        }

    if event_type == "suggested_traits":
        return {
            **event,
            "items": result.get("suggested_traits") or [],
        }

    return event


@login_required
def process_candidate_personality_questions_stream(
    request,
    process_id,
    candidate_id,
):
    """Stream personality questions with up to eight selected traits."""

    from apps.core.ai import personality_questions as personality_ai
    from . import views

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not views.user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this process."
        )

    invitation = _owner_for_process_candidate(
        process,
        candidate_id,
    )

    language_code = get_request_ai_language(request)
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="personality_questions",
        result_field="ai_personality_questions",
        status_field="ai_personality_questions_status",
        language_code=language_code,
    )

    personality_results = (
        views.build_personality_question_traits_for_ai_owner(
            invitation
        )
    )

    if not personality_results:
        return JsonResponse(
            {
                "error": (
                    "No personality assessment results "
                    "are available for this candidate."
                )
            },
            status=400,
        )

    current_status = (
        invitation.ai_personality_questions_status
        or "not_started"
    )

    saved_result = (
        invitation.ai_personality_questions
        or {}
    )

    current_purpose = (
        process.purpose
        or ""
    ).strip().lower()

    saved_purpose = (
        invitation.ai_personality_questions_purpose
        or ""
    ).strip().lower()

    if (
        saved_result
        and current_status == "completed"
        and saved_purpose != current_purpose
    ):
        current_status = "outdated"
        invitation.ai_personality_questions_status = "outdated"
        invitation.save(
            update_fields=[
                "ai_personality_questions_status",
            ]
        )

    if (
        ai_content_language_matches(
            invitation,
            "personality_questions",
            language_code,
        )
        and views.should_return_saved_ai_result(
            saved_result,
            current_status,
        )
    ):
        saved_result = _normalise_saved_question_labels(
            saved_result,
            invitation,
        )

        def existing_generator():
            yield json.dumps(
                {
                    "type": "saved_result",
                    "data": saved_result,
                    "status": current_status,
                },
                ensure_ascii=False,
            ) + "\n"

        response = StreamingHttpResponse(
            existing_generator(),
            content_type=(
                "application/x-ndjson; charset=utf-8"
            ),
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    if current_status == "generating":
        return JsonResponse(
            {
                "error": (
                    "The personality questions are "
                    "already being generated."
                )
            },
            status=409,
        )

    invitation.ai_personality_questions_status = "generating"
    invitation.save(
        update_fields=[
            "ai_personality_questions_status",
        ]
    )

    def generator():
        result = personality_ai.create_empty_personality_questions(
            invitation,
            language_code=language_code,
        )
        received_done_event = False

        try:
            for event in personality_ai.stream_personality_questions(
                owner=invitation,
                personality_results=personality_results,
                language_code=language_code,
            ):
                result = personality_ai.apply_personality_questions_event(
                    result,
                    event,
                )

                if event.get("type") == "done":
                    received_done_event = True

                public_event = _stream_event_from_result(
                    event,
                    result,
                )

                yield json.dumps(
                    public_event,
                    ensure_ascii=False,
                ) + "\n"

            selected_traits = (
                result.get("selected_traits")
                or []
            )
            questions = (
                result.get("questions")
                or []
            )

            selection_limit = _selection_limit(
                selected_traits
            )

            if not (
                1 <= len(selected_traits) <= selection_limit
            ):
                raise ValueError(
                    "The personality question selection was invalid."
                )

            if not questions:
                raise ValueError(
                    "The AI response did not contain "
                    "valid personality questions."
                )

            if any(
                not (
                    isinstance(question.get("traits"), list)
                    and question.get("traits")
                )
                for question in questions
                if isinstance(question, dict)
            ):
                raise ValueError(
                    "Every personality question must include a valid focus label."
                )

            if not received_done_event:
                yield json.dumps(
                    {
                        "type": "done",
                    },
                    ensure_ascii=False,
                ) + "\n"

            personality_ai.save_personality_questions(
                owner=invitation,
                result=result,
                language_code=language_code,
            )

        except Exception as error:
            invitation.ai_personality_questions_status = "failed"
            invitation.save(
                update_fields=[
                    "ai_personality_questions_status",
                ]
            )

            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                },
                ensure_ascii=False,
            ) + "\n"

    response = StreamingHttpResponse(
        generator(),
        content_type=(
            "application/x-ndjson; charset=utf-8"
        ),
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
@require_POST
def process_candidate_personality_traits_update(
    request,
    process_id,
    candidate_id,
):
    """Save up to eight traits, or six competencies, for personality questions."""

    from apps.core.ai import personality_questions as personality_ai
    from . import views

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not views.user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this process."
        )

    invitation = _owner_for_process_candidate(
        process,
        candidate_id,
    )

    try:
        payload = json.loads(
            request.body.decode("utf-8")
            or "{}"
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "error": "Invalid JSON payload."
            },
            status=400,
        )

    raw_traits = payload.get("traits")
    if not isinstance(raw_traits, list):
        return JsonResponse(
            {
                "error": (
                    "Traits must be supplied as a list."
                )
            },
            status=400,
        )

    personality_results = (
        views.build_personality_question_traits_for_ai_owner(
            invitation
        )
    )

    selected_traits = personality_ai.normalise_selected_traits(
        selected_traits=raw_traits,
        available_results=personality_results,
    )

    selection_limit = _selection_limit(
        selected_traits
    )

    if len(selected_traits) > selection_limit:
        noun = (
            "competencies"
            if selection_limit == MAX_PERSONALITY_COMPETENCIES
            else "personality traits"
        )
        return JsonResponse(
            {
                "error": (
                    f"Select no more than {selection_limit} "
                    f"available {noun}."
                )
            },
            status=400,
        )

    invitation.selected_personality_traits = selected_traits
    invitation.ai_personality_questions_status = (
        "outdated"
        if invitation.ai_personality_questions
        else "not_started"
    )

    invitation.save(
        update_fields=[
            "selected_personality_traits",
            "ai_personality_questions_status",
        ]
    )

    return JsonResponse(
        {
            "ok": True,
            "selected_traits": selected_traits,
            "selection_mode": (
                "manual"
                if selected_traits
                else "automatic"
            ),
        }
    )


def install_personality_question_selection_policy() -> None:
    """Replace legacy six-trait endpoints before URL patterns are constructed."""

    global _INSTALLED
    if _INSTALLED:
        return

    from . import views

    views.process_candidate_personality_questions_stream = (
        process_candidate_personality_questions_stream
    )
    views.process_candidate_personality_traits_update = (
        process_candidate_personality_traits_update
    )

    _INSTALLED = True
