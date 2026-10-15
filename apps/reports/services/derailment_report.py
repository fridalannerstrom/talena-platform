"""Build localized candidate-specific derailment report content from STEN scores."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path


_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "derailment_report.json"

_SOURCE_NAMES = {
    "dependent": ("Dependent", "Beroende"),
    "over_sensitive": ("Over-sensitive", "Oversensitive", "Over Sensitive", "Överkänslig"),
    "detached": ("Detached", "Isolated", "Isolerad"),
    "individualistic": ("Individualistic", "Individualistisk"),
    "unconventional": ("Unconventional", "Okonventionell"),
    "unpredictable": ("Unpredictable", "Oberäknelig"),
    "dramatic": ("Dramatic", "Dramatisk"),
    "boldness": ("Boldness", "Bold", "Djärv"),
    "rigid": ("Rigid", "Inflexible", "Oflexibel"),
    "meticulous": ("Meticulous", "Pedantic", "Pedantic", "Pedantisk"),
    "stubborn": ("Stubborn", "Envis"),
    "hesitant": ("Hesitant", "Tveksam"),
    "casual": ("Casual", "Volatile", "Flyktig"),
    "intense": ("Intense", "Intensiv"),
}


@lru_cache(maxsize=1)
def _load_data() -> dict:
    with _DATA_FILE.open("r", encoding="utf-8") as source:
        return json.load(source)


def _name_key(value: str | None) -> str:
    value = (value or "").strip().casefold().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def _score(item: dict) -> int | None:
    raw = item.get("sten_rounded")
    if raw is None:
        raw = item.get("sten")
    if raw is None:
        raw = item.get("score")
    try:
        return max(1, min(10, int(round(float(raw)))))
    except (TypeError, ValueError):
        return None


def build_derailment_report_content(
    language_code: str | None = None,
    competencies: list[dict] | None = None,
) -> dict:
    """Return localized report copy matched to the candidate's STEN results."""
    language = (language_code or "en").lower().split("-", 1)[0]
    language = "sv" if language == "sv" else "en"
    content = _load_data()[language]

    source_key_by_name = {}
    for key, names in _SOURCE_NAMES.items():
        for name in names:
            source_key_by_name[_name_key(name)] = key

    result_by_key = {}
    for item in competencies or []:
        name = item.get("competency") or item.get("name")
        key = source_key_by_name.get(_name_key(name))
        score = _score(item)
        if key and score is not None:
            result_by_key.setdefault(key, score)

    factors = []
    for factor in content["factors"]:
        score = result_by_key.get(factor["key"])
        if score is None:
            continue
        level_key = "low" if score <= 3 else ("high" if score >= 8 else "mid")
        factors.append({
            **factor,
            "score": score,
            "score_percent": score * 10,
            "score_display": f'{content["score_label"]} {score}',
            "scale_segments": list(range(1, 11)),
            "level_key": level_key,
            "level_label": content[f"{level_key}_label"],
            "interpretation": factor["levels"][level_key],
        })

    return {
        **content,
        "factors": factors,
        "has_results": bool(factors),
        "scores_count": len(factors),
        "total_factors": 14,
    }
