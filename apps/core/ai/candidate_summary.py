from typing import Iterable
from django.utils import timezone

from .openai_client import get_openai_client, get_chat_model


def build_candidate_prompt(invitation) -> str:
    activities = invitation.sova_activities or []
    candidate = invitation.candidate

    lines = []

    for act in activities:
        name = act.get("activity")
        comps = act.get("competencies") or []

        lines.append(f"\n{name}:")

        for c in comps:
            comp_name = c.get("competency")
            sten = c.get("sten_rounded")
            stive = c.get("stive_rounded")
            percentile = c.get("percentile")

            score_parts = []

            if sten is not None:
                score_parts.append(f"sten {sten}")

            if stive is not None:
                score_parts.append(f"stive {stive}")

            if percentile is not None:
                score_parts.append(f"percentile {percentile}")

            score_text = ", ".join(score_parts) if score_parts else "no score available"

            lines.append(f"- {comp_name}: {score_text}")

    test_data = "\n".join(lines)

    prompt = f"""
You are generating the first section of a candidate assessment report in Talena.

This section is called: Insight summary.

Important:
- This is GENERAL MODE.
- No role, job, team, leadership or development context has been added.
- Do not assess whether the candidate fits a specific role.
- Do not make hiring recommendations.
- Do not use a match score.
- Do not overstate certainty.
- Write in professional, clear English.
- Keep it concise and useful for a recruiter, hiring manager or HR professional.
- Interpret the assessment results. Do not list raw numbers in the final answer.
- Write about the candidate as a person, but avoid sounding absolute or deterministic.
- Use cautious language such as "may indicate", "suggests", "appears to", "could be useful to explore".

Use this structure exactly:

Overall summary
Write 1–2 short sentences summarising the candidate's general assessment profile.

Most important interpretation
- Write exactly 3 bullet points.
- Each bullet should highlight one important general insight from the assessment results.
- Include both strengths and possible areas to validate where relevant.

Confidence / context level
Write 1 short sentence explaining that confidence is limited because no process context has been added.

What this report is based on
Write 1 short sentence explaining which completed assessment data this summary is based on.

Do not include any markdown tables.
Do not include headings other than the four headings above.
Do not include the candidate's raw scores.

Candidate:
- Name: {candidate.first_name} {candidate.last_name}

Candidate test data:
{test_data}
""".strip()

    return prompt

def save_candidate_summary(invitation, full_text: str):
    invitation.ai_summary = full_text
    invitation.ai_summary_generated_at = timezone.now()
    invitation.ai_summary_status = "completed"
    invitation.save(update_fields=[
        "ai_summary",
        "ai_summary_generated_at",
        "ai_summary_status"
    ])

def stream_candidate_summary(invitation) -> Iterable[str]:
    client = get_openai_client()

    prompt = build_candidate_prompt(invitation)

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        stream=True,
    )

    for event in stream:
        delta = event.choices[0].delta
        if delta and delta.content:
            yield delta.content