from __future__ import annotations

import json
from typing import Any, Iterable

from django.forms.models import model_to_dict
from django.utils import timezone

from .openai_client import get_openai_client, get_chat_model


PURPOSE_FIT_TITLES = {
    # Recruitment
    "hiring": "Role fit",
    "recruitment": "Role fit",

    # Role matching
    "role_match": "Role alignment",
    "internal_role_match": "Role alignment",

    # Leadership
    "leadership_potential": "Leadership potential fit",
    "leader_development": "Leadership development focus",

    # Development
    "employee_development": "Development fit",
    "career_path": "Development fit",

    # Onboarding
    "onboarding": "Onboarding fit",

    # Team
    "team_development": "Team contribution",

    # Change
    "reorganisation": "Change and transition fit",
    "reorganization": "Change and transition fit",
}


PURPOSE_LABELS = {
    "hiring": "Recruitment",
    "recruitment": "Recruitment",
    "role_match": "Role matching",
    "internal_role_match": "Role matching",
    "leadership_potential": "Leadership potential",
    "leader_development": "Leadership development",
    "employee_development": "Employee development",
    "career_path": "Career development",
    "onboarding": "Onboarding",
    "team_development": "Team development",
    "reorganisation": "Reorganisation",
    "reorganization": "Reorganisation",
}


ALLOWED_RECOMMENDATIONS = {
    "Strong alignment",
    "Potential alignment",
    "Mixed alignment",
    "Limited alignment",
    "Insufficient context",
}


ALLOWED_CONFIDENCE_LEVELS = {
    "Low",
    "Medium",
    "High",
}


def get_purpose_key(process) -> str:
    return (process.purpose or "").strip().lower()


def get_purpose_fit_title(process) -> str:
    purpose_key = get_purpose_key(process)

    return PURPOSE_FIT_TITLES.get(
        purpose_key,
        "Purpose fit",
    )


def purpose_supports_fit(process) -> bool:
    """
    Flexible/general processes should not receive a purpose-fit verdict.
    """

    purpose_key = get_purpose_key(process)

    return purpose_key not in {
        "",
        "flexible",
        "unsure",
        "general",
    }


def _has_score(competency: dict[str, Any]) -> bool:
    return any(
        competency.get(field_name) is not None
        for field_name in (
            "score",
            "sten",
            "sten_rounded",
            "stive",
            "stive_rounded",
            "percentile",
        )
    )


def build_assessment_evidence(invitation) -> tuple[str, int]:
    """
    Build compact assessment evidence for the AI prompt.

    Returns:
        tuple:
        - formatted assessment evidence
        - number of assessment types containing real results
    """

    activities = invitation.sova_activities or []
    assessment_sections = []
    completed_result_types = 0

    for activity in activities:
        activity_name = (
            activity.get("activity")
            or "Assessment"
        )

        competencies = activity.get("competencies") or []

        scored_competencies = [
            competency
            for competency in competencies
            if _has_score(competency)
        ]

        if not scored_competencies:
            continue

        completed_result_types += 1
        result_lines = []

        for competency in scored_competencies:
            competency_name = (
                competency.get("competency")
                or competency.get("name")
                or "Unnamed competency"
            )

            score_parts = []

            sten = competency.get("sten_rounded")
            if sten is None:
                sten = competency.get("sten")

            stive = competency.get("stive_rounded")
            if stive is None:
                stive = competency.get("stive")

            percentile = competency.get("percentile")

            if sten is not None:
                score_parts.append(f"sten {sten}")

            if stive is not None:
                score_parts.append(f"stive {stive}")

            if percentile is not None:
                score_parts.append(
                    f"percentile {percentile}"
                )

            if score_parts:
                result_lines.append(
                    f"- {competency_name}: "
                    f"{', '.join(score_parts)}"
                )

        if result_lines:
            assessment_sections.append(
                f"{activity_name}:\n"
                + "\n".join(result_lines)
            )

    if not assessment_sections:
        return (
            "No completed assessment results were available.",
            0,
        )

    return (
        "\n\n".join(assessment_sections),
        completed_result_types,
    )


