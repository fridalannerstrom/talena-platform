from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _, get_language

from apps.processes.models import HistoricalProcessCandidate, TestInvitation
from apps.processes.services.access import get_accessible_processes_for_user
from apps.processes.services.candidate_profile import build_historical_candidate_profile
from apps.processes.services.team_styles import build_team_style_profile

from .views import (
    TEAM_STYLE_ORDER,
    TEAM_STYLE_QUADRANTS,
    _accessible_candidate_ids,
    _team_visibility_queryset,
    _user_can_edit_team,
    get_initials,
)


STYLE_KEY_BY_NAME = {
    "Connector": "connector",
    "Catalyst": "catalyst",
    "Director": "director",
    "Energiser": "energiser",
    "Architect": "architect",
    "Harmoniser": "harmoniser",
    "Analyst": "analyst",
    "Auditor": "auditor",
}


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _collect_live_competencies(invitation):
    """Collect Sova competency rows from every available live payload shape."""
    activities = []

    activities.extend(_as_list(invitation.sova_activities))

    payloads = [
        invitation.sova_payload,
        invitation.result_payload,
        invitation.project_results,
    ]

    for payload in payloads:
        if not isinstance(payload, dict):
            continue

        activities.extend(_as_list(payload.get("activities")))

        for phase in _as_list(payload.get("phases")):
            if isinstance(phase, dict):
                activities.extend(_as_list(phase.get("activities")))

        competencies = _as_list(payload.get("competencies"))
        if competencies:
            activities.append({"competencies": competencies})

    for phase in _as_list(invitation.sova_phases):
        if isinstance(phase, dict):
            activities.extend(_as_list(phase.get("activities")))

    competencies = []
    for activity in activities:
        if not isinstance(activity, dict):
            continue

        for competency in _as_list(activity.get("competencies")):
            if isinstance(competency, dict):
                competencies.append(competency)

    return competencies


def _values_from_profile(profile):
    values = {}
    chart_styles = {
        style.get("key"): style
        for style in profile.get("chart_styles") or []
        if style.get("key")
    }

    for name, key in STYLE_KEY_BY_NAME.items():
        style = chart_styles.get(key)
        if not style or not style.get("available"):
            continue

        value = style.get("raw_value")
        if value is None:
            value = style.get("display_value")

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        values[name] = max(1.0, min(5.0, value))

    return values


def _values_from_live_invitation(invitation):
    competencies = _collect_live_competencies(invitation)
    if not competencies:
        return {}

    return _values_from_profile(
        build_team_style_profile(competencies)
    )


def _values_from_historical_candidate(historical_candidate):
    profile = build_historical_candidate_profile(historical_candidate)
    team_style_scores = profile.get("team_style_scores") or []
    if not team_style_scores:
        return {}

    return _values_from_profile(
        build_team_style_profile(team_style_scores)
    )


def build_candidate_team_style_values(candidate_id, process_ids=None):
    """
    Return Team Style values for one candidate on Talena's five-point scale.

    Live Sova results are preferred. Historical imports are used as a fallback.
    When process_ids is supplied, no result outside the caller's accessible
    process scope can contribute to the team report.
    """
    live_qs = TestInvitation.objects.filter(candidate_id=candidate_id)
    historical_qs = HistoricalProcessCandidate.objects.filter(
        candidate_id=candidate_id
    )

    if process_ids is not None:
        process_ids = list(process_ids)
        if not process_ids:
            return {}
        live_qs = live_qs.filter(process_id__in=process_ids)
        historical_qs = historical_qs.filter(process_id__in=process_ids)

    live_qs = live_qs.order_by("-completed_at", "-created_at")

    for invitation in live_qs:
        values = _values_from_live_invitation(invitation)
        if values:
            return values

    historical_qs = historical_qs.order_by("-completed_at", "-created_at")

    for historical_candidate in historical_qs:
        values = _values_from_historical_candidate(historical_candidate)
        if values:
            return values

    return {}


def build_team_style_statistics(team, candidate_ids=None, process_ids=None):
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
    style_values = {style: [] for style in TEAM_STYLE_ORDER}
    member_profiles = []

    for candidate in candidates:
        candidate_values = build_candidate_team_style_values(
            candidate.id,
            process_ids=process_ids,
        )
        member_scores = []

        for style in TEAM_STYLE_ORDER:
            value = candidate_values.get(style)

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
                        min(max((float(value) / 5) * 100, 0), 100)
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
                    min(max((avg_value / 5) * 100, 0), 100)
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
                    min(max((max_value / 5) * 100, 0), 100)
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
        process_ids=accessible_process_ids,
    )

    from .ai_insights import build_team_insight_input, normalize_language
    from .models import TeamAIInsight

    language = normalize_language(get_language())
    _, current_signature, _, _, _ = build_team_insight_input(
        team,
        accessible_processes,
        language,
    )
    insight_rows = TeamAIInsight.objects.filter(
        team=team,
        language=language,
    )
    insights = {
        insight.insight_type: {
            "record": insight,
            "is_stale": insight.source_signature != current_signature,
        }
        for insight in insight_rows
    }
    insight_sections = [
        {
            "type": "communication_styles",
            "title_sv": "Kommunikationsstilar",
            "title_en": "Communication styles",
            "insight": insights.get("communication_styles"),
        },
        {
            "type": "collaboration",
            "title_sv": "Samarbete",
            "title_en": "Collaboration",
            "insight": insights.get("collaboration"),
        },
    ]

    return render(
        request,
        "customer/teams/team_detail.html",
        {
            "company": company,
            "team": team,
            "memberships": memberships,
            "stats": stats,
            "team_style_stats": team_style_stats,
            "team_insights": insights,
            "insight_sections": insight_sections,
            "insight_language": language,
            "can_edit_team": _user_can_edit_team(
                request.user,
                company,
                team,
            ),
        },
    )


@login_required
def generate_team_insight_view(request, pk, insight_type):
    if request.method != "POST":
        return redirect("teams:team_detail", pk=pk)

    accessible_processes, company = get_accessible_processes_for_user(
        request.user,
        include_archived=True,
    )
    team = get_object_or_404(
        _team_visibility_queryset(request.user, company),
        pk=pk,
    )
    if not _user_can_edit_team(request.user, company, team):
        return redirect("teams:team_detail", pk=team.pk)

    from .ai_insights import generate_team_insight

    try:
        generate_team_insight(
            team=team,
            insight_type=insight_type,
            accessible_processes=accessible_processes,
            user=request.user,
            language=get_language(),
        )
    except ValueError as exc:
        messages.warning(request, _(str(exc)))
    except Exception:
        messages.error(
            request,
            _("The team insight could not be generated. Please try again later."),
        )
    else:
        messages.success(request, _("Team insight updated."))

    return redirect("teams:team_detail", pk=team.pk)
