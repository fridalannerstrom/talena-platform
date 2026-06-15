from django.shortcuts import render

from apps.teams.models import Team
from apps.projects.models import ProjectMeta

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from apps.processes.models import (
    Candidate,
    TestInvitation,
    HistoricalProcessCandidate,
)
from apps.processes.services.access import get_accessible_processes_for_user

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

@login_required
def candidate_list(request):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    accessible_process_ids = list(
        accessible_processes.values_list("id", flat=True)
    )

    # ---------------------------------------------------------
    # Candidate memberships in live processes
    # ---------------------------------------------------------
    live_memberships = list(
        TestInvitation.objects
        .filter(process_id__in=accessible_process_ids)
        .select_related("process")
    )

    # ---------------------------------------------------------
    # Candidate memberships in historical processes
    # ---------------------------------------------------------
    historical_memberships = list(
        HistoricalProcessCandidate.objects
        .filter(process_id__in=accessible_process_ids)
        .select_related("process", "candidate")
        .prefetch_related("assessment_results__scores")
    )

    live_candidate_ids = {
        invitation.candidate_id
        for invitation in live_memberships
    }

    historical_candidate_ids = {
        membership.candidate_id
        for membership in historical_memberships
    }

    candidate_ids = live_candidate_ids | historical_candidate_ids

    candidates = (
        Candidate.objects
        .filter(id__in=candidate_ids)
        .prefetch_related("team_memberships__team")
        .order_by("last_name", "first_name", "email")
    )

    # ---------------------------------------------------------
    # Count processes per candidate
    # ---------------------------------------------------------
    live_process_counts = {
        row["candidate_id"]: row["process_count"]
        for row in (
            TestInvitation.objects
            .filter(
                process_id__in=accessible_process_ids,
                candidate_id__in=candidate_ids,
            )
            .values("candidate_id")
            .annotate(
                process_count=Count(
                    "process_id",
                    distinct=True,
                )
            )
        )
    }

    historical_process_counts = {
        row["candidate_id"]: row["process_count"]
        for row in (
            HistoricalProcessCandidate.objects
            .filter(
                process_id__in=accessible_process_ids,
                candidate_id__in=candidate_ids,
            )
            .values("candidate_id")
            .annotate(
                process_count=Count(
                    "process_id",
                    distinct=True,
                )
            )
        )
    }

    # ---------------------------------------------------------
    # Load ProjectMeta for the accessible live processes
    # ---------------------------------------------------------
    process_meta_keys = {
        (
            invitation.process.account_code,
            invitation.process.project_code,
        )
        for invitation in live_memberships
        if (
            invitation.process.account_code
            and invitation.process.project_code
        )
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

    # ---------------------------------------------------------
    # Create empty test overview for every candidate
    # ---------------------------------------------------------
    test_statuses_by_candidate = {
        candidate_id: {
            definition["key"]: {
                **definition,
                "status": "not_sent",
                "completed_count": 0,
                "pending_count": 0,
            }
            for definition in TEST_DEFINITIONS
        }
        for candidate_id in candidate_ids
    }

    # ---------------------------------------------------------
    # Build test overview from live processes
    # ---------------------------------------------------------
    for invitation in live_memberships:
        candidate_statuses = test_statuses_by_candidate.get(
            invitation.candidate_id
        )

        if not candidate_statuses:
            continue

        process_test_keys = get_process_test_keys(
            invitation.process,
            project_meta_by_key,
        )

        invitation_status = str(
            invitation.status or ""
        ).strip().lower()

        if invitation_status == "completed":
            process_base_status = "completed"

        elif invitation_status in {
            "sent",
            "started",
            "expired",
        }:
            process_base_status = "pending"

        else:
            process_base_status = "not_sent"

        # Use the general invitation status for tests included in the process.
        for test_key in process_test_keys:
            update_test_status(
                candidate_statuses,
                test_key,
                process_base_status,
            )

            if process_base_status == "completed":
                candidate_statuses[test_key]["completed_count"] += 1

            elif process_base_status == "pending":
                candidate_statuses[test_key]["pending_count"] += 1

        # Sova activity data is more precise than the invitation status.
        activity_test_keys = set()

        for activity in invitation.sova_activities or []:
            test_key = normalize_test_key(
                activity.get("activity")
            )

            if not test_key:
                continue

            activity_status = normalize_activity_status(
                activity.get("status")
            )

            activity_test_keys.add(test_key)

            update_test_status(
                candidate_statuses,
                test_key,
                activity_status,
            )

            if activity_status == "completed":
                candidate_statuses[test_key]["completed_count"] += 1

            elif activity_status == "pending":
                candidate_statuses[test_key]["pending_count"] += 1

    # ---------------------------------------------------------
    # Build test overview from historical assessment results
    # ---------------------------------------------------------
    for membership in historical_memberships:
        candidate_statuses = test_statuses_by_candidate.get(
            membership.candidate_id
        )

        if not candidate_statuses:
            continue

        completed_test_keys = set()

        for assessment_result in membership.assessment_results.all():
            test_key = normalize_test_key(
                assessment_result.assessment_type
            )

            if test_key:
                completed_test_keys.add(test_key)

        for test_key in completed_test_keys:
            update_test_status(
                candidate_statuses,
                test_key,
                "completed",
            )

            candidate_statuses[test_key]["completed_count"] += 1

    # ---------------------------------------------------------
    # Find each candidate's most recent process membership
    # ---------------------------------------------------------
    latest_membership_by_candidate = {}

    for invitation in live_memberships:
        current_latest = latest_membership_by_candidate.get(
            invitation.candidate_id
        )

        if (
            current_latest is None
            or invitation.created_at > current_latest["created_at"]
        ):
            latest_membership_by_candidate[invitation.candidate_id] = {
                "process_id": invitation.process_id,
                "created_at": invitation.created_at,
            }

    for membership in historical_memberships:
        current_latest = latest_membership_by_candidate.get(
            membership.candidate_id
        )

        if (
            current_latest is None
            or membership.created_at > current_latest["created_at"]
        ):
            latest_membership_by_candidate[membership.candidate_id] = {
                "process_id": membership.process_id,
                "created_at": membership.created_at,
            }

    # ---------------------------------------------------------
    # Team filtering
    # ---------------------------------------------------------
    teams = (
        Team.objects
        .filter(
            company=company,
            is_archived=False,
        )
        .order_by("name")
    )

    selected_team_id = request.GET.get("team")

    if selected_team_id == "none":
        candidates = candidates.filter(
            team_memberships__isnull=True
        )

    elif selected_team_id:
        candidates = candidates.filter(
            team_memberships__team_id=selected_team_id
        )

    candidates = candidates.distinct()

    # ---------------------------------------------------------
    # Attach display/navigation values to candidates
    # ---------------------------------------------------------
    for candidate in candidates:
        candidate.live_process_count = (
            live_process_counts.get(candidate.id, 0)
        )

        candidate.historical_process_count = (
            historical_process_counts.get(candidate.id, 0)
        )

        candidate.total_process_count = (
            candidate.live_process_count
            + candidate.historical_process_count
        )

        latest_membership = latest_membership_by_candidate.get(
            candidate.id
        )

        candidate.latest_process_id = (
            latest_membership["process_id"]
            if latest_membership
            else None
        )

        candidate.latest_activity = (
            latest_membership["created_at"]
            if latest_membership
            else None
        )

        candidate.test_overview = [
            test_statuses_by_candidate[candidate.id][definition["key"]]
            for definition in TEST_DEFINITIONS
        ]

    return render(
        request,
        "customer/candidates/candidate_list.html",
        {
            "company": company,
            "candidates": candidates,
            "teams": teams,
            "selected_team_id": selected_team_id,
        },
    )