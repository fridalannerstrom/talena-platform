from __future__ import annotations

from .candidate_name_privacy import redact_candidate_name

import json
import math
from typing import Any, Iterable

from apps.core.motivation_factor_names import MOTIVATION_FACTOR_NAMES_SV
from django.utils import timezone

from .openai_client import (
    get_openai_client,
    get_chat_model,
)
from .language import (
    get_ai_language_instruction,
    get_ai_language_update_fields,
    get_ai_system_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)

# Talena motivation AI language batch 1

from .shared_context import (
    build_shared_ai_context,
    get_process_purpose_key,
)

from .prompt_templates import (
    get_ai_prompt_instructions,
    get_ai_feature_prompt_instructions,
)

MOTIVATION_DEFINITIONS = {
    "attachment": (
        "Value social interaction with others at work. This is a primary driver for them. Enjoys the feeling of belonging to a team and is driven by developing strong bonds and good working relationships."
    ),
    "customer_service": (
        "Thrives in a customer-oriented role where they get to help and support others. Values building relationships with customers and understanding customer needs. Places great emphasis on meeting and exceeding customer needs and expectations."
    ),
    "work_life_balance": (
        "Values work-life balance so they can fulfil their commitments both at work and outside. Looks for clear boundaries so they can switch off at the end of the workday and devote that time to other activities that are important."
    ),
    "people_development": (
        "Helps and supports others and actively contributes to their development. Enjoys guiding others through difficult times and helping others overcome adversity or challenges. Offers proactive support so others can grow."
    ),
    "stability": (
        "Wants to feel secure at work and will probably prefer to work in an industry or organisation they see as stable. Places importance on feeling that their position at work is secure and is likely to be more concerned with having stability in their role."
    ),
    "authority": (
        "Values the opportunity to take on leadership positions and the opportunity for promotion. Appreciates roles where there is room to set direction, organise others and ensure work is done properly."
    ),
    "acquisition": (
        "Is motivated by financial reward and by working in a well-paid role so they can afford the things they want without having to worry about costs. The focus on salary and benefits is strong; attractive remuneration is motivating."
    ),
    "independence": (
        "Values the freedom to make their own decisions about how to plan their time and organise their work. Performs at their best when trusted to set their own work direction and complete their work in the way they see fit."
    ),
    "recognition": (
        "Is motivated by recognition, praise and appreciation. Prioritises activities or projects that are visible in the organisation so others can see the work they do and the value they add. Positive feedback and praise are motivating for them."
    ),
    "making_a_difference": (
        "Wants to feel that they make a positive difference to others. Considers it important to be part of an organisation whose goals and purpose seem worthwhile to them, and to be able to see how their work has a beneficial impact on society at large."
    ),
    "achievement": (
        "Is energised by defined and challenging goals to work towards. Professionally challenging opportunities are important; thrives on competition and an environment where they have the opportunity to compare their performance to others."
    ),
    "quality": (
        "Is motivated by delivering high-quality results on a consistent basis. Takes pride in producing work that is in line with both what they have promised and what is expected of them. Ensures their work is completed as perfectly as possible."
    ),
    "learning": (
        "Is driven by the opportunity to learn and develop their expertise. Feels comfortable in an environment where there are plenty of opportunities for ongoing training and development to master new skills."
    ),
    "ethics": (
        "Maintains high ethical standards for themselves and the organisation they work for. Adheres to industry guidelines and best-practice requirements. Takes pride in their professional integrity and enjoys working in an organisation whose ethical values are in line with their own."
    ),
    "commercial_focus": (
        "Thrives in a commercially focused role and contributes to the organisation's financial success. Values seeing the connection between their role and the organisation's results. Gains energy from seeing how their work leads to commercial profit."
    ),
    "curiosity": (
        "Explores and discovers new things. Pursues knowledge and experience, takes advantage of opportunities for new experiences and new information, and explores the things that capture their interest."
    ),
    "creativity": (
        "Enjoys exercising creativity, thinking outside the box, generating new ideas and identifying new solutions. Ideas and suggestions are likely to be useful, not just original for the sake of being different or unique."
    ),
    "enjoyment": (
        "Values an environment where they enjoy their work but can also have fun with their colleagues. Thrives in an easy-going environment where they can express their playful side, share humour with colleagues and be accepted for who they are."
    ),
    "variety": (
        "Is motivated by a role that offers a lot of variety and the opportunity to work with many different things. Thrives in a diverse role with a mix of tasks and projects where they can focus their attention on different work demands and take advantage of their different skills."
    ),
    "risk": (
        "Is motivated by risk at work and by having to face situations where the outcome is unclear. Is comfortable making risky decisions and thrives in roles that allow room to experience the thrill of taking a risk and then seeing if it pays off."
    ),
}