def build_process_context(process) -> tuple[str, dict[str, Any]]:
    """
    Convert the active process context into prompt-friendly text.
    """

    role_context = getattr(
        process,
        "role_context",
        None,
    )

    if not role_context or not role_context.has_content():
        return (
            "No additional process context has been added.",
            {},
        )

    raw_context = model_to_dict(role_context)

    excluded_fields = {
        "id",
        "process",
        "created_at",
        "updated_at",
        "purpose_data",
    }

    context_data = {}
    context_lines = []

    for field_name, value in raw_context.items():
        if field_name in excluded_fields:
            continue

        if value in (None, "", [], {}):
            continue

        readable_name = (
            field_name
            .replace("_", " ")
            .strip()
            .title()
        )

        context_data[field_name] = value
        context_lines.append(
            f"- {readable_name}: {value}"
        )

    if not context_lines:
        return (
            "No additional process context has been added.",
            {},
        )

    return (
        "\n".join(context_lines),
        context_data,
    )


def calculate_max_confidence(
    *,
    context_data: dict[str, Any],
    assessment_type_count: int,
) -> str:
    """
    Set the maximum confidence the AI is allowed to use.

    Confidence reflects the amount of relevant evidence, not how
    strongly the candidate appears aligned.
    """

    context_field_count = len(context_data)

    if context_field_count == 0:
        return "Low"

    if (
        context_field_count >= 4
        and assessment_type_count >= 2
    ):
        return "High"

    return "Medium"


def build_purpose_fit_prompt(invitation) -> str:
    candidate = invitation.candidate
    process = invitation.process

    purpose_key = get_purpose_key(process)

    purpose_label = PURPOSE_LABELS.get(
        purpose_key,
        process.get_purpose_display()
        if hasattr(process, "get_purpose_display")
        else purpose_key,
    )

    fit_title = get_purpose_fit_title(process)

    assessment_text, assessment_type_count = (
        build_assessment_evidence(invitation)
    )

    context_text, context_data = build_process_context(
        process
    )

    max_confidence = calculate_max_confidence(
        context_data=context_data,
        assessment_type_count=assessment_type_count,
    )

    return f"""
You are generating a purpose-fit interpretation for Talena,
an assessment and talent management platform.

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

PROCESS PURPOSE
Purpose: {purpose_label}
Section title: {fit_title}

PROCESS CONTEXT
{context_text}

ASSESSMENT EVIDENCE
{assessment_text}

MAXIMUM ALLOWED CONFIDENCE
{max_confidence}

YOUR TASK
Interpret how the candidate's assessment profile may align with
the selected process purpose and the supplied context.

This is assessment-based decision support. It is not a final
selection, hiring, promotion or development decision.

RECOMMENDATION LEVELS
Use exactly one of these:
- Strong alignment
- Potential alignment
- Mixed alignment
- Limited alignment
- Insufficient context

CONFIDENCE LEVELS
Use exactly one of these:
- Low
- Medium
- High

Never use a confidence level above:
{max_confidence}

IMPORTANT RULES
- Do not create a percentage or numerical match score.
- Do not write "recommended" or "not recommended".
- Do not make a final hiring decision.
- Do not diagnose the candidate.
- Do not invent role requirements or context.
- Do not treat lower scores as automatic weaknesses.
- Separate assessment evidence from assumptions.
- Use cautious language such as "may indicate", "suggests",
  "appears to" and "could be useful to verify".
- Keep each item concise and practical.
- Do not include raw assessment scores in the output.
- Write in professional, clear English.

STREAMING OUTPUT FORMAT
Return newline-delimited JSON, also called NDJSON.

Every JSON object must be written on one single line.
Do not use markdown.
Do not use code fences.
Do not add any text outside the JSON objects.

Return events in this exact order:

1. One meta event:
{{"type":"meta","title":"{fit_title}","recommendation":"Potential alignment","confidence":"Medium"}}

2. Between 3 and 6 summary_delta events:
{{"type":"summary_delta","text":"First part of the summary. "}}
{{"type":"summary_delta","text":"Next part of the summary. "}}

Together, the summary should be approximately 80 to 130 words.

3. One key_alignment event containing exactly 3 items:
{{"type":"key_alignment","items":["Alignment one","Alignment two","Alignment three"]}}

4. One areas_to_verify event containing exactly 3 items:
{{"type":"areas_to_verify","items":["Area one","Area two","Area three"]}}

5. One suggested_next_step event:
{{"type":"suggested_next_step","text":"A practical next step."}}

6. One context_note event:
{{"type":"context_note","text":"Briefly explain what evidence and context the interpretation is based on."}}

7. One final done event:
{{"type":"done"}}
""".strip()


