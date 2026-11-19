from types import SimpleNamespace

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.shortcuts import render

from apps.projects.models import ProjectMeta
from apps.processes.models import (
    Candidate,
    HistoricalProcessCandidate,
    TestInvitation,
)
from apps.processes.services.access import get_accessible_processes_for_user
from apps.teams.models import TeamMembership
from apps.teams.views import _team_visibility_queryset


TEST_DEFINITIONS = [
    {
        "key": "personality",
        "label": "PQ",
        "name": "Personality",
    },
    {
        "key": "motivation",
        "label": "MQ",
        "name": "Motivation",
    },
    {
        "key": "logical",
        "label": "L",
        "name": "Logical reasoning",
    },
    {
        "key": "verbal",
        "label": "V",
        "name": "Verbal reasoning",
    },
    {
        "key": "numerical",
        "label": "N",
        "name": "Numerical reasoning",
    },
]


TEST_STATUS_RANK = {
    "not_sent": 0,
    "pending": 1,
    "completed": 2,
}


def normalize_test_key(value):
    """
    Converts names from:
    - process.selected_tests
    - ProjectMeta.tests
    - Sova activities
    - historical assessment types

    into the same five internal test keys.
    """
    text = str(value or "").strip().lower()

    if not text:
        return None

    if (
        "personality" in text
        or "personlighet" in text
        or text == "pq"
    ):
        return "personality"

    if (
        "motivation" in text
        or text == "mq"
    ):
        return "motivation"

    if (
        "logical" in text
        or "logisk" in text
    ):
        return "logical"

    if "verbal" in text:
        return "verbal"

    if (
        "numerical" in text
        or "numeric" in text
        or "numerisk" in text
    ):
        return "numerical"

    return None


def normalize_activity_status(value):
    """
    Converts Sova/activity statuses into the three statuses
    used in the candidate overview.
    """
    status = str(value or "").strip().lower()

    if status in {
        "completed",
        "complete",
        "finished",
        "done",
        "result available",
        "result_available",
        "passed",
        "failed",
    }:
        return "completed"

    if status in {
        "sent",
        "started",
        "in progress",
        "in_progress",
        "invited",
    }:
        return "pending"

    return "not_sent"


def update_test_status(statuses, test_key, new_status):
    """
    Keeps the strongest known status:

    completed > pending > not_sent
    """
    if test_key not in statuses:
        return

    current_status = statuses[test_key]["status"]

    if TEST_STATUS_RANK[new_status] > TEST_STATUS_RANK[current_status]:
        statuses[test_key]["status"] = new_status


def get_process_test_keys(process, project_meta_by_key):
    """
    Finds which tests are included in a process.

    Uses selected_tests first and ProjectMeta.tests as a fallback.
    """
    test_keys = set()

    selected_tests = process.selected_tests or []

    if isinstance(selected_tests, str):
        selected_tests = [
            item.strip()
            for item in selected_tests.split(",")
            if item.strip()
        ]

    for test_name in selected_tests:
        test_key = normalize_test_key(test_name)

        if test_key:
            test_keys.add(test_key)

    meta = project_meta_by_key.get(
        (
            process.account_code,
            process.project_code,
        )
    )

    if meta:
        meta_tests = [
            item.strip()
            for item in (meta.tests or "").split(",")
            if item.strip()
        ]

        for test_name in meta_tests:
            test_key = normalize_test_key(test_name)

            if test_key:
                test_keys.add(test_key)

    return test_keys


def _empty_test_overview():
    """Start each project membership from a clean, independent test state."""
    return {
        definition["key"]: {
            **definition,
            "status": "not_sent",
            "completed_count": 0,
            "pending_count": 0,
        }
        for definition in TEST_DEFINITIONS
    }


def _live_membership_test_overview(invitation, project_meta_by_key):
    """Show results for THIS invitation, never those from another project.

    Individual Sova activity statuses take precedence over an invitation's
    overall status. In particular, a pending activity must not be painted as
    completed just because the invitation has an overall completed flag.
    """
    statuses = _empty_test_overview()
    included_keys = get_process_test_keys(
        invitation.process, project_meta_by_key,
    )
    raw_status = str(invitation.status or "").strip().lower()
    if raw_status == "completed":
        base_status = "completed"
    elif raw_status in {"sent", "started", "expired"}:
        base_status = "pending"
    else:
        base_status = "not_sent"

    activity_status_by_key = {}
    for activity in invitation.sova_activities or []:
        if not isinstance(activity, dict):
            continue
        key = normalize_test_key(
            activity.get("activity") or activity.get("name"),
        )
        if not key:
            continue
        status = normalize_activity_status(activity.get("status"))
        existing = activity_status_by_key.get(key)
        if existing is None or TEST_STATUS_RANK[status] > TEST_STATUS_RANK[existing]:
            activity_status_by_key[key] = status

    for key in included_keys | set(activity_status_by_key):
        if key not in statuses:
            continue
        status = activity_status_by_key.get(
            key, base_status if key in included_keys else "not_sent",
        )
        update_test_status(statuses, key, status)
        if status == "completed":
            statuses[key]["completed_count"] = 1
        elif status == "pending":
            statuses[key]["pending_count"] = 1

    return [statuses[definition["key"]] for definition in TEST_DEFINITIONS]


