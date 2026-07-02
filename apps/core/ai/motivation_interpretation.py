from __future__ import annotations

import json
from typing import Any, Iterable

from django.forms.models import model_to_dict
from django.utils import timezone

from .openai_client import (
    get_openai_client,
    get_chat_model,
)


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
    "flexible": "General insights",
    "unsure": "General insights",
    "general": "General insights",
}


MOTIVATION_DEFINITIONS = {
    "attachment": (
        "Social interaction, support and working as part of a team."
    ),
    "work-life balance": (
        "Maintaining a sustainable balance between work and life "
        "outside work."
    ),
    "stability": (
        "Predictability, continuity and security in the working "
        "environment."
    ),
    "customer service": (
        "Understanding customer needs and providing helpful service."
    ),
    "people development": (
        "Helping other people learn, grow and develop."
    ),
    "independence": (
        "Freedom to make decisions and shape how work is carried out."
    ),
    "recognition": (
        "Visibility, praise and acknowledgement for personal contribution."
    ),
    "authority": (
        "Status, seniority and the opportunity to influence or lead others."
    ),
    "making a difference": (
        "Contributing to a wider purpose or creating positive impact."
    ),
    "acquisition": (
        "Financial reward, resources and tangible gain."
    ),
    "commercial focus": (
        "Creating measurable commercial value and business results."
    ),
    "quality": (
        "Producing accurate and reliable work to a high standard."
    ),
    "learning": (
        "Developing knowledge, capability and new skills."
    ),
    "achievement": (
        "Clear goals, challenge and a visible sense of progress."
    ),
    "ethics": (
        "Acting in line with clear principles and ethical standards."
    ),
    "risk": (
        "Taking calculated risks and acting despite uncertainty."
    ),
    "enjoyment": (
        "Positive energy and enjoyment in day-to-day work."
    ),
    "variety": (
        "Change, different tasks and varied ways of working."
    ),
    "curiosity": (
        "Exploring new information, questions and unfamiliar problems."
    ),
    "creativity": (
        "Generating new ideas and finding original approaches."
    ),
}


def get_purpose_key(process) -> str:
    return (process.purpose or "").strip().lower()


def get_purpose_label(process) -> str:
    purpose_key = get_purpose_key(process)

    if purpose_key in PURPOSE_LABELS:
        return PURPOSE_LABELS[purpose_key]

    if hasattr(process, "get_purpose_display"):
        return process.get_purpose_display()

    return purpose_key or "General insights"


