"""Build a candidate-specific Leadership Report from SOVA scores."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path


_DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "leadership_report.json"
)

# SOVA returns these competencies in English even when Talena is Swedish.
_SOURCE_NAMES = {
    "creates_the_vision": ("Creates the Vision",),
    "generates_solutions": ("Generates Solutions",),
    "builds_alliances": ("Builds Alliances",),
    "embraces_diversity": ("Embraces Diversity",),
    "nurtures_talent": ("Nurtures Talent",),
    "leads_by_example": ("Leads by Example", "Leads by Exapmle"),
    "clarifies_expectations": ("Clarifies Expectations",),
    "drives_momentum": ("Drives Momentum",),
}


@lru_cache(maxsize=1)
def _load_leadership_report_data() -> dict:
    with _DATA_FILE.open("r", encoding="utf-8") as source:
        return json.load(source)


def _name_key(value: str | None) -> str:
    value = (value or "").strip().casefold().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def _parse_score(item: dict) -> float | None:
    # STIVE is SOVA's native 1–5 leadership preference score.
    raw_score = item.get("stive")
    if raw_score is None:
        raw_score = item.get("stive_rounded")
    if raw_score is None and str(item.get("category") or "").strip().lower() == "leadership":
        scale = str(item.get("scale") or "").strip().lower().replace("-", "_")
        if scale in {"one_to_five", "1_to_5", "1 to 5"}:
            raw_score = item.get("score")

    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return None
    if not 1 <= score <= 5:
        return None
    return score


def _display_score(score: float, language: str) -> str:
    rendered = f"{score:.1f}".rstrip("0").rstrip(".")
    if language == "sv":
        rendered = rendered.replace(".", ",")
        return f"Poäng {rendered}"
    return f"Score {rendered}"


def build_leadership_report_content(
    language_code: str | None = None,
    competencies: list[dict] | None = None,
) -> dict:
    """Return localized report copy matched to this candidate's actual scores."""
    language = (language_code or "en").lower().split("-", 1)[0]
    language = "sv" if language == "sv" else "en"
    content = _load_leadership_report_data()[language]

    source_key_by_name = {}
    for source_key, source_names in _SOURCE_NAMES.items():
        for source_name in source_names:
            source_key_by_name[_name_key(source_name)] = source_key

    report_competencies = [
        competency
        for quadrant in content["quadrants"]
        for competency in quadrant["competencies"]
    ]
    source_keys = list(_SOURCE_NAMES)
    for index, competency in enumerate(report_competencies):
        if index < len(source_keys):
            source_key_by_name[_name_key(competency["title"])] = source_keys[index]

    scores_by_key = {}
    for item in competencies or []:
        name_key = _name_key(item.get("competency") or item.get("name"))
        source_key = source_key_by_name.get(name_key)
        score = _parse_score(item)
        if source_key and score is not None:
            scores_by_key.setdefault(source_key, score)

    quadrants = []
    all_competencies = []
    slot_index = 0
    for quadrant in content["quadrants"]:
        rendered_quadrant = {**quadrant, "competencies": []}
        for competency in quadrant["competencies"]:
            source_key = source_keys[slot_index] if slot_index < len(source_keys) else None
            slot_index += 1
            score = scores_by_key.get(source_key) if source_key else None
            if score is None:
                continue

            rounded_score = max(1, min(5, int(round(score))))
            level_key = "low" if rounded_score == 1 else ("high" if rounded_score == 5 else "mid")
            level = next(
                item for item in competency["levels"]
                if item["key"] == level_key
            )
            rendered = {
                **competency,
                "score": score,
                "score_display": _display_score(score, language),
                "score_percent": score * 20,
                "level": level,
                "interpretation": level["interpretation"],
                "questions": level["questions"],
            }
            rendered_quadrant["competencies"].append(rendered)
            all_competencies.append(rendered)

        quadrants.append(rendered_quadrant)

    ordered = sorted(all_competencies, key=lambda item: item["score"], reverse=True)
    return {
        **content,
        "quadrants": quadrants,
        "has_results": bool(all_competencies),
        "scores_count": len(all_competencies),
        "total_competencies": 8,
        "top_competencies": ordered[:2],
        "development_competencies": (
            [min(all_competencies, key=lambda item: item["score"])]
            if all_competencies else []
        ),
        "empty_title": "Inga ledarskapspoäng tillgängliga" if language == "sv"
            else "No leadership scores available",
        "empty_body": (
            "SOVA har ännu inte skickat resultat för kandidatens åtta ledarskapskompetenser."
            if language == "sv"
            else "SOVA has not provided results for this candidate's eight leadership competencies yet."
        ),
        "score_count_label": "av 8 poäng" if language == "sv" else "of 8 scores",
        "highest_scores_title": "Högsta resultat" if language == "sv" else "Highest results",
        "lowest_score_title": "Lägsta resultat" if language == "sv" else "Lowest result",
        "score_scale_label": "Poängskala 1–5" if language == "sv" else "Score scale 1–5",
    }
