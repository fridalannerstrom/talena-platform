"""Localized response-style results for Talena.

The Sova source keys and score calculations remain unchanged. Only
user-facing labels and explanatory text vary with the active language.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import get_language


def _normalise_language(language: str | None = None) -> str:
    value = str(language or get_language() or "sv").strip().lower()
    return "sv" if value.startswith("sv") else "en"


_BAND_LABELS = {
    "sv": {
        "missing": "Ej tillgängligt",
        "low": "Låg",
        "middle": "Typisk",
        "high": "Hög",
        "missing_interpretation": (
            "Inget svarsstilsresultat är tillgängligt för den här bedömningen."
        ),
    },
    "en": {
        "missing": "Not available",
        "low": "Low",
        "middle": "Typical",
        "high": "High",
        "missing_interpretation": (
            "No response-style result is available for this assessment."
        ),
    },
}


_STYLE_CONTENT = [
    {
        "key": "social_desirability",
        "source_name": "social desirability",
        "sv": {
            "title": "Social önskvärdhet",
            "low_pole": (
                "Tenderar att svara på ett självkritiskt sätt. "
                "Kan ha tydligare preferenser än vad resultaten antyder"
            ),
            "high_pole": (
                "Framställde sig själv på ett positivt sätt. "
                "Kan ha preferenser som inte är lika tydliga som resultaten antyder."
            ),
            "low_text": (
                "Svarsmönstret tyder på en relativt självkritisk självpresentation. "
                "Vissa preferenser kan vara mer framträdande än resultaten visar."
            ),
            "middle_text": (
                "Svarsmönstret verkar vara förhållandevis balanserat, utan någon "
                "tydlig tendens till vare sig självkritisk eller alltför positiv "
                "självpresentation."
            ),
            "high_text": (
                "Svarsmönstret tyder på en positiv självpresentation. "
                "Vissa preferenser kan vara mindre framträdande än resultaten visar."
            ),
        },
        "en": {
            "title": "Social Desirability",
            "low_pole": (
                "Tended to respond self-critically; preferences may be more "
                "accentuated than the results suggest"
            ),
            "high_pole": (
                "Presented themselves positively; preferences may be less "
                "accentuated than the results suggest"
            ),
            "low_text": (
                "The response pattern suggests a relatively self-critical "
                "presentation. Some preferences may be more pronounced than "
                "the results indicate."
            ),
            "middle_text": (
                "The response pattern appears reasonably balanced, with no "
                "clear tendency towards either self-critical or overly "
                "positive self-presentation."
            ),
            "high_text": (
                "The response pattern suggests a positive self-presentation. "
                "Some preferences may be less pronounced than the results indicate."
            ),
        },
    },
    {
        "key": "profile_spread",
        "source_name": "fillers",
        "sv": {
            "title": "Konsekvensskala",
            "low_pole": (
                "Svaren visar mindre differentiering mellan egenskaperna vilket kan "
                "bero på mindre konsekvens eller brist på självinsikt"
            ),
            "high_pole": (
                "Svaren visar tydliga styrkor och utvecklingsbehov, profilen visar "
                "ett brett utbud av poäng över egenskaperna"
            ),
            "low_text": (
                "Svaren visar mindre skillnader mellan personlighetsdragen. "
                "Det kan spegla ett mer generellt svarsmönster eller lägre "
                "konsekvens mellan relaterade svar."
            ),
            "middle_text": (
                "Profilen innehåller en blandning av mer och mindre tydligt "
                "differentierade svar. Personen känner sannolikt igen sig "
                "starkare i vissa delar av profilen än i andra."
            ),
            "high_text": (
                "Svaren visar tydliga skillnader mellan personlighetsdragen "
                "och ger en profil med framträdande styrkor och områden som "
                "kan vara mer krävande."
            ),
        },
        "en": {
            "title": "Profile Spread",
            "low_pole": (
                "Responses show less differentiation across the traits which may be "
                "due to less consistency or lack of self-insight"
            ),
            "high_pole": (
                "Responses show clear strengths and development needs, profile "
                "demonstrates a wide range of scores across the traits"
            ),
            "low_text": (
                "The responses show less differentiation across personality "
                "traits. This may reflect a more general response pattern or "
                "less consistency between related responses."
            ),
            "middle_text": (
                "The profile contains a mixture of differentiated and less "
                "differentiated responses. The candidate is likely to recognise "
                "some parts of the profile more strongly than others."
            ),
            "high_text": (
                "The responses show clear differentiation across personality "
                "traits, producing a profile with distinct strengths and areas "
                "that may be more demanding."
            ),
        },
    },
    {
        "key": "ratings_spread",
        "source_name": "reliability",
        "sv": {
            "title": "Värderingsspridning",
            "low_pole": (
                "Svaren på frågeformuläret visar mindre användning av extrema "
                "alternativ, tendens att välja ett smalt urval av betyg"
            ),
            "high_pole": (
                "Svaren på enkäten visar tydlig differentiering i svaren; mer "
                "användning av extrema alternativ"
            ),
            "low_text": (
                "Personen använde färre ytterlighetsalternativ och valde "
                "inom ett relativt smalt spann av skattningar."
            ),
            "middle_text": (
                "Personen verkar ha använt hela svarsskalan utan någon tydlig "
                "preferens för vare sig mitten eller ytterligheterna."
            ),
            "high_text": (
                "Personen använde ett brett spann av svarsalternativ, "
                "med större användning av skattningsskalans ytterligheter."
            ),
        },
        "en": {
            "title": "Ratings Spread",
            "low_pole": (
                "Responses to the questionnaire show less use of extreme options, "
                "tendency to select narrow range of ratings"
            ),
            "high_pole": (
                "Responses to the questionnaire show clear differentiation in "
                "responses; more use of extreme options"
            ),
            "low_text": (
                "The candidate used fewer extreme response options and tended "
                "to select a relatively narrow range of ratings."
            ),
            "middle_text": (
                "The candidate appears to have used the full response scale "
                "without a strong preference for either middle or extreme "
                "response options."
            ),
            "high_text": (
                "The candidate used a wide range of response options, with "
                "greater use of the extreme ends of the rating scale."
            ),
        },
    },
]


def build_response_style_results(
    personality_competencies: list[dict[str, Any]],
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Build localized response-style results using rounded STEN 1–10."""
    language = _normalise_language(language)
    band_labels = _BAND_LABELS[language]

    competency_lookup = {
        (item.get("competency") or "").strip().lower(): item
        for item in (personality_competencies or [])
    }

    response_styles = []

    for config in _STYLE_CONTENT:
        content = config[language]
        source = competency_lookup.get(config["source_name"])
        raw_value = source.get("sten_rounded") if source else None

        try:
            value = (
                int(round(float(raw_value)))
                if raw_value is not None
                else None
            )
        except (TypeError, ValueError):
            value = None

        if value is not None:
            value = max(1, min(10, value))

        if value is None:
            band_key = "missing"
            interpretation = band_labels["missing_interpretation"]
        elif value <= 3:
            band_key = "low"
            interpretation = content["low_text"]
        elif value <= 7:
            band_key = "middle"
            interpretation = content["middle_text"]
        else:
            band_key = "high"
            interpretation = content["high_text"]

        if value is None:
            scale_side = None
            scale_strength = 0
        elif value <= 5:
            scale_side = "left"
            scale_strength = 6 - value
        else:
            scale_side = "right"
            scale_strength = value - 5

        response_styles.append({
            "key": config["key"],
            "title": content["title"],
            "low_pole": content["low_pole"],
            "high_pole": content["high_pole"],
            "value": value,
            "available": value is not None,
            "band_key": band_key,
            "band_label": band_labels[band_key],
            "interpretation": interpretation,
            "scale_side": scale_side,
            "scale_strength": scale_strength,
            "source_name": source.get("competency") if source else None,
            "percentile": source.get("percentile") if source else None,
        })

    return response_styles