def build_process_context(
    process,
) -> tuple[str, dict[str, Any]]:
    """
    Convert optional process context into prompt-friendly text.
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
        return (
            "No additional process context has been added.",
            {},
        )

    raw_context = model_to_dict(
        purpose_context
    )

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


def _normalise_name(value: Any) -> str:
    return str(value or "").strip()


def _normalise_score(value: Any) -> int | None:
    if value is None:
        return None

    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return None

    return max(1, min(5, score))


def extract_motivation_results(
    invitation,
) -> list[dict[str, Any]]:
    """
    Extract available motivation results from Sova activities.

    Motivation scores use the rounded five-point STIVE scale.
    """

    activities = (
        invitation.sova_activities
        or []
    )

    results_by_name: dict[str, dict[str, Any]] = {}

    for activity in activities:
        activity_name = _normalise_name(
            activity.get("activity")
        )

        activity_name_lower = (
            activity_name.lower()
        )

        competencies = (
            activity.get("competencies")
            or []
        )

        looks_like_motivation = any(
            keyword in activity_name_lower
            for keyword in (
                "motivation",
                "motivational",
                "motivator",
                "mq",
            )
        )

        for competency in competencies:
            competency_name = _normalise_name(
                competency.get("competency")
                or competency.get("name")
            )

            if not competency_name:
                continue

            competency_key = (
                competency_name.lower()
            )

            known_factor = (
                competency_key
                in MOTIVATION_DEFINITIONS
            )

            if not (
                looks_like_motivation
                or known_factor
            ):
                continue

            score = _normalise_score(
                competency.get("stive_rounded")
            )

            if score is None:
                score = _normalise_score(
                    competency.get("stive")
                )

            if score is None:
                continue

            results_by_name[competency_key] = {
                "name": competency_name,
                "score": score,
                "definition": (
                    MOTIVATION_DEFINITIONS.get(
                        competency_key,
                        "",
                    )
                ),
            }

    return list(
        results_by_name.values()
    )


def describe_motivation_level(
    score: int,
) -> str:
    """
    Return a neutral interpretation of a STIVE motivation score.
    """

    if score == 1:
        return "likely to be considerably less central"

    if score == 2:
        return "likely to be less central"

    if score == 3:
        return "likely to be moderately important"

    if score == 4:
        return "likely to be prominent"

    return "likely to be highly prominent"


def build_motivation_evidence_text(
    results: list[dict[str, Any]],
) -> str:
    if not results:
        return (
            "No motivation assessment results are available."
        )

    sorted_results = sorted(
        results,
        key=lambda item: (
            -item["score"],
            item["name"].lower(),
        ),
    )

    lines = []

    for result in sorted_results:
        definition = (
            result.get("definition")
            or "No predefined factor definition is available."
        )

        lines.append(
            f"- {result['name']}: "
            f"STIVE {result['score']} of 5; "
            f"{describe_motivation_level(result['score'])}. "
            f"Definition: {definition}"
        )

    return "\n".join(lines)


def build_motivation_interpretation_prompt(
    invitation,
    motivation_results: list[dict[str, Any]],
) -> str:
    """
    Build the prompt for Talena's motivation interpretation.
    """

    candidate = invitation.candidate
    process = invitation.process

    purpose_label = get_purpose_label(
        process
    )

    context_text, context_data = (
        build_process_context(process)
    )

    evidence_text = (
        build_motivation_evidence_text(
            motivation_results
        )
    )

    has_context = bool(context_data)

    sorted_results = sorted(
        motivation_results,
        key=lambda item: (
            -item["score"],
            item["name"].lower(),
        ),
    )

    prominent_factors = sorted_results[:3]

    less_central_factors = sorted(
        motivation_results,
        key=lambda item: (
            item["score"],
            item["name"].lower(),
        ),
    )[:3]

    prominent_text = "\n".join(
        (
            f"- {item['name']}: "
            f"STIVE {item['score']} of 5"
        )
        for item in prominent_factors
    )

    less_central_text = "\n".join(
        (
            f"- {item['name']}: "
            f"STIVE {item['score']} of 5"
        )
        for item in less_central_factors
    )

    if has_context:
        context_instruction = """
Use the supplied process context to explain how the motivation profile
may relate to the stated role, situation or development purpose.

Clearly distinguish between:
- motivational preferences indicated by the assessment
- information explicitly stated in the process context
- assumptions that must be explored through conversation

Do not invent requirements, working conditions, rewards, culture or
candidate experience that are not present in the supplied information.
""".strip()

    else:
        context_instruction = """
No additional process context has been supplied.

Provide a broader interpretation based on the available motivation
results and the selected purpose only.

Do not invent specific role conditions, organisational culture,
leadership style, rewards, responsibilities or career opportunities.

State clearly that practical relevance depends on the actual context
and the person's own reflections.
""".strip()

    return f"""
You are generating an AI-supported motivation interpretation for
Talena, an assessment and talent management platform.

You are an experienced, balanced and commercially aware assessment
consultant with strong knowledge of workplace motivation, engagement,
expectation setting and structured follow-up conversations.

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

SELECTED PROCESS PURPOSE
Purpose: {purpose_label}

OPTIONAL PROCESS CONTEXT
{context_text}

ALL AVAILABLE MOTIVATION RESULTS
{evidence_text}

THREE MOST PROMINENT AVAILABLE FACTORS
{prominent_text}

THREE LEAST CENTRAL AVAILABLE FACTORS
{less_central_text}

CONTEXT INSTRUCTION
{context_instruction}

YOUR TASK
Create one practical and balanced interpretation of the available
motivation profile in relation to the selected process purpose and any
supplied process context.

Help the user understand:

1. What may provide energy and engagement.
2. Which working conditions may support sustainable motivation.
3. Which expectations, tensions or less central drivers should be clarified.
4. Which questions may help understand how the person experiences motivation
   in practice.
5. How the role, situation or development opportunity should be described
   realistically.

CORE INTERPRETATION RULES
- Motivation results describe likely sources of energy, engagement and
  preference.
- They do not measure ability, personality, competence, values, integrity,
  experience or likely job performance.
- A lower score does not indicate poor motivation in general.
- A lower score means that the factor may be less central as a source of
  energy or engagement.
- A higher score does not mean that the person always requires the factor
  or will perform well when it is present.
