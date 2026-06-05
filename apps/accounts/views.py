from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.db.models import Count
from django.views.decorators.http import require_POST
from apps.core.integrations.sova import SovaClient
from apps.projects.models import ProjectMeta
from .utils.org_access import get_accessible_orgunit_ids
from apps.processes.views import (
    build_scores_by_competency,
    build_practitioner_report,
    build_manager_report,
    build_candidate_report,
    build_motivation_coaching_report,
)

from django.db.models import Count, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce

from apps.processes.models import (
    Candidate,
    TestProcess,
    TestInvitation,
    HistoricalProcessCandidate,
)

from apps.processes.models import HistoricalCandidateReport

from django.views.decorators.http import require_POST

from apps.processes.forms import (
    TestProcessWizardCreateForm,
    HistoricalTestProcessForm,
    HistoricalCandidateForm,
)

from apps.processes.services.process_recommendations import (
    PROCESS_PURPOSES,
    AVAILABLE_TESTS,
    PURPOSE_RECOMMENDED_TESTS,
    resolve_dev_sova_template,
    build_default_process_name,
)

from apps.processes.forms import HistoricalTestProcessForm, HistoricalCandidateForm

from datetime import datetime, date, time
from apps.activity.services import log_event

from apps.processes.views import build_cognitive_reports_for_test

from apps.processes.views import build_personality_reports_for_candidate
from apps.activity.models import ActivityEvent

from apps.core.utils.auth import is_admin
from apps.processes.models import TestProcess, TestInvitation, Candidate

from .forms import InviteUserForm, OrgUnitForm, UserOrgUnitAccessForm
from .services.invites import send_invite_email
from .decorators import admin_required
from apps.portal.forms import AccountForm as PortalAccountForm, ProfileImageForm
from .utils.permissions import get_user_accessible_accounts

from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from .models import Company, CompanyMember, OrgUnit, UserOrgUnitAccess
from .forms import CompanyMemberAddForm, CompanyForm, CompanyInviteMemberForm, OrgUnitAccessAddForm

from django.db import transaction

from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from .models import UserInvite
from django.utils import timezone

import json
from django.http import JsonResponse
from django.db.models import Count, Q, Max

from django.db.models.functions import Coalesce

from django import template
from django.utils import timezone
from apps.processes.forms import TestProcessCreateForm
import uuid

from apps.processes.forms import CandidateCreateForm
from apps.processes.models import ProcessLabel
from apps.processes.services.send_tests import send_assessments_and_emails


User = get_user_model()

from apps.accounts.utils.org_units import (
    get_or_create_main_org_unit,
    ensure_user_has_default_orgunit,
)


COMPLETED_ACTIVITY_STATUSES = {
    "completed",
    "complete",
    "finished",
    "done",
    "result available",
    "result_available",
}

STARTED_ACTIVITY_STATUSES = {
    "started",
    "in progress",
    "in_progress",
    "completed",
    "complete",
    "finished",
    "done",
    "result available",
    "result_available",
}

SENT_INVITATION_STATUSES = {
    "sent",
    "started",
    "completed",
    "expired",
    "failed",
}


def parse_date_param(value):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def make_aware_start(d):
    if not d:
        return None

    return timezone.make_aware(
        datetime.combine(d, time.min),
        timezone.get_current_timezone(),
    )


def make_aware_end(d):
    if not d:
        return None

    return timezone.make_aware(
        datetime.combine(d, time.max),
        timezone.get_current_timezone(),
    )


def classify_assessment(activity_name):
    name = (activity_name or "").strip().lower()

    if "personality" in name:
        return "personality"

    if "motivation" in name:
        return "motivation"

    if "verbal" in name:
        return "verbal"

    if "numerical" in name:
        return "numerical"

    if "logical" in name:
        return "logical"

    return "other"


def activity_is_completed(activity):
    status = (activity.get("status") or "").strip().lower()
    return status in COMPLETED_ACTIVITY_STATUSES


def activity_is_started(activity):
    status = (activity.get("status") or "").strip().lower()
    return status in STARTED_ACTIVITY_STATUSES


def count_activities_by_status(invitation):
    """
    Counts assessments inside one TestInvitation.

    Sent:
      We count all activities if the invitation has been sent/started/completed.
    Started:
      We count activities whose SOVA status indicates started/completed.
    Completed / billable:
      We count activities whose SOVA status indicates completed.

    Note:
      Billing period filtering is handled at invitation level using completed_at.
    """
    activities = invitation.sova_activities or []

    result = {
        "sent": 0,
        "started": 0,
        "completed": 0,
        "billable": 0,

        "personality": 0,
        "motivation": 0,
        "verbal": 0,
        "numerical": 0,
        "logical": 0,
        "other": 0,
    }

    if not isinstance(activities, list):
        return result

    invitation_was_sent = (
        invitation.status in SENT_INVITATION_STATUSES
        or invitation.invited_at is not None
    )

    for activity in activities:
        if not isinstance(activity, dict):
            continue

        activity_name = activity.get("activity") or activity.get("name") or ""
        assessment_type = classify_assessment(activity_name)

        if invitation_was_sent:
            result["sent"] += 1

        if activity_is_started(activity):
            result["started"] += 1

        if activity_is_completed(activity):
            result["completed"] += 1
            result["billable"] += 1
            result[assessment_type] += 1

    return result


def empty_usage_row(company, org_unit, process):
    return {
        "company": company,
        "org_unit": org_unit,
        "process": process,

        "company_name": company.name if company else "No company",
        "account_name": org_unit.name if org_unit else "No account",
        "account_code": org_unit.unit_code if org_unit else "",
        "process_name": process.name if process else "No process",
        "project_name": (
            process.project_name_snapshot
            or process.project_code
            or "Assessment"
        ) if process else "Assessment",
        "created_by": process.created_by if process else None,
        "created_by_admin": process.created_by_admin if process else None,
        "labels": list(process.labels.all()) if process else [],

        "sent": 0,
        "started": 0,
        "completed": 0,
        "unfinished": 0,
        "billable": 0,

        "personality": 0,
        "motivation": 0,
        "verbal": 0,
        "numerical": 0,
        "logical": 0,
        "other": 0,

        "candidates": set(),
    }


@login_required
@admin_required
def admin_usage_billing(request):
    today = timezone.localdate()
    default_start = today.replace(day=1)

    date_from = parse_date_param(request.GET.get("date_from")) or default_start
    date_to = parse_date_param(request.GET.get("date_to")) or today

    start_dt = make_aware_start(date_from)
    end_dt = make_aware_end(date_to)

    q = (request.GET.get("q") or "").strip()
    company_id = (request.GET.get("company") or "").strip()
    org_unit_id = (request.GET.get("org_unit") or "").strip()
    label_id = (request.GET.get("label") or "").strip()
    created_by_id = (request.GET.get("created_by") or "").strip()
    test_type = (request.GET.get("test_type") or "").strip()
    include_internal = request.GET.get("include_internal") == "1"

    invitations = (
        TestInvitation.objects
        .select_related(
            "candidate",
            "process",
            "process__company",
            "process__org_unit",
            "process__created_by",
            "process__created_by_admin",
        )
        .prefetch_related("process__labels")
        .filter(process__company__isnull=False)
    )

    # We include invitations that were sent OR completed in the selected period.
    # Sent/started numbers use invited_at; completed/billable uses completed_at.
    period_filter = (
        Q(invited_at__gte=start_dt, invited_at__lte=end_dt)
        | Q(completed_at__gte=start_dt, completed_at__lte=end_dt)
    )
    invitations = invitations.filter(period_filter)

    if q:
        invitations = invitations.filter(
            Q(process__company__name__icontains=q)
            | Q(process__org_unit__name__icontains=q)
            | Q(process__org_unit__unit_code__icontains=q)
            | Q(process__name__icontains=q)
            | Q(process__project_name_snapshot__icontains=q)
            | Q(process__project_code__icontains=q)
            | Q(candidate__email__icontains=q)
            | Q(candidate__first_name__icontains=q)
            | Q(candidate__last_name__icontains=q)
        )

    if company_id:
        invitations = invitations.filter(process__company_id=company_id)

    if org_unit_id:
        invitations = invitations.filter(process__org_unit_id=org_unit_id)

    if label_id:
        invitations = invitations.filter(process__labels__id=label_id)

    if created_by_id:
        invitations = invitations.filter(
            Q(process__created_by_id=created_by_id)
            | Q(process__created_by_admin_id=created_by_id)
        )

    if not include_internal:
        invitations = invitations.exclude(
            Q(process__labels__name__iexact="internal")
            | Q(process__labels__name__iexact="demo")
            | Q(process__labels__name__iexact="do not invoice")
            | Q(process__labels__name__iexact="not billable")
        )

    invitations = invitations.distinct().order_by(
        "process__company__name",
        "process__org_unit__name",
        "process__name",
    )

    rows_by_process = {}

    totals = {
        "sent": 0,
        "started": 0,
        "completed": 0,
        "unfinished": 0,
        "billable": 0,
        "personality": 0,
        "motivation": 0,
        "verbal": 0,
        "numerical": 0,
        "logical": 0,
        "other": 0,
        "candidates": set(),
        "processes": set(),
    }

    for invitation in invitations:
        process = invitation.process
        company = process.company
        org_unit = process.org_unit

        key = process.id

        if key not in rows_by_process:
            rows_by_process[key] = empty_usage_row(company, org_unit, process)

        row = rows_by_process[key]

        counts = count_activities_by_status(invitation)

        # Sent/started should only count if the invitation was sent in the period.
        invited_in_period = (
            invitation.invited_at
            and start_dt <= invitation.invited_at <= end_dt
        )

        # Completed/billable should only count if the invitation was completed in the period.
        completed_in_period = (
            invitation.completed_at
            and start_dt <= invitation.completed_at <= end_dt
        )

        if invited_in_period:
            row["sent"] += counts["sent"]
            row["started"] += counts["started"]

        if completed_in_period:
            row["completed"] += counts["completed"]
            row["billable"] += counts["billable"]

            row["personality"] += counts["personality"]
            row["motivation"] += counts["motivation"]
            row["verbal"] += counts["verbal"]
            row["numerical"] += counts["numerical"]
            row["logical"] += counts["logical"]
            row["other"] += counts["other"]

        row["candidates"].add(invitation.candidate_id)

    rows = list(rows_by_process.values())

    # Apply test type filter after counting.
    if test_type:
        rows = [row for row in rows if row.get(test_type, 0) > 0]

    for row in rows:
        row["unfinished"] = max(row["sent"] - row["completed"], 0)
        row["candidate_count"] = len(row["candidates"])

        for key in [
            "sent",
            "started",
            "completed",
            "unfinished",
            "billable",
            "personality",
            "motivation",
            "verbal",
            "numerical",
            "logical",
            "other",
        ]:
            totals[key] += row[key]

        totals["candidates"].update(row["candidates"])
        totals["processes"].add(row["process"].id)

    totals["candidate_count"] = len(totals["candidates"])
    totals["process_count"] = len(totals["processes"])

    companies = Company.objects.order_by("name")
    org_units = OrgUnit.objects.select_related("company").order_by("company__name", "name")
    labels = ProcessLabel.objects.select_related("company").order_by("company__name", "name")

    User = get_user_model()
    creators = (
        User.objects
        .filter(
            Q(test_processes__isnull=False)
            | Q(test_processes_created_as_admin__isnull=False)
        )
        .distinct()
        .order_by("first_name", "last_name", "email")
    )

    return render(request, "admin/accounts/usage_billing.html", {
        "rows": rows,
        "totals": totals,

        "date_from": date_from.strftime("%Y-%m-%d"),
        "date_to": date_to.strftime("%Y-%m-%d"),
        "q": q,
        "selected_company_id": company_id,
        "selected_org_unit_id": org_unit_id,
        "selected_label_id": label_id,
        "selected_created_by_id": created_by_id,
        "selected_test_type": test_type,
        "include_internal": include_internal,

        "companies": companies,
        "org_units": org_units,
        "labels": labels,
        "creators": creators,

        "test_types": [
            ("personality", "Personality"),
            ("motivation", "Motivation"),
            ("verbal", "Verbal"),
            ("numerical", "Numerical"),
            ("logical", "Logical"),
            ("other", "Other"),
        ],
    })

