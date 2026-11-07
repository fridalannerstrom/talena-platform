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


def report_activity(process, candidate, *, language=None, limit=100):
    """Two existing audit stores, one sorted metadata-only timeline.

    A restored override stays in event history but does not become a current
    editor. No notes, report texts, AI prompts or PDF bytes are ever exposed.
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

    rows = []
    for e in edits.select_related("actor").order_by("-created_at", "-pk")[:limit]:
        rows.append({
            "type": "edited" if e.action == ManagerReportTextEditEvent.Action.SAVED else "restored",
            "actor": actor_label(e.actor, language or "sv"),
            "actor_id": e.actor_id,
            "at": e.created_at,
            "block": e.block_key,  # allowlisted by update endpoint
            "version": e.version,
            "language": e.language_code,
        })
    for e in exports.select_related("actor").order_by("-created_at", "-pk")[:limit]:
        rows.append({
            "type": "generated" if e.verb == ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED else "prepared",
            "actor": actor_label(e.actor, language or "sv"),
            "actor_id": e.actor_id,
            "at": e.created_at,
            "block": "",
            "version": (e.meta or {}).get("edited_block_version"),
            "language": (e.meta or {}).get("language") or "",
        })

    rows.sort(key=lambda row: row["at"], reverse=True)
    rows = rows[:limit]
    return {
        "events": rows,
        "last_edited": next((r for r in rows if r["type"] == "edited"), None),
        "last_export": next((r for r in rows if r["type"] == "generated"), None),
        "last_prepared": next((r for r in rows if r["type"] == "prepared"), None),
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
