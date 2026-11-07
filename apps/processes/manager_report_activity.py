"""Privacy-minimised, tenant-scoped Chefsrapport activity (#430)."""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.activity.admin_views import can_view_platform_audit
from apps.activity.models import ActivityEvent
from apps.core.ai.language import get_request_ai_language
from .access_control import process_view_access_required
from .interview_question_models import ManagerReportTextEditEvent
from .interview_question_notes import get_candidate_question_owner
from .models import TestProcess


PDF_VERBS = {
    ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED,
    ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED,
}


def actor_label(user, language="sv"):
    if user is None:
        return "Tidigare användare" if language == "sv" else "Former user"
    return str(user.get_full_name() or user.get_username() or "").strip() or (
        "Okänd användare" if language == "sv" else "Unknown user"
    )


def _edit_row(event, language):
    if event is None:
        return None
    return {
        "type": "edited" if event.action == ManagerReportTextEditEvent.Action.SAVED else "restored",
        "actor": actor_label(event.actor, language or "sv"),
        "actor_id": event.actor_id,
        "at": event.created_at,
        "block": event.block_key,
        "version": event.version,
        "language": event.language_code,
    }


def _pdf_row(event, language):
    if event is None:
        return None
    return {
        "type": "generated" if event.verb == ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED else "prepared",
        "actor": actor_label(event.actor, language or "sv"),
        "actor_id": event.actor_id,
        "at": event.created_at,
        "block": "",
        "version": (event.meta or {}).get("edited_block_version"),
        "language": (event.meta or {}).get("language") or "",
    }


def report_activity(process, candidate, *, language=None, limit=100):
    """Two existing audit stores, one sorted metadata-only timeline.

    Fetch latest type-specific rows independently of pagination. A history
    dominated by repeated exports must never hide the actual latest editor.
    """
    language = language if language in {"sv", "en"} else None
    edits = ManagerReportTextEditEvent.objects.filter(
        process=process, candidate=candidate,
    )
    exports = ActivityEvent.objects.filter(
        company=process.company, process=process, candidate=candidate,
        verb__in=PDF_VERBS,
    )
    if language:
        edits = edits.filter(language_code=language)
        exports = exports.filter(meta__language=language)

    ordered_edits = edits.select_related("actor").order_by("-created_at", "-pk")
    ordered_exports = exports.select_related("actor").order_by("-created_at", "-pk")
    rows = (
        [_edit_row(e, language) for e in ordered_edits[:limit]]
        + [_pdf_row(e, language) for e in ordered_exports[:limit]]
    )
    rows.sort(key=lambda row: row["at"], reverse=True)
    return {
        "events": rows[:limit],
        "last_edited": _edit_row(
            ordered_edits.filter(action=ManagerReportTextEditEvent.Action.SAVED).first(),
            language,
        ),
        "last_export": _pdf_row(
            ordered_exports.filter(verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED).first(),
            language,
        ),
        "last_prepared": _pdf_row(
            ordered_exports.filter(verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED).first(),
            language,
        ),
    }


def report_activity_json(data, language):
    def serialize(row):
        if not row:
            return None
        return {
            "type": row["type"],
            "actor": row["actor"],
            "at": row["at"].isoformat(),
            "block": row["block"],
            "version": row["version"],
            "language": row["language"],
        }
    return {
        "ok": True,
        "language": language,
        "events": [serialize(row) for row in data["events"]],
        "last_edited": serialize(data["last_edited"]),
        "last_export": serialize(data["last_export"]),
        "last_prepared": serialize(data["last_prepared"]),
    }


@login_required
@process_view_access_required
@never_cache
@require_GET
def customer_manager_report_activity(request, process_id, candidate_id):
    process = get_object_or_404(TestProcess, pk=process_id)
    owner = get_candidate_question_owner(process, candidate_id)
    language = get_request_ai_language(request)
    payload = report_activity_json(
        report_activity(process, owner.candidate, language=language), language,
    )
    response = JsonResponse(payload)
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@never_cache
@require_GET
def platform_manager_report_activity(request, process_id, candidate_id):
    if not can_view_platform_audit(request.user):
        return HttpResponseForbidden("Not allowed.")
    process = get_object_or_404(TestProcess, pk=process_id)
    owner = get_candidate_question_owner(process, candidate_id)
    language = get_request_ai_language(request)
    payload = report_activity_json(
        report_activity(process, owner.candidate), language,
    )
    response = JsonResponse(payload)
    response["Cache-Control"] = "private, no-store"
    return response
