from apps.reports.libraries.motivation.definitions import MOTIVATION_REPORTS
from apps.reports.libraries.motivation.content import (
    PRACTITIONER_SECTION_CONTENT,
    MANAGER_SECTION_CONTENT,
    COACHING_SECTION_CONTENT,
)
from apps.reports.libraries.motivation.resolver import (
    resolve_motivation_report_text,
    resolve_practitioner_factor_content,
    resolve_manager_factor_content,
    resolve_coaching_factor_content,
)

def normalize_competency_name(name: str | None) -> str:
    return (name or "").strip().lower()


def build_scores_by_competency(competencies: list[dict]) -> dict:
    result = {}

    for item in competencies:
        raw_name = item.get("competency")
        normalized_name = normalize_competency_name(raw_name)
        score = item.get("score")

        if normalized_name:
            result[normalized_name] = score

    return result


def resolve_score_from_aliases(scores_by_competency: dict, aliases: list[str]) -> int | None:
    for alias in aliases:
        normalized_alias = normalize_competency_name(alias)
        if normalized_alias in scores_by_competency:
            return scores_by_competency[normalized_alias]
    return None


def build_practitioner_factor_items(
    *,
    scores_by_competency: dict,
    item_definitions: list[dict],
    bands=None,
) -> list[dict]:
    items = []

    for item_def in item_definitions:
        factor_key = item_def["key"]
        label = item_def["label"]
        aliases = item_def.get("aliases", [label])

        score = resolve_score_from_aliases(scores_by_competency, aliases)

        resolved = resolve_practitioner_factor_content(
            factor_key=factor_key,
            score=score,
            bands=bands,
        )

        items.append({
            "key": factor_key,
            "label": label,
            "aliases": aliases,
            "score": resolved["score"],
            "score_band": resolved["score_band"],
            "descriptor": resolved["descriptor"],
            "profile_summary": resolved["profile_summary"],
            "implications": resolved["implications"],
            "ideal_environment": resolved["ideal_environment"],
        })

    return items


def build_practitioner_report(
    *,
    competencies: list[dict],
    bands=None,
) -> dict:
    report_def = MOTIVATION_REPORTS["practitioner_report"]
    scores_by_competency = build_scores_by_competency(competencies)

    all_items = build_practitioner_factor_items(
        scores_by_competency=scores_by_competency,
        item_definitions=report_def["items"],
        bands=bands,
    )

    scored_items = [item for item in all_items if item["score"] is not None]
    sorted_items = sorted(scored_items, key=lambda x: x["score"], reverse=True)

    top_n = report_def.get("top_n", 3)
    bottom_n = report_def.get("bottom_n", 3)

    top_items = sorted_items[:top_n]
    bottom_items = sorted(scored_items, key=lambda x: x["score"])[:bottom_n]

    return {
        "key": "practitioner_report",
        "title": report_def["title"],
        "intro": report_def["intro"],
        "domain": report_def["domain"],
        "sections": [
            {
                "type": "motivation_summary",
                "title": PRACTITIONER_SECTION_CONTENT["motivation_summary"]["title"],
                "intro": PRACTITIONER_SECTION_CONTENT["motivation_summary"]["intro"],
                "items": [
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "score": item["score"],
                        "descriptor": item["descriptor"],
                    }
                    for item in all_items
                ],
            },
            {
                "type": "all_motivators",
                "title": PRACTITIONER_SECTION_CONTENT["all_motivators"]["title"],
                "intro": PRACTITIONER_SECTION_CONTENT["all_motivators"]["intro"],
                "items": [
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "score": item["score"],
                        "score_band": item["score_band"],
                        "descriptor": item["descriptor"],
                        "profile_summary": item["profile_summary"],
                    }
                    for item in all_items
                ],
            },
            {
                "type": "implications",
                "title": PRACTITIONER_SECTION_CONTENT["implications"]["title"],
                "intro": PRACTITIONER_SECTION_CONTENT["implications"]["intro"],
                "top_title": PRACTITIONER_SECTION_CONTENT["implications"]["top_title"],
                "bottom_title": PRACTITIONER_SECTION_CONTENT["implications"]["bottom_title"],
                "top_items": [
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "score": item["score"],
                        "descriptor": item["descriptor"],
                        "implications": item["implications"],
                    }
                    for item in top_items
                ],
                "bottom_items": [
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "score": item["score"],
                        "descriptor": item["descriptor"],
                        "implications": item["implications"],
                    }
                    for item in bottom_items
                ],
            },
            {
                "type": "ideal_environment",
                "title": PRACTITIONER_SECTION_CONTENT["ideal_environment"]["title"],
                "intro": PRACTITIONER_SECTION_CONTENT["ideal_environment"]["intro"],
                "top_title": PRACTITIONER_SECTION_CONTENT["ideal_environment"]["top_title"],
                "items": [
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "score": item["score"],
                        "ideal_environment": item["ideal_environment"],
                    }
                    for item in top_items
                ],
            },
        ],
    }

