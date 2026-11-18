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
from django.views.decorators.cache import never_cache
from django.utils.translation import get_language

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
    "reports": {"manager_report_pdf_prepared", "manager_report_pdf_generated", "report_export_generated"},
    "ai": {"ai_call_succeeded", "ai_call_failed", "ai_call_incomplete"},
}
ALL_KNOWN_VERBS = {item for verbs in CATEGORIES.values() for item in verbs}
# The two tabs are server-scoped, not just a client-side presentation filter.
# Company activity initiated by a *platform* admin belongs to Admin,
# including when it is associated with a customer company.
SCOPES = frozenset({"customer", "admin"})
CUSTOMER_CATEGORIES = frozenset(CATEGORIES) - {"audit", "security"}
# A prepare event is a technical request, not an actual file export.
# Keep it visible to platform admins for troubleshooting, and record only
# the browser-confirmed generated event as a customer-facing report export.
TECHNICAL_REPORT_VERBS = frozenset({
    ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED,
})
CATEGORY_CHOICES = (
    ("candidate", "Kandidat och test", "Candidate and assessment"),
    ("portal", "Kandidatportal", "Candidate portal"),
    ("organisation", "Organisation", "Organisation"),
    ("security", "Säkerhet", "Security"),
    ("audit", "Loggåtkomst", "Audit access"),
    ("reports", "Rapportexporter", "Report exports"),
    ("ai", "AI-anrop", "AI calls"),
)
CATEGORY_BY_VERB = {
    verb: key for key, values in CATEGORIES.items() for verb in values
}

# English interface labels. Source data and verb IDs remain unchanged.
ENGLISH_VERB_LABELS = {
    "process_created": "Project created",
    "process_archived": "Project archived",
    "process_deleted": "Project deleted",
    "candidate_added": "Candidate added to project",
    "candidate_removed": "Candidate removed from project",
    "invite_sent": "Assessment invitation sent",
    "test_started": "Assessment started",
    "test_completed": "Assessment completed",
    "all_tests_completed": "All assessments completed",
    "status_changed": "Status changed",
    "candidate_result_email_sent": "Candidate result email sent",
    "candidate_result_email_failed": "Candidate result email failed",
    "candidate_result_snapshot_created": "Candidate report created",
    "candidate_result_link_opened": "Candidate report link opened",
    "candidate_result_code_verified": "Candidate verification succeeded",
    "candidate_result_code_failed": "Candidate verification failed",
    "candidate_result_feedback_submitted": "Candidate feedback submitted",
    "candidate_result_code_replaced": "Verification code replaced",
    "candidate_result_access_revoked": "Candidate report access revoked",
    "candidate_result_access_expired": "Candidate report access expired",
    "company_created": "Company created",
    "company_updated": "Company updated",
    "company_deleted": "Company deleted",
    "company_member_invited": "User invited",
    "company_member_added": "User added",
    "company_member_removed": "User removed",
    "company_member_role_updated": "User role changed",
    "company_invite_accepted": "Invitation accepted",
    "orgunit_created": "Organisational unit created",
    "orgunit_updated": "Organisational unit updated",
    "orgunit_moved": "Organisational unit moved",
    "orgunit_deleted": "Organisational unit deleted",
    "user_access_updated": "User access updated",
    "user_logged_in": "User logged in",
    "admin_log_accessed": "Internal activity log accessed",
    "admin_log_exported": "Internal activity log CSV prepared",
    "manager_report_pdf_prepared": "Manager report PDF prepared",
    "manager_report_pdf_generated": "Manager report PDF generated (browser confirmed)",
    "report_export_generated": "Report PDF/ZIP generated (browser reported)",
    "ai_call_succeeded": "AI provider call succeeded",
    "ai_call_failed": "AI provider call failed",
    "ai_call_incomplete": "AI provider stream interrupted",
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
    result = {"scope": "admin" if params.get("scope") == "admin" else "customer"}
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
        try:
            date = parse_date((params.get(key) or "")[:10])
        except ValueError:
            date = None
        if date and 2020 <= date.year <= 2100:
            result[key] = date
    return result


def _query(filters):
    qs = ActivityEvent.objects.all()
    if filters.get("scope") == "admin":
        # Audit access, platform-level events and actions performed by
        # platform admins are internal. Include tenant-linked admin actions.
        qs = qs.filter(
            Q(verb__in=CATEGORIES["audit"])
            | Q(verb__in=TECHNICAL_REPORT_VERBS)
            | Q(company__isnull=True)
            | Q(actor__role="admin")
            | Q(actor__is_superuser=True)
        )
    else:
        # Customer-domain events with a tenant, initiated by a customer
        # account or generated by the platform/candidate portal. An actor
        # that was deleted remains unattributed rather than guessed.
        qs = qs.filter(company__isnull=False).exclude(
            verb__in=CATEGORIES["audit"] | TECHNICAL_REPORT_VERBS
        ).filter(
            Q(actor__isnull=True)
            | (Q(actor__role="customer") & Q(actor__is_superuser=False))
        )
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


def _row(event, *, sv=True):
    actor = event.actor
    actor_label = (
        (actor.get_full_name() or actor.get_username())
        if actor else ("System" if not event.actor_name else "Tidigare aktör")
    )
    return {
        "id": event.pk,
        "timestamp": event.created_at,
        "verb": event.verb,
        "label": (
            event.get_verb_display() if sv
            else ENGLISH_VERB_LABELS.get(event.verb, event.verb)
        ),
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
@never_cache
@require_GET
def platform_activity_log(request):
    if not can_view_platform_audit(request.user):
        return HttpResponseForbidden("Not allowed.")

    filters = _filters(request)
    page = Paginator(_query(filters), 30).get_page(request.GET.get("page"))
    sv = (get_language() or "sv").startswith("sv")
    rows = [_row(e, sv=sv) for e in page.object_list]
    scope = filters["scope"]
    category_choices = [(key, label_sv if sv else label_en)
                        for key, label_sv, label_en in CATEGORY_CHOICES
                        if scope == "admin" or key in CUSTOMER_CATEGORIES]
    available_verbs = [
        (code, label) for code, label in ActivityEvent.Verb.choices
        if scope == "admin" or code not in CATEGORIES["audit"] | CATEGORIES["security"] | TECHNICAL_REPORT_VERBS
    ]
    # Preserve only validated fields in export and page links.
    clean_params = {key: str(value) for key, value in filters.items()}
    # Switching tabs keeps only the date range. Keeping a tenant or verb
    # would accidentally hide platform audit-access records in Admin.
    tab_date_query = urlencode({
        key: str(filters[key]) for key in ("from", "to") if key in filters
    })
    response = render(request, "admin/activity/log.html", {
        "events": rows,
        "active_scope": scope,
        "tab_date_query": tab_date_query,
        "page_obj": page,
        "filters": clean_params,
        "filter_query": urlencode(clean_params),
        "categories": category_choices,
        "companies": Company.objects.order_by("name").only("id", "name"),
        "verbs": available_verbs,
        "tracked_categories": ("candidate", "portal", "organisation", "reports", "ai") if scope == "customer" else tuple(CATEGORIES),
        "earliest_known": (
            _query({"scope": scope}).order_by("created_at")
            .values_list("created_at", flat=True).first()
        ),
    })
    # A failed template render should not be recorded as a successful view.
    _audit_access(request, ActivityEvent.Verb.ADMIN_LOG_ACCESSED, "list")
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@login_required
@never_cache
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
    response["X-Robots-Tag"] = "noindex, nofollow"
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
