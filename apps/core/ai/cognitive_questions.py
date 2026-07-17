from __future__ import annotations

import json
from typing import Any, Iterable

from django.utils import timezone

from .openai_client import (
    get_openai_client,
    get_chat_model,
)

from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)

from .cognitive_interpretation import (
    build_cognitive_evidence_text,
)


def build_cognitive_questions_prompt(
    *,
    owner,
    cognitive_results: list[dict[str, Any]],
) -> str:
    """
    Build a prompt for practical, purpose-aware cognitive
    follow-up questions.

    This module generates questions only. It does not generate
    or update the cognitive interpretation.
    """

    shared_context = build_shared_ai_context(
        owner
    )

    candidate = shared_context["candidate"]
    process = shared_context["process"]

    purpose_label = shared_context["purpose_label"]
    context_text = shared_context["context_text"]
    context_data = shared_context["context_data"]

    evidence_text = (
        build_cognitive_evidence_text(
            cognitive_results
        )
    )

    if context_data:
        context_instruction = """
Use only the supplied process context when referring to role demands,
working situations or responsibilities.

Do not invent tasks, systems, responsibilities, time pressure,
leadership demands or required competence.

The questions may explore how the candidate approaches cognitive
demands explicitly described in the context.
""".strip()

    else:
        context_instruction = """
No additional process context has been supplied.

Base the questions on the available cognitive assessment results and
the selected process purpose.

Keep the questions broadly applicable. Do not invent specific role
tasks, systems, responsibilities or working conditions.
""".strip()

    return f"""
You are generating AI-supported cognitive follow-up questions for
Talena, an assessment and talent management platform.

You are an experienced and balanced assessment consultant with strong
knowledge of cognitive assessment, structured interviewing and
development conversations.

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

SELECTED PROCESS PURPOSE
Purpose: {purpose_label}

OPTIONAL PROCESS CONTEXT
{context_text}

AVAILABLE COGNITIVE ASSESSMENT EVIDENCE
{evidence_text}

CONTEXT INSTRUCTION
{context_instruction}

YOUR TASK
Generate exactly 3 practical questions that help the user gather
additional evidence relating to the available cognitive assessment
results.

The questions should help explore:
- how the candidate approaches relevant information or problems
- working methods and strategies
- how complexity, pace or unfamiliarity may affect the approach
- what conditions or support may help
- concrete examples from real situations

IMPORTANT ASSESSMENT PRINCIPLES
- Cognitive results describe relative performance on specific
  reasoning tasks compared with a reference group.
- They do not measure overall intelligence.
- They do not prove actual workplace competence or suitability.
- They do not measure experience, knowledge, motivation or personality.
- A lower result does not mean that the person cannot perform the work.
- A higher result does not guarantee strong workplace performance.
- Treat results as indicators and hypotheses.
- Do not make a hiring, promotion or suitability decision.
- Do not diagnose the candidate.
- Do not include percentile numbers in the questions.
- Do not invent candidate experience.
- Do not lead the candidate towards a preferred answer.

QUESTION RULES
Each question must:
- be open and practical
- request a concrete example, approach or working method
- be relevant to at least one available cognitive result
- be understandable without psychometric knowledge
- avoid repeating another question
- avoid wording that implies a confirmed strength or weakness

For recruitment, phrase questions as interview questions.

For development, onboarding, leadership or team purposes, use
reflection or discussion wording where appropriate.

WHY FIELD RULES
For every question, explain why the question is useful.

The explanation must:
- describe which assessment hypothesis it helps explore
- use cautious language
- avoid claiming that the question measures or proves competence
- avoid generic wording
- remain concise

Use formulations such as:
- "This helps explore..."
- "This may provide additional evidence about..."
- "This can add context to..."

LISTEN_FOR FIELD RULES
For every question, explain what concrete evidence the user should
look for in the answer.

Include specific cues such as:
- how the situation was understood or defined
- which information was used
- how the candidate structured the task
- decisions, priorities or trade-offs
- adjustments made when the first approach did not work
- use of checking, preparation, support or tools
- observable outcomes
- reflection and learning

Do not simply repeat the question.

Avoid vague phrases such as:
- "look for good problem-solving"
- "listen for effective strategies"
- "look for communication skills"
- "consider the outcome"

CONTEXT NOTE
Briefly explain:
- which cognitive assessments were available
- whether additional process context was available
- that the questions are intended to gather supporting evidence

STREAMING OUTPUT FORMAT
Return newline-delimited JSON, also called NDJSON.

Every JSON object must be on one single line.
Do not use Markdown.
Do not use code fences.
Do not add text outside the JSON objects.

Return events in this exact order:

1. One meta event:

{{"type":"meta","title":"Cognitive questions","label":"AI-supported questions"}}

2. One questions event containing exactly 3 objects:

{{"type":"questions","items":[{{"question":"Question one","why":"Why this question is useful","listen_for":"Concrete evidence to look for"}},{{"question":"Question two","why":"Why this question is useful","listen_for":"Concrete evidence to look for"}},{{"question":"Question three","why":"Why this question is useful","listen_for":"Concrete evidence to look for"}}]}}

3. One context_note event:

{{"type":"context_note","text":"Brief explanation of the evidence and context used."}}

4. One final done event:

{{"type":"done"}}
""".strip()


