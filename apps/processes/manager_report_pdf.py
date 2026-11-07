"""Server-authoritative provenance for a browser-rendered manager-report PDF (#429).

This endpoint records preparation, not a confirmed local download. The actual
PDF is rendered in the browser after receiving this response.
"""
import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
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
        meta={
            "report": "manager_report", "language": language, "status": "prepared",
            "edited_block_version": last_edit.version if last_edit else None,
        },
    )

    response = JsonResponse({
        "ok": True,
        "prepared_event_id": event.pk,
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


@login_required
@process_view_access_required
@require_POST
def confirm_manager_report_pdf_generated(request, process_id, candidate_id):
    """Record client-reported PDF generation; never claim a local download."""
    process = get_object_or_404(TestProcess, pk=process_id)
    owner = get_candidate_question_owner(process, candidate_id)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        prepared_id = payload.get("prepared_event_id") if isinstance(payload, dict) else None
    except (ValueError, UnicodeDecodeError):
        prepared_id = None
    if type(prepared_id) is not int or prepared_id <= 0:
        return JsonResponse({"error": "Invalid PDF preparation reference."}, status=400)

    with transaction.atomic():
        prepared = (
            ActivityEvent.objects.select_for_update()
            .filter(
                pk=prepared_id, company=process.company, process=process,
                candidate=owner.candidate, actor=request.user,
                verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED,
            )
            .first()
        )
        if prepared is None:
            return JsonResponse({"error": "PDF preparation not found."}, status=404)
        if prepared.created_at < timezone.now() - timedelta(hours=1):
            return JsonResponse({"error": "PDF preparation expired."}, status=409)
        generated = ActivityEvent.objects.filter(
            company=process.company, process=process, candidate=owner.candidate,
            actor=request.user,
            verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED,
            meta__prepared_event_id=prepared.pk,
        ).first()
        if generated is None:
            generated = ActivityEvent.objects.create(
                company=process.company,
                process=process,
                candidate=owner.candidate,
                invitation=owner if isinstance(owner, TestInvitation) else None,
                actor=request.user,
                actor_name=_verified_actor_label(
                    request.user, (prepared.meta or {}).get("language") or "sv",
                ),
                verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED,
                meta={
                    "report": "manager_report",
                    "language": (prepared.meta or {}).get("language"),
                    "status": "client_reported_generated",
                    "prepared_event_id": prepared.pk,
                    "edited_block_version": (prepared.meta or {}).get("edited_block_version"),
                },
            )

    response = JsonResponse({
        "ok": True, "status": "client_reported_generated",
        "generated_at": generated.created_at.isoformat(),
    })
    response["Cache-Control"] = "private, no-store"
    return response
