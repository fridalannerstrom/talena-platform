from __future__ import annotations

import json
from typing import Any, Iterable

from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)

from django.utils import timezone

from .openai_client import (
    get_openai_client,
    get_chat_model,
)




RESPONSE_STYLE_EXPERT_GUIDANCE = """
GENERAL PRINCIPLE

Response styles provide context for interpreting the personality
profile. They are not personality traits, measures of ability,
measures of suitability or proof of honesty.

They may help the practitioner understand how the candidate approached
the questionnaire and how much additional exploration may be useful.


SOCIAL DESIRABILITY

LOW
- May indicate a relatively self-critical way of describing oneself.
- Some personality preferences may be stronger than the displayed
  profile initially suggests.
- Do not assume low confidence or lack of capability.
- A useful next step is to ask the candidate which two or three traits
  someone who knows them well might rate more strongly.
- Invite the candidate to identify qualities they may have understated.

TYPICAL
- Usually suggests a reasonably balanced self-presentation.
- There is no clear tendency towards either overly critical or overly
  positive self-description.
- The personality profile may generally be interpreted in the usual way,
  while still validating important findings with examples.

HIGH
- May indicate a positive self-presentation.
- Some preferences may be less pronounced than the profile initially
  suggests.
- This must not be interpreted as dishonesty.
- A useful next step is to ask which two or three traits the candidate
  may possibly have rated somewhat generously.
- Validate strong results through specific behavioural examples.


PROFILE SPREAD

LOW
- The responses show less differentiation or consistency across
  questions connected to the same personality traits.
- This may have several possible explanations and none should be stated
  as fact.
- Possible areas to explore include:
  - whether the current role matches the person's natural preferences
  - a recent change of role, tasks, goals or responsibilities
  - a role that requires several different behaviours
  - strong situational adaptability
  - the influence of the current environment, manager or team
  - reluctance to take a firm position on some questions
  - uncertainty about how the person typically behaves
- Use neutral questions and explore context before drawing conclusions.

TYPICAL
- The candidate appears to have responded consistently in some parts
  of the questionnaire and with more variation in others.
- Clearer extremes in the personality profile may be the areas in which
  the candidate responded most consistently.
- Validate the most important findings and allow the candidate to add
  situational nuance.

HIGH
- The profile shows clear differentiation across the personality traits.
- The candidate appears to have responded consistently to questions
  connected to the same traits.
- The candidate may be more likely to recognise themselves in the
  resulting personality profile.
- Strong differences should still be explored rather than treated as
  fixed behaviour.


RATINGS SPREAD

LOW
- The candidate used a relatively narrow range of response options and
  made less use of the extreme ends of the scale.
- The candidate may be inclined to qualify answers or explain that their
  behaviour depends on the situation.
- Allow additional time during feedback.
- Use concrete examples and follow-up questions to help the candidate
  clarify where their preferences are strongest.

TYPICAL
- The candidate appears to have used the response scale without a strong
  preference for either neutral or extreme options.
- The profile may generally be interpreted in the usual way while still
  validating important conclusions with examples.

HIGH
- The candidate used a broad range of response options, including the
  more extreme ends of the scale.
- The candidate may express preferences and positions relatively clearly.
- Strong results should still be validated with examples and should not
  automatically be interpreted as fixed or inflexible behaviour.


KNOWN COMBINATION: PROFILE SPREAD HIGH AND RATINGS SPREAD HIGH

- The candidate used a broad range of ratings and appears to have
  responded consistently across related questions.
- The candidate may be relatively likely to recognise themselves in the
  personality profile.
- Consider the candidate's current situation when discussing why
  particular traits are especially pronounced.


KNOWN COMBINATION: PROFILE SPREAD LOW AND RATINGS SPREAD HIGH

- The candidate used clear or extreme ratings, while responses across
  questions connected to the same traits showed less consistency.
- Do not label this as poor self-awareness.
- Explore whether the pattern may relate to:
  - recent changes in role or responsibilities
  - a role requiring several different behaviours
  - strong situational adaptation
  - the influence of a manager, team or working environment
  - uncertainty about which situation to use as the reference point
  - a wish to present oneself in a particular way
- Treat the profile as a starting point for discussion and ask for
  concrete examples from different situations.
""".strip()


