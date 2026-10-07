from __future__ import annotations

import json
from typing import Any, Iterable

from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)

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

from .prompt_templates import (
    get_ai_prompt_instructions,
    get_ai_feature_prompt_instructions,
)

RESPONSE_STYLE_GUIDANCE_SCHEMA_VERSION = "social_desirability_only_v2"


# Talena personality UI and response styles language batch 1
def _get_response_style_output_examples(language_code: str) -> dict[str, str]:
    language_code = normalize_ai_language(language_code)
    if language_code == "sv":
        return {
            "title": "Så kan profilen tolkas",
            "label": "AI-stödd tolkning",
            "summary_1": "Första delen av tolkningen. ",
            "summary_2": "Nästa del av tolkningen. ",
            "how": "Vad som bör finnas i åtanke när personlighetsprofilen läses.",
            "approach": "Hur intervju- eller återkopplingssamtalet kan genomföras.",
            "question_1": "Första öppna frågan",
            "question_2": "Andra öppna frågan",
            "question_3": "Tredje öppna frågan",
            "combination": "Om ett känt kombinationsmönster är relevant och vad som kan utforskas.",
            "context": "Hur råden anpassades till syfte och eventuell processkontext.",
        }
    return {
        "title": "How to approach this profile",
        "label": "AI-supported interpretation",
        "summary_1": "First part of the interpretation. ",
        "summary_2": "Next part of the interpretation. ",
        "how": "What should be kept in mind when reading the personality traits.",
        "approach": "How to approach the interview or feedback conversation.",
        "question_1": "Question one",
        "question_2": "Question two",
        "question_3": "Question three",
        "combination": "Whether a known combination applies and what may be useful to explore.",
        "context": "Whether the advice was adapted to purpose or added context.",
    }





RESPONSE_STYLE_EXPERT_GUIDANCE = """

""".strip()


def build_response_style_evidence(
    response_styles: list[dict[str, Any]],
) -> tuple[str, dict[str, dict[str, Any]]]:
    """
    Convert available response-style results into neutral
    assessment evidence for the AI prompt.

    Talena supplies only the technical response-style key and
    rounded STEN result.

    Administrator guidance controls how those results are interpreted.
    """

    evidence_lines = []
    evidence_by_key = {}

    for style in response_styles or []:
        if not style.get("available"):
            continue

        key = str(
            style.get("key")
            or ""
        ).strip()

        title = str(
            style.get("title")
            or key
            or "Response style"
        ).strip()

        value = style.get("value")

        if not key:
            continue

        evidence_by_key[key] = {
            "key": key,
            "title": title,
            "value": value,
        }

        evidence_lines.append(
            "\n".join([
                f"{title}",
                f"- Technical key: {key}",
                f"- Rounded STEN: {value}",
            ])
        )

    if not evidence_lines:
        return (
            "No response-style results are available.",
            {},
        )

    return (
        "\n\n".join(evidence_lines),
        evidence_by_key,
    )


def build_response_style_guidance_prompt(
    *,
    guidance_owner,
    response_styles: list[dict[str, Any]],
    language_code: str = "en",
) -> str:
    """
    Build Talena's response-style guidance prompt.

    Administrator guidance controls all non-technical AI behaviour.
    """

    language_code = normalize_ai_language(
        language_code
    )

    language_instruction = get_ai_language_instruction(
        language_code
    )

    output_examples = (
        _get_response_style_output_examples(
            language_code
        )
    )

    interpretation_instructions = get_ai_prompt_instructions(
        key="response_style_interpretation",
        language=language_code,
    )

    interview_approach_instructions = get_ai_feature_prompt_instructions(
        key="response_style_interview_approach",
        language=language_code,
    )

    shared_context = build_shared_ai_context(
        guidance_owner
    )

    candidate = shared_context["candidate"]

    response_style_text, evidence_by_key = (
        build_response_style_evidence(
            response_styles
        )
    )

    if not evidence_by_key:
        raise ValueError(
            "No response-style results are available."
        )

    return f"""
TALENA INPUT DATA

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

SELECTED PROCESS PURPOSE
Purpose: {shared_context["purpose_label"]}

PROCESS CONTEXT
{shared_context["context_text"] or "No additional process context supplied."}

RESPONSE-STYLE ASSESSMENT DATA
{response_style_text}


ADMINISTRATOR AI GUIDANCE


RESPONSE-STYLE INTERPRETATION GUIDANCE

The following administrator guidance applies only to:

- summary_delta
- how_to_interpret
- combination_note
- context_note

It controls how response-style indicators are interpreted as context
for reading the personality profile.

It must not determine the substantive content of recommended_approach
or questions.

{interpretation_instructions}


INTERVIEW APPROACH GUIDANCE

The following administrator guidance applies only to:

- recommended_approach
- questions

It controls how response-style indicators are used to guide the
interviewer and formulate conversation questions.

It must not change the substantive response-style interpretation,
how_to_interpret guidance or combination note.

{interview_approach_instructions}


SECTION ISOLATION

Treat each dedicated guidance block as authoritative only for its
corresponding events.

Instructions for one section must not change the substantive content,
number of items or emphasis of the other section.

Global Talena administrator guidance still applies across all sections.

Do not allow administrator guidance to change Talena's technical event
structure, required JSON fields or streaming format.


TALENA TECHNICAL OUTPUT CONTRACT

The following requirements exist only so Talena can process,
stream, save and display the generated response.

Administrator guidance controls the substantive content inside
these fields.

Administrator guidance must not change the required event names,
JSON field names or NDJSON structure.


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

1. META

{{"type":"meta","title":"{output_examples["title"]}","label":"{output_examples["label"]}"}}


2. SUMMARY

Return one or more summary_delta events:

{{"type":"summary_delta","text":"{output_examples["summary_1"]}"}}


3. HOW TO INTERPRET

{{"type":"how_to_interpret","text":"{output_examples["how"]}"}}


4. RECOMMENDED APPROACH

{{"type":"recommended_approach","text":"{output_examples["approach"]}"}}


5. QUESTIONS

{{"type":"questions","items":["{output_examples["question_1"]}"]}}

The administrator guidance determines the number of question items.

If no substantive questions are requested, preserve the event
using an empty items array.


6. COMBINATION NOTE

{{"type":"combination_note","text":"{output_examples["combination"]}"}}


7. CONTEXT NOTE

{{"type":"context_note","text":"{output_examples["context"]}"}}


8. DONE

{{"type":"done"}}
""".strip()


