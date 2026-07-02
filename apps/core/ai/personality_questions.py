from __future__ import annotations

import json
from typing import Any, Iterable

from django.forms.models import model_to_dict
from django.utils import timezone

from .openai_client import (
    get_openai_client,
    get_chat_model,
)


PURPOSE_LABELS = {
    "hiring": "Recruitment",
    "recruitment": "Recruitment",
    "role_match": "Role matching",
    "internal_role_match": "Role matching",
    "leadership_potential": "Leadership potential",
    "leader_development": "Leadership development",
    "employee_development": "Employee development",
    "career_path": "Career development",
    "onboarding": "Onboarding",
    "team_development": "Team development",
    "reorganisation": "Reorganisation",
    "reorganization": "Reorganisation",
    "flexible": "General insights",
    "unsure": "General insights",
    "general": "General insights",
}


EXCLUDED_PERSONALITY_COMPETENCIES = {
    "social desirability",
    "fillers",
    "reliability",
    "profile spread",
    "ratings spread",
}


def get_purpose_key(process) -> str:
    return (process.purpose or "").strip().lower()


def get_purpose_label(process) -> str:
    purpose_key = get_purpose_key(process)

    if purpose_key in PURPOSE_LABELS:
        return PURPOSE_LABELS[purpose_key]

    if hasattr(process, "get_purpose_display"):
        return process.get_purpose_display()

    return purpose_key or "General insights"


def build_process_context(
    process,
) -> tuple[str, dict[str, Any]]:
    """
    Convert optional process context into prompt-friendly text.
    """

    purpose_context = getattr(
        process,
        "role_context",
        None,
    )

    if (
        not purpose_context
        or not purpose_context.has_content()
    ):
        return (
            "No additional process context has been added.",
            {},
        )

    raw_context = model_to_dict(
        purpose_context
    )

    excluded_fields = {
        "id",
        "process",
        "created_at",
        "updated_at",
        "purpose_data",
    }

    context_data = {}
    context_lines = []

    for field_name, value in raw_context.items():
        if field_name in excluded_fields:
            continue

        if value in (None, "", [], {}):
            continue

        readable_name = (
            field_name
            .replace("_", " ")
            .strip()
            .title()
        )

        context_data[field_name] = value

        context_lines.append(
            f"- {readable_name}: {value}"
        )

    if not context_lines:
        return (
            "No additional process context has been added.",
            {},
        )

    return (
        "\n".join(context_lines),
        context_data,
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

    candidate = invitation.candidate
    process = invitation.process

    purpose_label = get_purpose_label(
        process
    )

    context_text, context_data = (
        build_process_context(process)
    )

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
        items = event.get("items")

        if isinstance(items, list):
            normalised_questions = []

            for item in items[:3]:
                if not isinstance(item, dict):
                    continue

                question = str(
                    item.get("question")
                    or ""
                ).strip()

                if not question:
                    continue

                raw_traits = item.get("traits")

                traits = (
                    [
                        str(trait).strip()
                        for trait in raw_traits
                        if str(trait).strip()
                    ]
                    if isinstance(raw_traits, list)
                    else []
                )

                normalised_questions.append({
                    "question": question,
                    "traits": traits,
                    "why": str(
                        item.get("why")
                        or ""
                    ).strip(),
                    "listen_for": str(
                        item.get("listen_for")
                        or ""
                    ).strip(),
                })

            result["questions"] = (
                normalised_questions
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


def stream_personality_questions(
    *,
    owner,
    personality_results: list[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
    """
    Stream personality trait suggestions and questions from OpenAI.
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
        get_purpose_key(owner.process)
    )

    owner.save(update_fields=[
        "selected_personality_traits",
        "ai_personality_questions",
        "ai_personality_questions_status",
        "ai_personality_questions_generated_at",
        "ai_personality_questions_purpose",
    ])