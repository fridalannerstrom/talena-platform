from __future__ import annotations

from .candidate_name_privacy import redact_candidate_name

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

from .prompt_templates import (
    get_ai_prompt_instructions,
    get_ai_feature_prompt_instructions,
)



EXCLUDED_PERSONALITY_COMPETENCIES = {
    "social desirability",
    "fillers",
    "reliability",
    "profile spread",
    "ratings spread",
}

QUESTION_PARENT_TRAIT_KEYS = {
    "cooperative",
    "empathy",
    "supporting",
    "connecting",
    "dynamic",
    "influential",

    # Sova/report library may use either wording.
    "goal focused",
    "achievement striving",

    "structured",
    "analytical",
    "complex thinking",
    "creativity",
    "adaptability",
    "straightforward",
    "status avoidance",
    "modesty",
    "resilience",
    "emotional control",
    "independence",
}


def _normalise_trait_key(
    value: Any,
) -> str:
    """
    Normalise trait names so differences such as
    hyphens, underscores and casing do not matter.
    """

    text = str(
        value
        or ""
    ).strip().casefold()

    for character in (
        "_",
        "-",
        "–",
        "—",
        "/",
    ):
        text = text.replace(
            character,
            " ",
        )

    return " ".join(
        text.split()
    )



def _normalise_name(value: Any) -> str:
    return str(value or "").strip()


def _normalise_sten(value: Any) -> int | None:
    if value is None:
        return None

    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return None

    return max(1, min(10, score))


def extract_personality_results(
    invitation,
) -> list[dict[str, Any]]:
    """
    Extract personality traits from the candidate's Sova activities.

    Response-style competencies are excluded because they are handled
    separately in the Personality Profile.
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

        looks_like_personality = any(
            keyword in activity_name_lower
            for keyword in (
                "personality",
                "personlighet",
                "personality profile",
            )
        )

        if not looks_like_personality:
            continue

        competencies = (
            activity.get("competencies")
            or []
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

            if (
                competency_key
                in EXCLUDED_PERSONALITY_COMPETENCIES
            ):
                continue

            sten = _normalise_sten(
                competency.get("sten_rounded")
            )

            if sten is None:
                sten = _normalise_sten(
                    competency.get("sten")
                )

            if sten is None:
                continue

            results_by_name[competency_key] = {
                "name": competency_name,
                "sten": sten,
            }

    return list(
        results_by_name.values()
    )

def extract_personality_question_traits(
    invitation,
) -> list[dict[str, Any]]:
    """
    Return only the 18 parent personality traits that
    are available in the Trait Profile.

    Indicators, response styles and other personality
    competencies are excluded from question selection.
    """

    all_results = (
        extract_personality_results(
            invitation
        )
    )

    return [
        result
        for result in all_results
        if _normalise_trait_key(
            result.get("name")
        ) in QUESTION_PARENT_TRAIT_KEYS
    ]


def build_personality_evidence_text(
    results: list[dict[str, Any]],
) -> str:
    if not results:
        return (
            "No personality trait results are available."
        )

    sorted_results = sorted(
        results,
        key=lambda item: item["name"].lower(),
    )

    lines = []

    for result in sorted_results:
        lines.append(
            f"- {result['name']}: "
            f"STEN {result['sten']} of 10"
        )

    return "\n".join(lines)


def normalise_selected_traits(
    *,
    selected_traits: list[Any],
    available_results: list[dict[str, Any]],
) -> list[str]:
    """
    Keep only selected traits that exist in the personality results.
    """

    available_lookup = {
        item["name"].strip().lower(): item["name"]
        for item in available_results
    }

    normalised = []
    seen = set()

    for raw_trait in selected_traits or []:
        trait_key = str(
            raw_trait or ""
        ).strip().lower()

        if (
            not trait_key
            or trait_key not in available_lookup
            or trait_key in seen
        ):
            continue

        seen.add(trait_key)

        normalised.append(
            available_lookup[trait_key]
        )

    return normalised


def get_personality_question_count(
    selected_traits: list[str],
) -> int:
    """
    Return between three and six questions.

    Generate at least as many questions as there are
    selected traits, with three as the minimum.
    """

    return max(
        3,
        min(
            6,
            len(selected_traits or []),
        ),
    )


def personality_questions_cover_all_traits(
    questions: list[dict[str, Any]],
    selected_traits: list[str],
) -> bool:
    """
    Check that every selected trait is represented
    in at least one question.
    """

    required_traits = {
        str(trait).strip().lower()
        for trait in selected_traits or []
        if str(trait).strip()
    }

    covered_traits = {
        str(trait).strip().lower()
        for question in questions or []
        for trait in question.get("traits", [])
        if str(trait).strip()
    }

    return required_traits.issubset(
        covered_traits
    )

def build_personality_questions_prompt(
    invitation,
    personality_results: list[dict[str, Any]],
    *,
    language_code: str = "en",
) -> str:
    """
    Build Talena's personality questions prompt.

    Administrator guidance controls all non-technical AI behaviour.

    Talena protects application data, explicit user trait selections
    and the technical output contract required by the platform.
    """

    language_code = normalize_ai_language(
        language_code
    )

    language_instruction = get_ai_language_instruction(
        language_code
    )

    admin_instructions = get_ai_prompt_instructions(
        key="personality_questions",
        language=language_code,
    )

    shared_context = build_shared_ai_context(
        invitation
    )

    candidate = shared_context["candidate"]

    evidence_text = build_personality_evidence_text(
        personality_results
    )

    selected_traits = normalise_selected_traits(
        selected_traits=(
            invitation.selected_personality_traits
            or []
        ),
        available_results=personality_results,
    )

    selected_traits_text = (
        "\n".join(
            f"- {trait}"
            for trait in selected_traits
        )
        if selected_traits
        else "No explicit user-selected traits."
    )

    selection_mode = (
        "USER_SELECTED"
        if selected_traits
        else "AI_SELECTION"
    )

    trait_selection_instructions = ""

    if selection_mode == "AI_SELECTION":
        trait_selection_instructions = (
            get_ai_feature_prompt_instructions(
                key="personality_trait_selection",
                language=language_code,
            )
        )

    available_trait_names = "\n".join(
        f"- {item['name']}"
        for item in personality_results
        if item.get("name")
    )

    return f"""
