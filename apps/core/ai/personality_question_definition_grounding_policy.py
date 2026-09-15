from __future__ import annotations

from functools import wraps
from typing import Any

from apps.reports.libraries.personality.content import (
    INDICATOR_PROFILE_CONTENT,
    TRAIT_PROFILE_CONTENT,
)
from apps.reports.libraries.personality.definitions import (
    TRAIT_AND_INDICATOR_PROFILE,
)


_INSTALLED = False


def _normalise_key(value: Any) -> str:
    text = str(value or "").strip().casefold()

    for character in ("_", "-", "–", "—", "/"):
        text = text.replace(character, " ")

    return " ".join(text.split())


def _localised(value: Any, language_code: str) -> str:
    if isinstance(value, dict):
        return str(
            value.get(language_code)
            or value.get("en")
            or value.get("sv")
            or ""
        ).strip()

    return str(value or "").strip()


def _score_band_key(sten: Any) -> str | None:
    try:
        score = int(round(float(sten)))
    except (TypeError, ValueError):
        return None

    score = max(1, min(10, score))

    if score <= 2:
        return "1_2"
    if score == 3:
        return "3"
    if score <= 7:
        return "4_7"
    if score == 8:
        return "8"
    return "9_10"


def _score_band_label(sten: Any) -> str:
    band_key = _score_band_key(sten)
    return {
        "1_2": "1–2",
        "3": "3",
        "4_7": "4–7",
        "8": "8",
        "9_10": "9–10",
    }.get(band_key or "", "unknown")


def _build_trait_indicator_map() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}

    for section in TRAIT_AND_INDICATOR_PROFILE.get("sections", []):
        for trait in section.get("traits", []):
            trait_name = str(
                trait.get("trait_name")
                or ""
            ).strip()

            if not trait_name:
                continue

            mapping[trait_name] = [
                str(indicator).strip()
                for indicator in trait.get("indicators", [])
                if str(indicator).strip()
            ]

    return mapping


_TRAIT_INDICATORS = _build_trait_indicator_map()
_TRAIT_CANONICAL_BY_KEY = {
    _normalise_key(name): name
    for name in TRAIT_PROFILE_CONTENT
}
_TRAIT_CANONICAL_BY_KEY["achievement striving"] = "Goal-focused"
_INDICATOR_CANONICAL_BY_KEY = {
    _normalise_key(name): name
    for name in INDICATOR_PROFILE_CONTENT
}


def _canonical_trait_name(value: Any) -> str | None:
    return _TRAIT_CANONICAL_BY_KEY.get(
        _normalise_key(value)
    )


def _result_lookup(
    results: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        _normalise_key(item.get("name")): item
        for item in results or []
        if _normalise_key(item.get("name"))
    }


def _raw_personality_results(owner) -> list[dict[str, Any]]:
    from apps.core.ai import personality_questions as pq

    try:
        return pq.extract_personality_results(owner)
    except (AttributeError, TypeError, ValueError):
        return []


def _direct_selected_trait_keys(owner) -> set[str]:
    selected = [
        str(item or "").strip()
        for item in getattr(
            owner,
            "selected_personality_traits",
            None,
        ) or []
        if str(item or "").strip()
    ]

    # Competency-based personality questions have their own evidence contract.
    # This policy only augments the 18 parent-trait mode from ticket #230.
    if any(
        item.casefold().startswith("competency::")
        for item in selected
    ):
        return set()

    keys: set[str] = set()

    for item in selected:
        canonical_name = _canonical_trait_name(item)
        if not canonical_name:
            continue

        # Keep both the supplied technical name and the canonical report name.
        # This covers Sova's Achievement Striving / Goal-focused alias.
        keys.add(_normalise_key(item))
        keys.add(_normalise_key(canonical_name))

    return keys


