"""Server-authoritative provenance for a browser-rendered manager-report PDF (#429).

This endpoint records preparation, not a confirmed local download. The actual
PDF is rendered in the browser after receiving this response.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.activity.models import ActivityEvent
from apps.core.ai.language import get_request_ai_language
from .access_control import process_view_access_required
from .interview_question_models import ManagerReportTextEdit
from .interview_question_notes import get_candidate_question_owner
from .models import TestInvitation, TestProcess


def _verified_actor_label(user, language: str) -> str:
    """Never infer identity from a request payload or from another user."""
    if user is None:
        return "Okänd användare" if language == "sv" else "Unknown user"
    name = str(user.get_full_name() or "").strip()
    if not name:
        name = str(user.get_username() or "").strip()
    return name or ("Okänd användare" if language == "sv" else "Unknown user")


@login_required
@process_view_access_required
@require_POST
def prepare_manager_report_pdf(request, process_id, candidate_id):
    process = get_object_or_404(TestProcess, pk=process_id)
    owner = get_candidate_question_owner(process, candidate_id)
    language = get_request_ai_language(request)

    last_edit = (
        ManagerReportTextEdit.objects
        .filter(process=process, candidate=owner.candidate, language_code=language)
        .select_related("updated_by")
        .order_by("-updated_at", "-pk")
        .first()
    )
    event = ActivityEvent.objects.create(
        company=process.company,
        process=process,
        candidate=owner.candidate,
        invitation=owner if isinstance(owner, TestInvitation) else None,
        actor=request.user,
        actor_name=_verified_actor_label(request.user, language),
        verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED,
        meta={"report": "manager_report", "language": language, "status": "prepared"},
    )

    response = JsonResponse({
        "ok": True,
        "language": language,
        "exported_by": {
            "name": _verified_actor_label(request.user, language),
            "at": event.created_at.isoformat(),
        },
        "last_edited_by": ({
            "name": _verified_actor_label(last_edit.updated_by, language),
            "at": last_edit.updated_at.isoformat(),
        } if last_edit else None),
    })
    response["Cache-Control"] = "private, no-store"
    return response
