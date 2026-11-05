"""Platform-only, privacy-minimised ActivityEvent explorer (#432/#434).

Phase 1 uses the existing event table. No hidden client-side tracking, no raw
meta/payload inspection and no claim that previously uninstrumented actions
are historically present.
"""
import csv
from datetime import datetime, time, timedelta, timezone as utc_timezone

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils.dateparse import parse_date
from django.utils.http import urlencode
from django.views.decorators.http import require_GET

from apps.activity.models import ActivityEvent
from apps.accounts.models import Company


# Explicitly distinguish what is already logged from not-yet-instrumented AI
# and export workflows. These categories never imply candidate assessment.
CATEGORIES = {
    "candidate": {
        "candidate_added", "candidate_removed", "invite_sent",
        "test_started", "test_completed", "all_tests_completed", "status_changed",
    },
    "portal": {
        "candidate_result_email_sent", "candidate_result_email_failed",
        "candidate_result_snapshot_created", "candidate_result_link_opened",
        "candidate_result_code_verified", "candidate_result_code_failed",
        "candidate_result_feedback_submitted", "candidate_result_code_replaced",
        "candidate_result_access_revoked", "candidate_result_access_expired",
    },
    "organisation": {
        "process_created", "process_archived", "process_deleted",
        "company_created", "company_updated", "company_deleted",
        "company_member_invited", "company_member_added",
        "company_member_removed", "company_member_role_updated",
        "company_invite_accepted", "orgunit_created", "orgunit_updated",
        "orgunit_moved", "orgunit_deleted", "user_access_updated",
    },
    "security": {"user_logged_in"},
    "audit": {"admin_log_accessed", "admin_log_exported"},
}
ALL_KNOWN_VERBS = {item for verbs in CATEGORIES.values() for item in verbs}
CATEGORY_CHOICES = (
    ("candidate", "Kandidat och test", "Candidate and assessment"),
    ("portal", "Kandidatportal", "Candidate portal"),
    ("organisation", "Organisation", "Organisation"),
    ("security", "Säkerhet", "Security"),
    ("audit", "Loggåtkomst", "Audit access"),
)
CATEGORY_BY_VERB = {
    verb: key for key, values in CATEGORIES.items() for verb in values
}


def can_view_platform_audit(user):
    """Staff-only is not enough; require the actual *platform* admin role."""
    return bool(
        user.is_authenticated and user.is_active
        and (getattr(user, "role", "") == "admin" or user.is_superuser)
    )


def _filters(request):
    # Only allow numeric IDs and recognised verb/category names.
    params = request.GET
    result = {}
    for field in ("company", "process", "candidate", "actor"):
        value = (params.get(field) or "")[:20]
        if value.isascii() and value.isdecimal():
            result[field] = int(value)
    category = (params.get("category") or "")[:32]
    if category in CATEGORIES:
        result["category"] = category
    verb = (params.get("verb") or "")[:80]
    if verb in ALL_KNOWN_VERBS:
        result["verb"] = verb
    q = (params.get("q") or "").strip()[:80]
    if q:
        result["q"] = q
    for key in ("from", "to"):
        date = parse_date((params.get(key) or "")[:10])
        if date and 2020 <= date.year <= 2100:
            result[key] = date
    return result


def _query(filters):
    qs = ActivityEvent.objects.all()
    if "company" in filters:
        qs = qs.filter(company_id=filters["company"])
    if "process" in filters:
        qs = qs.filter(process_id=filters["process"])
    if "candidate" in filters:
        qs = qs.filter(candidate_id=filters["candidate"])
    if "actor" in filters:
        qs = qs.filter(actor_id=filters["actor"])
    if "category" in filters:
        qs = qs.filter(verb__in=CATEGORIES[filters["category"]])
    if "verb" in filters:
        qs = qs.filter(verb=filters["verb"])
    if "from" in filters:
        qs = qs.filter(created_at__gte=datetime.combine(
            filters["from"], time.min, utc_timezone.utc,
        ))
    if "to" in filters:
        qs = qs.filter(created_at__lt=datetime.combine(
            filters["to"] + timedelta(days=1), time.min, utc_timezone.utc,
        ))
    if "q" in filters:
        # Never search raw meta, prompts, notes, emails or Sova payloads.
        qs = qs.filter(
            Q(company__name__icontains=filters["q"])
            | Q(process__name__icontains=filters["q"])
            | Q(candidate__first_name__icontains=filters["q"])
            | Q(candidate__last_name__icontains=filters["q"])
            | Q(actor__first_name__icontains=filters["q"])
            | Q(actor__last_name__icontains=filters["q"])
        )
    return qs.select_related("company", "actor", "process", "candidate").order_by(
        "-created_at", "-pk"
    )


