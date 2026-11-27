from django.conf import settings
from types import SimpleNamespace
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.db.models import Count
from django.views.decorators.http import require_POST
from apps.core.integrations.sova import SovaClient
from apps.projects.models import ProjectMeta
from apps.processes.services.project_assessment_status import (
    project_test_columns,
    attach_test_statuses,
    invitation_test_statuses,
)
from django.utils.translation import get_language
from apps.accounts.report_branding import get_report_branding
from .utils.org_access import get_accessible_orgunit_ids, get_effective_orgunit_permissions
from apps.processes.views import (
    build_candidate_detail_context as build_shared_candidate_detail_context,
    build_historical_candidate_detail_context as build_shared_historical_candidate_detail_context,
    build_scores_by_competency,
    build_practitioner_report,
    build_manager_report,
    build_candidate_report,
    build_motivation_coaching_report,
)
from .forms import HistoricalAssessmentImportForm
from apps.teams.models import Team, TeamMembership
from django.db.models import Count, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce

from apps.processes.models import (
    AssessmentUsage,
    Candidate,
    TestProcess,
    TestInvitation,
    HistoricalProcessCandidate,
)

from apps.core.ai.language import (
    get_request_ai_language,
)

from apps.reports.services.candidate_insights import (
    build_general_insight_input,
    generate_general_candidate_insights,
)

from apps.processes.services.historical_assessment_import import (
    import_historical_assessment_file,
)


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
    resolve_sova_template,
    extract_tests_from_project_name,
    build_default_process_name,
)

from apps.processes.forms import HistoricalTestProcessForm, HistoricalCandidateForm

from datetime import datetime, date, time, timedelta
from apps.activity.services import log_event

from apps.processes.views import build_cognitive_reports_for_test

from apps.processes.views import build_personality_reports_for_candidate
from apps.activity.models import ActivityEvent

from apps.core.utils.auth import is_admin
from apps.processes.models import TestProcess, TestInvitation, Candidate

from .forms import InviteUserForm, OrgUnitForm, UserOrgUnitAccessForm
from .services.invites import send_invite_email, render_account_invitation
from .decorators import admin_required
from apps.portal.forms import AccountForm as PortalAccountForm, ProfileImageForm
from .utils.permissions import get_user_accessible_accounts

from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from .models import Company, CompanyMember, OrgUnit, UserOrgUnitAccess, UserOrgUnitProjectAccess
from .forms import (CompanyMemberAddForm, CompanyForm, CompanyInviteMemberForm,
                    OrgUnitAccessAddForm, CompanyNameForm, OrgUnitNameForm)

from django.db import transaction
from django.db.models.deletion import ProtectedError

from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from .models import UserInvite
from django.utils import timezone

