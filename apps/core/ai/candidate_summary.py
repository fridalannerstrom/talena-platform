from typing import Iterable
from django.utils import timezone

from .openai_client import get_openai_client, get_chat_model

import json
from typing import Any

from apps.core.ai.language import (
    get_ai_system_language_instruction,
)

from apps.core.ai.language import (
    get_ai_language_instruction,
    get_ai_language_update_fields,
    get_ai_system_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)

from apps.processes.services.candidate_profile import (
    build_historical_candidate_profile,
)

from apps.core.ai.openai_client import (
    get_openai_client,
    get_chat_model,
)

from apps.core.ai.prompt_templates import get_ai_feature_prompt_instructions

from django.forms.models import model_to_dict


def _get_score_parts(
    item: dict,
) -> list[str]:
    parts = []

    sten = item.get("sten_rounded")
    if sten is None:
        sten = item.get("sten")

    # Keep the precise STIVE value in AI Overview evidence.
    stive = item.get("stive")
    if stive is None:
        stive = item.get("stive_rounded")

    percentile = item.get("percentile")

    if sten is not None:
        parts.append(f"sten {sten}")

    if stive is not None:
        parts.append(f"stive {stive}")

    if percentile is not None:
        parts.append(f"percentile {percentile}")

    return parts


def _build_active_summary_assessment_text(
    owner,
) -> str:
    activities = owner.sova_activities or []

    assessment_lines = []

    for activity in activities:
        activity_name = (
            activity.get("activity")
            or "Assessment"
        )

        competencies = (
            activity.get("competencies")
            or []
        )

        result_lines = []

        for competency in competencies:
            competency_name = (
                competency.get("competency")
                or competency.get("name")
                or "Unnamed competency"
            )

            score_parts = _get_score_parts(
                competency
            )

            if not score_parts:
                continue

            result_lines.append(
                f"- {competency_name}: "
                f"{', '.join(score_parts)}"
            )

        if result_lines:
            assessment_lines.append(
                f"{activity_name}:\n"
                + "\n".join(result_lines)
            )

    return (
        "\n\n".join(assessment_lines)
        if assessment_lines
        else "No completed assessment scores were available."
    )


def _build_historical_summary_assessment_text(
    owner,
) -> str:
    profile = build_historical_candidate_profile(
        owner
    )

    assessment_lines = []

    sections = (
        (
            "Personality",
            profile.get(
                "personality_competencies"
            ) or [],
        ),
        (
            "Motivation",
            profile.get(
                "motivation_competencies"
            ) or [],
        ),
    )

    for section_name, items in sections:
        result_lines = []

        for item in items:
            name = (
                item.get("competency")
                or item.get("name")
                or item.get("label")
                or "Unnamed competency"
            )

            score_parts = _get_score_parts(
                item
            )

            if not score_parts:
                continue

            result_lines.append(
                f"- {name}: "
                f"{', '.join(score_parts)}"
            )

        if result_lines:
            assessment_lines.append(
                f"{section_name}:\n"
                + "\n".join(result_lines)
            )

    # Cognitive ability results
    ability_results = (
        profile.get("ability_results")
        or {}
    )

    ability_labels = {
        "logical": "Logical reasoning",
        "numerical": "Numerical reasoning",
        "verbal": "Verbal reasoning",
    }

    ability_lines = []

    for key, label in ability_labels.items():
        result = ability_results.get(key)

        if result is None:
            continue

        if isinstance(result, dict):
            percentile = result.get(
                "percentile"
            )

            if percentile is None:
                percentile = result.get(
                    "value"
                )
        else:
            percentile = result

        if percentile is None:
            continue

        ability_lines.append(
            f"- {label}: percentile {percentile}"
        )

    if ability_lines:
        assessment_lines.append(
            "Cognitive ability:\n"
            + "\n".join(ability_lines)
        )

    return (
        "\n\n".join(assessment_lines)
        if assessment_lines
        else "No completed assessment scores were available."
    )


