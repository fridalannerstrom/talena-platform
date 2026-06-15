from __future__ import annotations

import json
from typing import Any

from apps.core.ai.openai_client import (
    get_openai_client,
    get_chat_model,
)


def _clean_score_items(
    items: list[dict] | None,
    *,
    score_fields: tuple[str, ...],
) -> list[dict]:
    """
    Convert assessment rows into a compact and predictable format
    suitable for the candidate insights AI prompt.
    """
    cleaned_items = []

    for item in items or []:
        name = (
            item.get("competency")
            or item.get("label")
            or item.get("name")
        )

        if not name:
            continue

        score = None

        for score_field in score_fields:
            value = item.get(score_field)

            if value is not None:
                score = value
                break

        if score is None:
            continue

        cleaned_items.append({
            "name": str(name).strip(),
            "score": score,
        })

    return cleaned_items


def _sort_score_items(
    items: list[dict],
    *,
    reverse: bool,
    limit: int,
) -> list[dict]:
    return sorted(
        items,
        key=lambda item: item.get("score", -1),
        reverse=reverse,
    )[:limit]


def build_general_insight_input(
    *,
    personality_competencies: list[dict] | None,
    motivation_competencies: list[dict] | None,
    verbal_percentile: int | float | None,
    logical_percentile: int | float | None,
    numerical_percentile: int | float | None,
) -> dict[str, Any]:
    """
    Build a compact assessment payload for Flexible process.

    This contains assessment evidence only. It does not contain role,
    recruitment, leadership or team context.
    """

    personality_scores = _clean_score_items(
        personality_competencies,
        score_fields=(
            "sten_rounded",
            "sten",
            "score",
            "percentile",
        ),
    )

    motivation_scores = _clean_score_items(
        motivation_competencies,
        score_fields=(
            "score",
            "stive_rounded",
            "stive",
            "sten_rounded",
            "sten",
            "percentile",
        ),
    )

    ability_results = {
        "verbal_percentile": verbal_percentile,
        "logical_percentile": logical_percentile,
        "numerical_percentile": numerical_percentile,
    }

    available_ability_results = {
        key: value
        for key, value in ability_results.items()
        if value is not None
    }

    return {
        "report_group": "general",
        "purpose": "flexible",
        "has_context": False,

        "personality": {
            "all_scores": personality_scores,
            "highest_scores": _sort_score_items(
                personality_scores,
                reverse=True,
                limit=5,
            ),
            "lowest_scores": _sort_score_items(
                personality_scores,
                reverse=False,
                limit=5,
            ),
        },

        "motivation": {
            "all_scores": motivation_scores,
            "highest_scores": _sort_score_items(
                motivation_scores,
                reverse=True,
                limit=5,
            ),
            "lowest_scores": _sort_score_items(
                motivation_scores,
                reverse=False,
                limit=5,
            ),
        },

        "ability": {
            "results": available_ability_results,
        },

        "instructions": {
            "focus": (
                "Provide general insights about the person's likely strengths, "
                "work style, motivation and useful areas to explore."
            ),
            "do_not": [
                "Do not assess fit for a specific role.",
                "Do not make hiring recommendations.",
                "Do not diagnose the person.",
                "Do not treat assessment results as absolute facts.",
                "Do not invent context or requirements.",
            ],
        },
    }


