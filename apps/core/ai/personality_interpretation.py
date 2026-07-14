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


def build_personality_interpretation_prompt(
    owner,
    personality_results: list[dict[str, Any]],
) -> str:
    """
    Build the prompt for Talena's combined personality interpretation.

    Response styles and interview questions are handled separately.
    This interpretation focuses on the personality trait profile as a whole.
    """

    shared_context = build_shared_ai_context(
        owner
    )

    evidence_text = build_personality_evidence_text(
        personality_results
    )

    if shared_context["has_context"]:
        context_instruction = """
Use the supplied process context to explain how the personality
preferences may be relevant to the stated role, situation or
development purpose.

Clearly distinguish between:
- behavioural preferences indicated by the assessment
- information explicitly stated in the process context
- interpretations that should be explored through examples or conversation

Do not invent responsibilities, requirements, organisational culture,
team conditions or candidate experience.
""".strip()

    else:
        context_instruction = """
No additional process context has been supplied.

Provide a broader interpretation based on the available personality
results and the selected purpose.

Do not invent specific responsibilities, requirements, organisational
culture, team conditions or candidate experience.

State clearly that the practical relevance of the personality profile
depends on the actual situation and should be explored further.
""".strip()

    return f"""
You are generating an AI-supported personality interpretation for
Talena, an assessment and talent management platform.

You are an experienced and balanced workplace assessment consultant
with strong knowledge of personality, behavioural preferences,
structured feedback and development conversations.

CANDIDATE
Name: {shared_context["candidate_name"]}

SELECTED PROCESS PURPOSE
Purpose: {shared_context["purpose_label"]}

OPTIONAL PROCESS CONTEXT
{shared_context["context_text"]}

AVAILABLE PERSONALITY TRAIT RESULTS
{evidence_text}

CONTEXT INSTRUCTION
{context_instruction}

YOUR TASK
Create one practical and balanced interpretation of the available
personality trait profile.

Help the user understand:

1. The most important overall behavioural preferences in the profile.
2. How different personality traits may work together.
3. Which patterns may be useful or supportive for the selected purpose.
4. Which patterns, tensions or situational demands should be explored.
5. The limitations of drawing conclusions from personality results alone.

IMPORTANT SCOPE
- Focus on personality traits only.
- Do not interpret response-style indicators here.
- Response styles are handled in a separate Talena section.
- Do not generate interview or reflection questions here.
- Questions are handled in a separate Talena section.

CORE INTERPRETATION RULES
- Personality results describe likely behavioural preferences or
  tendencies, not fixed behaviour.
- Higher and lower results are not automatically strengths or weaknesses.
- Mid-range results may indicate moderation, flexibility or context
  dependence.
- Personality results do not measure cognitive ability, motivation,
  competence, experience, integrity or future performance.
- Do not assume that a preference has been demonstrated successfully
  in the workplace.
- Do not make a hiring, promotion, placement or development decision.
- Do not create a match score, suitability verdict or prediction of success.
- Do not diagnose the candidate.
- Do not invent candidate experience or process requirements.
- Treat results as indicators and hypotheses, not facts.
- Consider combinations between available traits where useful.
- Do not create invented psychological constructs, competency names
  or composite scores.
- Do not include raw STEN scores in the final output.
- Do not describe the person using fixed labels.
- Use concrete and practical workplace language.

INTERPRETING COMBINATIONS
When discussing how traits may work together:

- Describe the possible behavioural effect of the combination.
- Acknowledge that behaviour may vary by situation.
- Explain both the potentially useful expression and what may require
  conscious adaptation.
- Do not claim that one trait cancels out another.
- Do not invent contradictions where the evidence does not support them.
- Prioritise the combinations that are most relevant to the selected
  purpose or supplied context.

LANGUAGE AND TONE
- Write in professional, clear English.
- Be balanced, practical and non-judgemental.
- Use cautious formulations such as:
  "may indicate",
  "suggests",
  "could mean",
  "may prefer",
  "may be useful to explore".
- Avoid repeatedly writing "the candidate is".
- Refer to the candidate by first name where natural.
- Avoid technical or academic terminology.
- Avoid exaggerated positive or negative wording.

CONTENT REQUIREMENTS

OVERALL PERSONALITY INTERPRETATION
Write approximately 100 to 150 words.

The interpretation should:
- summarise the most important personality patterns
- consider the profile as a whole
- connect cautiously to the selected purpose
- use supplied context when available
- include both potentially useful patterns and relevant considerations
- acknowledge missing context where necessary
- avoid simply listing individual traits

PROFILE DYNAMICS
Write one practical paragraph of approximately 50 to 90 words.

Describe:
- one or two meaningful combinations in the profile
- how these preferences may work together
- how the expression may change depending on the situation
- what may require conscious adaptation

Do not invent a contradiction or tension if none is supported.

POTENTIALLY SUPPORTIVE PATTERNS
Return exactly 3 concise points.

Each point must:
- be grounded in available personality traits
- explain possible relevance to the selected purpose or context
- describe a behavioural preference rather than proven competence
- remain cautious and practical

Do not force exaggerated strengths.

WHAT TO EXPLORE OR VALIDATE
Return exactly 3 concise points.

These may include:
- situations where a natural preference may be less effective
- behavioural demands that may require adaptation
- tensions between different preferences
- requirements that personality results cannot evaluate
- areas where actual examples are needed
- limitations caused by missing process context

These are hypotheses to explore, not confirmed weaknesses.

CONTEXT NOTE
Briefly explain:
- that personality trait results were used
- whether additional process context was available
- that response styles and questions are handled separately
- that actual behaviour should be validated using relevant examples

STREAMING OUTPUT FORMAT
Return newline-delimited JSON, also called NDJSON.

Every JSON object must appear on one single line.
Do not use Markdown.
Do not use code fences.
Do not add text outside the JSON objects.

Return events in this exact order:

1. One meta event:

{{"type":"meta","title":"Personality interpretation","label":"AI-supported interpretation"}}

2. Between 3 and 6 interpretation_delta events:

{{"type":"interpretation_delta","text":"First part of the interpretation. "}}
{{"type":"interpretation_delta","text":"Next part of the interpretation. "}}

Together, these events form the complete overall interpretation.

3. One profile_dynamics event:

{{"type":"profile_dynamics","text":"A practical explanation of how important personality preferences may work together."}}

4. One supportive_patterns event containing exactly 3 items:

{{"type":"supportive_patterns","items":["Pattern one","Pattern two","Pattern three"]}}

5. One areas_to_explore event containing exactly 3 items:

{{"type":"areas_to_explore","items":["Area one","Area two","Area three"]}}

6. One context_note event:

{{"type":"context_note","text":"Brief explanation of the evidence, context and limitations."}}

7. One final done event:

{{"type":"done"}}
""".strip()