def _build_personality_definition_grounding(
    *,
    owner,
    personality_results: list[dict[str, Any]],
    language_code: str,
) -> str:
    """Build approved trait and indicator evidence for question generation."""

    language_code = (
        "sv"
        if str(language_code).casefold().startswith("sv")
        else "en"
    )

    raw_results = _raw_personality_results(owner)
    raw_lookup = _result_lookup(raw_results)
    selected_keys = _direct_selected_trait_keys(owner)

    raw_selection = [
        str(item or "").strip()
        for item in getattr(
            owner,
            "selected_personality_traits",
            None,
        ) or []
        if str(item or "").strip()
    ]

    # If competency mode is active, leave the competency policy as the only
    # source of personality evidence so the two selection modes never mix.
    if any(
        item.casefold().startswith("competency::")
        for item in raw_selection
    ):
        return ""

    trait_blocks = []

    for supplied_trait in personality_results or []:
        supplied_name = str(
            supplied_trait.get("name")
            or ""
        ).strip()
        canonical_name = _canonical_trait_name(
            supplied_name
        )

        if not canonical_name:
            continue

        supplied_key = _normalise_key(supplied_name)
        canonical_key = _normalise_key(canonical_name)

        if (
            selected_keys
            and supplied_key not in selected_keys
            and canonical_key not in selected_keys
        ):
            continue

        trait_content = (
            TRAIT_PROFILE_CONTENT.get(canonical_name)
            or {}
        )
        sten = supplied_trait.get("sten")

        if sten is None:
            raw_parent = (
                raw_lookup.get(supplied_key)
                or raw_lookup.get(canonical_key)
                or {}
            )
            sten = raw_parent.get("sten")

        display_label = str(
            trait_content.get(f"label_{language_code}")
            or trait_content.get("label_en")
            or canonical_name
        ).strip()
        low_pole = _localised(
            trait_content.get("low_pole"),
            language_code,
        )
        high_pole = _localised(
            trait_content.get("high_pole"),
            language_code,
        )

        block_lines = [
            f"TECHNICAL TRAIT NAME: {supplied_name}",
            f"APPROVED TRAIT: {canonical_name}",
            f"DISPLAY LABEL: {display_label}",
        ]

        if sten is not None:
            block_lines.append(
                f"CANDIDATE RESULT: STEN {sten} of 10"
            )

        if low_pole:
            block_lines.append(
                f"APPROVED LOW-POLE MEANING: {low_pole}"
            )

        if high_pole:
            block_lines.append(
                f"APPROVED HIGH-POLE MEANING: {high_pole}"
            )

        indicator_lines = []

        for indicator_name in _TRAIT_INDICATORS.get(
            canonical_name,
            [],
        ):
            indicator_canonical = (
                _INDICATOR_CANONICAL_BY_KEY.get(
                    _normalise_key(indicator_name)
                )
            )

            if not indicator_canonical:
                continue

            indicator_result = raw_lookup.get(
                _normalise_key(indicator_canonical)
            )

            if not indicator_result:
                continue

            indicator_sten = indicator_result.get("sten")
            band_key = _score_band_key(indicator_sten)

            if indicator_sten is None or not band_key:
                continue

            indicator_content = (
                INDICATOR_PROFILE_CONTENT.get(
                    indicator_canonical
                )
                or {}
            )
            score_texts = (
                indicator_content.get("score_texts")
                or {}
            )
            interpretation = _localised(
                score_texts.get(band_key),
                language_code,
            )
            indicator_label = str(
                indicator_content.get(
                    f"label_{language_code}"
                )
                or indicator_content.get("label_en")
                or indicator_canonical
            ).strip()

            if not interpretation:
                continue

            indicator_lines.extend(
                [
                    (
                        f"- {indicator_canonical} / {indicator_label}: "
                        f"STEN {indicator_sten} of 10"
                    ),
                    (
                        "  APPROVED SCORE-BAND INTERPRETATION "
                        f"({_score_band_label(indicator_sten)}): "
                        f"{interpretation}"
                    ),
                ]
            )

        block_lines.append(
            "UNDERLYING INDICATOR EVIDENCE:"
        )

        if indicator_lines:
            block_lines.extend(indicator_lines)
        else:
            block_lines.append(
                "- No indicator-level scores are available for this trait. "
                "Do not invent them."
            )

        trait_blocks.append(
            "\n".join(block_lines)
        )

    if not trait_blocks:
        return ""

    return """

TALENA APPROVED PERSONALITY MEANING AND INDICATOR EVIDENCE

The following definitions are Talena's approved interpretation framework.
Use them as the authoritative meaning of the supplied personality scales.
Do not replace them with a generic or outside definition of a similarly named
trait or indicator.

Indicator results are supporting evidence beneath a parent trait. They are
NOT additional user-selected traits, must not appear as new technical trait
names in selected_traits/traits arrays, and must not be treated as separate
competencies.

Do not copy these definitions mechanically into the interview question. Use
them to understand the candidate's score direction and to form a more precise,
neutral hypothesis that the interview can explore.

""" + "\n\n".join(trait_blocks) + """

PERSONALITY QUESTION QUALITY REQUIREMENTS

- Let the candidate's actual parent-trait direction and, where available, the
  underlying indicator pattern materially shape the angle of each question.
- When indicators within one parent trait point to different nuances, use that
  pattern when it creates a useful hypothesis instead of reducing the person to
  the broad parent-trait label.
- Do not force every question to mention an indicator. Indicator evidence should
  improve the question, not make the wording psychometric or technical.
- Never reveal raw STEN values in the candidate-facing question.
- Keep questions exploratory and non-judgemental. Neither pole is inherently
  better, and an assessment result is an indication to validate rather than
  proof of fixed behaviour, competence, performance or role fit.
- With multiple selected parent traits, distribute the question set across
  different traits. Normally cover each selected trait before reusing a trait.
- Prefer one clear primary parent trait per question. Combine traits only when
  their interaction creates a genuinely useful hypothesis or trade-off to
  explore.
- Avoid near-duplicate wording, repeated hypotheses and several questions that
  test essentially the same behaviour.
- If only one parent trait is selected, create distinct questions by exploring
  different situations, trade-offs or relevant indicator-level nuances rather
  than repeating the same broad trait hypothesis.
""".rstrip()