def build_general_insights_prompt(
    *,
    candidate_name: str,
    insight_input: dict[str, Any],
) -> str:
    """
    Build the prompt used to generate general candidate insights
    for a Flexible process.
    """

    assessment_data = json.dumps(
        insight_input,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    return f"""
You are generating candidate assessment insights for Talena.

The report purpose is Flexible process.

IMPORTANT CONTEXT
- This is a general assessment interpretation.
- No role, job, team, leadership or development context has been added.
- Do not assess role fit.
- Do not make a hiring recommendation.
- Do not produce a match score.
- Do not diagnose the candidate.
- Do not invent missing assessment information.
- Interpret lower scores carefully. A lower score is not automatically a weakness.
- Use cautious language such as "may indicate", "suggests", "appears to" and "could be useful to explore".
- Translate the assessment evidence into practical workplace meaning.
- Write in professional, clear English.
- Do not include raw scores unnecessarily.

Candidate:
{candidate_name}

Assessment evidence:
{assessment_data}

Return valid JSON only.

Use this exact structure:

{{
  "summary": {{
    "headline": "A short headline describing the general profile",
    "body": "A concise overall interpretation in 2 to 3 sentences.",
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
        "text": "Explain which available assessments were used."
      }}
    ]
  }},
  "overall_interpretation": {{
    "title": "Overall profile interpretation",
    "label": "General interpretation",
    "confidence": "Low, Medium or High",
    "body": "A practical overall interpretation.",
    "reasoning": [
      "Evidence-based interpretation one.",
      "Evidence-based interpretation two.",
      "Evidence-based interpretation three."
    ],
    "suggested_next_step": "A sensible general next step."
  }},
  "key_strengths": [
    {{
      "title": "Strength title",
      "body": "Short interpretation.",
      "how_it_may_show": "How this may appear at work.",
      "why_it_matters": "Why it may be useful.",
      "evidence": ["Assessment signal"]
    }}
  ],
  "areas_to_explore": [
    {{
      "title": "Area to explore",
      "body": "A cautious interpretation.",
      "explore_through": "How to explore it.",
      "what_to_listen_for": "What evidence to listen for.",
      "evidence": ["Assessment signal"]
    }}
  ],
  "questions": [
    {{
      "category": "strengths, explore, motivation or work_style",
      "category_label": "Strengths, Explore, Motivation or Work style",
      "question": "A useful behavioural question.",
      "why": "Why the question is relevant.",
      "listen_for": "What to listen for."
    }}
  ],
  "motivation_environment": {{
    "summary": "A general motivation interpretation.",
    "top_motivators": [],
    "possible_demotivators": [],
    "best_environment": [],
    "manager_tips": [],
    "context_implications": "Explain the limitation created by missing process context."
  }},
  "work_style": {{
    "summary": "A general work-style interpretation.",
    "items": [
      {{
        "title": "How they work",
        "subtitle": "Structure, pace and task approach",
        "body": "Practical interpretation.",
        "practical_tip": "Practical tip.",
        "evidence": ["Assessment signal"],
        "icon": "work",
        "icon_class": ""
      }},
      {{
        "title": "How they communicate",
        "subtitle": "Information sharing and collaboration",
        "body": "Practical interpretation.",
        "practical_tip": "Practical tip.",
        "evidence": ["Assessment signal"],
        "icon": "communicate",
        "icon_class": "is-blue"
      }},
      {{
        "title": "How they handle change",
        "subtitle": "Adaptability and changing priorities",
        "body": "Practical interpretation.",
        "practical_tip": "Practical tip.",
        "evidence": ["Assessment signal"],
        "icon": "change",
        "icon_class": "is-green"
      }},
      {{
        "title": "How they handle pressure",
        "subtitle": "Pressure response and workload",
        "body": "Practical interpretation.",
        "practical_tip": "Practical tip.",
        "evidence": ["Assessment signal"],
        "icon": "pressure",
        "icon_class": "is-orange"
      }},
      {{
        "title": "How they prefer to be managed",
        "subtitle": "Support, autonomy and feedback",
        "body": "Practical interpretation.",
        "practical_tip": "Practical tip.",
        "evidence": ["Assessment signal"],
        "icon": "managed",
        "icon_class": "is-pink"
      }}
    ],
    "footer_note": "Explain that these are hypotheses based on assessment evidence."
  }},
  "next_steps": [
    {{
      "label": "Recommended action",
      "title": "Next-step title",
      "body": "Practical next-step description.",
      "focus": "Specific focus."
    }}
  ]
}}

Requirements:
- Return 3 or 4 key strengths.
- Return 3 or 4 areas to explore.
- Return exactly 5 questions.
- Return exactly 5 work-style items.
- Return exactly 3 next steps.
- If no motivation data exists, do not invent motivators or demotivators. Return empty lists and explain that motivation data was unavailable.
""".strip()

def _normalise_general_insights(
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Ensure the template always receives the expected report structure.
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
            "body": summary.get("body", ""),
            "bullets": (
                summary.get("bullets")
                if isinstance(summary.get("bullets"), list)
                else []
            ),
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
            "reasoning": (
                overall_interpretation.get("reasoning")
                if isinstance(
                    overall_interpretation.get("reasoning"),
                    list,
                )
                else []
            ),
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
                motivation_environment.get("top_motivators")
                if isinstance(
                    motivation_environment.get("top_motivators"),
                    list,
                )
                else []
            ),
            "possible_demotivators": (
                motivation_environment.get("possible_demotivators")
                if isinstance(
                    motivation_environment.get("possible_demotivators"),
                    list,
                )
                else []
            ),
            "best_environment": (
                motivation_environment.get("best_environment")
                if isinstance(
                    motivation_environment.get("best_environment"),
                    list,
                )
                else []
            ),
            "manager_tips": (
                motivation_environment.get("manager_tips")
                if isinstance(
                    motivation_environment.get("manager_tips"),
                    list,
                )
                else []
            ),
            "context_implications": motivation_environment.get(
                "context_implications",
                "",
            ),
        },

        "work_style": {
            "summary": work_style.get("summary", ""),
            "items": (
                work_style.get("items")
                if isinstance(work_style.get("items"), list)
                else []
            ),
            "footer_note": work_style.get("footer_note", ""),
        },

        "next_steps": (
            data.get("next_steps")
            if isinstance(data.get("next_steps"), list)
            else []
        ),

        # Flexible process must not contain a role-fit verdict.
        "fit": None,
    }

def generate_general_candidate_insights(
    *,
    candidate_name: str,
    insight_input: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate AI candidate insights for a Flexible process.
    """

    print("=== GENERATE GENERAL CANDIDATE INSIGHTS STARTED ===")

    client = get_openai_client()

    prompt = build_general_insights_prompt(
        candidate_name=candidate_name,
        insight_input=insight_input,
    )

    response = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful assessment interpretation assistant. "
                    "Return valid JSON only and follow the supplied schema exactly."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"

    print("=== OPENAI RESPONSE RECEIVED ===")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "OpenAI returned invalid JSON for general candidate insights."
        ) from exc

    result = _normalise_general_insights(parsed)

    result["summary"]["headline"] = (
        "[AI GENERATED] "
        + result["summary"]["headline"]
    )

    print("=== GENERAL CANDIDATE INSIGHTS COMPLETED ===")

    return result