def _build_personality_summary_assessment_text(owner) -> str:
    """Return personality-only evidence for the three candidate summary areas."""
    process = owner.process

    if getattr(process, "is_historical", False):
        profile = build_historical_candidate_profile(owner)
        items = profile.get("personality_competencies") or []
        result_lines = []
        for item in items:
            name = item.get("competency") or item.get("name") or item.get("label") or "Unnamed competency"
            score_parts = _get_score_parts(item)
            if score_parts:
                result_lines.append(f"- {name}: {', '.join(score_parts)}")
        return "\n".join(result_lines) or "No completed personality assessment scores were available."

    result_lines = []
    for activity in (owner.sova_activities or []):
        activity_name = str(activity.get("activity") or "").strip()
        if not any(token in activity_name.casefold() for token in ("personality", "personlighet", "character", "karaktär", "pq")):
            continue
        for item in activity.get("competencies") or []:
            name = item.get("competency") or item.get("name") or "Unnamed competency"
            score_parts = _get_score_parts(item)
            if score_parts:
                result_lines.append(f"- {name}: {', '.join(score_parts)}")
    return "\n".join(result_lines) or "No completed personality assessment scores were available."


def _build_summary_assessment_text(
    owner,
) -> str:
    process = owner.process

    if getattr(
        process,
        "is_historical",
        False,
    ):
        return (
            _build_historical_summary_assessment_text(
                owner
            )
        )

    return _build_active_summary_assessment_text(
        owner
    )


def build_candidate_prompt(
    owner,
    *,
    language_code: str = "en",
) -> str:
    """
    Build the candidate summary prompt.

    The same prompt and AI generator are used for:
    - TestInvitation
    - HistoricalProcessCandidate

    Only the source of the assessment evidence differs.
    """

    language_code = normalize_ai_language(
        language_code
    )

    candidate = owner.candidate
    process = owner.process

    assessment_text = (
        _build_summary_assessment_text(
            owner
        )
    )
    personality_assessment_text = _build_personality_summary_assessment_text(owner)
    personality_area_guidance = {
        "leadership": get_ai_feature_prompt_instructions(
            key="candidate_personality_leadership", language=language_code
        ),
        "organisation": get_ai_feature_prompt_instructions(
            key="candidate_personality_organisation", language=language_code
        ),
        "interaction": get_ai_feature_prompt_instructions(
            key="candidate_personality_interaction", language=language_code
        ),
    }

    area_headings = (
        {
            "leadership": "Leda och arbeta med andra",
            "organisation": "Organisering och tankestil",
            "interaction": "Samspel och känslomässig hantering",
        }
        if language_code == "sv"
        else {
            "leadership": "Leading and working with others",
            "organisation": "Organising and thinking style",
            "interaction": "Interaction and emotional management",
        }
    )

    purpose_value = (
        process.purpose
        or ""
    ).strip()

    purpose_labels = {
        "flexible": (
            "Flexible process / general insights"
        ),
        "unsure": (
            "Flexible process / general insights"
        ),
        "recruitment": "Recruitment",
        "role_match": "Role matching",
        "career_path": "Career development",
        "onboarding": "Onboarding",
        "employee_development": (
            "Employee development"
        ),
        "leadership_potential": (
            "Leadership potential"
        ),
        "leader_development": (
            "Leadership development"
        ),
        "team_development": (
            "Team development"
        ),
        "reorganisation": "Reorganisation",
    }

    purpose_label = purpose_labels.get(
        purpose_value,
        (
            purpose_value
            or "No specific purpose selected"
        ),
    )

    process_context = getattr(
        process,
        "role_context",
        None,
    )

    context_lines = []

    if (
        process_context
        and process_context.has_content()
    ):
        context_data = model_to_dict(
            process_context
        )

        excluded_fields = {
            "id",
            "process",
            "created_at",
            "updated_at",
        }

        for field_name, value in (
            context_data.items()
        ):
            if field_name in excluded_fields:
                continue

            if value in (
                None,
                "",
                [],
                {},
            ):
                continue

            readable_name = (
                field_name
                .replace("_", " ")
                .title()
            )

            context_lines.append(
                f"- {readable_name}: {value}"
            )

    context_text = (
        "\n".join(context_lines)
        if context_lines
        else (
            "No additional process context "
            "has been added."
        )
    )

    if context_lines:
        interpretation_instruction = """
Use the selected purpose and the added process context to make the
summary more relevant. Explain how the candidate's assessment profile
may relate to the supplied context, but do not make a final decision
or treat the assessment results as absolute facts.
""".strip()

    else:
        interpretation_instruction = """
Provide a general interpretation based only on the available assessment
results and selected process purpose. Do not assess fit for a specific
role, team or situation when no such context has been supplied.
""".strip()

    language_instruction = (
        get_ai_language_instruction(
            language_code
        )
    )

    return f"""
You are generating the Insight summary section of a candidate
assessment report in Talena.

CANDIDATE

Name: {candidate.first_name} {candidate.last_name}


PROCESS PURPOSE

{purpose_label}


ADDED PROCESS CONTEXT

{context_text}


ASSESSMENT RESULTS

{assessment_text}


PERSONALITY RESULTS FOR THE THREE PROFILE AREAS

{personality_assessment_text}

AREA-SPECIFIC ADMINISTRATOR GUIDANCE

{area_headings["leadership"]}:
{personality_area_guidance["leadership"]}

{area_headings["organisation"]}:
{personality_area_guidance["organisation"]}

{area_headings["interaction"]}:
{personality_area_guidance["interaction"]}

Use only the personality results above for these three area descriptions. Do not use motivation, cognitive ability, process purpose or role context to change what the personality results may indicate.


INTERPRETATION INSTRUCTION

{interpretation_instruction}


OUTPUT LANGUAGE

{language_instruction}


WRITING RULES

- Write about the candidate as a person.
- Interpret the results rather than listing raw scores.
- Do not include raw score numbers in the final response.
- Do not diagnose the candidate.
- Do not overstate certainty.
- Do not make a final hiring recommendation.
- Do not produce a match percentage.
- Keep the summary useful and reasonably concise.


STRUCTURE

Overall summary

Write one concise paragraph of approximately 100–160 words. Preserve the existing overall summary as the first section.

Then add these three headings exactly, in this order, each followed by a short description of 2–3 sentences:
{area_headings["leadership"]}
{area_headings["organisation"]}
{area_headings["interaction"]}
Use the matching area-specific administrator guidance for each description. Keep each area distinct and use only personality assessment results for these descriptions. Never invent a missing result; if the evidence is insufficient for an area, say so briefly.

Do not include raw scores. Do not add any other headings.
Do not use markdown tables.
""".strip()