# Canonicalise Sova and legacy aliases before looking up the source definition.
MOTIVATION_FACTOR_ALIASES = {
    "attachment": "attachment",
    "affiliation": "attachment",
    "customer service": "customer_service",
    "customer focus": "customer_service",
    "work life balance": "work_life_balance",
    "work-life balance": "work_life_balance",
    "people development": "people_development",
    "developing people": "people_development",
    "stability": "stability",
    "security": "stability",
    "authority": "authority",
    "acquisition": "acquisition",
    "reward": "acquisition",
    "financial reward": "acquisition",
    "independence": "independence",
    "autonomy": "independence",
    "self determination": "independence",
    "self direction": "independence",
    "recognition": "recognition",
    "making a difference": "making_a_difference",
    "make a difference": "making_a_difference",
    "purpose": "making_a_difference",
    "achievement": "achievement",
    "performance": "achievement",
    "quality": "quality",
    "learning": "learning",
    "development": "learning",
    "ethics": "ethics",
    "ethical standards": "ethics",
    "commercial focus": "commercial_focus",
    "commercial value": "commercial_focus",
    "commercially focused": "commercial_focus",
    "curiosity": "curiosity",
    "creativity": "creativity",
    "enjoyment": "enjoyment",
    "joy": "enjoyment",
    "fun": "enjoyment",
    "variety": "variety",
    "variation": "variety",
    "risk": "risk",
    "risk taking": "risk",
    "anknytning": "attachment",
    "kundservice": "customer_service",
    "balans mellan arbete och privatliv": "work_life_balance",
    "människors utveckling": "people_development",
    "självständighet": "independence",
    "erkännande": "recognition",
    "göra skillnad": "making_a_difference",
    "prestation": "achievement",
    "kvalité": "quality",
    "kvalitet": "quality",
    "lärande": "learning",
    "etik": "ethics",
    "kommersiellt fokus": "commercial focus",
    "nyfikenhet": "curiosity",
    "kreativitet": "creativity",
    "glädje": "enjoyment",
    "stabilitet": "stability",
    "auktoritet": "authority",
    "anskaffning": "acquisition",
}


def _motivation_definition_key(value: Any) -> str:
    key = _normalise_name(value).casefold().replace("_", " ").replace("-", " ")
    canonical_key = MOTIVATION_FACTOR_ALIASES.get(key, key)
    return canonical_key.replace(" ", "_") if canonical_key in {
        "customer service",
        "work life balance",
        "people development",
        "making a difference",
        "commercial focus",
    } else canonical_key

def get_motivation_factor_display_name(
    value: Any,
    *,
    language_code: str | None = None,
) -> str:
    """Return a factor name in the requested output language."""
    name = _normalise_name(value)
    language = normalize_ai_language(language_code)
    if language != "sv":
        return name

    key = _motivation_definition_key(name)
    return MOTIVATION_FACTOR_NAMES_SV.get(key, name)


def _normalise_name(value: Any) -> str:
    return str(value or "").strip()


def normalise_motivation_score(value: Any) -> int | float | None:
    """
    Return the exact usable STIVE value without rounding away decimals.

    Motivation is a five-point scale, but Sova can provide a more precise
    value alongside the rounded display value. The precise value must be
    retained for ranking and AI evidence construction.
    """
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


