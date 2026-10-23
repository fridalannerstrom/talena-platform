from __future__ import annotations

from .candidate_name_privacy import redact_candidate_name

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

# Talena cognitive AI language batch 1

from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)

from .cognitive_interpretation import (
    build_cognitive_evidence_text,
)

from .prompt_templates import get_ai_prompt_instructions

def build_cognitive_questions_prompt(
    *,
    owner,
    cognitive_results: list[dict[str, Any]],
    language_code: str = "en",
) -> str:
    """
    Build the prompt for cognitive follow-up questions.

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
        key="cognitive_questions",
        language=language_code,
    )

    shared_context = build_shared_ai_context(
        owner
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

The following guidance is controlled by Talena administrators.

It controls all non-technical decisions about question content,
assessment interpretation, evidence boundaries, interviewing approach,
tone, caution, reasoning and communication.

{admin_instructions}


TALENA TECHNICAL OUTPUT CONTRACT

The following requirements exist only so Talena can process,
save and display the generated response.

Administrator guidance may control the content and number of questions,
but must not change the required JSON field names or event structure.


OUTPUT LANGUAGE

{language_instruction}

All user-facing text inside the JSON response must use the
configured output language.


OUTPUT FORMAT

Return JSON events.

Do not use Markdown.

Do not use code fences.

Do not add explanatory text outside the JSON objects.


REQUIRED EVENT STRUCTURE


1. META EVENT

Return one meta event:

{{"type":"meta","title":"Cognitive questions","label":"AI-supported questions"}}


2. QUESTIONS EVENT

Return one questions event.

The items array may contain the number of questions requested
by the administrator guidance.

Every question object must use these exact field names:

- question
- why
- listen_for

Example:

{{"type":"questions","items":[{{"question":"Question text","why":"Why this question is relevant","listen_for":"What to listen for"}}]}}


3. CONTEXT NOTE

Return one context_note event:

{{"type":"context_note","text":"Brief explanation of the evidence and context used."}}


4. DONE

Finish with:

{{"type":"done"}}
""".strip()

