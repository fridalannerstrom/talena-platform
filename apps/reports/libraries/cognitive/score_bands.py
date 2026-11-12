def resolve_cognitive_percentile_band(percentile: int | None) -> str:
    if percentile is None:
        return ""

    percentile = int(percentile)

    if percentile <= 24:
        return "low"
    if percentile <= 74:
        return "average"
    return "high"