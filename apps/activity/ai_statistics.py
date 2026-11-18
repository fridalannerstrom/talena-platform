"""Aggregated, admin-only AI provider usage dashboard (#435).

Only strictly allowlisted, opted-in ActivityEvent metadata is queried.
Success means the OpenAI provider stream/request finished, not that Talena's
downstream report validated or saved.
"""
import csv
from datetime import datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import BigIntegerField, Count, Q, Sum
from django.db.models.functions import Cast, TruncDate
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import get_language
from django.utils.http import urlencode
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.accounts.models import Company
from apps.activity.admin_views import _audit_access, can_view_platform_audit
from apps.activity.models import ActivityEvent
from apps.activity.usage_summary import platform_activity_summary, platform_report_exports
from apps.core.ai.usage_metrics import FEATURES, FEATURES_EN, OUTCOMES, usage_logging_enabled

AI_VERBS = tuple(OUTCOMES.values())
SUCCESS = OUTCOMES["succeeded"]
FAILED = OUTCOMES["failed"]
INCOMPLETE = OUTCOMES["incomplete"]


def _valid_date(value):
    try:
        date = parse_date(str(value or "")[:10])
    except (TypeError, ValueError):
        return None
    return date if date and 2020 <= date.year <= 2100 else None


def _date_filters(request):
    today = timezone.localdate()
    end = _valid_date(request.GET.get("to")) or today
    start = _valid_date(request.GET.get("from")) or end - timedelta(days=29)
    if end > today:
        end = today
    if start > end:
        start = end - timedelta(days=29)
    if (end - start).days > 365:
        start = end - timedelta(days=365)
    company = (request.GET.get("company") or "")[:20]
    company = int(company) if company.isascii() and company.isdecimal() else None
    if company is not None and not 1 <= company < 2 ** 63:
        company = None
    feature = (request.GET.get("feature") or "")[:64]
    if feature not in FEATURES:
        feature = ""
    return start, end, company, feature


def _base_queryset(start, end, company, feature):
    begin = timezone.make_aware(datetime.combine(start, time.min))
    stop = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min))
    qs = ActivityEvent.objects.filter(
        verb__in=AI_VERBS, created_at__gte=begin, created_at__lt=stop,
        meta__schema=1,
    )
    if company is not None:
        qs = qs.filter(company_id=company)
    if feature:
        qs = qs.filter(meta__feature=feature)
    return qs.order_by()


def _summary(queryset):
    """SQL aggregates; no candidate content and no Python event-row scans."""
    totals = queryset.aggregate(
        count=Count("id"),
        succeeded=Count("id", filter=Q(verb=SUCCESS)),
        failed=Count("id", filter=Q(verb=FAILED)),
        incomplete=Count("id", filter=Q(verb=INCOMPLETE)),
        with_usage=Count("id", filter=Q(meta__usage_available=True)),
        tokens=Sum(Cast("meta__total_tokens", BigIntegerField())),
        input_tokens=Sum(Cast("meta__prompt_tokens", BigIntegerField())),
        output_tokens=Sum(Cast("meta__completion_tokens", BigIntegerField())),
        unattributed=Count("id", filter=Q(company__isnull=True)),
    )
    totals["tokens"] = totals["tokens"] or 0
    totals["input_tokens"] = totals["input_tokens"] or 0
    totals["output_tokens"] = totals["output_tokens"] or 0
    decided = totals["succeeded"] + totals["failed"]
    totals["success_rate"] = (
        round(totals["succeeded"] * 100 / decided, 1) if decided else None
    )
    return totals


def _feature_rows(queryset, labels=None):
    labels = labels or FEATURES
    groups = queryset.values("meta__feature").annotate(
        count=Count("id"),
        succeeded=Count("id", filter=Q(verb=SUCCESS)),
        failed=Count("id", filter=Q(verb=FAILED)),
        incomplete=Count("id", filter=Q(verb=INCOMPLETE)),
        with_usage=Count("id", filter=Q(meta__usage_available=True)),
        tokens=Sum(Cast("meta__total_tokens", BigIntegerField())),
    ).order_by("-count", "meta__feature")
    rows = []
    for row in groups:
        code = row["meta__feature"]
        # Old/injected unsupported feature IDs must never become arbitrary UI.
        if code not in FEATURES:
            continue
        rows.append({
            "code": code,
            "label": labels[code],
            "count": row["count"],
            "succeeded": row["succeeded"],
            "failed": row["failed"],
            "incomplete": row["incomplete"],
            "with_usage": row["with_usage"],
            "tokens": row["tokens"] or 0,
        })
    return rows


