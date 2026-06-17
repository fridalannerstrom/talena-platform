import json
import os

from openai import OpenAI

from apps.processes.services.candidate_profile import (
    build_historical_candidate_profile,
)


def build_historical_summary_input(
    process,
    historical_candidate,
):
    candidate = historical_candidate.candidate

    profile = build_historical_candidate_profile(
        historical_candidate
    )

    candidate_name = (
        f"{candidate.first_name or ''} "
        f"{candidate.last_name or ''}"
    ).strip()

    return {
        "mode": "general",
        "candidate": {
            "name": candidate_name,
        },
        "process": {
            "name": process.name,
            "historical": True,
        },
        "assessment_results": {
            "personality": profile.get(
                "personality_competencies",
                [],
            ),
            "team_styles": profile.get(
                "team_style_scores",
                [],
            ),
            "motivation": profile.get(
                "motivation_competencies",
                [],
            ),
            "abilities": profile.get(
                "ability_results",
                {},
            ),
        },
    }


def stream_historical_candidate_summary(
    *,
    process,
    historical_candidate,
):
    """
    Stream a general AI assessment summary for a historical candidate.

    No role or original process context is included.
    """
    summary_input = build_historical_summary_input(
        process=process,
        historical_candidate=historical_candidate,
    )

    system_prompt = """
You are Talena's professional assessment interpretation assistant.

Write a clear and useful general assessment summary based only on the
assessment evidence supplied.

There is no reliable original role, recruitment purpose or development
context available for this historical candidate.

Rules:
- Do not assess fit for a specific role.
- Do not invent scores, traits or evidence.
- Distinguish interpretation from fact.
- Use cautious language such as "may", "suggests" and "could indicate".
- Do not diagnose the candidate.
- Do not make a hiring decision.
- Do not mention Excel, database models, imports or internal system details.
- Write for a manager, recruiter or HR professional.
- Focus on the most meaningful overall patterns.
- Include both likely strengths and useful areas to explore.
- Mention cognitive ability results only when they are available.
- Keep the summary coherent and concise.
""".strip()

    user_prompt = f"""
Assessment evidence:

{json.dumps(
    summary_input,
    ensure_ascii=False,
    indent=2,
    default=str,
)}

Write a professional candidate assessment summary of approximately
150 to 250 words.

Use paragraphs rather than bullet points.
""".strip()

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY")
    )

    stream = client.responses.create(
        model=os.environ.get(
            "OPENAI_CHAT_MODEL",
            "gpt-5-mini",
        ),
        instructions=system_prompt,
        input=user_prompt,
        stream=True,
    )

    for event in stream:
        if event.type == "response.output_text.delta":
            yield event.delta