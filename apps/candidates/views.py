from django.shortcuts import render

from apps.teams.models import Team

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import render

from apps.processes.models import (
    Candidate,
    TestInvitation,
    HistoricalProcessCandidate,
)
from apps.processes.services.access import get_accessible_processes_for_user

@login_required
def candidate_list(request):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    accessible_process_ids = list(
        accessible_processes.values_list("id", flat=True)
    )

    # Live candidates from normal test invitations
    live_candidate_ids = list(
        TestInvitation.objects
        .filter(process_id__in=accessible_process_ids)
        .values_list("candidate_id", flat=True)
    )

    # Historical candidates from historical imports
    historical_candidate_ids = list(
        HistoricalProcessCandidate.objects
        .filter(process_id__in=accessible_process_ids)
        .values_list("candidate_id", flat=True)
    )

    candidate_ids = set(live_candidate_ids) | set(historical_candidate_ids)

    candidates = (
        Candidate.objects
        .filter(id__in=candidate_ids)
        .prefetch_related("team_memberships__team")
        .order_by("last_name", "first_name", "email")
    )

    # Count live processes per candidate
    live_process_counts = {
        row["candidate_id"]: row["process_count"]
        for row in (
            TestInvitation.objects
            .filter(
                process_id__in=accessible_process_ids,
                candidate_id__in=candidate_ids,
            )
            .values("candidate_id")
            .annotate(process_count=Count("process_id", distinct=True))
        )
    }

    # Count historical processes per candidate
    historical_process_counts = {
        row["candidate_id"]: row["process_count"]
        for row in (
            HistoricalProcessCandidate.objects
            .filter(
                process_id__in=accessible_process_ids,
                candidate_id__in=candidate_ids,
            )
            .values("candidate_id")
            .annotate(process_count=Count("process_id", distinct=True))
        )
    }

    # Latest activity based on invitation created_at for now
    latest_live_activity = {
        row["candidate_id"]: row["latest_activity"]
        for row in (
            TestInvitation.objects
            .filter(
                process_id__in=accessible_process_ids,
                candidate_id__in=candidate_ids,
            )
            .values("candidate_id")
            .annotate(latest_activity=Max("created_at"))
        )
    }

    teams = (
        Team.objects
        .filter(company=company, is_archived=False)
        .order_by("name")
    )

    selected_team_id = request.GET.get("team")

    if selected_team_id == "none":
        candidates = candidates.filter(team_memberships__isnull=True)

    elif selected_team_id:
        candidates = candidates.filter(
            team_memberships__team_id=selected_team_id
        )

    # Attach display values directly to each candidate object
    for candidate in candidates:
        candidate.live_process_count = live_process_counts.get(candidate.id, 0)
        candidate.historical_process_count = historical_process_counts.get(candidate.id, 0)
        candidate.total_process_count = (
            candidate.live_process_count + candidate.historical_process_count
        )
        candidate.latest_live_activity = latest_live_activity.get(candidate.id)

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