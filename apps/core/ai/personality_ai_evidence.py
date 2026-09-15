from __future__ import annotations

from typing import Any, Iterable

from apps.reports.libraries.personality.content import TRAIT_PROFILE_CONTENT

from .language import normalize_ai_language


# Technical aliases that may occur in imported/Sova data. The report library
# remains the source of truth for the actual trait definitions.
_TRAIT_CANONICAL_BY_KEY: dict[str, str] = {}


def normalise_personality_trait_key(value: Any) -> str:
    text = str(value or "").strip().casefold()

    for character in ("_", "-", "–", "—", "/"):
        text = text.replace(character, " ")

    return " ".join(text.split())


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


def canonical_parent_trait_name(value: Any) -> str | None:
    """Return the approved parent-trait name, or None for non-parent rows."""

    return _TRAIT_CANONICAL_BY_KEY.get(
        normalise_personality_trait_key(value)
    )


def _localised(value: Any, language_code: str) -> str:
    if isinstance(value, dict):
        return str(
            value.get(language_code)
            or value.get("en")
            or value.get("sv")
            or ""
        ).strip()

    return str(value or "").strip()


def _normalise_sten(value: Any) -> int | float | None:
    if value is None:
        return None

    try:
        score = float(value)
    except (TypeError, ValueError):
        return None

    if score < 1 or score > 10:
        return None

    return int(score) if score.is_integer() else score


def _row_name(item: dict[str, Any]) -> str:
    return str(
        item.get("competency")
        or item.get("name")
        or item.get("label")
        or ""
    ).strip()


def _row_sten(item: dict[str, Any]) -> int | float | None:
    for field_name in ("sten_rounded", "sten", "score"):
        score = _normalise_sten(item.get(field_name))
        if score is not None:
            return score

    return None


def build_personality_ai_evidence(
    items: Iterable[dict[str, Any]] | None,
    *,
    language_code: str = "en",
    include_traits: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Normalize parent personality scores into Talena's shared AI evidence shape.

    The approved low/high-pole wording always comes directly from
    TRAIT_PROFILE_CONTENT. Unknown competencies, indicators and response-style
    rows are intentionally ignored rather than assigned invented definitions.
    """

    language_code = normalize_ai_language(language_code)

    included_canonical_names: set[str] | None = None
    if include_traits is not None:
        included_canonical_names = {
            canonical
            for value in include_traits
            if (canonical := canonical_parent_trait_name(value))
        }

    evidence_by_trait: dict[str, dict[str, Any]] = {}

    for item in items or []:
        if not isinstance(item, dict):
            continue

        source_name = _row_name(item)
        canonical_name = canonical_parent_trait_name(source_name)

        if not canonical_name:
            continue

        if (
            included_canonical_names is not None
            and canonical_name not in included_canonical_names
        ):
            continue

        sten = _row_sten(item)
        if sten is None:
            continue

        content = TRAIT_PROFILE_CONTENT.get(canonical_name) or {}
        label = str(
            content.get(f"label_{language_code}")
            or content.get("label_en")
            or canonical_name
        ).strip()

        evidence_by_trait[canonical_name] = {
            "name": canonical_name,
            "source_name": source_name or canonical_name,
            "label": label,
            "sten": sten,
            "low_pole": _localised(
                content.get("low_pole"),
                language_code,
            ),
            "high_pole": _localised(
                content.get("high_pole"),
                language_code,
            ),
        }

    # Keep report-library order stable across all downstream prompts.
    return [
        evidence_by_trait[name]
        for name in TRAIT_PROFILE_CONTENT
        if name in evidence_by_trait
    ]


def extract_owner_parent_personality_results(owner) -> list[dict[str, Any]]:
    """Return raw parent-trait score rows for active or historical candidates."""

    process = getattr(owner, "process", None)

    if getattr(process, "is_historical", False):
        # Lazy import keeps core AI startup independent of the processes service
        # import graph.
        from apps.processes.services.candidate_profile import (
            build_historical_candidate_profile,
        )

        profile = build_historical_candidate_profile(owner)
        return list(profile.get("personality_competencies") or [])

    # Reuse the established active-candidate Sova extraction. This returns all
    # scored personality rows; build_personality_ai_evidence then keeps only the
    # 18 approved parent traits.
    try:
        from .personality_questions import extract_personality_results

        return list(extract_personality_results(owner) or [])
    except (AttributeError, TypeError, ValueError):
        return []


def build_owner_personality_ai_evidence(
    owner,
    *,
    language_code: str = "en",
    include_traits: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    return build_personality_ai_evidence(
        extract_owner_parent_personality_results(owner),
        language_code=language_code,
        include_traits=include_traits,
    )


def render_personality_ai_evidence(
    evidence: Iterable[dict[str, Any]] | None,
    *,
    language_code: str = "en",
) -> str:
    """Render shared structured evidence for inclusion in AI prompts."""

    language_code = normalize_ai_language(language_code)
    rows = list(evidence or [])

    if not rows:
        return ""

    if language_code == "sv":
        intro = (
            "Definitionerna nedan är Talenas godkända betydelser av skalans "
            "riktningar. Använd kandidatens STEN-resultat i relation till dessa "
            "poler. Definitionerna är inte bevis för att ett beteende alltid "
            "förekommer, och ingen pol är i sig bättre än den andra."
        )
        low_label = "GODKÄND LÅG-POL"
        high_label = "GODKÄND HÖG-POL"
    else:
        intro = (
            "The definitions below are Talena's approved meanings for the scale "
            "directions. Interpret the candidate's STEN result in relation to "
            "these poles. The definitions are not proof that a behaviour always "
            "occurs, and neither pole is inherently better than the other."
        )
        low_label = "APPROVED LOW POLE"
        high_label = "APPROVED HIGH POLE"

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
            f"{low_label}: {row.get('low_pole') or ''}",
            f"{high_label}: {row.get('high_pole') or ''}",
        ]

        blocks.append("\n".join(lines))

    return (
        "TALENA APPROVED PERSONALITY DEFINITION EVIDENCE\n\n"
        + intro
        + "\n\n"
        + "\n\n".join(blocks)
    )


def build_personality_ai_evidence_text(
    items: Iterable[dict[str, Any]] | None,
    *,
    language_code: str = "en",
    include_traits: Iterable[str] | None = None,
) -> str:
    return render_personality_ai_evidence(
        build_personality_ai_evidence(
            items,
            language_code=language_code,
            include_traits=include_traits,
        ),
        language_code=language_code,
    )


def build_owner_personality_ai_evidence_text(
    owner,
    *,
    language_code: str = "en",
    include_traits: Iterable[str] | None = None,
) -> str:
    return render_personality_ai_evidence(
        build_owner_personality_ai_evidence(
            owner,
            language_code=language_code,
            include_traits=include_traits,
        ),
        language_code=language_code,
    )
