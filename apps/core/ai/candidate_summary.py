from typing import Iterable
from django.utils import timezone

from .openai_client import get_openai_client, get_chat_model


def build_candidate_prompt(invitation) -> str:
    activities = invitation.sova_activities or []

    lines = []

    for act in activities:
        name = act.get("activity")
        comps = act.get("competencies") or []

        lines.append(f"\n{name}:")

        for c in comps:
            comp_name = c.get("competency")
            sten = c.get("sten_rounded")
            percentile = c.get("percentile")

            lines.append(f"- {comp_name}: sten {sten}, percentile {percentile}")

    test_data = "\n".join(lines)

    prompt = f"""
You are an expert in psychometric assessment and recruitment.

Your task is to write a concise, professional summary of a candidate based on their test results.

Focus on:
- Cognitive ability (logical, verbal, numerical)
- Personality traits
- Motivation profile

Instructions:
- Write 1 short paragraph (4–6 sentences)
- Highlight strengths and potential risks
- Keep tone neutral and professional
- Do NOT list raw numbers
- Interpret the data instead

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