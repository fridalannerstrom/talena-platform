"""Build a candidate-specific Leadership Report from SOVA scores."""
from __future__ import annotations

import json
import math
import re
from html import escape
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
    rendered = str(score)
    if rendered.endswith(".0"):
        rendered = rendered[:-2]
    if language == "sv":
        rendered = rendered.replace(".", ",")
        return f"Poäng {rendered}"
    return f"Score {rendered}"


def _clean_display_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _split_reflection_questions(value: str | None) -> list[str]:
    pieces = re.split(r"(?:^|\n)\s*•\s*", (value or "").strip())
    return [_clean_display_text(piece) for piece in pieces if _clean_display_text(piece)]


def _wrap_svg_label(value: str, limit: int = 16) -> list[str]:
    words = value.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > limit:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _build_leadership_chart_svg(content: dict, scores_by_key: dict, language: str) -> str:
    """Render a balanced eight-petal leadership profile from SOVA 1–5 scores.

    Same four-area flower language as the candidate Team report.  The SVG is
    generated server-side (not by Chart.js); only presentation is changed.
    """
    width, height = 900, 780
    cx, cy, radius = 450, 390, 245
    source_keys = list(_SOURCE_NAMES)
    quadrant_colors = ("#ef978f", "#dbada7", "#a0baae", "#d9bc90")

    def point(distance: float, angle: float) -> tuple[float, float]:
        radians = math.radians(angle)
        return cx + distance * math.cos(radians), cy + distance * math.sin(radians)

    def fmt(value: float) -> str:
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def radial_sector(start_angle: float, end_angle: float, sector_radius: float) -> str:
        """Straight radial sector used only for faint full-scale guides."""
        start_x, start_y = point(sector_radius, start_angle)
        end_x, end_y = point(sector_radius, end_angle)
        return (
            f"M {cx} {cy} L {fmt(start_x)} {fmt(start_y)} "
            f"A {fmt(sector_radius)} {fmt(sector_radius)} 0 0 1 "
            f"{fmt(end_x)} {fmt(end_y)} Z"
        )

    def petal_path(index: int, sector_radius: float) -> str:
        """Round the outer corners of a radial sector without changing its reach."""
        # Two neighbouring petals have a little space around their edges.
        start_angle = -135 + index * 45 + 2.5
        end_angle = -90 + index * 45 - 2.5
        shoulder_radius = max(22.0, sector_radius - 16.0)
        corner_angle = min(10.0, math.degrees(15.0 / sector_radius))

        shoulder_start = point(shoulder_radius, start_angle)
        tip_start = point(sector_radius, start_angle)
        arc_start = point(sector_radius, start_angle + corner_angle)
        arc_end = point(sector_radius, end_angle - corner_angle)
        tip_end = point(sector_radius, end_angle)
        shoulder_end = point(shoulder_radius, end_angle)

        return (
            f"M {cx} {cy} "
            f"L {fmt(shoulder_start[0])} {fmt(shoulder_start[1])} "
            f"Q {fmt(tip_start[0])} {fmt(tip_start[1])} "
            f"{fmt(arc_start[0])} {fmt(arc_start[1])} "
            f"A {fmt(sector_radius)} {fmt(sector_radius)} 0 0 1 "
            f"{fmt(arc_end[0])} {fmt(arc_end[1])} "
            f"Q {fmt(tip_end[0])} {fmt(tip_end[1])} "
            f"{fmt(shoulder_end[0])} {fmt(shoulder_end[1])} Z"
        )

    parts = [
        f'<svg class="leadership-report__wheel" viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="leadership-wheel-title leadership-wheel-desc" '
        f'xmlns="http://www.w3.org/2000/svg">',
        f'<title id="leadership-wheel-title">{escape(content["chart_intro"]["title"])}</title>',
        f'<desc id="leadership-wheel-desc">{escape(content["chart_intro"]["body"]).replace(chr(10), " ")}</desc>',
    ]

    flattened = [
        (quadrant_index, competency)
        for quadrant_index, quadrant in enumerate(content["quadrants"])
        for competency in quadrant["competencies"]
    ]

    # Pale guide petals retain the full extent of the 1–5 scale, even when
    # a person's individual preferences are lower. The actual scores are
    # represented only by the opaque foreground petals further below.
    for index, (quadrant_index, _competency) in enumerate(flattened[:8]):
        angle_start = -135 + index * 45
        parts.append(
            f'<path class="leadership-wheel__track" '
            f'd="{radial_sector(angle_start, angle_start + 45, radius)}" '
            f'fill="{quadrant_colors[quadrant_index]}" fill-opacity="0.045"/>'
        )

    for level in range(1, 6):
        ring_radius = radius * level / 5
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{fmt(ring_radius)}" '
            f'fill="none" stroke="#e5e4e3" stroke-width="1.15"/>'
        )
        # The top gap between the two first petals is clearer than the
        # previous diagonal, where the ring numbers overlapped competence text.
        label_x, label_y = point(ring_radius, -90)
        parts.append(
            f'<text class="leadership-wheel__ring-label" x="{fmt(label_x)}" '
            f'y="{fmt(label_y - 1)}" text-anchor="middle">{level}</text>'
        )

    # Four diagonal boundaries distinguish areas without heavy spokes
    # crossing the score petals.
    for boundary in range(4):
        angle = -135 + boundary * 90
        x, y = point(radius, angle)
        parts.append(
            f'<line x1="{cx}" y1="{cy}" x2="{fmt(x)}" y2="{fmt(y)}" '
            f'stroke="#aaa8a8" stroke-opacity="0.28" stroke-width="1.2"/>'
        )

    for index, (quadrant_index, _competency) in enumerate(flattened[:8]):
        result = scores_by_key.get(source_keys[index])
        if result is None:
            continue
        _score, rounded_score = result
        sector_radius = radius * rounded_score / 5
        parts.append(
            f'<path class="leadership-wheel__petal" '
            f'd="{petal_path(index, sector_radius)}" '
            f'fill="{quadrant_colors[quadrant_index]}" '
            f'stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/>'
        )

    # The center is a quiet hub, as in the Team report. It covers the sharp
    # starts of the petals, but never obscures score numbers.
    parts.append(
        f'<circle class="leadership-wheel__hub" cx="{cx}" cy="{cy}" '
        f'r="19" fill="#fff"/>'
    )

    for index, (_quadrant_index, _competency) in enumerate(flattened[:8]):
        result = scores_by_key.get(source_keys[index])
        if result is None:
            continue
        _score, rounded_score = result
        score_radius = radius * rounded_score / 5
        score_x, score_y = point(
            max(34, score_radius * 0.66), -112.5 + index * 45
        )
        parts.append(
            f'<text class="leadership-wheel__score" x="{fmt(score_x)}" '
            f'y="{fmt(score_y)}" text-anchor="middle" '
            f'dominant-baseline="central">{rounded_score}</text>'
        )

    for index, (_quadrant_index, competency) in enumerate(flattened[:8]):
        angle = -112.5 + index * 45
        label_x, label_y = point(radius + 39, angle)
        cosine = math.cos(math.radians(angle))
        anchor = "middle" if abs(cosine) < 0.26 else ("start" if cosine > 0 else "end")
        lines = _wrap_svg_label(competency["title"], limit=16)
        line_height = 14
        first_y = label_y - (len(lines) - 1) * line_height / 2
        parts.append(f'<text class="leadership-wheel__trait" text-anchor="{anchor}">')
        for line_index, line in enumerate(lines):
            parts.append(
                f'<tspan x="{fmt(label_x)}" y="{fmt(first_y + line_index * line_height)}">'
                f'{escape(line)}</tspan>'
            )
        parts.append("</text>")

    quadrant_positions = (
        (cx, 45, "middle"),
        (width - 14, cy, "end"),
        (cx, height - 44, "middle"),
        (14, cy, "start"),
    )
    for index, quadrant in enumerate(content["quadrants"][:4]):
        x, y, anchor = quadrant_positions[index]
        parts.append(
            f'<text class="leadership-wheel__quadrant" x="{x}" y="{y}" '
            f'text-anchor="{anchor}" dominant-baseline="central">'
            f'{escape(quadrant["title"])}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


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
            rounded_score = item.get("stive_rounded")
            try:
                rounded_score = int(round(float(rounded_score))) if rounded_score is not None else int(score + 0.5)
            except (TypeError, ValueError):
                rounded_score = int(score + 0.5)
            scores_by_key.setdefault(source_key, (score, max(1, min(5, rounded_score))))

    quadrants = []
    all_competencies = []
    slot_index = 0
    for quadrant in content["quadrants"]:
        rendered_quadrant = {**quadrant, "competencies": []}
        for competency in quadrant["competencies"]:
            source_key = source_keys[slot_index] if slot_index < len(source_keys) else None
            slot_index += 1
            score_result = scores_by_key.get(source_key) if source_key else None
            if score_result is None:
                continue
            score, rounded_score = score_result
            level_key = "low" if rounded_score == 1 else ("high" if rounded_score == 5 else "mid")
            level = next(
                item for item in competency["levels"]
                if item["key"] == level_key
            )
            rendered = {
                **competency,
                "score": score,
                "score_display": _display_score(float(rounded_score), language),
                "score_percent": rounded_score * 20,
                "score_rounded": rounded_score,
                "scale_segments": list(range(1, 6)),
                "definition_display": _clean_display_text(competency["definition"]),
                "interpretation_display": _clean_display_text(level["interpretation"]),
                "question_items": _split_reflection_questions(level["questions"]),
                "level": level,
                "interpretation": level["interpretation"],
                "questions": level["questions"],
            }
            rendered_quadrant["competencies"].append(rendered)
            all_competencies.append(rendered)

        quadrants.append(rendered_quadrant)

    return {
        **content,
        "quadrants": quadrants,
        "chart_svg": _build_leadership_chart_svg(content, scores_by_key, language),
        "has_results": bool(all_competencies),
        "scores_count": len(all_competencies),
        "total_competencies": 8,
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
        "guidance_title": "Praktisk vägledning" if language == "sv" else "Practical guidance",
        "interpretation_title": "Tolkning av resultatet" if language == "sv" else "Score interpretation",
        "reflection_title": "Frågor att reflektera över" if language == "sv" else "Questions to reflect on",
        "reflection_question_label": "Reflektionsfråga" if language == "sv" else "Reflection question",
        "least_preferred_label": "Minst föredragen" if language == "sv" else "Least preferred",
        "average_label": "Medel" if language == "sv" else "Average",
        "most_preferred_label": "Mest föredragen" if language == "sv" else "Most preferred",
    }
