from __future__ import annotations

import json
from typing import Any, Iterable

from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)
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




def get_purpose_fit_title(process) -> str:
    purpose_key = get_process_purpose_key(
        process
    )

    return PURPOSE_FIT_TITLES.get(
        purpose_key,
        "Purpose fit",
    )


def purpose_supports_fit(process) -> bool:
    """
    Flexible/general processes should not receive a purpose-fit verdict.
    """

    purpose_key = get_process_purpose_key(
        process
    )

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
    """
    Build the prompt for Talena's combined AI Overview.

    The overview is based on:
    - all available assessment results
    - the selected process purpose
    - optional process context

    The output remains compatible with the existing purpose-fit
    streaming and storage structure while the feature is gradually
    renamed to AI Overview.
    """

    shared_context = build_shared_ai_context(
        invitation
    )

    candidate = shared_context["candidate"]
    process = shared_context["process"]

    purpose_key = shared_context["purpose_key"]
    purpose_label = shared_context["purpose_label"]

    context_text = shared_context["context_text"]
    context_data = shared_context["context_data"]

    assessment_text, assessment_type_count = (
        build_assessment_evidence(invitation)
    )

    has_context = bool(context_data)

    if has_context:
        context_instruction = """
Use the supplied process context to explain how the assessment
indications may be relevant to this specific purpose and situation.

Clearly distinguish between:
- information stated in the process context
- indications derived from assessment results
- interpretations that should be explored further

Do not invent requirements, responsibilities or candidate experience
that are not present in the supplied information.
""".strip()
    else:
        context_instruction = """
No additional process context has been supplied.

Base the overview on the available assessment results and the selected
process purpose only.

Do not invent specific role requirements, responsibilities, team
conditions or organisational circumstances.

Clearly state that the interpretation is broader and that specific
relevance should be explored using additional context or conversation.
""".strip()

    return f"""
You are generating the AI Overview for Talena, an assessment and
talent management platform.

You are an experienced, balanced and commercially aware assessment
consultant with a strong understanding of personality, motivation,
cognitive ability, workplace behaviour and structured follow-up
conversations.

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

SELECTED PROCESS PURPOSE
Purpose: {purpose_label}

OPTIONAL PROCESS CONTEXT
{context_text}

AVAILABLE ASSESSMENT EVIDENCE
{assessment_text}

CONTEXT INSTRUCTION
{context_instruction}

YOUR TASK
Create one balanced and practical overview of all available assessment
evidence in relation to the selected process purpose and any supplied
process context.

The result should help the user understand:

1. The most important overall indications in the profile.
2. Which assessment patterns may support the selected purpose.
3. Which topics should be explored, considered or followed up.
4. One practical and proportionate next step.

CORE INTERPRETATION RULES
- Treat assessment results as indicators and hypotheses, not facts.
- Do not make a final hiring, promotion, development or placement decision.
- Do not create a match score, suitability verdict or prediction of success.
- Do not use categorical or judgemental language.
- Do not diagnose the candidate.
- Do not invent role requirements, candidate experience or process context.
- Only draw conclusions from assessment types that are actually available.
- Do not imply that personality measures ability.
- Do not imply that cognitive ability results measure personality,
  motivation or experience.
- Do not describe lower scores as automatic weaknesses.
- Do not describe higher scores as automatic strengths.
- Explain what an indication may mean in practice for the selected purpose.
- Consider combinations across available results where useful, but do not
  invent new psychological constructs, competency themes or composite scores.
- If different parts of the evidence point in different directions,
  describe the nuance or discrepancy clearly.
- If the evidence is limited, say so clearly.
- If additional context is missing, say so clearly.
- Do not include raw assessment scores in the output.
- Avoid technical test language and academic phrasing.
- Keep the language practical and useful for the person reviewing the results.

LANGUAGE AND TONE
- Write in professional, clear English.
- Use cautious formulations such as:
  "may indicate",
  "suggests",
  "appears to",
  "could mean",
  "may be relevant",
  "could be useful to explore".
- Avoid repeatedly writing "the candidate is".
- Refer to the candidate by first name where natural.
- Keep the tone balanced and non-judgemental.
- Avoid exaggerated positive or negative wording.

IMPORTANT DISTINCTIONS
- Personality results describe likely preferences or behavioural tendencies.
- Motivation results describe possible sources of energy and engagement.
- Cognitive results describe relative performance on specific reasoning tasks.
- Process context describes the purpose, requirements or situation supplied
  by the user.
- Candidate experience, competence and actual workplace behaviour cannot be
  assumed unless explicitly supplied in the context.

CONTENT REQUIREMENTS

OVERALL INTERPRETATION
Write approximately 90 to 140 words.

The interpretation should:
- summarise the most important available indications
- connect them carefully to the selected purpose
- include both potentially supportive factors and relevant considerations
- acknowledge missing or limited evidence where necessary
- avoid repeating the lists word for word

WHAT SUPPORTS THE PURPOSE
Return exactly 3 concise points.

Each point must:
- be supported by available assessment evidence
- explain possible relevance to the selected purpose or supplied context
- remain cautious and practical
- not claim proven performance, competence or experience

Do not force three positive points if the evidence does not support them.
In that situation, use cautious wording describing potentially relevant
conditions or preferences.

WHAT TO EXPLORE OR CONSIDER
Return exactly 3 concise points.

These may include:
- lower or less preferred results that may matter in this context
- potential tensions between different results
- important requirements that cannot be evaluated from the available tests
- areas where actual examples, experience or behaviour are needed
- limitations caused by missing process context

These are hypotheses to explore, not confirmed weaknesses.

RECOMMENDED NEXT STEP
Return one practical next step appropriate to the selected purpose.

Examples may include:
- a structured follow-up conversation
- behavioural examples
- a relevant work sample
- a development discussion
- clarification of role or organisational context
- comparison with additional evidence

Do not automatically recommend an interview unless recruitment is the
selected purpose.

CONTEXT NOTE
Briefly and transparently explain:
- which assessment types were used
- whether additional process context was available
- how this affects the scope of the interpretation

STREAMING OUTPUT FORMAT
Return newline-delimited JSON, also called NDJSON.

Every JSON object must be written on one single line.
Do not use Markdown.
Do not use code fences.
Do not add any text outside the JSON objects.

The existing frontend still expects the following event names.
Use them exactly.

Return events in this exact order:

1. One meta event.

The recommendation and confidence properties are temporary legacy fields
used for technical compatibility. Always return the exact values below.
They are not displayed as a verdict in the AI Overview.

{{"type":"meta","title":"AI Overview","recommendation":"Insufficient context","confidence":"Low"}}

2. Between 3 and 6 summary_delta events.

Together, these events must form the complete overall interpretation.

{{"type":"summary_delta","text":"First part of the interpretation. "}}
{{"type":"summary_delta","text":"Next part of the interpretation. "}}

3. One key_alignment event containing exactly 3 items.

{{"type":"key_alignment","items":["Supporting point one","Supporting point two","Supporting point three"]}}

4. One areas_to_verify event containing exactly 3 items.

{{"type":"areas_to_verify","items":["Consideration one","Consideration two","Consideration three"]}}

5. One suggested_next_step event.

{{"type":"suggested_next_step","text":"One practical and purpose-relevant next step."}}

6. One context_note event.

{{"type":"context_note","text":"Brief explanation of the assessment evidence and process context used."}}

7. One final done event.

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
                    "You are a careful and experienced assessment "
                    "interpretation consultant. Treat test results as "
                    "indicators rather than facts, do not invent context, "
                    "and follow the requested NDJSON streaming format exactly."
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
        get_process_purpose_key(
            invitation.process
        )
    )

    invitation.save(update_fields=[
        "ai_purpose_fit",
        "ai_purpose_fit_status",
        "ai_purpose_fit_generated_at",
        "ai_purpose_fit_purpose",
    ])