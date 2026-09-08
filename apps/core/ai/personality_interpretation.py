from __future__ import annotations

import json
import math
from typing import Any, Iterable

from django.utils import timezone

from .openai_client import (
    get_openai_client,
    get_chat_model,
)

from .prompt_templates import (
    get_ai_prompt_instructions,
    get_ai_feature_prompt_instructions,
)

from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)

from .personality_questions import (
    build_personality_evidence_text,
)
from .motivation_interpretation import (
    MOTIVATION_DEFINITIONS,
    build_motivation_evidence_text,
    extract_motivation_results,
)
from .personality_motivation_interaction_policy import (
    PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_EN,
    PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_SV,
)
from .language import (
    get_ai_language_instruction,
    get_ai_system_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)


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
            "motivation_interaction": (
                "En kort förklaring av hur personlighetspreferenser "
                "kan samspela med kandidatens motivationsfaktorer."
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
        "motivation_interaction": (
            "A concise explanation of how personality preferences may "
            "interact with the candidate's motivation factors."
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


def _normalise_motivation_score(value: Any) -> int | float | None:
    if value is None:
        return None

    try:
        score = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(score):
        return None

    score = max(1.0, min(5.0, score))

    return int(score) if score.is_integer() else score


def build_motivation_results_for_personality_owner(
    owner,
) -> list[dict[str, Any]]:
    """
    Build motivation evidence for the personality interaction insight.

    Active candidates use the existing Sova extraction helper. Historical
    candidates use their normalized imported profile so the feature behaves
    consistently in both candidate views.
    """

    process = owner.process

    if not getattr(process, "is_historical", False):
        return extract_motivation_results(owner)

    # Keep the processes service import lazy so the core AI module does not
    # introduce a startup import cycle through process views/models.
    from apps.processes.services.candidate_profile import (
        build_historical_candidate_profile,
    )

    profile = build_historical_candidate_profile(owner)
    motivation_competencies = (
        profile.get("motivation_competencies")
        or []
    )

    results_by_name: dict[str, dict[str, Any]] = {}

    for item in motivation_competencies:
        name = str(
            item.get("competency")
            or item.get("name")
            or ""
        ).strip()

        if not name:
            continue

        # Keep the original STIVE value for the personality ×
        # motivation interaction. Rounded values are only a fallback.
        raw_score = item.get("stive")

        if raw_score is None:
            raw_score = item.get("stive_rounded")

        if raw_score is None:
            raw_score = item.get("score")

        score = _normalise_motivation_score(raw_score)

        if score is None:
            continue

        name_key = name.casefold()

        results_by_name[name_key] = {
            "name": name,
            "score": score,
            "definition": MOTIVATION_DEFINITIONS.get(
                name_key,
                "",
            ),
        }

    return list(results_by_name.values())


def build_personality_interpretation_prompt(
    owner,
    personality_results: list[dict[str, Any]],
    *,
    motivation_results: list[dict[str, Any]] | None = None,
    language_code: str = "en",
) -> str:
    """
    Build Talena's personality interpretation prompt.

    Administrator guidance controls all non-technical AI behaviour.

    Talena protects the technical input/output contract and the evidence
    boundary required for the focused personality × motivation insight.
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

    interplay_instructions = get_ai_feature_prompt_instructions(
        key="personality_trait_interplay",
        language=language_code,
    )

    motivation_interaction_default = (
        PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_SV
        if language_code == "sv"
        else PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_EN
    )

    motivation_interaction_instructions = get_ai_feature_prompt_instructions(
        key="personality_motivation_interaction",
        language=language_code,
        default=motivation_interaction_default,
    )

    supportive_patterns_instructions = get_ai_feature_prompt_instructions(
        key="personality_supportive_patterns",
        language=language_code,
    )

    areas_to_explore_instructions = get_ai_feature_prompt_instructions(
        key="personality_areas_to_explore",
        language=language_code,
    )

    shared_context = build_shared_ai_context(
        owner
    )

    evidence_text = build_personality_evidence_text(
        personality_results
    )

    if motivation_results is None:
        motivation_results = build_motivation_results_for_personality_owner(
            owner
        )

    motivation_evidence_text = build_motivation_evidence_text(
        motivation_results
    )

    has_motivation_results = bool(motivation_results)

    motivation_availability_instruction = (
        "Motivation assessment data is available. Return a grounded "
        "motivation_interaction insight."
        if has_motivation_results
        else (
            "No motivation assessment data is available. Preserve the "
            "motivation_interaction event but return an empty text value."
        )
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

MOTIVATION ASSESSMENT DATA
{motivation_evidence_text}

MOTIVATION DATA AVAILABILITY
{motivation_availability_instruction}


ADMINISTRATOR AI GUIDANCE


OVERALL PERSONALITY INTERPRETATION GUIDANCE

The following administrator guidance applies only to the
overall personality interpretation returned through
interpretation_delta events.

Do not use this guidance to determine the substantive content of
profile_dynamics, motivation_interaction, supportive_patterns or
areas_to_explore.

If this guidance contains older instructions relating to those
sections, the dedicated section guidance below takes precedence.

{admin_instructions}


COMBINED TRAIT DYNAMICS GUIDANCE

The following administrator guidance applies only to the
profile_dynamics event.

It controls which trait combinations are meaningful to describe,
how traits may interact, possible tensions, balancing or reinforcing
patterns and how those combinations should be communicated.

{interplay_instructions}


PERSONALITY AND MOTIVATION INTERACTION GUIDANCE

The following administrator guidance applies only to the
motivation_interaction event.

{motivation_interaction_instructions}

PROTECTED EVIDENCE BOUNDARY FOR THIS SECTION

The substantive content of motivation_interaction must be grounded only in
the supplied PERSONALITY ASSESSMENT DATA and MOTIVATION ASSESSMENT DATA.

Do not use PROCESS CONTEXT, process purpose, assumed role requirements,
candidate history or outside knowledge to infer an interaction for this
section. Do not invent missing assessment results.

Keep personality preference and motivational importance conceptually
distinct. A low motivation score must not be interpreted as low ability,
low competence, poor performance or absence of the quality named by a factor.

If no motivation assessment data is available, return an empty
motivation_interaction text value regardless of administrator guidance.


POTENTIALLY SUPPORTIVE PATTERNS GUIDANCE

The following administrator guidance applies only to the
supportive_patterns event.

Do not use it to change the overall interpretation,
profile dynamics, motivation interaction or areas to explore.

{supportive_patterns_instructions}


WHAT TO EXPLORE OR VALIDATE GUIDANCE

The following administrator guidance applies only to the
areas_to_explore event.

Do not use it to change the overall interpretation,
profile dynamics, motivation interaction or supportive patterns.

{areas_to_explore_instructions}


SECTION ISOLATION

Treat each dedicated section guidance as authoritative for its
corresponding event.

Instructions for one section must not change the substantive
content, number of items or emphasis of another section.

Global Talena administrator guidance still applies across all sections.

Do not allow administrator guidance to change Talena's technical
event structure, required JSON fields, evidence boundary or streaming format.


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


4. MOTIVATION INTERACTION

Return exactly one motivation_interaction event.

When motivation assessment data is available, return the focused combined
insight described above:

{{"type":"motivation_interaction","text":"{examples["motivation_interaction"]}"}}

When motivation assessment data is not available, return exactly:

{{"type":"motivation_interaction","text":""}}


5. SUPPORTIVE PATTERNS

Return one supportive_patterns event.

The items array may contain the number of items requested by the
administrator guidance:

{{"type":"supportive_patterns","items":["{examples["support"][0]}","{examples["support"][1]}"]}}


6. AREAS TO EXPLORE

Return one areas_to_explore event.

The items array may contain the number of items requested by the
administrator guidance:

{{"type":"areas_to_explore","items":["{examples["explore"][0]}","{examples["explore"][1]}"]}}


7. CONTEXT NOTE

Return one context_note event:

{{"type":"context_note","text":"{examples["context"]}"}}

If administrator guidance does not require substantive context-note
content, preserve the event and return an empty text value.


8. DONE

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
        "motivation_interaction": "",
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

    elif event_type == "motivation_interaction":
        interpretation["motivation_interaction"] = str(
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

    motivation_results = build_motivation_results_for_personality_owner(
        owner
    )

    client = get_openai_client()

    prompt = build_personality_interpretation_prompt(
        owner=owner,
        personality_results=personality_results,
        motivation_results=motivation_results,
        language_code=language_code,
    )

    system_language_instruction = (
        get_ai_system_language_instruction(
            language_code,
            owner=owner,
        )
    )

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI component inside Talena. "
                    "Follow the administrator-provided AI guidance for "
                    "all non-technical personality analysis, personality-"
                    "motivation interaction and communication decisions. "
                    "Follow Talena's technical output contract exactly, "
                    "including required JSON structure, field names, "
                    "event types, evidence boundaries and streaming format. "
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

    interpretation["motivation_interaction"] = (
        interpretation.get("motivation_interaction")
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
