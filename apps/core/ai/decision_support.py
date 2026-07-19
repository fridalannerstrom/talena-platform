from __future__ import annotations

import json
from typing import Any, Iterable

from django.utils import timezone

from .openai_client import (
    get_chat_model,
    get_openai_client,
)
from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)


# ============================================================
# Shared normalisation helpers
# ============================================================


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_string_list(
    value: Any,
    *,
    limit: int,
) -> list[str]:
    if not isinstance(value, list):
        return []

    return [
        _clean_text(item)
        for item in value[:limit]
        if _clean_text(item)
    ]


def _normalise_question(
    item: Any,
) -> dict[str, str] | None:
    if isinstance(item, str):
        question = _clean_text(item)

        if not question:
            return None

        return {
            "question": question,
            "why": "",
            "listen_for": "",
        }

    if not isinstance(item, dict):
        return None

    question = _clean_text(
        item.get("question")
    )

    if not question:
        return None

    return {
        "question": question,
        "why": _clean_text(
            item.get("why")
        ),
        "listen_for": _clean_text(
            item.get("listen_for")
        ),
    }


def _normalise_questions(
    value: Any,
    *,
    limit: int,
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    questions = []

    for item in value[:limit]:
        question = _normalise_question(
            item
        )

        if question:
            questions.append(question)

    return questions


def _format_text_field(
    label: str,
    value: Any,
) -> str:
    text = _clean_text(value)

    if not text:
        return ""

    return f"{label}:\n{text}"


def _format_list_field(
    label: str,
    value: Any,
    *,
    limit: int = 6,
) -> str:
    items = _clean_string_list(
        value,
        limit=limit,
    )

    if not items:
        return ""

    return (
        f"{label}:\n"
        + "\n".join(
            f"- {item}"
            for item in items
        )
    )


# ============================================================
# Evidence collection
# ============================================================


def build_pre_interview_evidence(
    owner,
) -> dict[str, Any]:
    """
    Collect existing saved Talena interpretations.

    No new interpretation is created here. This prepares the
    source material used by the final pre-interview synthesis.
    """

    sections = []
    source_names = []

    def add_section(
        *,
        title: str,
        status: str,
        content_parts: list[str],
    ):
        content = [
            part
            for part in content_parts
            if part
        ]

        if not content:
            return

        sections.append(
            "\n".join([
                f"SOURCE: {title}",
                f"STATUS: {status or 'not_started'}",
                *content,
            ])
        )

        if title not in source_names:
            source_names.append(title)

    # --------------------------------------------------------
    # AI Overview
    # --------------------------------------------------------

    overview = (
        owner.ai_purpose_fit
        or {}
    )

    add_section(
        title="AI Overview",
        status=(
            owner.ai_purpose_fit_status
            or "not_started"
        ),
        content_parts=[
            _format_text_field(
                "Overall summary",
                overview.get("summary"),
            ),
            _format_list_field(
                "Purpose-relevant indications",
                overview.get("key_alignment"),
            ),
            _format_list_field(
                "Topics to explore",
                overview.get("areas_to_verify"),
            ),
            _format_text_field(
                "Suggested next step",
                overview.get(
                    "suggested_next_step"
                ),
            ),
            _format_text_field(
                "Context note",
                overview.get("context_note"),
            ),
        ],
    )

    # --------------------------------------------------------
    # Personality interpretation
    # --------------------------------------------------------

    personality = (
        owner.ai_personality_interpretation
        or {}
    )

    add_section(
        title="Personality interpretation",
        status=(
            owner
            .ai_personality_interpretation_status
            or "not_started"
        ),
        content_parts=[
            _format_text_field(
                "Interpretation",
                personality.get(
                    "interpretation"
                ),
            ),
            _format_text_field(
                "Profile dynamics",
                personality.get(
                    "profile_dynamics"
                ),
            ),
            _format_list_field(
                "Supportive patterns",
                personality.get(
                    "supportive_patterns"
                ),
            ),
            _format_list_field(
                "Areas to explore",
                personality.get(
                    "areas_to_explore"
                ),
            ),
            _format_text_field(
                "Context note",
                personality.get(
                    "context_note"
                ),
            ),
        ],
    )

    # --------------------------------------------------------
    # Motivation interpretation
    # --------------------------------------------------------

    motivation = (
        owner.ai_motivation_interpretation
        or {}
    )

    add_section(
        title="Motivation interpretation",
        status=(
            owner
            .ai_motivation_interpretation_status
            or "not_started"
        ),
        content_parts=[
            _format_text_field(
                "Interpretation",
                motivation.get(
                    "interpretation"
                ),
            ),
            _format_list_field(
                "Engagement conditions",
                motivation.get(
                    "engagement_conditions"
                ),
            ),
            _format_list_field(
                "Areas to clarify",
                motivation.get(
                    "areas_to_clarify"
                ),
            ),
            _format_text_field(
                "Expectation setting",
                motivation.get(
                    "expectation_setting"
                ),
            ),
            _format_text_field(
                "Context note",
                motivation.get(
                    "context_note"
                ),
            ),
        ],
    )

    # --------------------------------------------------------
    # Cognitive interpretation
    # --------------------------------------------------------

    cognitive = (
        owner.ai_cognitive_interpretation
        or {}
    )

    add_section(
        title="Cognitive interpretation",
        status=(
            owner
            .ai_cognitive_interpretation_status
            or "not_started"
        ),
        content_parts=[
            _format_text_field(
                "Interpretation",
                cognitive.get(
                    "interpretation"
                ),
            ),
            _format_list_field(
                "Considerations",
                cognitive.get(
                    "considerations"
                ),
            ),
            _format_text_field(
                "Context note",
                cognitive.get(
                    "context_note"
                ),
            ),
        ],
    )

    # --------------------------------------------------------
    # Response-style guidance
    # --------------------------------------------------------

    response_styles = (
        owner.ai_response_style_guidance
        or {}
    )

    add_section(
        title="Response-style guidance",
        status=(
            owner
            .ai_response_style_guidance_status
            or "not_started"
        ),
        content_parts=[
            _format_text_field(
                "Summary",
                response_styles.get(
                    "summary"
                ),
            ),
            _format_text_field(
                "How to interpret",
                response_styles.get(
                    "how_to_interpret"
                ),
            ),
            _format_text_field(
                "Recommended discussion approach",
                response_styles.get(
                    "recommended_approach"
                ),
            ),
            _format_text_field(
                "Combination note",
                response_styles.get(
                    "combination_note"
                ),
            ),
            _format_text_field(
                "Context note",
                response_styles.get(
                    "context_note"
                ),
            ),
        ],
    )

    # --------------------------------------------------------
    # Available question bank
    # --------------------------------------------------------

    question_sources = [
        {
            "title": "Personality questions",
            "result": (
                owner.ai_personality_questions
                or {}
            ),
        },
        {
            "title": "Motivation questions",
            "result": motivation,
        },
        {
            "title": "Cognitive questions",
            "result": (
                owner.ai_cognitive_questions
                or cognitive
                or {}
            ),
        },
        {
            "title": "Response-style questions",
            "result": response_styles,
        },
    ]

    question_lines = []

    for source in question_sources:
        questions = _normalise_questions(
            source["result"].get(
                "questions"
            ),
            limit=6,
        )

        for question in questions:
            line_parts = [
                (
                    f"[{source['title']}] "
                    f"{question['question']}"
                ),
            ]

            if question["why"]:
                line_parts.append(
                    f"Why: {question['why']}"
                )

            if question["listen_for"]:
                line_parts.append(
                    (
                        "Listen for: "
                        f"{question['listen_for']}"
                    )
                )

            question_lines.append(
                " | ".join(line_parts)
            )

    if question_lines:
        question_text = "\n".join(
            f"- {line}"
            for line in question_lines[:18]
        )
    else:
        question_text = (
            "No saved assessment questions "
            "are available."
        )

    evidence_text = (
        "\n\n".join(sections)
        if sections
        else (
            "No completed Talena assessment "
            "interpretations are available."
        )
    )

    return {
        "evidence_text": evidence_text,
        "question_text": question_text,
        "source_names": source_names,
        "source_count": len(source_names),
        "has_evidence": bool(sections),
    }


# ============================================================
# Prompt
# ============================================================


def build_pre_interview_decision_support_prompt(
    owner,
) -> str:
    shared_context = build_shared_ai_context(
        owner
    )

    candidate = shared_context["candidate"]
    purpose_label = shared_context[
        "purpose_label"
    ]
    context_text = shared_context[
        "context_text"
    ]
    context_data = shared_context[
        "context_data"
    ]

    evidence = (
        build_pre_interview_evidence(
            owner
        )
    )

    source_names = (
        ", ".join(
            evidence["source_names"]
        )
        or "No completed interpretation sources"
    )

    if context_data:
        context_instruction = """
Use the supplied process context to explain why particular assessment
indications may be relevant to the stated role, situation or development
purpose.

Distinguish clearly between:
- information explicitly supplied in the process context
- indications drawn from assessment evidence
- assumptions that require validation through candidate examples
""".strip()
    else:
        context_instruction = """
No additional process context has been supplied.

Keep the synthesis broad and state clearly that the practical relevance
of the assessment indications depends on the actual role, situation or
development context.

Do not invent role requirements, responsibilities, culture, experience
or working conditions.
""".strip()

    return f"""
You are generating PRE-INTERVIEW DECISION SUPPORT for Talena, an
assessment and talent management platform.

You are an experienced and careful assessment practitioner. Your role is
to organise available evidence, explain uncertainty and help a human user
prepare a relevant interview or feedback conversation.

You do not make the final decision.

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

SELECTED PROCESS PURPOSE
Purpose: {purpose_label}

PROCESS CONTEXT
{context_text}

CONTEXT INSTRUCTION
{context_instruction}

AVAILABLE TALENA INTERPRETATION SOURCES
{source_names}

SAVED ASSESSMENT INTERPRETATION EVIDENCE
{evidence["evidence_text"]}

AVAILABLE SAVED QUESTION BANK
{evidence["question_text"]}

INTERVIEW EVIDENCE
No interview notes, candidate examples or interview answers are included
in this pre-interview output.

The absence of interview evidence must be treated as an evidence gap,
not as negative evidence about the candidate.

YOUR TASK

Create a clear, nuanced and practically useful pre-interview decision
support document.

The output should help a recruiter, manager, coach or assessment
practitioner understand:

1. The most important combined indications in the available evidence.
2. Which indications may be relevant to the selected purpose.
3. What should be interpreted cautiously.
4. How to approach feedback or interview discussion.
5. Which priority questions may help validate or add nuance to the profile.
6. Which important evidence is still missing.

THIS IS NOT A MATCHING VERDICT

Never:
- provide a match score, fit score, suitability score or confidence score
- state that the candidate is a match or is not a match
- state that the candidate is suitable or unsuitable
- describe the candidate as a strong fit, poor fit or recommended candidate
- recommend hiring, rejecting, promoting, selecting or excluding the candidate
- rank the candidate
- predict future job performance
- turn assessment indications into a final conclusion
- treat the absence of interview evidence as a weakness
- resolve contradictions when the evidence does not justify doing so

CORE INTERPRETATION RULES

- Treat assessment findings as indicators and hypotheses, not facts.
- Distinguish personality, motivation, cognitive and response-style evidence.
- Do not imply that personality measures ability.
- Do not imply that cognitive results measure experience, motivation or
  workplace behaviour.
- Do not describe high scores as automatic strengths.
- Do not describe low scores as automatic weaknesses.
- Identify combinations and tensions only when supported by the supplied
  source material.
- Explain discrepancies neutrally.
- State when evidence is incomplete, outdated or context-dependent.
- Do not invent candidate experience, interview responses or role requirements.
- Do not include raw assessment scores.
- Use candidate examples and behavioural evidence as information that still
  needs to be collected.
- Leave all selection, placement, promotion and development decisions to the
  responsible human user.

LANGUAGE AND TONE

- Write in professional, clear English.
- Be balanced, practical and non-judgemental.
- Use cautious language such as:
  "may indicate",
  "suggests",
  "could be relevant",
  "would benefit from validation",
  "may require further exploration".
- Refer to {candidate.first_name} by first name where natural.
- Avoid technical test terminology where plain language is sufficient.
- Do not repeat the same point across multiple sections.

CONTENT REQUIREMENTS

OVERALL SYNTHESIS
Write approximately 140 to 220 words.

It should:
- combine the available assessment themes
- explain their possible relevance to the selected purpose
- include both potentially useful indications and important uncertainty
- state clearly that interview evidence has not yet been added
- avoid presenting separate mini-reports for each assessment

PURPOSE-RELEVANT INDICATIONS
Return between 2 and 4 integrated themes.

Each theme must contain:
- a short descriptive title
- a cautious practical interpretation
- a list of evidence source labels

Evidence source labels must only use labels from:
{source_names}

These themes are not strengths, proof of competence or reasons to select
the candidate.

CAUTIOUS INTERPRETATIONS
Return between 2 and 4 items.

Each item must contain:
- a short title
- what should be interpreted cautiously
- why caution is required

Possible reasons include:
- missing behavioural examples
- missing process context
- conflicting or nuanced assessment indications
- response-style considerations
- limitations of what the available assessments measure
- an outdated source result

DISCUSSION GUIDANCE
Return:
- between 2 and 3 feedback approach points
- between 2 and 3 interview focus points

Feedback approach should explain how to discuss the profile fairly and
constructively.

Interview focus should explain where concrete examples or clarification
are especially important.

PRIORITY VALIDATION QUESTIONS
Return between 3 and 5 questions.

Use or adapt the most useful questions from the supplied question bank.

Each question must contain:
- question
- why
- listen_for

Questions must:
- be open and non-leading
- request examples, reflection or working methods
- help validate, challenge or add nuance to assessment indications
- cover different themes
- not assume that the assessment indication is true

EVIDENCE GAPS
Return between 2 and 4 concise items.

Always include that candidate examples and interview evidence have not
yet been added.

CONTEXT NOTE
Briefly explain:
- which Talena interpretation sources were available
- whether process context was supplied
- that interview evidence was not used
- that the final decision remains with the human user

STREAMING OUTPUT FORMAT

Return newline-delimited JSON, also called NDJSON.

Every JSON object must appear on one single line.
Do not use Markdown.
Do not use code fences.
Do not add text outside the JSON objects.

Return events in this exact order:

1. One meta event:

{{"type":"meta","title":"Pre-interview decision support","label":"AI-supported decision preparation"}}

2. Between 4 and 8 overall_synthesis_delta events:

{{"type":"overall_synthesis_delta","text":"First part of the synthesis. "}}
{{"type":"overall_synthesis_delta","text":"Next part of the synthesis. "}}

3. One purpose_relevant_indications event:

{{"type":"purpose_relevant_indications","items":[{{"title":"Theme title","interpretation":"Cautious practical interpretation","evidence_sources":["AI Overview","Personality interpretation"]}}]}}

4. One cautious_interpretations event:

{{"type":"cautious_interpretations","items":[{{"title":"Area requiring caution","interpretation":"What should be interpreted cautiously","reason_for_caution":"Why caution is required"}}]}}

5. One discussion_guidance event:

{{"type":"discussion_guidance","feedback_approach":["Feedback point one","Feedback point two"],"interview_focus":["Interview focus one","Interview focus two"]}}

6. One validation_questions event:

{{"type":"validation_questions","items":[{{"question":"Open question","why":"Why this helps","listen_for":"What evidence or nuance to listen for"}}]}}

7. One evidence_gaps event:

{{"type":"evidence_gaps","items":["Candidate examples and interview evidence have not yet been added.","Another relevant evidence gap."]}}

8. One context_note event:

{{"type":"context_note","text":"Transparent explanation of the evidence used, evidence missing and the human user's responsibility for the final decision."}}

9. One final done event:

{{"type":"done"}}
""".strip()


# ============================================================
# Empty result
# ============================================================


def create_empty_pre_interview_decision_support(
    owner,
) -> dict[str, Any]:
    return {
        "title": (
            "Pre-interview decision support"
        ),
        "label": (
            "AI-supported decision preparation"
        ),
        "overall_synthesis": "",
        "purpose_relevant_indications": [],
        "cautious_interpretations": [],
        "discussion_guidance": {
            "feedback_approach": [],
            "interview_focus": [],
        },
        "validation_questions": [],
        "evidence_gaps": [],
        "context_note": "",
    }


# ============================================================
# Event normalisation
# ============================================================


def _normalise_indication_items(
    value: Any,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    items = []

    for item in value[:4]:
        if not isinstance(item, dict):
            continue

        title = _clean_text(
            item.get("title")
        )
        interpretation = _clean_text(
            item.get("interpretation")
        )

        if not title or not interpretation:
            continue

        evidence_sources = (
            _clean_string_list(
                item.get(
                    "evidence_sources"
                ),
                limit=5,
            )
        )

        items.append({
            "title": title,
            "interpretation": interpretation,
            "evidence_sources": (
                evidence_sources
            ),
        })

    return items


def _normalise_caution_items(
    value: Any,
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    items = []

    for item in value[:4]:
        if not isinstance(item, dict):
            continue

        title = _clean_text(
            item.get("title")
        )
        interpretation = _clean_text(
            item.get("interpretation")
        )
        reason = _clean_text(
            item.get(
                "reason_for_caution"
            )
        )

        if not title or not interpretation:
            continue

        items.append({
            "title": title,
            "interpretation": interpretation,
            "reason_for_caution": reason,
        })

    return items


# ============================================================
# Apply streamed events
# ============================================================


def apply_pre_interview_decision_support_event(
    result: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    event_type = event.get("type")

    if event_type == "meta":
        title = _clean_text(
            event.get("title")
        )
        label = _clean_text(
            event.get("label")
        )

        if title:
            result["title"] = title

        if label:
            result["label"] = label

    elif event_type == "overall_synthesis_delta":
        result["overall_synthesis"] += str(
            event.get("text")
            or ""
        )

    elif event_type == "purpose_relevant_indications":
        result[
            "purpose_relevant_indications"
        ] = _normalise_indication_items(
            event.get("items")
        )

    elif event_type == "cautious_interpretations":
        result[
            "cautious_interpretations"
        ] = _normalise_caution_items(
            event.get("items")
        )

    elif event_type == "discussion_guidance":
        result["discussion_guidance"] = {
            "feedback_approach": (
                _clean_string_list(
                    event.get(
                        "feedback_approach"
                    ),
                    limit=3,
                )
            ),
            "interview_focus": (
                _clean_string_list(
                    event.get(
                        "interview_focus"
                    ),
                    limit=3,
                )
            ),
        }

    elif event_type == "validation_questions":
        result["validation_questions"] = (
            _normalise_questions(
                event.get("items"),
                limit=5,
            )
        )

    elif event_type == "evidence_gaps":
        result["evidence_gaps"] = (
            _clean_string_list(
                event.get("items"),
                limit=4,
            )
        )

    elif event_type == "context_note":
        result["context_note"] = (
            _clean_text(
                event.get("text")
            )
        )

    return result


# ============================================================
# NDJSON parsing
# ============================================================

_JSON_DECODER = json.JSONDecoder()


def _normalise_event_type(
    value: Any,
) -> str:
    """
    Normalise minor formatting differences in AI event names.
    """

    event_type = (
        str(value or "")
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )

    aliases = {
        "supported_evidence": (
            "supported_indications"
        ),
        "supported_assessment_indications": (
            "supported_indications"
        ),
        "evidence_supporting_indications": (
            "supported_indications"
        ),
        "interview_nuance": (
            "added_nuance"
        ),
        "interview_adds_nuance": (
            "added_nuance"
        ),
        "added_context": (
            "added_nuance"
        ),
        "remaining_uncertainty": (
            "remaining_uncertainties"
        ),
        "suggested_followup": (
            "suggested_follow_up"
        ),
        "follow_up": (
            "suggested_follow_up"
        ),
    }

    return aliases.get(
        event_type,
        event_type,
    )


def _extract_json_events_from_buffer(
    buffer: str,
) -> tuple[list[dict[str, Any]], str]:
    """
    Extract complete JSON objects from a streaming text buffer.

    Unlike line-based NDJSON parsing, this also supports JSON
    objects formatted across multiple lines.
    """

    events: list[dict[str, Any]] = []
    remaining = buffer

    while True:
        remaining = remaining.lstrip()

        if not remaining:
            return events, ""

        # Ignore Markdown code-fence openings.
        if remaining.startswith("```"):
            newline_index = remaining.find(
                "\n"
            )

            if newline_index == -1:
                return events, remaining

            remaining = remaining[
                newline_index + 1:
            ]

            continue

        object_start = remaining.find("{")

        if object_start == -1:
            # Keep a small trailing fragment in case the next
            # stream chunk completes an opening JSON object.
            return events, remaining[-200:]

        if object_start > 0:
            remaining = remaining[
                object_start:
            ]

        try:
            payload, end_index = (
                _JSON_DECODER.raw_decode(
                    remaining
                )
            )
        except json.JSONDecodeError:
            # The JSON object is probably incomplete. Keep it
            # until more stream content arrives.
            return events, remaining

        remaining = remaining[
            end_index:
        ]

        if not isinstance(
            payload,
            dict,
        ):
            continue

        event_type = _normalise_event_type(
            payload.get("type")
        )

        if not event_type:
            continue

        payload["type"] = event_type
        events.append(payload)



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

    event_type = _normalise_event_type(
        event.get("type")
    )

    if not event_type:
        return None

    event["type"] = event_type

    return event


# ============================================================
# Streaming
# ============================================================


def stream_pre_interview_decision_support(
    *,
    owner,
) -> Iterable[dict[str, Any]]:
    evidence = build_pre_interview_evidence(
        owner
    )

    if not evidence["has_evidence"]:
        raise ValueError(
            "No completed Talena interpretations "
            "are available for decision support."
        )

    client = get_openai_client()

    prompt = (
        build_pre_interview_decision_support_prompt(
            owner
        )
    )

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful and experienced "
                    "assessment synthesis consultant. "
                    "You organise evidence and uncertainty "
                    "but never make a suitability, matching, "
                    "selection, promotion or hiring decision. "
                    "Follow the requested NDJSON format exactly."
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
        delta = (
            response_event
            .choices[0]
            .delta
        )

        if (
            not delta
            or not delta.content
        ):
            continue

        buffer += delta.content

        parsed_events, buffer = (
            _extract_json_events_from_buffer(
                buffer
            )
        )

        for parsed_event in parsed_events:
            yield parsed_event

    parsed_events, buffer = (
        _extract_json_events_from_buffer(
            buffer
        )
    )

    for parsed_event in parsed_events:
        yield parsed_event

    trailing_content = (
        buffer
        .replace("```json", "")
        .replace("```ndjson", "")
        .replace("```", "")
        .strip()
    )

    if trailing_content:
        final_event = _parse_event_line(
            trailing_content
        )

        if final_event:
            yield final_event


# ============================================================
# Saving
# ============================================================


def save_pre_interview_decision_support(
    *,
    owner,
    result: dict[str, Any],
):
    result["overall_synthesis"] = (
        _clean_text(
            result.get(
                "overall_synthesis"
            )
        )
    )

    result["context_note"] = (
        _clean_text(
            result.get(
                "context_note"
            )
        )
    )

    result[
        "purpose_relevant_indications"
    ] = _normalise_indication_items(
        result.get(
            "purpose_relevant_indications"
        )
    )

    result[
        "cautious_interpretations"
    ] = _normalise_caution_items(
        result.get(
            "cautious_interpretations"
        )
    )

    discussion_guidance = (
        result.get(
            "discussion_guidance"
        )
        or {}
    )

    result["discussion_guidance"] = {
        "feedback_approach": (
            _clean_string_list(
                discussion_guidance.get(
                    "feedback_approach"
                ),
                limit=3,
            )
        ),
        "interview_focus": (
            _clean_string_list(
                discussion_guidance.get(
                    "interview_focus"
                ),
                limit=3,
            )
        ),
    }

    result["validation_questions"] = (
        _normalise_questions(
            result.get(
                "validation_questions"
            ),
            limit=5,
        )
    )

    result["evidence_gaps"] = (
        _clean_string_list(
            result.get(
                "evidence_gaps"
            ),
            limit=4,
        )
    )

    owner.ai_pre_interview_decision_support = (
        result
    )

    owner.ai_pre_interview_decision_support_status = (
        "completed"
    )

    owner.ai_pre_interview_decision_support_generated_at = (
        timezone.now()
    )

    owner.ai_pre_interview_decision_support_purpose = (
        get_process_purpose_key(
            owner.process
        )
    )

    owner.save(
        update_fields=[
            (
                "ai_pre_interview_"
                "decision_support"
            ),
            (
                "ai_pre_interview_"
                "decision_support_status"
            ),
            (
                "ai_pre_interview_"
                "decision_support_generated_at"
            ),
            (
                "ai_pre_interview_"
                "decision_support_purpose"
            ),
        ]
    )


# ============================================================
# Post-interview decision support
# ============================================================


def create_empty_post_interview_decision_support(
    owner,
) -> dict[str, Any]:
    return {
        "title": (
            "Post-interview decision support"
        ),
        "label": (
            "Assessment and interview synthesis"
        ),
        "overall_synthesis": "",
        "supported_indications": [],
        "added_nuance": [],
        "contradictions": [],
        "remaining_uncertainties": [],
        "suggested_follow_up": [],
        "context_note": "",
    }


def _normalise_supported_evidence_items(
    value: Any,
    *,
    limit: int = 4,
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    items = []

    for item in value[:limit]:
        if not isinstance(item, dict):
            continue

        title = _clean_text(
            item.get("title")
        )

        assessment_indication = _clean_text(
            item.get(
                "assessment_indication"
            )
        )

        interview_evidence = _clean_text(
            item.get(
                "interview_evidence"
            )
        )

        interpretation = _clean_text(
            item.get("interpretation")
        )

        if not title or not interpretation:
            continue

        items.append({
            "title": title,
            "assessment_indication": (
                assessment_indication
            ),
            "interview_evidence": (
                interview_evidence
            ),
            "interpretation": interpretation,
        })

    return items


def _normalise_nuance_items(
    value: Any,
    *,
    limit: int = 4,
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    items = []

    for item in value[:limit]:
        if not isinstance(item, dict):
            continue

        title = _clean_text(
            item.get("title")
        )

        assessment_indication = _clean_text(
            item.get(
                "assessment_indication"
            )
        )

        interview_evidence = _clean_text(
            item.get(
                "interview_evidence"
            )
        )

        interpretation = _clean_text(
            item.get("interpretation")
        )

        if not title or not interpretation:
            continue

        items.append({
            "title": title,
            "assessment_indication": (
                assessment_indication
            ),
            "interview_evidence": (
                interview_evidence
            ),
            "interpretation": interpretation,
        })

    return items


def _normalise_contradiction_items(
    value: Any,
    *,
    limit: int = 3,
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    items = []

    for item in value[:limit]:
        if not isinstance(item, dict):
            continue

        title = _clean_text(
            item.get("title")
        )

        assessment_evidence = _clean_text(
            item.get(
                "assessment_evidence"
            )
        )

        interview_evidence = _clean_text(
            item.get(
                "interview_evidence"
            )
        )

        interpretation = _clean_text(
            item.get("interpretation")
        )

        if not title or not interpretation:
            continue

        items.append({
            "title": title,
            "assessment_evidence": (
                assessment_evidence
            ),
            "interview_evidence": (
                interview_evidence
            ),
            "interpretation": interpretation,
        })

    return items


def build_post_interview_decision_support_prompt(
    owner,
) -> str:
    shared_context = build_shared_ai_context(
        owner
    )

    candidate = shared_context["candidate"]

    purpose_label = shared_context[
        "purpose_label"
    ]

    context_text = shared_context[
        "context_text"
    ]

    context_data = shared_context[
        "context_data"
    ]

    evidence = build_pre_interview_evidence(
        owner
    )

    interview_notes = _clean_text(
        owner.interview_notes
    )

    pre_interview_result = (
        owner.ai_pre_interview_decision_support
        or {}
    )

    if not interview_notes:
        raise ValueError(
            "Interview notes must be added before "
            "post-interview decision support can be generated."
        )

    if context_data:
        context_instruction = """
Use the supplied process context when explaining why assessment and
interview evidence may be relevant.

Do not assume that the context describes every requirement of the role.
Do not turn contextual relevance into a suitability conclusion.
""".strip()

    else:
        context_instruction = """
No additional process context has been supplied.

Keep the synthesis broad and state clearly that practical relevance
depends on the real role, situation or development context.

Do not invent role requirements.
""".strip()

    pre_interview_text = json.dumps(
        pre_interview_result,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
You are generating POST-INTERVIEW DECISION SUPPORT for Talena, an
assessment and talent management platform.

You are an experienced and careful assessment practitioner.

Your role is to compare structured assessment indications with interview
evidence, candidate examples and interviewer observations.

You organise the available evidence and explain uncertainty.

You do not make the final decision.

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

SELECTED PROCESS PURPOSE
Purpose: {purpose_label}

PROCESS CONTEXT
{context_text}

CONTEXT INSTRUCTION
{context_instruction}

SAVED ASSESSMENT INTERPRETATION EVIDENCE
{evidence["evidence_text"]}

PRE-INTERVIEW DECISION SUPPORT
{pre_interview_text}

INTERVIEW NOTES AND CANDIDATE EXAMPLES
{interview_notes}

YOUR TASK

Create a clear, balanced and practically useful post-interview decision
support document.

Compare the interview evidence with the assessment indications.

Identify:

1. Assessment indications that receive relevant support from concrete
   interview examples.
2. Interview evidence that adds important context or nuance.
3. Apparent contradictions or tensions that should not be resolved
   automatically.
4. Areas where the evidence remains incomplete or uncertain.
5. Useful follow-up actions or questions.

THIS IS NOT A MATCHING VERDICT

Never:
- provide a match score, fit score or suitability score
- state that the candidate is or is not a match
- state that the candidate is suitable or unsuitable
- recommend hiring, rejecting, selecting, promoting or excluding
  the candidate
- rank the candidate
- predict future performance
- present interview statements as independently verified facts
- treat one example as proof of a stable behaviour
- treat a low assessment score as an automatic weakness
- treat a high assessment score as an automatic strength
- resolve contradictions without sufficient evidence
- invent experience or examples not present in the notes
- assume the interviewer interpretation is objectively correct

EVIDENCE RULES

Distinguish clearly between:

- assessment indication
- candidate-provided example
- interviewer observation
- your cautious synthesis
- evidence that remains missing

Assessment results are indicators and hypotheses, not facts.

Interview notes may contain:
- direct candidate statements
- summaries written by the interviewer
- interviewer interpretations
- incomplete or subjective observations

Do not treat all interview-note content as equally strong evidence.

Concrete behavioural examples should generally carry more weight than:
- broad self-descriptions
- hypothetical answers
- unsupported interviewer impressions
- general claims without context

Do not ignore tensions between assessment and interview evidence.

A tension does not necessarily mean that either source is incorrect.
It may indicate:
- context-dependent behaviour
- learned coping strategies
- differences between preference and capability
- incomplete evidence
- differences between test conditions and practical work

NUMERICAL AND COGNITIVE RESULTS

Do not conclude that a comparatively low numerical result means the
candidate cannot succeed in a development role.

Instead:
- consider what numerical demands the actual role contains
- identify practical strategies described by the candidate
- distinguish rapid abstract reasoning from careful applied work
- consider checking, testing, documentation and review behaviours
- state clearly what has and has not been demonstrated

Do not minimise a relevant cognitive result simply because the candidate
gave a positive interview example.

LANGUAGE AND TONE

- Write in professional, clear English.
- Refer to {candidate.first_name} by first name where natural.
- Use cautious language.
- Avoid absolute statements.
- Avoid technical psychometric jargon where plain language works.
- Do not repeat the same point across sections.
- Keep each item practical and evidence-based.

OVERALL SYNTHESIS

Write approximately 160 to 240 words.

It should:
- integrate assessment and interview evidence
- identify supported indications and important nuance
- mention relevant uncertainty
- avoid separate mini-reports for each assessment
- explain that the final judgement remains with the human user

SUPPORTED INDICATIONS

Return between 2 and 4 items.

Each item must contain:

- title
- assessment_indication
- interview_evidence
- interpretation

Only include an item when the interview notes contain a reasonably
relevant example or observation.

Do not call these confirmed strengths.

ADDED NUANCE

Return between 2 and 4 items.

Each item must contain:

- title
- assessment_indication
- interview_evidence
- interpretation

Use this section where interview evidence:
- adds context
- shows conditions affecting behaviour
- suggests coping strategies
- limits an overly broad interpretation
- shows differences between preference and practical behaviour

CONTRADICTIONS

Return between 0 and 3 items.

Each item must contain:

- title
- assessment_evidence
- interview_evidence
- interpretation

Only include genuine tensions.

Do not manufacture contradictions merely to fill the section.

Explain plausible interpretations without deciding which source is right.

REMAINING UNCERTAINTIES

Return between 2 and 5 concise items.

Include important questions that remain unanswered after considering both
assessment and interview evidence.

SUGGESTED FOLLOW-UP

Return between 2 and 5 concise actions or questions.

These may include:
- targeted follow-up questions
- work samples
- references
- technical exercises
- clarification of role demands
- further examples

Do not recommend a selection decision.

CONTEXT NOTE

Briefly explain:
- that assessment interpretations and interview notes were used
- that interview evidence may contain subjective or unverified material
- that the output does not determine suitability
- that the final decision remains with the responsible human user

STREAMING OUTPUT FORMAT

Return newline-delimited JSON, also called NDJSON.

Every JSON object must appear on one single line.
Do not use Markdown.
Do not use code fences.
Do not add text outside the JSON objects.

Return events in this exact order:

1. One meta event:

{{"type":"meta","title":"Post-interview decision support","label":"Assessment and interview synthesis"}}

2. Between 4 and 8 overall_synthesis_delta events:

{{"type":"overall_synthesis_delta","text":"First part of the synthesis. "}}

3. One supported_indications event:

{{"type":"supported_indications","items":[{{"title":"Theme title","assessment_indication":"Relevant assessment indication","interview_evidence":"Relevant interview example","interpretation":"Cautious synthesis"}}]}}

4. One added_nuance event:

{{"type":"added_nuance","items":[{{"title":"Theme title","assessment_indication":"Relevant assessment indication","interview_evidence":"Relevant interview evidence","interpretation":"How the interview evidence adds nuance"}}]}}

5. One contradictions event:

{{"type":"contradictions","items":[{{"title":"Tension title","assessment_evidence":"Assessment evidence","interview_evidence":"Interview evidence","interpretation":"Balanced explanation of the tension"}}]}}

The items list may be empty when no genuine contradiction is present.

6. One remaining_uncertainties event:

{{"type":"remaining_uncertainties","items":["Uncertainty one","Uncertainty two"]}}

7. One suggested_follow_up event:

{{"type":"suggested_follow_up","items":["Follow-up action one","Follow-up action two"]}}

8. One context_note event:

{{"type":"context_note","text":"Transparent explanation of the evidence used, limitations and human responsibility for the final decision."}}

9. One final done event:

{{"type":"done"}}
""".strip()


def apply_post_interview_decision_support_event(
    result: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    event_type = event.get("type")

    if event_type == "meta":
        title = _clean_text(
            event.get("title")
        )

        label = _clean_text(
            event.get("label")
        )

        if title:
            result["title"] = title

        if label:
            result["label"] = label

    elif event_type == "overall_synthesis_delta":
        result["overall_synthesis"] += str(
            event.get("text")
            or ""
        )

    elif event_type == "supported_indications":
        result["supported_indications"] = (
            _normalise_supported_evidence_items(
                event.get("items"),
                limit=4,
            )
        )

    elif event_type == "added_nuance":
        result["added_nuance"] = (
            _normalise_nuance_items(
                event.get("items"),
                limit=4,
            )
        )

    elif event_type == "contradictions":
        result["contradictions"] = (
            _normalise_contradiction_items(
                event.get("items"),
                limit=3,
            )
        )

    elif event_type == "remaining_uncertainties":
        result["remaining_uncertainties"] = (
            _clean_string_list(
                event.get("items"),
                limit=5,
            )
        )

    elif event_type == "suggested_follow_up":
        result["suggested_follow_up"] = (
            _clean_string_list(
                event.get("items"),
                limit=5,
            )
        )

    elif event_type == "context_note":
        result["context_note"] = (
            _clean_text(
                event.get("text")
            )
        )

    return result


def stream_post_interview_decision_support(
    *,
    owner,
) -> Iterable[dict[str, Any]]:
    interview_notes = _clean_text(
        owner.interview_notes
    )

    if not interview_notes:
        raise ValueError(
            "Interview notes must be added before "
            "post-interview decision support can be generated."
        )

    evidence = build_pre_interview_evidence(
        owner
    )

    if not evidence["has_evidence"]:
        raise ValueError(
            "No completed Talena interpretations "
            "are available for decision support."
        )

    client = get_openai_client()

    prompt = (
        build_post_interview_decision_support_prompt(
            owner
        )
    )

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful assessment synthesis "
                    "consultant. Compare assessment indications "
                    "with interview evidence without making a "
                    "matching, suitability, selection, promotion "
                    "or hiring decision. Follow the requested "
                    "NDJSON format exactly."
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
        delta = (
            response_event
            .choices[0]
            .delta
        )

        if (
            not delta
            or not delta.content
        ):
            continue

        buffer += delta.content

        parsed_events, buffer = (
            _extract_json_events_from_buffer(
                buffer
            )
        )

        for parsed_event in parsed_events:
            yield parsed_event

    # Flush any complete JSON objects remaining after
    # the final streamed chunk.
    parsed_events, buffer = (
        _extract_json_events_from_buffer(
            buffer
        )
    )

    for parsed_event in parsed_events:
        yield parsed_event

    trailing_content = (
        buffer
        .replace("```json", "")
        .replace("```ndjson", "")
        .replace("```", "")
        .strip()
    )

    if trailing_content:
        final_event = _parse_event_line(
            trailing_content
        )

        if final_event:
            yield final_event


def save_post_interview_decision_support(
    *,
    owner,
    result: dict[str, Any],
):
    result["overall_synthesis"] = (
        _clean_text(
            result.get(
                "overall_synthesis"
            )
        )
    )

    result["supported_indications"] = (
        _normalise_supported_evidence_items(
            result.get(
                "supported_indications"
            ),
            limit=4,
        )
    )

    result["added_nuance"] = (
        _normalise_nuance_items(
            result.get(
                "added_nuance"
            ),
            limit=4,
        )
    )

    result["contradictions"] = (
        _normalise_contradiction_items(
            result.get(
                "contradictions"
            ),
            limit=3,
        )
    )

    result["remaining_uncertainties"] = (
        _clean_string_list(
            result.get(
                "remaining_uncertainties"
            ),
            limit=5,
        )
    )

    result["suggested_follow_up"] = (
        _clean_string_list(
            result.get(
                "suggested_follow_up"
            ),
            limit=5,
        )
    )

    result["context_note"] = (
        _clean_text(
            result.get(
                "context_note"
            )
        )
    )

    generated_at = timezone.now()

    owner.ai_post_interview_decision_support = (
        result
    )

    owner.ai_post_interview_decision_support_status = (
        "completed"
    )

    owner.ai_post_interview_decision_support_generated_at = (
        generated_at
    )

    owner.ai_post_interview_decision_support_purpose = (
        get_process_purpose_key(
            owner.process
        )
    )

    owner.ai_post_interview_decision_support_notes_version = (
        owner.interview_notes_updated_at
        or generated_at
    )

    owner.save(
        update_fields=[
            (
                "ai_post_interview_"
                "decision_support"
            ),
            (
                "ai_post_interview_"
                "decision_support_status"
            ),
            (
                "ai_post_interview_"
                "decision_support_generated_at"
            ),
            (
                "ai_post_interview_"
                "decision_support_purpose"
            ),
            (
                "ai_post_interview_"
                "decision_support_notes_version"
            ),
        ]
    )