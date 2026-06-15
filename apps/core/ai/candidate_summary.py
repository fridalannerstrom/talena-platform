from typing import Iterable
from django.utils import timezone

from .openai_client import get_openai_client, get_chat_model

import json
from typing import Any

from apps.core.ai.openai_client import (
    get_openai_client,
    get_chat_model,
)


def build_candidate_prompt(invitation) -> str:
    activities = invitation.sova_activities or []
    candidate = invitation.candidate

    lines = []

    for act in activities:
        name = act.get("activity")
        comps = act.get("competencies") or []

        lines.append(f"\n{name}:")

        for c in comps:
            comp_name = c.get("competency")
            sten = c.get("sten_rounded")
            stive = c.get("stive_rounded")
            percentile = c.get("percentile")

            score_parts = []

            if sten is not None:
                score_parts.append(f"sten {sten}")

            if stive is not None:
                score_parts.append(f"stive {stive}")

            if percentile is not None:
                score_parts.append(f"percentile {percentile}")

            score_text = ", ".join(score_parts) if score_parts else "no score available"

            lines.append(f"- {comp_name}: {score_text}")

    test_data = "\n".join(lines)

    prompt = f"""
You are generating the first section of a candidate assessment report in Talena.

This section is called: Insight summary.

Important:
- This is GENERAL MODE.
- No role, job, team, leadership or development context has been added.
- Do not assess whether the candidate fits a specific role.
- Do not make hiring recommendations.
- Do not use a match score.
- Do not overstate certainty.
- Write in professional, clear English.
- Keep it concise and useful for a recruiter, hiring manager or HR professional.
- Interpret the assessment results. Do not list raw numbers in the final answer.
- Write about the candidate as a person, but avoid sounding absolute or deterministic.
- Use cautious language such as "may indicate", "suggests", "appears to", "could be useful to explore".

Use this structure exactly:

Overall summary
Write 1–2 short sentences summarising the candidate's general assessment profile.

Most important interpretation
- Write exactly 3 bullet points.
- Each bullet should highlight one important general insight from the assessment results.
- Include both strengths and possible areas to validate where relevant.

Confidence / context level
Write 1 short sentence explaining that confidence is limited because no process context has been added.

What this report is based on
Write 1 short sentence explaining which completed assessment data this summary is based on.

Do not include any markdown tables.
Do not include headings other than the four headings above.
Do not include the candidate's raw scores.

Candidate:
- Name: {candidate.first_name} {candidate.last_name}

Candidate test data:
{test_data}
""".strip()

    return prompt

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

