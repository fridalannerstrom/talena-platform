from __future__ import annotations

from functools import wraps
from typing import Any, Iterable


_INSTALLED = False


PROFILE_DYNAMICS_CONTRACT = """
3. PROFILE DYNAMICS

Return exactly one profile_dynamics event with an items array containing
exactly 2 separate, substantive personality dynamics:

{"type":"profile_dynamics","items":["First standalone dynamic","Second standalone dynamic"]}

This is a protected Talena product structure for Combined trait dynamics:

- items must be an array
- return exactly 2 non-empty items
- each item must contain one complete, standalone dynamic
- keep the two dynamics separate; never merge both into one item
- do not add numbering, bullets, Markdown headings or labels inside the items
- the administrator guidance controls the wording, sentence count, evidence,
  selection logic and tone inside each item
- the technical structure does not change the administrator's substantive
  instructions

The two items are displayed as two separate paragraphs in Talena.
""".strip()


def _replace_profile_dynamics_contract(prompt: str) -> str:
    """Replace the legacy single-text dynamics contract with two items."""

    text = str(prompt or "")
    start_marker = "3. PROFILE DYNAMICS\n"
    end_marker = "\n\n4. MOTIVATION INTERACTION"

    start = text.find(start_marker)
    if start < 0:
        return text

    end = text.find(end_marker, start)
    if end < 0:
        return text

    return (
        text[:start]
        + PROFILE_DYNAMICS_CONTRACT
        + text[end:]
    )


def _clean_dynamics_items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    items: list[str] = []

    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        items.append(text)
        if len(items) == 2:
            break

    return items


def _split_legacy_dynamics_text(value: Any) -> list[str]:
    """Recover two paragraphs when a model still returns legacy text."""

    text = str(value or "").strip()
    if not text:
        return []

    paragraphs = [
        paragraph.strip()
        for paragraph in text.replace("\r\n", "\n").replace("\r", "\n").split("\n\n")
        if paragraph.strip()
    ]

    if len(paragraphs) >= 2:
        return paragraphs[:2]

    return []


def normalise_profile_dynamics_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    Keep the AI contract structured while preserving Talena's saved string field.

    Existing consumers expect profile_dynamics to be a string. New model output
    uses an items array, which is joined with a blank line so current storage,
    Decision Support and the live UI stay backwards compatible.
    """

    if not isinstance(event, dict) or event.get("type") != "profile_dynamics":
        return event

    items = _clean_dynamics_items(event.get("items"))

    if not items:
        items = _split_legacy_dynamics_text(event.get("text"))

    if items:
        text = "\n\n".join(items)
        return {
            **event,
            "items": items,
            "text": text,
        }

    # Backwards compatibility for old/single-text model responses.
    return {
        **event,
        "text": str(event.get("text") or "").strip(),
    }


def install_personality_dynamics_structure_policy() -> None:
    """Require two separately structured Combined trait dynamics."""

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import personality_interpretation as personality

    original_build_prompt = personality.build_personality_interpretation_prompt
    original_apply_event = personality.apply_personality_interpretation_event
    original_stream = personality.stream_personality_interpretation

    @wraps(original_build_prompt)
    def build_personality_interpretation_prompt(*args, **kwargs):
        prompt = original_build_prompt(*args, **kwargs)
        return _replace_profile_dynamics_contract(prompt)

    @wraps(original_apply_event)
    def apply_personality_interpretation_event(
        interpretation: dict[str, Any],
        event: dict[str, Any],
    ) -> dict[str, Any]:
        return original_apply_event(
            interpretation,
            normalise_profile_dynamics_event(event),
        )

    @wraps(original_stream)
    def stream_personality_interpretation(*args, **kwargs) -> Iterable[dict[str, Any]]:
        for event in original_stream(*args, **kwargs):
            yield normalise_profile_dynamics_event(event)

    personality.build_personality_interpretation_prompt = (
        build_personality_interpretation_prompt
    )
    personality.apply_personality_interpretation_event = (
        apply_personality_interpretation_event
    )
    personality.stream_personality_interpretation = (
        stream_personality_interpretation
    )

    _INSTALLED = True
