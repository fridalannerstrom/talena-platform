from __future__ import annotations

from .candidate_name_privacy import redact_candidate_name

import json
from typing import Any, Iterable

from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)
from django.utils import timezone

from .openai_client import get_openai_client, get_chat_model
from .language import (
    get_ai_language_instruction,
    get_ai_system_language_instruction,
    get_purpose_fit_output_examples,
    normalize_ai_language,
    set_ai_content_language,
)

from .prompt_templates import (
    get_ai_prompt_instructions,
    get_ai_feature_prompt_instructions,
)

from .motivation_interpretation import (
    get_motivation_factor_display_name,
    build_motivation_top_three_evidence,
    build_motivation_summary_supplement,
)
from apps.processes.services.cognitive_insights import (
    build_owner_cognitive_ai_evidence,
    build_owner_cognitive_summary_supplement,
)
from .personality_ai_evidence import (
    build_owner_personality_ai_evidence_text,
)

# Talena AI Overview language batch 1


PURPOSE_FIT_TITLES = {
    # Recruitment
    "hiring": "Role fit",
    "recruitment": "Role fit",

    # Role matching
    "role_match": "Role alignment",
    "internal_role_match": "Role alignment",

    # Leadership
    "leadership_potential": "Leadership potential fit",
    "leader_development": "Leadership development focus",

    # Development
    "employee_development": "Development fit",
    "career_path": "Development fit",

    # Onboarding
    "onboarding": "Onboarding fit",

    # Team
    "team_development": "Team contribution",

    # Change
    "reorganisation": "Change and transition fit",
    "reorganization": "Change and transition fit",
}


ALLOWED_RECOMMENDATIONS = {
    "Strong alignment",
    "Potential alignment",
    "Mixed alignment",
    "Limited alignment",
    "Insufficient context",
}


ALLOWED_CONFIDENCE_LEVELS = {
    "Low",
    "Medium",
    "High",
}




def get_purpose_fit_title(process) -> str:
    purpose_key = get_process_purpose_key(
        process
    )

    return PURPOSE_FIT_TITLES.get(
        purpose_key,
        "Purpose fit",
    )


def purpose_supports_fit(process) -> bool:
    """
    AI Overview is available for every active process.

    When no specific purpose is selected, Talena should generate
    a general assessment-based overview instead of a purpose-specific
    interpretation.
    """
    return True


def _has_score(competency: dict[str, Any]) -> bool:
    return any(
        competency.get(field_name) is not None
        for field_name in (
            "score",
            "sten",
            "sten_rounded",
            "stive",
            "stive_rounded",
            "percentile",
        )
    )


def _assessment_activity_evidence_label(value: Any) -> str:
    """Replace Sova's internal activity codes with readable assessment labels."""
    activity = str(value or "").strip()
    normalized = activity.casefold().replace("_", " ").replace("-", " ")
    padded = f" {normalized} "

    if "motivation" in normalized or " mq " in padded:
        return "Motivation"
    if "personality" in normalized or " pq " in padded:
        return "Personality"
    if "verbal" in normalized:
        return "Verbal reasoning"
    if "numerical" in normalized or "numeric" in normalized:
        return "Numerical reasoning"
    if "logical" in normalized:
        return "Logical reasoning"
    if "team" in normalized:
        return "Team styles"

    # Opaque Sova keys should never be exposed as assessment evidence labels.
    if "_" in activity or any(character.isdigit() for character in activity):
        return "Assessment results"
    return activity or "Assessment results"


