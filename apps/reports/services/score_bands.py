from apps.reports.constants import DEFAULT_SCORE_BANDS


def resolve_score_band(score: int | None, bands=None) -> str | None:
    if score is None:
        return None

    bands = bands or DEFAULT_SCORE_BANDS

    for band in bands:
        if band["min"] <= score <= band["max"]:
            return band["key"]

    return None