from typing import Iterable
from django.utils import timezone

from .openai_client import get_openai_client, get_chat_model

import json
from typing import Any

from apps.core.ai.openai_client import (
    get_openai_client,
    get_chat_model,
)

from django.forms.models import model_to_dict


def build_candidate_prompt(invitation) -> str:
    """
    Build the AI prompt for the candidate insight summary.

    The summary is based on:
    - completed assessment data
    - the selected process purpose
    - any added process context
    """

    activities = invitation.sova_activities or []
    candidate = invitation.candidate
    process = invitation.process

    # ------------------------------------------------------------
    # Assessment results
    # ------------------------------------------------------------
    assessment_lines = []

    for activity in activities:
        activity_name = activity.get("activity") or "Assessment"
        competencies = activity.get("competencies") or []

        result_lines = []

        for competency in competencies:
            competency_name = (
                competency.get("competency")
                or competency.get("name")
                or "Unnamed competency"
            )

            sten = competency.get("sten_rounded")
            stive = competency.get("stive_rounded")
            percentile = competency.get("percentile")

            score_parts = []

            if sten is not None:
                score_parts.append(f"sten {sten}")

            if stive is not None:
                score_parts.append(f"stive {stive}")

            if percentile is not None:
                score_parts.append(f"percentile {percentile}")

            if not score_parts:
                continue

            result_lines.append(
                f"- {competency_name}: {', '.join(score_parts)}"
            )

        if result_lines:
            assessment_lines.append(
                f"{activity_name}:\n" + "\n".join(result_lines)
            )

    assessment_text = (
        "\n\n".join(assessment_lines)
        if assessment_lines
        else "No completed assessment scores were available."
    )

    # ------------------------------------------------------------
    # Process purpose
    # ------------------------------------------------------------
    purpose_value = (process.purpose or "").strip()

    purpose_labels = {
        "flexible": "Flexible process / general insights",
        "unsure": "Flexible process / general insights",
        "recruitment": "Recruitment",
        "role_match": "Role matching",
        "career_path": "Career development",
        "onboarding": "Onboarding",
        "employee_development": "Employee development",
        "leadership_potential": "Leadership potential",
        "leader_development": "Leadership development",
        "team_development": "Team development",
        "reorganisation": "Reorganisation",
    }

    purpose_label = purpose_labels.get(
        purpose_value,
        purpose_value or "No specific purpose selected",
    )

    # ------------------------------------------------------------
    # Optional process context
    # ------------------------------------------------------------
    process_context = getattr(process, "role_context", None)
    context_lines = []

    if process_context and process_context.has_content():
        context_data = model_to_dict(process_context)

        excluded_fields = {
            "id",
            "process",
            "created_at",
            "updated_at",
        }

        for field_name, value in context_data.items():
            if field_name in excluded_fields:
                continue

            if value in (None, "", [], {}):
                continue

            readable_name = field_name.replace("_", " ").title()

            context_lines.append(
                f"- {readable_name}: {value}"
            )

    context_text = (
        "\n".join(context_lines)
        if context_lines
        else "No additional process context has been added."
    )

    has_added_context = bool(context_lines)

    # ------------------------------------------------------------
    # Prompt behaviour
    # ------------------------------------------------------------
    if has_added_context:
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

INTERPRETATION INSTRUCTION
{interpretation_instruction}

WRITING RULES
- Write in professional, clear English.
- Write about the candidate as a person.
- Interpret the results rather than listing raw scores.
- Do not include raw score numbers in the final response.
- Do not diagnose the candidate.
- Do not overstate certainty.
- Do not make a final hiring recommendation.
- Do not produce a match percentage.
- Use cautious language such as:
  "may indicate", "suggests", "appears to" and
  "could be useful to explore".
- Keep the summary useful and reasonably concise.

STRUCTURE

Overall summary

Write one concise paragraph of approximately 100–160 words.

The paragraph should:
- describe the most important overall profile themes
- highlight likely strengths
- mention one or two useful areas to explore
- reflect the process purpose
- use added context when available
- clearly remain an assessment-based interpretation

Do not include any other headings.
Do not use markdown tables.
""".strip()

def save_candidate_summary(invitation, full_text: str):
    invitation.ai_summary = full_text
    invitation.ai_summary_generated_at = timezone.now()
    invitation.ai_summary_status = "completed"
    invitation.save(update_fields=[
        "ai_summary",
        "ai_summary_generated_at",
        "ai_summary_status"
    ])

def stream_candidate_summary(invitation) -> Iterable[str]:
    client = get_openai_client()

    prompt = build_candidate_prompt(invitation)

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[{"role": "user", "content": prompt}],
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
            "body": summary.get(
                "body",
                "The available assessment results provide a general view "
                "of the candidate's likely work-related preferences and behaviours.",
            ),
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
            "body": overall_interpretation.get("body", ""),
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

