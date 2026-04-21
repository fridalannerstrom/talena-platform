from apps.reports.services.resolver import resolve_report_text
from apps.reports.services.score_bands import resolve_score_band


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



def build_motivation_coaching_report(
    *,
    competencies: list[dict],
    report_definition: dict,
    content_library: dict,
    bands=None,
) -> dict:
    """
    Builds a coaching-style motivation report.

    Logic:
    - take all MQ competencies
    - match them against coaching content aliases
    - resolve score band
    - sort by highest score
    - pick top N
    """

    matched_items = []

    for content_key, content_def in content_library.items():
        aliases = content_def.get("aliases", [])
        label = content_def.get("label", content_key)

        matched_score = None
        matched_source_name = None

        for comp in competencies:
            comp_name = comp.get("competency")
            comp_score = comp.get("sten_rounded")

            if normalize_competency_name(comp_name) in {
                normalize_competency_name(alias) for alias in aliases
            }:
                matched_score = comp_score
                matched_source_name = comp_name
                break

        if matched_score is None:
            continue

        score_band = resolve_score_band(matched_score, bands=bands)
        band_content = content_def.get("bands", {}).get(score_band, {})

        matched_items.append({
            "key": content_key,
            "label": label,
            "source_name": matched_source_name,
            "score": matched_score,
            "score_band": score_band,
            "summary": band_content.get("summary", ""),
            "upsides": band_content.get("upsides", []),
            "downsides": band_content.get("downsides", []),
            "questions": band_content.get("questions", []),
        })

    matched_items.sort(key=lambda item: item.get("score") or 0, reverse=True)

    top_n = report_definition.get("top_n", 3)
    selected_items = matched_items[:top_n]

    return {
        "key": "coaching_report",
        "title": report_definition.get("title", "Coaching Report"),
        "intro": report_definition.get("intro", ""),
        "domain": report_definition.get("domain", "motivation"),
        "items": selected_items,
    }