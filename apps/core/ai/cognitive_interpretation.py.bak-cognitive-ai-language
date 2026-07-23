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



def extract_cognitive_results(
    invitation,
) -> list[dict[str, Any]]:
    """
    Extract available cognitive percentile results from the
    candidate's Sova activities.

    Returns only assessments that contain a usable percentile.
    """

    activities = (
        invitation.sova_activities
        or []
    )

    result_config = {
        "logical": {
            "label": "Logical reasoning",
            "keywords": (
                "logical",
                "logisk",
            ),
        },
        "numerical": {
            "label": "Numerical reasoning",
            "keywords": (
                "numerical",
                "numeric",
                "numerisk",
            ),
        },
        "verbal": {
            "label": "Verbal reasoning",
            "keywords": (
                "verbal",
            ),
        },
    }

    results = []

    for activity in activities:
        activity_name = (
            activity.get("activity")
            or ""
        ).strip()

        activity_name_lower = (
            activity_name.lower()
        )

        matched_key = None

        for test_key, config in result_config.items():
            if any(
                keyword in activity_name_lower
                for keyword in config["keywords"]
            ):
                matched_key = test_key
                break

        if not matched_key:
            continue

        competencies = (
            activity.get("competencies")
            or []
        )

        percentile = None

        for competency in competencies:
            value = competency.get(
                "percentile"
            )

            if value is None:
                continue

            try:
                percentile = int(
                    round(float(value))
                )
            except (TypeError, ValueError):
                percentile = None

            if percentile is not None:
                break

        if percentile is None:
            continue

        percentile = max(
            0,
            min(100, percentile),
        )

        results.append({
            "key": matched_key,
            "label": (
                result_config[matched_key]["label"]
            ),
            "percentile": percentile,
        })

    return results


def describe_percentile_band(
    percentile: int,
) -> str:
    """
    Provide a neutral reference-group description for the prompt.
    """

    if percentile <= 9:
        return "very low relative to the reference group"

    if percentile <= 24:
        return "lower than many people in the reference group"

    if percentile <= 74:
        return "within the typical range for the reference group"

    if percentile <= 90:
        return "higher than many people in the reference group"

    return "very high relative to the reference group"


def build_cognitive_evidence_text(
    results: list[dict[str, Any]],
) -> str:
    if not results:
        return (
            "No cognitive assessment results are available."
        )

    lines = []

    for result in results:
        percentile = result["percentile"]

        lines.append(
            f"- {result['label']}: "
            f"percentile {percentile}, "
            f"{describe_percentile_band(percentile)}"
        )

    return "\n".join(lines)


def build_cognitive_interpretation_prompt(
    invitation,
    cognitive_results: list[dict[str, Any]],
) -> str:
    """
    Build the prompt for the cognitive interpretation section.
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
        build_cognitive_evidence_text(
            cognitive_results
        )
    )

    has_context = bool(context_data)

    if has_context:
        context_instruction = """
Use the supplied process context to explain which types of cognitive
demands may be relevant.

Do not assume that a test result proves actual workplace performance,
experience or competence.

Clearly distinguish between:
- the cognitive assessment result
- requirements stated in the supplied context
- questions that should be explored using other evidence
""".strip()

    else:
        context_instruction = """
No additional process context has been supplied.

Provide a broader interpretation based on the available cognitive
assessment results and the selected purpose.

Do not invent specific job tasks, leadership demands, customer
situations, systems, responsibilities or working conditions.

State clearly that specific relevance depends on the actual demands
of the role or situation.
""".strip()

    return f"""
You are generating a cognitive assessment interpretation for Talena,
an assessment and talent management platform.

You are an experienced, balanced and commercially aware assessment
consultant with strong knowledge of cognitive assessment, workplace
demands and structured follow-up conversations.

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
Create a practical and balanced interpretation of the available
cognitive assessment results.

The interpretation should help the user understand:

1. What the results may indicate about how readily the person processes
   the specific type of information measured by each assessment.
2. Which types of work demands may make the result more or less relevant.
3. Which conditions, strategies or support may be useful to consider.
4. Which questions could help gather concrete behavioural evidence.

IMPORTANT INTERPRETATION PRINCIPLES
- Cognitive assessment results describe relative performance on specific
  reasoning tasks compared with a reference group.
- They do not measure overall intelligence.
- They do not measure personality, motivation, knowledge or experience.
- They do not prove actual workplace competence.
- Previous experience, familiarity, preparation, language, fatigue,
  test conditions and working methods may affect how results appear.
- A lower result does not mean that the person cannot perform the task.
- A higher result does not guarantee strong workplace performance.
- Do not make a final hiring, promotion or development decision.
- Do not create a match score or suitability verdict.
- Do not diagnose the candidate.
- Do not invent role demands or candidate experience.
- Treat the results as indicators and hypotheses.
- Do not include raw percentile numbers in the final output.
- Use cautious and practical language.

WORKPLACE DEMAND FRAMEWORK
Use the following framework where relevant.

Higher cognitive demands may involve:
- unfamiliar, ambiguous or complex problems
- large amounts of information from multiple sources
- independent decisions with significant consequences
- rapid learning without extensive support
- errors that may have broad impact

Moderate cognitive demands may involve:
- some complexity within reasonably defined boundaries
- several information sources that remain manageable
- some independent judgement
- gradual learning with support
- errors affecting part of the work or process