def build_assessment_evidence(
    invitation,
    *,
    language_code: str = "en",
) -> tuple[str, int]:
    """
    Build compact assessment evidence for the AI prompt.

    Returns:
        tuple:
        - formatted assessment evidence
        - number of assessment types containing real results
    """

    # ---------------------------------------------------------
    # HISTORICAL CANDIDATE
    # ---------------------------------------------------------
    #
    # Historical candidates do not have sova_activities.
    # Their imported Sova results are instead normalised through
    # build_historical_candidate_profile().
    #
    if getattr(
        invitation.process,
        "is_historical",
        False,
    ):
        from apps.processes.services.candidate_profile import (
            build_historical_candidate_profile,
        )

        profile = build_historical_candidate_profile(
            invitation
        )

        assessment_sections = []
        completed_result_types = 0

        def add_competency_section(
            title,
            competencies,
        ):
            nonlocal completed_result_types

            result_lines = []

            for competency in competencies or []:
                name = (
                    competency.get("competency")
                    or competency.get("name")
                    or "Unnamed competency"
                )
                if "motivation" in title.casefold():
                    name = get_motivation_factor_display_name(
                        name,
                        language_code=language_code,
                    )

                score_parts = []

                sten = competency.get("sten_rounded")
                if sten is None:
                    sten = competency.get("sten")

                # Prefer precise STIVE; rounded values are fallback only.
                stive = competency.get("stive")
                if stive is None:
                    stive = competency.get("stive_rounded")

                percentile = competency.get("percentile")

                if sten is not None:
                    score_parts.append(
                        f"sten {sten}"
                    )

                if stive is not None:
                    score_parts.append(
                        f"stive {stive}"
                    )

                if percentile is not None:
                    score_parts.append(
                        f"percentile {percentile}"
                    )

                if score_parts:
                    result_lines.append(
                        f"- {name}: "
                        f"{', '.join(score_parts)}"
                    )

            if result_lines:
                assessment_sections.append(
                    f"{title}:\n"
                    + "\n".join(result_lines)
                )

                completed_result_types += 1

        # Personality
        add_competency_section(
            "Personality",
            profile.get(
                "personality_competencies",
                [],
            ),
        )

        # Team styles
        add_competency_section(
            "Team styles",
            profile.get(
                "team_style_scores",
                [],
            ),
        )

        # Motivation
        add_competency_section(
            "Motivation",
            profile.get(
                "motivation_competencies",
                [],
            ),
        )

        # Cognitive abilities
        ability_results = (
            profile.get("ability_results")
            or {}
        )

        ability_lines = []

        for ability_key, ability in ability_results.items():
            if not ability:
                continue

            percentile = ability.get("percentile")

            if percentile is None:
                percentile = ability.get("value")

            if percentile is None:
                continue

            ability_lines.append(
                f"- {ability_key.title()}: "
                f"percentile {percentile}"
            )

        if ability_lines:
            assessment_sections.append(
                "Cognitive abilities:\n"
                + "\n".join(ability_lines)
            )

            completed_result_types += 1

        if not assessment_sections:
            return (
                "No completed assessment results were available.",
                0,
            )

        return (
            "\n\n".join(assessment_sections),
            completed_result_types,
        )

    # ---------------------------------------------------------
    # ACTIVE CANDIDATE
    # ---------------------------------------------------------

    activities = invitation.sova_activities or []
    assessment_sections = []
    completed_result_types = 0

    for activity in activities:
        activity_name = _assessment_activity_evidence_label(
            activity.get("activity")
        )

        competencies = activity.get("competencies") or []

        scored_competencies = [
            competency
            for competency in competencies
            if _has_score(competency)
        ]

        if not scored_competencies:
            continue

        completed_result_types += 1
        result_lines = []

        for competency in scored_competencies:
            competency_name = (
                competency.get("competency")
                or competency.get("name")
                or "Unnamed competency"
            )
            if activity_name == "Motivation":
                competency_name = get_motivation_factor_display_name(
                    competency_name,
                    language_code=language_code,
                )

            score_parts = []

            sten = competency.get("sten_rounded")
            if sten is None:
                sten = competency.get("sten")

            # Prefer precise STIVE; rounded values are fallback only.
            stive = competency.get("stive")
            if stive is None:
                stive = competency.get("stive_rounded")

            percentile = competency.get("percentile")

            if sten is not None:
                score_parts.append(f"sten {sten}")

            if stive is not None:
                score_parts.append(f"stive {stive}")

            if percentile is not None:
                score_parts.append(
                    f"percentile {percentile}"
                )

            if score_parts:
                result_lines.append(
                    f"- {competency_name}: "
                    f"{', '.join(score_parts)}"
                )

        if result_lines:
            assessment_sections.append(
                f"{activity_name}:\n"
                + "\n".join(result_lines)
            )

    if not assessment_sections:
        return (
            "No completed assessment results were available.",
            0,
        )

    return (
        "\n\n".join(assessment_sections),
        completed_result_types,
    )


