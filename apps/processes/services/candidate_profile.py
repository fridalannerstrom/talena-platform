from typing import Any


def empty_candidate_profile() -> dict[str, Any]:
    return {
        "motivation_competencies": [],
        "personality_competencies": [],
        "team_style_scores": [],
        "ability_results": {
            "verbal": None,
            "logical": None,
            "numerical": None,
        },
        "has_motivation_results": False,
        "has_personality_results": False,
        "has_ability_results": False,
        "has_any_results": False,
    }

def build_historical_candidate_profile(historical_candidate):
    """
    Build one normalized candidate profile from imported historical Sova data.

    The output should mirror the data concepts used for active candidates:

    - Personality traits / response styles: STEN 1-10
    - Team styles: STIVE 1-5
    - Motivation: STIVE 1-5
    - Cognitive abilities: percentile

    Historical imports may contain several files/scales for the same
    candidate. Each assessment area therefore only consumes the scale
    that actually belongs to that area.
    """

    profile = empty_candidate_profile()

    assessment_results = (
        historical_candidate.assessment_results
        .prefetch_related("scores", "import_file")
        .all()
        .order_by(
            "assessment_type",
            "scale",
            "-created_at",
        )
    )

    # ---------------------------------------------------------
    # DEDUPLICATION
    # ---------------------------------------------------------
    #
    # A historical candidate may have several imported files,
    # for example both Personality STEN and Personality 1-to-5.
    #
    # Keep one normalized value per result name instead of
    # accidentally showing the same competency several times.
    #
    personality_by_name = {}
    motivation_by_name = {}
    team_styles_by_name = {}

    ability_results = {
        "verbal": None,
        "logical": None,
        "numerical": None,
    }

    for result in assessment_results:
        assessment_type = (
            result.assessment_type
            or ""
        ).strip().lower()

        scale = (
            result.scale
            or ""
        ).strip().lower()

        # Normalise possible historical naming variants.
        if scale in {
            "1-to-5",
            "1_to_5",
            "1 to 5",
            "one-to-five",
        }:
            scale = "one_to_five"

        for score in result.scores.all():
            score_value = score.score
            percentile_value = score.percentile

            score_name = (
                score.name
                or ""
            ).strip()

            if not score_name:
                continue

            score_key = score_name.lower()

            category = (
                score.category
                or ""
            ).strip().lower()

            # =====================================================
            # PERSONALITY
            # =====================================================

            if assessment_type == "personality":

                # -------------------------------------------------
                # TEAM STYLES
                #
                # Sova team styles use the five-point STIVE scale.
                # Never interpret a STEN value as STIVE.
                # -------------------------------------------------
                if category == "team_style":
                    if scale != "one_to_five":
                        continue

                    if score_value is None:
                        continue

                    team_styles_by_name[score_key] = {
                        "name": score_name,
                        "competency": score_name,
                        "category": "team_style",
                        "scale": "one_to_five",

                        "score": score_value,

                        "sten": None,
                        "sten_rounded": None,

                        "stive": score_value,
                        "stive_rounded": round(score_value),

                        "percentile": percentile_value,

                        "source": "historical_import",
                    }

                    continue

                # -------------------------------------------------
                # PERSONALITY TRAITS + RESPONSE STYLES
                #
                # These use STEN 1-10.
                # -------------------------------------------------
                if scale != "sten":
                    continue

                if score_value is None:
                    continue

                personality_by_name[score_key] = {
                    "name": score_name,
                    "competency": score_name,
                    "category": category or "personality",
                    "scale": "sten",

                    "score": score_value,

                    "sten": score_value,
                    "sten_rounded": round(score_value),

                    "stive": None,
                    "stive_rounded": None,

                    "percentile": percentile_value,

                    "source": "historical_import",
                }

                continue

            # =====================================================
            # MOTIVATION
            # =====================================================

            if assessment_type == "motivation":

                # Motivation uses Sova's five-point STIVE scale.
                if scale != "one_to_five":
                    continue

                if score_value is None:
                    continue

                motivation_by_name[score_key] = {
                    "name": score_name,
                    "competency": score_name,
                    "category": category or "motivation",
                    "scale": "one_to_five",

                    "score": score_value,

                    "sten": None,
                    "sten_rounded": None,

                    "stive": score_value,
                    "stive_rounded": round(score_value),

                    "percentile": percentile_value,

                    "source": "historical_import",
                }

                continue

            # =====================================================
            # COGNITIVE ABILITIES
            # =====================================================

            if assessment_type in {
                "verbal",
                "logical",
                "numerical",
            }:
                # Prefer the actual percentile column when available.
                value = percentile_value

                # Some historical exports may store the percentile
                # directly as score in a file whose scale is percentile.
                if (
                    value is None
                    and scale == "percentile"
                ):
                    value = score_value

                if value is None:
                    continue

                # Once a usable percentile has been found for this
                # ability, keep it.
                if ability_results[assessment_type] is None:
                    ability_results[assessment_type] = {
                        "name": score_name,
                        "score": score_value,
                        "percentile": value,
                        "value": value,
                        "scale": "percentile",
                        "source": "historical_import",
                    }

    # ---------------------------------------------------------
    # FINAL NORMALIZED PROFILE
    # ---------------------------------------------------------

    profile["personality_competencies"] = list(
        personality_by_name.values()
    )

    profile["motivation_competencies"] = list(
        motivation_by_name.values()
    )

    profile["team_style_scores"] = list(
        team_styles_by_name.values()
    )

    profile["ability_results"] = ability_results

    profile["has_personality_results"] = bool(
        profile["personality_competencies"]
        or profile["team_style_scores"]
    )

    profile["has_motivation_results"] = bool(
        profile["motivation_competencies"]
    )

    profile["has_ability_results"] = any(
        value is not None
        for value in ability_results.values()
    )

    profile["has_any_results"] = any([
        profile["has_personality_results"],
        profile["has_motivation_results"],
        profile["has_ability_results"],
    ])

    # Keep the raw imported result queryset available for parts of
    # Talena that need import metadata or historical source details.
    profile["assessment_results"] = assessment_results

    return profile