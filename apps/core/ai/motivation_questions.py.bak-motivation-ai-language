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
from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)


def build_motivation_questions_prompt(
    *,
    owner,
    motivation_results: list[dict[str, Any]],
) -> str:
    """
    Build a purpose-aware prompt for motivation questions only.
    """

    shared_context = build_shared_ai_context(
        owner
    )

    candidate = shared_context["candidate"]
    purpose_label = shared_context["purpose_label"]
    context_text = shared_context["context_text"]
    context_data = shared_context["context_data"]

    evidence_text = (
        build_motivation_evidence_text(
            motivation_results
        )
    )

    if context_data:
        context_instruction = """
Use only the supplied process context when referring to role conditions,
working environment, responsibilities, rewards or development opportunities.

Do not invent culture, benefits, tasks or expectations that are not
present in the supplied context.
""".strip()

    else:
        context_instruction = """
No additional process context has been supplied.

Base the questions on the available motivation results and selected
purpose. Keep them broadly applicable and do not invent role conditions,
rewards, responsibilities or organisational culture.
""".strip()

    return f"""
You are generating AI-supported motivation follow-up questions for
Talena, an assessment and talent management platform.

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

SELECTED PROCESS PURPOSE
Purpose: {purpose_label}

OPTIONAL PROCESS CONTEXT
{context_text}

AVAILABLE MOTIVATION EVIDENCE
{evidence_text}

CONTEXT INSTRUCTION
{context_instruction}

YOUR TASK
Generate exactly 3 practical questions that help gather additional
evidence about how the motivation profile appears in real situations.

Cover different themes, such as:
- what provides energy and engagement
- what happens when an important condition is absent
- how prominent and less central drivers appear in practice
- tensions between motivational preferences
- expectations or working conditions that should be clarified
- sustainable motivation over time

ASSESSMENT PRINCIPLES
- Motivation results describe likely sources of energy, engagement
  and preference.
- They do not measure ability, personality, competence, experience,
  values, integrity or likely job performance.
- Lower results are not weaknesses or poor motivation in general.
- Higher results do not guarantee performance.
- Treat results as indicators and hypotheses rather than facts.
- Do not make a suitability decision or diagnose the candidate.
- Do not include raw scores.
- Do not invent candidate experience or process context.
- Do not lead the respondent towards a preferred answer.

QUESTION RULES
Each question must:
- be open and practical
- invite a concrete example or reflection
- relate to available motivation evidence
- be understandable without psychometric knowledge
- explore a different theme
- avoid presenting a result as confirmed fact

For recruitment, use interview wording.

For development, onboarding, leadership or team purposes, use
reflection or discussion wording where appropriate.

For every question return:
- question: the complete question
- why: the specific motivation hypothesis it helps explore
- listen_for: concrete evidence to look for in the answer

The listen_for field should mention cues such as:
- conditions that increased or reduced energy
- responses when a driver was absent
- priorities, choices and trade-offs
- self-awareness about motivational needs
- strategies used to maintain engagement
- observable outcomes
- reflection and learning

Do not use vague phrases such as:
- "listen for motivation"
- "look for a good fit"
- "consider whether they are engaged"

Also return a short context_note explaining:
- that a motivation assessment was used
- whether additional process context was available
- that the questions gather supporting evidence

OUTPUT FORMAT
Return exactly one JSON object.

Do not use Markdown.
Do not use code fences.
Do not add any other text.

Use this exact structure:

{{
  "title": "Motivation questions",
  "label": "AI-supported questions",
  "questions": [
    {{
      "question": "Question one",
      "why": "Why this question is useful",
      "listen_for": "Concrete evidence to look for"
    }},
    {{
      "question": "Question two",
      "why": "Why this question is useful",
      "listen_for": "Concrete evidence to look for"
    }},
    {{
      "question": "Question three",
      "why": "Why this question is useful",
      "listen_for": "Concrete evidence to look for"
    }}
  ],
  "context_note": "Brief explanation of evidence and context used."
}}
""".strip()


def create_empty_motivation_questions(
    owner,
) -> dict[str, Any]:
    """
    Return the initial motivation questions structure.
    """

    return {
        "title": "Motivation questions",
        "label": "AI-supported questions",
        "questions": [],
        "context_note": "",
    }


def _normalise_questions(
    value: Any,
) -> list[dict[str, str]]:
    """
    Return up to three complete question objects.
    """

    if not isinstance(
        value,
        list,
    ):
        return []

    questions = []

    for item in value[:3]:
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

        if not (
            question
            and why
            and listen_for
        ):
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

    if len(questions) != 3:
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
) -> Iterable[dict[str, Any]]:
    """
    Generate motivation questions independently from
    the motivation interpretation.
    """

    if not motivation_results:
        raise ValueError(
            "No motivation assessment results are available."
        )

    client = get_openai_client()

    prompt = build_motivation_questions_prompt(
        owner=owner,
        motivation_results=motivation_results,
    )

    system_message = (
        "You are a careful workplace motivation assessment "
        "consultant. Treat results as indicators rather than "
        "facts, never invent context and return valid JSON."
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
            "three valid motivation questions."
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
):
    """
    Save motivation questions independently from
    the motivation interpretation.
    """

    questions = (
        _normalise_questions(
            result.get("questions")
        )
    )

    if len(questions) != 3:
        raise ValueError(
            "The AI response did not contain "
            "three valid motivation questions."
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