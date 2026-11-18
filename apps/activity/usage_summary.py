"""Operational activity KPIs for Talena platform admins (#435).

Read existing, accurately-labelled event types only. Internal audit access and
OpenAI provider calls are deliberately excluded, so opening this dashboard
cannot inflate customer/project activity. No raw metadata or assessment values.
"""
from datetime import datetime, time, timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.activity.admin_views import CATEGORIES
from apps.activity.models import ActivityEvent
from apps.processes.interview_question_models import ManagerReportTextEditEvent


# No admin_log_accessed/exported, AI SDK calls, user sign-ins or PDF
# 'prepared' events: none is proof of a customer-facing business action.
ACTIVITY_VERBS = frozenset().union(
    CATEGORIES["candidate"],
    CATEGORIES["portal"],
    CATEGORIES["organisation"],
    {"manager_report_pdf_generated"},
)
CATEGORIZED_VERBS = (
    ("projects", "Projekt och organisationer", "Projects & organisations",
     frozenset(CATEGORIES["organisation"])),
    ("tests", "Kandidater och tester", "Candidates & assessments",
     frozenset(CATEGORIES["candidate"])),
    ("portal", "Kandidatportal", "Candidate portal",
     frozenset(CATEGORIES["portal"])),
    ("exports", "Bekräftade chefsrapport-PDF", "Confirmed manager report PDFs",
     frozenset({"manager_report_pdf_generated"})),
)


def platform_activity_summary(*, start, end, company=None, english=False):
    """Bounded aggregations; returns zeros only for *logged* event categories.

    Distinct company/project counts mean entities with at least one qualifying
    recorded event during the period, not all live accounts or projects.
    """
    begin = timezone.make_aware(datetime.combine(start, time.min))
    until = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min))
    events = ActivityEvent.objects.filter(
        verb__in=ACTIVITY_VERBS,
        created_at__gte=begin,
        created_at__lt=until,
    )
    edits = ManagerReportTextEditEvent.objects.filter(
        action=ManagerReportTextEditEvent.Action.SAVED,
        created_at__gte=begin,
        created_at__lt=until,
    )
    if company is not None:
        events = events.filter(company_id=company)
        edits = edits.filter(process__company_id=company)

    summary = events.aggregate(
        events=Count("pk"),
        companies=Count("company_id", distinct=True),
        projects=Count("process_id", distinct=True),
        actors=Count("actor_id", distinct=True),
        invitations=Count(
            "pk", filter=Q(verb=ActivityEvent.Verb.INVITE_SENT),
        ),
        assessments_completed=Count(
            "pk", filter=Q(verb=ActivityEvent.Verb.TEST_COMPLETED),
        ),
        candidate_report_opens=Count(
            "pk", filter=Q(verb=ActivityEvent.Verb.CANDIDATE_RESULT_LINK_OPENED),
        ),
        confirmed_manager_pdfs=Count(
            "pk", filter=Q(verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED),
        ),
    )
    summary["manager_text_edits"] = edits.count()

    grouped = events.values("verb").annotate(n=Count("pk"))
    by_verb = {entry["verb"]: entry["n"] for entry in grouped}
    rows = [
        {
            "key": key,
            "name": en if english else sv,
            "count": sum(by_verb.get(verb, 0) for verb in verbs),
        }
        for key, sv, en, verbs in CATEGORIZED_VERBS
    ]
    peak = max((row["count"] for row in rows), default=0)
    for row in rows:
        row["width"] = round(100 * row["count"] / peak) if peak else 0
    return {"totals": summary, "categories": rows}
