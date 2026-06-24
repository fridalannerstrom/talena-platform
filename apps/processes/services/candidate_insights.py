"""Shared candidate insight content for active and historical candidates."""

from __future__ import annotations

from typing import Any, Literal
import re

InsightMode = Literal["general", "context"]

# Indicators that may be highly significant, but where a high score
# should not automatically be presented as a strength.
DOUBLE_EDGED_INDICATORS = {
    "stubborn",
    "rigid",
    "casual",
    "dramatic",
    "unpredictable",
    "dependent",
    "dependence",
    "vulnerability",
    "over sensitive",
    "over-sensitive",
    "volatility",
    "impulsiveness",
    "hesitant",
    "detached",
}

EXPLORE_COMBINATION_RULES = {
    "flexibility_when_challenged": {
        "title": "Flexibility when challenged",
        "high_any": {
            "stubborn",
            "rigid",
        },
        "low_any": {
            "flexibility",
            "flexible",
            "adaptability",
            "adapting to change",
            "openness to change",
            "change oriented",
            "dealing with the changes",
        },
        "high_threshold": 8,
        "low_threshold": 4,
        "body": (
            "The candidate may show strong persistence and conviction, "
            "but could find it difficult to reconsider an established "
            "position or adapt quickly when circumstances change."
        ),
        "explore_through": (
            "Ask about a situation where the candidate needed to abandon "
            "an original plan, accept another person’s approach or adjust "
            "quickly to unexpected change."
        ),
        "what_to_listen_for": (
            "Listen for self-awareness, openness to new information and "
            "practical strategies for adapting without losing determination."
        ),
    },

    "structure_and_follow_through": {
        "title": "Structure and follow-through",
        "high_any": {
            "casual",
        },
        "low_any": {
            "self discipline",
            "keeping promises",
            "attention to detail",
            "meticulous",
            "order",
            "structured",
            "planning and organising",
            "planning and organizing",
        },
        "high_threshold": 8,
        "low_threshold": 4,
        "body": (
            "The candidate may prefer an informal or flexible approach, "
            "which could make consistent structure and detailed follow-through "
            "more demanding in some situations."
        ),
        "explore_through": (
            "Ask for an example involving detailed planning, recurring "
            "deadlines or responsibility for completing precise work."
        ),
        "what_to_listen_for": (
            "Listen for practical systems, checking routines and examples "
            "of maintaining reliability over time."
        ),
    },

    "independence_and_reassurance": {
        "title": "Independent decision-making",
        "high_any": {
            "dependent",
            "dependence",
        },
        "low_any": {
            "independence",
            "self reliant",
            "thinking independently",
        },
        "high_threshold": 7,
        "low_threshold": 4,
        "body": (
            "The candidate may value guidance, reassurance or close alignment "
            "with others when making decisions."
        ),
        "explore_through": (
            "Ask about a situation where the candidate needed to make an "
            "important decision without immediate support or detailed guidance."
        ),
        "what_to_listen_for": (
            "Listen for confidence in personal judgement, appropriate use "
            "of support and the ability to act independently when required."
        ),
    },

    "emotional_response_under_pressure": {
        "title": "Emotional response under pressure",
        "high_any": {
            "vulnerability",
            "over sensitive",
            "over-sensitive",
            "volatility",
        },
        "low_any": {
            "emotional control",
            "controlling stress",
            "calm",
            "composed",
            "recovering",
            "resilience",
        },
        "high_threshold": 7,
        "low_threshold": 4,
        "body": (
            "The candidate may experience demanding or uncertain situations "
            "more intensely and may need effective strategies for maintaining "
            "balance under pressure."
        ),
        "explore_through": (
            "Ask about a demanding period involving criticism, uncertainty "
            "or sustained pressure and how the candidate managed it."
        ),
        "what_to_listen_for": (
            "Listen for emotional self-awareness, recovery strategies and "
            "the ability to continue functioning effectively under pressure."
        ),
    },
}


