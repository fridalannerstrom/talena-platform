from apps.reports.libraries.motivation.score_bands import resolve_motivation_score_band
from apps.reports.libraries.motivation.content import (
    MOTIVATION_TEXTS,
    PRACTITIONER_FACTOR_CONTENT,
    MANAGER_FACTOR_CONTENT,
    MOTIVATION_COACHING_CONTENT,
)


def resolve_motivation_report_text(
    *,
    report_key: str,
    competency: str,
    score: int | None,
    bands=None,
) -> dict:
    score_band = resolve_motivation_score_band(score)

    text = (
        MOTIVATION_TEXTS.get(report_key, {})
        .get(competency, {})
        .get(score_band, "")
    )

    return {
        "score": score,
        "score_band": score_band,
        "text": text,
    }


def resolve_practitioner_factor_content(
    *,
    factor_key: str,
    score: int | None,
    bands=None,
) -> dict:
    score_band = resolve_motivation_score_band(score)

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


def resolve_manager_factor_content(
    *,
    factor_key: str,
    score: int | None,
    bands=None,
) -> dict:
    score_band = resolve_motivation_score_band(score)

    factor_content = MANAGER_FACTOR_CONTENT.get(factor_key, {})
    band_content = factor_content.get("bands", {}).get(score_band, {})

    return {
        "score": score,
        "score_band": score_band,
        "descriptor": factor_content.get("descriptor", ""),
        "management_tips": band_content.get("management_tips", ""),
        "relationships_text": band_content.get("relationships_text", ""),
    }

def resolve_coaching_factor_content(
    *,
    factor_key: str,
    score: int | None,
    bands=None,
) -> dict:
    score_band = resolve_motivation_score_band(score)

    factor_content = MOTIVATION_COACHING_CONTENT.get(factor_key, {})
    band_content = factor_content.get("bands", {}).get(score_band, {})

    return {
        "score": score,
        "score_band": score_band,
        "label": factor_content.get("label", ""),
        "descriptor": factor_content.get("descriptor", ""),
        "summary": band_content.get("summary", ""),
        "upsides": band_content.get("upsides", []),
        "downsides": band_content.get("downsides", []),
        "questions": band_content.get("questions", []),
    }