def create_empty_cognitive_questions(
    owner,
) -> dict[str, Any]:
    """
    Return the initial structure used while cognitive
    questions are being streamed.
    """

    return {
        "title": "Cognitive questions",
        "label": "AI-supported questions",
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

    for item in value[:3]:
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
                existing_questions[:3]
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
) -> Iterable[dict[str, Any]]:
    """
    Generate cognitive questions and repair a missing or
    malformed questions event before yielding the final result.
    """

    if not cognitive_results:
        raise ValueError(
            "No cognitive assessment results are available."
        )

    client = get_openai_client()

    prompt = build_cognitive_questions_prompt(
        owner=owner,
        cognitive_results=cognitive_results,
    )

    system_message = (
        "You are a careful and experienced cognitive "
        "assessment consultant. Treat assessment results "
        "as indicators rather than facts. Do not invent "
        "candidate or process context. Follow the requested "
        "JSON output format exactly."
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

            if len(questions) == 3:
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
The previous response did not contain exactly three valid cognitive
questions.

Use the same candidate, purpose, context and cognitive evidence from
the original request below.

Return exactly one JSON object on one line.

The object must have this exact structure:

{{"type":"questions","items":[
{{"question":"Open practical question","why":"Why this helps explore the assessment hypothesis","listen_for":"Specific evidence to look for"}},
{{"question":"Open practical question","why":"Why this helps explore the assessment hypothesis","listen_for":"Specific evidence to look for"}},
{{"question":"Open practical question","why":"Why this helps explore the assessment hypothesis","listen_for":"Specific evidence to look for"}}
]}}

Every question object must contain:
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

            if len(repaired_questions) == 3:
                questions_event = {
                    "type": "questions",
                    "items": repaired_questions,
                }

                break

    if questions_event is None:
        print(
            "[COGNITIVE QUESTIONS RAW RESPONSE]",
            full_response,
        )

        print(
            "[COGNITIVE QUESTIONS PARSED EVENTS]",
            events,
        )

        raise ValueError(
            "The AI response did not contain "
            "three valid cognitive questions."
        )

    if meta_event is None:
        meta_event = {
            "type": "meta",
            "title": "Cognitive questions",
            "label": "AI-supported questions",
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
):
    """
    Save completed cognitive questions independently from
    the cognitive interpretation.
    """

    questions = (
        _normalise_cognitive_questions(
            result.get("questions")
        )
    )

    if len(questions) != 3:
        raise ValueError(
            "The AI response did not contain "
            "three valid cognitive questions."
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