- Do not make a hiring, promotion, placement or development decision.
- Do not create a match score, suitability verdict or prediction of success.
- Do not diagnose the candidate.
- Do not invent role conditions, company culture or candidate experience.
- Treat results as indicators and hypotheses, not facts.
- Interpret combinations across factors where useful.
- Do not create invented psychological constructs or composite scores.
- Where factors point in different directions, describe the tension or nuance.
- Do not include raw scores in the final output.
- Use the person's own examples and reflections as important additional
  evidence.
- If context is limited or missing, say so clearly.

IMPORTANT DISTINCTIONS
- Prominent factors may provide energy when present, but can also create
  frustration when consistently absent.
- Less central factors are not weaknesses and do not mean the person rejects
  those conditions.
- Mid-range results may indicate flexibility or that the factor is neither a
  particularly strong driver nor a strong source of disengagement.
- The same motivation factor can be expressed differently depending on the
  work environment and the individual.
- Motivation can change over time and across situations.

LANGUAGE AND TONE
- Write in professional, clear English.
- Be practical, balanced and non-judgemental.
- Use cautious formulations such as:
  "may indicate",
  "suggests",
  "may gain energy from",
  "may be less dependent on",
  "could be useful to clarify".
- Avoid technical or academic language.
- Avoid repeatedly writing "the candidate is".
- Refer to the candidate by first name where natural.
- Do not use exaggerated positive or negative wording.

CONTENT REQUIREMENTS

OVERALL MOTIVATION INTERPRETATION
Write approximately 100 to 150 words.

The interpretation should:
- describe the most important motivation patterns
- consider combinations across prominent, mid-range and less central factors
- connect cautiously to the selected purpose
- use supplied context where available
- identify any meaningful tension or condition
- explain limitations where context is missing
- avoid simply repeating the top-three descriptions

ENGAGEMENT CONDITIONS
Return exactly 3 concise points.

Each point should:
- describe a condition that may support energy or sustainable engagement
- be grounded in the available motivation results
- connect to the selected purpose or context where possible
- remain cautious rather than prescriptive

Do not simply repeat the factor names.

WHAT TO EXPLORE OR CLARIFY
Return exactly 3 concise points.

These may include:
- how prominent drivers are expressed in practice
- how the person responds when a prominent factor is absent
- what less central factors mean to the individual
- possible tensions between different drivers
- unclear or missing information about the actual context
- expectations that should be discussed before decisions are made

These are topics for clarification, not confirmed risks or weaknesses.

QUESTIONS TO EXPLORE
Return exactly 3 question objects.

Each question must:
- be open and practical
- invite a concrete example or reflection
- help understand how the motivation pattern appears in real situations
- be relevant to the selected purpose
- avoid leading the respondent towards a preferred answer
- cover different themes rather than asking the same question three ways

For recruitment, questions may be phrased as interview questions.
For development, leadership, onboarding or team purposes, phrase them
as reflection or discussion questions where appropriate.

For each question, also return:
- why the question is relevant
- what the user should listen for

REALISTIC EXPECTATION SETTING
Write one short practical paragraph.

Explain what the user should describe or clarify honestly about the role,
environment or development situation.

Base this only on:
- the available motivation profile
- the selected purpose
- supplied process context

Do not invent benefits, working conditions or organisational promises.

CONTEXT NOTE
Briefly explain:
- that a motivation assessment was used
- whether additional process context was available
- how this affects the scope of the interpretation

STREAMING OUTPUT FORMAT
Return newline-delimited JSON, also called NDJSON.

Every JSON object must appear on one single line.
Do not use Markdown.
Do not use code fences.
Do not add text outside the JSON objects.

Return events in this exact order:

1. One meta event:

{{"type":"meta","title":"Motivation interpretation","label":"AI-supported interpretation"}}

2. Between 3 and 6 interpretation_delta events:

{{"type":"interpretation_delta","text":"First part of the interpretation. "}}
{{"type":"interpretation_delta","text":"Next part of the interpretation. "}}

Together, these events form the complete overall interpretation.

3. One engagement_conditions event containing exactly 3 items:

{{"type":"engagement_conditions","items":["Condition one","Condition two","Condition three"]}}

4. One areas_to_clarify event containing exactly 3 items:

{{"type":"areas_to_clarify","items":["Clarification one","Clarification two","Clarification three"]}}

5. One questions event containing exactly 3 objects:

