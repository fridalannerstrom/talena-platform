from __future__ import annotations

import json
from typing import Any, Iterable

from django.utils import timezone

from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)

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

from .prompt_templates import (
    get_ai_prompt_instructions,
    get_ai_feature_prompt_instructions,
)

def extract_cognitive_results(
    invitation,
) -> list[dict[str, Any]]:
    """
    Extract available cognitive percentile results from the
    candidate's Sova activities.

    Returns only assessments that contain a usable percentile.
    """

    activities = (
        invitation.sova_activities
        or []
    )

    result_config = {
        "logical": {
            "label": "Logical reasoning",
            "keywords": (
                "logical",
                "logisk",
            ),
        },
        "numerical": {
            "label": "Numerical reasoning",
            "keywords": (
                "numerical",
                "numeric",
                "numerisk",
            ),
        },
        "verbal": {
            "label": "Verbal reasoning",
            "keywords": (
                "verbal",
            ),
        },
    }

    results = []

    for activity in activities:
        activity_name = (
            activity.get("activity")
            or ""
        ).strip()

        activity_name_lower = (
            activity_name.lower()
        )

        matched_key = None

        for test_key, config in result_config.items():
            if any(
                keyword in activity_name_lower
                for keyword in config["keywords"]
            ):
                matched_key = test_key
                break

        if not matched_key:
            continue

        competencies = (
            activity.get("competencies")
            or []
        )

        percentile = None

        for competency in competencies:
            value = competency.get(
                "percentile"
            )

            if value is None:
                continue

            try:
                percentile = int(
                    round(float(value))
                )
            except (TypeError, ValueError):
                percentile = None

            if percentile is not None:
                break

        if percentile is None:
            continue

        percentile = max(
            0,
            min(100, percentile),
        )

        results.append({
            "key": matched_key,
            "label": (
                result_config[matched_key]["label"]
            ),
            "percentile": percentile,
        })

    return results



def build_cognitive_evidence_text(
    results: list[dict[str, Any]],
) -> str:
    if not results:
        return (
            "No cognitive assessment results are available."
        )

    lines = []

    for result in results:
        percentile = result["percentile"]

        lines.append(
            f"- {result['label']}: "
            f"percentile {percentile}"
        )

    return "\n".join(lines)


def build_cognitive_interpretation_prompt(
    invitation,
    cognitive_results: list[dict[str, Any]],
    *,
    language_code: str = "en",
) -> str:
    """
    Build the prompt for the cognitive interpretation section.

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
        key="cognitive_interpretation",
        language=language_code,
    )

    considerations_instructions = get_ai_feature_prompt_instructions(
        key="cognitive_considerations",
        language=language_code,
    )

    shared_context = build_shared_ai_context(
        invitation
    )

    candidate = shared_context["candidate"]

    purpose_label = shared_context["purpose_label"]
    context_text = shared_context["context_text"]

    evidence_text = build_cognitive_evidence_text(
        cognitive_results
    )

    return f"""
TALENA INPUT DATA

CANDIDATE
Reference: CANDIDATE_A

SELECTED PROCESS PURPOSE
Purpose: {purpose_label}

PROCESS CONTEXT
{context_text or "No additional process context supplied."}

COGNITIVE ASSESSMENT DATA
{evidence_text}


ADMINISTRATOR AI GUIDANCE


PRACTICAL INTERPRETATION GUIDANCE

The following administrator guidance applies only to the
practical cognitive interpretation returned through
interpretation_delta events.

Do not use this guidance to determine the substantive content
of the considerations event.

If this guidance contains older instructions relating to
considerations, the dedicated considerations guidance below
takes precedence.

{admin_instructions}


RELEVANT CONSIDERATIONS GUIDANCE

The following administrator guidance applies only to the
considerations event.

Do not use it to change the practical interpretation.

{considerations_instructions}


SECTION ISOLATION

Treat each dedicated section guidance as authoritative for its
corresponding event.

Instructions for one section must not change the substantive
content, number of items or emphasis of another section.

Global Talena administrator guidance still applies across all sections.

The technical questions event, if generated, is not controlled by
either of these visible interpretation-section prompts.

Do not allow administrator guidance to change Talena's technical
event structure, required JSON fields or streaming format.


TALENA TECHNICAL OUTPUT CONTRACT

The following requirements exist only so Talena can process,
stream, save and display the generated response.

Administrator guidance may control the content inside these fields,
but must not change the required event types, JSON field names or
NDJSON structure.

OUTPUT LANGUAGE

{language_instruction}

All user-facing text inside the JSON response must use the
configured output language.