def build_response_style_evidence(
    response_styles: list[dict[str, Any]],
) -> tuple[str, dict[str, dict[str, Any]]]:
    """
    Convert the calculated response-style results into compact
    evidence for the AI prompt.
    """

    evidence_lines = []
    evidence_by_key = {}

    for style in response_styles or []:
        if not style.get("available"):
            continue

        key = (
            style.get("key")
            or ""
        ).strip()

        title = (
            style.get("title")
            or key
            or "Response style"
        ).strip()

        value = style.get("value")
        band_key = (
            style.get("band_key")
            or ""
        ).strip()

        band_label = (
            style.get("band_label")
            or ""
        ).strip()

        interpretation = (
            style.get("interpretation")
            or ""
        ).strip()

        low_pole = (
            style.get("low_pole")
            or ""
        ).strip()

        high_pole = (
            style.get("high_pole")
            or ""
        ).strip()

        evidence_by_key[key] = {
            "key": key,
            "title": title,
            "value": value,
            "band_key": band_key,
            "band_label": band_label,
            "interpretation": interpretation,
            "low_pole": low_pole,
            "high_pole": high_pole,
        }

        evidence_lines.append(
            "\n".join([
                f"{title}",
                f"- Internal key: {key}",
                f"- Rounded STEN: {value}",
                f"- Result band: {band_label} ({band_key})",
                f"- Current interpretation: {interpretation}",
                f"- Lower end of scale: {low_pole}",
                f"- Higher end of scale: {high_pole}",
            ])
        )

    if not evidence_lines:
        return (
            "No response-style results are available.",
            {},
        )

    return (
        "\n\n".join(evidence_lines),
        evidence_by_key,
    )


def build_response_style_guidance_prompt(
    *,
    guidance_owner,
    response_styles: list[dict[str, Any]],
) -> str:
    """
    Build the AI prompt for the response-style interpretation box.

    guidance_owner may be either:
    - TestInvitation
    - HistoricalProcessCandidate
    """

    shared_context = build_shared_ai_context(
        guidance_owner
    )

    candidate = shared_context["candidate"]
    process = shared_context["process"]

    purpose_label = shared_context["purpose_label"]
    context_text = shared_context["context_text"]
    context_data = shared_context["context_data"]

    response_style_text, evidence_by_key = (
        build_response_style_evidence(
            response_styles
        )
    )

    if not evidence_by_key:
        raise ValueError(
            "No response-style results are available."
        )

    has_added_context = bool(
        context_data
    )

    if has_added_context:
        context_instruction = """
Use the selected process purpose and supplied context only when
formulating the practical interview or feedback advice.

The context must not change the psychometric meaning of the
response-style scores.
""".strip()
    else:
        context_instruction = """
Provide general practical advice because no additional process context
has been supplied.

Do not invent a role, team, development objective or organisational
requirement.
""".strip()

    return f"""
You are generating an AI-supported interpretation of questionnaire
response styles for Talena, an assessment and talent management
platform.

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

PROCESS PURPOSE
{purpose_label}

PROCESS CONTEXT
{context_text}

RESPONSE-STYLE RESULTS
{response_style_text}

EXPERT INTERPRETATION GUIDANCE
{RESPONSE_STYLE_EXPERT_GUIDANCE}

CONTEXT INSTRUCTION
{context_instruction}

YOUR TASK

Explain how the response-style results should influence the way the
personality profile is interpreted and discussed with the candidate.

The output should help a recruiter, manager, coach or assessment
practitioner understand:

- what the combined response pattern may indicate
- what should be interpreted cautiously
- how to approach feedback or interview discussion
- which questions may help validate the profile
- whether a known combination pattern applies

IMPORTANT SAFETY AND INTERPRETATION RULES

- Base every conclusion on the supplied response-style results and
  expert guidance.
- Do not interpret unrelated personality traits.
- Do not invent information about the candidate.
- Do not diagnose poor self-awareness.
- Do not question the candidate's honesty.
- Do not claim that the candidate deliberately manipulated the test.
- Do not treat any response-style result as good or bad.
- Do not describe response styles as measures of ability, performance,
  integrity or suitability.
- Do not make a hiring, promotion or development decision.
- Do not include a percentage, fit score or recommendation verdict.
- Do not repeat raw STEN values in the final wording.
- Use cautious language such as:
  "may indicate",
  "suggests",
  "could reflect",
  "may be useful to explore",
  "should be validated with the candidate".
- Write about the candidate using their first name where natural.
- Write in clear, professional English.
- Keep the guidance practical and reasonably concise.
- Do not overstate known combination rules.
- When no known combination applies, say so neutrally instead of
  inventing a concern.

STREAMING OUTPUT FORMAT

Return newline-delimited JSON, also called NDJSON.

Every JSON object must appear on one single line.
Do not use markdown.
Do not use code fences.
Do not write any text outside the JSON objects.

Return events in this exact order:

1. One meta event:

{{"type":"meta","title":"How to approach this profile","label":"AI-supported interpretation"}}

2. Between 3 and 6 summary_delta events:

{{"type":"summary_delta","text":"First part of the interpretation. "}}
{{"type":"summary_delta","text":"Next part of the interpretation. "}}

Together, the summary should be approximately 80 to 130 words.
It should explain the overall combined response pattern and the most
important implication for reading the personality profile.

3. One how_to_interpret event:

{{"type":"how_to_interpret","text":"One or two concise sentences explaining what should be kept in mind when reading the personality traits."}}

4. One recommended_approach event:

{{"type":"recommended_approach","text":"One or two concise sentences describing how to approach the interview or feedback conversation."}}

5. One questions event containing exactly 3 questions:

{{"type":"questions","items":["Question one","Question two","Question three"]}}

The questions must:
- be phrased directly to the candidate
- be open and non-accusatory
- help validate or add context to the response pattern
- reflect the supplied purpose or context when relevant

6. One combination_note event:

{{"type":"combination_note","text":"Explain whether a known combination pattern applies and what it may be useful to explore. If no known combination applies, provide a short neutral note."}}

7. One context_note event:

{{"type":"context_note","text":"Briefly explain whether the advice was adapted to process purpose or added context."}}

8. One final done event:

{{"type":"done"}}
""".strip()