import csv
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

    date_from = (
        parse_date_param(
            request.GET.get("date_from")
        )
        or default_start
    )

    date_to = (
        parse_date_param(
            request.GET.get("date_to")
        )
        or today
    )

    start_dt = make_aware_start(date_from)
    end_dt = make_aware_end(date_to)

    q = (
        request.GET.get("q")
        or ""
    ).strip()

    company_id = (
        request.GET.get("company")
        or ""
    ).strip()

    org_unit_id = (
        request.GET.get("org_unit")
        or ""
    ).strip()

    label_id = (
        request.GET.get("label")
        or ""
    ).strip()

    sent_by_id = (
        request.GET.get("sent_by")
        or request.GET.get("created_by")
        or ""
    ).strip()

    test_type = (
        request.GET.get("test_type")
        or ""
    ).strip()

    lifecycle = (
        request.GET.get("lifecycle")
        or "completed"
    ).strip().lower()

    valid_lifecycles = {
        "sent",
        "started",
        "completed",
        "all",
    }

    if lifecycle not in valid_lifecycles:
        lifecycle = "completed"

    include_internal = (
        request.GET.get("include_internal")
        == "1"
    )

    usages = (
        AssessmentUsage.objects
        .select_related(
            "company",
            "org_unit",
            "process",
            "candidate",
            "invitation",
            "sent_by",
        )
        .prefetch_related(
            "process__labels"
        )
        .filter(
            company__isnull=False,
        )
    )

    # ------------------------------------------------------------
    # General filters
    # ------------------------------------------------------------

    if q:
        usages = usages.filter(
            Q(
                company_name_snapshot__icontains=q
            )
            | Q(
                company__name__icontains=q
            )
            | Q(
                org_unit_name_snapshot__icontains=q
            )
            | Q(
                org_unit__name__icontains=q
            )
            | Q(
                process_name_snapshot__icontains=q
            )
            | Q(
                process__name__icontains=q
            )
            | Q(
                project_name_snapshot__icontains=q
            )
            | Q(
                process__project_code__icontains=q
            )
            | Q(
                candidate_name_snapshot__icontains=q
            )
            | Q(
                candidate_email_snapshot__icontains=q
            )
            | Q(
                candidate__email__icontains=q
            )
            | Q(
                sent_by__first_name__icontains=q
            )
            | Q(
                sent_by__last_name__icontains=q
            )
            | Q(
                sent_by__email__icontains=q
            )
        )

    if company_id:
        usages = usages.filter(
            company_id=company_id
        )

    if org_unit_id:
        usages = usages.filter(
            org_unit_id=org_unit_id
        )

    if label_id:
        usages = usages.filter(
            process__labels__id=label_id
        )

    if sent_by_id:
        usages = usages.filter(
            sent_by_id=sent_by_id
        )

    if test_type:
        usages = usages.filter(
            assessment_type=test_type
        )

    if not include_internal:
        usages = usages.exclude(
            Q(
                process__labels__name__iexact=(
                    "internal"
                )
            )
            | Q(
                process__labels__name__iexact=(
                    "demo"
                )
            )
            | Q(
                process__labels__name__iexact=(
                    "do not invoice"
                )
            )
            | Q(
                process__labels__name__iexact=(
                    "not billable"
                )
            )
        )

    usages = usages.distinct()

    # ------------------------------------------------------------
    # Separate lifecycle periods
    #
    # Each filter uses the timestamp belonging to that event.
    # ------------------------------------------------------------

    sent_period = usages.filter(
        sent_at__gte=start_dt,
        sent_at__lte=end_dt,
    )

    started_period = usages.filter(
        started_at__gte=start_dt,
        started_at__lte=end_dt,
    )

    completed_period = usages.filter(
        completed_at__gte=start_dt,
        completed_at__lte=end_dt,
        billing_excluded=False,
    )

    if lifecycle == "sent":
        selected_usages = sent_period
        lifecycle_label = "Sent"
        date_basis_label = "Filtered by sent date"

    elif lifecycle == "started":
        selected_usages = started_period
        lifecycle_label = "Started"
        date_basis_label = "Filtered by started date"

    elif lifecycle == "all":
        selected_usages = usages.filter(
            Q(
                sent_at__gte=start_dt,
                sent_at__lte=end_dt,
            )
            | Q(
                started_at__gte=start_dt,
                started_at__lte=end_dt,
            )
            | Q(
                completed_at__gte=start_dt,
                completed_at__lte=end_dt,
            )
        ).distinct()

        lifecycle_label = "All activity"
        date_basis_label = (
            "Filtered by sent, started or completed date"
        )

    else:
        selected_usages = completed_period
        lifecycle_label = "Completed / billable"
        date_basis_label = (
            "Filtered by individual completion date"
        )

    selected_usages = (
        selected_usages
        .order_by(
            "company__name",
            "org_unit__name",
            "process__name",
            "sent_by__first_name",
            "sent_by__last_name",
            "assessment_type",
        )
    )

    # ------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------

    totals = {
        "sent": sent_period.count(),
        "started": started_period.count(),
        "completed": completed_period.count(),
        "billable": completed_period.count(),

        "unfinished": sent_period.filter(
            completed_at__isnull=True,
        ).count(),

        "estimated_completed": (
            completed_period
            .filter(
                completed_at_is_estimated=True
            )
            .count()
        ),

        "selected_count": (
            selected_usages.count()
        ),

        "personality": 0,
        "motivation": 0,
        "verbal": 0,
        "numerical": 0,
        "logical": 0,
        "other": 0,

        "candidates": set(),
        "processes": set(),
    }

    # ------------------------------------------------------------
    # Group rows by process and actual sender
    # ------------------------------------------------------------

    rows_by_key = {}

    for usage in selected_usages:
        process = usage.process
        company = usage.company
        org_unit = usage.org_unit

        key = (
            usage.process_id,
            usage.sent_by_id,
        )

        if key not in rows_by_key:
            rows_by_key[key] = {
                "company": company,
                "org_unit": org_unit,
                "process": process,
                "sent_by": usage.sent_by,

                "company_name": (
                    usage.company_name_snapshot
                    or company.name
                    or "No company"
                ),

                "account_name": (
                    usage.org_unit_name_snapshot
                    or (
                        org_unit.name
                        if org_unit
                        else "No account"
                    )
                ),

                "account_code": (
                    org_unit.unit_code
                    if org_unit
                    else ""
                ),

                "process_name": (
                    usage.process_name_snapshot
                    or process.name
                    or "No project"
                ),

                "project_name": (
                    usage.project_name_snapshot
                    or process.project_name_snapshot
                    or process.project_code
                    or "Assessment"
                ),

                "labels": list(
                    process.labels.all()
                ),

                "selected_count": 0,

                "sent": 0,
                "started": 0,
                "completed": 0,
                "unfinished": 0,
                "billable": 0,

                "estimated_completed": 0,

                "personality": 0,
                "motivation": 0,
                "verbal": 0,
                "numerical": 0,
                "logical": 0,
                "other": 0,

                "candidates": set(),
            }

        row = rows_by_key[key]

        row["selected_count"] += 1

        assessment_type = (
            usage.assessment_type
            if usage.assessment_type in {
                "personality",
                "motivation",
                "verbal",
                "numerical",
                "logical",
                "other",
            }
            else "other"
        )

        row[assessment_type] += 1
        totals[assessment_type] += 1

        if (
            usage.sent_at
            and start_dt
            <= usage.sent_at
            <= end_dt
        ):
            row["sent"] += 1

        if (
            usage.started_at
            and start_dt
            <= usage.started_at
            <= end_dt
        ):
            row["started"] += 1

        if (
            usage.completed_at
            and start_dt
            <= usage.completed_at
            <= end_dt
            and not usage.billing_excluded
        ):
            row["completed"] += 1
            row["billable"] += 1

            if usage.completed_at_is_estimated:
                row["estimated_completed"] += 1

        if usage.completed_at is None:
            row["unfinished"] += 1

        row["candidates"].add(
            usage.candidate_id
        )

        totals["candidates"].add(
            usage.candidate_id
        )

        totals["processes"].add(
            usage.process_id
        )

    rows = list(
        rows_by_key.values()
    )

    for row in rows:
        row["candidate_count"] = len(
            row["candidates"]
        )

    totals["candidate_count"] = len(
        totals["candidates"]
    )

    totals["process_count"] = len(
        totals["processes"]
    )

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="talena-billing-{date_from}-{date_to}.csv"'
        )
        response.write("\ufeff")
        writer = csv.writer(response, delimiter=";")
        headers = [
            "Company / account",
            "Project",
            "Sent by",
            "Candidates",
            "Tests",
            "Test types",
        ]
        if lifecycle == "completed":
            headers.append("Status")
        writer.writerow(headers)

        type_labels = (
            ("personality", "Personality"),
            ("motivation", "Motivation"),
            ("verbal", "Verbal"),
            ("numerical", "Numerical"),
            ("logical", "Logical"),
            ("other", "Other"),
        )
        for row in rows:
            if not row["selected_count"]:
                continue
            account = row["account_name"]
            if row["account_code"]:
                account += f" · {row['account_code']}"
            process_name = f"{row['process_name']} · {row['project_name']}"
            if row["labels"]:
                process_name += " · " + ", ".join(
                    label.name for label in row["labels"]
                )
            sender = row["sent_by"]
            sender_name = (
                sender.get_full_name() or sender.email
                if sender else "Unknown / historical"
            )
            types = ", ".join(
                f"{label} {row[key]}"
                for key, label in type_labels
                if row[key]
            )
            values = [
                f"{row['company_name']} · {account}",
                process_name,
                sender_name,
                row["candidate_count"],
                row["selected_count"],
                types,
            ]
            if lifecycle == "completed":
                estimated = row["estimated_completed"]
                if estimated == row["selected_count"]:
                    detail = "Historical completion date"
                elif estimated:
                    detail = (
                        f"{estimated} of {row['selected_count']} "
                        "use historical dates"
                    )
                else:
                    detail = "Recorded per assessment"
                values.append(f"Completed & billable · {detail}")
            writer.writerow(values)
        return response

    # ------------------------------------------------------------
    # Filter choices
    # ------------------------------------------------------------

    companies = Company.objects.order_by(
        "name"
    )

    org_units = (
        OrgUnit.objects
        .select_related("company")
        .order_by(
            "company__name",
            "name",
        )
    )

    labels = (
        ProcessLabel.objects
        .select_related("company")
        .order_by(
            "company__name",
            "name",
        )
    )

    User = get_user_model()

    senders = (
        User.objects
        .filter(
            assessment_usages_sent__isnull=False
        )
        .distinct()
        .order_by(
            "first_name",
            "last_name",
            "email",
        )
    )

    return render(
        request,
        "admin/accounts/usage_billing.html",
        {
            "rows": rows,
            "totals": totals,

            "date_from": (
                date_from.strftime("%Y-%m-%d")
            ),

            "date_to": (
                date_to.strftime("%Y-%m-%d")
            ),

            "q": q,

            "selected_company_id": (
                company_id
            ),

            "selected_org_unit_id": (
                org_unit_id
            ),

            "selected_label_id": (
                label_id
            ),

            "selected_sent_by_id": (
                sent_by_id
            ),

            "selected_test_type": (
                test_type
            ),

            "selected_lifecycle": (
                lifecycle
            ),

            "lifecycle_label": (
                lifecycle_label
            ),

            "date_basis_label": (
                date_basis_label
            ),

            "include_internal": (
                include_internal
            ),

            "companies": companies,
            "org_units": org_units,
            "labels": labels,
            "senders": senders,

            "lifecycle_options": [
                (
                    "completed",
                    "Completed / billable",
                ),
                (
                    "sent",
                    "Sent",
                ),
                (
                    "started",
                    "Started",
                ),
                (
                    "all",
                    "All activity",
                ),
            ],

            "test_types": [
                (
                    "personality",
                    "Personality",
                ),
                (
                    "motivation",
                    "Motivation",
                ),
                (
                    "verbal",
                    "Verbal",
                ),
                (
                    "numerical",
                    "Numerical",
                ),
                (
                    "logical",
                    "Logical",
                ),
                (
                    "other",
                    "Other",
                ),
            ],
        },
    )


