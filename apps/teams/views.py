from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Count

from apps.teams.models import Team
from apps.processes.services.access import get_accessible_processes_for_user

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect

from .forms import TeamForm

from apps.teams.models import Team, TeamMembership
from apps.processes.models import Candidate, TestInvitation, HistoricalProcessCandidate


@login_required
def team_list(request):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    teams = (
        Team.objects
        .filter(company=company, is_archived=False)
        .annotate(member_count=Count("memberships", distinct=True))
        .order_by("name")
    )

    return render(
        request,
        "customer/teams/team_list.html",
        {
            "company": company,
            "teams": teams,
        },
    )


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Count

from apps.teams.models import Team
from apps.processes.models import TestInvitation, HistoricalProcessCandidate
from apps.processes.services.access import get_accessible_processes_for_user


@login_required
def team_list(request):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    teams = (
        Team.objects
        .filter(company=company, is_archived=False)
        .annotate(member_count=Count("memberships", distinct=True))
        .order_by("name")
    )

    return render(
        request,
        "customer/teams/team_list.html",
        {
            "company": company,
            "teams": teams,
        },
    )


@login_required
def team_detail(request, pk):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    team = get_object_or_404(
        Team.objects.filter(company=company),
        pk=pk,
    )

    memberships = (
        team.memberships
        .select_related("candidate")
        .prefetch_related("candidate__team_memberships__team")
        .order_by("candidate__last_name", "candidate__first_name", "candidate__email")
    )

    candidate_ids = list(
        memberships.values_list("candidate_id", flat=True)
    )

    accessible_process_ids = list(
        accessible_processes.values_list("id", flat=True)
    )

    live_process_count = (
        TestInvitation.objects
        .filter(
            candidate_id__in=candidate_ids,
            process_id__in=accessible_process_ids,
        )
        .values("process_id")
        .distinct()
        .count()
    )

    completed_count = (
        TestInvitation.objects
        .filter(
            candidate_id__in=candidate_ids,
            process_id__in=accessible_process_ids,
            status="completed",
        )
        .count()
    )

    historical_count = (
        HistoricalProcessCandidate.objects
        .filter(
            candidate_id__in=candidate_ids,
            process_id__in=accessible_process_ids,
        )
        .count()
    )

    stats = {
        "members": len(candidate_ids),
        "processes": live_process_count,
        "completed": completed_count,
        "historical": historical_count,
    }

    return render(
        request,
        "customer/teams/team_detail.html",
        {
            "company": company,
            "team": team,
            "memberships": memberships,
            "stats": stats,
        },
    )

@login_required
def team_create(request):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    if not company:
        messages.error(request, "You are not linked to a company.")
        return redirect("processes:process_list")

    if request.method == "POST":
        form = TeamForm(request.POST)

        if form.is_valid():
            team = form.save(commit=False)
            team.company = company
            team.save()

            messages.success(request, "Team created.")
            return redirect("teams:team_detail", pk=team.pk)
    else:
        form = TeamForm()

    return render(
        request,
        "customer/teams/team_form.html",
        {
            "form": form,
            "team": None,
            "page_title": "Create team",
            "submit_label": "Create team",
        },
    )


@login_required
def team_members_edit(request, pk):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    team = get_object_or_404(
        Team.objects.filter(company=company),
        pk=pk,
    )

    accessible_process_ids = list(
        accessible_processes.values_list("id", flat=True)
    )

    live_candidate_ids = list(
        TestInvitation.objects
        .filter(process_id__in=accessible_process_ids)
        .values_list("candidate_id", flat=True)
    )

    historical_candidate_ids = list(
        HistoricalProcessCandidate.objects
        .filter(process_id__in=accessible_process_ids)
        .values_list("candidate_id", flat=True)
    )

    candidate_ids = set(live_candidate_ids) | set(historical_candidate_ids)

    candidates = (
        Candidate.objects
        .filter(id__in=candidate_ids)
        .order_by("last_name", "first_name", "email")
    )

    if request.method == "POST":
        selected_ids = request.POST.getlist("candidate_ids")

        # Remove candidates that were unchecked
        team.memberships.exclude(candidate_id__in=selected_ids).delete()

        # Add selected candidates
        for candidate_id in selected_ids:
            TeamMembership.objects.get_or_create(
                team=team,
                candidate_id=candidate_id,
                defaults={
                    "source": "manual",
                },
            )

        messages.success(request, "Team members updated.")
        return redirect("teams:team_detail", pk=team.pk)

    selected_candidate_ids = set(
        team.memberships.values_list("candidate_id", flat=True)
    )

    return render(
        request,
        "customer/teams/team_members_edit.html",
        {
            "company": company,
            "team": team,
            "candidates": candidates,
            "selected_candidate_ids": selected_candidate_ids,
        },
    )


@login_required
def team_edit(request, pk):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    team = get_object_or_404(
        Team.objects.filter(company=company),
        pk=pk,
    )

    if request.method == "POST":
        form = TeamForm(request.POST, instance=team)

        if form.is_valid():
            form.save()
            messages.success(request, "Team updated.")
            return redirect("teams:team_detail", pk=team.pk)
    else:
        form = TeamForm(instance=team)

    return render(
        request,
        "customer/teams/team_form.html",
        {
            "form": form,
            "team": team,
            "page_title": "Edit team",
            "submit_label": "Save changes",
        },
    )