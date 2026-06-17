import json

from apps.processes.services.candidate_profile import (
    build_historical_candidate_profile,
)


def build_historical_summary_input(
    *,
    process,
    historical_candidate,
):
    profile = build_historical_candidate_profile(
        historical_candidate
    )

    candidate = historical_candidate.candidate

    return {
        "mode": "general",
        "candidate": {
            "name": (
                f"{candidate.first_name} {candidate.last_name}"
            ).strip(),
        },
        "process": {
            "name": process.name,
            "is_historical": True,
        },
        "assessment_results": {
            "personality": profile[
                "personality_competencies"
            ],
            "team_styles": profile[
                "team_style_scores"
            ],
            "motivation": profile[
                "motivation_competencies"
            ],
            "abilities": profile[
                "ability_results"
            ],
        },
    }


def serialize_summary_input(summary_input):
    return json.dumps(
        summary_input,
        ensure_ascii=False,
        indent=2,
        default=str,
    )