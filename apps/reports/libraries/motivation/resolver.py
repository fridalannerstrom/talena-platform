from apps.reports.services.score_bands import resolve_score_band
from apps.reports.libraries.motivation.content import MOTIVATION_TEXTS, PRACTITIONER_FACTOR_CONTENT


def resolve_motivation_report_text(
    *,
    report_key: str,
    competency: str,
    score: int | None,
    bands=None,
) -> dict:
    band = resolve_score_band(score, bands=bands)

    text = (
        MOTIVATION_TEXTS.get(report_key, {})
        .get(competency, {})
        .get(band, "")
    )

    return {
        "score": score,
        "score_band": band,
        "text": text,
    }


def resolve_practitioner_factor_content(
    *,
    factor_key: str,
    score: int | None,
    bands=None,
) -> dict:
    score_band = resolve_score_band(score, bands=bands)

    factor_content = PRACTITIONER_FACTOR_CONTENT.get(factor_key, {})
    band_content = factor_content.get("bands", {}).get(score_band, {})

    return {
        "score": score,
        "score_band": score_band,
        "descriptor": factor_content.get("descriptor", ""),
        "profile_summary": band_content.get("profile_summary", ""),
        "implications": band_content.get("implications", ""),
        "ideal_environment": band_content.get("ideal_environment", []),
    }