from apps.reports.libraries.personality.content import (
    INDICATOR_PROFILE_CONTENT,
    TRAIT_PROFILE_CONTENT,
)
from apps.reports.libraries.personality.resolver import (
    build_personality_reports_for_candidate,
)


DEFAULT_GRAPH_HEIGHTS = [
    18,
    32,
    50,
    70,
    88,
    88,
    70,
    50,
    32,
    18,
]


def normalize_sten(value):
    """
    Convert a STEN value into an integer between 1 and 10.

    Returns None when the value cannot be interpreted.
    """
    if value is None or value == "":
        return None

    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return None

    return max(1, min(10, score))


def get_score_band(sten):
    """
    Match a rounded STEN score against the content-library bands:

    1–2
    3
    4–7
    8
    9–10
    """
    sten = normalize_sten(sten)

    if sten is None:
        return None

    if sten <= 2:
        return "1_2"

    if sten == 3:
        return "3"

    if sten <= 7:
        return "4_7"

    if sten == 8:
        return "8"

    return "9_10"


def get_localized_text(value, language="sv"):
    """
    Read a localized value from dictionaries such as:

    {
        "sv": "...",
        "en": "...",
    }

    Falls back to English and then Swedish.
    """
    if not value:
        return ""

    if isinstance(value, str):
        return value

    if not isinstance(value, dict):
        return str(value)

    return (
        value.get(language)
        or value.get("en")
        or value.get("sv")
        or ""
    )


def get_trait_label(trait_name, trait_content, language="sv"):
    """
    Resolve the label for a trait.

    Supports the current label_sv structure while allowing
    label_en or a future localized label dictionary.
    """
    localized_label = trait_content.get("label")

    if localized_label:
        return get_localized_text(localized_label, language)

    if language == "sv":
        return trait_content.get("label_sv") or trait_name

    if language == "en":
        return trait_content.get("label_en") or trait_name

    return trait_name


def get_indicator_label(indicator_name, indicator_content, language="sv"):
    """
    Resolve the label for an indicator.
    """
    localized_label = indicator_content.get("label")

    if localized_label:
        return get_localized_text(localized_label, language)

    if language == "sv":
        return indicator_content.get("label_sv") or indicator_name

    if language == "en":
        return indicator_content.get("label_en") or indicator_name

    return indicator_name


def build_graph_segments(selected_sten):
    """
    Build the ten visual segments used by the arched STEN graph.

    The heights are purely visual. They do not represent another
    assessment calculation.
    """
    selected_sten = normalize_sten(selected_sten)

    return [
        {
            "score": score,
            "height": height,
            "selected": score == selected_sten,
        }
        for score, height in enumerate(
            DEFAULT_GRAPH_HEIGHTS,
            start=1,
        )
    ]


def build_indicator_profile(row, language="sv"):
    """
    Combine one resolved indicator row with its interpretation content.
    """
    indicator_name = row.get("expected_name", "")
    indicator_content = INDICATOR_PROFILE_CONTENT.get(
        indicator_name,
        {},
    )

    sten = normalize_sten(row.get("sten"))
    score_band = get_score_band(sten)

    score_texts = indicator_content.get("score_texts", {})
    localized_score_text = score_texts.get(score_band, {})

    return {
            "name": indicator_name,
            "label": get_indicator_label(
                indicator_name=indicator_name,
                indicator_content=indicator_content,
                language=language,
            ),
            "low_pole": get_localized_text(
                indicator_content.get("low_pole"),
                language,
            ),
            "high_pole": get_localized_text(
                indicator_content.get("high_pole"),
                language,
            ),
            "canonical_key": row.get("canonical_key", ""),
            "sten": sten,
            "percentile": row.get("percentile"),
            "score_band": score_band,
            "text": get_localized_text(
                localized_score_text,
                language,
            ),
            "mapping_status": row.get("mapping_status", "missing"),
            "library_status": row.get("library_status", "not_started"),
            "has_result": sten is not None,
            "has_content": bool(indicator_content),
        }


