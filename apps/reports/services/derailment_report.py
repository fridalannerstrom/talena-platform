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


# Only the score-jargon opening is edited; the approved interpretation
# continues unchanged. Missing text is never fabricated.
_NEUTRAL_OPENINGS = {
    "sv": (
        ("Låg poäng på denna skala tyder på att", "Resultatet tyder på att"),
        ("Poäng i mitten av denna skala innebär att", "Resultatet tyder på att"),
        ("En hög poäng på denna skala tyder på att", "Resultatet tyder på att"),
        ("En låg poäng på skalan tyder på", "Resultatet tyder på att"),
        ("En hög poäng på skalan tyder på", "Resultatet tyder på att"),
        ("En låg poäng på skalan innebär att", "Resultatet tyder på att"),
        ("Poäng i mitten av skalan innebär att", "Resultatet tyder på att"),
        ("En hög poäng på skalan kan innebära att", "Resultatet kan tyda på att"),
        ("Personer som får låg poäng på denna skala", "Personer med denna profil"),
        ("De som får poäng i mitten på denna skala", "Personer med denna profil"),
        ("De som får höga poäng", "Personer med denna profil"),
        ("De som får låga poäng på skalan", "Personer med denna profil"),
        ("De som får hög poäng på denna skala", "Personer med denna profil"),
        ("Personer som får höga poäng på skalan", "Personer med denna profil"),
    ),
    "en": (
        ("A low score suggests", "The result suggests"),
        ("A mid-range score suggests", "The result suggests"),
        ("A high score suggests", "The result suggests"),
        ("A high score may indicate", "The result may indicate"),
        ("People with low scores on this scale", "People with this profile"),
        ("Mid-range scores do not suggest", "The result does not suggest"),
        ("High scores may indicate", "The result may indicate"),
        ("People with low scores", "People with this profile"),
        ("People with high scores", "People with this profile"),
    ),
}


def _display_interpretation(text: str | None, language: str) -> str:
    """Remove only recognised score-level preambles from existing approved text."""
    value = (text or "").strip()
    for prefix, replacement in _NEUTRAL_OPENINGS[language]:
        if value.startswith(prefix):
            return replacement + value[len(prefix):]
    return value


def _centered_scale_fill(score: int) -> list[int]:
    """Fill from the midline between 5 and 6 towards the actual 1–10 result."""
    return list(range(score, 6)) if score <= 5 else list(range(6, score + 1))


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
        # Exactly one approved level is selected for each result.
        level_key = "low" if score <= 2 else ("mid" if score <= 7 else "high")
        selected_text = _display_interpretation(
            factor.get("levels", {}).get(level_key), language
        )
        interpretations = (
            [{"key": level_key, "text": selected_text}]
            if selected_text else []
        )
        factors.append({
            **factor,
            "score": score,
            "score_percent": score * 10,
            "score_display": str(score),
            "score_accessible": (
                f"Resultat {score} av 10" if language == "sv"
                else f"Result {score} of 10"
            ),
            "scale_segments": list(range(1, 11)),
            "scale_filled_segments": _centered_scale_fill(score),
            "interpretations": interpretations,
        })

    return {
        **content,
        "factors": factors,
        "has_results": bool(factors),
        "scores_count": len(factors),
        "total_factors": 14,
    }
