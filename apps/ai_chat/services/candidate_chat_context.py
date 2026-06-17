import json

from apps.processes.models import (
    HistoricalProcessCandidate,
    TestInvitation,
)
from apps.processes.services.candidate_profile import (
    build_historical_candidate_profile,
)


def build_live_candidate_profile(invitation):
    """
    Convert live SOVA activity data into a compact structure for AI chat.
    """
    activities = invitation.sova_activities or []

    return {
        "source": "live_sova_api",
        "candidate": {
            "id": invitation.candidate_id,
            "name": invitation.candidate.full_name,
            "email": invitation.candidate.email,
        },
        "assessment_activities": activities,
        "project_results": invitation.project_results or {},
        "overall_score": invitation.overall_score,
    }


def build_historical_chat_profile(historical_candidate):
    """
    Convert imported historical assessment data into the same kind
    of compact structure used by AI chat.
    """
    profile = build_historical_candidate_profile(
        historical_candidate
    )

    return {
        "source": "historical_import",
        "candidate": {
            "id": historical_candidate.candidate_id,
            "name": f"{historical_candidate.candidate.first_name} {historical_candidate.candidate.last_name}".strip(),
            "email": historical_candidate.candidate.email,
        },
        "motivation_competencies": profile[
            "motivation_competencies"
        ],
        "personality_competencies": profile[
            "personality_competencies"
        ],
        "team_style_scores": profile[
            "team_style_scores"
        ],
        "ability_results": profile["ability_results"],
        "has_motivation_results": profile[
            "has_motivation_results"
        ],
        "has_personality_results": profile[
            "has_personality_results"
        ],
        "has_ability_results": profile[
            "has_ability_results"
        ],
    }


def build_candidate_chat_context(
    *,
    process,
    candidate_id,
):
    """
    Return AI context for either a live or historical candidate.
    """
    if process.is_historical:
        historical_candidate = (
            HistoricalProcessCandidate.objects
            .select_related("candidate", "process")
            .prefetch_related(
                "assessment_results__scores",
                "assessment_results__import_file",
            )
            .get(
                process=process,
                candidate_id=candidate_id,
            )
        )

        profile = build_historical_chat_profile(
            historical_candidate
        )

        process_context = None
        mode = "general"

    else:
        invitation = (
            TestInvitation.objects
            .select_related("candidate", "process")
            .get(
                process=process,
                candidate_id=candidate_id,
            )
        )

        profile = build_live_candidate_profile(
            invitation
        )

        purpose_context = getattr(
            process,
            "role_context",
            None,
        )

        has_context = (
            purpose_context
            and purpose_context.has_content()
        )

        process_context = (
            {
                "purpose": process.purpose,
                "role_title": purpose_context.role_title,
                "job_advertisement": (
                    purpose_context.job_advertisement
                ),
                "requirements": (
                    purpose_context.requirements
                ),
                "priorities": purpose_context.priorities,
                "interview_focus": (
                    purpose_context.interview_focus
                ),
            }
            if has_context
            else None
        )

        mode = "context" if has_context else "general"

    return {
        "mode": mode,
        "process": {
            "id": process.id,
            "name": process.name,
            "purpose": process.purpose,
            "is_historical": process.is_historical,
        },
        "process_context": process_context,
        "candidate_profile": profile,
    }


def serialize_candidate_chat_context(context):
    return json.dumps(
        context,
        ensure_ascii=False,
        default=str,
        indent=2,
    )