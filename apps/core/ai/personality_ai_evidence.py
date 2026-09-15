from __future__ import annotations

from typing import Any, Iterable

from apps.reports.libraries.personality.builder import (
    build_trait_summary,
    get_localized_text,
    get_score_band,
    normalize_sten,
)
from apps.reports.libraries.personality.content import (
    INDICATOR_PROFILE_CONTENT,
    TRAIT_PROFILE_CONTENT,
)
from apps.reports.libraries.personality.definitions import (
    TRAIT_AND_INDICATOR_PROFILE,
)

from .language import normalize_ai_language


# ---------------------------------------------------------------------------
# Canonical names
# ---------------------------------------------------------------------------


def normalise_personality_trait_key(value: Any) -> str:
    text = str(value or "").strip().casefold()

    for character in ("_", "-", "–", "—", "/"):
        text = text.replace(character, " ")

    return " ".join(text.split())


_TRAIT_CANONICAL_BY_KEY: dict[str, str] = {}
_INDICATOR_CANONICAL_BY_KEY: dict[str, str] = {}

for _canonical_name, _content in TRAIT_PROFILE_CONTENT.items():
    _TRAIT_CANONICAL_BY_KEY[
        normalise_personality_trait_key(_canonical_name)
    ] = _canonical_name

    for _label_key in ("label_sv", "label_en"):
        _label = str(_content.get(_label_key) or "").strip()
        if _label:
            _TRAIT_CANONICAL_BY_KEY[
                normalise_personality_trait_key(_label)
            ] = _canonical_name

# Sova/report wording has historically used both names for this trait.
_TRAIT_CANONICAL_BY_KEY["achievement striving"] = "Goal-focused"

for _canonical_name, _content in INDICATOR_PROFILE_CONTENT.items():
    _INDICATOR_CANONICAL_BY_KEY[
        normalise_personality_trait_key(_canonical_name)
    ] = _canonical_name

    for _label_key in ("label_sv", "label_en"):
        _label = str(_content.get(_label_key) or "").strip()
        if _label:
            _INDICATOR_CANONICAL_BY_KEY[
                normalise_personality_trait_key(_label)
            ] = _canonical_name


def canonical_parent_trait_name(value: Any) -> str | None:
    """Return the approved parent-trait name, or None for non-parent rows."""

    return _TRAIT_CANONICAL_BY_KEY.get(
        normalise_personality_trait_key(value)
    )


def canonical_indicator_name(value: Any) -> str | None:
    return _INDICATOR_CANONICAL_BY_KEY.get(
        normalise_personality_trait_key(value)
    )


# ---------------------------------------------------------------------------
# Trait -> indicator hierarchy
# ---------------------------------------------------------------------------


def _build_trait_indicator_map() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}

    for section in TRAIT_AND_INDICATOR_PROFILE.get("sections", []):
        for trait in section.get("traits", []):
            trait_name = str(trait.get("trait_name") or "").strip()
            canonical_trait = canonical_parent_trait_name(trait_name)

            if not canonical_trait:
                continue

            mapping[canonical_trait] = [
                canonical_indicator
                for raw_indicator in trait.get("indicators", [])
                if (
                    canonical_indicator := canonical_indicator_name(
                        raw_indicator
                    )
                )
            ]

    return mapping


_TRAIT_INDICATORS = _build_trait_indicator_map()


# ---------------------------------------------------------------------------
# Raw row normalisation
# ---------------------------------------------------------------------------


def _row_name(item: dict[str, Any]) -> str:
    return str(
        item.get("competency")
        or item.get("name")
        or item.get("label")
        or ""
    ).strip()


def _row_sten(item: dict[str, Any]) -> int | None:
    for field_name in ("sten_rounded", "sten", "score"):
        score = normalize_sten(item.get(field_name))
        if score is not None:
            return score

    return None


def _localised_label(
    content: dict[str, Any],
    canonical_name: str,
    language_code: str,
) -> str:
    return str(
        content.get(f"label_{language_code}")
        or content.get("label_en")
        or content.get("label_sv")
        or canonical_name
    ).strip()


def _included_traits(
    include_traits: Iterable[str] | None,
) -> set[str] | None:
    if include_traits is None:
        return None

    return {
        canonical
        for value in include_traits
        if (canonical := canonical_parent_trait_name(value))
    }