def build_candidate_detail_context(process, invitation):
    candidate = invitation.candidate
    activities = invitation.sova_activities or []

    activity_events = (
        ActivityEvent.objects
        .filter(company=process.company, process=process, candidate=candidate)
        .select_related("actor", "candidate", "invitation")[:50]
    )

    from apps.emails.models import EmailLog

    email_log_ids = [
        (event.meta or {}).get("email_log_id")
        for event in activity_events
        if (event.meta or {}).get("email_log_id")
    ]

    email_logs_by_id = {
        log.id: log
        for log in EmailLog.objects.filter(id__in=email_log_ids)
    }

    for event in activity_events:
        email_log_id = (event.meta or {}).get("email_log_id")
        event.email_log = email_logs_by_id.get(email_log_id)

    def has_real_result(competencies):
        return any(
            comp.get("score") is not None
            or comp.get("stive") is not None
            or comp.get("stive_rounded") is not None
            or comp.get("sten") is not None
            or comp.get("sten_rounded") is not None
            or comp.get("percentile") is not None
            for comp in competencies
        )

    activity_count = len(activities)

    completed_statuses = {
        "completed",
        "complete",
        "finished",
        "done",
        "result available",
        "result_available",
    }

    tests_completed_count = sum(
        1
        for activity in activities
        if (activity.get("status") or "").strip().lower() in completed_statuses
    )

    mq_competencies = []
    personality_competencies = []
    has_motivation_results = False
    has_personality_results = False

    for item in activities:
        activity_name = (item.get("activity") or "").strip().lower()
        competencies = item.get("competencies", []) or []

        is_motivation_activity = (
            activity_name == "motivation questionnaire"
            or activity_name == "sova motivation questionnaire"
            or "motivation" in activity_name
        )

        if is_motivation_activity:
            if has_real_result(competencies):
                has_motivation_results = True

            for comp in competencies:
                mq_competencies.append({
                    "competency": comp.get("competency"),
                    "score": comp.get("stive_rounded"),
                    "stive_rounded": comp.get("stive_rounded"),
                    "stive": comp.get("stive"),
                    "sten_rounded": comp.get("sten_rounded"),
                    "sten": comp.get("sten"),
                    "percentile": comp.get("percentile"),
                })

        is_personality_activity = (
            activity_name == "personality assessment"
            or activity_name == "sova personality questionnaire"
            or "personality" in activity_name
        )

        if is_personality_activity:
            if has_real_result(competencies):
                has_personality_results = True

            for comp in competencies:
                personality_competencies.append({
                    "competency": comp.get("competency"),
                    "sten_rounded": comp.get("sten_rounded"),
                    "sten": comp.get("sten"),
                    "percentile": comp.get("percentile"),
                })

    personality_competencies = sorted(
        personality_competencies,
        key=lambda x: (x.get("competency") or "").lower()
    )

    motivation_scores = build_scores_by_competency(mq_competencies)

    practitioner_report = build_practitioner_report(
        competencies=mq_competencies,
    )

    manager_report = build_manager_report(
        competencies=mq_competencies,
    )

    candidate_report = build_candidate_report(
        competencies=mq_competencies,
    )

    coaching_report = build_motivation_coaching_report(
        competencies=mq_competencies,
    )

    motivation_reports_for_ui = [
        practitioner_report,
        manager_report,
        coaching_report,
        candidate_report,
    ]

    def safe_motivation_score(item):
        return item.get("score") if item.get("score") is not None else -1

    def safe_personality_score(item):
        return item.get("sten_rounded") if item.get("sten_rounded") is not None else -1

    sorted_mq_desc = sorted(
        mq_competencies,
        key=safe_motivation_score,
        reverse=True,
    )

    sorted_personality_desc = sorted(
        personality_competencies,
        key=safe_personality_score,
        reverse=True,
    )

    top_motivations = sorted_mq_desc[:3]
    top_personality_traits = sorted_personality_desc[:3]

    sorted_mq_asc = sorted(
        mq_competencies,
        key=safe_motivation_score,
    )

    sorted_personality_asc = sorted(
        personality_competencies,
        key=safe_personality_score,
    )

    motivation_development_areas = sorted_mq_asc[:2]
    personality_development_areas = sorted_personality_asc[:2]

    numerical_percentile = None
    logical_percentile = None
    verbal_percentile = None

    has_verbal_results = False
    has_logical_results = False
    has_numerical_results = False

    for item in activities:
        activity_name = item.get("activity", "")
        competencies = item.get("competencies", []) or []
        first_comp = competencies[0] if competencies else {}

        percentile = first_comp.get("percentile")

        if activity_name == "Sova Numerical Reasoning Assessment":
            numerical_percentile = percentile
            if percentile is not None:
                has_numerical_results = True

        elif activity_name == "Sova Logical Reasoning Assessment":
            logical_percentile = percentile
            if percentile is not None:
                has_logical_results = True

        elif activity_name == "Sova Verbal Reasoning Assessment":
            verbal_percentile = percentile
            if percentile is not None:
                has_verbal_results = True

    has_ability_results = (
        has_verbal_results
        or has_logical_results
        or has_numerical_results
    )

    ability_reports_for_ui = {
        "overview": [],
        "verbal": build_cognitive_reports_for_test(
            test_key="verbal",
            percentile=verbal_percentile,
        ) if verbal_percentile is not None else None,

        "logical": build_cognitive_reports_for_test(
            test_key="logical",
            percentile=logical_percentile,
        ) if logical_percentile is not None else None,

        "numerical": build_cognitive_reports_for_test(
            test_key="numerical",
            percentile=numerical_percentile,
        ) if numerical_percentile is not None else None,
    }

    if ability_reports_for_ui["verbal"]:
        ability_reports_for_ui["overview"].append({
            "key": "verbal",
            "label": "Verbal",
            "percentile": verbal_percentile,
        })

    if ability_reports_for_ui["logical"]:
        ability_reports_for_ui["overview"].append({
            "key": "logical",
            "label": "Logical",
            "percentile": logical_percentile,
        })

    if ability_reports_for_ui["numerical"]:
        ability_reports_for_ui["overview"].append({
            "key": "numerical",
            "label": "Numerical",
            "percentile": numerical_percentile,
        })

    project_results = invitation.project_results or {}
    reports = invitation.sova_reports or []

    project_scores = (
        project_results.get("project_scores", [])
        if isinstance(project_results, dict)
        else []
    )

    competency_scores = (
        project_results.get("competency_scores", [])
        if isinstance(project_results, dict)
        else []
    )

    overall_score = (
        project_results.get("overall_score")
        if isinstance(project_results, dict)
        and project_results.get("overall_score") is not None
        else invitation.overall_score
    )

    ability_results = []
    motivation_results = []
    all_competencies = []

    for item in activities:
        activity_name = item.get("activity", "") or ""
        item_status = item.get("status", "") or ""
        item_score = item.get("score")
        item_competencies = item.get("competencies", []) or []

        for comp in item_competencies:
            all_competencies.append({
                "activity": activity_name,
                "status": item_status,
                "competency": comp.get("competency"),
                "stive": comp.get("stive"),
                "stive_rounded": comp.get("stive_rounded"),
                "sten": comp.get("sten"),
                "sten_rounded": comp.get("sten_rounded"),
                "percentile": comp.get("percentile"),
                "assessment_centre": comp.get("assessment_centre"),
            })

        if activity_name in {
            "Sova Logical Reasoning Assessment",
            "Sova Numerical Reasoning Assessment",
            "Sova Verbal Reasoning Assessment",
        }:
            first_comp = item_competencies[0] if item_competencies else {}

            label_map = {
                "Sova Logical Reasoning Assessment": "Logical",
                "Sova Numerical Reasoning Assessment": "Numerical",
                "Sova Verbal Reasoning Assessment": "Verbal",
            }

            ability_results.append({
                "activity": activity_name,
                "label": label_map.get(activity_name, activity_name),
                "status": item_status,
                "score": item_score,
                "competency": first_comp.get("competency"),
                "stive": first_comp.get("stive"),
                "stive_rounded": first_comp.get("stive_rounded"),
                "sten": first_comp.get("sten"),
                "sten_rounded": first_comp.get("sten_rounded"),
                "percentile": first_comp.get("percentile"),
            })

        elif activity_name == "Motivation Questionnaire":
            for comp in item_competencies:
                motivation_results.append({
                    "activity": activity_name,
                    "competency": comp.get("competency"),
                    "stive": comp.get("stive"),
                    "stive_rounded": comp.get("stive_rounded"),
                    "sten": comp.get("sten"),
                    "sten_rounded": comp.get("sten_rounded"),
                    "percentile": comp.get("percentile"),
                    "assessment_centre": comp.get("assessment_centre"),
                })

    ability_order = {"Verbal": 1, "Logical": 2, "Numerical": 3}
    ability_results.sort(key=lambda x: ability_order.get(x["label"], 99))

    motivation_results.sort(
        key=lambda x: (x.get("competency") or "").lower()
    )

    library_status_lookup = {
        "cooperative": "not_started",
        "sensitivity": "not_started",
        "teamwork": "not_started",
        "agreeableness": "not_started",
        "empathy": "not_started",
        "tolerance": "not_started",
        "listening": "not_started",
        "warmth": "not_started",
        "supporting": "not_started",
        "developing_others": "not_started",
        "helpfulness": "not_started",
        "considerate": "not_started",
        "connecting": "not_started",
        "open_communication": "not_started",
        "building_networks": "not_started",
        "initiating_contact": "not_started",
        "dynamic": "not_started",
        "energetic": "not_started",
        "enthusiastic": "not_started",
        "risk_appetite": "not_started",
        "influential": "not_started",
        "persuading": "not_started",
        "desire_to_lead": "not_started",
        "assertive": "not_started",
        "goal_focused": "not_started",
        "competitive": "not_started",
        "challenge": "not_started",
        "self_discipline": "not_started",
        "structured": "not_started",
        "planning_and_organising": "not_started",
        "attention_to_detail": "not_started",
        "keeping_promises": "not_started",
        "analytical": "not_started",
        "data_focus": "not_started",
        "evaluating": "not_started",
        "analysing_problems": "not_started",
        "complex_thinking": "not_started",
        "strategic_thinking": "not_started",
        "conceptual": "not_started",
        "curiosity": "not_started",
        "creativity": "not_started",
        "innovating": "not_started",
        "generating_ideas": "not_started",
        "experimenting": "not_started",
        "adaptability": "not_started",
        "adapting_to_change": "not_started",
        "flexible": "not_started",
        "variety": "not_started",
        "straightforward": "not_started",
        "adhering_to_rules": "not_started",
        "candid": "not_started",
        "earnest": "not_started",
        "status_avoidance": "not_started",
        "egalitarian": "not_started",
        "collective": "not_started",
        "avoiding_status": "not_started",
        "modesty": "not_started",
        "humble": "not_started",
        "modest": "not_started",
        "avoiding_attention": "not_started",
        "resilience": "not_started",
        "tough_minded": "not_started",
        "recovering": "not_started",
        "optimistic": "not_started",
        "emotional_control": "not_started",
        "controlling_stress": "not_started",
        "calm": "not_started",
        "composed": "not_started",
        "independence": "not_started",
        "self_reliant": "not_started",
        "self_contained": "not_started",
        "thinking_independently": "not_started",
    }

    personality_reports = build_personality_reports_for_candidate(
        sova_activities=activities,
        library_status_lookup=library_status_lookup,
    )

    available_reports_count = 0

    if has_verbal_results:
        available_reports_count += 2

    if has_numerical_results:
        available_reports_count += 2

    if has_logical_results:
        available_reports_count += 2

    if has_motivation_results:
        available_reports_count += 4

    if has_personality_results:
        available_reports_count += 11

    return {
        "company": process.company,
        "process": process,
        "invitation": invitation,
        "inv": invitation,
        "candidate": candidate,
        "activity_events": activity_events,

        "activities": activities,
        "project_results": project_results,
        "project_scores": project_scores,
        "competency_scores": competency_scores,
        "overall_score": overall_score,
        "reports": reports,

        "ability_results": ability_results,
        "motivation_results": motivation_results,
        "all_competencies": all_competencies,

        "numerical_percentile": numerical_percentile,
        "logical_percentile": logical_percentile,
        "verbal_percentile": verbal_percentile,
        "has_ability_results": has_ability_results,

        "mq_competencies": mq_competencies,
        "personality_competencies": personality_competencies,

        "tests_sent_count": activity_count,
        "tests_completed_count": tests_completed_count,
        "available_reports_count": available_reports_count,
        "email_logs_by_id": email_logs_by_id,

        "top_motivations": top_motivations,
        "top_personality_traits": top_personality_traits,
        "motivation_development_areas": motivation_development_areas,
        "personality_development_areas": personality_development_areas,

        "motivation_scores": motivation_scores,
        "motivation_reports_for_ui": motivation_reports_for_ui,
        "ability_reports_for_ui": ability_reports_for_ui,
        "personality_reports": personality_reports,
        "has_motivation_results": has_motivation_results,
        "has_personality_results": has_personality_results,
    }