def _format_motivation_score(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def extract_motivation_results(
    invitation,
) -> list[dict[str, Any]]:
    """
    Extract available motivation results from Sova activities.

    Motivation scores use Sova's five-point STIVE scale; precise values are retained.
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

        competencies = (
            activity.get("competencies")
            or []
        )

        looks_like_motivation = any(
            keyword in activity_name_lower
            for keyword in (
                "motivation",
                "motivational",
                "motivator",
                "mq",
            )
        )

        for competency in competencies:
            competency_name = _normalise_name(
                competency.get("competency")
                or competency.get("name")
            )

            if not competency_name:
                continue

            competency_key = _motivation_definition_key(
                competency_name
            )

            # Only a clearly identified motivation activity may
            # contribute motivation evidence. A personality trait such as
            # "Creativity" must never be accepted merely because the name
            # also exists in the motivation factor dictionary.
            if not looks_like_motivation:
                continue

            # Prefer the precise STIVE value. The rounded
            # field is only a compatibility fallback for older payloads.
            score = normalise_motivation_score(
                competency.get("stive")
            )

            if score is None:
                score = normalise_motivation_score(
                    competency.get("stive_rounded")
                )

            if score is None:
                continue

            results_by_name[competency_key] = {
                "name": competency_name,
                "score": score,
                "definition": (
                    MOTIVATION_DEFINITIONS.get(
                        competency_key,
                        "",
                    )
                ),
            }

    return list(
        results_by_name.values()
    )


def build_motivation_evidence_text(
    results: list[dict[str, Any]],
) -> str:
    if not results:
        return (
            "No motivation assessment results are available."
        )

    sorted_results = sorted(
        results,
        key=lambda item: (
            -item["score"],
            item["name"].lower(),
        ),
    )

    lines = [
        "SCALE INTERPRETATION",
        "",
        "These are Sova Motivation Questionnaire results on the "
        "five-point STIVE scale.",
        "",
        "A higher score means that the factor is more likely to be "
        "a prominent source of motivation, energy or engagement.",
        "",
        "A lower score means that the factor is less central as a "
        "source of motivation for this individual.",
        "",
        "IMPORTANT:",
        "- A low score does NOT mean poor performance.",
        "- A low score does NOT mean low ability or competence.",
        "- A low score does NOT mean the candidate lacks the quality "
        "described by the factor.",
        "- Interpret each score only as the relative motivational "
        "importance of that factor.",
        "",
        "MOTIVATION FACTORS",
    ]

    for result in sorted_results:
        definition = (
            result.get("definition")
            or MOTIVATION_DEFINITIONS.get(
                result["name"].strip().lower(),
                "",
            )
        )

        lines.append("")
        lines.append(
            f"- {result['name']}: STIVE "
            f"{_format_motivation_score(result['score'])} of 5"
        )

        if definition:
            lines.append(
                f"  Meaning: {definition}"
            )

        if result["score"] >= 4:
            lines.append(
                "  Score meaning: More prominent motivational driver."
            )
        elif result["score"] <= 2:
            lines.append(
                "  Score meaning: Less central motivational driver."
            )
        else:
            lines.append(
                "  Score meaning: Mid-range motivational importance."
            )

    return "\n".join(lines)


def build_motivation_interpretation_prompt(
    invitation,
    motivation_results: list[dict[str, Any]],
    *,
    language_code: str = "en",
) -> str:
    """
    Build Talena's motivation interpretation prompt.

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
        key="motivation_interpretation",
        language=language_code,
    )

    expectation_setting_instructions = get_ai_feature_prompt_instructions(
        key="motivation_expectation_setting",
        language=language_code,
    )

    engagement_conditions_instructions = get_ai_feature_prompt_instructions(
        key="motivation_engagement_conditions",
        language=language_code,
    )

    areas_to_clarify_instructions = get_ai_feature_prompt_instructions(
        key="motivation_areas_to_clarify",
        language=language_code,
    )

    shared_context = build_shared_ai_context(
        invitation
    )

    candidate = shared_context["candidate"]

    purpose_label = shared_context["purpose_label"]
    context_text = shared_context["context_text"]

    evidence_text = build_motivation_evidence_text(
        motivation_results
    )

    return f"""
TALENA INPUT DATA

CANDIDATE
Reference: CANDIDATE_A

SELECTED PROCESS PURPOSE
Purpose: {purpose_label}

PROCESS CONTEXT
{context_text or "No additional process context supplied."}

MOTIVATION ASSESSMENT DATA
{evidence_text}


ADMINISTRATOR AI GUIDANCE


OVERALL MOTIVATION INTERPRETATION GUIDANCE

The following administrator guidance applies only to the
overall motivation interpretation returned through
interpretation_delta events.

Do not use this guidance to determine the substantive content of
expectation_setting, engagement_conditions or areas_to_clarify.

If this guidance contains older instructions relating to those
sections, the dedicated section guidance below takes precedence.

{admin_instructions}


REALISTIC EXPECTATION SETTING GUIDANCE

The following administrator guidance applies only to the
expectation_setting event.

Do not use it to change the overall interpretation,
engagement conditions or areas to clarify.

{expectation_setting_instructions}


CONDITIONS LIKELY TO SUPPORT ENGAGEMENT GUIDANCE

The following administrator guidance applies only to the
engagement_conditions event.

Do not use it to change the overall interpretation,
expectation setting or areas to clarify.

{engagement_conditions_instructions}


WHAT TO EXPLORE OR CLARIFY GUIDANCE

The following administrator guidance applies only to the
areas_to_clarify event.

Do not use it to change the overall interpretation,
expectation setting or engagement conditions.

{areas_to_clarify_instructions}


SECTION ISOLATION

Treat each dedicated section guidance as authoritative for its
corresponding event.

Instructions for one section must not change the substantive
content, number of items or emphasis of another section.

Global Talena administrator guidance still applies across all sections.

Do not allow administrator guidance to change Talena's technical
event structure, required JSON fields or streaming format.


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

Return one meta event:

{{"type":"meta","title":"Motivation interpretation","label":"AI-supported interpretation"}}


2. INTERPRETATION CONTENT

Return the overall interpretation using one or more
interpretation_delta events:

{{"type":"interpretation_delta","text":"First part of the interpretation. "}}

{{"type":"interpretation_delta","text":"Next part of the interpretation. "}}


3. ENGAGEMENT CONDITIONS

Return one engagement_conditions event.

The items array may contain the number of items requested by the
administrator guidance:

{{"type":"engagement_conditions","items":["Condition one","Condition two"]}}


4. AREAS TO CLARIFY

Return one areas_to_clarify event.

The items array may contain the number of items requested by the
administrator guidance:

{{"type":"areas_to_clarify","items":["Clarification one","Clarification two"]}}


5. EXPECTATION SETTING

Return one expectation_setting event:

{{"type":"expectation_setting","text":"Expectation-setting content."}}

If administrator guidance does not require substantive content here,
return an empty text value while preserving the technical event.


6. CONTEXT NOTE

Return one context_note event:

{{"type":"context_note","text":"Brief explanation of the evidence and context used."}}


7. DONE

Finish with:

{{"type":"done"}}
""".strip()