def _historical_membership_test_overview(membership):
    """Only the assessment results attached to this historical project count."""
    statuses = _empty_test_overview()
    completed_keys = set()
    for result in membership.assessment_results.all():
        key = normalize_test_key(result.assessment_type)
        if key:
            completed_keys.add(key)

    for key in completed_keys:
        update_test_status(statuses, key, "completed")
        statuses[key]["completed_count"] = 1

    return [statuses[definition["key"]] for definition in TEST_DEFINITIONS]


@login_required
def candidate_list(request):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )
    accessible_process_ids = list(
        accessible_processes.values_list("id", flat=True)
    )

    # Keep permission scopes at the project membership level. A Candidate is
    # global (unique by email), but each TestInvitation / historical membership
    # is a distinct assessment record and must have its own row and link.
    live_memberships = list(
        TestInvitation.objects
        .filter(
            process_id__in=accessible_process_ids,
            process__is_historical=False,
            removed_from_process_at__isnull=True,
        )
        .select_related("process", "candidate")
    )
    historical_memberships = list(
        HistoricalProcessCandidate.objects
        .filter(
            process_id__in=accessible_process_ids,
            process__is_historical=True,
        )
        .select_related("process", "candidate")
        .prefetch_related("assessment_results")
    )

    candidate_ids = {
        membership.candidate_id
        for membership in live_memberships + historical_memberships
    }

    # Team filtering and badges must stay constrained to visible teams, not
    # all teams ever associated with a globally shared candidate.
    visible_teams = (
        _team_visibility_queryset(request.user, company)
        .filter(is_archived=False)
        .order_by("name")
    )
    visible_team_ids = list(visible_teams.values_list("id", flat=True))
    candidates = (
        Candidate.objects
        .filter(id__in=candidate_ids)
        .prefetch_related(
            Prefetch(
                "team_memberships",
                queryset=(
                    TeamMembership.objects
                    .filter(team_id__in=visible_team_ids)
                    .select_related("team")
                ),
            )
        )
        .order_by("last_name", "first_name", "email")
    )

    teams = visible_teams
    selected_team_id = request.GET.get("team")

    if selected_team_id == "none":
        candidates = candidates.exclude(
            team_memberships__team_id__in=visible_team_ids
        )
    elif selected_team_id:
        try:
            selected_team_id_int = int(selected_team_id)
        except (TypeError, ValueError):
            selected_team_id_int = None

        if selected_team_id_int in visible_team_ids:
            candidates = candidates.filter(
                team_memberships__team_id=selected_team_id_int
            )
        else:
            candidates = candidates.none()

    candidate_by_id = {
        candidate.id: candidate
        for candidate in candidates.distinct()
    }

    process_meta_keys = {
        (invitation.process.account_code, invitation.process.project_code)
        for invitation in live_memberships
        if invitation.process.account_code and invitation.process.project_code
    }
    project_meta_by_key = {}
    if process_meta_keys:
        meta_query = Q()
        for account_code, project_code in process_meta_keys:
            meta_query |= Q(
                account_code=account_code,
                project_code=project_code,
            )
        project_meta_by_key = {
            (meta.account_code, meta.project_code): meta
            for meta in ProjectMeta.objects.filter(meta_query)
        }

    # One display row per accessible project membership, even when multiple
    # projects share the same global Candidate ID/email.
    candidate_entries = []
    for invitation in live_memberships:
        candidate = candidate_by_id.get(invitation.candidate_id)
        if candidate is None:
            continue
        candidate_entries.append(SimpleNamespace(
            candidate=candidate,
            project=invitation.process,
            test_overview=_live_membership_test_overview(
                invitation, project_meta_by_key,
            ),
            latest_activity=invitation.created_at,
        ))

    for membership in historical_memberships:
        candidate = candidate_by_id.get(membership.candidate_id)
        if candidate is None:
            continue
        candidate_entries.append(SimpleNamespace(
            candidate=candidate,
            project=membership.process,
            test_overview=_historical_membership_test_overview(membership),
            latest_activity=membership.created_at,
        ))

    candidate_entries.sort(key=lambda entry: (
        (entry.candidate.last_name or "").casefold(),
        (entry.candidate.first_name or "").casefold(),
        (entry.candidate.email or "").casefold(),
        -entry.latest_activity.timestamp(),
        entry.project.pk,
    ))

    return render(
        request,
        "customer/candidates/candidate_list.html",
        {
            "company": company,
            "candidates": candidate_entries,
            "unique_candidate_count": len(candidate_by_id),
            "teams": teams,
            "selected_team_id": selected_team_id,
        },
    )