INSIGHT_THEMES = {
    "structured_delivery": {
        "title": "Structured and reliable delivery",
        "indicator_keys": {
            "planning",
            "planning and organising",
            "planning and organizing",
            "quality focus",
            "reliability",
            "self discipline",
            "attention to detail",
            "task focus",
            "keeping promises",
            "meticulous",
            "structured",
            "order",
            "perfectionism",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may bring structure, accuracy and dependable "
            "follow-through to their work."
        ),
        "strength_show": (
            "May organise work clearly, maintain quality and follow agreed "
            "tasks through to completion."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate maintains "
            "structure, accuracy and follow-through in demanding situations."
        ),
        "explore_through": (
            "Ask for an example involving competing deadlines, detailed work "
            "or responsibility for recurring delivery."
        ),
    },

    "analytical_problem_solving": {
        "title": "Analytical problem solving",
        "indicator_keys": {
            "analytical thinking",
            "analytical",
            "analysing problems",
            "analyzing problems",
            "analytical orientation",
            "analytical approach",
            "analyst",
            "evaluating",
            "using the facts",
            "data focus",
            "logical reasoning",
            "numerical reasoning",
            "verbal reasoning",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may be comfortable examining information, "
            "identifying patterns and reaching evidence-based conclusions."
        ),
        "strength_show": (
            "May compare alternatives, question assumptions and use relevant "
            "information to support decisions."
        ),
        "explore_body": (
            "It may be useful to explore how confidently the candidate works "
            "with information and reaches sound conclusions."
        ),
        "explore_through": (
            "Ask for an example of analysing a difficult problem and explain "
            "how the conclusion was reached."
        ),
    },

    "strategic_complex_thinking": {
        "title": "Strategic and complex thinking",
        "indicator_keys": {
            "strategic thinking",
            "strategic insight",
            "strategic focus",
            "complex thinking",
            "conceptual",
            "architect",
            "creates the vision",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may be comfortable considering broader patterns, "
            "longer-term implications and complex information."
        ),
        "strength_show": (
            "May connect different pieces of information, consider several "
            "perspectives and think beyond immediate operational details."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate translates "
            "strategic thinking into practical action."
        ),
        "explore_through": (
            "Ask for an example of turning a complex issue into a clear "
            "decision or course of action."
        ),
    },

    "innovation_originality": {
        "title": "Innovation and original thinking",
        "indicator_keys": {
            "innovating",
            "innovation",
            "thinking innovatively",
            "creativity",
            "generating ideas",
            "generates solutions",
            "unconventional",
            "curiosity",
            "experimenting",
            "catalyst",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may contribute original perspectives and be open "
            "to alternative ways of approaching challenges."
        ),
        "strength_show": (
            "May question established approaches, explore possibilities and "
            "suggest new ways forward."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate balances original "
            "thinking with practical requirements."
        ),
        "explore_through": (
            "Ask for an example where the candidate introduced a new approach "
            "and evaluated whether it would work."
        ),
    },

    "learning_orientation": {
        "title": "Learning orientation",
        "indicator_keys": {
            "learning mindset",
            "curiosity",
            "inquisitiveness",
            "openness to experience",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may show an active interest in learning, developing "
            "their knowledge and understanding unfamiliar topics."
        ),
        "strength_show": (
            "May seek information, ask questions and engage actively with "
            "new knowledge or experiences."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate develops and "
            "applies new knowledge."
        ),
        "explore_through": (
            "Ask about something the candidate recently needed to learn and "
            "how they approached it."
        ),
    },

    "network_building": {
        "title": "Network building",
        "indicator_keys": {
            "building networks",
            "building strong networks",
            "connecting",
            "connector",
            "builds alliances",
            "keeping in touch",
            "initiating contact",
            "sociability",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may be comfortable establishing and maintaining "
            "useful professional relationships."
        ),
        "strength_show": (
            "May connect with relevant people and develop relationships "
            "across teams or professional networks."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate establishes and "
            "maintains professional relationships."
        ),
        "explore_through": (
            "Ask for an example of building a relationship that supported "
            "a work-related outcome."
        ),
    },

    "collaboration": {
        "title": "Collaborative working style",
        "indicator_keys": {
            "teamwork",
            "cooperative",
            "cooperation",
            "collective",
            "listening",
            "empathy",
            "helpfulness",
            "supporting",
            "service focus",
            "open communication",
            "builds alliances",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may contribute positively to collaboration and "
            "shared ways of working."
        ),
        "strength_show": (
            "May listen, support colleagues and contribute toward shared goals."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate collaborates with "
            "different personalities and working styles."
        ),
        "explore_through": (
            "Ask about a situation involving disagreement, feedback or the "
            "need to establish cooperation."
        ),
    },

    "supporting_others": {
        "title": "Supporting and developing others",
        "indicator_keys": {
            "developing others",
            "nurtures talent",
            "coaching and developing",
            "coaching developing",
            "supporting",
            "helpfulness",
            "compassion",
            "altruism",
            "looking out for others",
            "considerate",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may be motivated to support others and contribute "
            "to their development or wellbeing."
        ),
        "strength_show": (
            "May offer support, share knowledge and take an interest in the "
            "needs or development of colleagues."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate supports and "
            "develops others in practice."
        ),
        "explore_through": (
            "Ask for an example of helping another person improve, learn or "
            "manage a difficult situation."
        ),
    },

    "adaptability_pressure": {
        "title": "Adaptability under pressure",
        "indicator_keys": {
            "adaptability",
            "adapting to change",
            "openness to change",
            "change oriented",
            "dealing with the changes",
            "flexible",
            "flexibility",
            "variety",
            "resilience",
            "recovering",
            "staying strong",
            "emotional control",
            "controlling stress",
            "calm",
            "composed",
            "optimistic",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may remain adaptable and composed when demands "
            "or circumstances change."
        ),
        "strength_show": (
            "May adjust priorities, recover from setbacks and continue "
            "working effectively under pressure."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate responds when "
            "priorities shift or pressure increases."
        ),
        "explore_through": (
            "Ask for an example involving uncertainty, stress or several "
            "changing demands at once."
        ),
    },

    "drive_ownership": {
        "title": "Drive and ownership",
        "indicator_keys": {
            "achievement",
            "achievement striving",
            "drive to achieve",
            "drive and motivation",
            "goal focused",
            "competitive",
            "challenge",
            "independence",
            "self reliant",
            "thinking independently",
            "entrepreneurial",
            "drives momentum",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may show personal drive, initiative and a "
            "willingness to take responsibility for outcomes."
        ),
        "strength_show": (
            "May pursue objectives, act independently and maintain ownership "
            "of agreed responsibilities."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate takes ownership "
            "and maintains momentum."
        ),
        "explore_through": (
            "Ask about a situation where they needed to take initiative "
            "without detailed guidance."
        ),
    },

    "leadership_influence": {
        "title": "Leadership and influence",
        "indicator_keys": {
            "desire to lead",
            "taking the lead",
            "leading and influencing",
            "leads by example",
            "director",
            "assertive",
            "assertiveness",
            "persuading",
            "influential",
            "influencing",
            "inspiring others",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may be comfortable influencing direction, "
            "expressing a position and taking a visible role."
        ),
        "strength_show": (
            "May communicate a clear point of view, influence others and "
            "step forward when direction is needed."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate influences others "
            "and adapts their leadership approach."
        ),
        "explore_through": (
            "Ask for an example of gaining support for an idea or providing "
            "direction to others."
        ),
    },

    "communication_engagement": {
        "title": "Communication and engagement",
        "indicator_keys": {
            "effective communication",
            "open communication",
            "candid",
            "straightforward",
            "enthusiastic",
            "warmth",
            "initiating contact",
            "sociability",
            "connecting",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may communicate with energy and engage readily "
            "with other people."
        ),
        "strength_show": (
            "May express ideas openly, create engagement and establish contact "
            "with others."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate adjusts their "
            "communication to different audiences."
        ),
        "explore_through": (
            "Ask for an example of communicating a difficult message or "
            "engaging an initially unreceptive audience."
        ),
    },

    "integrity_sincerity": {
        "title": "Integrity and sincerity",
        "indicator_keys": {
            "honesty",
            "earnest",
            "straightforward",
            "candid",
            "modest",
            "modesty",
            "humility",
            "humble",
            "being open and modest",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may value honesty, sincerity and an open approach "
            "in their interactions."
        ),
        "strength_show": (
            "May communicate sincerely, avoid unnecessary self-promotion and "
            "seek to behave consistently with stated values."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate handles situations "
            "where openness and diplomacy need to be balanced."
        ),
        "explore_through": (
            "Ask about a situation where the candidate needed to communicate "
            "an uncomfortable truth constructively."
        ),
    },

    "energy_momentum": {
        "title": "Energy and momentum",
        "indicator_keys": {
            "energetic",
            "dynamic",
            "enthusiastic",
            "energiser",
            "drives momentum",
            "intense",
            "catalyst",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may bring energy and momentum to tasks, discussions "
            "or collaborative activity."
        ),
        "strength_show": (
            "May create pace, communicate enthusiasm and encourage progress."
        ),
        "explore_body": (
            "It may be useful to explore how the candidate maintains energy "
            "over longer or less stimulating assignments."
        ),
        "explore_through": (
            "Ask about a lengthy assignment where motivation or momentum was "
            "difficult to sustain."
        ),
    },
}

