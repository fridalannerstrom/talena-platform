from __future__ import annotations

import json
from urllib.parse import urlencode

from django.urls import reverse

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.core.ai.language import (
    ai_content_language_matches,
    get_request_ai_language,
    mark_ai_content_outdated_if_language_changed,
)

from .project_personality_trait_selection import (
    _role_context,
    get_project_personality_trait_selection,
    get_project_personality_trait_overrides,
    map_project_traits_to_candidate_results,
    project_selection_items_for_candidate,
)

from .models import (
    HistoricalProcessCandidate,
    TestInvitation,
    TestProcess,
)


MAX_PERSONALITY_TRAITS = 8
MAX_PERSONALITY_COMPETENCIES = 6
_INSTALLED = False


def _contains_competency_selection(selected_traits) -> bool:
    return any(
        str(item or "").strip().casefold().startswith("competency::")
        for item in selected_traits or []
    )


def _selection_limit(selected_traits: list[str]) -> int:
    return (
        MAX_PERSONALITY_COMPETENCIES
        if _contains_competency_selection(selected_traits)
        else MAX_PERSONALITY_TRAITS
    )


def _role_context_required_message(language_code: str) -> str:
    if str(language_code or "").lower().startswith("sv"):
        return "Lägg till rollkontext i projektet innan du skapar personlighetsfrågor."
    return "Add role context to the project before generating personality questions."


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

    # An unchanged purpose does not imply unchanged role context. Preserve
    # the old questions for viewing, but mark them outdated for regeneration.
    from apps.core.ai.personality_question_context_quality_policy import (
        is_personality_question_context_outdated,
    )
    if (
        saved_result
        and current_status == "completed"
        and is_personality_question_context_outdated(process, saved_result)
    ):
        current_status = "outdated"
        invitation.ai_personality_questions_status = "outdated"
        invitation.save(update_fields=["ai_personality_questions_status"])

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

    # Keep existing generated questions viewable, but never generate a new
    # set without role context saved for the project's active purpose.
    role_context_data = _role_context(process)
    if role_context_data is None:
        return JsonResponse(
            {"error": _role_context_required_message(language_code)},
            status=409,
        )

    project_selection = None
    try:
        project_selection = get_project_personality_trait_selection(
            process,
            language_code=language_code,
            generate=True,
        )
    except Exception as error:
        message = (
            "Kunde inte välja personlighetsdrag för projektet. "
            "Kontrollera rollkontexten och försök igen."
            if str(language_code or "").lower().startswith("sv")
            else (
                "Could not select personality traits for the project. "
                "Check the role context and try again."
            )
        )
        return JsonResponse({"error": message}, status=503)

    effective_selection = map_project_traits_to_candidate_results(
        project_selection,
        personality_results,
    )
    if (
        not project_selection
        or len(effective_selection) != len(project_selection)
    ):
        message = (
            "Projektets valda personlighetsdrag saknas i kandidatens resultat."
            if str(language_code or "").lower().startswith("sv")
            else (
                "The project's selected personality traits are not "
                "available in this candidate's results."
            )
        )
        return JsonResponse({"error": message}, status=409)

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
        original_selection = getattr(
            invitation,
            "selected_personality_traits",
            None,
        )
        automatic_project_selection = True
        # Use only the shared project selection; old per-candidate selections
        # remain stored for compatibility but no longer control generation.
        invitation.selected_personality_traits = effective_selection

        try:
            for event in personality_ai.stream_personality_questions(
                owner=invitation,
                personality_results=personality_results,
                language_code=language_code,
            ):
                if automatic_project_selection:
                    if event.get("type") == "selected_traits":
                        event = {
                            **event,
                            "items": effective_selection,
                        }
                    elif event.get("type") == "suggested_traits":
                        event = {
                            **event,
                            "items": project_selection_items_for_candidate(
                                project_selection,
                                personality_results,
                                language_code=language_code,
                            ),
                        }
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

            if _contains_competency_selection(selected_traits):
                raise ValueError(
                    "Competency-based personality questions are temporarily unavailable."
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

            # Focus labels are supplemental metadata. The AI normalizer
            # keeps recognized selected-trait labels and drops unknown ones;
            # missing labels must not block complete generated questions.

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
        finally:
            if automatic_project_selection:
                invitation.selected_personality_traits = original_selection

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
    """Candidate-level trait editing is replaced by the project editor."""

    from . import views

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not views.user_can_access_process(request.user, process):
        return HttpResponseForbidden(
            "You do not have access to this process."
        )

    _owner_for_process_candidate(process, candidate_id)

    if _role_context(process) is None:
        return JsonResponse(
            {
                "error": _role_context_required_message(
                    get_request_ai_language(request)
                )
            },
            status=409,
        )

    language_code = get_request_ai_language(request)
    message = (
        "Personlighetsdrag väljs för hela projektet på sidan för rollkontext."
        if str(language_code or "").lower().startswith("sv")
        else "Personality traits are selected for the whole project on the role context page."
    )
    return JsonResponse({"error": message}, status=409)



def _install_candidate_detail_context_policy(views) -> None:
    original = views.build_candidate_detail_context
    if getattr(original, "_project_personality_trait_policy", False):
        return

    def build_candidate_detail_context_with_project_traits(
        process,
        invitation,
        language="sv",
    ):
        context = original(
            process=process,
            invitation=invitation,
            language=language,
        )
        role_context_data = _role_context(process)
        project_traits = (
            get_project_personality_trait_overrides(
                role_context_data["role_context"],
                role_context_data["purpose_key"],
            )
            if role_context_data is not None
            else []
        )
        project_selection = (
            get_project_personality_trait_selection(
                process,
                language_code=language,
                generate=False,
            )
            if role_context_data is not None
            else None
        )
        mapped_project_traits = map_project_traits_to_candidate_results(
            project_selection,
            context.get("personality_traits_for_selection") or [],
        )
        saved_selection = (
            (context.get("personality_questions") or {}).get("selected_traits")
            or []
        )
        context["has_personality_role_context"] = (
            role_context_data is not None
        )
        context["personality_question_selection_mode"] = (
            "project_manual"
            if project_traits
            else "project_default"
            if role_context_data is not None
            else "unavailable"
        )
        context["personality_project_selection_source"] = (
            "project_manual"
            if project_traits
            else "project_default"
            if role_context_data is not None
            else "unavailable"
        )
        context["personality_project_default_traits"] = mapped_project_traits
        context["selected_personality_traits"] = (
            mapped_project_traits or saved_selection
        )
        candidate_detail_url = reverse(
            "processes:process_candidate_detail",
            kwargs={
                "process_id": process.id,
                "candidate_id": invitation.candidate_id,
            },
        )
        role_context_url = reverse(
            "processes:process_role_context",
            kwargs={"pk": process.id},
        )
        context["personality_role_context_url"] = (
            role_context_url
            + "?"
            + urlencode({"next": candidate_detail_url})
        )
        return context

    build_candidate_detail_context_with_project_traits._project_personality_trait_policy = True
    views.build_candidate_detail_context = (
        build_candidate_detail_context_with_project_traits
    )


def _install_role_context_regeneration_guard(views) -> None:
    original = views.process_candidate_personality_questions_regenerate
    if getattr(original, "_project_role_context_guard", False):
        return

    @login_required
    @require_POST
    def regenerate_with_role_context_guard(
        request,
        process_id,
        candidate_id,
    ):
        process = get_object_or_404(TestProcess, pk=process_id)
        if not views.user_can_access_process(request.user, process):
            return HttpResponseForbidden(
                "You do not have access to this project."
            )
        if _role_context(process) is None:
            return JsonResponse(
                {
                    "error": _role_context_required_message(
                        get_request_ai_language(request)
                    )
                },
                status=409,
            )
        return original(
            request,
            process_id,
            candidate_id,
        )

    regenerate_with_role_context_guard._project_role_context_guard = True
    views.process_candidate_personality_questions_regenerate = (
        regenerate_with_role_context_guard
    )


def install_personality_question_selection_policy() -> None:
    """Install project-scoped trait selection before URL callbacks are bound."""

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
    _install_candidate_detail_context_policy(views)
    _install_role_context_regeneration_guard(views)

    _INSTALLED = True