# The customer route marks a completed AI interpretation outdated when its
# saved language differs from the current interface language. In admin we
# calculate exactly the same visible state on a shallow copy: no database
# writes should happen merely because someone opened the mirror.
def _admin_saved_interview_notes(raw_text):
    """Split only Talena's exact saved category headings; preserve legacy text."""
    import re

    source = str(raw_text or "").strip()
    labels = {
        "Personlighet": "Personlighet",
        "Motivation": "Motivation",
        "Färdighet": "Färdighet",
    }
    pattern = re.compile(
        r"^### Intervjuunderlag: (Personlighet|Motivation|Färdighet)[ \t]*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(source))
    if not matches:
        return [{"title": "Tidigare intervjuanteckningar", "text": source}] if source else []

    sections = []
    prefix = source[:matches[0].start()].strip()
    if prefix:
        sections.append({"title": "Tidigare intervjuanteckningar", "text": prefix})
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        chunk = source[start:end].strip()
        if chunk:
            sections.append({"title": labels[match.group(1)], "text": chunk})
    return sections


def _admin_saved_after_interview_context(process, candidate, owner, language_code):
    """Expose only stored customer evidence/report edits, scoped to this process."""
    from apps.processes.interview_question_models import (
        InterviewQuestionNote,
        ManagerReportTextEdit,
    )

    question_notes = (
        InterviewQuestionNote.objects
        .filter(process=process, candidate=candidate)
        .exclude(note="")
        .select_related("updated_by")
        .order_by("source", "created_at", "pk")
    )
    edits = list(
        ManagerReportTextEdit.objects
        .filter(process=process, candidate=candidate, language_code=language_code)
        .order_by("block_key")
        .values("block_key", "text", "version")
    )
    saved = getattr(owner, "ai_post_interview_decision_support", None) or {}
    blocks = saved.get("content_blocks") or {}
    personality = getattr(owner, "ai_manager_report_personality", None) or {}
    has_manager_text = any(
        str(part or "").strip()
        for value in personality.values() if isinstance(value, dict)
        for part in value.values()
    )
    return {
        "admin_interview_note_sections": _admin_saved_interview_notes(
            getattr(owner, "interview_notes", "") or ""
        ),
        "admin_interview_question_notes": list(question_notes),
        "admin_manager_report_edits_payload": {
            "ok": True,
            "language": language_code,
            "edits": edits,
        },
        "admin_has_manager_report": bool(
            has_manager_text
            or str(blocks.get("wellbeing_tips") or "").strip()
            or edits
        ),
    }


def _admin_readonly_ai_state(owner, language):
    from copy import copy
    from apps.core.ai.language import ai_content_language_matches

    visible = copy(owner)
    fields = (
        ("purpose_fit", "ai_purpose_fit", "ai_purpose_fit_status"),
        ("response_style_guidance", "ai_response_style_guidance", "ai_response_style_guidance_status"),
        ("cognitive_interpretation", "ai_cognitive_interpretation", "ai_cognitive_interpretation_status"),
        ("cognitive_questions", "ai_cognitive_questions", "ai_cognitive_questions_status"),
        ("motivation_interpretation", "ai_motivation_interpretation", "ai_motivation_interpretation_status"),
        ("motivation_questions", "ai_motivation_questions", "ai_motivation_questions_status"),
        ("personality_interpretation", "ai_personality_interpretation", "ai_personality_interpretation_status"),
        ("personality_questions", "ai_personality_questions", "ai_personality_questions_status"),
        ("pre_interview_decision_support", "ai_pre_interview_decision_support", "ai_pre_interview_decision_support_status"),
        ("post_interview_decision_support", "ai_post_interview_decision_support", "ai_post_interview_decision_support_status"),
    )
    for content_key, result_field, status_field in fields:
        if (
            getattr(visible, result_field, None)
            and getattr(visible, status_field, None) == "completed"
            and not ai_content_language_matches(visible, content_key, language)
        ):
            setattr(visible, status_field, "outdated")
    return visible


def build_candidate_detail_context(process, invitation, language="sv"):
    """Same customer view-model, with read-only derived language states."""
    return build_shared_candidate_detail_context(
        process=process,
        invitation=_admin_readonly_ai_state(invitation, language),
        language=language,
    )


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
        .annotate(
            company_admin_count=Count(
                "company__memberships",
                filter=Q(company__memberships__role=CompanyMember.ROLE_ADMIN),
            )
        )
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
            # Match the account's first UI language to the invitation language.
            user.preferred_language = form.cleaned_data.get("invite_language") or "en"
            user.set_unusable_password()
            user.is_active = False
            user.save()

            send_invite_email(
                request,
                user,
                invite_link=build_invite_link(request, user),
                subject=form.cleaned_data["invite_subject"],
                message=form.cleaned_data["invite_message"],
                language=form.cleaned_data["invite_language"],
            )
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
        .filter(process=process, removed_from_process_at__isnull=True)
        .select_related("candidate", "process__company")
        .prefetch_related("assessment_usages")
        .order_by("-created_at")
    )

    removed_invitations = (
        TestInvitation.objects.filter(
            process=process, removed_from_process_at__isnull=False
        ).select_related("candidate").order_by("-removed_from_process_at")
    )

    # Snabb statistik
    status_counts = {}
    for inv in invitations:
        status_counts[inv.status] = status_counts.get(inv.status, 0) + 1

    total_sent = invitations.count()
    meta = ProjectMeta.objects.filter(
        account_code=process.account_code, project_code=process.project_code,
    ).first()
    project_tests = [] if process.is_historical else project_test_columns(process, meta)
    attach_test_statuses(invitations, project_tests, get_language() or "sv")

    return render(request, "admin/accounts/customer/process_detail.html", {
        "process": process,
        "invitations": invitations,
        "removed_invitations": removed_invitations,
        "project_tests": project_tests,
        "project_table_colspan": max(1, len(project_tests)) + 6,
        "status_counts": status_counts,
        "total_sent": total_sent,
        "self_reg_url": request.build_absolute_uri(process.get_self_registration_url()),
    })


