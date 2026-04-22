def resolve_motivation_score_band(score: int | None) -> str:
    if score is None:
        return ""

    score = int(score)

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