def calculate_max_confidence(
    *,
    context_data: dict[str, Any],
    assessment_type_count: int,
) -> str:
    """
    Set the maximum confidence the AI is allowed to use.

    Confidence reflects the amount of relevant evidence, not how
    strongly the candidate appears aligned.
    """

    context_field_count = len(context_data)

    if context_field_count == 0:
        return "Low"

    if (
        context_field_count >= 4
        and assessment_type_count >= 2
    ):
        return "High"

    return "Medium"

def build_purpose_fit_prompt(
    invitation,
    *,
    language_code: str = "en",
) -> str:
    """
    Build Talena's AI Overview prompt.

    Administrator guidance controls all non-technical analysis,
    synthesis, interpretation and communication decisions.

    Talena protects only input plumbing and the technical
    streaming/output contract.
    """

    language_code = normalize_ai_language(
        language_code
    )

    language_instruction = get_ai_language_instruction(
        language_code
    )

    output_examples = get_purpose_fit_output_examples(
        language_code
    )

    admin_instructions = get_ai_prompt_instructions(
        key="ai_overview",
        language=language_code,
    )

    supportive_patterns_instructions = get_ai_feature_prompt_instructions(
        key="ai_overview_supportive_patterns",
        language=language_code,
    )

    areas_to_explore_instructions = get_ai_feature_prompt_instructions(
        key="ai_overview_areas_to_explore",
        language=language_code,
    )

    personality_area_guidance = {
        "leadership": get_ai_feature_prompt_instructions(
            key="ai_overview_personality_leadership",
            language=language_code,
        ),
        "organisation": get_ai_feature_prompt_instructions(
            key="ai_overview_personality_organisation",
            language=language_code,
        ),
        "interaction": get_ai_feature_prompt_instructions(
            key="ai_overview_personality_interaction",
            language=language_code,
        ),
    }

    shared_context = build_shared_ai_context(
        invitation
    )

    candidate = shared_context["candidate"]

    assessment_text, _ = build_assessment_evidence(
        invitation,
        language_code=language_code,
    )
    motivation_top_three_text = build_motivation_top_three_evidence(
        invitation,
        language_code=language_code,
    )
    cognitive_interpretation_text = build_owner_cognitive_ai_evidence(
        invitation,
        language_code=language_code,
    )
    # Use Talena's canonical personality evidence builder for this section.
    # The general evidence string may also contain appended grounding under a
    # separate heading, so extracting by section title can accidentally omit
    # the candidate's actual personality results.
    personality_assessment_text = build_owner_personality_ai_evidence_text(
        invitation,
        language_code=language_code,
        include_indicator_details=True,
    )

    if not personality_assessment_text:
        personality_assessment_text = next(
            (
                section
                for section in assessment_text.split("\n\n")
                if section.splitlines()
                and section.splitlines()[0].rstrip(":").strip().casefold()
                in {"personality", "personlighet"}
            ),
            "No completed personality assessment scores were available.",
        )

    return f"""
TALENA INPUT DATA

CANDIDATE
Reference: CANDIDATE_A

SELECTED PROCESS PURPOSE
Purpose: {shared_context["purpose_label"]}
Purpose key: {shared_context["purpose_key"] or "No specific purpose"}

PROCESS CONTEXT
{shared_context["context_text"] or "No additional process context supplied."}

AVAILABLE ASSESSMENT EVIDENCE
{assessment_text}

TOP THREE MOTIVATION FACTORS AND APPROVED INTERPRETATIONS
{motivation_top_three_text}

COGNITIVE RESULTS AND APPROVED INTERPRETATIONS
{cognitive_interpretation_text}

INTERVIEW EVIDENCE LIMIT
No interview notes or interview examples are supplied to AI Overview. Do not claim that interview information confirms or contradicts assessment results. If administrator guidance refers to interviews, make no comparison with interview evidence.

PERSONALITY ASSESSMENT EVIDENCE FOR THE THREE AREA SUMMARIES
{personality_assessment_text}


ADMINISTRATOR AI GUIDANCE


OVERALL INTERPRETATION GUIDANCE

The following administrator guidance applies only to the
overall AI Overview interpretation returned through
summary_delta events.

Do not use this guidance to determine the substantive content
of key_alignment or areas_to_verify.

If this guidance contains older instructions relating to those
sections, the dedicated section guidance below takes precedence.

{admin_instructions}


OVERALL INTERPRETATION COVERAGE

The administrator guidance above remains authoritative for the
interpretation. For summary_delta events, do not silently omit an
assessment domain when its evidence is available:

- Begin with the evidenced personality preferences and use the
  approved personality interpretations.
- When TOP THREE MOTIVATION FACTORS AND APPROVED INTERPRETATIONS
  lists factors, name every listed factor and weave its approved
  interpretation into the personality themes. Explain supported
  ways the factors reinforce or nuance those preferences; do not
  present them as a detached list.
- When COGNITIVE RESULTS AND APPROVED INTERPRETATIONS lists results,
  include a concise statement about each ability result it contains.
  Explain only what the approved interpretation suggests about
  processing new or complex information, and keep it complementary
  to the personality and motivation themes.
- Use the approved interpretation wording rather than reproducing
  raw STEN, STIVE, or percentile values. Do not infer job performance,
  communication ability, or role suitability from cognitive results.
- Weave the available domains into 2–3 connected themes. When
  personality, motivation, and cognitive results are all available,
  write 2–3 substantive paragraphs; a two-sentence personality-only
  overview is incomplete.
- Do not invent or imply results for domains whose evidence says
  they are unavailable.


WHAT SUPPORTS THE PURPOSE GUIDANCE

The following administrator guidance applies only to the
key_alignment event.

For historical candidates this corresponds to
Potentially supportive patterns.

Do not use it to change the overall interpretation
or areas to explore.

{supportive_patterns_instructions}


WHAT TO EXPLORE OR CONSIDER GUIDANCE

The following administrator guidance applies only to the
areas_to_verify event.

Do not use it to change the overall interpretation
or supportive patterns.

{areas_to_explore_instructions}


PERSONALITY AREA SUMMARY GUIDANCE

The following three administrator prompts apply only to their matching
personality_area_summary event. Use only PERSONALITY ASSESSMENT EVIDENCE
FOR THE THREE AREA SUMMARIES. Do not use motivation, ability, process purpose,
role context or outside knowledge in these descriptions.

LEADING AND WORKING WITH OTHERS
{personality_area_guidance["leadership"]}

ORGANISING AND THINKING STYLE
{personality_area_guidance["organisation"]}

INTERACTION AND EMOTIONAL MANAGEMENT
{personality_area_guidance["interaction"]}


SECTION ISOLATION

Treat each dedicated section guidance as authoritative for its
corresponding event.

Instructions for one section must not change the substantive
content, number of items or emphasis of another section.

Global Talena administrator guidance still applies across all sections.

The context_note and suggested_next_step events remain governed
by Talena's existing overall guidance and technical contract.

Do not allow administrator guidance to change Talena's technical
event structure, required JSON fields or streaming format.


TALENA TECHNICAL OUTPUT CONTRACT

The following requirements exist only so Talena can process,
stream, save and display the AI Overview.

Administrator guidance controls the substantive content inside
these fields.

Administrator guidance must not change the required event names,
JSON field names or NDJSON structure.


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

Return:

{{"type":"meta","title":"{output_examples["title"]}","recommendation":"Insufficient context","confidence":"Low"}}

The recommendation and confidence fields are legacy technical
compatibility fields.

Always return exactly:

recommendation = "Insufficient context"
confidence = "Low"

They do not control the substantive AI Overview.


2. OVERALL INTERPRETATION

Return the overall interpretation using one or more
summary_delta events:

{{"type":"summary_delta","text":"{output_examples["summary_1"]}"}}


3. SUPPORTIVE / RELEVANT PATTERNS

Return one key_alignment event.

The administrator guidance determines the number of items:

{{"type":"key_alignment","items":["{output_examples["support_1"]}"]}}


4. AREAS TO EXPLORE OR CONSIDER

Return one areas_to_verify event.

The administrator guidance determines the number of items:

{{"type":"areas_to_verify","items":["{output_examples["consider_1"]}"]}}


5. SUGGESTED NEXT STEP

Return one suggested_next_step event:

{{"type":"suggested_next_step","text":"{output_examples["next_step"]}"}}

If administrator guidance does not require substantive content,
preserve the event using an empty text value.


6. CONTEXT NOTE

Return one context_note event:

{{"type":"context_note","text":"{output_examples["context_note"]}"}}

If administrator guidance does not require substantive content,
preserve the event using an empty text value.


7. PERSONALITY AREA SUMMARIES

Return exactly one personality_area_summary event for each of these area keys,
in this order: leadership, organisation, interaction. Each text must be 2–3
short sentences, use the matching administrator guidance, and describe
possible personality preferences rather than fixed behaviours. Do not include
raw scores. When the personality evidence block contains candidate results,
write a concise evidence-based summary for every area; return empty text only
when the block explicitly states that no completed personality results exist.

{{"type":"personality_area_summary","area":"leadership","text":"Short, evidence-based description."}}

{{"type":"personality_area_summary","area":"organisation","text":"Short, evidence-based description."}}

{{"type":"personality_area_summary","area":"interaction","text":"Short, evidence-based description."}}


8. DONE

Finish with:

{{"type":"done"}}
""".strip()