{{"type":"questions","items":[{{"question":"Question one","why":"Why it matters","listen_for":"What to listen for"}},{{"question":"Question two","why":"Why it matters","listen_for":"What to listen for"}},{{"question":"Question three","why":"Why it matters","listen_for":"What to listen for"}}]}}

6. One expectation_setting event:

{{"type":"expectation_setting","text":"A short, honest expectation-setting recommendation."}}

7. One context_note event:

{{"type":"context_note","text":"Brief explanation of the evidence and context used."}}

8. One final done event:

{{"type":"done"}}
""".strip()


def create_empty_motivation_interpretation(
    owner,
) -> dict[str, Any]:
    return {
        "title": "Motivation interpretation",
        "label": "AI-supported interpretation",
        "interpretation": "",
        "engagement_conditions": [],
        "areas_to_clarify": [],
        "questions": [],
        "expectation_setting": "",
        "context_note": "",
    }


def apply_motivation_interpretation_event(
    interpretation: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one streamed event to the complete saved result.
    """

    event_type = event.get("type")

    if event_type == "meta":
        interpretation["title"] = str(
            event.get("title")
            or interpretation["title"]
        ).strip()

        interpretation["label"] = str(
            event.get("label")
            or interpretation["label"]
        ).strip()

    elif event_type == "interpretation_delta":
        interpretation["interpretation"] += str(
            event.get("text")
            or ""
        )

    elif event_type == "engagement_conditions":
        items = event.get("items")

        if isinstance(items, list):
            interpretation["engagement_conditions"] = [
                str(item).strip()
                for item in items[:3]
                if str(item).strip()
            ]

    elif event_type == "areas_to_clarify":
        items = event.get("items")

        if isinstance(items, list):
            interpretation["areas_to_clarify"] = [
                str(item).strip()
                for item in items[:3]
                if str(item).strip()
            ]

    elif event_type == "questions":
        items = event.get("items")

        if isinstance(items, list):
            normalised_questions = []

            for item in items[:3]:
                if not isinstance(item, dict):
                    continue

                question = str(
                    item.get("question")
                    or ""
                ).strip()

                if not question:
                    continue

                normalised_questions.append({
                    "question": question,
                    "why": str(
                        item.get("why")
                        or ""
                    ).strip(),
                    "listen_for": str(
                        item.get("listen_for")
                        or ""
                    ).strip(),
                })

            interpretation["questions"] = (
                normalised_questions
            )

    elif event_type == "expectation_setting":
        interpretation["expectation_setting"] = str(
            event.get("text")
            or ""
        ).strip()

    elif event_type == "context_note":
        interpretation["context_note"] = str(
            event.get("text")
            or ""
        ).strip()

    return interpretation


def _parse_event_line(
    raw_line: str,
) -> dict[str, Any] | None:
    line = raw_line.strip()

    if not line:
        return None

    if line in {
        "```",
        "```json",
        "```ndjson",
    }:
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


def stream_motivation_interpretation(
    *,
    owner,
    motivation_results: list[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
    """
    Stream motivation interpretation events from OpenAI.
    """

    if not motivation_results:
        raise ValueError(
            "No motivation assessment results are available."
        )

    client = get_openai_client()

    prompt = build_motivation_interpretation_prompt(
        invitation=owner,
        motivation_results=motivation_results,
    )

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful and experienced workplace "
                    "motivation assessment consultant. Treat motivation "
                    "results as indicators rather than facts, never "
                    "invent context, and follow the requested NDJSON "
                    "streaming format exactly."
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

    final_event = _parse_event_line(
        buffer
    )

    if final_event:
        yield final_event


def save_motivation_interpretation(
    *,
    owner,
    interpretation: dict[str, Any],
):
    """
    Save the completed motivation interpretation.
    """

    interpretation["interpretation"] = (
        interpretation.get("interpretation")
        or ""
    ).strip()

    owner.ai_motivation_interpretation = (
        interpretation
    )

    owner.ai_motivation_interpretation_status = (
        "completed"
    )

    owner.ai_motivation_interpretation_generated_at = (
        timezone.now()
    )

    owner.ai_motivation_interpretation_purpose = (
        get_purpose_key(owner.process)
    )

    owner.save(update_fields=[
        "ai_motivation_interpretation",
        "ai_motivation_interpretation_status",
        "ai_motivation_interpretation_generated_at",
        "ai_motivation_interpretation_purpose",
    ])