Lower cognitive demands may involve:
- clear and recurring tasks
- limited, structured and linear information
- rule-based decisions
- clear instruction, training and repetition
- errors with limited consequences

Do not describe these levels as better or worse.
The relevance depends on the actual work demands.

LANGUAGE AND TONE
- Write in professional, clear English.
- Be balanced, practical and non-judgemental.
- Use formulations such as:
  "may indicate",
  "suggests",
  "could mean",
  "may require",
  "could be useful to explore".
- Avoid academic or overly technical language.
- Avoid repeatedly writing "the candidate is".
- Refer to the candidate by first name where natural.

CONTENT REQUIREMENTS

PRACTICAL INTERPRETATION
Write approximately 90 to 140 words.

The interpretation should:
- cover all available cognitive assessments
- explain the likely practical meaning of the results
- connect cautiously to the selected purpose
- use supplied context when available
- clearly state relevant limitations
- avoid repeating the later bullet points word for word

CONSIDERATIONS
Return between 2 and 4 concise points.

Each point should describe:
- a relevant condition
- a possible support need
- a limitation of the evidence
- or a work demand that should be clarified

Do not frame these as confirmed weaknesses.

FOLLOW-UP QUESTIONS
Return exactly 3 questions.

Each question must:
- be open and practical
- request a concrete example or working method
- help compare assessment indications with actual behaviour
- be relevant to the selected purpose
- not lead the respondent towards a preferred answer

For recruitment, questions may be phrased as interview questions.
For development, leadership, onboarding or team purposes, phrase them
as reflection or discussion questions where appropriate.

For every question, also return:
- why the question is relevant
- what the user should listen for

CONTEXT NOTE
Briefly explain:
- which cognitive assessments were available
- whether additional process context was available
- how this affects the scope of the interpretation

STREAMING OUTPUT FORMAT
Return newline-delimited JSON, also called NDJSON.

Every JSON object must be written on one single line.
Do not use Markdown.
Do not use code fences.
Do not add text outside the JSON objects.

Return events in this exact order:

1. One meta event:

{{"type":"meta","title":"Cognitive interpretation","label":"AI-supported interpretation"}}

2. Between 3 and 6 interpretation_delta events:

{{"type":"interpretation_delta","text":"First part of the interpretation. "}}
{{"type":"interpretation_delta","text":"Next part of the interpretation. "}}

Together, these events form the complete practical interpretation.

3. One considerations event containing between 2 and 4 items:

{{"type":"considerations","items":["Consideration one","Consideration two"]}}

4. One questions event containing exactly 3 objects:

{{"type":"questions","items":[{{"question":"Question one","why":"Why it matters","listen_for":"What to listen for"}},{{"question":"Question two","why":"Why it matters","listen_for":"What to listen for"}},{{"question":"Question three","why":"Why it matters","listen_for":"What to listen for"}}]}}

5. One context_note event:

{{"type":"context_note","text":"Brief explanation of the evidence and context used."}}

6. One final done event:

{{"type":"done"}}
""".strip()


def create_empty_cognitive_interpretation(
    owner,
) -> dict[str, Any]:
    return {
        "title": "Cognitive interpretation",
        "label": "AI-supported interpretation",
        "interpretation": "",
        "considerations": [],
        "questions": [],
        "context_note": "",
    }


def apply_cognitive_interpretation_event(
    interpretation: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one streamed event to the complete saved result.
    """

    event_type = event.get("type")

    if event_type == "meta":
        interpretation["title"] = (
            str(
                event.get("title")
                or interpretation["title"]
            ).strip()
        )

        interpretation["label"] = (
            str(
                event.get("label")
                or interpretation["label"]
            ).strip()
        )

    elif event_type == "interpretation_delta":
        interpretation["interpretation"] += str(
            event.get("text")
            or ""
        )

    elif event_type == "considerations":
        items = event.get("items")

        if isinstance(items, list):
            interpretation["considerations"] = [
                str(item).strip()
                for item in items[:4]
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

                normalised_questions.append({
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

            interpretation["questions"] = (
                normalised_questions
            )

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


def stream_cognitive_interpretation(
    *,
    owner,
    cognitive_results: list[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
    """
    Stream cognitive interpretation events from OpenAI.
    """

    if not cognitive_results:
        raise ValueError(
            "No cognitive assessment results are available."
        )

    client = get_openai_client()

    prompt = build_cognitive_interpretation_prompt(
        invitation=owner,
        cognitive_results=cognitive_results,
    )

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful and experienced cognitive "
                    "assessment interpretation consultant. Treat test "
                    "results as indicators rather than facts, do not "
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


def save_cognitive_interpretation(
    *,
    owner,
    interpretation: dict[str, Any],
):
    """
    Save the completed cognitive interpretation.
    """

    interpretation["interpretation"] = (
        interpretation.get("interpretation")
        or ""
    ).strip()

    owner.ai_cognitive_interpretation = (
        interpretation
    )

    owner.ai_cognitive_interpretation_status = (
        "completed"
    )

    owner.ai_cognitive_interpretation_generated_at = (
        timezone.now()
    )

    owner.ai_cognitive_interpretation_purpose = (
        get_process_purpose_key(
            owner.process
        )
    )

    owner.save(update_fields=[
        "ai_cognitive_interpretation",
        "ai_cognitive_interpretation_status",
        "ai_cognitive_interpretation_generated_at",
        "ai_cognitive_interpretation_purpose",
    ])