def create_empty_purpose_fit(invitation) -> dict[str, Any]:
    return {
        "title": get_purpose_fit_title(
            invitation.process
        ),
        "recommendation": "",
        "confidence": "",
        "summary": "",
        "key_alignment": [],
        "areas_to_verify": [],
        "suggested_next_step": "",
        "context_note": "",
        "personality_area_summaries": {
            "leadership": "",
            "organisation": "",
            "interaction": "",
        },
    }


def apply_purpose_fit_event(
    purpose_fit: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one streamed event to the complete JSON result.
    """

    event_type = event.get("type")

    if event_type == "meta":
        recommendation = event.get(
            "recommendation",
            "",
        )

        confidence = event.get(
            "confidence",
            "",
        )

        if recommendation not in ALLOWED_RECOMMENDATIONS:
            recommendation = "Insufficient context"

        if confidence not in ALLOWED_CONFIDENCE_LEVELS:
            confidence = "Low"

        purpose_fit["title"] = (
            event.get("title")
            or purpose_fit["title"]
        )

        purpose_fit["recommendation"] = recommendation
        purpose_fit["confidence"] = confidence

    elif event_type == "summary_delta":
        purpose_fit["summary"] += str(
            event.get("text") or ""
        )

    elif event_type == "key_alignment":
        items = event.get("items")

        if isinstance(items, list):
            purpose_fit["key_alignment"] = [
                str(item).strip()
                for item in items
                if str(item).strip()
            ]

    elif event_type == "areas_to_verify":
        items = event.get("items")

        if isinstance(items, list):
            purpose_fit["areas_to_verify"] = [
                str(item).strip()
                for item in items
                if str(item).strip()
            ]

    elif event_type == "personality_area_summary":
        area = event.get("area")
        if area in {"leadership", "organisation", "interaction"}:
            purpose_fit.setdefault("personality_area_summaries", {})[
                area
            ] = str(event.get("text") or "").strip()

    elif event_type == "suggested_next_step":
        purpose_fit["suggested_next_step"] = str(
            event.get("text") or ""
        ).strip()

    elif event_type == "context_note":
        purpose_fit["context_note"] = str(
            event.get("text") or ""
        ).strip()

    return purpose_fit


def _parse_event_line(
    raw_line: str,
) -> dict[str, Any] | None:
    line = raw_line.strip()

    if not line:
        return None

    # Safety in case the model adds Markdown fences.
    if line in {"```", "```json", "```ndjson"}:
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


def stream_candidate_purpose_fit(
    invitation,
    *,
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
    """
    Stream purpose-fit events from OpenAI.

    Each yielded value is a parsed event dictionary.
    The view will later convert these dictionaries to NDJSON
    and send them to the browser.
    """

    if not purpose_supports_fit(invitation.process):
        raise ValueError(
            "Flexible processes do not support purpose-fit analysis."
        )

    language_code = normalize_ai_language(
        language_code
    )
    system_language_instruction = (
        get_ai_system_language_instruction(
            language_code,
            owner=invitation,
        )
    )

    client = get_openai_client()

    prompt = build_purpose_fit_prompt(
        invitation,
        language_code=language_code,
    )

    prompt = redact_candidate_name(prompt, invitation.candidate)

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI component inside Talena. "
                    "Follow the administrator-provided AI guidance for "
                    "all non-technical assessment analysis, synthesis, "
                    "interpretation and communication decisions. "
                    "Follow Talena's technical output contract exactly, "
                    "including required JSON field names, event types "
                    "and streaming format. "
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
    summary_text = ""
    assessment_coverage_checked = False

    def assessment_coverage_event():
        nonlocal assessment_coverage_checked

        if assessment_coverage_checked:
            return None

        assessment_coverage_checked = True
        supplements = []

        motivation_supplement = build_motivation_summary_supplement(
            invitation,
            summary_text,
            language_code=language_code,
        )
        if motivation_supplement:
            supplements.append(motivation_supplement)

        cognitive_supplement = build_owner_cognitive_summary_supplement(
            invitation,
            summary_text,
            language_code=language_code,
        )
        if cognitive_supplement:
            supplements.append(cognitive_supplement)

        if not supplements:
            return None

        return {
            "type": "summary_delta",
            "text": "\n\n".join(supplements),
        }

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

            if not parsed_event:
                continue

            if parsed_event.get("type") == "summary_delta":
                summary_text += str(parsed_event.get("text") or "")
            elif parsed_event.get("type") == "done":
                supplement_event = assessment_coverage_event()
                if supplement_event:
                    yield supplement_event

            yield parsed_event

    # Parse the final line if the model did not end with newline.
    final_event = _parse_event_line(buffer)

    if final_event:
        if final_event.get("type") == "summary_delta":
            summary_text += str(final_event.get("text") or "")
        elif final_event.get("type") == "done":
            supplement_event = assessment_coverage_event()
            if supplement_event:
                yield supplement_event

        yield final_event

    if not assessment_coverage_checked:
        supplement_event = assessment_coverage_event()
        if supplement_event:
            yield supplement_event


def save_candidate_purpose_fit(
    invitation,
    purpose_fit: dict[str, Any],
    *,
    language_code: str = "en",
):
    """
    Save the completed purpose-fit interpretation.
    """

    # Talena AI Overview result language stamp batch 1
    language_code = normalize_ai_language(
        language_code
    )
    purpose_fit["_language"] = language_code

    purpose_fit["summary"] = (
        purpose_fit.get("summary")
        or ""
    ).strip()

    set_ai_content_language(
        invitation,
        "purpose_fit",
        language_code,
    )

    invitation.ai_purpose_fit = purpose_fit
    invitation.ai_purpose_fit_status = "completed"
    invitation.ai_purpose_fit_generated_at = (
        timezone.now()
    )
    invitation.ai_purpose_fit_purpose = (
        get_process_purpose_key(
            invitation.process
        )
    )

    invitation.save(update_fields=[
        "ai_purpose_fit",
        "ai_purpose_fit_status",
        "ai_purpose_fit_generated_at",
                "ai_purpose_fit_purpose",
        "ai_content_languages",
    ])