def create_empty_response_style_guidance(
    guidance_owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
    output_examples = _get_response_style_output_examples(language_code)
    return {
        "title": output_examples["title"],
        "label": output_examples["label"],
        "summary": "",
        "how_to_interpret": "",
        "recommended_approach": "",
        "questions": [],
        "combination_note": "",
        "context_note": "",
    }


def apply_response_style_guidance_event(
    guidance: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one streamed NDJSON event to the complete guidance result.
    """

    event_type = event.get("type")

    if event_type == "meta":
        title = str(
            event.get("title")
            or ""
        ).strip()

        label = str(
            event.get("label")
            or ""
        ).strip()

        if title:
            guidance["title"] = title

        if label:
            guidance["label"] = label

    elif event_type == "summary_delta":
        guidance["summary"] += str(
            event.get("text")
            or ""
        )

    elif event_type == "how_to_interpret":
        guidance["how_to_interpret"] = str(
            event.get("text")
            or ""
        ).strip()

    elif event_type == "recommended_approach":
        guidance["recommended_approach"] = str(
            event.get("text")
            or ""
        ).strip()

    elif event_type == "questions":
        items = event.get("items")

        if isinstance(items, list):
            guidance["questions"] = [
                str(item).strip()
                for item in items
                if str(item).strip()
            ]

    elif event_type == "combination_note":
        guidance["combination_note"] = str(
            event.get("text")
            or ""
        ).strip()

    elif event_type == "context_note":
        guidance["context_note"] = str(
            event.get("text")
            or ""
        ).strip()

    return guidance


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
        event = json.loads(
            line
        )
    except json.JSONDecodeError:
        return None

    if not isinstance(event, dict):
        return None

    if not event.get("type"):
        return None

    return event


def stream_response_style_guidance(
    *,
    guidance_owner,
    response_styles: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
    """
    Stream parsed response-style guidance events from OpenAI.

    Each yielded value is a dictionary. The view will convert each
    dictionary into NDJSON for the browser.
    """

    language_code = normalize_ai_language(language_code)
    system_language_instruction = get_ai_system_language_instruction(
        language_code,
        owner=guidance_owner,
    )
    prompt = build_response_style_guidance_prompt(
        guidance_owner=guidance_owner,
        response_styles=response_styles,
        language_code=language_code,
    )

    client = get_openai_client()

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI component inside Talena. "
                    "Follow the administrator-provided AI guidance for "
                    "all non-technical response-style analysis, "
                    "interpretation and communication decisions. "
                    "Follow Talena's technical output contract exactly, "
                    "including required JSON field names, event types "
                    "and streaming format. "
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

        if (
            not delta
            or not delta.content
        ):
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


def save_response_style_guidance(
    *,
    guidance_owner,
    guidance: dict[str, Any],
    language_code: str = "en",
):
    """
    Save completed response-style guidance on either a
    TestInvitation or HistoricalProcessCandidate.
    """

    language_code = normalize_ai_language(language_code)
    guidance["_language"] = language_code
    guidance["_schema_version"] = RESPONSE_STYLE_GUIDANCE_SCHEMA_VERSION
    set_ai_content_language(
        guidance_owner,
        "response_style_guidance",
        language_code,
    )

    guidance["summary"] = (
        guidance.get("summary")
        or ""
    ).strip()

    guidance["how_to_interpret"] = (
        guidance.get("how_to_interpret")
        or ""
    ).strip()

    guidance["recommended_approach"] = (
        guidance.get("recommended_approach")
        or ""
    ).strip()

    guidance["combination_note"] = (
        guidance.get("combination_note")
        or ""
    ).strip()

    guidance["context_note"] = (
        guidance.get("context_note")
        or ""
    ).strip()

    questions = guidance.get(
        "questions"
    )

    if not isinstance(questions, list):
        questions = []

    guidance["questions"] = [
        str(question).strip()
        for question in questions
        if str(question).strip()
    ]

    guidance_owner.ai_response_style_guidance = (
        guidance
    )

    guidance_owner.ai_response_style_guidance_status = (
        "completed"
    )

    guidance_owner.ai_response_style_guidance_generated_at = (
        timezone.now()
    )

    guidance_owner.ai_response_style_guidance_purpose = (
        get_process_purpose_key(
            guidance_owner.process
        )
    )

    update_fields = [
        "ai_response_style_guidance",
        "ai_response_style_guidance_status",
        "ai_response_style_guidance_generated_at",
        "ai_response_style_guidance_purpose",
    ]
    update_fields.extend(get_ai_language_update_fields(guidance_owner))
    guidance_owner.save(update_fields=update_fields)
