"""Load Talena's supplied bilingual leadership report text."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


_DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "leadership_report.json"
)


@lru_cache(maxsize=1)
def _load_leadership_report_data() -> dict:
    with _DATA_FILE.open("r", encoding="utf-8") as source:
        return json.load(source)


def build_leadership_report_content(language_code: str | None = None) -> dict:
    """Return the supplied leadership report copy in the requested language."""
    language = (language_code or "en").lower().split("-", 1)[0]
    language = "sv" if language == "sv" else "en"
    return _load_leadership_report_data()[language]