def create_empty_cognitive_questions(
    owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
    """
    Return the initial structure used while cognitive
    questions are being streamed.
    """

    language_code = normalize_ai_language(
        language_code
    )

    return {
        "title": (
            "Kognitiva frågor"
            if language_code == "sv"
            else "Cognitive questions"
        ),
        "label": (
            "AI-stödda frågor"
            if language_code == "sv"
            else "AI-supported questions"
        ),
        "questions": [],
        "context_note": "",
    }


def _normalise_cognitive_questions(
    value: Any,
) -> list[dict[str, str]]:
    """
    Return up to three valid cognitive question objects.
    """

    if not isinstance(value, list):
        return []

    questions = []

    for item in value:
        if not isinstance(item, dict):
            continue

        question = str(
            item.get("question")
            or ""
        ).strip()

        if not question:
            continue

        questions.append({
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

    return questions

def _get_cognitive_question_items(
    event: dict[str, Any],
) -> list[Any]:
    """
    Find question items in the common response shapes
    that the model may return.
    """

    items = event.get("items")

    if isinstance(items, list):
        return items

    questions = event.get("questions")

    if isinstance(questions, list):
        return questions

    data = event.get("data")

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        nested_items = data.get("items")

        if isinstance(nested_items, list):
            return nested_items

        nested_questions = data.get("questions")

        if isinstance(nested_questions, list):
            return nested_questions

    result = event.get("result")

    if isinstance(result, dict):
        nested_items = result.get("items")

        if isinstance(nested_items, list):
            return nested_items

        nested_questions = result.get("questions")

        if isinstance(nested_questions, list):
            return nested_questions

    return []


def apply_cognitive_questions_event(
    result: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one streamed event to the cognitive questions result.
    """

    event_type = str(
        event.get("type")
        or ""
    ).strip().lower()

    if event_type == "meta":
        result["title"] = str(
            event.get("title")
            or result["title"]
        ).strip()

        result["label"] = str(
            event.get("label")
            or result["label"]
        ).strip()

    elif event_type in {
        "questions",
        "question_list",
        "cognitive_questions",
    }:
        result["questions"] = (
            _normalise_cognitive_questions(
                _get_cognitive_question_items(
                    event
                )
            )
        )

    elif event_type == "question":
        question = (
            _normalise_cognitive_questions(
                [event]
            )
        )

        if question:
            existing_questions = list(
                result.get("questions")
                or []
            )

            existing_questions.extend(
                question
            )

            result["questions"] = (
                existing_questions
            )

    elif event_type == "context_note":
        result["context_note"] = str(
            event.get("text")
            or event.get("context_note")
            or event.get("content")
            or ""
        ).strip()

    return result

def _extract_cognitive_question_events(
    raw_text: str,
) -> list[dict[str, Any]]:
    """
    Extract cognitive question events from an OpenAI response.

    Supports:
    - NDJSON events
    - pretty-printed JSON
    - a JSON list of events
    - a normal result object containing questions
    - optional Markdown code fences
    """

    text = str(
        raw_text
        or ""
    ).strip()

    if not text:
        return []

    # Remove an optional opening Markdown code fence.
    if text.startswith("```"):
        first_newline = text.find("\n")

        if first_newline != -1:
            text = text[
                first_newline + 1:
            ]

    # Remove an optional closing Markdown code fence.
    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    events: list[dict[str, Any]] = []


    def add_payload(
        payload: Any,
    ) -> None:
        """
        Convert one decoded JSON payload into events.
        """

        if isinstance(
            payload,
            list,
        ):
            for item in payload:
                add_payload(
                    item
                )

            return

        if not isinstance(
            payload,
            dict,
        ):
            return

        # The requested event format.
        if payload.get("type"):
            events.append(
                payload
            )

            return

        # Also support a normal result object such as:
        #
        # {
        #   "questions": [...],
        #   "context_note": "..."
        # }
        if isinstance(
            payload.get("questions"),
            list,
        ):
            events.append({
                "type": "meta",

                "title": str(
                    payload.get("title")
                    or "Cognitive questions"
                ).strip(),

                "label": str(
                    payload.get("label")
                    or "AI-supported questions"
                ).strip(),
            })

            events.append({
                "type": "questions",

                "items": payload.get(
                    "questions"
                ),
            })

            context_note = str(
                payload.get("context_note")
                or ""
            ).strip()

            if context_note:
                events.append({
                    "type": "context_note",
                    "text": context_note,
                })

            events.append({
                "type": "done",
            })


    # First try parsing the complete response as one
    # JSON value.
    try:
        payload = json.loads(
            text
        )

    except json.JSONDecodeError:
        payload = None

    if payload is not None:
        add_payload(
            payload
        )

        return events


    # Otherwise scan for consecutive JSON values.
    # This supports NDJSON and pretty-printed objects.
    decoder = json.JSONDecoder()

    position = 0
    text_length = len(
        text
    )

    while position < text_length:

        while (
            position < text_length
            and text[position].isspace()
        ):
            position += 1

        if position >= text_length:
            break

        try:
            payload, end_position = (
                decoder.raw_decode(
                    text,
                    position,
                )
            )

        except json.JSONDecodeError:

            next_object = text.find(
                "{",
                position + 1,
            )

            next_array = text.find(
                "[",
                position + 1,
            )

            candidates = [
                candidate
                for candidate in (
                    next_object,
                    next_array,
                )
                if candidate != -1
            ]

            if not candidates:
                break

            position = min(
                candidates
            )

            continue

        add_payload(
            payload
        )

        position = end_position

    return events


def stream_cognitive_questions(
    *,
    owner,
    cognitive_results: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
    """
    Generate cognitive questions and repair a missing or
    malformed questions event before yielding the final result.
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

    prompt = build_cognitive_questions_prompt(
        owner=owner,
        cognitive_results=cognitive_results,
        language_code=language_code,
    )

    system_message = (
        "You are an AI component inside Talena. "
        "Follow the administrator-provided AI guidance for "
        "all non-technical question content, assessment "
        "interpretation and communication decisions. "
        "Follow Talena's technical output contract exactly, "
        "including required JSON field names and event structure. "
        f"{system_language_instruction}"
    )

    prompt = redact_candidate_name(prompt, owner.candidate)

    stream = client.chat.completions.create(
        model=get_chat_model(),

        messages=[
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],

        temperature=0.2,
        stream=True,
    )

    response_parts: list[str] = []

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

        if not delta:
            continue

        content = getattr(
            delta,
            "content",
            None,
        )

        if not content:
            continue

        response_parts.append(
            content
        )

    full_response = "".join(
        response_parts
    ).strip()

    if not full_response:
        raise ValueError(
            "The AI returned an empty cognitive questions response."
        )

    events = (
        _extract_cognitive_question_events(
            full_response
        )
    )

    meta_event: dict[str, Any] | None = None
    context_event: dict[str, Any] | None = None
    questions_event: dict[str, Any] | None = None

    for event in events:
        event_type = str(
            event.get("type")
            or ""
        ).strip().lower()

        if (
            event_type == "meta"
            and meta_event is None
        ):
            meta_event = event
            continue

        if (
            event_type == "context_note"
            and context_event is None
        ):
            context_event = {
                "type": "context_note",
                "text": str(
                    event.get("text")
                    or event.get("context_note")
                    or event.get("content")
                    or ""
                ).strip(),
            }

            continue

        if event_type in {
            "questions",
            "question_list",
            "cognitive_questions",
        }:
            questions = (
                _normalise_cognitive_questions(
                    _get_cognitive_question_items(
                        event
                    )
                )
            )

            if questions:
                questions_event = {
                    "type": "questions",
                    "items": questions,
                }

                continue

    # --------------------------------------------------------
    # Repair a missing or malformed questions event
    # --------------------------------------------------------
    if questions_event is None:
        repair_prompt = f"""
The previous response did not contain a valid cognitive questions event.

Use the same candidate, purpose, context, assessment evidence and
administrator guidance from the original request below.

Follow the administrator guidance regarding the number and content
of questions.

Return exactly one JSON object.

The object must have this structure:

{{"type":"questions","items":[
{{"question":"Question text","why":"Why this question is relevant","listen_for":"What to listen for"}}
]}}

The items array must contain at least one valid question.

Every question object must contain these exact fields:

- question
- why
- listen_for

Do not use Markdown.
Do not use code fences.
Do not add explanatory text outside the JSON object.

ORIGINAL REQUEST
{prompt}
""".strip()

        repair_response = (
            client.chat.completions.create(
                model=get_chat_model(),

                messages=[
                    {
                        "role": "system",
                        "content": (
                            system_message
                            + " Return only the requested JSON object."
                        ),
                    },
                    {
                        "role": "user",
                        "content": repair_prompt,
                    },
                ],

                temperature=0.1,
                stream=False,
            )
        )

        repair_content = str(
            repair_response
            .choices[0]
            .message
            .content
            or ""
        ).strip()

        repair_events = (
            _extract_cognitive_question_events(
                repair_content
            )
        )

        for event in repair_events:
            event_type = str(
                event.get("type")
                or ""
            ).strip().lower()

            if event_type not in {
                "questions",
                "question_list",
                "cognitive_questions",
            }:
                continue

            repaired_questions = (
                _normalise_cognitive_questions(
                    _get_cognitive_question_items(
                        event
                    )
                )
            )

            if repaired_questions:
                questions_event = {
                    "type": "questions",
                    "items": repaired_questions,
                }

                break

    if questions_event is None:
        raise ValueError(
            "The AI response did not contain "
            "valid cognitive questions."
        )

    if meta_event is None:
        meta_event = {
            "type": "meta",
            "title": (
                "Kognitiva frågor"
                if language_code == "sv"
                else "Cognitive questions"
            ),
            "label": (
                "AI-stödda frågor"
                if language_code == "sv"
                else "AI-supported questions"
            ),
        }

    yield meta_event
    yield questions_event

    if (
        context_event
        and context_event.get("text")
    ):
        yield context_event

    yield {
        "type": "done",
    }


def save_cognitive_questions(
    *,
    owner,
    result: dict[str, Any],
    language_code: str = "en",
):
    """
    Save completed cognitive questions independently from
    the cognitive interpretation.
    """

    language_code = normalize_ai_language(
        language_code
    )
    result["_language"] = language_code

    set_ai_content_language(
        owner,
        "cognitive_questions",
        language_code,
    )

    questions = (
        _normalise_cognitive_questions(
            result.get("questions")
        )
    )

    if not questions:
        raise ValueError(
            "The AI response did not contain "
            "valid cognitive questions."
        )

    result["questions"] = questions

    result["context_note"] = str(
        result.get("context_note")
        or ""
    ).strip()

    owner.ai_cognitive_questions = result

    owner.ai_cognitive_questions_status = (
        "completed"
    )

    owner.ai_cognitive_questions_generated_at = (
        timezone.now()
    )

    owner.ai_cognitive_questions_purpose = (
        get_process_purpose_key(
            owner.process
        )
    )

    owner.save(
        update_fields=[
            "ai_cognitive_questions",
            "ai_cognitive_questions_status",
            "ai_cognitive_questions_generated_at",
            "ai_cognitive_questions_purpose",
        ]
    )

    language_update_fields = (
        get_ai_language_update_fields(
            owner
        )
    )
    if language_update_fields:
        owner.save(
            update_fields=language_update_fields
        )