# ---------------------------------------------------------------------------
# Shared candidate-specific evidence
# ---------------------------------------------------------------------------


def build_personality_ai_evidence(
    items: Iterable[dict[str, Any]] | None,
    *,
    language_code: str = "en",
    include_traits: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Build Talena's shared candidate-specific personality evidence.

    This intentionally mirrors the logic behind the Result Summary UI:
    each indicator contributes the exact approved text for the candidate's
    rounded STEN band, and the parent-trait summary is the joined indicator
    interpretation text.

    Low/high-pole definitions are not used as the primary AI evidence here.
    The candidate's actual result description is more informative and less
    likely to flatten a nuanced profile into generic scale-direction language.
    """

    language_code = normalize_ai_language(language_code)
    included_canonical_names = _included_traits(include_traits)

    parent_rows: dict[str, dict[str, Any]] = {}
    indicator_rows: dict[str, dict[str, Any]] = {}

    for item in items or []:
        if not isinstance(item, dict):
            continue

        source_name = _row_name(item)
        if not source_name:
            continue

        parent_name = canonical_parent_trait_name(source_name)
        if parent_name:
            parent_rows[parent_name] = item
            continue

        indicator_name = canonical_indicator_name(source_name)
        if indicator_name:
            indicator_rows[indicator_name] = item

    evidence = []

    for canonical_name, trait_content in TRAIT_PROFILE_CONTENT.items():
        if (
            included_canonical_names is not None
            and canonical_name not in included_canonical_names
        ):
            continue

        parent_row = parent_rows.get(canonical_name)
        if not parent_row:
            continue

        sten = _row_sten(parent_row)
        if sten is None:
            continue

        indicators = []

        for indicator_name in _TRAIT_INDICATORS.get(canonical_name, []):
            indicator_row = indicator_rows.get(indicator_name)
            if not indicator_row:
                continue

            indicator_sten = _row_sten(indicator_row)
            if indicator_sten is None:
                continue

            indicator_content = (
                INDICATOR_PROFILE_CONTENT.get(indicator_name)
                or {}
            )
            score_band = get_score_band(indicator_sten)
            score_text = get_localized_text(
                (indicator_content.get("score_texts") or {}).get(
                    score_band
                ),
                language_code,
            ).strip()

            if not score_text:
                continue

            indicators.append(
                {
                    "name": indicator_name,
                    "label": _localised_label(
                        indicator_content,
                        indicator_name,
                        language_code,
                    ),
                    "sten": indicator_sten,
                    "score_band": score_band,
                    "text": score_text,
                }
            )

        evidence.append(
            {
                "name": canonical_name,
                "source_name": _row_name(parent_row) or canonical_name,
                "label": _localised_label(
                    trait_content,
                    canonical_name,
                    language_code,
                ),
                "sten": sten,
                "summary": build_trait_summary(indicators),
                "indicators": indicators,
            }
        )

    return evidence


def extract_owner_personality_results(owner) -> list[dict[str, Any]]:
    """Return raw personality rows for active or historical candidates."""

    process = getattr(owner, "process", None)

    if getattr(process, "is_historical", False):
        from apps.processes.services.candidate_profile import (
            build_historical_candidate_profile,
        )

        profile = build_historical_candidate_profile(owner)
        return list(profile.get("personality_competencies") or [])

    try:
        from .personality_questions import extract_personality_results

        return list(extract_personality_results(owner) or [])
    except (AttributeError, TypeError, ValueError):
        return []


# Backwards-compatible name used by the first #231 implementation/tests.
def extract_owner_parent_personality_results(owner) -> list[dict[str, Any]]:
    return extract_owner_personality_results(owner)


def build_owner_personality_ai_evidence(
    owner,
    *,
    language_code: str = "en",
    include_traits: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    return build_personality_ai_evidence(
        extract_owner_personality_results(owner),
        language_code=language_code,
        include_traits=include_traits,
    )


def render_personality_ai_evidence(
    evidence: Iterable[dict[str, Any]] | None,
    *,
    language_code: str = "en",
    include_indicator_details: bool = False,
) -> str:
    """Render the same candidate-specific meaning used by Result Summary."""

    language_code = normalize_ai_language(language_code)
    rows = list(evidence or [])

    if not rows:
        return ""

    if language_code == "sv":
        intro = (
            "Detta är kandidatens resultatspecifika personlighetsevidens. "
            "Sammanfattningarna byggs av samma godkända indikatortexter och "
            "STEN-band som används i Talenas Resultatsammanfattning. Använd "
            "därför kandidatens faktiska sammanfattning som primär betydelse, "
            "inte en generell vänster/höger-definition av skalan. Om STEN 4–7 "
            "beskrivs som nivå ska termen situationsbaserat användas, men reducera "
            "inte hela resultatet till ordet situationsbaserat när den konkreta "
            "sammanfattningen innehåller mer nyans. Personlighetsevidens är "
            "hypoteser att utforska, inte bevis på fast beteende, kompetens, "
            "prestation eller rollpassning. Processkontext får styra relevansen "
            "och situationen som utforskas, men inte skriva om själva resultatet."
        )
        summary_label = "KANDIDATENS RESULTATSAMMANFATTNING"
        indicator_label = "UNDERLIGGANDE INDIKATORNYANSER"
        no_summary = "Ingen resultatsammanfattning kunde byggas från indikatorerna."
    else:
        intro = (
            "This is candidate-specific personality evidence. The summaries are "
            "built from the same approved indicator texts and STEN bands used in "
            "Talena's Result Summary. Use the candidate's actual result summary as "
            "the primary meaning rather than a generic left/right scale definition. "
            "If STEN 4–7 is described as a level, use the term situational, but do "
            "not reduce the full result to the word situational when the concrete "
            "summary contains more nuance. Personality evidence is a hypothesis to "
            "explore, not proof of fixed behaviour, competence, performance or role "
            "fit. Process context may shape relevance and the situation explored, "
            "but it must not rewrite the assessment result itself."
        )
        summary_label = "CANDIDATE-SPECIFIC RESULT SUMMARY"
        indicator_label = "UNDERLYING INDICATOR NUANCE"
        no_summary = "No result summary could be built from the indicators."

    blocks = []

    for row in rows:
        canonical_name = str(row.get("name") or "").strip()
        label = str(row.get("label") or canonical_name).strip()
        source_name = str(row.get("source_name") or canonical_name).strip()
        sten = row.get("sten")

        heading = canonical_name
        if label and label != canonical_name:
            heading = f"{canonical_name} / {label}"

        lines = [
            f"TRAIT: {heading}",
            f"SOURCE NAME: {source_name}",
            f"CANDIDATE RESULT: STEN {sten} of 10",
            f"{summary_label}: {row.get('summary') or no_summary}",
        ]

        if include_indicator_details and row.get("indicators"):
            lines.append(f"{indicator_label}:")

            for indicator in row["indicators"]:
                indicator_name = str(indicator.get("name") or "").strip()
                indicator_display = str(
                    indicator.get("label") or indicator_name
                ).strip()
                indicator_heading = indicator_name

                if (
                    indicator_display
                    and indicator_display != indicator_name
                ):
                    indicator_heading = (
                        f"{indicator_name} / {indicator_display}"
                    )

                lines.append(
                    f"- {indicator_heading}: STEN {indicator.get('sten')} of 10. "
                    f"{indicator.get('text') or ''}"
                )

        blocks.append("\n".join(lines))

    return (
        "TALENA CANDIDATE-SPECIFIC PERSONALITY RESULT EVIDENCE\n\n"
        + intro
        + "\n\n"
        + "\n\n".join(blocks)
    )


def build_personality_ai_evidence_text(
    items: Iterable[dict[str, Any]] | None,
    *,
    language_code: str = "en",
    include_traits: Iterable[str] | None = None,
    include_indicator_details: bool = False,
) -> str:
    return render_personality_ai_evidence(
        build_personality_ai_evidence(
            items,
            language_code=language_code,
            include_traits=include_traits,
        ),
        language_code=language_code,
        include_indicator_details=include_indicator_details,
    )


def build_owner_personality_ai_evidence_text(
    owner,
    *,
    language_code: str = "en",
    include_traits: Iterable[str] | None = None,
    include_indicator_details: bool = False,
) -> str:
    return render_personality_ai_evidence(
        build_owner_personality_ai_evidence(
            owner,
            language_code=language_code,
            include_traits=include_traits,
        ),
        language_code=language_code,
        include_indicator_details=include_indicator_details,
    )