def save_candidate_summary(
    owner,
    full_text: str,
    *,
    language_code: str = "en",
):
    language_code = normalize_ai_language(
        language_code
    )

    owner.ai_summary = (
        full_text
        or ""
    ).strip()

    owner.ai_summary_generated_at = (
        timezone.now()
    )

    owner.ai_summary_status = "completed"

    set_ai_content_language(
        owner,
        "candidate_summary",
        language_code,
    )

    update_fields = [
        "ai_summary",
        "ai_summary_generated_at",
        "ai_summary_status",
    ]

    for field_name in (
        get_ai_language_update_fields(
            owner
        )
    ):
        if field_name not in update_fields:
            update_fields.append(
                field_name
            )

    owner.save(
        update_fields=update_fields
    )


def stream_candidate_summary(
    owner,
    *,
    language_code: str = "en",
) -> Iterable[str]:
    language_code = normalize_ai_language(
        language_code
    )

    client = get_openai_client()

    prompt = build_candidate_prompt(
        owner,
        language_code=language_code,
    )

    system_prompt = (
        "You are an AI component inside Talena. "
        "Generate a careful candidate assessment summary "
        "using only the supplied assessment evidence and "
        "process context. "
        f"{get_ai_system_language_instruction(
            language_code,
            owner=owner,
        )}"
    )

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
        temperature=0.3,
        stream=True,
    )

    for event in stream:
        delta = event.choices[0].delta

        if delta and delta.content:
            yield delta.content
            

