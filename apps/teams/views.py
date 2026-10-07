from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.accounts.utils.org_access import get_effective_orgunit_permissions
from apps.core.utils.auth import is_admin
from apps.processes.models import (
    Candidate,
    HistoricalAssessmentScore,
    HistoricalProcessCandidate,
    TestInvitation,
)
from apps.processes.services.access import get_accessible_processes_for_user

from .forms import TeamForm
from .models import Team, TeamMembership


TEAM_STYLE_ORDER = [
    "Connector",
    "Catalyst",
    "Director",
    "Energiser",
    "Architect",
    "Harmoniser",
    "Analyst",
    "Auditor",
]

TEAM_STYLE_QUADRANTS = {
    "Connector": "Exploring",
    "Catalyst": "Exploring",
    "Director": "Directing",
    "Energiser": "Directing",
    "Architect": "Delivering",
    "Harmoniser": "Delivering",
    "Analyst": "Critiquing",
    "Auditor": "Critiquing",
}


def _permission_map(user, company):
    if not company:
        return {}
    return get_effective_orgunit_permissions(user, company)


def _team_visibility_queryset(user, company):
    """
    Teams follow the same org-unit scope as test processes:

    - viewer/editor: see shared teams in that org unit
    - own: see only teams created by the user in that org unit

    Existing teams created before this access model have org_unit=None. They
    remain visible to users with shared viewer/editor access, but are hidden
    from own-only users unless they have a creator recorded.
    """
    if not company:
        return Team.objects.none()

    if is_admin(user):
        return Team.objects.filter(company=company)

    perms = _permission_map(user, company)
    own_ids = [unit_id for unit_id, perm in perms.items() if perm == "own"]
    shared_ids = [
        unit_id
        for unit_id, perm in perms.items()
        if perm in ("viewer", "editor")
    ]

    scope = Q(pk__in=[])

    if shared_ids:
        scope |= Q(org_unit_id__in=shared_ids)
        # Safe compatibility for teams created before org-unit scoping existed.
        scope |= Q(org_unit__isnull=True)

    if own_ids:
        scope |= Q(org_unit_id__in=own_ids, created_by=user)
        scope |= Q(org_unit__isnull=True, created_by=user)

    return Team.objects.filter(company=company).filter(scope)


def _user_can_edit_team(user, company, team):
    if is_admin(user):
        return True

    if not company or team.company_id != company.id:
        return False

    perms = _permission_map(user, company)

    if team.org_unit_id:
        perm = perms.get(team.org_unit_id)
        if perm == "editor":
            return True
        if perm == "own":
            return team.created_by_id == user.id
        return False

    # Legacy team without org_unit. Editors may maintain it. Own users can
    # maintain it only when it is explicitly theirs.
    if team.created_by_id == user.id and "own" in perms.values():
        return True

    return "editor" in perms.values()


def _resolve_team_create_org_unit_id(request, company):
    if is_admin(request.user):
        active_id = request.session.get("active_org_unit_id")
        if active_id:
            return int(active_id)
        return (
            company.org_units
            .order_by("id")
            .values_list("id", flat=True)
            .first()
        )

    perms = _permission_map(request.user, company)
    editable_ids = {
        int(unit_id)
        for unit_id, perm in perms.items()
        if perm in ("editor", "own")
    }

    if not editable_ids:
        return None

    active_id = request.session.get("active_org_unit_id")
    if active_id:
        try:
            active_id = int(active_id)
        except (TypeError, ValueError):
            active_id = None

    if active_id in editable_ids:
        return active_id

    return sorted(editable_ids)[0]


def _accessible_candidate_ids(accessible_processes):
    process_ids = list(
        accessible_processes.values_list("id", flat=True)
    )

    if not process_ids:
        return set()

    live_ids = set(
        TestInvitation.objects
        .filter(process_id__in=process_ids)
        .values_list("candidate_id", flat=True)
    )

    historical_ids = set(
        HistoricalProcessCandidate.objects
        .filter(process_id__in=process_ids)
        .values_list("candidate_id", flat=True)
    )

    return live_ids | historical_ids


