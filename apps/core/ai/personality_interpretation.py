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

from .personality_questions import (
    build_personality_evidence_text,
)
from .language import (
    get_ai_language_instruction,
    get_ai_system_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)

from .prompt_templates import get_ai_prompt_instructions

def _personality_interpretation_examples(
    language_code: str,
) -> dict[str, Any]:
    if normalize_ai_language(language_code) == "sv":
        return {
            "title": "Personlighetstolkning",
            "label": "AI-stödd tolkning",
            "first": "Första delen av tolkningen. ",
            "next": "Nästa del av tolkningen. ",
            "dynamics": (
                "En praktisk förklaring av hur viktiga "
                "personlighetspreferenser kan samverka."
            ),
            "support": [
                "Första potentiellt stödjande mönstret",
                "Andra potentiellt stödjande mönstret",
                "Tredje potentiellt stödjande mönstret",
            ],
            "explore": [
                "Första området att utforska",
                "Andra området att utforska",
                "Tredje området att utforska",
            ],
            "context": (
                "Kort förklaring av underlaget, kontexten "
                "och tolkningens begränsningar."
            ),
        }

    return {
        "title": "Personality interpretation",
        "label": "AI-supported interpretation",
        "first": "First part of the interpretation. ",
        "next": "Next part of the interpretation. ",
        "dynamics": (
            "A practical explanation of how important personality "
            "preferences may work together."
        ),
        "support": [
            "Pattern one",
            "Pattern two",
            "Pattern three",
        ],
        "explore": [
            "Area one",
            "Area two",
            "Area three",
        ],
        "context": (
            "Brief explanation of the evidence, context and limitations."
        ),
    }


def build_personality_interpretation_prompt(
    owner,
    personality_results: list[dict[str, Any]],
    *,
    language_code: str = "en",
) -> str:
    """
    Build Talena's personality interpretation prompt.

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
        key="personality_interpretation",
        language=language_code,
    )

    shared_context = build_shared_ai_context(
        owner
    )

    evidence_text = build_personality_evidence_text(
        personality_results
    )

    examples = _personality_interpretation_examples(
        language_code
    )

    return f"""
TALENA INPUT DATA

CANDIDATE
Name: {shared_context["candidate_name"]}

SELECTED PROCESS PURPOSE
Purpose: {shared_context["purpose_label"]}

PROCESS CONTEXT
{shared_context["context_text"] or "No additional process context supplied."}

PERSONALITY ASSESSMENT DATA
{evidence_text}


ADMINISTRATOR AI GUIDANCE

The following guidance is controlled by Talena administrators.

It controls all non-technical decisions about personality
interpretation, STEN interpretation, assessment principles,
evidence boundaries, reasoning, trait combinations, tone,
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

Return one meta event using these exact field names:

{{"type":"meta","title":"{examples["title"]}","label":"{examples["label"]}"}}

Administrator guidance may influence the user-facing title and label
text, but the fields type, title and label must remain present.


2. INTERPRETATION CONTENT

Return the overall personality interpretation using one or more
interpretation_delta events:

{{"type":"interpretation_delta","text":"{examples["first"]}"}}

{{"type":"interpretation_delta","text":"{examples["next"]}"}}


3. PROFILE DYNAMICS

Return one profile_dynamics event:

{{"type":"profile_dynamics","text":"{examples["dynamics"]}"}}

If the administrator guidance does not require substantive content
for this section, preserve the event and return an empty text value.


4. SUPPORTIVE PATTERNS

Return one supportive_patterns event.

The items array may contain the number of items requested by the
administrator guidance:

{{"type":"supportive_patterns","items":["{examples["support"][0]}","{examples["support"][1]}"]}}


5. AREAS TO EXPLORE

Return one areas_to_explore event.

The items array may contain the number of items requested by the
administrator guidance:

{{"type":"areas_to_explore","items":["{examples["explore"][0]}","{examples["explore"][1]}"]}}