@login_required
@admin_required
def admin_candidate_detail(request, process_pk, candidate_pk):
    """Read-only customer candidate mirror within the internal admin context."""
    process = get_object_or_404(
        TestProcess.objects.select_related("company", "org_unit"),
        pk=process_pk, company__isnull=False,
    )
    language_code = get_request_ai_language(request)

    if process.is_historical:
        historical_candidate = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related("candidate", "process", "created_by")
            .prefetch_related(
                "reports", "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process, candidate_id=candidate_pk,
        )
        ctx = build_shared_historical_candidate_detail_context(
            process=process,
            historical_candidate=_admin_readonly_ai_state(historical_candidate, language_code),
            language=language_code,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation.objects.select_related("candidate"),
            process=process, candidate_id=candidate_pk,
            removed_from_process_at__isnull=True,
        )
        from apps.processes.services.automatic_interview_questions import (
            generate_ready_interview_questions,
        )

        # Backfill question sets for completed tests that predate automatic
        # Sova-callback generation, so the admin mirror can show them too.
        generate_ready_interview_questions(invitation)
        invitation.refresh_from_db()
        ctx = build_candidate_detail_context(
            process=process, invitation=invitation, language=language_code,
        )
        ctx["is_historical"] = False

    ctx.update(_admin_saved_after_interview_context(
        process=process,
        candidate=ctx["candidate"],
        owner=historical_candidate if process.is_historical else invitation,
        language_code=language_code,
    ))
    ctx.update({
        "is_admin_view": True,
        "is_admin_candidate_mirror": True,
        "can_manage_candidate_results": False,
        "company": process.company,
        "process": process,
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(
            request, "admin/accounts/companies/company_candidate_sheet.html", ctx,
        )
    return render(request, "admin/accounts/customer/candidate_detail.html", ctx)

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
@require_POST
def company_integrity_guard_visibility(request, pk):
    """Company-wide Talena-only visibility, writable by platform admins."""
    # Staff permissions alone must not grant access to this setting.
    if not (request.user.is_superuser or getattr(request.user, "role", "") == "admin"):
        return HttpResponseForbidden("Not allowed")

    company = get_object_or_404(Company, pk=pk)
    value = request.POST.get("integrity_guard_visible")
    if value not in ("0", "1"):
        return HttpResponse("Invalid visibility value.", status=400)

    visible = value == "1"
    if company.integrity_guard_visible != visible:
        company.integrity_guard_visible = visible
        company.save(update_fields=["integrity_guard_visible"])

    messages.success(
        request,
        "Integrity Guard is now shown in Talena for this company."
        if visible else "Integrity Guard is now hidden in Talena for this company.",
    )
    return redirect("accounts:company_detail", pk=company.pk)


@login_required
@admin_required
@require_POST
def project_integrity_guard_visibility(request, pk):
    """Change the Talena-only Integrity Guard visibility for one project."""
    # Company customers and ordinary staff must never be able to write this.
    if not (request.user.is_superuser or getattr(request.user, "role", "") == "admin"):
        return HttpResponseForbidden("Not allowed")

    process = get_object_or_404(
        TestProcess.objects.select_related("company"),
        pk=pk, company__isnull=False,
    )
    value = request.POST.get("integrity_guard_visible")
    if value not in ("0", "1", "default"):
        return HttpResponse("Invalid visibility value.", status=400)

    override = None if value == "default" else value == "1"
    if process.integrity_guard_visible_override != override:
        process.integrity_guard_visible_override = override
        process.save(update_fields=["integrity_guard_visible_override"])

    if override is None:
        messages.success(request, "Integrity Guard now follows the company setting.")
    else:
        messages.success(
            request,
            "Integrity Guard is now shown in Talena for this project."
            if override else "Integrity Guard is now hidden in Talena for this project.",
        )
    return redirect("processes:process_detail", pk=process.pk)


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
    """Remove company access; deactivate non-admins without remaining memberships."""
    with transaction.atomic():
        # Serialize removals in the same company so concurrent requests
        # cannot remove two administrators while each sees the other.
        company = get_object_or_404(
            Company.objects.select_for_update(), pk=company_pk,
        )
        membership = get_object_or_404(
            CompanyMember.objects.select_for_update(),
            company=company,
            user_id=user_pk,
        )
        # Serialize removals of memberships in different companies for the
        # same global user, so only the removal of the FINAL membership
        # deactivates the account. Project/history FKs still keep this user.
        user = get_object_or_404(
            User.objects.select_for_update(), pk=membership.user_id,
        )
        if membership.user_id == request.user.pk:
            messages.error(request, "Du kan inte ta bort din egen företagskoppling.")
            return redirect("accounts:company_users", pk=company.pk)

        if (
            membership.role == CompanyMember.ROLE_ADMIN
            and not CompanyMember.objects.filter(
                company=company, role=CompanyMember.ROLE_ADMIN
            ).exclude(pk=membership.pk).exists()
        ):
            messages.error(
                request,
                "Det går inte att ta bort företagets sista administratör. "
                "Tilldela först en annan användare administratörsrollen.",
            )
            return redirect("accounts:company_users", pk=company.pk)

        removed_role = membership.role
        # Org-unit access is stored separately from CompanyMember; it must be
        # removed as well, otherwise permissions can survive the membership.
        UserOrgUnitAccess.objects.filter(
            user=user, org_unit__company=company
        ).delete()
        # Old activation links must not remain usable after company removal.
        UserInvite.objects.filter(
            user=user, company=company,
            accepted_at__isnull=True, revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
        # Retain the projects and their creator history, but prevent future
        # candidate-completion emails reaching someone who has left the company.
        TestProcess.objects.filter(
            company=company, created_by=user,
            project_completion_notifications_enabled=True,
        ).update(project_completion_notifications_enabled=False)
        membership.delete()

        # A user can work in multiple tenants. Removing one tenant must not
        # affect the user's ability to use any other. Platform admins keep
        # their own independent login even with zero company memberships.
        remaining_companies = CompanyMember.objects.filter(user=user).exists()
        deactivate_account = not remaining_companies and not is_admin(user)
        if deactivate_account and user.is_active:
            user.is_active = False
            user.save(update_fields=["is_active"])

        log_event(
            company=company,
            actor=request.user,
            verb=ActivityEvent.Verb.COMPANY_MEMBER_REMOVED,
            meta={
                "company_id": company.pk,
                "company_name": company.name,
                "user_id": user.pk,
                "user_email": user.email,
                "user_name": user.get_full_name(),
                "removed_role": removed_role,
                "remaining_company_memberships": CompanyMember.objects.filter(user=user).count(),
                "account_deactivated": deactivate_account,
            },
        )

    if deactivate_account:
        messages.success(
            request,
            f"{user.email or user.username} togs bort från {company.name}. "
            "Det sista företagsmedlemskapet är borttaget och användarkontot "
            "är nu inaktiverat. Tidigare projekt och historik finns kvar.",
        )
    else:
        messages.success(
            request,
            f"{user.email or user.username} togs bort från {company.name}. "
            "Kontot är fortfarande aktivt och andra företagskopplingar påverkas inte.",
        )
    return redirect("accounts:company_users", pk=company.pk)


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

def invalid_invite_link(request, invalid_path):
    """Uniform, non-enumerating fallback for malformed account invite URLs."""
    return render(request, "accounts/invite_invalid.html", status=400)


def accept_invite_uuid(request, invite_id):
    # Do not disclose whether an account exists or which invite state failed.
    # The same helpful page is used for unknown, revoked, used and expired links.
    invite = UserInvite.objects.select_related("user", "company").filter(id=invite_id).first()
    if invite is None:
        return render(request, "accounts/invite_invalid.html", status=400)

    max_age = timedelta(days=max(1, int(getattr(settings, "TALENA_ACCOUNT_INVITE_EXPIRY_DAYS", 14))))
    expired = timezone.now() >= invite.created_at + max_age
    if invite.revoked_at is not None or invite.accepted_at is not None or expired:
        return render(request, "accounts/invite_invalid.html", status=400)
    # Never reactivate an account via an orphaned link after its company
    # membership has been removed. A fresh admin invitation is required.
    if not CompanyMember.objects.filter(
        user_id=invite.user_id, company_id=invite.company_id,
    ).exists():
        return render(request, "accounts/invite_invalid.html", status=400)

    user = invite.user
    if user.is_active:
        return render(request, "accounts/invite_invalid.html", status=400)

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
def company_rename(request, company_pk):
    """Rename a company in Talena only; preserve IDs, organisation number and Sova links."""
    company = get_object_or_404(Company, pk=company_pk)
    # ModelForm.is_valid() copies cleaned form values onto instance. Capture
    # the previous name FIRST so the change check and audit log stay correct.
    old_name = company.name
    form = CompanyNameForm(request.POST, instance=company)
    if not form.is_valid():
        messages.error(request, "Ange ett giltigt företagsnamn (max 255 tecken).")
        return redirect("accounts:company_detail", pk=company.pk)

    new_name = form.cleaned_data["name"]
    if old_name != new_name:
        company.name = new_name
        company.save(update_fields=["name", "updated_at"])
        log_event(
            company=company, actor=request.user,
            verb=ActivityEvent.Verb.COMPANY_UPDATED,
            meta={
                "company_id": company.pk, "company_name": new_name,
                "old_name": old_name, "new_name": new_name,
            },
        )
        messages.success(request, f"Företagsnamnet har ändrats till {new_name}.")
    else:
        messages.info(request, "Företagsnamnet är oförändrat.")
    return redirect("accounts:company_detail", pk=company.pk)


def _orgunit_delete_blocker(unit):
    """Require an unused leaf unit; deleting it must not cascade user access or history."""
    if unit.unit_code == "MAIN":
        return "Huvudkontot (MAIN) behövs i Talena och kan inte raderas."
    if unit.children.exists():
        return "Kontot har underkonton. Flytta eller ta bort dem först."
    if unit.processes.exists():
        return "Kontot används av rekryteringsprojekt och kan inte raderas."
    if unit.teams.exists():
        return "Kontot används av team och kan inte raderas."
    if unit.assessment_usages.exists():
        return "Kontot har testhistorik och kan inte raderas."
    if unit.primary_members.exists():
        return "Kontot är primärt konto för användare. Ändra deras åtkomst först."
    if unit.user_accesses.exists():
        return "Användare har åtkomst till kontot. Ta bort deras åtkomst först."
    return ""


@login_required
@admin_required
@require_POST
def orgunit_rename(request, company_pk, unit_pk):
    company = get_object_or_404(Company, pk=company_pk)
    unit = get_object_or_404(OrgUnit, company=company, pk=unit_pk)
    # Preserve the old name before the ModelForm populates instance.
    old_name = unit.name
    form = OrgUnitNameForm(request.POST, instance=unit)
    if not form.is_valid():
        messages.error(request, "Ange ett giltigt kontonamn (max 200 tecken).")
        return redirect("accounts:company_account_structure", pk=company.pk)

    new_name = form.cleaned_data["name"]
    if new_name != old_name:
        unit.name = new_name
        unit.save(update_fields=["name", "updated_at"])
        log_event(
            company=company, actor=request.user,
            verb=ActivityEvent.Verb.ORGUNIT_UPDATED,
            meta={
                "company_id": company.pk, "org_unit_id": unit.pk,
                "org_unit_name": new_name, "unit_code": unit.unit_code,
                "old_name": old_name, "new_name": new_name,
            },
        )
        messages.success(request, f"Kontot har bytt namn till {new_name}.")
    else:
        messages.info(request, "Kontonamnet är oförändrat.")
    return redirect("accounts:company_account_structure", pk=company.pk)


@login_required
@admin_required
@require_POST
def orgunit_delete(request, company_pk, unit_pk):
    """Only remove unused units; never delete projects, teams or permissions."""
    company = get_object_or_404(Company, pk=company_pk)
    with transaction.atomic():
        # Coordinate with other deletions in this company.
        unit = get_object_or_404(
            OrgUnit.objects.select_for_update(), pk=unit_pk, company=company,
        )
        blocker = _orgunit_delete_blocker(unit)
        if blocker:
            messages.error(request, blocker)
            return redirect("accounts:company_account_structure", pk=company.pk)

        unit_id, old_name, unit_code = unit.pk, unit.name, unit.unit_code
        try:
            unit.delete()
        except ProtectedError:
            messages.error(request, "Kontot används fortfarande och kan inte raderas.")
            return redirect("accounts:company_account_structure", pk=company.pk)

        log_event(
            company=company, actor=request.user,
            verb=ActivityEvent.Verb.ORGUNIT_DELETED,
            meta={
                "company_id": company.pk, "org_unit_id": unit_id,
                "org_unit_name": old_name, "unit_code": unit_code,
            },
        )
    messages.success(request, f"Kontot {old_name} har tagits bort.")
    return redirect("accounts:company_account_structure", pk=company.pk)


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

    # Explain disabled delete icons in the tree. Revalidate on POST.
    for unit in all_units:
        unit.delete_blocker = _orgunit_delete_blocker(unit)

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

    project_scopes = {}
    projects_by_unit = {}
    if selected_user:
        for scope in UserOrgUnitProjectAccess.objects.filter(
            user=selected_user,
            org_unit__company=company,
        ).prefetch_related("projects"):
            project_scopes[scope.org_unit_id] = set(
                scope.projects.values_list("id", flat=True)
            )
    for process in TestProcess.objects.filter(
        company=company,
        org_unit__isnull=False,
    ).only("id", "name", "org_unit_id").order_by("name"):
        projects_by_unit.setdefault(process.org_unit_id, []).append(process)

    return render(request, "admin/accounts/companies/company_user_access.html", {
        "company": company,
        "project_scopes": project_scopes,
        "projects_by_unit": projects_by_unit,
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
    project_scopes = payload.get("project_scopes", [])
    if not isinstance(project_scopes, list):
        return JsonResponse({"ok": False, "error": "project_scopes must be a list"}, status=400)

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

        # Replace optional per-unit project restrictions. Opening a list in the
        # admin UI does not submit a restriction unless "Selected projects" is chosen.
        UserOrgUnitProjectAccess.objects.filter(
            user=user,
            org_unit__company=company,
        ).delete()
        seen_scope_ids = set()
        scopes_to_create = []
        for row in project_scopes:
            try:
                unit_id = int(row.get("org_unit_id"))
            except (TypeError, ValueError):
                return JsonResponse({"ok": False, "error": "Invalid project scope unit"}, status=400)
            restricted = row.get("restricted") is True
            if not restricted:
                continue
            if unit_id in seen_scope_ids or unit_id not in found_ids:
                return JsonResponse({"ok": False, "error": "Invalid or duplicate project scope unit"}, status=400)
            seen_scope_ids.add(unit_id)
            raw_project_ids = row.get("project_ids", [])
            if not isinstance(raw_project_ids, list):
                return JsonResponse({"ok": False, "error": "project_ids must be a list"}, status=400)
            try:
                project_ids = {int(value) for value in raw_project_ids}
            except (TypeError, ValueError):
                return JsonResponse({"ok": False, "error": "Invalid project id"}, status=400)
            unit = next(item for item in units if item.id == unit_id)
            valid_ids = set(TestProcess.objects.filter(
                company=company,
                org_unit=unit,
                id__in=project_ids,
            ).values_list("id", flat=True))
            if project_ids != valid_ids:
                return JsonResponse({"ok": False, "error": "Selected projects must belong to their unit"}, status=400)
            scopes_to_create.append((unit, project_ids))
        for unit, project_ids in scopes_to_create:
            scope = UserOrgUnitProjectAccess.objects.create(user=user, org_unit=unit)
            scope.projects.set(project_ids)

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
        .annotate(
            company_admin_count=Count(
                "company__memberships",
                filter=Q(company__memberships__role=CompanyMember.ROLE_ADMIN),
            )
        )
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
        accounts = client.get_template_accounts_with_projects()
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

            messages.success(request, "Projekt skapat.")
            return redirect(next_url)

        messages.error(request, "Kunde inte skapa projekt. Kontrollera fälten.")
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
        accounts = client.get_template_accounts_with_projects()
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
    # An existing, locked process may still point to Main Account. Preserve
    # that choice for edits to labels/name without offering it for new processes.
    if locked and current_value and current_value not in dict(choices):
        legacy_title = obj.project_name_snapshot or old_proj
        choices.append((current_value, legacy_title))
        template_cards.append({
            "value": current_value,
            "title": legacy_title,
            "subtitle": f"{old_acc} · {old_proj}",
            "icon": "layers",
            "account_code": old_acc,
            "project_code": old_proj,
            "sova_name": legacy_title,
        })


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
                    "Du kan inte ändra testpaket efter att tester har skickats i projektet."
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

            messages.success(request, "Projekt uppdaterat.")
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
def admin_confirm_sova_revocation(request, process_id, candidate_id):
    """Manually record VERIFIED provider revocation; no API call is implied."""
    if request.POST.get("verified_in_sova") != "yes":
        return HttpResponseForbidden("Explicit verification in Sova required.")
    invitation = get_object_or_404(
        TestInvitation,
        process_id=process_id, candidate_id=candidate_id,
        removed_from_process_at__isnull=False,
        sova_revocation_state="manual_pending",
    )
    invitation.sova_revocation_state = "confirmed"
    invitation.save(update_fields=["sova_revocation_state"])
    log_event(
        company=invitation.process.company,
        verb=ActivityEvent.Verb.CANDIDATE_REMOVED,
        actor=request.user,
        process=invitation.process,
        candidate=invitation.candidate,
        meta={"action": "sova_revocation_manually_verified"},
    )
    messages.success(request, "Bekräftad spärrning hos Sova har registrerats.")
    return redirect("accounts:admin_process_detail", pk=process_id)


@admin_required
@require_POST
def admin_remove_candidate_from_process(request, process_id, candidate_id):
    process = get_object_or_404(TestProcess, pk=process_id)

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate_id=candidate_id,
    )
    from apps.processes.services.candidate_project_removal import remove_candidate_from_project
    outcome = remove_candidate_from_project(invitation=invitation, actor=request.user)
    if outcome == "hidden":
        messages.warning(
            request,
            "Borttagen från aktiva listan. Sova-testlänken är INTE automatiskt spärrad. "
            "Kontakta Sova för manuell återkallelse.",
        )
    else:
        messages.success(request, "Kandidaten togs bort från projektet.")
    return redirect("accounts:admin_process_detail", pk=process.id)


def _admin_process_return_url(process, submitted_url):
    """Default to the admin project workspace; permit only safe project-local return URLs."""
    default = reverse("accounts:admin_process_detail", kwargs={"pk": process.pk})
    if process.company_id:
        company_url = reverse(
            "accounts:company_process_detail",
            kwargs={"company_pk": process.company_id, "process_pk": process.pk},
        )
        # The legacy admin-tools view uses a fixed query flag. Preserve this
        # explicit return target without allowing arbitrary redirect URLs.
        if submitted_url in (company_url, f"{company_url}?admin_tools=1"):
            return submitted_url
    return default


@admin_required
def admin_process_send_tests(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)
    return_url = _admin_process_return_url(process, request.POST.get("next"))
    swedish = (get_language() or "sv").startswith("sv")

    if request.method != "POST":
        return redirect(return_url)

    if (
        process.is_historical
        or process.is_archived
        or not process.sova_sync_enabled
        or not process.account_code
        or not process.project_code
    ):
        messages.error(
            request,
            "Projektet är inte ett aktivt Sova-projekt som kan skicka tester."
            if swedish else "This project is not an active Sova project that can send tests.",
        )
        return redirect(return_url)

    invitation_ids = request.POST.getlist("invitation_ids")
    if not invitation_ids:
        messages.warning(
            request,
            "Välj minst en kandidat." if swedish else "Select at least one candidate.",
        )
        return redirect(return_url)

    # Never accept IDs belonging to a different project or removed candidates.
    # Expired/sent/started/completed invitations must not be reordered.
    invitations = list(
        TestInvitation.objects.filter(
            process=process,
            id__in=invitation_ids,
            removed_from_process_at__isnull=True,
            status__in=("created", "failed"),
        ).select_related("candidate")
    )
    if not invitations:
        messages.info(
            request,
            "Inga valda kandidater har oskickade tester. Redan skickade, "
            "påbörjade, avslutade eller utgångna tester skickas inte igen."
            if swedish else
            "No selected candidate has a pending invitation. Sent, started, "
            "completed or expired tests will not be ordered again.",
        )
        return redirect(return_url)

    try:
        result = send_assessments_and_emails(
            process=process,
            invitations=invitations,
            actor_user=request.user,
            context="admin",
        )
    except Exception as exc:
        # Never render provider exception bodies or candidate details in the UI.
        import logging
        logging.getLogger(__name__).warning(
            "Admin Sova send could not start: process_id=%s error_type=%s",
            process.pk, type(exc).__name__,
        )
        messages.error(
            request,
            "Utskicket kunde inte startas. Kontrollera Sova-inställningarna "
            "och försök igen. Ingen ny inbjudan ska skapas manuellt."
            if swedish else
            "The send could not be started. Check the Sova configuration "
            "and retry. Do not create another invitation manually.",
        )
        return redirect(return_url)

    if result.get("sent_count"):
        messages.success(
            request,
            f"Tester skickade till {result['sent_count']} kandidat(er)."
            if swedish else f"Tests sent to {result['sent_count']} candidate(s).",
        )

    if result.get("errors"):
        # Errors returned by the shared service can contain external response
        # bodies or candidate email addresses: never disclose them here.
        messages.error(
            request,
            f"Utskicket misslyckades för {len(result['errors'])} kandidat(er). "
            "Kontrollera Sova-konfiguration och mejlleverans. "
            "Det går att försöka igen utan att beställa om redan skapade tester."
            if swedish else
            f"Sending failed for {len(result['errors'])} candidate(s). "
            "Check the Sova configuration and email delivery. You can retry "
            "without reordering assessments that were already created.",
        )

    if not result.get("sent_count") and not result.get("errors"):
        messages.info(
            request,
            "Inget ytterligare utskick behövdes."
            if swedish else "No additional invitations needed to be sent.",
        )

    return redirect(return_url)


@admin_required
def admin_process_invitation_statuses(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    qs = (
        TestInvitation.objects
        .filter(process=process, removed_from_process_at__isnull=True)
        .select_related("candidate", "process__company")
        .prefetch_related("assessment_usages")
        .order_by("created_at")
    )
    columns = project_test_columns(
        process,
        ProjectMeta.objects.filter(
            account_code=process.account_code, project_code=process.project_code,
        ).first(),
    )
    lang = get_language() or "sv"
    return JsonResponse({
        "invitations": [
            {
                "id": inv.id,
                "status": inv.status,
                "completed_at": inv.completed_at.isoformat() if inv.completed_at else None,
                "sova_overall_status": getattr(inv, "sova_overall_status", "") or "",
                "assessments": invitation_test_statuses(inv, columns, lang),
            }
            for inv in qs
        ]
    })



@login_required
@admin_required
def admin_process_add_candidate(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    submitted_next = (
        request.POST.get("next") if request.method == "POST"
        else request.GET.get("next")
    )
    return_url = _admin_process_return_url(process, submitted_next)

    if process.is_historical or process.is_archived or not process.sova_sync_enabled:
        return HttpResponseForbidden("This project does not accept live candidates.")

    if request.method == "POST":
        form = CandidateCreateForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()

            candidate, _ = Candidate.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": form.cleaned_data["first_name"],
                    "last_name": form.cleaned_data["last_name"],
                },
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

            if invitation.removed_from_process_at:
                # Removed links are retained for audit; never quietly reactivate.
                message = (
                    "Kandidaten har tidigare tagits bort från projektet. "
                    "Kontrollera historiken innan kandidaten återaktiveras."
                )
                messages.warning(request, message)
                if is_ajax:
                    return JsonResponse({"ok": False, "message": message}, status=409)
                return redirect(return_url)

            if not inv_created and invitation.source == "invited" and not invitation.invited_by_id:
                invitation.invited_by = request.user
                invitation.save(update_fields=["invited_by"])

            if inv_created:
                message = "Kandidaten har lagts till i projektet."
                messages.success(request, message)
            else:
                message = "Kandidaten finns redan i projektet. Ingen dubbel inbjudan skapades."
                messages.info(request, message)

            if is_ajax:
                return JsonResponse({
                    "ok": True,
                    "message": message,
                    "redirect_url": return_url,
                })

            return redirect(return_url)

        if is_ajax:
            return render(
                request,
                "admin/accounts/customer/_add_candidate_form.html",
                {"process": process, "form": form},
                status=400,
            )
    else:
        form = CandidateCreateForm()

    if is_ajax:
        return render(
            request,
            "admin/accounts/customer/_add_candidate_form.html",
            {"process": process, "form": form},
        )

    return render(
        request,
        "admin/accounts/customer/process_add_candidate.html",
        {"process": process, "form": form, "next_url": return_url},
    )


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
    messages.success(request, f"Projektet '{process_name}' raderades.")
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
        CompanyMember.objects.select_related("company", "primary_org_unit")
        .annotate(
            company_admin_count=Count(
                "company__memberships",
                filter=Q(company__memberships__role=CompanyMember.ROLE_ADMIN),
            )
        ),
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

    # Talena staff open the real customer project workspace by default.
    # The previous administrative overview remains available explicitly for
    # internal operations (historical imports, audit and billing controls).
    if request.GET.get("admin_tools") != "1":
        return redirect("processes:process_detail", pk=process.pk)

    invitations = (
        TestInvitation.objects
        .filter(process=process, removed_from_process_at__isnull=True)
        .select_related("candidate", "process__company")
        .prefetch_related("assessment_usages")
        .order_by("-created_at")
    )

    # Internal audit only. This queryset must never be sent to customer views.
    removed_invitations = (
        TestInvitation.objects.filter(
            process=process,
            removed_from_process_at__isnull=False,
        ).select_related("candidate").order_by("-removed_from_process_at")
    )

    historical_candidates = (
        HistoricalProcessCandidate.objects
        .filter(process=process)
        .select_related("candidate", "created_by")
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
    meta = ProjectMeta.objects.filter(
        account_code=process.account_code, project_code=process.project_code,
    ).first()
    project_tests = [] if process.is_historical else project_test_columns(process, meta)
    attach_test_statuses(invitations, project_tests, get_language() or "sv")

    return render(request, "admin/accounts/companies/company_process_detail.html", {
        "company": company,
        "process": process,
        "invitations": invitations,
        "removed_invitations": removed_invitations,
        "project_tests": project_tests,
        "project_table_colspan": max(1, len(project_tests)) + 5,
        "sendable_count": invitations.filter(status__in=("created", "failed")).count() if not process.is_archived and process.sova_sync_enabled else 0,
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
    """Render the exact customer candidate sheet without admin-only AI writes."""
    company = get_object_or_404(Company, pk=company_pk)
    process = get_object_or_404(
        TestProcess.objects.select_related("company", "created_by", "org_unit"),
        pk=process_pk, company=company,
    )
    language_code = get_request_ai_language(request)

    if process.is_historical:
        historical_candidate = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related("candidate", "process", "created_by")
            .prefetch_related(
                "reports", "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process, candidate_id=candidate_pk,
        )
        ctx = build_shared_historical_candidate_detail_context(
            process=process,
            historical_candidate=_admin_readonly_ai_state(historical_candidate, language_code),
            language=language_code,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation.objects.select_related("candidate", "process"),
            process=process, candidate_id=candidate_pk,
            removed_from_process_at__isnull=True,
        )
        from apps.processes.services.automatic_interview_questions import (
            generate_ready_interview_questions,
        )

        # Backfill question sets for completed tests that predate automatic
        # Sova-callback generation, so the admin mirror can show them too.
        generate_ready_interview_questions(invitation)
        invitation.refresh_from_db()
        ctx = build_candidate_detail_context(
            process=process, invitation=invitation, language=language_code,
        )
        ctx["is_historical"] = False

    ctx.update(_admin_saved_after_interview_context(
        process=process,
        candidate=ctx["candidate"],
        owner=historical_candidate if process.is_historical else invitation,
        language_code=language_code,
    ))
    ctx.update({
        "company": company,
        "process": process,
        "is_admin_view": True,
        "is_company_view": True,
        "is_admin_candidate_mirror": True,
        "can_manage_candidate_results": False,
        "active": "processes",
        "show_invite_button": True,
    })
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(
            request, "admin/accounts/companies/company_candidate_sheet.html", ctx,
        )
    ctx["invite_form"] = CompanyInviteMemberForm()
    return render(
        request, "admin/accounts/companies/company_candidate_detail.html", ctx,
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
            process.purpose = "unsure"
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

            messages.success(request, "Historical project created.")
            return redirect(
                "accounts:company_process_detail",
                company_pk=company.pk,
                process_pk=process.pk,
            )

        messages.error(request, "Could not create historical project. Check the form fields.")

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
        form = HistoricalCandidateForm(
            request.POST,
            request.FILES,
            company=company,
        )

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

            selected_teams = list(form.cleaned_data.get("teams") or [])
            new_team_name = (form.cleaned_data.get("new_team_name") or "").strip()

            if new_team_name:
                new_team, _ = Team.objects.get_or_create(
                    company=company,
                    name=new_team_name,
                    defaults={
                        "description": "Created while adding historical candidate."
                    },
                )
                selected_teams.append(new_team)

            assigned_team_count = 0

            for team in selected_teams:
                _, membership_created = TeamMembership.objects.get_or_create(
                    team=team,
                    candidate=candidate,
                    defaults={
                        "source": "historical_import",
                    },
                )

                if membership_created:
                    assigned_team_count += 1

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
                    "assigned_teams": assigned_team_count,
                },
            )

            message_parts = ["Historical candidate added"]

            if uploaded_reports:
                message_parts.append(f"{len(uploaded_reports)} report(s) uploaded")

            if selected_teams:
                message_parts.append(f"assigned to {len(selected_teams)} team(s)")

            messages.success(request, ". ".join(message_parts) + ".")

            return redirect(
                "accounts:company_process_detail",
                company_pk=company.pk,
                process_pk=process.pk,
            )

        messages.error(request, "Could not add historical candidate. Check the form fields.")

    else:
        form = HistoricalCandidateForm(company=company)


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
    project_owners = list(
        CompanyMember.objects.filter(company=company, user__is_active=True)
        .exclude(user__is_staff=True)
        .exclude(user__is_superuser=True)
        .select_related("user")
        .order_by("user__first_name", "user__last_name", "user__email")
    )

    error = None

    # --------------------------------------------------
    # 1. Hämta mallar från det konfigurerade Sova-kontot.
    # --------------------------------------------------
    try:
        client = SovaClient()
        accounts = client.get_template_accounts_with_projects()
    except Exception as exc:
        # Do not reveal provider errors, credential details or request bodies.
        accounts = []
        error = (
            "Could not load Sova Modern Projects. Check the integration "
            "configuration and try again. ("
            + type(exc).__name__ + ")"
        )

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

            if not tests:
                tests = extract_tests_from_project_name(sova_name)

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
        "project_owners": project_owners,
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
        form = TestProcessWizardCreateForm(request.POST, org_units=org_units)

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
                    "Please select which account/unit this project belongs to."
                )

                return render(
                    request,
                    "admin/accounts/companies/company_process_create.html",
                    {
                        **context_base,
                        "form": form,
                    },
                )

            # The owning customer must actually have access to the chosen
            # unit. Own-only customer access depends on created_by matching.
            project_owner = request.user
            if project_owners:
                owner_id = (request.POST.get("project_owner") or "").strip()
                project_owner = next(
                    (member.user for member in project_owners
                     if str(member.user_id) == owner_id),
                    None,
                )
                if project_owner is None:
                    form.add_error(
                        None, "Select a project owner from this customer."
                    )
                    return render(
                        request, "admin/accounts/companies/company_process_create.html",
                        {**context_base, "form": form},
                    )
                if not get_effective_orgunit_permissions(
                    project_owner, company
                ).get(org_unit.id):
                    form.add_error(
                        None, "The selected project owner has no access to this account/unit."
                    )
                    return render(
                        request, "admin/accounts/companies/company_process_create.html",
                        {**context_base, "form": form},
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

            try:
                resolved_template = resolve_sova_template(selected_tests, template_cards)
            except ValueError as exc:
                form.add_error("selected_tests", str(exc))
                return render(
                    request,
                    "admin/accounts/companies/company_process_create.html",
                    {**context_base, "form": form},
                )

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
                created_by=project_owner,
                created_by_admin=request.user,
                purpose=purpose,
                selected_tests=selected_tests,
                candidate_language=form.cleaned_data["candidate_language"],
                candidate_results_enabled=form.cleaned_data.get("candidate_results_enabled", False),
                project_completion_notifications_enabled=form.cleaned_data.get("project_completion_notifications_enabled", True),
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

            messages.success(request, "SOVA project created.")
            return redirect(
                "accounts:company_process_detail",
                company_pk=company.pk,
                process_pk=obj.pk,
            )

        messages.error(request, "Could not create SOVA project. Check the form fields.")

    else:
        form = TestProcessWizardCreateForm(org_units=org_units)

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
        messages.info(request, "This project is already archived.")
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

    messages.success(request, "Project archived.")
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
        messages.info(request, "This project is not archived.")
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

    messages.success(request, "Project restored.")
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
            "This project cannot be deleted because tests have been sent, started or completed. Archive it instead."
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

    messages.success(request, f"Project '{process_name}' deleted.")
    return redirect(
        "accounts:company_processes",
        pk=company.pk,
    )

@login_required
@admin_required
@require_POST
def account_invitation_preview(request, company_pk=None):
    """Admin-only, no-send preview of the real account invitation markup."""
    company = get_object_or_404(Company, pk=company_pk) if company_pk is not None else None
    # Show only synthetic recipient data; never generate or reveal real tokens.
    example_user = SimpleNamespace(first_name="Alex", email="alex@example.com")
    sample_invitation_url = request.build_absolute_uri(
        reverse("accounts:accept_invite_uuid", kwargs={"invite_id": uuid.UUID(int=0)})
    )
    subject, _text, email_html = render_account_invitation(
        request, example_user, sample_invitation_url, company,
        subject=(request.POST.get("invite_subject") or "")[:160] or None,
        message=(request.POST.get("invite_message") or "")[:3000] or None,
        language=request.POST.get("invite_language") or "en",
    )
    response = render(request, "admin/accounts/account_invite_preview.html", {
        "subject": subject,
        "email_html": email_html,
    })
    response["Cache-Control"] = "no-store, private"
    response["Referrer-Policy"] = "no-referrer"
    return response


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
                    "preferred_language": invite_form.cleaned_data.get("invite_language") or "en",
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
                subject=invite_form.cleaned_data["invite_subject"],
                message=invite_form.cleaned_data["invite_message"],
                language=invite_form.cleaned_data["invite_language"],
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


@login_required
@admin_required
def company_historical_candidate_edit(request, company_pk, process_pk, candidate_pk):
    company = get_object_or_404(Company, pk=company_pk)

    process = get_object_or_404(
        TestProcess,
        pk=process_pk,
        company=company,
        is_historical=True,
    )

    historical_candidate = get_object_or_404(
        HistoricalProcessCandidate.objects
        .select_related("candidate", "process", "created_by"),
        process=process,
        candidate_id=candidate_pk,
    )

    candidate = historical_candidate.candidate

    if request.method == "POST":
        form = HistoricalCandidateForm(
            request.POST,
            request.FILES,
            company=company,
            historical_candidate=historical_candidate,
        )

        if form.is_valid():
            new_email = form.cleaned_data["email"].strip().lower()

            candidate.first_name = form.cleaned_data["first_name"]
            candidate.last_name = form.cleaned_data["last_name"]
            candidate.email = new_email
            candidate.save(update_fields=["first_name", "last_name", "email"])

            historical_candidate.status = form.cleaned_data["status"]
            historical_candidate.notes = form.cleaned_data.get("historical_notes") or ""
            historical_candidate.save(update_fields=["status", "notes"])

            selected_teams = list(form.cleaned_data.get("teams") or [])
            new_team_name = (form.cleaned_data.get("new_team_name") or "").strip()

            if new_team_name:
                new_team, _ = Team.objects.get_or_create(
                    company=company,
                    name=new_team_name,
                    defaults={
                        "description": "Created while editing historical candidate."
                    },
                )
                selected_teams.append(new_team)

            selected_team_ids = [team.id for team in selected_teams]

            TeamMembership.objects.filter(
                candidate=candidate,
                team__company=company,
            ).exclude(
                team_id__in=selected_team_ids
            ).delete()

            assigned_team_count = 0

            for team in selected_teams:
                _, membership_created = TeamMembership.objects.get_or_create(
                    team=team,
                    candidate=candidate,
                    defaults={
                        "source": "historical_edit",
                    },
                )

                if membership_created:
                    assigned_team_count += 1

            log_event(
                company=company,
                verb=ActivityEvent.Verb.CANDIDATE_ADDED,
                actor=request.user,
                process=process,
                candidate=candidate,
                meta={
                    "source": "historical_edit",
                    "uploaded_reports": len(uploaded_reports),
                    "selected_teams": len(selected_teams),
                    "new_team_memberships": assigned_team_count,
                },
            )

            messages.success(request, "Historical candidate updated.")
            return redirect(
                "accounts:company_process_detail",
                company_pk=company.pk,
                process_pk=process.pk,
            )

        messages.error(request, "Could not update historical candidate. Check the form fields.")

    else:
        form = HistoricalCandidateForm(
            company=company,
            historical_candidate=historical_candidate,
        )

    return render(request, "admin/accounts/companies/company_historical_candidate_form.html", {
        "company": company,
        "process": process,
        "candidate": candidate,
        "historical_candidate": historical_candidate,
        "form": form,
        "is_edit": True,
        "active": "processes",
        "show_invite_button": True,
        "invite_form": CompanyInviteMemberForm(),
    })


@login_required
@admin_required
def company_historical_assessment_import_upload(request, company_pk, process_pk):
    company = get_object_or_404(Company, pk=company_pk)

    process = get_object_or_404(
        TestProcess,
        pk=process_pk,
        company=company,
        is_historical=True,
    )

    import_results = []

    if request.method == "POST":
        form = HistoricalAssessmentImportForm(request.POST, request.FILES)

        if form.is_valid():
            files = request.FILES.getlist("files")

            for uploaded_file in files:
                result = import_historical_assessment_file(
                    process=process,
                    uploaded_file=uploaded_file,
                    user=request.user,
                )
                import_results.append(result)

            messages.success(
                request,
                f"Imported {len(import_results)} SOVA data extract file(s)."
            )

            return render(
                request,
                "admin/accounts/companies/company_historical_assessment_import_result.html",
                {
                    "company": company,
                    "process": process,
                    "import_results": import_results,
                    "active": "processes",
                    "show_invite_button": True,
                    "invite_form": CompanyInviteMemberForm(),
                },
            )

        messages.error(request, "Could not import files. Please check the uploaded files.")

    else:
        form = HistoricalAssessmentImportForm()

    return render(
        request,
        "admin/accounts/companies/company_historical_assessment_import_upload.html",
        {
            "company": company,
            "process": process,
            "form": form,
            "active": "processes",
            "show_invite_button": True,
            "invite_form": CompanyInviteMemberForm(),
        },
    )