TALENA INPUT DATA

CANDIDATE
Reference: CANDIDATE_A

SELECTED PROCESS PURPOSE
Purpose: {shared_context["purpose_label"]}

PROCESS CONTEXT
{shared_context["context_text"] or "No additional process context supplied."}

PERSONALITY ASSESSMENT DATA
{evidence_text}

AVAILABLE TECHNICAL TRAIT NAMES
{available_trait_names}

TRAIT SELECTION MODE
{selection_mode}

EXPLICIT USER-SELECTED TRAITS
{selected_traits_text}

PERSONALITY TRAIT SELECTION GUIDANCE

This guidance applies only when TRAIT SELECTION MODE is AI_SELECTION.

When AI_SELECTION is active, use the following administrator guidance
to decide which available personality traits should be selected:

{trait_selection_instructions}

When TRAIT SELECTION MODE is USER_SELECTED, do not use this guidance
to replace, add or remove personality traits. The user's explicit
selection must be preserved exactly.

This guidance controls trait selection only.

It does not control how the resulting personality questions,
why explanations or listen_for guidance are written.

If the trait-selection guidance conflicts with the general personality
questions guidance about which traits should be selected, the dedicated
trait-selection guidance takes precedence.

ADMINISTRATOR AI GUIDANCE

The following guidance is controlled by Talena administrators.

It controls all non-technical decisions about question content,
personality interpretation, STEN interpretation, question count,
trait coverage, interviewing approach, reasoning, evidence boundaries,
tone, caution and communication.

{admin_instructions}


TALENA INPUT CONTRACT

The following requirements preserve explicit application data.

If TRAIT SELECTION MODE is USER_SELECTED:

- the selected_traits event must contain exactly the explicit
  user-selected traits supplied above
- do not replace the user's explicit selection with other traits

If TRAIT SELECTION MODE is AI_SELECTION:

- Talena must select traits according to the dedicated personality
  trait-selection administrator guidance
- selected trait names must come from AVAILABLE TECHNICAL TRAIT NAMES
- the application currently supports a maximum of 6 selected traits

Trait names used in technical name and traits fields must exactly
match the supplied technical trait names.


TALENA TECHNICAL OUTPUT CONTRACT

The following requirements exist only so Talena can process,
save and display the generated response.

Administrator guidance may control:

- question content
- number of questions
- how selected traits are explored
- whether every selected trait needs question coverage
- substantive content of why and listen_for
- reasoning and communication style

Administrator guidance must not change the required event names,
JSON field names or NDJSON structure.


OUTPUT LANGUAGE

{language_instruction}

Translate user-facing content to the configured language.

Keep personality trait names inside technical name and traits fields
exactly as supplied by Talena.


STREAMING FORMAT

Return newline-delimited JSON, also called NDJSON.

Every JSON object must appear on one single line.

Do not use Markdown.

