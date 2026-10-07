import hashlib
import json

from apps.core.ai.openai_client import get_chat_model, get_openai_client
from apps.core.ai.prompt_templates import get_ai_prompt_instructions
from apps.processes.models import HistoricalProcessCandidate, TestInvitation

from .models import TeamAIInsight
from .team_report_views import build_team_style_statistics
from .views import _accessible_candidate_ids


INSIGHT_PROMPTS = {
    "communication_styles": "team_communication_styles",
    "collaboration": "team_collaboration",
}


def normalize_language(language):
    return "sv" if str(language or "").lower().startswith("sv") else "en"


GOAL_LABELS = {
    "understand_collaboration": {
        "sv": "Förstå hur vi samarbetar",
        "en": "Understand how we collaborate",
    },
    "develop_communication": {
        "sv": "Utveckla vår kommunikation",
        "en": "Develop our communication",
    },
    "discover_strengths": {
        "sv": "Upptäcka styrkor och utvecklingsområden",
        "en": "Discover strengths and development areas",
    },
    "support_team_development": {
        "sv": "Stödja teamets utveckling",
        "en": "Support the team’s development",
    },
}


def build_team_insight_input(team, accessible_processes, language="en"):
    language = normalize_language(language)
    process_ids = list(accessible_processes.values_list("id", flat=True))
    accessible_ids = _accessible_candidate_ids(accessible_processes)
    memberships = list(
        team.memberships.filter(candidate_id__in=accessible_ids)
        .order_by("candidate_id")
        .values_list("candidate_id", flat=True)
    )
    member_ids = set(memberships)

    stats = build_team_style_statistics(
        team,
        candidate_ids=member_ids,
        process_ids=process_ids,
    )
    available_styles = [
        {
            "style": row["style"],
            "team_average": row["average"],
            "members_with_score": row["count"],
        }
        for row in stats["average_rows"]
        if row["average"] is not None
    ]

    prompt_context = {
        "team_goals": [
            GOAL_LABELS.get(goal, {}).get(language, goal)
            for goal in (team.goals or [])
        ],
        "team_description": team.description or "",
        "team_context": team.context or "",
        "team_member_count": len(member_ids),
        "members_with_usable_assessment_results": stats["members_with_scores"],
        "members_missing_usable_assessment_results": max(
            0, len(member_ids) - stats["members_with_scores"]
        ),
        "team_style_summary": available_styles,
    }

    live_versions = list(
        TestInvitation.objects.filter(
            candidate_id__in=member_ids,
            process_id__in=process_ids,
            status="completed",
        ).order_by("candidate_id", "id")
        .values_list("candidate_id", "id", "created_at", "completed_at")
    )
    historical_versions = list(
        HistoricalProcessCandidate.objects.filter(
            candidate_id__in=member_ids,
            process_id__in=process_ids,
        ).order_by("candidate_id", "id")
        .values_list("candidate_id", "id", "created_at", "completed_at", "status")
    )
    signature_data = {
        "prompt_context": prompt_context,
        "member_ids": memberships,
        "live_result_versions": [
            [candidate_id, row_id, created.isoformat(), completed.isoformat() if completed else None]
            for candidate_id, row_id, created, completed in live_versions
        ],
        "historical_result_versions": [
            [candidate_id, row_id, created.isoformat(), completed.isoformat() if completed else None, status]
            for candidate_id, row_id, created, completed, status in historical_versions
        ],
        "anonymous_result_vectors": sorted(
            [
                [score["style"], score["score"]]
                for score in profile["scores"]
                if score["score"] is not None
            ]
            for profile in stats["member_profiles"]
        ),
    }
    signature = hashlib.sha256(
        json.dumps(signature_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    source_metadata = {
        "accessible_process_count": len(process_ids),
        "team_member_count": len(member_ids),
        "members_with_usable_team_style_results": stats["members_with_scores"],
        "completed_live_result_members": TestInvitation.objects.filter(
            candidate_id__in=member_ids,
            process_id__in=process_ids,
            status="completed",
        ).values("candidate_id").distinct().count(),
        "completed_historical_result_members": HistoricalProcessCandidate.objects.filter(
            candidate_id__in=member_ids,
            process_id__in=process_ids,
            status="completed",
        ).values("candidate_id").distinct().count(),
        "sources": ["live_sova", "historical_import"],
    }
    return (
        prompt_context,
        signature,
        len(member_ids),
        stats["members_with_scores"],
        source_metadata,
    )


def generate_team_insight(*, team, insight_type, accessible_processes, user, language):
    prompt_key = INSIGHT_PROMPTS.get(insight_type)
    if not prompt_key:
        raise ValueError("Unknown team insight type")

    language = normalize_language(language)
    (
        prompt_context,
        signature,
        member_count,
        result_count,
        source_metadata,
    ) = build_team_insight_input(team, accessible_processes, language)
    if member_count == 0 or result_count == 0:
        raise ValueError("No team assessment data is available yet.")

    feature_instructions = get_ai_prompt_instructions(
        key=prompt_key,
        language=language,
    )
    # The fixed contract is protected application guidance. Admin prompts only
    # set the tone, focus and length for their own independent insight.
    technical_contract = (
        f"Write one team-level insight only in {language}. Use only the "
        "supplied team context and aggregated results. Do not make claims about "
        "individual members, team quality, performance, diagnosis, or causes. "
        "Do not infer anything from missing results. Clearly mention when the "
        "available evidence is limited. Treat patterns as possibilities to "
        "explore, not conclusions. Return plain text only.\n\n"
    )
    client = get_openai_client()
    response = client.chat.completions.create(
        model=get_chat_model(),
        temperature=0.3,
        max_tokens=900,
        messages=[
            {
                "role": "system",
                "content": technical_contract + feature_instructions,
            },
            {
                "role": "user",
                "content": (
                    f"Language: {language}\n"
                    "Team context (JSON):\n"
                    + json.dumps(prompt_context, ensure_ascii=False, indent=2)
                ),
            },
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise ValueError("The AI returned an empty team insight.")

    from apps.processes.models import AIPromptTemplate

    active_prompt = AIPromptTemplate.objects.filter(
        key=prompt_key,
        language=language,
        is_active=True,
    ).first()
    prompt_revision = "protected-default"
    if active_prompt:
        latest_version = active_prompt.versions.order_by("-saved_at", "-id").first()
        prompt_revision = str(latest_version.pk) if latest_version else f"override-{active_prompt.updated_at.isoformat()}"
    prompt_digest = hashlib.sha256(
        (technical_contract + feature_instructions).encode("utf-8")
    ).hexdigest()

    insight, _ = TeamAIInsight.objects.update_or_create(
        team=team,
        insight_type=insight_type,
        language=language,
        defaults={
            "content": content,
            "source_signature": signature,
            "source_metadata": source_metadata,
            "prompt_key": prompt_key,
            "prompt_revision": prompt_revision,
            "prompt_digest": prompt_digest,
            "generated_by": user,
        },
    )
    return insight
