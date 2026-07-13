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



EXCLUDED_PERSONALITY_COMPETENCIES = {
    "social desirability",
    "fillers",
    "reliability",
    "profile spread",
    "ratings spread",
}



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


def describe_sten_position(
    sten: int,
) -> str:
    """
    Describe a STEN result neutrally for the AI prompt.
    """

    if sten <= 3:
        return "lower-range behavioural preference"

    if sten <= 7:
        return "mid-range behavioural preference"

    return "higher-range behavioural preference"


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
            f"STEN {result['sten']} of 10; "
            f"{describe_sten_position(result['sten'])}"
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


def build_personality_questions_prompt(
    invitation,
    personality_results: list[dict[str, Any]],
) -> str:
    """
    Build the prompt for trait suggestions and purpose-aware questions.
    """

    shared_context = build_shared_ai_context(
        invitation
    )

    candidate = shared_context["candidate"]
    process = shared_context["process"]

    purpose_label = shared_context["purpose_label"]
    context_text = shared_context["context_text"]
    context_data = shared_context["context_data"]

    evidence_text = (
        build_personality_evidence_text(
            personality_results
        )
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
        else (
            "No user-selected traits are currently saved. "
            "Suggest the most relevant available traits."
        )
    )

    has_context = bool(context_data)
    has_user_selection = bool(selected_traits)

    if has_context:
        context_instruction = """
Use the supplied process context to identify which behavioural
preferences may be especially relevant to explore.

Only use requirements, situations or responsibilities explicitly
included in the supplied context.

Do not invent role requirements, company culture, leadership demands,
team conditions or candidate experience.
""".strip()
    else:
        context_instruction = """
No additional process context has been supplied.

Base the suggestions and questions on the available personality
results and selected process purpose only.

Do not invent specific role requirements, company culture, leadership
demands, team conditions or candidate experience.

State that the relevance of the suggested traits should be checked
against the actual situation.
""".strip()

    if has_user_selection:
        selection_instruction = """
The user has already selected personality traits.

Use exactly those selected traits for the questions.
Do not replace them with different traits.
Return the same selected traits in the selected_traits event.
Suggested traits may still explain why those traits are relevant.
""".strip()
    else:
        selection_instruction = """
No user-selected traits are currently saved.

Suggest between 4 and 6 traits from the available personality results.
Select traits because they are useful to explore for the stated purpose
or supplied context, not merely because they have the highest or lowest
scores.

The questions must be based on those suggested traits.
""".strip()

    return f"""
You are generating AI-supported personality questions for Talena,
an assessment and talent management platform.

You are an experienced and balanced assessment consultant with strong
knowledge of workplace personality, behavioural interviewing,
leadership reflection and development conversations.

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

SELECTED PROCESS PURPOSE
Purpose: {purpose_label}

OPTIONAL PROCESS CONTEXT
{context_text}

AVAILABLE PERSONALITY RESULTS
{evidence_text}

CURRENT USER-SELECTED TRAITS
{selected_traits_text}

CONTEXT INSTRUCTION
{context_instruction}

TRAIT SELECTION INSTRUCTION
{selection_instruction}

YOUR TASK
Identify relevant personality traits and generate practical questions
that help the user explore how those behavioural preferences appear in
real situations.

The output must help the user understand:

1. Which available traits may be particularly relevant to the purpose.
2. Why each selected or suggested trait may be useful to explore.
3. Which behavioural questions can test or deepen the assessment
   hypotheses.
4. What useful evidence or nuance the user should listen for.

CORE INTERPRETATION RULES
- Personality results describe likely behavioural preferences or
  tendencies, not fixed behaviour.
- They do not measure cognitive ability, motivation, competence,
  experience, integrity or future performance.
- Higher and lower results are not automatically strengths or weaknesses.
- Mid-range results may indicate flexibility, moderation or context
  dependence.
- Treat results as hypotheses to explore, not facts.
- Do not diagnose the candidate.
- Do not make a final hiring, promotion or development decision.
- Do not create a match score or suitability verdict.
- Do not invent traits that are not present in the supplied results.
- Do not invent psychological constructs or combine traits into newly
  named competencies.
- Do not include raw STEN scores in the final output.
- Do not claim that the person has demonstrated a behaviour unless
  supporting examples are supplied elsewhere.
- Questions should invite evidence that may confirm, challenge or
  nuance the assessment indication.

TRAIT SELECTION RULES
- Return between 4 and 6 traits.
- Every returned trait must exactly match a trait name from the
  available personality results.
- Do not select response-style measures.
- Do not select traits solely because their results are extreme.
- Prefer a balanced set that is relevant to the process purpose.
- Avoid selecting several traits that would lead to nearly identical
  questions.
- If the user has selected traits, preserve that selection exactly.

QUESTION RULES
Return exactly 3 question objects.

Each question must:
- be open and behavioural or reflective
- ask for a concrete example, approach or learning
- be based on one or more selected traits
- cover a distinct theme
- avoid leading the respondent towards a preferred answer
- avoid mentioning assessment scores
- avoid labelling the person

For recruitment:
- use behavioural interview wording
- ask for specific situations and actions

For leadership or employee development:
- use reflective or coaching-oriented wording
- invite examples, self-awareness and development thinking

For onboarding:
- focus on preferred ways of working, communication and support

For team development:
- focus on collaboration, contribution and interaction patterns

For each question return:
- question
- traits
- why
- listen_for

The "traits" value must be a list containing only selected trait names.

LANGUAGE AND TONE
- Write in professional, clear English.
- Be practical, balanced and non-judgemental.
- Use cautious language.
- Avoid technical test terminology.
- Refer to the candidate by first name only where natural.

CONTEXT NOTE
Briefly explain:
- that personality results were used
- whether additional process context was available
- whether the traits were AI-suggested or user-selected
- that the questions are hypotheses for exploration

STREAMING OUTPUT FORMAT
Return newline-delimited JSON, also called NDJSON.

Every JSON object must appear on one single line.
Do not use Markdown.
Do not use code fences.
Do not add text outside the JSON objects.

Return events in this exact order:

1. One meta event:

{{"type":"meta","title":"Personality questions","label":"AI-supported questions"}}

2. One suggested_traits event containing between 4 and 6 objects:

{{"type":"suggested_traits","items":[{{"name":"Trait name","reason":"Why this trait may be relevant"}},{{"name":"Trait name","reason":"Why this trait may be relevant"}},{{"name":"Trait name","reason":"Why this trait may be relevant"}},{{"name":"Trait name","reason":"Why this trait may be relevant"}}]}}

3. One selected_traits event containing the trait names used for questions:

{{"type":"selected_traits","items":["Trait name","Trait name","Trait name","Trait name"]}}

4. One questions event containing exactly 3 objects:

{{"type":"questions","items":[{{"question":"Question one","traits":["Trait name"],"why":"Why it matters","listen_for":"What to listen for"}},{{"question":"Question two","traits":["Trait name","Trait name"],"why":"Why it matters","listen_for":"What to listen for"}},{{"question":"Question three","traits":["Trait name"],"why":"Why it matters","listen_for":"What to listen for"}}]}}

5. One context_note event:

{{"type":"context_note","text":"Brief explanation of the evidence, context and trait selection used."}}

6. One final done event:

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
    Return complete personality question objects.

    Every valid question must contain:
    - question
    - at least one selected trait
    - why
    - listen_for
    """

    if not isinstance(items, list):
        return []

    trait_lookup = {
        str(trait).strip().lower(): str(trait).strip()
        for trait in selected_traits or []
        if str(trait).strip()
    }

    questions = []

    for item in items[:3]:
        if not isinstance(item, dict):
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

        raw_traits = item.get("traits")
        traits = []

        if isinstance(raw_traits, list):
            for raw_trait in raw_traits:
                trait_key = str(
                    raw_trait
                    or ""
                ).strip().lower()

                canonical_trait = trait_lookup.get(
                    trait_key
                )

                if (
                    canonical_trait
                    and canonical_trait not in traits
                ):
                    traits.append(
                        canonical_trait
                    )

        if (
            not question
            or not why
            or not listen_for
            or not traits
        ):
            continue

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

    return f"""
You are repairing a missing or malformed personality questions event
for Talena.

CANDIDATE
Name: {shared_context["candidate_name"]}

SELECTED PROCESS PURPOSE
Purpose: {shared_context["purpose_label"]}

PROCESS CONTEXT
{shared_context["context_text"]}

AVAILABLE PERSONALITY RESULTS
{evidence_text}

SELECTED PERSONALITY TRAITS
{selected_traits_text}

YOUR TASK
Return exactly three complete questions based on the selected traits.

Each question must:
- be open and behavioural or reflective
- ask for a concrete example, approach or learning
- use one or more of the selected traits
- be relevant to the selected purpose
- use supplied process context when available
- avoid leading the respondent
- avoid mentioning raw assessment scores
- treat personality results as hypotheses rather than facts

Every question object must contain:
- question
- traits
- why
- listen_for

The traits property must be a list containing only names from the
selected personality traits above.

OUTPUT FORMAT
Return exactly one JSON object on one single line.
Do not use Markdown.
Do not use code fences.
Do not add any other text.

{{"type":"questions","items":[{{"question":"Question one","traits":["Trait name"],"why":"Why it matters","listen_for":"What to listen for"}},{{"question":"Question two","traits":["Trait name"],"why":"Why it matters","listen_for":"What to listen for"}},{{"question":"Question three","traits":["Trait name"],"why":"Why it matters","listen_for":"What to listen for"}}]}}
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

    if len(questions) != 3:
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
    Last-resort deterministic questions.

    This prevents a valid trait selection from being lost because the
    model formatted its questions event incorrectly.
    """

    traits = [
        str(trait).strip()
        for trait in selected_traits
        if str(trait).strip()
    ]

    if not traits:
        traits = [
            item["name"]
            for item in personality_results[:4]
            if item.get("name")
        ]

    if not traits:
        raise ValueError(
            "No personality traits are available for the questions."
        )

    def trait_at(index):
        return traits[index % len(traits)]

    return {
        "type": "questions",
        "items": [
            {
                "question": (
                    "Tell me about a recent situation where your usual "
                    "way of working was particularly effective. What did "
                    "you do, and what was the outcome?"
                ),
                "traits": [
                    trait_at(0),
                ],
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
                    "Describe a situation where you needed to adapt your "
                    "normal approach. What made the adjustment necessary?"
                ),
                "traits": [
                    trait_at(1),
                    trait_at(2),
                ],
                "why": (
                    "This explores flexibility and how personality "
                    "preferences may change across situations."
                ),
                "listen_for": (
                    "Self-awareness, deliberate adaptation and the effect "
                    "of the surrounding context."
                ),
            },
            {
                "question": (
                    "What feedback have you received about how you work "
                    "with other people, and what did you learn from it?"
                ),
                "traits": [
                    trait_at(3),
                ],
                "why": (
                    "This provides external behavioural evidence that may "
                    "confirm or add nuance to the personality profile."
                ),
                "listen_for": (
                    "Concrete feedback, reflection and examples of changes "
                    "made in response."
                ),
            },
        ],
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

        response = client.chat.completions.create(
            model=get_chat_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful workplace personality "
                        "assessment consultant. Return the requested "
                        "JSON object exactly."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        _build_personality_questions_repair_prompt(
                            owner=owner,
                            personality_results=personality_results,
                            selected_traits=selected_traits,
                        )
                    ),
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

    return _build_safe_personality_questions_event(
        selected_traits=selected_traits,
        personality_results=personality_results,
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

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful and experienced workplace "
                    "personality assessment consultant. Treat personality "
                    "results as hypotheses rather than facts, never invent "
                    "context or traits, and follow the requested NDJSON "
                    "streaming format exactly."
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
    received_valid_questions = False

    def prepare_event(
        event: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        nonlocal selected_traits
        nonlocal suggested_traits
        nonlocal received_valid_questions

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
            questions = _normalise_personality_questions(
                event.get("items"),
                selected_traits,
            )

            if len(questions) != 3:
                return None

            received_valid_questions = True

            return {
                "type": "questions",
                "items": questions,
            }

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
        # Make sure an AI-generated selection contains 4 to 6 traits.
        trait_candidates = (
            selected_traits
            + suggested_traits
            + [
                item["name"]
                for item in personality_results
                if item.get("name")
            ]
        )

        selected_traits = normalise_selected_traits(
            selected_traits=trait_candidates,
            available_results=personality_results,
        )[:6]

        if len(selected_traits) < 4:
            raise ValueError(
                "Fewer than four personality traits are available."
            )

    # Emit the final canonical selection.
    yield {
        "type": "selected_traits",
        "items": selected_traits,
    }

    if not received_valid_questions:
        yield _generate_repaired_personality_questions_event(
            owner=owner,
            personality_results=personality_results,
            selected_traits=selected_traits,
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
    """

    selected_traits = (
        result.get("selected_traits")
        or []
    )

    if not owner.selected_personality_traits:
        owner.selected_personality_traits = (
            selected_traits
        )

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

    owner.save(update_fields=[
        "selected_personality_traits",
        "ai_personality_questions",
        "ai_personality_questions_status",
        "ai_personality_questions_generated_at",
        "ai_personality_questions_purpose",
    ])