def get_initials(candidate):
    first = (candidate.first_name or "").strip()
    last = (candidate.last_name or "").strip()

    if first or last:
        return f"{first[:1]}{last[:1]}".upper()

    if candidate.email:
        return candidate.email[:2].upper()

    return "?"


def build_team_style_statistics(team, candidate_ids=None):
    memberships = (
        team.memberships
        .select_related("candidate")
        .order_by(
            "candidate__last_name",
            "candidate__first_name",
            "candidate__email",
        )
    )

    if candidate_ids is not None:
        memberships = memberships.filter(candidate_id__in=candidate_ids)

    candidates = [membership.candidate for membership in memberships]
    candidate_ids = [candidate.id for candidate in candidates]

    scores_qs = (
        HistoricalAssessmentScore.objects
        .filter(
            result__candidate_id__in=candidate_ids,
            result__assessment_type="personality",
            category="team_style",
            score__isnull=False,
        )
        .select_related("result", "result__candidate")
        .order_by(
            "result__candidate_id",
            "name",
            "-result__time_completed",
            "-result__created_at",
        )
    )

    # Use one score per candidate + team style. If a candidate has multiple
    # historical personality results, use the latest one.
    score_by_candidate_and_style = {}

    for score in scores_qs:
        key = (score.result.candidate_id, score.name)
        if key not in score_by_candidate_and_style:
            score_by_candidate_and_style[key] = score

    style_values = {style: [] for style in TEAM_STYLE_ORDER}
    member_profiles = []

    for candidate in candidates:
        member_scores = []

        for style in TEAM_STYLE_ORDER:
            score_obj = score_by_candidate_and_style.get(
                (candidate.id, style)
            )
            value = score_obj.score if score_obj else None

            if value is not None:
                style_values[style].append(
                    {
                        "candidate": candidate,
                        "value": float(value),
                    }
                )

            member_scores.append(
                {
                    "style": style,
                    "quadrant": TEAM_STYLE_QUADRANTS.get(style, ""),
                    "score": (
                        round(float(value), 1)
                        if value is not None
                        else None
                    ),
                    "score_rounded": (
                        round(float(value))
                        if value is not None
                        else None
                    ),
                    "percent": (
                        min(max((float(value) / 10) * 100, 0), 100)
                        if value is not None
                        else 0
                    ),
                }
            )

        has_scores = any(item["score"] is not None for item in member_scores)

        member_profiles.append(
            {
                "candidate": candidate,
                "initials": get_initials(candidate),
                "scores": member_scores,
                "has_scores": has_scores,
            }
        )

    average_rows = []
    maximum_rows = []
    most_least_rows = []

    for style in TEAM_STYLE_ORDER:
        values = style_values[style]
        numeric_values = [item["value"] for item in values]

        if numeric_values:
            avg_value = sum(numeric_values) / len(numeric_values)
            max_value = max(numeric_values)
            min_value = min(numeric_values)

            most_candidates = [
                {
                    "name": (
                        f"{item['candidate'].first_name} "
                        f"{item['candidate'].last_name}"
                    ).strip()
                    or item["candidate"].email,
                    "initials": get_initials(item["candidate"]),
                }
                for item in values
                if item["value"] == max_value
            ]

            least_candidates = [
                {
                    "name": (
                        f"{item['candidate'].first_name} "
                        f"{item['candidate'].last_name}"
                    ).strip()
                    or item["candidate"].email,
                    "initials": get_initials(item["candidate"]),
                }
                for item in values
                if item["value"] == min_value
            ]
        else:
            avg_value = None
            max_value = None
            min_value = None
            most_candidates = []
            least_candidates = []

        average_rows.append(
            {
                "style": style,
                "quadrant": TEAM_STYLE_QUADRANTS.get(style, ""),
                "average": (
                    round(avg_value, 1)
                    if avg_value is not None
                    else None
                ),
                "average_rounded": (
                    round(avg_value)
                    if avg_value is not None
                    else None
                ),
                "average_percent": (
                    min(max((avg_value / 10) * 100, 0), 100)
                    if avg_value is not None
                    else 0
                ),
                "count": len(numeric_values),
            }
        )

        maximum_rows.append(
            {
                "style": style,
                "quadrant": TEAM_STYLE_QUADRANTS.get(style, ""),
                "maximum": (
                    round(max_value, 1)
                    if max_value is not None
                    else None
                ),
                "maximum_rounded": (
                    round(max_value)
                    if max_value is not None
                    else None
                ),
                "maximum_percent": (
                    min(max((max_value / 10) * 100, 0), 100)
                    if max_value is not None
                    else 0
                ),
                "count": len(numeric_values),
            }
        )

        most_least_rows.append(
            {
                "style": style,
                "quadrant": TEAM_STYLE_QUADRANTS.get(style, ""),
                "most": most_candidates,
                "least": least_candidates,
                "max": (
                    round(max_value, 1)
                    if max_value is not None
                    else None
                ),
                "min": (
                    round(min_value, 1)
                    if min_value is not None
                    else None
                ),
            }
        )

    ranked_averages = sorted(
        average_rows,
        key=lambda item: (
            item["average"] if item["average"] is not None else -1
        ),
        reverse=True,
    )

    ranked_maximums = sorted(
        maximum_rows,
        key=lambda item: (
            item["maximum"] if item["maximum"] is not None else -1
        ),
        reverse=True,
    )

    members_with_scores = sum(
        1 for member in member_profiles if member["has_scores"]
    )

    strongest_average = (
        ranked_averages[0]
        if ranked_averages and ranked_averages[0]["average"] is not None
        else None
    )
    lowest_average = (
        ranked_averages[-1]
        if ranked_averages and ranked_averages[-1]["average"] is not None
        else None
    )

    return {
        "styles": TEAM_STYLE_ORDER,
        "average_rows": average_rows,
        "maximum_rows": maximum_rows,
        "ranked_averages": ranked_averages,
        "ranked_maximums": ranked_maximums,
        "most_least_rows": most_least_rows,
        "member_profiles": member_profiles,
        "members_total": len(candidates),
        "members_with_scores": members_with_scores,
        "strongest_average": strongest_average,
        "lowest_average": lowest_average,
        "chart_labels": TEAM_STYLE_ORDER,
        "chart_average_values": [
            row["average"] if row["average"] is not None else 0
            for row in average_rows
        ],
        "chart_max_values": [
            row["maximum"] if row["maximum"] is not None else 0
            for row in maximum_rows
        ],
    }