Do not use code fences.

Do not add text outside the JSON objects.


REQUIRED EVENT STRUCTURE


1. META EVENT

Return one meta event:

{{"type":"meta","title":"Personality questions","label":"AI-supported questions"}}


2. SUGGESTED TRAITS

Return one suggested_traits event.

Every item must use these exact fields:

- name
- reason

The application supports up to 6 suggested trait objects.

Example:

{{"type":"suggested_traits","items":[{{"name":"Trait name","reason":"Reason for exploring the trait"}}]}}


3. SELECTED TRAITS

Return one selected_traits event:

{{"type":"selected_traits","items":["Trait name"]}}

When the user has explicitly selected traits, this array must preserve
that application selection exactly.


4. QUESTIONS

Return one questions event.

The administrator guidance determines the number of question objects.

The example below illustrates the JSON shape only. Its number of sample items
does not set the question count; follow Talena's fixed question-count
instruction appended to this prompt.

Every question object must contain these exact fields:

- question
- traits
- why
- listen_for

The traits field must be an array.

Trait names inside traits must match names from the selected_traits
event.

If administrator guidance does not require substantive why,
listen_for or trait tagging, preserve those technical fields using
an empty string or empty array as appropriate.

Example:

{{"type":"questions","items":[{{"question":"Question text","traits":["Trait name"],"why":"Why it matters","listen_for":"What to listen for"}}]}}


5. CONTEXT NOTE

Return one context_note event:

{{"type":"context_note","text":"Brief explanation of evidence and context used."}}


6. DONE

Finish with:

{{"type":"done"}}
""".strip()


def create_empty_personality_questions(
    owner,
) -> dict[str, Any]:
    return {
        "title": "Personality questions",
        "label": "AI-supported questions",
        "suggested_traits": [],
        "selected_traits": [],
        "questions": [],
        "context_note": "",
    }

def _normalise_personality_questions(
    items: Any,
    selected_traits: list[str],
) -> list[dict[str, Any]]:
    """
    Return technically valid personality question objects.

    Question content is controlled by administrator guidance.
    """

    if not isinstance(items, list):
        return []

    from .personality_ai_evidence import canonical_parent_trait_name

    trait_lookup = {}
    canonical_trait_lookup = {}

    for raw_trait in selected_traits or []:
        selected_trait = str(raw_trait or "").strip()
        if not selected_trait:
            continue

        trait_lookup[_normalise_trait_key(selected_trait)] = selected_trait
        canonical_name = canonical_parent_trait_name(selected_trait)
        if canonical_name:
            canonical_trait_lookup[
                _normalise_trait_key(canonical_name)
            ] = selected_trait

    questions = []

    for item in items:
        if not isinstance(item, dict):
            continue

        question = str(
            item.get("question")
            or ""
        ).strip()

        if not question:
            continue

        why = str(
            item.get("why")
            or ""
        ).strip()

        listen_for = str(
            item.get("listen_for")
            or ""
        ).strip()

        raw_traits = item.get("traits")
        traits = []

        if isinstance(raw_traits, list):
            for raw_trait in raw_traits:
                raw_trait_name = str(raw_trait or "").strip()
                trait_key = _normalise_trait_key(raw_trait_name)

                canonical_trait = trait_lookup.get(trait_key)
                if not canonical_trait:
                    canonical_name = canonical_parent_trait_name(raw_trait_name)
                    if canonical_name:
                        canonical_trait = canonical_trait_lookup.get(
                            _normalise_trait_key(canonical_name)
                        )

                if (
                    canonical_trait
                    and canonical_trait not in traits
                ):
                    traits.append(
                        canonical_trait
                    )

        questions.append({
            "question": question,
            "traits": traits,
            "why": why,
            "listen_for": listen_for,
        })

    return questions

def apply_personality_questions_event(
    result: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one streamed event to the complete saved result.
    """

    event_type = event.get("type")

    if event_type == "meta":
        result["title"] = str(
            event.get("title")
            or result["title"]
        ).strip()

        result["label"] = str(
            event.get("label")
            or result["label"]
        ).strip()

    elif event_type == "suggested_traits":
        items = event.get("items")

        if isinstance(items, list):
            normalised_traits = []

            for item in items[:6]:
                if not isinstance(item, dict):
                    continue

                name = str(
                    item.get("name")
                    or ""
                ).strip()

                if not name:
                    continue

                normalised_traits.append({
                    "name": name,
                    "reason": str(
                        item.get("reason")
                        or ""
                    ).strip(),
                })

            result["suggested_traits"] = (
                normalised_traits
            )

    elif event_type == "selected_traits":
        items = event.get("items")

        if isinstance(items, list):
            result["selected_traits"] = [
                str(item).strip()
                for item in items[:6]
                if str(item).strip()
            ]

    elif event_type == "questions":
        result["questions"] = (
            _normalise_personality_questions(
                event.get("items"),
                result.get("selected_traits") or [],
            )
        )

    elif event_type == "context_note":
        result["context_note"] = str(
            event.get("text")
            or ""
        ).strip()

    return result


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

