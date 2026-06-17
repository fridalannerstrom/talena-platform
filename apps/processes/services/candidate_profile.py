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
    profile = empty_candidate_profile()

    assessment_results = (
        historical_candidate.assessment_results
        .prefetch_related("scores", "import_file")
        .all()
        .order_by("assessment_type", "scale", "-created_at")
    )

    for result in assessment_results:
        assessment_type = (result.assessment_type or "").strip().lower()

        for score in result.scores.all():
            score_value = score.score
            percentile_value = score.percentile

            score_item = {
                "name": score.name,
                "competency": score.name,
                "category": score.category,
                "scale": score.scale,
                "score": score_value,
                "sten": score_value if score.scale == "sten" else None,
                "sten_rounded": (
                    round(score_value)
                    if score_value is not None and score.scale == "sten"
                    else None
                ),
                "stive": score_value,
                "stive_rounded": (
                    round(score_value)
                    if score_value is not None
                    else None
                ),
                "percentile": percentile_value,
                "source": "historical_import",
            }

            if assessment_type == "motivation":
                profile["motivation_competencies"].append(score_item)
                profile["has_motivation_results"] = True

            elif assessment_type == "personality":
                if score.category == "team_style":
                    profile["team_style_scores"].append(score_item)
                else:
                    profile["personality_competencies"].append(score_item)

                profile["has_personality_results"] = True

            elif assessment_type in {
                "verbal",
                "logical",
                "numerical",
            }:
                value = (
                    percentile_value
                    if percentile_value is not None
                    else score_value
                )

                if value is not None:
                    profile["ability_results"][assessment_type] = {
                        "name": score.name,
                        "score": score_value,
                        "percentile": percentile_value,
                        "value": value,
                        "scale": score.scale,
                    }

                    profile["has_ability_results"] = True

    profile["has_any_results"] = any([
        profile["has_motivation_results"],
        profile["has_personality_results"],
        profile["has_ability_results"],
    ])

    profile["assessment_results"] = assessment_results

    return profile