6. CONTEXT NOTE

Return one context_note event:

{{"type":"context_note","text":"{examples["context"]}"}}

If administrator guidance does not require substantive context-note
content, preserve the event and return an empty text value.


7. DONE

Finish with:

{{"type":"done"}}
""".strip()


def create_empty_personality_interpretation(
    owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
    examples = _personality_interpretation_examples(language_code)

    return {
        "title": examples["title"],
        "label": examples["label"],
        "interpretation": "",
        "profile_dynamics": "",
        "supportive_patterns": [],
        "areas_to_explore": [],
        "context_note": "",
    }

def apply_personality_interpretation_event(
    interpretation: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one streamed event to the complete interpretation.
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

    elif event_type == "profile_dynamics":
        interpretation["profile_dynamics"] = str(
            event.get("text")
            or ""
        ).strip()

    elif event_type == "supportive_patterns":
        items = event.get("items")

        if isinstance(items, list):
            interpretation["supportive_patterns"] = [
                str(item).strip()
                for item in items
                if str(item).strip()
            ]

    elif event_type == "areas_to_explore":
        items = event.get("items")

        if isinstance(items, list):
            interpretation["areas_to_explore"] = [
                str(item).strip()
                for item in items
                if str(item).strip()
            ]

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

def stream_personality_interpretation(
    *,
    owner,
    personality_results: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
    """
    Stream personality interpretation events from OpenAI.
    """

    if not personality_results:
        raise ValueError(
            "No personality assessment results are available."
        )

    language_code = normalize_ai_language(language_code)

    client = get_openai_client()

    prompt = build_personality_interpretation_prompt(
        owner=owner,
        personality_results=personality_results,
        language_code=language_code,
    )

    system_language_instruction = (
        get_ai_system_language_instruction(language_code)
    )

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI component inside Talena. "
                    "Follow the administrator-provided AI guidance for "
                    "all non-technical personality analysis, interpretation "
                    "and communication decisions. "
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

def save_personality_interpretation(
    *,
    owner,
    interpretation: dict[str, Any],
    language_code: str = "en",
):
    """
    Save a completed personality interpretation and its language metadata.
    """

    language_code = normalize_ai_language(language_code)

    interpretation["interpretation"] = (
        interpretation.get("interpretation")
        or ""
    ).strip()

    interpretation["profile_dynamics"] = (
        interpretation.get("profile_dynamics")
        or ""
    ).strip()

    interpretation["context_note"] = (
        interpretation.get("context_note")
        or ""
    ).strip()

    supportive_patterns = interpretation.get(
        "supportive_patterns"
    )

    if not isinstance(supportive_patterns, list):
        supportive_patterns = []

    interpretation["supportive_patterns"] = [
        str(item).strip()
        for item in supportive_patterns
        if str(item).strip()
    ]

    areas_to_explore = interpretation.get(
        "areas_to_explore"
    )

    if not isinstance(areas_to_explore, list):
        areas_to_explore = []

    interpretation["areas_to_explore"] = [
        str(item).strip()
        for item in areas_to_explore
        if str(item).strip()
    ]

    interpretation["_language"] = language_code

    set_ai_content_language(
        owner,
        "personality_interpretation",
        language_code,
    )

    owner.ai_personality_interpretation = (
        interpretation
    )

    owner.ai_personality_interpretation_status = (
        "completed"
    )

    owner.ai_personality_interpretation_generated_at = (
        timezone.now()
    )

    owner.ai_personality_interpretation_purpose = (
        get_process_purpose_key(
            owner.process
        )
    )

    update_fields = [
        "ai_personality_interpretation",
        "ai_personality_interpretation_status",
        "ai_personality_interpretation_generated_at",
        "ai_personality_interpretation_purpose",
    ]

    if hasattr(owner, "ai_content_languages"):
        update_fields.append(
            "ai_content_languages"
        )

    owner.save(
        update_fields=update_fields
    )