def create_empty_motivation_interpretation(
    owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
    language_code = normalize_ai_language(
        language_code
    )

    return {
        "title": (
            "Motivationstolkning"
            if language_code == "sv"
            else "Motivation interpretation"
        ),
        "label": (
            "AI-stödd tolkning"
            if language_code == "sv"
            else "AI-supported interpretation"
        ),
        "interpretation": "",
        "engagement_conditions": [],
        "areas_to_clarify": [],
        "expectation_setting": "",
        "context_note": "",
    }



def apply_motivation_interpretation_event(
    interpretation: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply one streamed event to the complete saved result.
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

    elif event_type == "engagement_conditions":
        items = event.get("items")

        if isinstance(items, list):
            interpretation["engagement_conditions"] = [
                str(item).strip()
                for item in items
                if str(item).strip()
            ]

    elif event_type == "areas_to_clarify":
        items = event.get("items")

        if isinstance(items, list):
            interpretation["areas_to_clarify"] = [
                str(item).strip()
                for item in items
                if str(item).strip()
            ]

    elif event_type == "expectation_setting":
        interpretation["expectation_setting"] = str(
            event.get("text")
            or ""
        ).strip()

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

def get_motivation_interpretation_system_prompt(
    language_code: str = "en",
    *,
    owner=None,
) -> str:
    """
    Return Talena's technical system instructions for
    motivation interpretation generation.
    """

    language_code = normalize_ai_language(
        language_code
    )

    system_language_instruction = (
        get_ai_system_language_instruction(
            language_code,
            owner=owner,
        )
    )

    return (
        "You are an AI component inside Talena. "
        "Follow the administrator-provided AI guidance for "
        "all non-technical analysis, motivation interpretation "
        "and communication decisions. "
        "Follow Talena's technical output contract exactly, "
        "including required JSON structure, field names, "
        "event types and streaming format. "
        f"{system_language_instruction}"
    )

def stream_motivation_interpretation(
    *,
    owner,
    motivation_results: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
    """
    Stream motivation interpretation events from OpenAI.

    Motivation questions are generated independently in
    motivation_questions.py.
    """

    if not motivation_results:
        raise ValueError(
            "No motivation assessment results are available."
        )

    language_code = normalize_ai_language(
        language_code
    )

    system_prompt = (
        get_motivation_interpretation_system_prompt(
            language_code,
            owner=owner,
        )
    )

    client = get_openai_client()

    prompt = build_motivation_interpretation_prompt(
        invitation=owner,
        motivation_results=motivation_results,
        language_code=language_code,
    )

    prompt = redact_candidate_name(prompt, owner.candidate)

    stream = client.chat.completions.create(
        model=get_chat_model(),

        messages=[
            {
                "role": "system",
                "content": system_prompt,
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
        choices = getattr(
            response_event,
            "choices",
            None,
        )

        if not choices:
            continue

        delta = getattr(
            choices[0],
            "delta",
            None,
        )

        content = getattr(
            delta,
            "content",
            None,
        )

        if not content:
            continue

        buffer += content

        while "\n" in buffer:
            raw_line, buffer = buffer.split(
                "\n",
                1,
            )

            event = _parse_event_line(
                raw_line
            )

            if event:
                yield event

    final_event = _parse_event_line(
        buffer
    )

    if final_event:
        yield final_event

def save_motivation_interpretation(
    *,
    owner,
    interpretation: dict[str, Any],
    language_code: str = "en",
):
    """
    Save the completed motivation interpretation.
    """

    language_code = normalize_ai_language(
        language_code
    )
    interpretation["_language"] = language_code

    set_ai_content_language(
        owner,
        "motivation_interpretation",
        language_code,
    )

    interpretation["interpretation"] = (
        interpretation.get("interpretation")
        or ""
    ).strip()

    owner.ai_motivation_interpretation = (
        interpretation
    )

    owner.ai_motivation_interpretation_status = (
        "completed"
    )

    owner.ai_motivation_interpretation_generated_at = (
        timezone.now()
    )

    owner.ai_motivation_interpretation_purpose = (
        get_process_purpose_key(
            owner.process
        )
    )

    owner.save(update_fields=[
        "ai_motivation_interpretation",
        "ai_motivation_interpretation_status",
        "ai_motivation_interpretation_generated_at",
        "ai_motivation_interpretation_purpose",
    ])

    language_update_fields = (
        get_ai_language_update_fields(
            owner
        )
    )
    if language_update_fields:
        owner.save(
            update_fields=language_update_fields
        )