def build_general_insights_prompt(
    *,
    candidate_name: str,
    insight_input: dict[str, Any],
) -> str:
    """
    Build the AI prompt for Flexible process / General insights.

    The AI must return JSON matching the structure used by
    the candidate sheet.
    """

    assessment_json = json.dumps(
        insight_input,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    return f"""
You are generating general candidate assessment insights for Talena,
an assessment and talent management platform.

REPORT MODE
- Purpose: Flexible process
- Report group: General insights
- No role, job, leadership, development, team or organisational context has been added.
- Do not assess whether the candidate is suitable for a specific role.
- Do not make hiring recommendations.
- Do not create a match score or fit verdict.

INTERPRETATION RULES
- Base every insight on the supplied assessment evidence.
- Do not invent traits, requirements, scores or context.
- Do not diagnose the candidate.
- Do not treat assessment results as absolute facts.
- Use cautious professional language such as:
  "may indicate", "suggests", "appears likely", "may prefer",
  "could be useful to explore".
- Translate results into practical workplace meaning.
- Do not repeat raw scores unnecessarily.
- Lower scores are not automatically weaknesses.
- Consider combinations and patterns across personality, motivation
  and cognitive ability where appropriate.
- If little assessment data is available, say so clearly.
- Write in clear professional English.

CANDIDATE
{candidate_name}

ASSESSMENT EVIDENCE
{assessment_json}

RETURN FORMAT
Return valid JSON only.
Do not include markdown fences.
Do not include commentary before or after the JSON.

Use this exact top-level structure:

{{
  "summary": {{
    "headline": "Short general profile headline",
    "body": "A concise overall interpretation in 2-3 sentences.",
    "bullets": [
      {{
        "label": "Most important interpretation",
        "text": "The most useful overall interpretation."
      }},
      {{
        "label": "Confidence / context level",
        "text": "Explain that this is a general interpretation without added process context."
      }},
      {{
        "label": "What this report is based on",
        "text": "Briefly describe which available assessments were used."
      }}
    ]
  }},

  "overall_interpretation": {{
    "title": "Overall profile interpretation",
    "label": "General interpretation",
    "confidence": "Low, Medium or High",
    "body": "A short practical interpretation of the overall profile.",
    "reasoning": [
      "Evidence-based interpretation 1.",
      "Evidence-based interpretation 2.",
      "Evidence-based interpretation 3."
    ],
    "suggested_next_step": "A general and non-decisive suggested next step."
  }},

  "key_strengths": [
    {{
      "title": "Strength title",
      "body": "Short explanation.",
      "how_it_may_show": "How this may appear in workplace behaviour.",
      "why_it_matters": "Why this could be useful.",
      "evidence": ["Relevant assessment signal", "Relevant assessment signal"]
    }}
  ],

  "areas_to_explore": [
    {{
      "title": "Exploration area",
      "body": "A cautious explanation of what may be useful to understand further.",
      "explore_through": "A practical way to explore it.",
      "what_to_listen_for": "What useful evidence or nuance to listen for.",
      "evidence": ["Relevant assessment signal"]
    }}
  ],

  "questions": [
    {{
      "category": "strengths, explore, motivation or work_style",
      "category_label": "Strengths, Explore, Motivation or Work style",
      "question": "A behavioural or reflective question.",
      "why": "Why this question is relevant.",
      "listen_for": "What to listen for in the response."
    }}
  ],

  "motivation_environment": {{
    "summary": "Overall interpretation of likely motivation and environment preferences.",
    "top_motivators": [
      {{
        "title": "Motivator",
        "body": "Practical interpretation."
      }}
    ],
    "possible_demotivators": [
      {{
        "title": "Possible demotivator",
        "body": "Practical and cautious interpretation."
      }}
    ],
    "best_environment": [
      {{
        "title": "Environment factor",
        "body": "Practical interpretation."
      }}
    ],
    "manager_tips": [
      {{
        "title": "Manager tip",
        "body": "Practical advice."
      }}
    ],
    "context_implications": "Explain that these are general themes without added process context."
  }},

  "work_style": {{
    "summary": "A short interpretation of likely general work style.",
    "items": [
      {{
        "title": "How they work",
        "subtitle": "Structure, pace and task approach",
        "body": "Practical interpretation.",
        "practical_tip": "A practical tip.",
        "evidence": ["Relevant assessment signal"],
        "icon": "work",
        "icon_class": ""
      }},
      {{
        "title": "How they communicate",
        "subtitle": "Information sharing and collaboration",
        "body": "Practical interpretation.",
        "practical_tip": "A practical tip.",
        "evidence": ["Relevant assessment signal"],
        "icon": "communicate",
        "icon_class": "is-blue"
      }},
      {{
        "title": "How they handle change",
        "subtitle": "Adaptability and changing priorities",
        "body": "Practical interpretation.",
        "practical_tip": "A practical tip.",
        "evidence": ["Relevant assessment signal"],
        "icon": "change",
        "icon_class": "is-green"
      }},
      {{
        "title": "How they handle pressure",
        "subtitle": "Pressure response and workload",
        "body": "Practical interpretation.",
        "practical_tip": "A practical tip.",
        "evidence": ["Relevant assessment signal"],
        "icon": "pressure",
        "icon_class": "is-orange"
      }},
      {{
        "title": "How they prefer to be managed",
        "subtitle": "Support, autonomy and feedback",
        "body": "Practical interpretation.",
        "practical_tip": "A practical tip.",
        "evidence": ["Relevant assessment signal"],
        "icon": "managed",
        "icon_class": "is-pink"
      }}
    ],
    "footer_note": "Explain that these are assessment-based hypotheses to explore."
  }},

  "next_steps": [
    {{
      "label": "Recommended action",
      "title": "Short next-step title",
      "body": "Practical next-step description.",
      "focus": "Specific focus for the next step."
    }}
  ]
}}

CONTENT REQUIREMENTS
- Return 3 or 4 key strengths.
- Return 3 or 4 areas to explore.
- Return exactly 5 questions.
- Return 2 or 3 top motivators where motivation results exist.
- Return 2 or 3 possible demotivators where motivation results exist.
- Return 3 or 4 best-environment items.
- Return 3 or 4 manager tips.
- Return exactly 5 work-style items using the titles and icons shown above.
- Return exactly 3 next-step items.
""".strip()


def _normalise_general_insights(data: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure that the candidate sheet always receives the expected keys,
    even if the AI omits an optional section.
    """

    if not isinstance(data, dict):
        data = {}

    summary = data.get("summary")
    if not isinstance(summary, dict):
        summary = {}

    overall_interpretation = data.get("overall_interpretation")
    if not isinstance(overall_interpretation, dict):
        overall_interpretation = {}

    motivation_environment = data.get("motivation_environment")
    if not isinstance(motivation_environment, dict):
        motivation_environment = {}

    work_style = data.get("work_style")
    if not isinstance(work_style, dict):
        work_style = {}

    return {
        "summary": {
            "headline": summary.get(
                "headline",
                "General assessment insights",
            ),
            "body": (
                summary.get("body")
                or (
                    "The available assessment results provide a general view "
                    "of the candidate's likely work-related preferences and behaviours."
                )
            ).strip(),
            "bullets": summary.get("bullets") or [],
        },

        "overall_interpretation": {
            "title": overall_interpretation.get(
                "title",
                "Overall profile interpretation",
            ),
            "label": overall_interpretation.get(
                "label",
                "General interpretation",
            ),
            "confidence": overall_interpretation.get(
                "confidence",
                "Medium",
            ),
            "body": (
                overall_interpretation.get("body") or ""
            ).strip(),
            "reasoning": overall_interpretation.get("reasoning") or [],
            "suggested_next_step": overall_interpretation.get(
                "suggested_next_step",
                "",
            ),
        },

        "key_strengths": (
            data.get("key_strengths")
            if isinstance(data.get("key_strengths"), list)
            else []
        ),

        "areas_to_explore": (
            data.get("areas_to_explore")
            if isinstance(data.get("areas_to_explore"), list)
            else []
        ),

        "questions": (
            data.get("questions")
            if isinstance(data.get("questions"), list)
            else []
        ),

        "motivation_environment": {
            "summary": motivation_environment.get("summary", ""),
            "top_motivators": (
                motivation_environment.get("top_motivators") or []
            ),
            "possible_demotivators": (
                motivation_environment.get("possible_demotivators") or []
            ),
            "best_environment": (
                motivation_environment.get("best_environment") or []
            ),
            "manager_tips": (
                motivation_environment.get("manager_tips") or []
            ),
            "context_implications": motivation_environment.get(
                "context_implications",
                "",
            ),
        },

        "work_style": {
            "summary": work_style.get("summary", ""),
            "items": work_style.get("items") or [],
            "footer_note": work_style.get("footer_note", ""),
        },

        "next_steps": (
            data.get("next_steps")
            if isinstance(data.get("next_steps"), list)
            else []
        ),

        # Flexible process must never display a role-fit verdict.
        "fit": None,
    }