def _audit_access(request, verb, scope):
    # Always attribute actor on the server. A global audit visit has no tenant
    # and must never be misattributed to a guessed company.
    ActivityEvent.objects.create(
        company=None,
        actor=request.user,
        verb=verb,
        meta={"schema": 1, "scope": scope},  # strict static allowlist
    )


def _row(event):
    actor = event.actor
    actor_label = (
        (actor.get_full_name() or actor.get_username())
        if actor else ("System" if not event.actor_name else "Tidigare aktör")
    )
    return {
        "id": event.pk,
        "timestamp": event.created_at,
        "verb": event.verb,
        "label": event.get_verb_display() if event.verb in ALL_KNOWN_VERBS else event.verb,
        "category": CATEGORY_BY_VERB.get(event.verb, "other"),
        "actor": actor_label,
        "actor_id": event.actor_id,
        "company": event.company.name if event.company_id else "",
        "company_id": event.company_id,
        "process": event.process.name if event.process_id else "",
        "process_id": event.process_id,
        "candidate": str(event.candidate) if event.candidate_id else "",
        "candidate_id": event.candidate_id,
    }


@login_required
@require_GET
def platform_activity_log(request):
    if not can_view_platform_audit(request.user):
        return HttpResponseForbidden("Not allowed.")

    filters = _filters(request)
    page = Paginator(_query(filters), 30).get_page(request.GET.get("page"))
    _audit_access(request, ActivityEvent.Verb.ADMIN_LOG_ACCESSED, "list")
    rows = [_row(e) for e in page.object_list]
    sv = (request.LANGUAGE_CODE or "sv").startswith("sv")
    category_choices = [(key, label_sv if sv else label_en)
                        for key, label_sv, label_en in CATEGORY_CHOICES]
    # Preserve only validated fields in export and page links.
    clean_params = {key: str(value) for key, value in filters.items()}
    return render(request, "admin/activity/log.html", {
        "events": rows,
        "page_obj": page,
        "filters": clean_params,
        "filter_query": urlencode(clean_params),
        "categories": category_choices,
        "companies": Company.objects.order_by("name").only("id", "name"),
        "verbs": ActivityEvent.Verb.choices,
        "tracked_categories": ("candidate", "portal", "organisation", "security"),
        "earliest_known": (
            ActivityEvent.objects.exclude(
                verb__in=CATEGORIES["audit"]
            ).order_by("created_at").values_list("created_at", flat=True).first()
        ),
    })


@login_required
@require_GET
def platform_activity_export(request):
    if not can_view_platform_audit(request.user):
        return HttpResponseForbidden("Not allowed.")

    filters = _filters(request)
    # Hard cap; no full-table downloads, no metadata or candidate emails.
    rows = list(_query(filters)[:1000])
    _audit_access(request, ActivityEvent.Verb.ADMIN_LOG_EXPORTED, "csv_prepared")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="talena-activity.csv"'
    response["Cache-Control"] = "no-store"
    writer = csv.writer(response)
    writer.writerow([
        "event_id", "occurred_at_utc", "event_type", "actor_id",
        "company_id", "project_id", "candidate_id",
    ])
    for event in rows:
        writer.writerow([
            event.pk, event.created_at.astimezone(utc_timezone.utc).isoformat(),
            event.verb, event.actor_id or "",
            event.company_id or "", event.process_id or "", event.candidate_id or "",
        ])
    return response
