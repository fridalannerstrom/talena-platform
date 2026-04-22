from apps.reports.libraries.cognitive.score_bands import resolve_cognitive_percentile_band
from apps.reports.libraries.cognitive.content import COGNITIVE_CONTENT


def resolve_cognitive_report_content(
    *,
    test_key: str,
    audience: str,
    percentile: int | None,
) -> dict:
    percentile_band = resolve_cognitive_percentile_band(percentile)

    test_content = COGNITIVE_CONTENT.get(test_key, {})
    audience_content = test_content.get(audience, {})
    band_content = audience_content.get("bands", {}).get(percentile_band, {})

    return {
        "percentile": percentile,
        "percentile_band": percentile_band,
        "label": test_content.get("label", ""),
        "intro": audience_content.get("intro", ""),
        "test_description": audience_content.get("test_description", ""),
        "result_text": band_content.get("result_text", ""),
    }