def normalize_indicator_key(value: Any) -> str:
    text = str(value or "").strip().lower()

    text = text.replace("&", " and ")
    text = text.replace("_", " ")
    text = text.replace("-", " ")

    return re.sub(r"\s+", " ", text).strip()


def ordinal_percentile(value: float) -> str:
    rounded = int(round(value))

    if 10 <= rounded % 100 <= 20:
        suffix = "th"
    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd",
        }.get(rounded % 10, "th")

    return f"{rounded}{suffix} percentile"


def safe_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_assessment_indicators(
    general_insight_input: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    source = general_insight_input or {}
    indicators: list[dict[str, Any]] = []

    personality_data = source.get("personality") or {}
    motivation_data = source.get("motivation") or {}
    ability_data = source.get("ability") or {}
    ability_results = ability_data.get("results") or {}

    personality_items = (
        personality_data.get("all_scores")
        or []
    )

    motivation_items = (
        motivation_data.get("all_scores")
        or []
    )

    # --------------------------------------------------
    # Personality
    # Input format:
    # {"name": "Adaptability", "score": 2}
    # Scores are already on a 1–10 scale.
    # --------------------------------------------------
    seen_personality = set()

    for item in personality_items:
        name = item.get("name")
        score = safe_float(item.get("score"))

        if not name or score is None:
            continue

        key = normalize_indicator_key(name)

        # The input currently contains some duplicate names.
        # Keep only one instance of each indicator.
        if key in seen_personality:
            continue

        seen_personality.add(key)

        normalized_score = max(
            1.0,
            min(10.0, score),
        )

        indicators.append({
            "key": key,
            "name": str(name),
            "source": "personality",
            "source_label": "Personality assessment",
            "raw_score": score,
            "scale": "sten",
            "normalized_score": normalized_score,
            "display_score": f"{score:g}/10",
            "tooltip": (
                f"Personality assessment · "
                f"STEN score {score:g} of 10."
            ),
        })

    # --------------------------------------------------
    # Motivation
    # Input format is expected to be:
    # {"name": "...", "score": ...}
    #
    # Your example currently contains no motivation
    # results, so this part will simply add nothing.
    # --------------------------------------------------
    seen_motivation = set()

    for item in motivation_items:
        name = item.get("name")
        score = safe_float(item.get("score"))

        if not name or score is None:
            continue

        key = normalize_indicator_key(name)

        if key in seen_motivation:
            continue

        seen_motivation.add(key)

        # Adjust this if the input later proves to use
        # another motivation scale.
        normalized_score = max(
            1.0,
            min(10.0, score * 2),
        )

        indicators.append({
            "key": key,
            "name": str(name),
            "source": "motivation",
            "source_label": "Motivation questionnaire",
            "raw_score": score,
            "scale": "five_point",
            "normalized_score": normalized_score,
            "display_score": f"{score:g}/5",
            "tooltip": (
                f"Motivation questionnaire · "
                f"score {score:g} of 5."
            ),
        })

    # --------------------------------------------------
    # Cognitive abilities
    # Input format:
    # ability.results.numerical_percentile
    # ability.results.logical_percentile
    # ability.results.verbal_percentile
    # --------------------------------------------------
    cognitive_results = [
        {
            "name": "Verbal reasoning",
            "value": ability_results.get(
                "verbal_percentile"
            ),
        },
        {
            "name": "Logical reasoning",
            "value": ability_results.get(
                "logical_percentile"
            ),
        },
        {
            "name": "Numerical reasoning",
            "value": ability_results.get(
                "numerical_percentile"
            ),
        },
    ]

    for cognitive_result in cognitive_results:
        name = cognitive_result["name"]
        percentile = safe_float(
            cognitive_result["value"]
        )

        if percentile is None:
            continue

        normalized_score = max(
            1.0,
            min(10.0, percentile / 10),
        )

        indicators.append({
            "key": normalize_indicator_key(name),
            "name": name,
            "source": "cognitive",
            "source_label": "Cognitive assessment",
            "raw_score": percentile,
            "scale": "percentile",
            "normalized_score": normalized_score,
            "display_score": ordinal_percentile(
                percentile
            ),
            "tooltip": (
                f"Cognitive assessment · "
                f"{ordinal_percentile(percentile)}."
            ),
        })

    return indicators

def build_combination_explore_areas(
    indicators: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    explore_areas: list[dict[str, Any]] = []

    personality_indicators = [
        item
        for item in indicators
        if item.get("source") == "personality"
    ]

    for rule_key, rule in EXPLORE_COMBINATION_RULES.items():
        high_matches = [
            item
            for item in personality_indicators
            if (
                item.get("key") in rule["high_any"]
                and item["normalized_score"]
                >= rule.get("high_threshold", 8)
            )
        ]

        low_matches = [
            item
            for item in personality_indicators
            if (
                item.get("key") in rule["low_any"]
                and item["normalized_score"]
                <= rule.get("low_threshold", 4)
            )
        ]

        if not high_matches or not low_matches:
            continue

        high_matches.sort(
            key=lambda item: item["normalized_score"],
            reverse=True,
        )

        low_matches.sort(
            key=lambda item: item["normalized_score"],
        )

        selected = (
            high_matches[:2]
            + low_matches[:3]
        )

        high_strength = max(
            item["normalized_score"]
            for item in high_matches
        )

        low_strength = max(
            1,
            11 - min(
                item["normalized_score"]
                for item in low_matches
            ),
        )

        level = round(
            (high_strength + low_strength) / 2,
            1,
        )

        explanation = (
            "This area was identified from a combination of one or more "
            "elevated double-edged indicators and related lower assessment "
            "results. It is intended as a topic to verify, not a confirmed "
            "weakness."
        )

        explore_areas.append({
            "theme_key": rule_key,
            "title": rule["title"],
            "body": rule["body"],
            "explore_through": rule["explore_through"],
            "what_to_listen_for": rule["what_to_listen_for"],
            "level": level,
            "level_rounded": round(level),
            "level_label": "Priority to explore",
            "explanation": explanation,
            "supporting_indicators": selected,
            "evidence": [
                item["name"]
                for item in selected
            ],
            "area_type": "combination",
        })

    return explore_areas

def build_low_score_explore_areas(
    indicators: list[dict[str, Any]],
    excluded_theme_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    explore_areas: list[dict[str, Any]] = []
    excluded_theme_keys = excluded_theme_keys or set()

    for theme_key, theme in INSIGHT_THEMES.items():
        if theme_key in excluded_theme_keys:
            continue

        matched = [
            indicator
            for indicator in indicators
            if (
                indicator.get("source") == "personality"
                and indicator.get("key")
                in theme["indicator_keys"]
            )
        ]

        if not matched:
            continue

        lower_indicators = [
            item
            for item in matched
            if item["normalized_score"] <= 4
        ]

        lower_indicators.sort(
            key=lambda item: item["normalized_score"],
        )

        has_multiple_low_indicators = (
            len(lower_indicators) >= 2
        )

        has_one_extremely_low_indicator = (
            len(lower_indicators) == 1
            and lower_indicators[0]["normalized_score"] <= 2
        )

        is_supported_explore_area = (
            has_multiple_low_indicators
            or has_one_extremely_low_indicator
        )

        if not is_supported_explore_area:
            continue

        selected = lower_indicators[:4]

        average_score = (
            sum(
                item["normalized_score"]
                for item in selected
            )
            / len(selected)
        )

        # A lower raw result creates a higher exploration priority.
        level = round(
            max(1, min(10, 11 - average_score)),
            1,
        )

        if level >= 8.5:
            level_label = "High priority to explore"
        elif level >= 7:
            level_label = "Explore further"
        else:
            level_label = "Consider exploring"

        if len(selected) == 1:
            explanation = (
                "This area was identified from one particularly low "
                "personality result. It should be explored and verified, "
                "not treated as a confirmed weakness."
            )
        else:
            explanation = (
                f"This area was identified from {len(selected)} related "
                f"personality results in the lower part of the scale. "
                f"It should be explored and verified, not treated as a "
                f"confirmed weakness."
            )

        explore_areas.append({
            "theme_key": theme_key,
            "title": theme["title"],
            "body": theme["explore_body"],
            "explore_through": theme["explore_through"],
            "what_to_listen_for": (
                "Listen for relevant context, self-awareness and practical "
                "strategies the candidate uses to manage this area."
            ),
            "level": level,
            "level_rounded": round(level),
            "level_label": level_label,
            "explanation": explanation,
            "supporting_indicators": selected,
            "evidence": [
                item["name"]
                for item in selected
            ],
            "area_type": "low_scores",
        })

    return explore_areas


def build_evidence_themes(
    indicators: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    strengths: list[dict[str, Any]] = []

    # We will build Areas to explore separately later.
    explore_areas: list[dict[str, Any]] = []

    for theme_key, theme in INSIGHT_THEMES.items():
        matched = [
            indicator
            for indicator in indicators
            if indicator["key"] in theme["indicator_keys"]
        ]

        if not matched:
            continue

        matched.sort(
            key=lambda item: item["normalized_score"],
            reverse=True,
        )

        # Only clearly elevated results may support a Key strength.
        strong_indicators = [
            item
            for item in matched
            if item["normalized_score"] >= 7
        ]

        # Key strengths must be anchored in personality data.
        # Double-edged indicators are excluded from automatic strengths.
        strong_personality_indicators = [
            item
            for item in strong_indicators
            if (
                item.get("source") == "personality"
                and item.get("key") not in DOUBLE_EDGED_INDICATORS
            )
        ]

        minimum_strong = theme.get(
            "minimum_strong",
            2,
        )

        allow_single_from = theme.get(
            "allow_single_from",
            8,
        )

        has_multiple_strong_indicators = (
            len(strong_personality_indicators)
            >= minimum_strong
        )

        has_one_very_strong_indicator = (
            len(strong_personality_indicators) == 1
            and strong_personality_indicators[0][
                "normalized_score"
            ] >= allow_single_from
        )

        is_supported_strength = (
            has_multiple_strong_indicators
            or has_one_very_strong_indicator
        )

        if not is_supported_strength:
            continue

        selected = strong_personality_indicators[:4]

        level = round(
            sum(
                item["normalized_score"]
                for item in selected
            ) / len(selected),
            1,
        )

        if level >= 8.5:
            level_label = "Very strong evidence"
        elif level >= 7:
            level_label = "Strong evidence"
        else:
            level_label = "Moderate evidence"

        if len(selected) == 1:
            explanation = (
                "This theme was identified from one particularly "
                "elevated personality result. The displayed level "
                "is a visual summary, not a separate assessment score."
            )
        else:
            explanation = (
                f"This theme was identified from {len(selected)} "
                f"clearly elevated personality results. The displayed "
                f"level is their combined visual level, not a separate "
                f"assessment score."
            )

        strengths.append({
            "theme_key": theme_key,
            "title": theme["title"],
            "body": theme["strength_body"],
            "how_it_may_show": theme["strength_show"],
            "why_it_matters": (
                "This theme may be relevant where the process requires "
                "these behaviours or capabilities."
            ),
            "level": level,
            "level_rounded": round(level),
            "level_label": level_label,
            "explanation": explanation,
            "supporting_indicators": selected,
            "evidence": [
                item["name"]
                for item in selected
            ],
        })

    strengths.sort(
        key=lambda item: (
            item["level"],
            len(item["supporting_indicators"]),
        ),
        reverse=True,
    )

    strength_theme_keys = {
        item["theme_key"]
        for item in strengths
    }

    combination_explore_areas = (
        build_combination_explore_areas(indicators)
    )

    combination_theme_keys = {
        item["theme_key"]
        for item in combination_explore_areas
    }

    low_score_explore_areas = (
        build_low_score_explore_areas(
            indicators,
            excluded_theme_keys=(
                strength_theme_keys
                | combination_theme_keys
            ),
        )
    )

    explore_areas = (
        combination_explore_areas
        + low_score_explore_areas
    )

    explore_areas.sort(
        key=lambda item: (
            item["level"],
            len(item["supporting_indicators"]),
        ),
        reverse=True,
    )

    return strengths[:4], explore_areas[:4]

def build_candidate_insights(
    *,
    mode: InsightMode = "general",
    general_insight_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the candidate insight structure used by the candidate sheet.

    ``general_insight_input`` is accepted now so both active and historical
    candidate flows use the same API. The current implementation still returns
    the deterministic content that previously lived in views.py.
    """

    candidate_insights_mode: InsightMode = (
        "context" if mode == "context" else "general"
    )

    assessment_indicators = normalize_assessment_indicators(
        general_insight_input
    )

    has_personality_indicators = any(
        indicator.get("source") == "personality"
        for indicator in assessment_indicators
    )

    if has_personality_indicators:
        evidence_strengths, evidence_explore_areas = (
            build_evidence_themes(assessment_indicators)
        )
    else:
        evidence_strengths = []
        evidence_explore_areas = []


    if candidate_insights_mode == "context":
        candidate_insights = {
            "summary": {
                "headline": "Potential fit for a structured Business Controller role",
                "body": (
                    "The candidate shows a profile that may support structured analysis, reliable delivery and careful business follow-up. "
                    "For this Business Controller context, the strongest signal is the combination of analytical thinking, planning and quality focus. "
                    "The main areas to validate are stakeholder communication, pace when priorities change and the ability to turn analysis into practical recommendations."
                ),
                "bullets": [
                    {
                        "label": "Most important interpretation",
                        "text": "The candidate appears well aligned with work that requires structure, accuracy and thoughtful analysis, but the interview should validate how this translates into stakeholder-facing business support.",
                    },
                    {
                        "label": "Confidence / context level",
                        "text": "Medium confidence. The interpretation uses completed assessment data and the added Business Controller role context, but should be combined with interview evidence.",
                    },
                    {
                        "label": "What this report is based on",
                        "text": "Assessment results, personality and motivation indicators, cognitive reasoning data, and the added role context covering requirements, priorities and interview focus.",
                    },
                ],
            },
            "fit": {
                "title": "Role match verdict",
                "label": "Potential match",
                "confidence": "Medium",
                "summary": (
                    "Talena sees a promising match for the Business Controller role, mainly because the candidate shows strong "
                    "indicators for structure, analytical thinking and reliable delivery."
                ),
                "body": (
                    "Talena sees a promising match for the Business Controller role, mainly because the candidate shows strong "
                    "indicators for structure, analytical thinking and reliable delivery."
                ),
                "reasoning": [
                    "The role requires structured analysis and careful follow-up, which appears aligned with the candidate’s strengths in planning, quality focus and analytical thinking.",
                    "The candidate may be well suited to work that requires accuracy, ownership and thoughtful decision support.",
                    "The match is not yet strong enough to confirm without interview validation, especially around stakeholder-facing business support.",
                ],
                "watch_points": [
                    "Stakeholder communication",
                    "Pace under ambiguity",
                    "Commercial judgement",
                ],
                "suggested_next_step": "Proceed with a structured interview focused on stakeholder communication, changing priorities and business impact.",
                "decision_note": (
                    "This is a decision-support recommendation, not a final hiring decision. Combine it with interview evidence, experience and role requirements."
                ),
            },
            "key_strengths": evidence_strengths,
            "areas_to_explore": evidence_explore_areas,
            "questions": [
                {
                    "category": "strengths",
                    "category_label": "Strengths",
                    "question": "Tell me about a time when you used financial or business analysis to support an important decision.",
                    "why": "Helps validate analytical problem-solving and ability to turn data into practical recommendations.",
                    "listen_for": "Look for clear reasoning, business understanding, accuracy and impact on the decision.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Can you describe a situation where you had to explain complex financial information to someone without a finance background?",
                    "why": "Explores stakeholder communication and ability to make analysis understandable.",
                    "listen_for": "Look for clarity, adaptation to the audience and ability to connect numbers to business reality.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Tell me about a time when priorities changed close to a deadline. How did you handle it?",
                    "why": "Helps understand pace, flexibility and prioritisation under pressure.",
                    "listen_for": "Look for structure, calmness, communication and practical decision-making.",
                },
                {
                    "category": "motivation",
                    "category_label": "Motivation",
                    "question": "What type of financial or analytical work gives you the most energy?",
                    "why": "Explores motivation fit with the role’s recurring tasks and stakeholder support.",
                    "listen_for": "Look for alignment with analysis, quality, ownership and business impact.",
                },
                {
                    "category": "work_style",
                    "category_label": "Work style",
                    "question": "How do you prefer to work with managers who need support but may not know exactly what analysis they need?",
                    "why": "Explores consulting style, communication and ability to clarify needs.",
                    "listen_for": "Look for curiosity, structure, patience and ability to guide stakeholders.",
                },
            ],
            "motivation_environment": {
                "summary": (
                    "In this Business Controller context, the candidate’s likely motivation for quality, autonomy and meaningful contribution "
                    "may support independent delivery and careful analysis. Engagement may be strongest when expectations are clear and the work "
                    "has visible business value."
                ),
                "top_motivators": [
                    {
                        "title": "Quality",
                        "body": "May be motivated by accurate, reliable work and high standards.",
                    },
                    {
                        "title": "Autonomy",
                        "body": "May value ownership over tasks and freedom to decide how to approach analysis.",
                    },
                    {
                        "title": "Making a difference",
                        "body": "May gain energy from seeing that their work improves decisions or creates business value.",
                    },
                ],
                "possible_demotivators": [
                    {
                        "title": "Unclear priorities",
                        "body": "May lose energy if goals, responsibilities or decision-making authority remain vague.",
                    },
                    {
                        "title": "Low-quality shortcuts",
                        "body": "May become frustrated if speed is repeatedly prioritised over accuracy.",
                    },
                    {
                        "title": "Limited ownership",
                        "body": "May find it less engaging if there is little room to influence how work is done.",
                    },
                ],
                "best_environment": [
                    {
                        "title": "Clear expectations",
                        "body": "Clear priorities and success criteria may help the candidate focus effectively.",
                    },
                    {
                        "title": "Trust and responsibility",
                        "body": "The candidate may perform well when trusted to own analysis and follow through.",
                    },
                    {
                        "title": "Business-oriented dialogue",
                        "body": "Regular dialogue with managers can help connect analysis to practical decisions.",
                    },
                    {
                        "title": "Constructive feedback",
                        "body": "Feedback on usefulness and business impact may help maintain motivation.",
                    },
                ],
                "manager_tips": [
                    {
                        "title": "Clarify the business question",
                        "body": "Explain what decision the analysis should support before asking for numbers or reports.",
                    },
                    {
                        "title": "Agree on priorities",
                        "body": "Be clear about what is urgent, what can wait and what level of detail is needed.",
                    },
                    {
                        "title": "Give ownership",
                        "body": "Let the candidate own recurring analysis while agreeing on checkpoints and deadlines.",
                    },
                    {
                        "title": "Connect work to impact",
                        "body": "Show how their analysis contributes to decisions, improvements or financial control.",
                    },
                ],
                "context_implications": (
                    "For this role, the motivation profile may support careful and independent delivery. "
                    "The main thing to watch is whether the role provides enough clarity, ownership and connection to business impact."
                ),
            },
            "work_style": {
                "summary": (
                    "The candidate appears likely to work best with clarity, structure and enough space to think things through. "
                    "In this role context, that may support reliable analysis, careful financial follow-up and considered business recommendations."
                ),
                "items": [
                    {
                        "title": "How they work",
                        "subtitle": "Structure, pace and task approach",
                        "body": "May prefer clear expectations, organised work and time to understand the task before moving into action.",
                        "practical_tip": "Provide clear priorities and agree on what good delivery looks like early in the process.",
                        "evidence": ["Planning", "Reliability", "Quality Focus"],
                        "icon": "work",
                        "icon_class": "",
                    },
                    {
                        "title": "How they communicate",
                        "subtitle": "Information sharing and stakeholder dialogue",
                        "body": "May communicate most effectively when there is a clear purpose and enough context to form a considered view.",
                        "practical_tip": "Invite them to explain their reasoning and connect analysis to practical business consequences.",
                        "evidence": ["Communication", "Analytical Thinking"],
                        "icon": "communicate",
                        "icon_class": "is-blue",
                    },
                    {
                        "title": "How they handle change",
                        "subtitle": "Changing priorities and business needs",
                        "body": "May adapt well when changes are explained clearly, but may need clarity around priorities if several things change at once.",
                        "practical_tip": "When priorities shift, clarify what changed, what stays the same and what should be handled first.",
                        "evidence": ["Adaptability", "Decision-making"],
                        "icon": "change",
                        "icon_class": "is-green",
                    },
                    {
                        "title": "How they handle pressure",
                        "subtitle": "Deadlines and workload",
                        "body": "May perform best when pressure is paired with structure, realistic priorities and clear expectations.",
                        "practical_tip": "Use short check-ins during intense reporting periods to remove blockers and keep priorities visible.",
                        "evidence": ["Resilience", "Emotional Control"],
                        "icon": "pressure",
                        "icon_class": "is-orange",
                    },
                    {
                        "title": "How they prefer to be managed",
                        "subtitle": "Support, autonomy and feedback",
                        "body": "May respond well to a management style that combines trust and autonomy with clear goals and constructive feedback.",
                        "practical_tip": "Give ownership, but agree on checkpoints and make expectations explicit.",
                        "evidence": ["Autonomy", "Quality", "Achievement"],
                        "icon": "managed",
                        "icon_class": "is-pink",
                    },
                ],
                "footer_note": (
                    "This section translates personality and motivation indicators into practical behaviours for the current role context. "
                    "Full trait-level results can be reviewed further down as evidence."
                ),
            },
            "next_steps": [
                {
                    "label": "Recommended action",
                    "title": "Proceed with a structured interview",
                    "body": "Use the report to guide a focused interview rather than as a standalone decision.",
                    "focus": "Validate stakeholder communication, commercial judgement and pace under ambiguity.",
                },
                {
                    "label": "Interview focus",
                    "title": "Ask evidence-based follow-up questions",
                    "body": "Use behavioural questions to understand how the candidate applies analysis and structure in real work situations.",
                    "focus": "Ask for examples involving financial analysis, deadlines, prioritisation and influencing decisions.",
                },
                {
                    "label": "Decision support",
                    "title": "Combine assessment insights with interview evidence",
                    "body": "Use the assessment results together with interview notes, experience and role requirements.",
                    "focus": "Avoid making a decision from assessment data alone.",
                },
            ],
        }

    else:
        candidate_insights = {
            "summary": {
                "headline": (
                    "General assessment summary"
                    if candidate_insights_mode == "general"
                    else "Contextual candidate insight summary"
                ),
                "body": (
                    "The candidate’s assessment profile suggests a structured and analytical work style, with strong indicators around planning, quality focus and working with complex information. "
                    "This may support roles or situations where careful follow-up, accuracy and thoughtful problem-solving are important. "
                    "At the same time, the results should be explored further through conversation, especially around stakeholder influence, decision-making pace and how the candidate handles changing priorities. "
                    "Add role or process context to make this interpretation more specific."
                ),
            },
            "fit": {
                "label": (
                    "Insufficient context"
                    if candidate_insights_mode == "general"
                    else "Potential fit"
                ),
                "confidence": (
                    "Low"
                    if candidate_insights_mode == "general"
                    else "Medium"
                ),
                "suggested_next_step": (
                    "Add context"
                    if candidate_insights_mode == "general"
                    else "Structured follow-up"
                ),
                "body": (
                    "No process context has been added yet, so this section does not assess "
                    "fit for a specific role, team, leadership situation or development goal."
                    if candidate_insights_mode == "general"
                    else
                    "Based on the added context, the candidate appears to show several relevant "
                    "indicators. Some areas should be explored further before making a decision."
                ),
            },
                "key_strengths": evidence_strengths,
            "areas_to_explore": evidence_explore_areas,
            "questions": [
                {
                    "question": "Tell me about a time when you used analysis to influence a decision.",
                    "why": "Validates analytical thinking and communication in a practical situation.",
                },
                {
                    "question": "How do you handle situations where priorities change quickly?",
                    "why": "Explores adaptability, structure and decision-making under pressure.",
                },
                {
                    "question": "What type of work environment helps you perform at your best?",
                    "why": "Connects motivation and work style to the candidate’s preferred conditions.",
                },
            ],
            "motivation_environment": {
                "summary": (
                    "The candidate appears likely to be energised by quality, autonomy and meaningful contribution. "
                    "They may perform best in an environment with clear expectations, room for ownership and opportunities to do work properly."
                ),
                "top_motivators": [
                    {
                        "title": "Quality",
                        "body": "May be motivated by doing work to a high standard and feeling that the result is accurate and reliable.",
                    },
                    {
                        "title": "Autonomy",
                        "body": "May value having ownership over tasks and enough freedom to decide how work should be approached.",
                    },
                    {
                        "title": "Making a difference",
                        "body": "May gain energy from seeing that their work contributes to something meaningful or useful.",
                    },
                ],
                "possible_demotivators": [
                    {
                        "title": "Unclear expectations",
                        "body": "May lose energy if goals, responsibilities or decision-making authority are vague for too long.",
                    },
                    {
                        "title": "Low-quality shortcuts",
                        "body": "May become frustrated if speed is consistently prioritised over accuracy or thoughtful delivery.",
                    },
                    {
                        "title": "Limited ownership",
                        "body": "May find it less engaging if there is little room to take responsibility or influence how work is done.",
                    },
                ],
                "best_environment": [
                    {
                        "title": "Clear goals",
                        "body": "An environment with clear priorities and expectations may help the candidate focus their energy effectively.",
                    },
                    {
                        "title": "Trust and ownership",
                        "body": "They may perform well when trusted to take responsibility and manage tasks with a degree of independence.",
                    },
                    {
                        "title": "Quality-focused culture",
                        "body": "A culture that values accuracy, improvement and thoughtful work may support engagement.",
                    },
                    {
                        "title": "Constructive feedback",
                        "body": "Regular feedback and clear dialogue may help maintain motivation and alignment.",
                    },
                ],
                "manager_tips": [
                    {
                        "title": "Clarify expectations early",
                        "body": "Be clear about what success looks like and which priorities matter most.",
                    },
                    {
                        "title": "Give ownership with boundaries",
                        "body": "Allow independence while agreeing on checkpoints, timelines and decision areas.",
                    },
                    {
                        "title": "Connect work to purpose",
                        "body": "Explain why tasks matter and how they contribute to wider goals or customer value.",
                    },
                    {
                        "title": "Avoid unnecessary ambiguity",
                        "body": "When things are changing, communicate what is known, what is uncertain and when decisions will be made.",
                    },
                ],
                "context_implications": (
                    "Without added process context, these insights should be read as general motivation themes. "
                    "If this report is used for a specific role, onboarding plan or development purpose, the motivation profile should be interpreted against that situation."
                ),
            },
            "work_style": {
                "summary": (
                    "The candidate appears likely to work best with clarity, structure and enough space to think things through. "
                    "Their profile may suggest a thoughtful and reliable working style, with a preference for quality and considered decisions."
                ),
                "items": [
                    {
                        "title": "How they work",
                        "subtitle": "Structure, pace and task approach",
                        "body": "The candidate may prefer clear expectations, organised work and time to understand the task before moving into action.",
                        "practical_tip": "Provide clear priorities and agree on what good delivery looks like early in the process.",
                        "evidence": ["Planning", "Reliability", "Quality Focus"],
                        "icon": "work",
                        "icon_class": "",
                    },
                    {
                        "title": "How they communicate",
                        "subtitle": "Information sharing and collaboration",
                        "body": "They may communicate most effectively when there is a clear purpose and enough context to form a considered view.",
                        "practical_tip": "Invite them to explain their reasoning and give space for questions, especially in complex discussions.",
                        "evidence": ["Communication", "Analytical Thinking"],
                        "icon": "communicate",
                        "icon_class": "is-blue",
                    },
                    {
                        "title": "How they handle change",
                        "subtitle": "Adaptability and shifting priorities",
                        "body": "They may adapt well when changes are explained clearly, but may need clarity around priorities if several things change at once.",
                        "practical_tip": "When priorities shift, clarify what has changed, what stays the same and what should be handled first.",
                        "evidence": ["Adaptability", "Decision-making"],
                        "icon": "change",
                        "icon_class": "is-green",
                    },
                    {
                        "title": "How they handle pressure",
                        "subtitle": "Pressure response and workload",
                        "body": "The candidate may perform best when pressure is paired with structure, realistic priorities and clear expectations.",
                        "practical_tip": "Use regular check-ins during intense periods to remove blockers and keep priorities visible.",
                        "evidence": ["Resilience", "Emotional Control"],
                        "icon": "pressure",
                        "icon_class": "is-orange",
                    },
                    {
                        "title": "How they prefer to be managed",
                        "subtitle": "Support, autonomy and feedback",
                        "body": "They may respond well to a management style that combines trust and autonomy with clear goals and constructive feedback.",
                        "practical_tip": "Give ownership, but agree on checkpoints and make expectations explicit.",
                        "evidence": ["Autonomy", "Quality", "Achievement"],
                        "icon": "managed",
                        "icon_class": "is-pink",
                    },
                ],
                "footer_note": (
                    "This section translates personality and work style indicators into practical behaviours. "
                    "Full trait-level results can be reviewed further down as evidence."
                ),
            },
            "next_steps": [
                {
                    "label": "Recommended action",
                    "title": "Use a structured follow-up conversation",
                    "body": "Use the insights as a starting point for a structured conversation rather than as a final conclusion.",
                    "focus": "Focus on examples from real work situations, especially where the candidate had to apply their strengths in practice.",
                },
                {
                    "label": "Validate through examples",
                    "title": "Explore the most relevant follow-up themes",
                    "body": "Ask targeted questions around the areas that would benefit from more context before making decisions or recommendations.",
                    "focus": "Prioritise stakeholder influence, pace under ambiguity and collaboration style.",
                },
                {
                    "label": "Connect insights to context",
                    "title": "Add process context for sharper recommendations",
                    "body": "If this report will be used for a specific role, team, onboarding plan or development purpose, add context to make the next steps more precise.",
                    "focus": "Add role, team, leadership or onboarding context to tailor the interpretation.",
                },
            ],

            "questions": [
                {
                    "category": "strengths",
                    "category_label": "Strengths",
                    "question": "Tell me about a situation where you used structure or analysis to solve a work-related problem.",
                    "why": "Helps validate how the candidate applies analytical and structured strengths in real situations.",
                    "listen_for": "Look for clear reasoning, practical action, follow-through and ability to explain the outcome.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Can you describe a time when you needed to influence someone who had a different opinion from you?",
                    "why": "Explores how the candidate gains buy-in and handles different perspectives.",
                    "listen_for": "Look for listening, clarity, adaptability, confidence and respect for other viewpoints.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Tell me about a situation where you had to make progress without having all the information you wanted.",
                    "why": "Helps understand how the candidate handles ambiguity and changing priorities.",
                    "listen_for": "Look for balance between careful thinking and practical action.",
                },
                {
                    "category": "motivation",
                    "category_label": "Motivation",
                    "question": "What type of work tends to give you the most energy, and what tends to drain your energy over time?",
                    "why": "Explores motivation fit and the conditions that may support sustained performance.",
                    "listen_for": "Look for alignment between the candidate’s drivers and the realities of the role or context.",
                },
                {
                    "category": "work_style",
                    "category_label": "Work style",
                    "question": "How do you prefer to receive goals, feedback and follow-up from a manager?",
                    "why": "Helps understand what management style may support the candidate’s performance.",
                    "listen_for": "Look for self-awareness, clarity around support needs and ability to work with expectations.",
                },
            ],

        }

    print(
        "AREAS TO EXPLORE:",
        candidate_insights.get("areas_to_explore"),
        flush=True,
    )


    return candidate_insights


