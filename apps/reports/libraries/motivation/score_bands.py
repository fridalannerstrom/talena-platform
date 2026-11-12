def resolve_motivation_score_band(score: int | float | None) -> str:
    if score is None:
        return ""

    # Report copy still uses the established five bands, but the precise
    # score must be rounded only for band selection—not for evidence/ranking.
    try:
        score = int(round(float(score)))
    except (TypeError, ValueError):
        return ""

    if score == 1:
        return "1"
    if score == 2:
        return "2"
    if score == 3:
        return "3"
    if score == 4:
        return "4"
    if score == 5:
        return "5"

    return ""