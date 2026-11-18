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
    {"manager_report_pdf_generated", "report_export_generated"},
)
CATEGORIZED_VERBS = (
    ("projects", "Projekt och organisationer", "Projects & organisations",
     frozenset(CATEGORIES["organisation"])),
    ("tests", "Kandidater och tester", "Candidates & assessments",
     frozenset(CATEGORIES["candidate"])),
    ("portal", "Kandidatportal", "Candidate portal",
     frozenset(CATEGORIES["portal"])),
    ("exports", "Webbläsarbekräftade rapportfiler", "Browser-reported report files",
     frozenset({"manager_report_pdf_generated", "report_export_generated"})),
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
        report_export_receipts=Count(
            "pk", filter=Q(verb=ActivityEvent.Verb.REPORT_EXPORT_GENERATED),
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


# Static, code-owned report names. Never render arbitrary report_type from JSON
# as a label, and never expose filenames or subject identities.
REPORT_LABELS = {
    "overview": ("Överblick", "Overview"),
    "personality-results": ("Personlighet · Resultat", "Personality · Results"),
    "personality-interpretation": ("Personlighet · AI-tolkning", "Personality · AI interpretation"),
    "personality-questions": ("Personlighet · Frågor", "Personality · Questions"),
    "personality-candidate-reflection": ("Personlighet · Reflektioner", "Personality · Reflections"),
    "motivation-results": ("Motivation · Resultat", "Motivation · Results"),
    "motivation-interpretation": ("Motivation · AI-tolkning", "Motivation · AI interpretation"),
    "motivation-questions": ("Motivation · Frågor", "Motivation · Questions"),
    "motivation-candidate-reflection": ("Motivation · Reflektioner", "Motivation · Reflections"),
    "cognitive-results": ("Färdighet · Resultat", "Ability · Results"),
    "cognitive-interpretation": ("Färdighet · AI-tolkning", "Ability · AI interpretation"),
    "cognitive-questions": ("Färdighet · Frågor", "Ability · Questions"),
    "cognitive-candidate-reflection": ("Färdighet · Reflektioner", "Ability · Reflections"),
    "team-report": ("Individuell teamprofil", "Individual team profile"),
    "leadership-report": ("Ledarskapsrapport", "Leadership report"),
    "derailment-report": ("Urspårningsrapport", "Derailment report"),
    "prepare-interview": ("Inför intervju", "Before interview"),
    "after-overview": ("Helhetsbild", "Overall picture"),
    "after-interview": ("Intervjusammanfattning", "Interview summary"),
    "manager-report": ("Chefsrapport", "Manager report"),
    "candidate-package-pdf": ("Kandidatpaket · sammanslagen PDF", "Candidate package · merged PDF"),
    "candidate-package-zip": ("Kandidatpaket · ZIP", "Candidate package · ZIP"),
    "team-overview": ("Teamrapport", "Team report"),
    "team-profile": ("Individuell teamprofil · team", "Individual team profile · team"),
    "team-profiles-zip": ("Alla teamprofiler · ZIP", "All team profiles · ZIP"),
    "team-package-pdf": ("Teamrapporter · sammanslagen PDF", "Team reports · merged PDF"),
    "team-package-zip": ("Teamrapporter · ZIP", "Team reports · ZIP"),
}


def platform_report_exports(*, start, end, company=None, english=False):
    """Counts browser-reported file preparations, not verified local downloads.

    Distinguish prior dedicated Chefsrapport receipts, PDF vs ZIP and one
    successful *package* from any constituent PDF blobs.
    """
    begin = timezone.make_aware(datetime.combine(start, time.min))
    until = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min))
    qs = ActivityEvent.objects.filter(
        created_at__gte=begin, created_at__lt=until,
        verb__in=[
            ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED,
            ActivityEvent.Verb.REPORT_EXPORT_GENERATED,
        ],
    )
    if company is not None:
        qs = qs.filter(company_id=company)
    grouped = qs.values("verb", "meta__report_type").annotate(count=Count("pk"))
    by_report = {}
    for item in grouped:
        code = ("manager-report"
                if item["verb"] == ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED
                else item["meta__report_type"])
        if code not in REPORT_LABELS:
            continue
        by_report[code] = by_report.get(code, 0) + item["count"]
    rows = []
    for code, count in by_report.items():
        name_sv, name_en = REPORT_LABELS[code]
        rows.append({
            "code": code, "label": name_en if english else name_sv,
            "format": "ZIP" if code.endswith("-zip") else "PDF",
            "count": count,
        })
    rows.sort(key=lambda row: (-row["count"], row["label"]))
    pdf_count = sum(row["count"] for row in rows if row["format"] == "PDF")
    zip_count = sum(row["count"] for row in rows if row["format"] == "ZIP")
    return {
        "total": pdf_count + zip_count,
        "pdf": pdf_count, "zip": zip_count, "rows": rows,
    }
