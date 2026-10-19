from __future__ import annotations

import json
from typing import Any, Iterable

from django.utils import timezone

from .motivation_interpretation import (
    build_motivation_evidence_text,
)
from .openai_client import (
    get_chat_model,
    get_openai_client,
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


def build_motivation_questions_prompt(
    *,
    owner,
    motivation_results: list[dict[str, Any]],
    language_code: str = "en",
) -> str:
    """
    Build Talena's prompt for motivation follow-up questions.

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
        key="motivation_questions",
        language=language_code,
    )

    shared_context = build_shared_ai_context(
        owner
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
Reference: CANDIDATE_A

SELECTED PROCESS PURPOSE
Purpose: {purpose_label}

PROCESS CONTEXT
{context_text or "No additional process context supplied."}

MOTIVATION ASSESSMENT DATA
{evidence_text}


ADMINISTRATOR AI GUIDANCE

The following guidance is controlled by Talena administrators.

It controls all non-technical decisions about question content,
motivation assessment interpretation, factor meanings, score
interpretation, evidence boundaries, interviewing approach,
reasoning, tone, caution and communication.

{admin_instructions}


TALENA TECHNICAL OUTPUT CONTRACT

The following requirements exist only so Talena can process,
save and display the generated response.

Administrator guidance may control the number and content of
questions and whether the explanatory fields contain substantive
content.

The required JSON field names and structure must not change.


OUTPUT LANGUAGE

{language_instruction}

All user-facing text inside the JSON response must use the
configured output language.


OUTPUT FORMAT

Return exactly one JSON object.

Do not use Markdown.

Do not use code fences.

Do not add text outside the JSON object.


REQUIRED JSON STRUCTURE

Use these exact top-level field names:

- title
- label
- questions
- context_note

The questions field must be an array.

Every question object must use these exact field names:

- question
- why
- listen_for

The administrator guidance determines how many question objects
should be returned.

If the administrator guidance does not require substantive content
for why or listen_for, preserve the technical field and return an
empty string.


Example:

{{
  "title": "Motivation questions",
  "label": "AI-supported questions",
  "questions": [
    {{
      "question": "Question text",
      "why": "Why this question is relevant",
      "listen_for": "What to listen for"
    }}
  ],
  "context_note": "Brief explanation of evidence and context used."
}}
""".strip()


def create_empty_motivation_questions(
    owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
    """
    Return the initial motivation questions structure.
    """

    language_code = normalize_ai_language(
        language_code
    )

    return {
        "title": (
            "Motivationsfrågor"
            if language_code == "sv"
            else "Motivation questions"
        ),
        "label": (
            "AI-stödda frågor"
            if language_code == "sv"
            else "AI-supported questions"
        ),
        "questions": [],
        "context_note": "",
    }


def _normalise_questions(
    value: Any,
) -> list[dict[str, str]]:
    """
    Return valid motivation question objects.
    """

    if not isinstance(
        value,
        list,
    ):
        return []

    questions = []

    for item in value:
        if not isinstance(
            item,
            dict,
        ):
            continue

        question = str(
            item.get("question")
            or ""
        ).strip()

        why = str(
            item.get("why")
            or ""
        ).strip()

        listen_for = str(
            item.get("listen_for")
            or ""
        ).strip()

        if not question:
            continue

        questions.append({
            "question": question,
            "why": why,
            "listen_for": listen_for,
        })

    return questions


def apply_motivation_questions_event(
    result: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one generated event to the saved result.
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

    elif event_type == "questions":
        result["questions"] = (
            _normalise_questions(
                event.get("items")
            )
        )

    elif event_type == "context_note":
        result["context_note"] = str(
            event.get("text")
            or ""
        ).strip()

    return result


def _clean_json_text(
    value: str,
) -> str:
    """
    Remove optional Markdown fences around JSON.
    """

    text = str(
        value
        or ""
    ).strip()

    if text.startswith("```"):
        first_newline = text.find(
            "\n"
        )

        if first_newline != -1:
            text = text[
                first_newline + 1:
            ]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def _parse_result(
    value: str,
) -> dict[str, Any] | None:
    """
    Parse and validate the complete AI response.
    """

    text = _clean_json_text(
        value
    )

    if not text:
        return None

    try:
        payload = json.loads(
            text
        )

    except json.JSONDecodeError:
        start = text.find(
            "{"
        )

        end = text.rfind(
            "}"
        )

        if (
            start == -1
            or end == -1
        ):
            return None

        try:
            payload = json.loads(
                text[
                    start:end + 1
                ]
            )

        except json.JSONDecodeError:
            return None

    if not isinstance(
        payload,
        dict,
    ):
        return None

    questions = (
        _normalise_questions(
            payload.get("questions")
        )
    )

    if not questions:
        return None

    return {
        "title": str(
            payload.get("title")
            or "Motivation questions"
        ).strip(),

        "label": str(
            payload.get("label")
            or "AI-supported questions"
        ).strip(),

        "questions": questions,

        "context_note": str(
            payload.get("context_note")
            or ""
        ).strip(),
    }


def _collect_stream_content(
    stream,
) -> str:
    """
    Collect the streamed response before validating its JSON.
    """

    parts: list[str] = []

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

        if content:
            parts.append(
                content
            )

    return "".join(
        parts
    ).strip()


def stream_motivation_questions(
    *,
    owner,
    motivation_results: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
    """
    Generate motivation questions independently from
    the motivation interpretation.
    """

    if not motivation_results:
        raise ValueError(
            "No motivation assessment results are available."
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

    prompt = build_motivation_questions_prompt(
        owner=owner,
        motivation_results=motivation_results,
        language_code=language_code,
    )

    system_message = (
        "You are an AI component inside Talena. "
        "Follow the administrator-provided AI guidance for "
        "all non-technical question content, motivation "
        "interpretation and communication decisions. "
        "Follow Talena's technical output contract exactly, "
        "including required JSON structure and field names. "
        f"{system_language_instruction}"
    )

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

    raw_content = (
        _collect_stream_content(
            stream
        )
    )

    result = _parse_result(
        raw_content
    )

    # Repair malformed or incomplete JSON once.
    if result is None:
        repair_response = (
            client.chat.completions.create(
                model=get_chat_model(),

                messages=[
                    {
                        "role": "system",
                        "content": (
                            system_message
                            + " Return only one valid JSON object."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "The previous response was malformed. "
                            "Generate the result again and follow the "
                            "JSON structure exactly.\n\n"
                            + prompt
                        ),
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

        result = _parse_result(
            repair_content
        )

    if result is None:
        print(
            "[MOTIVATION QUESTIONS RAW RESPONSE]",
            raw_content,
        )

        raise ValueError(
            "The AI response did not contain "
            "valid motivation questions."
        )

    yield {
        "type": "meta",
        "title": result["title"],
        "label": result["label"],
    }

    yield {
        "type": "questions",
        "items": result["questions"],
    }

    if result["context_note"]:
        yield {
            "type": "context_note",
            "text": result["context_note"],
        }

    yield {
        "type": "done",
    }


def save_motivation_questions(
    *,
    owner,
    result: dict[str, Any],
    language_code: str = "en",
):
    """
    Save motivation questions independently from
    the motivation interpretation.
    """

    language_code = normalize_ai_language(
        language_code
    )
    result["_language"] = language_code

    set_ai_content_language(
        owner,
        "motivation_questions",
        language_code,
    )

    questions = (
        _normalise_questions(
            result.get("questions")
        )
    )

    if not questions:
        raise ValueError(
            "The AI response did not contain "
            "valid motivation questions."
        )

    result["questions"] = questions

    result["context_note"] = str(
        result.get("context_note")
        or ""
    ).strip()

    owner.ai_motivation_questions = (
        result
    )

    owner.ai_motivation_questions_status = (
        "completed"
    )

    owner.ai_motivation_questions_generated_at = (
        timezone.now()
    )

    owner.ai_motivation_questions_purpose = (
        get_process_purpose_key(
            owner.process
        )
    )

    owner.save(
        update_fields=[
            "ai_motivation_questions",
            "ai_motivation_questions_status",
            "ai_motivation_questions_generated_at",
            "ai_motivation_questions_purpose",
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