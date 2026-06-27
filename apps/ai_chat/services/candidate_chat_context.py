import json

from apps.processes.models import (
    HistoricalProcessCandidate,
    TestInvitation,
)
from apps.processes.services.candidate_profile import (
    build_historical_candidate_profile,
)

def build_chat_assessment_activities(activities):
    """
    Build a compact AI-friendly version of live SOVA activities.

    Personality competencies use STEN rounded as the primary score.
    Percentiles are kept only for cognitive ability assessments.
    """
    compact_activities = []

    for activity in activities or []:
        activity_name = (
            activity.get("activity")
            or activity.get("name")
            or "Assessment"
        )

        activity_name_lower = activity_name.lower()

        is_cognitive = any(
            keyword in activity_name_lower
            for keyword in (
                "verbal",
                "logical",
                "numerical",
                "ability",
                "cognitive",
            )
        )

        compact_competencies = []

        for competency in activity.get("competencies", []) or []:
            item = {
                "name": (
                    competency.get("competency")
                    or competency.get("name")
                    or ""
                ),
            }

            if is_cognitive:
                item["percentile"] = competency.get(
                    "percentile"
                )

            else:
                item["sten_rounded"] = competency.get(
                    "sten_rounded"
                )

            compact_competencies.append(item)

        compact_activities.append(
            {
                "assessment": activity_name,
                "status": activity.get("status"),
                "assessment_type": (
                    "cognitive"
                    if is_cognitive
                    else "personality_or_motivation"
                ),
                "competencies": compact_competencies,
            }
        )

    return compact_activities


def get_candidate_display_name(candidate):
    """
    Return a safe display name for a candidate.

    Falls back to email and finally "Candidate" when no name exists.
    """
    first_name = (candidate.first_name or "").strip()
    last_name = (candidate.last_name or "").strip()

    full_name = " ".join(
        part
        for part in (first_name, last_name)
        if part
    )

    return (
        full_name
        or candidate.email
        or "Candidate"
    )


def build_live_candidate_profile(invitation):
    """
    Convert live SOVA assessment data into a compact structure
    that can be included in the AI chat context.
    """
    candidate = invitation.candidate

    return {
        "source": "live_sova_api",
        "candidate": {
            "id": candidate.id,
            "name": get_candidate_display_name(candidate),
            "email": candidate.email or "",
        },
        "assessment_activities": (
            build_chat_assessment_activities(
                invitation.sova_activities or []
            )
        ),
        "interpretation_guide": {
            "personality_score": "STEN rounded",
            "personality_bands": {
                "1_3": "lower",
                "4_7": "typical or moderate",
                "8_10": "higher",
            },
            "cognitive_score": "percentile",
        },
        "project_results": (
            invitation.project_results or {}
        ),
        "overall_score": invitation.overall_score,
    }


def build_historical_chat_profile(historical_candidate):
    """
    Convert imported historical assessment data into a compact
    structure matching the live candidate chat context.
    """
    candidate = historical_candidate.candidate

    profile = build_historical_candidate_profile(
        historical_candidate
    )

    return {
        "source": "historical_import",
        "candidate": {
            "id": candidate.id,
            "name": get_candidate_display_name(candidate),
            "email": candidate.email or "",
        },
        "motivation_competencies": profile.get(
            "motivation_competencies",
            [],
        ),
        "personality_competencies": profile.get(
            "personality_competencies",
            [],
        ),
        "team_style_scores": profile.get(
            "team_style_scores",
            [],
        ),
        "ability_results": profile.get(
            "ability_results",
            {},
        ),
        "has_motivation_results": profile.get(
            "has_motivation_results",
            False,
        ),
        "has_personality_results": profile.get(
            "has_personality_results",
            False,
        ),
        "has_ability_results": profile.get(
            "has_ability_results",
            False,
        ),
    }


def build_process_context(process):
    """
    Build the process context used by the AI assistant.

    Uses the ProcessRoleContext helper methods so the chat stays
    aligned with the fields defined on that model.
    """
    purpose_context = getattr(
        process,
        "role_context",
        None,
    )

    if (
        not purpose_context
        or not purpose_context.has_content()
    ):
        return None

    return {
        "purpose": process.purpose or "",
        **purpose_context.get_current_context_data(),
    }


def build_candidate_chat_context(
    *,
    process,
    candidate_id,
):
    """
    Return AI chat context for either a live or historical candidate.
    """
    if process.is_historical:
        historical_candidate = (
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
            )
            .prefetch_related(
                "assessment_results__scores",
                "assessment_results__import_file",
            )
            .get(
                process=process,
                candidate_id=candidate_id,
            )
        )

        candidate_profile = build_historical_chat_profile(
            historical_candidate
        )

        process_context = None
        mode = "general"

    else:
        invitation = (
            TestInvitation.objects
            .select_related(
                "candidate",
                "process",
            )
            .get(
                process=process,
                candidate_id=candidate_id,
            )
        )

        candidate_profile = build_live_candidate_profile(
            invitation
        )

        process_context = build_process_context(
            process
        )

        mode = (
            "context"
            if process_context
            else "general"
        )

    return {
        "mode": mode,
        "process": {
            "id": process.id,
            "name": process.name or "",
            "purpose": process.purpose or "",
            "is_historical": process.is_historical,
        },
        "process_context": process_context,
        "candidate_profile": candidate_profile,
    }


def serialize_candidate_chat_context(context):
    """
    Serialize the candidate context into readable JSON
    for the OpenAI prompt.
    """
    return json.dumps(
        context,
        ensure_ascii=False,
        default=str,
        indent=2,
    )