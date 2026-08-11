from __future__ import annotations

import json
from typing import Any, Iterable
from django.utils import timezone

from .openai_client import (
    get_openai_client,
    get_chat_model,
)
from .language import (
    get_ai_language_instruction,
    get_ai_language_update_fields,
    get_ai_system_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)

# Talena motivation AI language batch 1

from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)

from .prompt_templates import get_ai_prompt_instructions

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
        lines.append(
            f"- {result['name']}: "
            f"STIVE {result['score']} of 5"
        )

    return "\n".join(lines)

def build_motivation_interpretation_prompt(
    invitation,
    motivation_results: list[dict[str, Any]],
    *,
    language_code: str = "en",
) -> str:
    """
    Build Talena's motivation interpretation prompt.

    Administrator guidance controls all non-technical AI behaviour.

    Talena protects only the technical input/output contract required
    by the application.
    """

    language_code = normalize_ai_language(
        language_code
    )

    language_instruction = get_ai_language_instruction(
        language_code
    )

    admin_instructions = get_ai_prompt_instructions(
        key="motivation_interpretation",
        language=language_code,
    )

    shared_context = build_shared_ai_context(
        invitation
    )

    candidate = shared_context["candidate"]

    purpose_label = shared_context["purpose_label"]
    context_text = shared_context["context_text"]

    evidence_text = build_motivation_evidence_text(
        motivation_results
    )

    return f"""
TALENA INPUT DATA

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

SELECTED PROCESS PURPOSE
Purpose: {purpose_label}

PROCESS CONTEXT
{context_text or "No additional process context supplied."}

MOTIVATION ASSESSMENT DATA
{evidence_text}


ADMINISTRATOR AI GUIDANCE

The following guidance is controlled by Talena administrators.

It controls all non-technical decisions about analysis,
interpretation, motivation assessment principles, factor meanings,
score interpretation, evidence boundaries, reasoning, tone,
caution, conclusions and communication.

{admin_instructions}


TALENA TECHNICAL OUTPUT CONTRACT

The following requirements exist only so Talena can process,
stream, save and display the generated response.

Administrator guidance may control the content and number of
items inside each section, but must not change the required
event types, JSON field names or NDJSON structure.


OUTPUT LANGUAGE

{language_instruction}

All user-facing text inside the JSON response must use the
configured output language.


STREAMING FORMAT

Return newline-delimited JSON, also called NDJSON.

Every JSON object must appear on one single line.

Do not use Markdown.

Do not use code fences.

Do not add text outside the JSON objects.


REQUIRED EVENT STRUCTURE


1. META EVENT

Return one meta event:

{{"type":"meta","title":"Motivation interpretation","label":"AI-supported interpretation"}}


2. INTERPRETATION CONTENT

Return the overall interpretation using one or more
interpretation_delta events:

{{"type":"interpretation_delta","text":"First part of the interpretation. "}}

{{"type":"interpretation_delta","text":"Next part of the interpretation. "}}


3. ENGAGEMENT CONDITIONS

Return one engagement_conditions event.

The items array may contain the number of items requested by the
administrator guidance:

{{"type":"engagement_conditions","items":["Condition one","Condition two"]}}


4. AREAS TO CLARIFY

Return one areas_to_clarify event.

The items array may contain the number of items requested by the
administrator guidance:

{{"type":"areas_to_clarify","items":["Clarification one","Clarification two"]}}


5. EXPECTATION SETTING

Return one expectation_setting event:

{{"type":"expectation_setting","text":"Expectation-setting content."}}

If administrator guidance does not require substantive content here,
return an empty text value while preserving the technical event.


6. CONTEXT NOTE

Return one context_note event:

{{"type":"context_note","text":"Brief explanation of the evidence and context used."}}


7. DONE

Finish with:

{{"type":"done"}}
""".strip()

def create_empty_motivation_interpretation(
    owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
    language_code = normalize_ai_language(
        language_code
    )

    return {
        "title": (
            "Motivationstolkning"
            if language_code == "sv"
            else "Motivation interpretation"
        ),
        "label": (
            "AI-stödd tolkning"
            if language_code == "sv"
            else "AI-supported interpretation"
        ),
        "interpretation": "",
        "engagement_conditions": [],
        "areas_to_clarify": [],
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
                for item in items
                if str(item).strip()
            ]

    elif event_type == "areas_to_clarify":
        items = event.get("items")

        if isinstance(items, list):
            interpretation["areas_to_clarify"] = [
                str(item).strip()
                for item in items
                if str(item).strip()
            ]

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

def get_motivation_interpretation_system_prompt(
    language_code: str = "en",
) -> str:
    """
    Return Talena's technical system instructions for
    motivation interpretation generation.
    """

    language_code = normalize_ai_language(
        language_code
    )

    system_language_instruction = (
        get_ai_system_language_instruction(
            language_code
        )
    )

    return (
        "You are an AI component inside Talena. "
        "Follow the administrator-provided AI guidance for "
        "all non-technical analysis, motivation interpretation "
        "and communication decisions. "
        "Follow Talena's technical output contract exactly, "
        "including required JSON structure, field names, "
        "event types and streaming format. "
        f"{system_language_instruction}"
    )

def stream_motivation_interpretation(
    *,
    owner,
    motivation_results: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
    """
    Stream motivation interpretation events from OpenAI.

    Motivation questions are generated independently in
    motivation_questions.py.
    """

    if not motivation_results:
        raise ValueError(
            "No motivation assessment results are available."
        )

    language_code = normalize_ai_language(
        language_code
    )

    system_prompt = (
        get_motivation_interpretation_system_prompt(
            language_code
        )
    )

    client = get_openai_client()

    prompt = build_motivation_interpretation_prompt(
        invitation=owner,
        motivation_results=motivation_results,
        language_code=language_code,
    )

    stream = client.chat.completions.create(
        model=get_chat_model(),

        messages=[
            {
                "role": "system",
                "content": system_prompt,
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
        choices = getattr(
            response_event,
            "choices",
            None,
        )

        if not choices:
            continue

        delta = getattr(
            choices[0],
            "delta",
            None,
        )

        content = getattr(
            delta,
            "content",
            None,
        )

        if not content:
            continue

        buffer += content

        while "\n" in buffer:
            raw_line, buffer = buffer.split(
                "\n",
                1,
            )

            event = _parse_event_line(
                raw_line
            )

            if event:
                yield event

    final_event = _parse_event_line(
        buffer
    )

    if final_event:
        yield final_event

def save_motivation_interpretation(
    *,
    owner,
    interpretation: dict[str, Any],
    language_code: str = "en",
):
    """
    Save the completed motivation interpretation.
    """

    language_code = normalize_ai_language(
        language_code
    )
    interpretation["_language"] = language_code

    set_ai_content_language(
        owner,
        "motivation_interpretation",
        language_code,
    )

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
        get_process_purpose_key(
            owner.process
        )
    )

    owner.save(update_fields=[
        "ai_motivation_interpretation",
        "ai_motivation_interpretation_status",
        "ai_motivation_interpretation_generated_at",
        "ai_motivation_interpretation_purpose",
    ])

    language_update_fields = (
        get_ai_language_update_fields(
            owner
        )
    )
    if language_update_fields:
        owner.save(
            update_fields=language_update_fields
        )