def build_invite_link(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("accounts:accept_invite", kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)

def build_invite_uuid_link(request, invite):
    path = reverse("accounts:accept_invite_uuid", kwargs={"invite_id": invite.id})
    return request.build_absolute_uri(path)


from django.db.models import Count, Q


@login_required
def admin_user_detail(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    user_obj = get_object_or_404(User, pk=pk)
    pending_invite = not user_obj.is_active

    invite_link = None
    open_invite_modal = False

    company = Company.objects.filter(memberships__user=user_obj).first()

    # --- POST actions (din befintliga kod) ---
    if request.method == "POST":
        action = request.POST.get("action")
        if action in ("resend_invite_email", "generate_invite_link"):
            if not pending_invite:
                messages.info(request, "Användaren är redan aktiv. Ingen invite behövs.")
                return redirect("accounts:admin_user_detail", pk=user_obj.pk)

            if not company:
                messages.error(request, "Användaren är inte kopplad till något företag.")
                return redirect("accounts:admin_user_detail", pk=user_obj.pk)

            with transaction.atomic():
                UserInvite.objects.filter(
                    user=user_obj,
                    company=company,
                    accepted_at__isnull=True,
                    revoked_at__isnull=True,
                ).update(revoked_at=timezone.now())

                invite = UserInvite.objects.create(
                    user=user_obj,
                    company=company,
                    created_by=request.user,
                )

                invite_link = build_invite_uuid_link(request, invite)

                if user_obj.has_usable_password():
                    user_obj.set_unusable_password()
                if user_obj.is_active:
                    user_obj.is_active = False
                user_obj.save(update_fields=["password", "is_active"])

            if action == "resend_invite_email":
                send_invite_email(request, user_obj, invite_link=invite_link, company=company)
                messages.success(request, f"Inbjudan skickad till {user_obj.email}.")
                return redirect("accounts:admin_user_detail", pk=user_obj.pk)

            open_invite_modal = True
            messages.success(request, "Ny invite-länk genererad.")

    # --- DATA: processer + KPI ---
    processes = (
        TestProcess.objects
        .filter(created_by=user_obj)
        .annotate(invitations_count=Count("invitations", distinct=True))  # <-- ändra related_name om behövs
        .order_by("-created_at")
    )

    processes_count = processes.count()

    invitations_qs = TestInvitation.objects.filter(process__created_by=user_obj)
    invitations_created = invitations_qs.count()
    invitations_completed = invitations_qs.filter(status="completed").count()

    active_processes = processes
    if hasattr(TestProcess, "is_completed"):
        active_processes = processes.filter(is_completed=False)

    orgunit_accesses = (
        UserOrgUnitAccess.objects
        .filter(user=user_obj)
        .select_related("org_unit", "org_unit__company")
        .order_by("org_unit__company__name", "org_unit__name")
    )

    memberships = (
        CompanyMember.objects
        .filter(user=user_obj)
        .select_related("company")
        .order_by("company__name")
    )

    return render(request, "admin/accounts/customer/customer_detail.html", {
        # ✅ använd samma namn som templaten använder
        "user_obj": user_obj,
        "u": user_obj,  # valfritt bakåtkompatibelt om du råkar använda u någonstans

        "company": company,
        "memberships": memberships,

        "processes": processes,
        "active_processes": active_processes,

        # KPI
        "processes_count": processes_count,
        "invitations_created": invitations_created,
        "invitations_completed": invitations_completed,

        "pending_invite": pending_invite,
        "invite_link": invite_link,
        "open_invite_modal": open_invite_modal,

        "orgunit_accesses": orgunit_accesses,
    })


@login_required
def admin_customers_list(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    role = (request.GET.get("role") or "").strip()
    sort = (request.GET.get("sort") or "newest").strip()

    users = (
        User.objects
        .all()
        .prefetch_related(
            "company_memberships__company",
            "company_memberships__primary_org_unit",
        )
    )

    if q:
        users = users.filter(
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(username__icontains=q) |
            Q(company_memberships__company__name__icontains=q)
        ).distinct()

    if status == "active":
        users = users.filter(is_active=True)
    elif status == "pending":
        users = users.filter(is_active=False)

    if role == "admin":
        users = users.filter(Q(is_staff=True) | Q(is_superuser=True))
    elif role == "customer":
        users = users.filter(is_staff=False, is_superuser=False)

    sort_map = {
        "newest": "-date_joined",
        "oldest": "date_joined",
        "name": "first_name",
        "-name": "-first_name",
        "email": "email",
        "-email": "-email",
    }

    users = users.order_by(sort_map.get(sort, "-date_joined"))

    return render(request, "admin/accounts/customer/customers_list.html", {
        "customers": users,
        "q": q,
        "status": status,
        "role": role,
        "sort": sort,
    })


@login_required
def admin_customers_create(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    if request.method == "POST":
        form = InviteUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_unusable_password()
            user.is_active = False
            user.save()

            send_invite_email(request, user)
            messages.success(request, f"Invite sent to {user.email}.")
            return redirect("accounts:admin_customers_list")

        messages.error(request, "Could not create invite. Check the form fields.")
    else:
        form = InviteUserForm()

    return render(request, "admin/accounts/customer/customers_create.html", {"form": form})


def accept_invite(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, "accounts/invite_invalid.html", status=400)

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            user.is_active = True
            user.save(update_fields=["is_active"])

            login(request, user)
            messages.success(request, "Password set. Welcome to Talena!")
            return redirect("core:post_login_redirect")
    else:
        form = SetPasswordForm(user)

    return render(request, "accounts/accept_invite.html", {"form": form, "user": user})


@login_required
def admin_process_detail(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    process = get_object_or_404(
        TestProcess.objects.prefetch_related("labels"),
        pk=pk
    )

    invitations = (
        TestInvitation.objects
        .filter(process=process)
        .select_related("candidate")
        .order_by("-created_at")
    )

    # Snabb statistik
    status_counts = {}
    for inv in invitations:
        status_counts[inv.status] = status_counts.get(inv.status, 0) + 1

    total_sent = invitations.count()

    return render(request, "admin/accounts/customer/process_detail.html", {
        "process": process,
        "invitations": invitations,
        "status_counts": status_counts,
        "total_sent": total_sent,
        "self_reg_url": request.build_absolute_uri(process.get_self_registration_url()),
    })


@login_required
def admin_candidate_detail(request, process_pk, candidate_pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    process = get_object_or_404(TestProcess, pk=process_pk)

    invitation = get_object_or_404(
        TestInvitation.objects.select_related("candidate"),
        process=process,
        candidate_id=candidate_pk,
    )

    ctx = build_candidate_detail_context(
        process=process,
        invitation=invitation,
    )

    ctx["is_admin_view"] = True

    return render(
        request,
        "admin/accounts/customer/candidate_detail.html",
        ctx,
    )


from django.db.models import Count, Q

@login_required
@admin_required
def company_list(request):
    q = (request.GET.get("q") or "").strip()
    sort = request.GET.get("sort") or "name"

    qs = (
        Company.objects
        .annotate(
            member_count=Count("memberships", distinct=True),
            orgunit_count=Count("org_units", distinct=True),
            last_activity=Max("memberships__user__last_login"),
            pending_invites=Count("memberships", filter=Q(memberships__user__is_active=False), distinct=True),
        )
    )

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(org_number__icontains=q)
        )

    sort_map = {
        "name": "name",
        "-name": "-name",
        "members": "-member_count",
        "units": "-orgunit_count",
        "newest": "-created_at",  # om du har created_at
        "oldest": "created_at",
        "pending": "-pending_invites",
        "activity": "-last_activity",
    }
    qs = qs.order_by(sort_map.get(sort, "name"))

    return render(request, "admin/accounts/companies/company_list.html", {
        "companies": qs,
        "q": q,
        "sort": sort,
    })



@login_required
@admin_required
def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk)

    # ------------------------------------------------------------
    # KPI:er (samma logik som stats, men för overview)
    # ------------------------------------------------------------
    users_count = CompanyMember.objects.filter(company=company).count()

    orgunits_qs = OrgUnit.objects.filter(company=company)
    accounts_total = orgunits_qs.count()
    accounts_root = orgunits_qs.filter(parent__isnull=True).count()
    accounts_sub = accounts_total - accounts_root

    processes_qs = TestProcess.objects.filter(company=company)
    processes_count = processes_qs.count()

    invitations_qs = TestInvitation.objects.filter(process__company=company)
    invitations_count = invitations_qs.count()

    company_created_event = (
        ActivityEvent.objects
        .filter(
            company=company,
            verb=ActivityEvent.Verb.COMPANY_CREATED,
        )
        .select_related("actor")
        .order_by("created_at")
        .first()
    )

    active_users_count = CompanyMember.objects.filter(
        company=company,
        user__is_active=True,
    ).count()

    pending_users_count = CompanyMember.objects.filter(
        company=company,
        user__is_active=False,
    ).count()

    candidate_invitations_count = invitations_qs.count()

    started_candidates_count = invitations_qs.filter(
        status__in=["started", "completed"]
    ).count()

    completed_candidates_count = invitations_qs.filter(
        status="completed"
    ).count()

    historical_candidate_count_subquery = (
        HistoricalProcessCandidate.objects
        .filter(process=OuterRef("pk"))
        .values("process")
        .annotate(count=Count("id"))
        .values("count")
    )

    latest_processes = (
        TestProcess.objects
        .filter(company=company)
        .select_related("created_by", "org_unit")
        .annotate(
            live_candidates_count=Count("invitations", distinct=True),
            historical_candidates_count=Coalesce(
                Subquery(
                    historical_candidate_count_subquery,
                    output_field=IntegerField(),
                ),
                0,
            ),
        )
        .order_by("-created_at")[:4]
    )

    candidates_count = invitations_qs.values("candidate_id").distinct().count()

    invitation_status = (
        invitations_qs
        .values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # ------------------------------------------------------------
    # Listor för overview (liten “preview”)
    # ------------------------------------------------------------
    memberships = (
        CompanyMember.objects
        .filter(company=company)
        .select_related("user")
        .order_by("user__email")
    )

    recent_memberships = memberships[:6]  # lagom för en overview-preview

    # Modaler / actions (om du vill kunna bjuda in härifrån)
    invite_form = CompanyInviteMemberForm()


    # Kandidater (unika via invitations i företaget)
    candidate_rows = (
        TestInvitation.objects
        .filter(process__company=company)
        .select_related("candidate", "process")
        .order_by("candidate__name")
    )

    invitations_created = (
        invitations_qs
        .filter(status="created")
        .count()
    )

    # ------------------------------------------------------------
    # Render
    # ------------------------------------------------------------
    return render(request, "admin/accounts/companies/company_detail.html", {
        "company": company,
        "active_tab": "overview",
        "show_invite_button": True,

        # KPI
        "users_count": users_count,
        "accounts_total": accounts_total,
        "accounts_root": accounts_root,
        "accounts_sub": accounts_sub,
        "processes_count": processes_count,
        "candidates_count": candidates_count,
        "invitations_count": invitations_count,
        "invitation_status": invitation_status,
        "candidate_rows": candidate_rows,
        "invitations_created": invitations_created,

        # Preview-data
        "memberships": memberships,
        "recent_memberships": recent_memberships,

        # Modal/form
        "invite_form": invite_form,
        "active": "overview",

        "company_created_event": company_created_event,
        "active_users_count": active_users_count,
        "pending_users_count": pending_users_count,

        "candidate_invitations_count": candidate_invitations_count,
        "started_candidates_count": started_candidates_count,
        "completed_candidates_count": completed_candidates_count,

        "latest_processes": latest_processes,
    })



@login_required
@admin_required
@require_POST
def company_member_remove(request, company_pk, user_pk):
    company = get_object_or_404(Company, pk=company_pk)
    membership = get_object_or_404(CompanyMember, company=company, user_id=user_pk)
    email = membership.user.email
    membership.delete()
    messages.success(request, f"{email} togs bort från {company.name}.")
    return redirect("accounts:company_detail", pk=company.pk)


@login_required
@admin_required
@require_POST
def company_member_update_role(request, company_pk, user_pk):
    company = get_object_or_404(Company, pk=company_pk)
    membership = get_object_or_404(CompanyMember, company=company, user_id=user_pk)

    form = CompanyMemberRoleForm(request.POST)
    if form.is_valid():
        membership.role = form.cleaned_data["role"]
        membership.save(update_fields=["role"])
        messages.success(request, "Rollen uppdaterades.")
    else:
        messages.error(request, "Kunde inte uppdatera rollen.")

    return redirect("accounts:company_detail", pk=company.pk)




@login_required
@admin_required
def company_create(request):
    if request.method == "POST":
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save()

            main_unit = get_or_create_main_org_unit(company)

            log_event(
                company=company,
                actor=request.user,
                verb=ActivityEvent.Verb.COMPANY_CREATED,
                meta={
                    "company_id": company.id,
                    "company_name": company.name,
                    "org_number": company.org_number,
                    "default_org_unit_id": main_unit.id,
                    "default_org_unit_name": main_unit.name,
                },
            )

            messages.success(request, f"Företag '{company.name}' skapat.")
            return redirect("accounts:company_detail", pk=company.pk)
    else:
        form = CompanyForm()

    return render(request, "admin/accounts/companies/company_form.html", {
        "form": form,
        "is_create": True,
    })

def accept_invite_uuid(request, invite_id):
    invite = get_object_or_404(UserInvite, id=invite_id)

    # Ogiltig om revoked eller redan accepterad
    if invite.revoked_at is not None or invite.accepted_at is not None:
        return render(request, "accounts/invite_invalid.html", status=400)

    user = invite.user

    # Om användaren redan är aktiv: låt den logga in istället
    if user.is_active:
        messages.info(request, "Kontot är redan aktiverat. Logga in.")
        return redirect("login")

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            user.is_active = True
            user.save(update_fields=["is_active"])

            invite.accepted_at = timezone.now()
            invite.save(update_fields=["accepted_at"])

            log_event(
                company=invite.company,
                actor=user,
                verb=ActivityEvent.Verb.COMPANY_INVITE_ACCEPTED,
                meta={
                    "company_id": invite.company.id,
                    "company_name": invite.company.name,
                    "user_id": user.id,
                    "user_email": user.email,
                    "user_name": user.get_full_name(),
                    "invite_id": str(invite.id),
                },
            )

            login(request, user)
            return redirect("core:post_login_redirect")
    else:
        form = SetPasswordForm(user)

    return render(request, "accounts/accept_invite.html", {"form": form, "user": user})


@login_required
@admin_required
@require_POST
def orgunit_move(request, company_pk):
    """
    Tar emot JSON:
      { "unit_id": 123, "new_parent_id": 456 }   -> flytta under annan
      { "unit_id": 123, "new_parent_id": null }  -> gör root
    """
    company = get_object_or_404(Company, pk=company_pk)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON."}, status=400)

    unit_id = payload.get("unit_id")
    new_parent_id = payload.get("new_parent_id", None)

    if not unit_id:
        return JsonResponse({"ok": False, "error": "unit_id is required."}, status=400)

    unit = get_object_or_404(OrgUnit, pk=unit_id, company=company)

    new_parent = None
    if new_parent_id:
        new_parent = get_object_or_404(OrgUnit, pk=new_parent_id, company=company)

        # skydd: förhindra loop (lägga under sig själv eller sin egen subtree)
        cur = new_parent
        while cur:
            if cur.pk == unit.pk:
                return JsonResponse({"ok": False, "error": "Cannot move unit under itself/descendant."}, status=400)
            cur = cur.parent

    with transaction.atomic():
        unit.parent = new_parent
        unit.save(update_fields=["parent"])

    return JsonResponse({
        "ok": True,
        "unit_id": unit.pk,
        "new_parent_id": new_parent.pk if new_parent else None,
    })

@login_required
@admin_required
def company_account_structure(request, pk):
    company = get_object_or_404(Company, pk=pk)

    orgunit_form = OrgUnitForm(company=company)

    # Tree
    all_units = (
        OrgUnit.objects
        .filter(company=company)
        .select_related("parent")
        .order_by("name")
    )
    children_map = {}
    for u in all_units:
        children_map.setdefault(u.parent_id, []).append(u)
    root_units = children_map.get(None, [])

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_orgunit":
            orgunit_form = OrgUnitForm(request.POST, company=company)
            if orgunit_form.is_valid():
                unit = orgunit_form.save(commit=False)
                unit.company = company
                unit.save()
                messages.success(request, f"Enhet '{unit.name}' skapad.")
                return redirect("accounts:company_account_structure", pk=company.pk)
            messages.error(request, "Kunde inte skapa enhet. Kontrollera fälten.")

    return render(request, "admin/accounts/companies/company_account_structure.html", {
        "company": company,
        "orgunit_form": orgunit_form,
        "root_units": root_units,
        "children_map": children_map,
        "active": "structure",
        "show_invite_button": True,
        "invite_form": CompanyInviteMemberForm(),
    })


@login_required
@admin_required
def company_user_access(request, pk):
    company = get_object_or_404(Company, pk=pk)

    # alla users i bolaget
    users = (
        User.objects
        .filter(company_memberships__company=company)
        .distinct()
        .order_by("email")
    )

    # vilken user är vald?
    selected_user_id = request.GET.get("user")
    selected_user = None
    selected_membership = None
    selected_primary_id = None

    if selected_user_id:
        selected_user = get_object_or_404(User, pk=selected_user_id)

        # säkerhet: måste vara medlem i företaget
        if not CompanyMember.objects.filter(company=company, user=selected_user).exists():
            return HttpResponseForbidden("No access.")

        selected_membership = (
            CompanyMember.objects
            .filter(company=company, user=selected_user)
            .select_related("primary_org_unit")
            .first()
        )
        selected_primary_id = selected_membership.primary_org_unit_id if selected_membership else None

    # accounts/orgunits för checkbox-lista
    all_units = (
        OrgUnit.objects
        .filter(company=company)
        .select_related("parent")
        .order_by("name")
    )
    children_map = {}
    for u in all_units:
        children_map.setdefault(u.parent_id, []).append(u)
    root_units = children_map.get(None, [])

    # prechecked för vald user
    checked_ids = set()
    if selected_user:
        checked_ids = set(
            UserOrgUnitAccess.objects
            .filter(user=selected_user, org_unit__company=company)
            .values_list("org_unit_id", flat=True)
        )

    # ✅ permission map (måste ligga EFTER att selected_user är satt)
    perm_map = {}
    if selected_user:
        perm_map = dict(
            UserOrgUnitAccess.objects
            .filter(user=selected_user, org_unit__company=company)
            .values_list("org_unit_id", "permission")  # byt till permission_level om ditt fältnamn heter så
        )

    return render(request, "admin/accounts/companies/company_user_access.html", {
        "company": company,
        "users": users,
        "selected_user": selected_user,
        "root_units": root_units,
        "children_map": children_map,
        "checked_ids": checked_ids,
        "selected_membership": selected_membership,
        "selected_primary_id": selected_primary_id,
        "perm_map": perm_map,
        "all_units": all_units,
        "active": "access",
        "show_invite_button": True,
        "invite_form": CompanyInviteMemberForm(),
    })


@login_required
@admin_required
def company_user_access_state(request, company_pk):
    company = get_object_or_404(Company, pk=company_pk)
    user_id = request.GET.get("user_id")
    if not user_id:
        return JsonResponse({"ok": False, "error": "user_id required"}, status=400)

    user = get_object_or_404(User, pk=user_id)

    if not CompanyMember.objects.filter(company=company, user=user).exists():
        return JsonResponse({"ok": False, "error": "User not in company"}, status=403)

    checked_ids = list(
        UserOrgUnitAccess.objects
        .filter(user=user, org_unit__company=company)
        .values_list("org_unit_id", flat=True)
    )
    return JsonResponse({"ok": True, "checked_ids": checked_ids})



@login_required
@admin_required
@require_POST
def set_active_org_unit(request, company_pk):
    company = get_object_or_404(Company, pk=company_pk)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    unit_id = payload.get("unit_id")
    if not unit_id:
        return JsonResponse({"ok": False, "error": "unit_id required"}, status=400)

    unit = get_object_or_404(OrgUnit, pk=unit_id, company=company)

    accessible_ids = get_accessible_orgunit_ids(request.user, company)
    if unit.id not in accessible_ids:
        return JsonResponse({"ok": False, "error": "No access to this org unit"}, status=403)

    request.session["active_org_unit_id"] = unit.id
    return JsonResponse({"ok": True, "active_org_unit_id": unit.id, "active_org_unit_name": unit.name})


@login_required
@admin_required
@require_POST
def company_user_access_set(request, company_pk):
    company = get_object_or_404(Company, pk=company_pk)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    user_id = payload.get("user_id")
    mode = payload.get("mode")
    access = payload.get("access", [])  # <-- NEW
    primary_org_unit_id = payload.get("primary_org_unit_id")  # <-- NEW

    if not user_id or mode != "replace" or not isinstance(access, list):
        return JsonResponse({"ok": False, "error": "user_id + mode='replace' + access[] required"}, status=400)

    user = get_object_or_404(User, pk=user_id)

    if not CompanyMember.objects.filter(company=company, user=user).exists():
        return JsonResponse({"ok": False, "error": "User not in company"}, status=403)

    # Validate access rows
    requested_ids = []
    perm_by_id = {}

    allowed_perms = {"viewer", "editor", "own"}

    for row in access:
        try:
            oid = int(row.get("org_unit_id"))
        except Exception:
            return JsonResponse({"ok": False, "error": "Invalid org_unit_id in access"}, status=400)

        perm = (row.get("permission") or "").strip()
        if perm not in allowed_perms:
            return JsonResponse({"ok": False, "error": f"Invalid permission '{perm}'"}, status=400)

        requested_ids.append(oid)
        perm_by_id[oid] = perm

    # Ensure units exist in this company
    units = list(OrgUnit.objects.filter(company=company, id__in=requested_ids))
    found_ids = {u.id for u in units}
    missing = sorted(list(set(requested_ids) - found_ids))
    if missing:
        return JsonResponse({"ok": False, "error": f"Invalid unit_ids for company: {missing}"}, status=400)

    # Validate primary (optional)
    primary_unit = None
    if primary_org_unit_id:
        try:
            primary_org_unit_id = int(primary_org_unit_id)
        except Exception:
            return JsonResponse({"ok": False, "error": "Invalid primary_org_unit_id"}, status=400)

        primary_unit = OrgUnit.objects.filter(company=company, id=primary_org_unit_id).first()
        if not primary_unit:
            return JsonResponse({"ok": False, "error": "Primary org unit not in company"}, status=400)

        # rekommenderat: primary måste vara vald i access
        if primary_unit.id not in set(requested_ids):
            return JsonResponse({"ok": False, "error": "Primary org unit must be selected for the user"}, status=400)

    with transaction.atomic():
        # Replace access rows
        UserOrgUnitAccess.objects.filter(user=user, org_unit__company=company).delete()

        objs = []
        for u in units:
            objs.append(UserOrgUnitAccess(
                user=user,
                org_unit=u,
                permission=perm_by_id[u.id],
            ))
        if objs:
            UserOrgUnitAccess.objects.bulk_create(objs)

        # Save primary on CompanyMember
        membership = CompanyMember.objects.get(company=company, user=user)
        membership.primary_org_unit = primary_unit
        membership.save(update_fields=["primary_org_unit"])

    return JsonResponse({"ok": True, "action": "replaced", "count": len(objs)})



@login_required
@admin_required
def company_users(request, pk):
    company = get_object_or_404(Company, pk=pk)

    memberships = (
        CompanyMember.objects
        .filter(company=company)
        .select_related("user")
        .order_by("user__email")
    )

    invite_form = CompanyInviteMemberForm()  # ✅ behövs för modalen

    return render(request, "admin/accounts/companies/company_users.html", {
        "company": company,
        "memberships": memberships,
        "active": "users",
        "show_invite_button": True,  # så knappen syns uppe i headern
        "invite_form": invite_form,  # ✅
    })


@login_required
@admin_required
def company_stats(request, pk):
    company = get_object_or_404(Company, pk=pk)

    # --- Users / Accounts ---
    users_count = CompanyMember.objects.filter(company=company).count()

    orgunits_qs = OrgUnit.objects.filter(company=company)
    accounts_total = orgunits_qs.count()
    accounts_root = orgunits_qs.filter(parent__isnull=True).count()
    accounts_sub = accounts_total - accounts_root

    # Users per account (OrgUnit)
    users_per_unit = (
        UserOrgUnitAccess.objects
        .filter(org_unit__company=company)
        .values("org_unit_id", "org_unit__name", "org_unit__unit_code")
        .annotate(user_count=Count("user", distinct=True))
        .order_by("-user_count", "org_unit__name")
    )

    # --- Process / candidates / invitations ---
    # Välj EN av varianterna nedan beroende på din datamodell.

    # VARIANT A: Om TestProcess har FK -> company
    processes_qs = TestProcess.objects.filter(company=company)
    processes_count = processes_qs.count()

    # Invitations
    invitations_qs = TestInvitation.objects.filter(process__company=company)
    invitations_count = invitations_qs.count()
    invite_form = CompanyInviteMemberForm()

    # Candidates (distinct candidates invited in this company)
    candidates_count = invitations_qs.values("candidate_id").distinct().count()

    # (Valfritt) status breakdown, snyggt för “Skickade tester”
    invitation_status = (
        invitations_qs
        .values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    invitations_created = (
        invitations_qs
        .filter(status="created")
        .count()
    )

    return render(request, "admin/accounts/companies/company_stats.html", {
        "company": company,
        "active": "stats",
        "show_invite_button": True,

        "users_count": users_count,
        "accounts_total": accounts_total,
        "accounts_root": accounts_root,
        "accounts_sub": accounts_sub,

        "processes_count": processes_count,
        "candidates_count": candidates_count,
        "invitations_count": invitations_count,
        "invitation_status": invitation_status,
        "invitations_created": invitations_created,
        "invite_form": invite_form,

        "users_per_unit": users_per_unit,
    })



@login_required
def admin_process_create_for_user(request, user_pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    user_obj = get_object_or_404(User, pk=user_pk)

    next_url = request.GET.get("next") or reverse(
        "accounts:admin_user_detail",
        kwargs={"pk": user_obj.pk}
    )

    client = SovaClient()
    error = None

    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    choices = []
    template_cards = []
    project_id_map = {}

    for a in accounts:
        acc = (a.get("code") or "").strip()
        for p in (a.get("projects") or []):
            proj_code = (p.get("code") or "").strip()
            sova_name = (p.get("name") or proj_code).strip()

            value = f"{acc}|{proj_code}"
            project_id_map[value] = p.get("id")

            meta = meta_map.get((acc, proj_code))
            title = (getattr(meta, "intern_name", None) or sova_name)

            choices.append((value, title))
            template_cards.append({
                "value": value,
                "title": title,
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
                "sova_project_id": p.get("id"),
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    if request.method == "POST":
        form = TestProcessCreateForm(request.POST)
        form.fields["sova_template"].choices = choices

        if form.is_valid():
            # --- labels text normalize ---
            raw_labels = form.cleaned_data.get("labels_text", "")
            if isinstance(raw_labels, (list, tuple)):
                labels_text = ", ".join([str(x).strip() for x in raw_labels if str(x).strip()])
            else:
                labels_text = str(raw_labels or "").strip()

            obj = form.save(commit=False)

            value = form.cleaned_data["sova_template"]
            acc, proj = value.split("|", 1)

            # ✅ Company kopplad till kunden (user_obj)
            company_id = (
                CompanyMember.objects
                .filter(user=user_obj)
                .values_list("company_id", flat=True)
                .first()
            )
            if not company_id:
                form.add_error(None, "Kunden är inte kopplad till något företag.")
                return render(request, "admin/accounts/customer/process_create.html", {
                    "user_obj": user_obj,
                    "form": form,
                    "error": error,
                    "template_cards": template_cards,
                    "next_url": next_url,
                    "templates_count": len(template_cards),
                    "accounts_count": len(accounts),
                })

            # ✅ Membership + primary org unit
            membership = (
                CompanyMember.objects
                .filter(company_id=company_id, user=user_obj)
                .select_related("primary_org_unit")
                .first()
            )

            company = get_object_or_404(Company, pk=company_id)

            membership, primary_unit, access = ensure_user_has_default_orgunit(
                user=user_obj,
                company=company,
                permission="own",
            )

            # ✅ Set required fields
            obj.company = company
            obj.org_unit = primary_unit

            obj.provider = "sova"
            obj.account_code = acc
            obj.project_code = proj
            obj.sova_project_id = project_id_map.get(value)

            meta = meta_map.get((acc, proj))
            obj.project_name_snapshot = (getattr(meta, "intern_name", None) or "")
            if not obj.project_name_snapshot:
                match = next((t for t in template_cards if t["value"] == value), None)
                obj.project_name_snapshot = (match["sova_name"] if match else proj)

            obj.created_by = user_obj
            obj.created_by_admin = request.user  # om fältet finns
            obj.save()

            # ✅ Labels
            if labels_text:
                parts = [p.strip() for p in labels_text.replace("\n", ",").split(",")]
                parts = [p for p in parts if p]

                label_objs = []
                for name in parts:
                    lab, _ = ProcessLabel.objects.get_or_create(company_id=company_id, name=name)
                    label_objs.append(lab)

                obj.labels.set(label_objs)
            else:
                obj.labels.clear()

            messages.success(request, "Testprocess skapad.")
            return redirect(next_url)

        messages.error(request, "Kunde inte skapa testprocess. Kontrollera fälten.")
    else:
        form = TestProcessCreateForm()
        form.fields["sova_template"].choices = choices

    return render(request, "admin/accounts/customer/process_create.html", {
        "user_obj": user_obj,
        "form": form,
        "error": error,
        "template_cards": template_cards,
        "next_url": next_url,
        "templates_count": len(template_cards),
        "accounts_count": len(accounts),
    })

@login_required
def admin_process_update(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    obj = get_object_or_404(TestProcess.objects.prefetch_related("labels"), pk=pk)

    next_url = request.GET.get("next") or reverse(
        "accounts:admin_process_detail", kwargs={"pk": obj.pk}
    )

    old_acc = (obj.account_code or "").strip()
    old_proj = (obj.project_code or "").strip()
    locked = obj.is_template_locked()

    client = SovaClient()
    error = None

    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    choices = []
    template_cards = []

    for a in accounts:
        acc = (a.get("code") or "").strip()
        for p in (a.get("projects") or []):
            proj_code = (p.get("code") or "").strip()
            sova_name = (p.get("name") or proj_code).strip()

            meta = meta_map.get((acc, proj_code))
            title = (getattr(meta, "intern_name", None) or sova_name)

            value = f"{acc}|{proj_code}"
            choices.append((value, title))

            template_cards.append({
                "value": value,
                "title": title,
                "subtitle": f"{acc} · {proj_code}",
                "icon": "layers",
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    current_value = f"{old_acc}|{old_proj}" if old_acc and old_proj else None

    # ✅ Förifyll labels_text från M2M
    existing_labels_text = ", ".join(obj.labels.values_list("name", flat=True))

    def normalize_labels(raw):
        # raw kan vara str eller lista
        if isinstance(raw, (list, tuple)):
            labels_text = ", ".join([str(x).strip() for x in raw if str(x).strip()])
        else:
            labels_text = str(raw or "").strip()

        # splitta på komma / radbrytning, ta bort tomma, unika (case-insensitive)
        parts = []
        seen = set()
        for chunk in labels_text.replace("\n", ",").split(","):
            name = chunk.strip()
            key = name.lower()
            if name and key not in seen:
                seen.add(key)
                parts.append(name)
        return parts

    if request.method == "POST":
        form = TestProcessCreateForm(request.POST, instance=obj)
        form.fields["sova_template"].choices = choices
        if current_value:
            form.fields["sova_template"].initial = current_value

        if form.is_valid():
            updated = form.save(commit=False)

            value = form.cleaned_data["sova_template"]
            acc, proj = value.split("|", 1)

            if locked and ((acc.strip() != old_acc) or (proj.strip() != old_proj)):
                messages.error(
                    request,
                    "Du kan inte ändra testpaket efter att tester har skickats i processen."
                )
                return redirect(f"{reverse('accounts:admin_process_update', kwargs={'pk': obj.pk})}?next={next_url}")

            updated.provider = "sova"
            updated.account_code = acc
            updated.project_code = proj

            meta = meta_map.get((acc, proj))
            if meta and getattr(meta, "intern_name", None):
                updated.project_name_snapshot = meta.intern_name
            else:
                match = next((t for t in template_cards if t["value"] == value), None)
                updated.project_name_snapshot = (match["sova_name"] if match else proj)

            updated.save()

            # ✅ Spara labels (ManyToMany) efter save
            company_id = updated.company_id
            parts = normalize_labels(form.cleaned_data.get("labels_text", ""))

            if parts:
                label_objs = []
                for name in parts:
                    lab, _ = ProcessLabel.objects.get_or_create(company_id=company_id, name=name)
                    label_objs.append(lab)
                updated.labels.set(label_objs)
            else:
                updated.labels.clear()

            messages.success(request, "Process uppdaterad.")
            return redirect(next_url)

        messages.error(request, "Kunde inte spara. Kontrollera fälten.")

    else:
        form = TestProcessCreateForm(instance=obj)
        form.fields["sova_template"].choices = choices
        if current_value:
            form.fields["sova_template"].initial = current_value

        # ✅ Viktigt: initial på labels_text i GET
        if "labels_text" in form.fields:
            form.fields["labels_text"].initial = existing_labels_text

    return render(request, "admin/accounts/customer/process_edit.html", {
        "form": form,
        "process": obj,
        "error": error,
        "template_cards": template_cards,
        "template_locked": locked,
        "next_url": next_url,
    })


@admin_required
@require_POST
def admin_remove_candidate_from_process(request, process_id, candidate_id):
    process = get_object_or_404(TestProcess, pk=process_id)

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate_id=candidate_id,
    )
    invitation.delete()
    messages.success(request, "Kandidaten togs bort från processen.")
    return redirect("accounts:admin_process_detail", pk=process.id)


@admin_required
def admin_process_send_tests(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    if process.is_historical or not process.sova_sync_enabled:
        messages.error(request, "This is a historical process and cannot send SOVA invitations.")
        return redirect("accounts:admin_process_detail", pk=process.pk)

    if request.method != "POST":
        return redirect("accounts:admin_process_detail", pk=process.pk)

    invitation_ids = request.POST.getlist("invitation_ids")
    if not invitation_ids:
        messages.warning(request, "Välj minst en kandidat.")
        return redirect("accounts:admin_process_detail", pk=process.pk)

    invitations = (
        TestInvitation.objects
        .filter(process=process, id__in=invitation_ids)
        .select_related("candidate")
    )

    result = send_assessments_and_emails(
        process=process,
        invitations=invitations,
        actor_user=request.user,
        context="admin",
    )

    if result["sent_count"]:
        messages.success(request, f"Skickade test till {result['sent_count']} kandidat(er).")

    if result["errors"]:
        for err in result["errors"]:
            messages.error(request, f"Kunde inte skicka till {err['email']}: {err['error']}")

    if result["sent_count"] == 0:
        if result["skipped_count"]:
            messages.info(request, "Inget skickades (alla markerade var redan skickade/igång/klara).")
        else:
            messages.warning(request, "Inget skickades. Kolla felmeddelanden ovan.")

    return redirect("accounts:admin_process_detail", pk=process.pk)



@admin_required
def admin_process_invitation_statuses(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    qs = (
        TestInvitation.objects
        .filter(process=process)
        .select_related("candidate")
        .order_by("created_at")
    )

    return JsonResponse({
        "invitations": [
            {
                "id": inv.id,
                "status": inv.status,
                "completed_at": inv.completed_at.isoformat() if inv.completed_at else None,
                "sova_overall_status": getattr(inv, "sova_overall_status", "") or "",
            }
            for inv in qs
        ]
    })



@login_required
@admin_required
def admin_process_add_candidate(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if request.method == "POST":
        form = CandidateCreateForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()

            candidate, created = Candidate.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": form.cleaned_data["first_name"],
                    "last_name": form.cleaned_data["last_name"],
                }
            )

            invitation, inv_created = TestInvitation.objects.get_or_create(
                process=process,
                candidate=candidate,
                defaults={
                    "source": "invited",
                    "status": "created",
                    "invited_by": request.user,
                },
            )

            if not inv_created and invitation.source == "invited" and invitation.invited_by_id is None:
                invitation.invited_by = request.user
                invitation.save(update_fields=["invited_by"])


            if inv_created:
                msg = f"{candidate.email} har lagts till i processen."
                messages.success(request, msg)
            else:
                msg = f"{candidate.email} är redan i processen."
                messages.info(request, msg)

            if is_ajax:
                return JsonResponse({
                    "ok": True,
                    "message": msg,
                    "redirect_url": reverse("accounts:admin_process_detail", kwargs={"pk": process.pk})
                })

            return redirect("accounts:admin_process_detail", pk=process.pk)

        # Ogiltigt form
        if is_ajax:
            return render(
                request,
                "admin/accounts/customer/_add_candidate_form.html",
                {"process": process, "form": form},
                status=400
            )

    else:
        form = CandidateCreateForm()

    # GET: om AJAX -> partial, annars hel sida (valfritt)
    if is_ajax:
        return render(request, "admin/accounts/customer/_add_candidate_form.html", {
            "process": process,
            "form": form,
        })

    return render(request, "admin/accounts/customer/process_add_candidate.html", {
        "process": process,
        "form": form,
    })



@admin_required
@require_POST
def admin_process_delete(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    # Extra safety: bara admins
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    # För att kunna gå tillbaka snyggt
    next_url = request.POST.get("next") or request.GET.get("next") or reverse(
        "accounts:admin_user_detail",
        kwargs={"pk": process.created_by_id},
    )

    process_name = process.name
    process.delete()
    messages.success(request, f"Processen '{process_name}' raderades.")
    return redirect(next_url)

@login_required
@admin_required
def company_processes(request, pk):
    company = get_object_or_404(Company, pk=pk)

    processes = (
        TestProcess.objects
        .filter(company=company)
        .select_related("created_by", "created_by_admin", "org_unit")
        .prefetch_related("labels")
        .annotate(candidates_count=Count("invitations", distinct=True))
        .order_by("is_archived", "-created_at")
    )

    invite_form = CompanyInviteMemberForm()

    company_created_event = (
        ActivityEvent.objects
        .filter(
            company=company,
            verb=ActivityEvent.Verb.COMPANY_CREATED,
        )
        .select_related("actor")
        .order_by("created_at")
        .first()
    )

    historical_candidate_count_subquery = (
        HistoricalProcessCandidate.objects
        .filter(process=OuterRef("pk"))
        .values("process")
        .annotate(count=Count("id"))
        .values("count")
    )

    processes = (
        TestProcess.objects
        .filter(company=company)
        .select_related("created_by", "created_by_admin", "org_unit")
        .prefetch_related("labels")
        .annotate(
            live_candidates_count=Count("invitations", distinct=True),
            historical_candidates_count=Coalesce(
                Subquery(
                    historical_candidate_count_subquery,
                    output_field=IntegerField(),
                ),
                0,
            ),
        )
        .order_by("is_archived", "-created_at")
    )

    return render(request, "admin/accounts/companies/company_processes.html", {
        "company": company,
        "processes": processes,
        "active": "processes",
        "show_invite_button": True,
        "invite_form": invite_form,
        "company_created_event": company_created_event,
    })

@login_required
@admin_required
def company_user_detail(request, company_pk, user_pk):
    company = get_object_or_404(Company, pk=company_pk)

    user_obj = get_object_or_404(
        User.objects.prefetch_related(
            "company_memberships__company",
            "company_memberships__primary_org_unit",
        ),
        pk=user_pk,
    )

    membership = get_object_or_404(
        CompanyMember.objects.select_related("company", "primary_org_unit"),
        company=company,
        user=user_obj,
    )

    pending_invite = not user_obj.is_active

    processes = (
        TestProcess.objects
        .filter(company=company, created_by=user_obj)
        .annotate(invitations_count=Count("invitations", distinct=True))
        .order_by("-created_at")
    )

    processes_count = processes.count()

    invitations_qs = TestInvitation.objects.filter(
        process__company=company,
        process__created_by=user_obj,
    )

    invitations_created = invitations_qs.count()
    invitations_completed = invitations_qs.filter(status="completed").count()

    orgunit_accesses = (
        UserOrgUnitAccess.objects
        .filter(user=user_obj, org_unit__company=company)
        .select_related("org_unit", "org_unit__company")
        .order_by("org_unit__name")
    )

    company_created_event = (
        ActivityEvent.objects
        .filter(
            company=company,
            verb=ActivityEvent.Verb.COMPANY_CREATED,
        )
        .select_related("actor")
        .order_by("created_at")
        .first()
    )

    invite_form = CompanyInviteMemberForm()

    return render(request, "admin/accounts/companies/company_user_detail.html", {
        "company": company,
        "membership": membership,
        "user_obj": user_obj,
        "u": user_obj,

        "processes": processes,
        "active_processes": processes,

        "processes_count": processes_count,
        "invitations_created": invitations_created,
        "invitations_completed": invitations_completed,

        "pending_invite": pending_invite,
        "orgunit_accesses": orgunit_accesses,

        "active": "users",
        "show_invite_button": True,
        "invite_form": invite_form,
        "company_created_event": company_created_event,
    })

@login_required
@admin_required
def company_process_detail(request, company_pk, process_pk):
    company = get_object_or_404(Company, pk=company_pk)

    process = get_object_or_404(
        TestProcess.objects
        .select_related("company", "created_by", "org_unit")
        .prefetch_related("labels"),
        pk=process_pk,
        company=company,
    )

    invitations = (
        TestInvitation.objects
        .filter(process=process)
        .select_related("candidate")
        .order_by("-created_at")
    )

    historical_candidates = (
        HistoricalProcessCandidate.objects
        .filter(process=process)
        .select_related("candidate", "created_by")
        .prefetch_related("reports")
        .order_by("-created_at")
    )

    if process.is_historical:
        total_candidates = historical_candidates.count()
        invited_count = 0
        started_count = historical_candidates.filter(status="started").count()
        completed_count = historical_candidates.filter(status="completed").count()
        expired_count = 0
    else:
        total_candidates = invitations.count()

        invited_count = invitations.filter(
            Q(status__in=["sent", "started", "completed", "expired"]) |
            Q(invited_at__isnull=False)
        ).distinct().count()

        started_count = invitations.filter(
            status__in=["started", "completed"]
        ).count()

        completed_count = invitations.filter(
            status="completed"
        ).count()

        expired_count = invitations.filter(
            status="expired"
        ).count()

    kpis = {
        "total_candidates": total_candidates,
        "invited": invited_count,
        "started": started_count,
        "completed": completed_count,
        "expired": expired_count,
    }

    invite_form = CompanyInviteMemberForm()

    company_created_event = (
        ActivityEvent.objects
        .filter(
            company=company,
            verb=ActivityEvent.Verb.COMPANY_CREATED,
        )
        .select_related("actor")
        .order_by("created_at")
        .first()
    )

    self_reg_url = request.build_absolute_uri(
        process.get_self_registration_url()
    )

    return render(request, "admin/accounts/companies/company_process_detail.html", {
        "company": company,
        "process": process,
        "invitations": invitations,
        "historical_candidates": historical_candidates,
        "kpis": kpis,
        "self_reg_url": self_reg_url,

        "active": "processes",
        "show_invite_button": True,
        "invite_form": invite_form,
        "company_created_event": company_created_event,
    })

@login_required
@admin_required
def company_process_candidate_detail(request, company_pk, process_pk, candidate_pk):
    company = get_object_or_404(Company, pk=company_pk)

    process = get_object_or_404(
        TestProcess.objects.select_related("company", "created_by", "org_unit"),
        pk=process_pk,
        company=company,
    )

    candidate = get_object_or_404(Candidate, pk=candidate_pk)

    if process.is_historical:
        historical_candidate = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related("candidate", "process", "created_by")
            .prefetch_related("reports"),
            process=process,
            candidate=candidate,
        )

        ctx = {
            "company": company,
            "process": process,
            "candidate": candidate,
            "historical_candidate": historical_candidate,
            "historical_reports": historical_candidate.reports.all(),
            "is_historical": True,
            "active": "processes",
            "show_invite_button": True,
            "invite_form": CompanyInviteMemberForm(),
            "is_admin_view": True,
            "is_company_view": True,
        }

    else:
        invitation = get_object_or_404(
            TestInvitation.objects.select_related("candidate", "process"),
            process=process,
            candidate_id=candidate_pk,
        )

        ctx = build_candidate_detail_context(
            process=process,
            invitation=invitation,
        )

        ctx.update({
            "company": company,
            "process": process,
            "active": "processes",
            "show_invite_button": True,
            "invite_form": CompanyInviteMemberForm(),
            "is_admin_view": True,
            "is_company_view": True,
            "is_historical": False,
        })

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(
            request,
            "admin/accounts/companies/company_candidate_sheet.html",
            ctx,
        )

    return render(
        request,
        "admin/accounts/companies/company_candidate_detail.html",
        ctx,
    )

@login_required
@admin_required
def company_historical_process_create(request, pk):
    company = get_object_or_404(Company, pk=pk)

    if request.method == "POST":
        form = HistoricalTestProcessForm(request.POST, company=company)

        if form.is_valid():
            process = form.save(commit=False)

            process.company = company
            process.provider = "sova"

            process.source = "sova_import"
            process.is_historical = True
            process.sova_sync_enabled = False
            process.is_archived = True

            process.account_code = "HIST"
            process.project_code = f"HIST-{company.id}-{uuid.uuid4().hex[:8]}"

            process.project_name_snapshot = (
                process.sova_project_name
                or process.name
                or process.project_code
            )

            process.created_by = request.user
            process.created_by_admin = request.user

            process.save()
            form.save_m2m()

            log_event(
                company=company,
                verb=ActivityEvent.Verb.PROCESS_CREATED,
                actor=request.user,
                process=process,
                meta={
                    "source": "sova_import",
                    "is_historical": True,
                    "process_name": process.name,
                    "sova_account_name": process.sova_account_name,
                    "sova_project_name": process.sova_project_name,
                },
            )

            messages.success(request, "Historical test process created.")
            return redirect(
                "accounts:company_process_detail",
                company_pk=company.pk,
                process_pk=process.pk,
            )

        messages.error(request, "Could not create historical process. Check the form fields.")

    else:
        form = HistoricalTestProcessForm(company=company)

    return render(request, "admin/accounts/companies/company_historical_process_form.html", {
        "company": company,
        "form": form,
        "active": "processes",
        "show_invite_button": True,
        "invite_form": CompanyInviteMemberForm(),
    })

@login_required
@admin_required
def company_historical_candidate_add(request, company_pk, process_pk):
    company = get_object_or_404(Company, pk=company_pk)

    process = get_object_or_404(
        TestProcess,
        pk=process_pk,
        company=company,
        is_historical=True,
    )

    if request.method == "POST":
        form = HistoricalCandidateForm(request.POST, request.FILES)

        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()

            candidate, created = Candidate.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": form.cleaned_data["first_name"],
                    "last_name": form.cleaned_data["last_name"],
                }
            )

            if not created:
                changed_fields = []

                if form.cleaned_data["first_name"] and not candidate.first_name:
                    candidate.first_name = form.cleaned_data["first_name"]
                    changed_fields.append("first_name")

                if form.cleaned_data["last_name"] and not candidate.last_name:
                    candidate.last_name = form.cleaned_data["last_name"]
                    changed_fields.append("last_name")

                if changed_fields:
                    candidate.save(update_fields=changed_fields)

            historical_candidate, record_created = HistoricalProcessCandidate.objects.get_or_create(
                process=process,
                candidate=candidate,
                defaults={
                    "status": form.cleaned_data["status"],
                    "notes": form.cleaned_data.get("historical_notes") or "",
                    "created_by": request.user,
                },
            )

            historical_candidate.status = form.cleaned_data["status"]
            historical_candidate.notes = form.cleaned_data.get("historical_notes") or ""
            historical_candidate.save(update_fields=["status", "notes"])

            uploaded_reports = form.cleaned_data.get("historical_reports") or []

            for uploaded_file in uploaded_reports:
                HistoricalCandidateReport.objects.create(
                    historical_candidate=historical_candidate,
                    title=uploaded_file.name,
                    original_filename=uploaded_file.name,
                    file=uploaded_file,
                    uploaded_by=request.user,
                )

            log_event(
                company=company,
                verb=ActivityEvent.Verb.CANDIDATE_ADDED,
                actor=request.user,
                process=process,
                candidate=candidate,
                meta={
                    "source": "historical",
                    "record_created": record_created,
                    "uploaded_reports": len(uploaded_reports),
                },
            )

            if uploaded_reports:
                messages.success(
                    request,
                    f"Historical candidate added with {len(uploaded_reports)} report(s)."
                )
            else:
                messages.success(request, "Historical candidate added.")

            return redirect(
                "accounts:company_process_detail",
                company_pk=company.pk,
                process_pk=process.pk,
            )

        messages.error(request, "Could not add historical candidate. Check the form fields.")

    else:
        form = HistoricalCandidateForm()

    return render(request, "admin/accounts/companies/company_historical_candidate_form.html", {
        "company": company,
        "process": process,
        "form": form,
        "active": "processes",
        "show_invite_button": True,
        "invite_form": CompanyInviteMemberForm(),
    })

def get_template_icon_class(tests, title=""):
    """
    Returns a FontAwesome icon class based on the test types/title.
    Used when displaying SOVA project/template cards.
    """
    text = " ".join(tests).lower()
    title = (title or "").lower()

    if "360" in text or "360" in title:
        return "fa-solid fa-arrows-rotate"

    if (
        "numerical" in text
        or "numerisk" in text
        or "färdighet" in text
        or "fardighet" in text
        or "ability" in text
        or "skills" in text
    ):
        return "fa-solid fa-chart-simple"

    if (
        "personality" in text
        or "personlighet" in text
        or "pq" in title
    ):
        return "fa-solid fa-user-check"

    if (
        "motivation" in text
        or "motivationstest" in text
        or "mq" in title
    ):
        return "fa-solid fa-bullseye"

    if "leadership" in text or "ledarskap" in text:
        return "fa-solid fa-award"

    if "sales" in text or "sälj" in title or "salj" in title:
        return "fa-solid fa-handshake"

    if "admin" in text or "interim" in text or "interim" in title:
        return "fa-solid fa-briefcase"

    if "modern" in title:
        return "fa-solid fa-wand-magic-sparkles"

    if "linear" in title:
        return "fa-solid fa-wave-square"

    if "ihp" in title:
        return "fa-solid fa-layer-group"

    return "fa-solid fa-layer-group"


@login_required
@admin_required
def company_process_create(request, company_pk):
    company = get_object_or_404(Company, pk=company_pk)
    org_units = OrgUnit.objects.filter(company=company).order_by("name")

    client = SovaClient()
    error = None

    # --------------------------------------------------
    # 1. Hämta SOVA-projekt från API
    # --------------------------------------------------
    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    # --------------------------------------------------
    # 2. Hämta ProjectMeta så vi kan hitta namn, tester osv
    # --------------------------------------------------
    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    project_id_map = {}
    template_cards = []

    for account in accounts:
        acc = (account.get("code") or "").strip()

        for project in (account.get("projects") or []):
            proj_code = (project.get("code") or "").strip()
            sova_name = (project.get("name") or proj_code).strip()

            value = f"{acc}|{proj_code}"
            project_id_map[value] = project.get("id")

            meta = meta_map.get((acc, proj_code))
            title = getattr(meta, "intern_name", None) or sova_name

            description = ""
            tests = []
            languages = []

            if meta:
                description = (getattr(meta, "notes", None) or "").strip()

                tests_raw = (getattr(meta, "tests", None) or "").strip()
                if tests_raw:
                    tests = [t.strip() for t in tests_raw.split(",") if t.strip()]

                languages_raw = (getattr(meta, "languages", None) or "").strip()
                if languages_raw:
                    languages = [l.strip() for l in languages_raw.split(",") if l.strip()]

            template_cards.append({
                "value": value,
                "title": title,
                "description": description,
                "tests": tests,
                "languages": languages,
                "icon_class": get_template_icon_class(tests, title),
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
                "sova_project_id": project.get("id"),
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    context_base = {
        "company": company,
        "error": error,
        "org_units": org_units,
        "process_purposes": PROCESS_PURPOSES,
        "available_tests": AVAILABLE_TESTS,
        "purpose_recommended_tests": PURPOSE_RECOMMENDED_TESTS,
        "template_cards": template_cards,
        "templates_count": len(template_cards),
        "accounts_count": len(accounts),
        "active": "processes",
        "show_invite_button": True,
        "invite_form": CompanyInviteMemberForm(),
    }

    # --------------------------------------------------
    # 3. POST: skapa processen
    # --------------------------------------------------
    if request.method == "POST":
        form = TestProcessWizardCreateForm(request.POST)

        if form.is_valid():
            purpose = form.cleaned_data.get("purpose")
            selected_tests = form.cleaned_data.get("selected_tests") or []
            name = (form.cleaned_data.get("name") or "").strip()
            label_names = form.cleaned_data.get("labels_text") or []

            # --------------------------------------------------
            # 4. Välj org unit / account
            # --------------------------------------------------
            org_unit_id = request.POST.get("org_unit")

            org_unit = None
            if org_unit_id:
                org_unit = OrgUnit.objects.filter(
                    pk=org_unit_id,
                    company=company,
                ).first()

            if not org_unit:
                form.add_error(
                    None,
                    "Please select which account/unit this process belongs to."
                )

                return render(
                    request,
                    "admin/accounts/companies/company_process_create.html",
                    {
                        **context_base,
                        "form": form,
                    },
                )

            if isinstance(label_names, str):
                label_names = [
                    item.strip()
                    for item in label_names.split(",")
                    if item.strip()
                ]

            if not name:
                name = build_default_process_name(
                    purpose=purpose,
                    selected_tests=selected_tests,
                )

            resolved_template = resolve_dev_sova_template(selected_tests)

            if not resolved_template:
                form.add_error(
                    "selected_tests",
                    "Please select a valid test combination. No matching SOVA project/template was found."
                )

                return render(
                    request,
                    "admin/accounts/companies/company_process_create.html",
                    {
                        **context_base,
                        "form": form,
                    },
                )

            acc = (resolved_template["account_code"] or "").strip()
            proj = (resolved_template["project_code"] or "").strip()
            value = f"{acc}|{proj}"

            obj = TestProcess(
                name=name,
                company=company,
                org_unit=org_unit,
                provider="sova",
                account_code=acc,
                project_code=proj,
                created_by=request.user,
                created_by_admin=request.user,
                purpose=purpose,
                selected_tests=selected_tests,
                source="talena",
                is_historical=False,
                sova_sync_enabled=True,
            )

            meta = meta_map.get((acc, proj))

            if meta and getattr(meta, "intern_name", None):
                obj.project_name_snapshot = meta.intern_name
            else:
                match = next(
                    (t for t in template_cards if t["value"] == value),
                    None
                )
                obj.project_name_snapshot = (
                    match["sova_name"] if match else proj
                )

            obj.save()

            if label_names:
                label_objs = []

                for label_name in label_names:
                    lab, _ = ProcessLabel.objects.get_or_create(
                        company=company,
                        name=label_name,
                    )
                    label_objs.append(lab)

                obj.labels.set(label_objs)
            else:
                obj.labels.clear()

            log_event(
                company=company,
                verb=ActivityEvent.Verb.PROCESS_CREATED,
                actor=request.user,
                process=obj,
                meta={
                    "source": "talena_admin_company_create",
                    "process_name": obj.name,
                    "purpose": obj.purpose,
                    "selected_tests": obj.selected_tests,
                    "org_unit_id": org_unit.id,
                    "org_unit_name": org_unit.name,
                    "resolved_sova_template": value,
                    "sova_project_id": project_id_map.get(value),
                },
            )

            messages.success(request, "SOVA process created.")
            return redirect(
                "accounts:company_process_detail",
                company_pk=company.pk,
                process_pk=obj.pk,
            )

        messages.error(request, "Could not create SOVA process. Check the form fields.")

    else:
        form = TestProcessWizardCreateForm()

    return render(
        request,
        "admin/accounts/companies/company_process_create.html",
        {
            **context_base,
            "form": form,
        },
    )

@login_required
@admin_required
@require_POST
def company_process_archive(request, company_pk, process_pk):
    company = get_object_or_404(Company, pk=company_pk)

    process = get_object_or_404(
        TestProcess,
        pk=process_pk,
        company=company,
    )

    if process.is_archived:
        messages.info(request, "This process is already archived.")
        return redirect(
            "accounts:company_process_detail",
            company_pk=company.pk,
            process_pk=process.pk,
        )

    process.archive()

    log_event(
        company=company,
        verb=ActivityEvent.Verb.PROCESS_ARCHIVED,
        actor=request.user,
        process=process,
        meta={"context": "admin_company_view"},
    )

    messages.success(request, "Process archived.")
    return redirect(
        "accounts:company_process_detail",
        company_pk=company.pk,
        process_pk=process.pk,
    )


@login_required
@admin_required
@require_POST
def company_process_unarchive(request, company_pk, process_pk):
    company = get_object_or_404(Company, pk=company_pk)

    process = get_object_or_404(
        TestProcess,
        pk=process_pk,
        company=company,
    )

    if not process.is_archived:
        messages.info(request, "This process is not archived.")
        return redirect(
            "accounts:company_process_detail",
            company_pk=company.pk,
            process_pk=process.pk,
        )

    process.unarchive()

    log_event(
        company=company,
        verb=ActivityEvent.Verb.PROCESS_UPDATED,
        actor=request.user,
        process=process,
        meta={
            "context": "admin_company_view",
            "action": "unarchive",
        },
    )

    messages.success(request, "Process restored.")
    return redirect(
        "accounts:company_process_detail",
        company_pk=company.pk,
        process_pk=process.pk,
    )


@login_required
@admin_required
@require_POST
def company_process_delete(request, company_pk, process_pk):
    company = get_object_or_404(Company, pk=company_pk)

    process = get_object_or_404(
        TestProcess,
        pk=process_pk,
        company=company,
    )

    if not process.can_delete():
        messages.error(
            request,
            "This process cannot be deleted because tests have been sent, started or completed. Archive it instead."
        )
        return redirect(
            "accounts:company_process_detail",
            company_pk=company.pk,
            process_pk=process.pk,
        )

    process_name = process.name

    log_event(
        company=company,
        verb=ActivityEvent.Verb.PROCESS_DELETED,
        actor=request.user,
        process=process,
        meta={
            "context": "admin_company_view",
            "process_name": process_name,
        },
    )

    process.delete()

    messages.success(request, f"Process '{process_name}' deleted.")
    return redirect(
        "accounts:company_processes",
        pk=company.pk,
    )

@login_required
@admin_required
@require_POST
def company_invite_member(request, company_pk):
    company = get_object_or_404(Company, pk=company_pk)

    next_url = (
        request.POST.get("next")
        or request.META.get("HTTP_REFERER")
        or reverse("accounts:company_detail", kwargs={"pk": company.pk})
    )

    invite_form = CompanyInviteMemberForm(request.POST)

    if invite_form.is_valid():
        email = invite_form.cleaned_data["email"].strip().lower()
        first_name = invite_form.cleaned_data.get("first_name", "").strip()
        last_name = invite_form.cleaned_data.get("last_name", "").strip()

        with transaction.atomic():
            user, created_user = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_active": False,
                }
            )

            if not created_user:
                changed_fields = []

                if first_name and not user.first_name:
                    user.first_name = first_name
                    changed_fields.append("first_name")

                if last_name and not user.last_name:
                    user.last_name = last_name
                    changed_fields.append("last_name")

                if changed_fields:
                    user.save(update_fields=changed_fields)

            ensure_user_has_default_orgunit(
                user=user,
                company=company,
                permission="own",
            )

            if user.is_active:
                messages.info(
                    request,
                    f"{email} har redan ett aktivt konto. Ingen inbjudan skickades."
                )
                return redirect(next_url)

            if user.has_usable_password():
                user.set_unusable_password()

            user.is_active = False
            user.save(update_fields=["is_active", "password"])

            UserInvite.objects.filter(
                user=user,
                company=company,
                accepted_at__isnull=True,
                revoked_at__isnull=True,
            ).update(revoked_at=timezone.now())

            invite = UserInvite.objects.create(
                user=user,
                company=company,
                created_by=request.user,
            )

            invite_link = build_invite_uuid_link(request, invite)

            send_invite_email(
                request,
                user,
                invite_link=invite_link,
                company=company,
            )

            log_event(
                company=company,
                actor=request.user,
                verb=ActivityEvent.Verb.COMPANY_MEMBER_INVITED,
                meta={
                    "company_id": company.id,
                    "company_name": company.name,
                    "invited_user_id": user.id,
                    "invited_user_email": user.email,
                    "invited_user_name": user.get_full_name(),
                    "invite_id": str(invite.id),
                },
            )

        messages.success(request, f"Inbjudan skickades till {email}.")
        return redirect(next_url)

    messages.error(request, "Kunde inte bjuda in användare. Kontrollera fälten.")
    return redirect(next_url)