def build_trait_summary(indicators):
    """
    Join the selected interpretation sentence from each indicator.

    Each indicator contributes one sentence based on its rounded STEN band.
    """
    sentences = []

    for indicator in indicators:
        text = (indicator.get("text") or "").strip()

        if not text:
            continue

        if text[-1] not in ".!?":
            text += "."

        sentences.append(text)

    return " ".join(sentences)


def build_trait_profile(trait_row, indicator_rows, language="sv"):
    """
    Combine one resolved trait and its resolved indicators into
    template-ready profile data.
    """
    trait_name = trait_row.get("expected_name", "")
    trait_content = TRAIT_PROFILE_CONTENT.get(
        trait_name,
        {},
    )

    sten = normalize_sten(trait_row.get("sten"))

    indicators = [
        build_indicator_profile(
            row=indicator_row,
            language=language,
        )
        for indicator_row in indicator_rows
    ]

    return {
        "name": trait_name,
        "label": get_trait_label(
            trait_name=trait_name,
            trait_content=trait_content,
            language=language,
        ),
        "canonical_key": trait_row.get("canonical_key", ""),
        "sten": sten,
        "percentile": trait_row.get("percentile"),
        "low_pole": get_localized_text(
            trait_content.get("low_pole"),
            language,
        ),
        "high_pole": get_localized_text(
            trait_content.get("high_pole"),
            language,
        ),
        "summary": build_trait_summary(indicators),
        "indicators": indicators,
        "graph_segments": build_graph_segments(sten),
        "mapping_status": trait_row.get(
            "mapping_status",
            "missing",
        ),
        "library_status": trait_row.get(
            "library_status",
            "not_started",
        ),
        "has_result": sten is not None,
        "has_content": bool(trait_content),
    }


def build_profile_section(section, language="sv"):
    """
    Reconstruct the trait hierarchy from the flattened rows returned
    by resolver.build_report_table().
    """
    rows = section.get("rows", [])
    traits = []

    for row in rows:
        if row.get("row_type") != "trait":
            continue

        trait_name = row.get("expected_name", "")

        indicator_rows = [
            candidate_row
            for candidate_row in rows
            if (
                candidate_row.get("row_type") == "indicator"
                and candidate_row.get("parent_trait") == trait_name
            )
        ]

        traits.append(
            build_trait_profile(
                trait_row=row,
                indicator_rows=indicator_rows,
                language=language,
            )
        )

    return {
        "section_name": section.get("section_name", ""),
        "traits": traits,
    }


def build_profile_from_resolved_report(
    resolved_report,
    language="sv",
    include_missing_traits=False,
):
    """
    Convert one resolver report into the final personality-profile
    structure used by the template.
    """
    sections = []

    for section in resolved_report.get("sections", []):
        profile_section = build_profile_section(
            section=section,
            language=language,
        )

        if not include_missing_traits:
            profile_section["traits"] = [
                trait
                for trait in profile_section["traits"]
                if trait.get("has_result")
            ]

        if profile_section["traits"]:
            sections.append(profile_section)

    return {
        "report_id": resolved_report.get("report_id"),
        "report_name": resolved_report.get("report_name", ""),
        "description": resolved_report.get("description", ""),
        "summary": resolved_report.get("summary", {}),
        "sections": sections,
    }


def build_personality_profile_for_candidate(
    sova_activities,
    report_id=None,
    language="sv",
    library_status_lookup=None,
    include_missing_traits=False,
):
    """
    Main entry point.

    1. Resolve the Sova competencies using resolver.py.
    2. Choose the requested personality report.
    3. Add labels, pole descriptions, indicator interpretations
       and graph segments.
    """
    resolved_reports = build_personality_reports_for_candidate(
        sova_activities=sova_activities,
        library_status_lookup=library_status_lookup,
    )

    if not resolved_reports:
        return None

    selected_report = None

    if report_id:
        selected_report = next(
            (
                report
                for report in resolved_reports
                if report.get("report_id") == report_id
            ),
            None,
        )
    else:
        selected_report = resolved_reports[0]

    if not selected_report:
        return None

    return build_profile_from_resolved_report(
        resolved_report=selected_report,
        language=language,
        include_missing_traits=include_missing_traits,
    )