def _build_personality_questions_repair_prompt(
    *,
    owner,
    personality_results: list[dict[str, Any]],
    selected_traits: list[str],
) -> str:
    """
    Build a focused prompt that repairs only the questions event.
    """

    shared_context = build_shared_ai_context(
        owner
    )

    evidence_text = (
        build_personality_evidence_text(
            personality_results
        )
    )

    selected_traits_text = "\n".join(
        f"- {trait}"
        for trait in selected_traits
    )

    question_count = (
        get_personality_question_count(
            selected_traits
        )
    )

    return f"""
You are repairing a missing or malformed personality questions event
for Talena.

CANDIDATE
Reference: CANDIDATE_A

SELECTED PROCESS PURPOSE
Purpose: {shared_context["purpose_label"]}

PROCESS CONTEXT
{shared_context["context_text"]}

AVAILABLE PERSONALITY RESULTS
{evidence_text}

SELECTED PERSONALITY TRAITS
{selected_traits_text}

YOUR TASK
Return exactly {question_count} complete questions based on the
selected traits.

Every selected trait must appear in the traits list of at least one
question.

Prefer combining two meaningfully related traits in a question when
that creates a coherent behavioural theme. Do not combine unrelated
traits merely to reduce the number of questions.

Each question must:
- be open and behavioural or reflective
- ask for a concrete example, approach or learning
- use one or more of the selected traits
- be relevant to the selected purpose
- use supplied process context when available
- avoid leading the respondent
- avoid mentioning raw assessment scores
- treat personality results as hypotheses rather than facts
- collectively cover every selected trait at least once
- normally use one or two selected traits per question

Every question object must contain:
- question
- traits
- why
- listen_for

The traits property must be a list containing only names from the
selected personality traits above.

OUTPUT FORMAT
Return exactly one JSON object on one single line.
The sample below illustrates the JSON shape only; return exactly
{question_count} complete questions.
Do not use Markdown.
Do not use code fences.
Do not add any other text.

{{"type":"questions","items":[{{"question":"Question text","traits":["Trait name"],"why":"Why it matters","listen_for":"What to listen for"}}]}}
""".strip()


def _parse_repaired_personality_questions(
    raw_content: str,
    selected_traits: list[str],
) -> dict[str, Any] | None:
    """
    Parse a repair response and verify all three questions.
    """

    text = str(
        raw_content
        or ""
    ).strip()

    if not text:
        return None

    if text.startswith("```"):
        text = "\n".join(
            line
            for line in text.splitlines()
            if not line.strip().startswith("```")
        ).strip()

    try:
        event = json.loads(text)
    except json.JSONDecodeError:
        event = None

        for line in text.splitlines():
            parsed_event = _parse_event_line(
                line
            )

            if parsed_event:
                event = parsed_event
                break

    if not isinstance(event, dict):
        return None

    if event.get("type") != "questions":
        return None

    questions = _normalise_personality_questions(
        event.get("items"),
        selected_traits,
    )

    if not questions:
        return None

    return {
        "type": "questions",
        "items": questions,
    }