def build_motivation_report(
    *,
    report_key: str,
    scores_by_competency: dict,
    bands=None,
) -> dict:
    report_def = MOTIVATION_REPORTS[report_key]

    items = []
    for item_def in report_def["items"]:
        item_key = item_def["key"]
        label = item_def["label"]
        aliases = item_def.get("aliases", [label])

        score = resolve_score_from_aliases(scores_by_competency, aliases)

        resolved = resolve_motivation_report_text(
            report_key=report_key,
            competency=item_key,
            score=score,
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


def build_manager_factor_items(
    *,
    scores_by_competency: dict,
    item_definitions: list[dict],
    bands=None,
) -> list[dict]:
    items = []

    for item_def in item_definitions:
        factor_key = item_def["key"]
        label = item_def["label"]
        aliases = item_def.get("aliases", [label])

        score = resolve_score_from_aliases(scores_by_competency, aliases)

        resolved = resolve_manager_factor_content(
            factor_key=factor_key,
            score=score,
            bands=bands,
        )

        items.append({
            "key": factor_key,
            "label": label,
            "aliases": aliases,
            "score": resolved["score"],
            "score_band": resolved["score_band"],
            "descriptor": resolved["descriptor"],
            "management_tips": resolved["management_tips"],
            "relationships_text": resolved["relationships_text"],
        })

    return items


def build_manager_report(
    *,
    competencies: list[dict],
    bands=None,
) -> dict:
    report_def = MOTIVATION_REPORTS["manager_report"]
    scores_by_competency = build_scores_by_competency(competencies)

    all_items = build_manager_factor_items(
        scores_by_competency=scores_by_competency,
        item_definitions=report_def["items"],
        bands=bands,
    )

    scored_items = [item for item in all_items if item["score"] is not None]
    sorted_items = sorted(scored_items, key=lambda x: x["score"], reverse=True)

    top_n = report_def.get("top_n", 3)
    top_items = sorted_items[:top_n]

    return {
        "key": "manager_report",
        "title": report_def["title"],
        "intro": report_def["intro"],
        "domain": report_def["domain"],
        "sections": [
            {
                "type": "management_tips",
                "title": MANAGER_SECTION_CONTENT["management_tips"]["title"],
                "intro": MANAGER_SECTION_CONTENT["management_tips"]["intro"],
                "items": [
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "score": item["score"],
                        "descriptor": item["descriptor"],
                        "management_tips": item["management_tips"],
                    }
                    for item in top_items
                ],
            },
            {
                "type": "relationships_at_work",
                "title": MANAGER_SECTION_CONTENT["relationships_at_work"]["title"],
                "intro": MANAGER_SECTION_CONTENT["relationships_at_work"]["intro"],
                "items": [
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "score": item["score"],
                        "descriptor": item["descriptor"],
                        "relationships_text": item["relationships_text"],
                    }
                    for item in top_items
                ],
            },
        ],
    }

def build_coaching_factor_items(
    *,
    scores_by_competency: dict,
    item_definitions: list[dict],
    bands=None,
) -> list[dict]:
    items = []

    for item_def in item_definitions:
        factor_key = item_def["key"]
        label = item_def["label"]
        aliases = item_def.get("aliases", [label])

        score = resolve_score_from_aliases(scores_by_competency, aliases)

        resolved = resolve_coaching_factor_content(
            factor_key=factor_key,
            score=score,
            bands=bands,
        )

        items.append({
            "key": factor_key,
            "label": label,
            "aliases": aliases,
            "score": resolved["score"],
            "score_band": resolved["score_band"],
            "descriptor": resolved["descriptor"],
            "summary": resolved["summary"],
            "upsides": resolved["upsides"],
            "downsides": resolved["downsides"],
            "questions": resolved["questions"],
        })

    return items


def build_motivation_coaching_report(
    *,
    competencies: list[dict],
    bands=None,
) -> dict:
    report_def = MOTIVATION_REPORTS["coaching_report"]
    scores_by_competency = build_scores_by_competency(competencies)

    all_items = build_coaching_factor_items(
        scores_by_competency=scores_by_competency,
        item_definitions=report_def["items"],
        bands=bands,
    )

    scored_items = [item for item in all_items if item["score"] is not None]
    sorted_items = sorted(scored_items, key=lambda x: x["score"], reverse=True)

    top_n = report_def.get("top_n", 3)
    top_items = sorted_items[:top_n]

    return {
        "key": "coaching_report",
        "title": report_def["title"],
        "intro": report_def["intro"],
        "domain": report_def["domain"],
        "sections": [
            {
                "type": "motivation_summary",
                "title": COACHING_SECTION_CONTENT["motivation_summary"]["title"],
                "intro": COACHING_SECTION_CONTENT["motivation_summary"]["intro"],
                "items": [
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "score": item["score"],
                        "descriptor": item["descriptor"],
                    }
                    for item in all_items
                ],
            },
            {
                "type": "coaching_facilitation",
                "title": COACHING_SECTION_CONTENT["coaching_facilitation"]["title"],
                "intro": COACHING_SECTION_CONTENT["coaching_facilitation"]["intro"],
                "items": [
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "score": item["score"],
                        "descriptor": item["descriptor"],
                        "summary": item["summary"],
                        "upsides": item["upsides"],
                        "downsides": item["downsides"],
                        "questions": item["questions"],
                    }
                    for item in top_items
                ],
            },
        ],
    }