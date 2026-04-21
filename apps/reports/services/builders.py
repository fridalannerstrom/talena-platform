from apps.reports.services.resolver import resolve_report_text


def normalize_competency_name(name: str | None) -> str:
    return (name or "").strip().lower()


def build_scores_by_competency(competencies: list[dict]) -> dict:
    """
    Builds a lookup dict from raw Sova competencies.
    Key = normalized competency name
    Value = sten_rounded
    """
    result = {}

    for item in competencies:
        raw_name = item.get("competency")
        normalized_name = normalize_competency_name(raw_name)
        score = item.get("sten_rounded")

        if normalized_name:
            result[normalized_name] = score

    return result


def resolve_score_from_aliases(scores_by_competency: dict, aliases: list[str]) -> int | None:
    """
    Tries all aliases in order and returns the first matching score.
    """
    for alias in aliases:
        normalized_alias = normalize_competency_name(alias)
        if normalized_alias in scores_by_competency:
            return scores_by_competency[normalized_alias]
    return None


def build_report(
    *,
    report_key: str,
    scores_by_competency: dict,
    report_definitions: dict,
    text_library: dict,
    bands=None,
) -> dict:
    """
    Builds one rendered report using:
    - a report definition
    - raw score lookup
    - text library
    """
    report_def = report_definitions[report_key]

    items = []
    for item_def in report_def["items"]:
        item_key = item_def["key"]
        label = item_def["label"]
        aliases = item_def.get("aliases", [label])

        score = resolve_score_from_aliases(scores_by_competency, aliases)

        resolved = resolve_report_text(
            report_key=report_key,
            competency=item_key,
            score=score,
            text_library=text_library,
            bands=bands,
        )

        items.append({
            "key": item_key,
            "competency": label,
            "aliases": aliases,
            "score": resolved["score"],
            "score_band": resolved["score_band"],
            "text": resolved["text"],
        })

    return {
        "key": report_key,
        "title": report_def["title"],
        "intro": report_def["intro"],
        "domain": report_def["domain"],
        "items": items,
    }


def build_reports(
    *,
    report_keys: list[str],
    scores_by_competency: dict,
    report_definitions: dict,
    text_library: dict,
    bands=None,
) -> list[dict]:
    """
    Builds multiple reports for UI tabs or similar.
    """
    return [
        build_report(
            report_key=report_key,
            scores_by_competency=scores_by_competency,
            report_definitions=report_definitions,
            text_library=text_library,
            bands=bands,
        )
        for report_key in report_keys
    ]