def _build_safe_personality_questions_event(
    *,
    selected_traits: list[str],
    personality_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build deterministic fallback questions.

    Every selected trait is represented in at least
    one question.
    """

    traits = [
        str(trait).strip()
        for trait in selected_traits
        if str(trait).strip()
    ]

    if not traits:
        traits = [
            item["name"]
            for item in personality_results[:6]
            if item.get("name")
        ]

    if not traits:
        raise ValueError(
            "No personality traits are available "
            "for the questions."
        )

    question_count = (
        get_personality_question_count(
            traits
        )
    )

    templates = [
        {
            "question": (
                "Tell me about a situation where your usual way "
                "of approaching work was particularly effective. "
                "What did you do, and what was the outcome?"
            ),
            "why": (
                "This helps compare the assessment indication with "
                "a concrete example of workplace behaviour."
            ),
            "listen_for": (
                "Specific actions, situational context and evidence "
                "of how the person used their natural preferences."
            ),
        },
        {
            "question": (
                "Describe a situation where you needed to adjust "
                "your normal approach. What made the adjustment "
                "necessary, and what did you do?"
            ),
            "why": (
                "This explores how behavioural preferences may "
                "change across different situations."
            ),
            "listen_for": (
                "Self-awareness, deliberate adaptation and the "
                "effect of the surrounding context."
            ),
        },
        {
            "question": (
                "Tell me about a challenging situation involving "
                "other people. How did you decide what approach "
                "to take?"
            ),
            "why": (
                "This provides evidence about how preferences may "
                "influence collaboration and judgement."
            ),
            "listen_for": (
                "Perspective-taking, communication choices and "
                "the reasoning behind the person's actions."
            ),
        },
        {
            "question": (
                "What feedback have you received about your way "
                "of working, and what did you learn from it?"
            ),
            "why": (
                "This adds external behavioural evidence that may "
                "confirm or add nuance to the personality profile."
            ),
            "listen_for": (
                "Concrete feedback, reflection and changes made "
                "in response."
            ),
        },
        {
            "question": (
                "Describe a situation where you had to balance "
                "different priorities or expectations. How did "
                "you approach it?"
            ),
            "why": (
                "This explores how several behavioural preferences "
                "may interact in a practical situation."
            ),
            "listen_for": (
                "Prioritisation, trade-offs and awareness of how "
                "the situation affected the chosen approach."
            ),
        },
        {
            "question": (
                "Tell me about a situation that required you to "
                "work outside your preferred style. What was "
                "difficult, and what helped?"
            ),
            "why": (
                "This explores flexibility and the conditions that "
                "support effective behaviour."
            ),
            "listen_for": (
                "Adaptation, support needs, learning and awareness "
                "of personal preferences."
            ),
        },
    ]

    questions = []

    for index in range(question_count):
        primary_trait = traits[
            index % len(traits)
        ]

        question_traits = [
            primary_trait
        ]

                # Combine a neighbouring trait on alternating
        # questions when more than one trait exists.
        if (
            len(traits) > 1
            and index % 2 == 0
        ):
            secondary_trait = traits[
                (index + 1) % len(traits)
            ]

            if secondary_trait != primary_trait:
                question_traits.append(
                    secondary_trait
                )

        template = templates[
            index % len(templates)
        ]

        questions.append({
            "question": template["question"],
            "traits": question_traits,
            "why": template["why"],
            "listen_for": template["listen_for"],
        })

    return {
        "type": "questions",
        "items": questions,
    }


def _generate_repaired_personality_questions_event(
    *,
    owner,
    personality_results: list[dict[str, Any]],
    selected_traits: list[str],
) -> dict[str, Any]:
    """
    Make one focused repair request.

    Use deterministic questions if the repair response remains malformed.
    """

    try:
        client = get_openai_client()

        repair_prompt = redact_candidate_name(
            _build_personality_questions_repair_prompt(
                owner=owner,
                personality_results=personality_results,
                selected_traits=selected_traits,
            ),
            owner.candidate,
        )
        response = client.chat.completions.create(
            model=get_chat_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI component inside Talena. "
                        "Follow the administrator-provided AI guidance "
                        "for all non-technical question decisions. "
                        "Repair only the technical JSON structure and "
                        "field requirements requested by Talena. "
                        f"{get_ai_system_language_instruction(
                            _personality_questions_language.get(),
                            owner=owner,
                        )}"
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

        raw_content = (
            response.choices[0].message.content
            or ""
        )

        repaired_event = (
            _parse_repaired_personality_questions(
                raw_content,
                selected_traits,
            )
        )

        if repaired_event:
            return repaired_event

    except Exception:
        pass

    raise ValueError(
        "The AI response did not contain "
        "valid personality questions."
    )


def stream_personality_questions(
    *,
    owner,
    personality_results: list[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
    """
    Stream personality events and repair malformed questions
    before emitting the final done event.
    """

    if not personality_results:
        raise ValueError(
            "No personality assessment results are available."
        )

    client = get_openai_client()

    prompt = build_personality_questions_prompt(
        invitation=owner,
        personality_results=personality_results,
    )

    prompt = redact_candidate_name(prompt, owner.candidate)

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI component inside Talena. "
                    "Follow the administrator-provided AI guidance for "
                    "all non-technical personality question decisions. "
                    "Follow Talena's application input contract and "
                    "technical output contract exactly, including required "
                    "JSON field names, event types and streaming format. "
                    f"{get_ai_system_language_instruction(
                        _personality_questions_language.get(),
                        owner=owner,
                    )}"
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

    selected_traits = normalise_selected_traits(
        selected_traits=(
            owner.selected_personality_traits
            or []
        ),
        available_results=personality_results,
    )

    suggested_traits = []
    received_questions: list[
        dict[str, Any]
    ] = []

    def prepare_event(
        event: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        nonlocal selected_traits
        nonlocal suggested_traits
        nonlocal received_questions

        if not event:
            return None

        event_type = event.get("type")

        # Hold back done until validation and repair are complete.
        if event_type == "done":
            return None

        if event_type == "suggested_traits":
            items = event.get("items")

            raw_names = []

            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue

                    name = str(
                        item.get("name")
                        or ""
                    ).strip()

                    if name:
                        raw_names.append(name)

            suggested_traits = normalise_selected_traits(
                selected_traits=raw_names,
                available_results=personality_results,
            )

            return event

        if event_type == "selected_traits":
            cleaned_traits = normalise_selected_traits(
                selected_traits=(
                    event.get("items")
                    or []
                ),
                available_results=personality_results,
            )

            if not cleaned_traits:
                return None

            selected_traits = cleaned_traits

            return {
                "type": "selected_traits",
                "items": selected_traits,
            }

        if event_type == "questions":
            received_questions = (
                _normalise_personality_questions(
                    event.get("items"),
                    selected_traits,
                )
            )

            # Hold the questions until the final canonical
            # trait selection has been established.
            return None

        return event

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

            prepared_event = prepare_event(
                parsed_event
            )

            if prepared_event:
                yield prepared_event

    final_event = _parse_event_line(
        buffer
    )

    prepared_final_event = prepare_event(
        final_event
    )

    if prepared_final_event:
        yield prepared_final_event

    # Preserve explicit user selection when one exists.
    user_selected_traits = normalise_selected_traits(
        selected_traits=(
            owner.selected_personality_traits
            or []
        ),
        available_results=personality_results,
    )

    if user_selected_traits:
        selected_traits = user_selected_traits

    else:
        # No explicit user selection exists.
        #
        # Allow the AI/admin guidance to determine which available
        # traits should be used, while preserving Talena's technical
        # maximum of six selected traits.

        ai_selected_traits = normalise_selected_traits(
            selected_traits=selected_traits,
            available_results=personality_results,
        )[:6]

        if not ai_selected_traits:
            ai_selected_traits = normalise_selected_traits(
                selected_traits=suggested_traits,
                available_results=personality_results,
            )[:6]

        selected_traits = ai_selected_traits

        # Emit the final canonical selection.
        yield {
            "type": "selected_traits",
            "items": selected_traits,
        }

    questions_are_valid = bool(
        received_questions
    )

    if questions_are_valid:
        yield {
            "type": "questions",
            "items": received_questions,
        }

    else:
        yield (
            _generate_repaired_personality_questions_event(
                owner=owner,
                personality_results=personality_results,
                selected_traits=selected_traits,
            )
        )

    yield {
        "type": "done",
    }
    

def save_personality_questions(
    *,
    owner,
    result: dict[str, Any],
):
    """
    Save generated personality trait suggestions and questions.

    Automatically suggested traits are stored in the generated
    question result, while selected_personality_traits remains
    reserved for an explicit user selection.
    """

    owner.ai_personality_questions = result

    owner.ai_personality_questions_status = (
        "completed"
    )

    owner.ai_personality_questions_generated_at = (
        timezone.now()
    )

    owner.ai_personality_questions_purpose = (
        get_process_purpose_key(
            owner.process
        )
    )

    owner.save(
        update_fields=[
            "ai_personality_questions",
            "ai_personality_questions_status",
            "ai_personality_questions_generated_at",
            "ai_personality_questions_purpose",
        ]
    )

# Talena personality language batch 1
from contextvars import ContextVar as _ContextVar
from .language import (
    get_ai_language_instruction,
    get_ai_system_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)

_personality_questions_language = _ContextVar(
    "personality_questions_language",
    default="en",
)

_original_build_personality_questions_prompt = build_personality_questions_prompt
_original_build_personality_questions_repair_prompt = (
    _build_personality_questions_repair_prompt
)
_original_build_safe_personality_questions_event = (
    _build_safe_personality_questions_event
)
_original_create_empty_personality_questions = create_empty_personality_questions
_original_stream_personality_questions = stream_personality_questions
_original_save_personality_questions = save_personality_questions


def _question_examples(language_code: str) -> dict[str, str]:
    if normalize_ai_language(language_code) == "sv":
        return {
            "title": "Personlighetsfrågor",
            "label": "AI-stödda frågor",
            "reason": "Varför personlighetsdraget kan vara relevant att utforska",
            "q1": "Första frågan",
            "q2": "Andra frågan",
            "q3": "Tredje frågan",
            "why": "Varför frågan är relevant",
            "listen": "Vad du kan lyssna efter",
            "context": (
                "Kort förklaring av underlaget, kontexten "
                "och valet av personlighetsdrag."
            ),
        }
    return {
        "title": "Personality questions",
        "label": "AI-supported questions",
    }


def _localize_question_prompt(prompt: str, language_code: str) -> str:
    language_code = normalize_ai_language(language_code)
    prompt = prompt.replace(
        "- Write in professional, clear English.",
        get_ai_language_instruction(language_code),
        1,
    )

    if language_code != "sv":
        return prompt

    examples = _question_examples(language_code)
    replacements = {
        '"title":"Personality questions"': f'"title":"{examples["title"]}"',
        '"label":"AI-supported questions"': f'"label":"{examples["label"]}"',
        "Why this trait may be relevant": examples["reason"],
        "Question one": examples["q1"],
        "Question two": examples["q2"],
        "Question three": examples["q3"],
        "Why it matters": examples["why"],
        "What to listen for": examples["listen"],
        (
            "Brief explanation of the evidence, context and trait selection used."
        ): examples["context"],
    }
    for old, new in replacements.items():
        prompt = prompt.replace(old, new)

    return prompt


def build_personality_questions_prompt(
    invitation,
    personality_results: list[dict[str, Any]],
    *,
    language_code: str | None = None,
) -> str:
    language_code = normalize_ai_language(
        language_code or _personality_questions_language.get()
    )
    prompt = _original_build_personality_questions_prompt(
        invitation,
        personality_results,
        language_code=language_code,
    )
    prompt = _localize_question_prompt(prompt, language_code)
    prompt = prompt.replace(
        "LANGUAGE AND TONE\n",
        (
            "LANGUAGE AND TONE\n"
            "- Keep trait names in the technical name and traits fields "
            "exactly as supplied.\n"
        ),
        1,
    )
    return prompt


def _build_personality_questions_repair_prompt(
    *,
    owner,
    personality_results: list[dict[str, Any]],
    selected_traits: list[str],
) -> str:
    """
    Repair only the technical personality questions structure.

    Non-technical content remains controlled by administrator guidance.
    """

    shared_context = build_shared_ai_context(
        owner
    )

    evidence_text = build_personality_evidence_text(
        personality_results
    )

    admin_instructions = get_ai_prompt_instructions(
        key="personality_questions",
        language=_personality_questions_language.get(),
    )

    selected_traits_text = "\n".join(
        f"- {trait}"
        for trait in selected_traits
    ) or "No selected traits."

    return f"""
The previous personality questions response did not contain a
technically valid questions event.

CANDIDATE
Reference: CANDIDATE_A

SELECTED PROCESS PURPOSE
Purpose: {shared_context["purpose_label"]}

PROCESS CONTEXT
{shared_context["context_text"] or "No additional process context supplied."}

PERSONALITY ASSESSMENT DATA
{evidence_text}

SELECTED TRAITS
{selected_traits_text}


ADMINISTRATOR AI GUIDANCE

Follow this guidance for all non-technical question decisions:

{admin_instructions}


TECHNICAL REPAIR TASK

Return exactly one JSON object on one line.

Use this exact structure:

{{"type":"questions","items":[{{"question":"Question text","traits":["Trait name"],"why":"Why it matters","listen_for":"What to listen for"}}]}}

The administrator guidance determines the number and content of questions.

Every question object must contain these exact fields:

- question
- traits
- why
- listen_for

traits must be an array.

Trait names inside traits may only use the selected trait names supplied above.

why and listen_for may be empty strings if administrator guidance
does not require substantive content.

Do not use Markdown.
Do not use code fences.
Do not add explanatory text outside the JSON object.
""".strip()


_SAFE_SWEDISH = {
    "Tell me about a situation where your usual way of approaching work was particularly effective. What did you do, and what was the outcome?": (
        "Berätta om en situation där ditt vanliga sätt att ta dig an arbetet "
        "var särskilt effektivt. Vad gjorde du och vad blev resultatet?"
    ),
    "This helps compare the assessment indication with a concrete example of workplace behaviour.": (
        "Detta hjälper till att jämföra testindikationen med ett konkret "
        "exempel på beteende i arbetet."
    ),
    "Specific actions, situational context and evidence of how the person used their natural preferences.": (
        "Konkreta handlingar, situationens förutsättningar och hur personen "
        "använde sina naturliga preferenser."
    ),
    "Describe a situation where you needed to adjust your normal approach. What made the adjustment necessary, and what did you do?": (
        "Beskriv en situation där du behövde anpassa ditt vanliga arbetssätt. "
        "Vad gjorde anpassningen nödvändig och hur agerade du?"
    ),
    "This explores how behavioural preferences may change across different situations.": (
        "Detta utforskar hur beteendepreferenser kan förändras mellan olika situationer."
    ),
    "Self-awareness, deliberate adaptation and the effect of the surrounding context.": (
        "Självinsikt, medveten anpassning och hur omgivande förutsättningar påverkade agerandet."
    ),
    "Tell me about a challenging situation involving other people. How did you decide what approach to take?": (
        "Berätta om en utmanande situation som involverade andra människor. "
        "Hur avgjorde du vilket tillvägagångssätt du skulle använda?"
    ),
    "This provides evidence about how preferences may influence collaboration and judgement.": (
        "Detta ger underlag om hur preferenser kan påverka samarbete och bedömningar."
    ),
    "Perspective-taking, communication choices and the reasoning behind the person's actions.": (
        "Perspektivtagande, kommunikationsval och resonemanget bakom personens agerande."
    ),
    "What feedback have you received about your way of working, and what did you learn from it?": (
        "Vilken återkoppling har du fått om ditt sätt att arbeta och vad lärde du dig av den?"
    ),
    "This adds external behavioural evidence that may confirm or add nuance to the personality profile.": (
        "Detta tillför extern beteendeevidens som kan bekräfta eller nyansera personlighetsprofilen."
    ),
    "Concrete feedback, reflection and changes made in response.": (
        "Konkret återkoppling, reflektion och förändringar som genomförts utifrån återkopplingen."
    ),
    "Describe a situation where you had to balance different priorities or expectations. How did you approach it?": (
        "Beskriv en situation där du behövde balansera olika prioriteringar "
        "eller förväntningar. Hur tog du dig an situationen?"
    ),
    "This explores how several behavioural preferences may interact in a practical situation.": (
        "Detta utforskar hur flera beteendepreferenser kan samverka i en praktisk situation."
    ),
    "Prioritisation, trade-offs and awareness of how the situation affected the chosen approach.": (
        "Prioriteringar, avvägningar och medvetenhet om hur situationen påverkade det valda arbetssättet."
    ),
    "Tell me about a situation that required you to work outside your preferred style. What was difficult, and what helped?": (
        "Berätta om en situation där du behövde arbeta utanför ditt föredragna "
        "arbetssätt. Vad var utmanande och vad hjälpte dig?"
    ),
    "This explores flexibility and the conditions that support effective behaviour.": (
        "Detta utforskar flexibilitet och vilka förutsättningar som stödjer ett effektivt agerande."
    ),
    "Adaptation, support needs, learning and awareness of personal preferences.": (
        "Anpassning, stödbehov, lärande och medvetenhet om personliga preferenser."
    ),
}


def _translate_safe_value(value):
    if isinstance(value, str):
        return _SAFE_SWEDISH.get(value, value)
    if isinstance(value, list):
        return [_translate_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _translate_safe_value(item) for key, item in value.items()}
    return value


def _build_safe_personality_questions_event(
    *,
    selected_traits: list[str],
    personality_results: list[dict[str, Any]],
) -> dict[str, Any]:
    result = _original_build_safe_personality_questions_event(
        selected_traits=selected_traits,
        personality_results=personality_results,
    )
    if normalize_ai_language(_personality_questions_language.get()) == "sv":
        return _translate_safe_value(result)
    return result


def create_empty_personality_questions(
    owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
    result = _original_create_empty_personality_questions(owner)
    examples = _question_examples(language_code)
    result["title"] = examples["title"]
    result["label"] = examples["label"]
    return result


def stream_personality_questions(
    *,
    owner,
    personality_results: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
    language_code = normalize_ai_language(language_code)
    token = _personality_questions_language.set(language_code)
    try:
        yield from _original_stream_personality_questions(
            owner=owner,
            personality_results=personality_results,
        )
    finally:
        _personality_questions_language.reset(token)


def save_personality_questions(
    *,
    owner,
    result: dict[str, Any],
    language_code: str = "en",
):
    language_code = normalize_ai_language(language_code)
    result["_language"] = language_code
    set_ai_content_language(
        owner,
        "personality_questions",
        language_code,
    )
    _original_save_personality_questions(
        owner=owner,
        result=result,
    )
    if hasattr(owner, "ai_content_languages"):
        owner.save(update_fields=["ai_content_languages"])