def create_empty_personality_interpretation(
    owner,
) -> dict[str, Any]:
    return {
        "title": "Personality interpretation",
        "label": "AI-supported interpretation",
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
                for item in items[:3]
                if str(item).strip()
            ]

    elif event_type == "areas_to_explore":
        items = event.get("items")

        if isinstance(items, list):
            interpretation["areas_to_explore"] = [
                str(item).strip()
                for item in items[:3]
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
) -> Iterable[dict[str, Any]]:
    """
    Stream personality interpretation events from OpenAI.
    """

    if not personality_results:
        raise ValueError(
            "No personality assessment results are available."
        )

    client = get_openai_client()

    prompt = build_personality_interpretation_prompt(
        owner=owner,
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
                    "results as hypotheses rather than facts, do not "
                    "invent context, and follow the requested NDJSON "
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


def save_personality_interpretation(
    *,
    owner,
    interpretation: dict[str, Any],
):
    """
    Save a completed personality interpretation.
    """

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
        for item in supportive_patterns[:3]
        if str(item).strip()
    ]

    areas_to_explore = interpretation.get(
        "areas_to_explore"
    )

    if not isinstance(areas_to_explore, list):
        areas_to_explore = []

    interpretation["areas_to_explore"] = [
        str(item).strip()
        for item in areas_to_explore[:3]
        if str(item).strip()
    ]

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

    owner.save(update_fields=[
        "ai_personality_interpretation",
        "ai_personality_interpretation_status",
        "ai_personality_interpretation_generated_at",
        "ai_personality_interpretation_purpose",
    ])