STREAMING FORMAT

Return newline-delimited JSON, also called NDJSON.

Every JSON object must be written on one single line.

Do not use Markdown.

Do not use code fences.

Do not add text outside the JSON objects.


REQUIRED EVENT STRUCTURE

Return events in this exact order.


1. META EVENT

Return one meta event:

{{"type":"meta","title":"Cognitive interpretation","label":"AI-supported interpretation"}}


2. INTERPRETATION CONTENT

Return the practical interpretation using one or more
interpretation_delta events:

{{"type":"interpretation_delta","text":"First part of the interpretation. "}}

{{"type":"interpretation_delta","text":"Next part of the interpretation. "}}


3. CONSIDERATIONS

Return one considerations event.

The items array contains the consideration texts requested by the
administrator guidance:

{{"type":"considerations","items":["Consideration one","Consideration two"]}}


4. QUESTIONS

Return one questions event.

Each question object must use these exact field names:

- question
- why
- listen_for

Example:

{{"type":"questions","items":[{{"question":"Question one","why":"Why it matters","listen_for":"What to listen for"}}]}}


5. CONTEXT NOTE

Return one context_note event:

{{"type":"context_note","text":"Brief explanation of the evidence and context used."}}


6. DONE

Finish with:

{{"type":"done"}}
""".strip()

def create_empty_cognitive_interpretation(
    owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
    language_code = normalize_ai_language(
        language_code
    )

    return {
        "title": (
            "Kognitiv tolkning"
            if language_code == "sv"
            else "Cognitive interpretation"
        ),
        "label": (
            "AI-stödd tolkning"
            if language_code == "sv"
            else "AI-supported interpretation"
        ),
        "interpretation": "",
        "considerations": [],
        "questions": [],
        "context_note": "",
    }


def apply_cognitive_interpretation_event(
    interpretation: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one streamed event to the complete saved result.
    """

    event_type = event.get("type")

    if event_type == "meta":
        interpretation["title"] = (
            str(
                event.get("title")
                or interpretation["title"]
            ).strip()
        )

        interpretation["label"] = (
            str(
                event.get("label")
                or interpretation["label"]
            ).strip()
        )

    elif event_type == "interpretation_delta":
        interpretation["interpretation"] += str(
            event.get("text")
            or ""
        )

    elif event_type == "considerations":
        items = event.get("items")

        if isinstance(items, list):
            interpretation["considerations"] = [
                str(item).strip()
                for item in items
                if str(item).strip()
            ]

    elif event_type == "questions":
        items = event.get("items")

        if isinstance(items, list):
            normalised_questions = []

            for item in items:
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


def stream_cognitive_interpretation(
    *,
    owner,
    cognitive_results: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
    """
    Stream cognitive interpretation events from OpenAI.
    """

    if not cognitive_results:
        raise ValueError(
            "No cognitive assessment results are available."
        )

    language_code = normalize_ai_language(
        language_code
    )
    system_language_instruction = (
        get_ai_system_language_instruction(
            language_code,
            owner=owner,
        )
    )

    client = get_openai_client()

    prompt = build_cognitive_interpretation_prompt(
        invitation=owner,
        cognitive_results=cognitive_results,
        language_code=language_code,
    )

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI component inside Talena. "
                    "Follow the administrator-provided AI guidance for "
                    "all non-technical analysis, interpretation and "
                    "communication decisions. "
                    "Follow Talena's technical output contract exactly, "
                    "including required JSON structure, field names, "
                    "event types and streaming format. "
                    f"{system_language_instruction}"
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


def save_cognitive_interpretation(
    *,
    owner,
    interpretation: dict[str, Any],
    language_code: str = "en",
):
    """
    Save the completed cognitive interpretation.
    """

    language_code = normalize_ai_language(
        language_code
    )
    interpretation["_language"] = language_code

    set_ai_content_language(
        owner,
        "cognitive_interpretation",
        language_code,
    )

    interpretation["interpretation"] = (
        interpretation.get("interpretation")
        or ""
    ).strip()

    owner.ai_cognitive_interpretation = (
        interpretation
    )

    owner.ai_cognitive_interpretation_status = (
        "completed"
    )

    owner.ai_cognitive_interpretation_generated_at = (
        timezone.now()
    )

    owner.ai_cognitive_interpretation_purpose = (
        get_process_purpose_key(
            owner.process
        )
    )

    owner.save(update_fields=[
        "ai_cognitive_interpretation",
        "ai_cognitive_interpretation_status",
        "ai_cognitive_interpretation_generated_at",
        "ai_cognitive_interpretation_purpose",
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