def install_personality_question_definition_grounding_policy() -> None:
    """Ground personality questions in approved trait and indicator meanings."""

    global _INSTALLED

    if _INSTALLED:
        return

    from apps.core.ai import personality_questions as pq

    original_prompt = (
        pq.build_personality_questions_prompt
    )
    original_repair_prompt = (
        pq._build_personality_questions_repair_prompt
    )

    @wraps(original_prompt)
    def build_personality_questions_prompt(
        invitation,
        personality_results,
        *,
        language_code=None,
    ):
        resolved_language = pq.normalize_ai_language(
            language_code
            or pq._personality_questions_language.get()
        )
        prompt = original_prompt(
            invitation,
            personality_results,
            language_code=resolved_language,
        )
        grounding = _build_personality_definition_grounding(
            owner=invitation,
            personality_results=personality_results,
            language_code=resolved_language,
        )

        if not grounding:
            return prompt

        return f"{str(prompt).rstrip()}\n{grounding}"

    @wraps(original_repair_prompt)
    def build_personality_questions_repair_prompt(
        *,
        owner,
        personality_results,
        selected_traits,
    ):
        prompt = original_repair_prompt(
            owner=owner,
            personality_results=personality_results,
            selected_traits=selected_traits,
        )
        resolved_language = pq.normalize_ai_language(
            pq._personality_questions_language.get()
        )
        grounding = _build_personality_definition_grounding(
            owner=owner,
            personality_results=personality_results,
            language_code=resolved_language,
        )

        if not grounding:
            return prompt

        return f"{str(prompt).rstrip()}\n{grounding}"

    pq.build_personality_questions_prompt = (
        build_personality_questions_prompt
    )
    pq._build_personality_questions_repair_prompt = (
        build_personality_questions_repair_prompt
    )

    _INSTALLED = True