def create_empty_response_style_guidance(
    guidance_owner,
) -> dict[str, Any]:
    return {
        "title": "How to approach this profile",
        "label": "AI-supported interpretation",
        "summary": "",
        "how_to_interpret": "",
        "recommended_approach": "",
        "questions": [],
        "combination_note": "",
        "context_note": "",
    }


def apply_response_style_guidance_event(
    guidance: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one streamed NDJSON event to the complete guidance result.
    """

    event_type = event.get("type")

    if event_type == "meta":
        title = str(
            event.get("title")
            or ""
        ).strip()

        label = str(
            event.get("label")
            or ""
        ).strip()

        if title:
            guidance["title"] = title

        if label:
            guidance["label"] = label

    elif event_type == "summary_delta":
        guidance["summary"] += str(
            event.get("text")
            or ""
        )

    elif event_type == "how_to_interpret":
        guidance["how_to_interpret"] = str(
            event.get("text")
            or ""
        ).strip()

    elif event_type == "recommended_approach":
        guidance["recommended_approach"] = str(
            event.get("text")
            or ""
        ).strip()

    elif event_type == "questions":
        items = event.get("items")

        if isinstance(items, list):
            guidance["questions"] = [
                str(item).strip()
                for item in items[:3]
                if str(item).strip()
            ]

    elif event_type == "combination_note":
        guidance["combination_note"] = str(
            event.get("text")
            or ""
        ).strip()

    elif event_type == "context_note":
        guidance["context_note"] = str(
            event.get("text")
            or ""
        ).strip()

    return guidance


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
        event = json.loads(
            line
        )
    except json.JSONDecodeError:
        return None

    if not isinstance(event, dict):
        return None

    if not event.get("type"):
        return None

    return event


def stream_response_style_guidance(
    *,
    guidance_owner,
    response_styles: list[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
    """
    Stream parsed response-style guidance events from OpenAI.

    Each yielded value is a dictionary. The view will convert each
    dictionary into NDJSON for the browser.
    """

    prompt = build_response_style_guidance_prompt(
        guidance_owner=guidance_owner,
        response_styles=response_styles,
    )

    client = get_openai_client()

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful psychometric assessment "
                    "interpretation assistant. Follow the requested "
                    "NDJSON format exactly and do not make unsupported "
                    "claims."
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

        if (
            not delta
            or not delta.content
        ):
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


def save_response_style_guidance(
    *,
    guidance_owner,
    guidance: dict[str, Any],
):
    """
    Save completed response-style guidance on either a
    TestInvitation or HistoricalProcessCandidate.
    """

    guidance["summary"] = (
        guidance.get("summary")
        or ""
    ).strip()

    guidance["how_to_interpret"] = (
        guidance.get("how_to_interpret")
        or ""
    ).strip()

    guidance["recommended_approach"] = (
        guidance.get("recommended_approach")
        or ""
    ).strip()

    guidance["combination_note"] = (
        guidance.get("combination_note")
        or ""
    ).strip()

    guidance["context_note"] = (
        guidance.get("context_note")
        or ""
    ).strip()

    questions = guidance.get(
        "questions"
    )

    if not isinstance(questions, list):
        questions = []

    guidance["questions"] = [
        str(question).strip()
        for question in questions[:3]
        if str(question).strip()
    ]

    guidance_owner.ai_response_style_guidance = (
        guidance
    )

    guidance_owner.ai_response_style_guidance_status = (
        "completed"
    )

    guidance_owner.ai_response_style_guidance_generated_at = (
        timezone.now()
    )

    guidance_owner.ai_response_style_guidance_purpose = (
        get_process_purpose_key(
            guidance_owner.process
        )
    )

    guidance_owner.save(update_fields=[
        "ai_response_style_guidance",
        "ai_response_style_guidance_status",
        "ai_response_style_guidance_generated_at",
        "ai_response_style_guidance_purpose",
    ])