def create_empty_purpose_fit(invitation) -> dict[str, Any]:
    return {
        "title": get_purpose_fit_title(
            invitation.process
        ),
        "recommendation": "",
        "confidence": "",
        "summary": "",
        "key_alignment": [],
        "areas_to_verify": [],
        "suggested_next_step": "",
        "context_note": "",
    }


def apply_purpose_fit_event(
    purpose_fit: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one streamed event to the complete JSON result.
    """

    event_type = event.get("type")

    if event_type == "meta":
        recommendation = event.get(
            "recommendation",
            "",
        )

        confidence = event.get(
            "confidence",
            "",
        )

        if recommendation not in ALLOWED_RECOMMENDATIONS:
            recommendation = "Insufficient context"

        if confidence not in ALLOWED_CONFIDENCE_LEVELS:
            confidence = "Low"

        purpose_fit["title"] = (
            event.get("title")
            or purpose_fit["title"]
        )

        purpose_fit["recommendation"] = recommendation
        purpose_fit["confidence"] = confidence

    elif event_type == "summary_delta":
        purpose_fit["summary"] += str(
            event.get("text") or ""
        )

    elif event_type == "key_alignment":
        items = event.get("items")

        if isinstance(items, list):
            purpose_fit["key_alignment"] = [
                str(item).strip()
                for item in items[:3]
                if str(item).strip()
            ]

    elif event_type == "areas_to_verify":
        items = event.get("items")

        if isinstance(items, list):
            purpose_fit["areas_to_verify"] = [
                str(item).strip()
                for item in items[:3]
                if str(item).strip()
            ]

    elif event_type == "suggested_next_step":
        purpose_fit["suggested_next_step"] = str(
            event.get("text") or ""
        ).strip()

    elif event_type == "context_note":
        purpose_fit["context_note"] = str(
            event.get("text") or ""
        ).strip()

    return purpose_fit


def _parse_event_line(
    raw_line: str,
) -> dict[str, Any] | None:
    line = raw_line.strip()

    if not line:
        return None

    # Safety in case the model adds Markdown fences.
    if line in {"```", "```json", "```ndjson"}:
        return None

    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None

    if not isinstance(event, dict):
        return None

    if not event.get("type"):
        return None

    return event


def stream_candidate_purpose_fit(
    invitation,
) -> Iterable[dict[str, Any]]:
    """
    Stream purpose-fit events from OpenAI.

    Each yielded value is a parsed event dictionary.
    The view will later convert these dictionaries to NDJSON
    and send them to the browser.
    """

    if not purpose_supports_fit(invitation.process):
        raise ValueError(
            "Flexible processes do not support purpose-fit analysis."
        )

    client = get_openai_client()

    prompt = build_purpose_fit_prompt(invitation)

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful assessment interpretation "
                    "assistant. Follow the requested NDJSON streaming "
                    "format exactly."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
        stream=True,
    )

    buffer = ""

    for response_event in stream:
        delta = response_event.choices[0].delta

        if not delta or not delta.content:
            continue

        buffer += delta.content

        while "\n" in buffer:
            raw_line, buffer = buffer.split(
                "\n",
                1,
            )

            parsed_event = _parse_event_line(
                raw_line
            )

            if parsed_event:
                yield parsed_event

    # Parse the final line if the model did not end with newline.
    final_event = _parse_event_line(buffer)

    if final_event:
        yield final_event


def save_candidate_purpose_fit(
    invitation,
    purpose_fit: dict[str, Any],
):
    """
    Save the completed purpose-fit interpretation.
    """

    purpose_fit["summary"] = (
        purpose_fit.get("summary")
        or ""
    ).strip()

    invitation.ai_purpose_fit = purpose_fit
    invitation.ai_purpose_fit_status = "completed"
    invitation.ai_purpose_fit_generated_at = (
        timezone.now()
    )
    invitation.ai_purpose_fit_purpose = (
        get_purpose_key(invitation.process)
    )

    invitation.save(update_fields=[
        "ai_purpose_fit",
        "ai_purpose_fit_status",
        "ai_purpose_fit_generated_at",
        "ai_purpose_fit_purpose",
    ])