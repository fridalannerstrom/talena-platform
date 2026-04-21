from apps.reports.services.score_bands import resolve_score_band


def resolve_report_text(
    *,
    report_key: str,
    competency: str,
    score: int | None,
    text_library: dict,
    bands=None,
) -> dict:
    band = resolve_score_band(score, bands=bands)

    text = (
        text_library.get(report_key, {})
        .get(competency, {})
        .get(band, "")
    )

    return {
        "score": score,
        "score_band": band,
        "text": text,
    }