def _trend(queryset, start, end):
    rows = queryset.annotate(day=TruncDate("created_at")).values("day").annotate(
        count=Count("id"),
    ).order_by("day")
    lookup = {item["day"]: item["count"] for item in rows}
    days = (end - start).days + 1
    # Max 32 bars: for longer periods use equally sized day buckets.
    bucket = max(1, (days + 31) // 32)
    series = []
    for offset in range(0, days, bucket):
        begin = start + timedelta(days=offset)
        count = sum(
            lookup.get(begin + timedelta(days=i), 0)
            for i in range(min(bucket, days - offset))
        )
        series.append({"day": begin, "count": count})
    high = max((x["count"] for x in series), default=0)
    for item in series:
        item["height"] = max(3, round(100 * item["count"] / high)) if high else 3
    return series


def _call_history(queryset, request, labels, *, limit=25):
    """Bounded, admin-only detail view. Never expose raw event.meta."""
    queryset = queryset.select_related(
        "company", "actor", "candidate", "process",
    ).order_by("-created_at", "-pk")
    page = Paginator(queryset, limit).get_page(request.GET.get("page"))
    rows = []
    for event in page.object_list:
        meta = event.meta if isinstance(event.meta, dict) else {}
        code = meta.get("feature")
        # All feature names shown are from our own static catalog.
        feature_label = labels.get(code) if isinstance(code, str) else None
        actor = event.actor
        actor_name = (
            (actor.get_full_name() or actor.get_username()) if actor else None
        )
        token_count = meta.get("total_tokens")
        if type(token_count) is not int or token_count < 0:
            token_count = None
        rows.append({
            "time": event.created_at,
            "feature": feature_label,
            "company": event.company.name if event.company_id else None,
            "actor": actor_name,
            "candidate": str(event.candidate) if event.candidate_id else None,
            "process": event.process.name if event.process_id else None,
            "outcome": event.verb,
            "tokens": token_count,
        })
    return page, rows


@login_required
@never_cache
@require_GET
def platform_ai_statistics(request):
    if not can_view_platform_audit(request.user):
        return HttpResponseForbidden("Not allowed.")
    start, end, company, feature = _date_filters(request)
    # Three distinct, server-rendered views with direct-linkable URLs.
    # Besides decluttering the UI, this avoids expensive AI/detail queries
    # when an admin only wants operational or report statistics.
    tab = request.GET.get("tab", "overview")
    if tab not in {"overview", "reports", "ai"}:
        tab = "overview"
    english = (get_language() or "sv").startswith("en")
    labels = FEATURES_EN if english else FEATURES
    shared_filters = {
        "from": start.isoformat(), "to": end.isoformat(),
        **({"company": company} if company else {}),
    }
    tab_query = urlencode(shared_filters)
    context = {
        "active_tab": tab,
        "start": start, "end": end,
        "selected_company": company,
        "selected_feature": feature if tab == "ai" else "",
        "companies": Company.objects.order_by("name").only("id", "name"),
        "tab_query": tab_query,
        "features": labels if tab == "ai" else {},
        "tracking_enabled": usage_logging_enabled() if tab == "ai" else False,
    }
    if tab == "overview":
        context["operational"] = platform_activity_summary(
            start=start, end=end, company=company,
        )
    elif tab == "reports":
        context["report_exports"] = platform_report_exports(
            start=start, end=end, company=company, english=english,
        )
    else:
        qs = _base_queryset(start, end, company, feature)
        call_page, call_rows = _call_history(qs, request, labels)
        context.update({
            "totals": _summary(qs),
            "feature_rows": _feature_rows(qs, labels),
            "trend": _trend(qs, start, end),
            "call_page": call_page,
            "call_rows": call_rows,
            "filter_query": urlencode({
                "tab": "ai", **shared_filters,
                **({"feature": feature} if feature else {}),
            }),
            "earliest": (
                ActivityEvent.objects.filter(verb__in=AI_VERBS)
                .order_by("created_at")
                .values_list("created_at", flat=True).first()
            ),
        })
    response = render(request, "admin/activity/ai_statistics.html", context)
    _audit_access(request, ActivityEvent.Verb.ADMIN_LOG_ACCESSED, "ai_stats")
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@login_required
@never_cache
@require_GET
def platform_ai_statistics_export(request):
    if not can_view_platform_audit(request.user):
        return HttpResponseForbidden("Not allowed.")
    start, end, company, feature = _date_filters(request)
    rows = _feature_rows(_base_queryset(start, end, company, feature))
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="talena-ai-usage-aggregate.csv"'
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex, nofollow"
    writer = csv.writer(response)
    writer.writerow(["period_from", "period_to", "feature", "calls",
                     "provider_succeeded", "provider_failed", "stream_incomplete",
                     "calls_with_usage", "reported_total_tokens"])
    for item in rows:
        writer.writerow([start.isoformat(), end.isoformat(), item["code"],
                         item["count"], item["succeeded"], item["failed"],
                         item["incomplete"], item["with_usage"], item["tokens"]])
    _audit_access(request, ActivityEvent.Verb.ADMIN_LOG_EXPORTED, "ai_stats_csv")
    return response
