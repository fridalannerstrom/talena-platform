from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _, override

# Talena cognitive results language batch 1
def build_cognitive_insight_results(
    verbal_percentile=None,
    logical_percentile=None,
    numerical_percentile=None,
    *,
    language_code: str | None = None,
):
    """
    Build the three cognitive result cards used in Candidate Insights.

    All three assessment types are always returned so the template can show
    a grey placeholder when an assessment has not been completed.

    Percentile calculations and thresholds are intentionally unchanged.
    """

    if language_code:
        with override(language_code):
            return build_cognitive_insight_results(
                verbal_percentile=verbal_percentile,
                logical_percentile=logical_percentile,
                numerical_percentile=numerical_percentile,
            )

    def normalise_percentile(value):
        if value is None:
            return None

        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    def get_level(percentile):
        """
        Translate a percentile result into a display level and interpretation.
        Adjust the thresholds later if Sova uses different norm bands.
        """

        if percentile is None:
            return {
                "completed": False,
                "level_key": "missing",
                "level_label": _("Not completed"),
            }

        if percentile <= 9:
            return {
                "completed": True,
                "level_key": "very-low",
                "level_label": _("Very low"),
            }

        if percentile <= 24:
            return {
                "completed": True,
                "level_key": "low",
                "level_label": _("Low"),
            }

        if percentile <= 74:
            return {
                "completed": True,
                "level_key": "average",
                "level_label": _("Typical range"),
            }

        if percentile <= 90:
            return {
                "completed": True,
                "level_key": "high",
                "level_label": _("High"),
            }

        return {
            "completed": True,
            "level_key": "very-high",
            "level_label": _("Very high"),
        }

    def get_interpretation(test_key, percentile):
        if percentile is None:
            return _(
                "This candidate has not completed this assessment."
            )

        ability_labels = {
            "verbal": _(
                "understand and evaluate written information"
            ),
            "logical": _(
                "identify patterns and reach logical conclusions"
            ),
            "numerical": _(
                "understand and work with numerical information"
            ),
        }

        ability_text = ability_labels[test_key]

        if percentile <= 9:
            return _(
                "The candidate may find it considerably more difficult "
                "than most people in the reference group to %(ability)s."
            ) % {
                "ability": ability_text,
            }

        if percentile <= 24:
            return _(
                "The candidate may find it more difficult than many "
                "others in the reference group to %(ability)s."
            ) % {
                "ability": ability_text,
            }

        if percentile <= 74:
            return _(
                "The candidate is likely to find it about as easy as "
                "most people in the reference group to %(ability)s."
            ) % {
                "ability": ability_text,
            }

        if percentile <= 90:
            return _(
                "The candidate may find it easier than many others in "
                "the reference group to %(ability)s."
            ) % {
                "ability": ability_text,
            }

        return _(
            "The candidate may find it considerably easier than most "
            "people in the reference group to %(ability)s."
        ) % {
            "ability": ability_text,
        }

    test_config = [
        {
            "key": "logical",
            "title": _("Logical reasoning"),
            "measure_label": _("Logical reasoning ability"),
            "percentile": normalise_percentile(
                logical_percentile
            ),
        },
        {
            "key": "numerical",
            "title": _("Numerical reasoning"),
            "measure_label": _("Numerical reasoning ability"),
            "percentile": normalise_percentile(
                numerical_percentile
            ),
        },
        {
            "key": "verbal",
            "title": _("Verbal reasoning"),
            "measure_label": _("Verbal reasoning ability"),
            "percentile": normalise_percentile(
                verbal_percentile
            ),
        },
    ]

    results = []

    for test in test_config:
        percentile = test["percentile"]
        level = get_level(percentile)

        if percentile is None:
            percentile_aria_label = ""
            missing_aria_label = _(
                "%(title)s assessment not completed"
            ) % {
                "title": test["title"],
            }
        else:
            percentile_aria_label = _(
                "%(title)s percentile %(percentile)s"
            ) % {
                "title": test["title"],
                "percentile": percentile,
            }
            missing_aria_label = ""

        results.append({
            "key": test["key"],
            "title": test["title"],
            "measure_label": test["measure_label"],
            "percentile": percentile,
            "completed": level["completed"],
            "level_key": level["level_key"],
            "level_label": level["level_label"],
            "interpretation": get_interpretation(
                test_key=test["key"],
                percentile=percentile,
            ),
            "percentile_aria_label": percentile_aria_label,
            "missing_aria_label": missing_aria_label,
        })

    return results



def build_cognitive_ai_evidence(
    percentiles: dict[str, Any] | None,
    *,
    language_code: str = "en",
) -> str:
    """Use Candidate Insights' approved interpretation for AI Overview."""
    values = percentiles or {}
    results = build_cognitive_insight_results(
        verbal_percentile=values.get("verbal"),
        logical_percentile=values.get("logical"),
        numerical_percentile=values.get("numerical"),
        language_code=language_code,
    )
    completed = [result for result in results if result["completed"]]
    if not completed:
        if language_code == "sv":
            return "Inga färdighetstestresultat finns tillgängliga."
        return "No cognitive assessment results are available."

    if language_code == "sv":
        lines = [
            "Percentilerna visar resultat i förhållande till en referensgrupp.",
            "Tolkningstexterna är Talenas godkända resultattolkningar.",
            "Använd dem som kompletterande information om att bearbeta ny information. Dra inte slutsatser om arbetsprestation, kommunikationsförmåga eller lämplighet för en roll.",
        ]
        percentile_label = "percentil"
    else:
        lines = [
            "Percentiles show results relative to a reference group.",
            "The interpretation text is Talena's approved result interpretation.",
            "Use it as complementary information about processing new information. Do not infer work performance, communication ability or role suitability.",
        ]
        percentile_label = "percentile"

    for result in completed:
        lines.append(
            f"- {result['title']}: {percentile_label} "
            f"{result['percentile']}. {result['interpretation']}"
        )
    return "\n".join(lines)


def build_owner_cognitive_ai_evidence(
    owner,
    *,
    language_code: str = "en",
) -> str:
    """Build cognitive evidence for active and historical candidates."""
    process = getattr(owner, "process", None)
    percentiles: dict[str, Any] = {}

    if getattr(process, "is_historical", False):
        from apps.processes.services.candidate_profile import (
            build_historical_candidate_profile,
        )

        profile = build_historical_candidate_profile(owner)
        ability_results = profile.get("ability_results") or {}
        for key in ("verbal", "logical", "numerical"):
            ability = ability_results.get(key)
            if isinstance(ability, dict):
                value = ability.get("percentile")
                if value is None:
                    value = ability.get("value")
            else:
                value = ability
            if value is not None:
                percentiles[key] = value
    else:
        from apps.core.ai.cognitive_interpretation import (
            extract_cognitive_results,
        )

        for result in extract_cognitive_results(owner):
            key = result.get("key")
            value = result.get("percentile")
            if key in {"verbal", "logical", "numerical"} and value is not None:
                percentiles.setdefault(key, value)

    return build_cognitive_ai_evidence(
        percentiles,
        language_code=language_code,
    )