@login_required
def team_list(request):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    candidate_ids = _accessible_candidate_ids(accessible_processes)
    create_org_unit_id = (
        _resolve_team_create_org_unit_id(request, company)
        if company
        else None
    )

    teams = (
        _team_visibility_queryset(request.user, company)
        .filter(is_archived=False)
        .annotate(
            member_count=Count(
                "memberships",
                filter=Q(memberships__candidate_id__in=candidate_ids),
                distinct=True,
            )
        )
        .order_by("name")
    )

    return render(
        request,
        "customer/teams/team_list.html",
        {
            "company": company,
            "teams": teams,
            "can_create_team": bool(create_org_unit_id),
        },
    )


@login_required
def team_detail(request, pk):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    team = get_object_or_404(
        _team_visibility_queryset(request.user, company),
        pk=pk,
    )

    accessible_candidate_ids = _accessible_candidate_ids(
        accessible_processes
    )

    memberships = (
        team.memberships
        .filter(candidate_id__in=accessible_candidate_ids)
        .select_related("candidate")
        .prefetch_related("candidate__team_memberships__team")
        .order_by(
            "candidate__last_name",
            "candidate__first_name",
            "candidate__email",
        )
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

    team_style_stats = build_team_style_statistics(
        team,
        candidate_ids=accessible_candidate_ids,
    )

    return render(
        request,
        "customer/teams/team_detail.html",
        {
            "company": company,
            "team": team,
            "memberships": memberships,
            "stats": stats,
            "team_style_stats": team_style_stats,
            "can_edit_team": _user_can_edit_team(
                request.user,
                company,
                team,
            ),
        },
    )


@login_required
def team_create(request):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    if not company:
        messages.error(
            request,
            _("You are not linked to a company."),
        )
        return redirect("processes:process_list")

    org_unit_id = _resolve_team_create_org_unit_id(request, company)
    if not org_unit_id:
        return HttpResponseForbidden(
            _("You do not have permission to create teams.")
        )

    if request.method == "POST":
        form = TeamForm(request.POST)

        if form.is_valid():
            team = form.save(commit=False)
            team.company = company
            team.org_unit_id = org_unit_id
            team.created_by = request.user
            team.full_clean()
            team.save()

            messages.success(request, _("Team created."))
            if request.POST.get("wizard_next_step") == "3":
                return redirect("teams:team_detail", pk=team.pk)
            return redirect("teams:team_members_edit", pk=team.pk)
    else:
        form = TeamForm()

    return render(
        request,
        "customer/teams/team_form.html",
        {
            "form": form,
            "team": None,
            "page_title": _("Create team"),
            "submit_label": _("Create team"),
        },
    )


@login_required
def team_members_edit(request, pk):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    team = get_object_or_404(
        _team_visibility_queryset(request.user, company),
        pk=pk,
    )

    if not _user_can_edit_team(request.user, company, team):
        return HttpResponseForbidden(
            _("You do not have permission to edit this team.")
        )

    candidate_ids = _accessible_candidate_ids(accessible_processes)

    candidates = (
        Candidate.objects
        .filter(id__in=candidate_ids)
        .order_by("last_name", "first_name", "email")
    )

    accessible_process_ids = list(
        accessible_processes.values_list("id", flat=True)
    )
    result_candidate_ids = set(
        TestInvitation.objects.filter(
            process_id__in=accessible_process_ids,
            candidate_id__in=candidate_ids,
            status="completed",
        ).values_list("candidate_id", flat=True)
    )
    result_candidate_ids.update(
        HistoricalProcessCandidate.objects.filter(
            process_id__in=accessible_process_ids,
            candidate_id__in=candidate_ids,
            status="completed",
        ).values_list("candidate_id", flat=True)
    )

    if request.method == "POST":
        posted_ids = {
            int(candidate_id)
            for candidate_id in request.POST.getlist("candidate_ids")
            if str(candidate_id).isdigit()
        }
        selected_ids = posted_ids & candidate_ids

        # Only modify memberships the current user is allowed to manage.
        team.memberships.filter(
            candidate_id__in=candidate_ids
        ).exclude(
            candidate_id__in=selected_ids
        ).delete()

        for candidate_id in selected_ids:
            TeamMembership.objects.get_or_create(
                team=team,
                candidate_id=candidate_id,
                defaults={"source": "manual"},
            )

        messages.success(request, _("Team members updated."))
        if request.POST.get("wizard_next_step") == "1":
            return redirect("teams:team_edit", pk=team.pk)
        return redirect("teams:team_detail", pk=team.pk)

    selected_candidate_ids = set(
        team.memberships
        .filter(candidate_id__in=candidate_ids)
        .values_list("candidate_id", flat=True)
    )

    return render(
        request,
        "customer/teams/team_members_edit.html",
        {
            "company": company,
            "team": team,
            "candidates": candidates,
            "selected_candidate_ids": selected_candidate_ids,
            "result_candidate_ids": result_candidate_ids,
        },
    )


@login_required
def team_edit(request, pk):
    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )

    team = get_object_or_404(
        _team_visibility_queryset(request.user, company),
        pk=pk,
    )

    if not _user_can_edit_team(request.user, company, team):
        return HttpResponseForbidden(
            _("You do not have permission to edit this team.")
        )

    if request.method == "POST":
        form = TeamForm(request.POST, instance=team)

        if form.is_valid():
            updated_team = form.save(commit=False)
            updated_team.full_clean()
            updated_team.save()

            messages.success(request, _("Team updated."))
            if request.POST.get("wizard_next_step") == "3":
                return redirect("teams:team_detail", pk=team.pk)
            return redirect("teams:team_members_edit", pk=team.pk)
    else:
        form = TeamForm(instance=team)

    return render(
        request,
        "customer/teams/team_form.html",
        {
            "form": form,
            "team": team,
            "page_title": _("Edit team"),
            "submit_label": _("Save changes"),
        },
    )
