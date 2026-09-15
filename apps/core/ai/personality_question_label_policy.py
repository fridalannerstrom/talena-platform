from __future__ import annotations

from functools import wraps
from typing import Any


_INSTALLED = False
MAX_PERSONALITY_TRAITS = 8


def _normalise_key(value: Any) -> str:
    text = str(value or "").strip().casefold()
    for character in ("_", "-", "–", "—", "/"):
        text = text.replace(character, " ")
    return " ".join(text.split())


def _question_label_contract() -> str:
    return f"""

TALENA PERSONALITY QUESTION LABEL CONTRACT

This is a protected product requirement.

- The application supports up to {MAX_PERSONALITY_TRAITS} selected personality traits.
- Every generated personality question must contain at least one valid item in
  its traits array.
- Every value in traits must exactly match one of the selected_traits values.
- The traits array must identify the personality trait or competency the actual
  question is primarily exploring. Never leave traits empty for a substantive
  question.
- If fewer traits than questions are selected, selected traits may be reused
  across questions when different behavioural aspects are explored.
- If eight traits are selected and eight questions are generated, normally give
  every selected trait coverage before repeating a trait unless administrator
  guidance explicitly requires a different substantive prioritisation.
- Trait labels are application metadata and must be present even when
  administrator guidance does not request visible trait tagging.
""".strip()


def _normalise_prompt_limits(prompt: str) -> str:
    text = str(prompt or "")

    replacements = {
        "maximum of 6 selected traits": "maximum of 8 selected traits",
        "maximum of six selected traits": "maximum of eight selected traits",
        "up to 6 suggested trait objects": "up to 8 suggested trait objects",
        "up to six suggested trait objects": "up to eight suggested trait objects",
        "currently supports a maximum of 6 selected traits": (
            "currently supports a maximum of 8 selected traits"
        ),
        "currently supports a maximum of six selected traits": (
            "currently supports a maximum of eight selected traits"
        ),
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    legacy_optional = (
        "If administrator guidance does not require substantive why,\n"
        "listen_for or trait tagging, preserve those technical fields using\n"
        "an empty string or empty array as appropriate."
    )
    required_metadata = (
        "If administrator guidance does not require substantive why or\n"
        "listen_for content, preserve those technical fields using an empty\n"
        "string as appropriate. The traits array is never optional for a\n"
        "substantive personality question and must contain at least one valid\n"
        "selected trait."
    )
    text = text.replace(legacy_optional, required_metadata)

    return text.rstrip() + "\n\n" + _question_label_contract()


def _normalise_questions_with_labels(
    items: Any,
    selected_traits: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    canonical_traits = [
        str(trait).strip()
        for trait in selected_traits or []
        if str(trait).strip()
    ]

    lookup = {
        _normalise_key(trait): trait
        for trait in canonical_traits
    }

    # Common Sova/report alias. Keep technical output canonical to the
    # selection value Talena already stores.
    if "goal focused" in lookup:
        lookup.setdefault("achievement striving", lookup["goal focused"])
    if "achievement striving" in lookup:
        lookup.setdefault("goal focused", lookup["achievement striving"])

    questions: list[dict[str, Any]] = []
    fallback_index = 0

    for item in items:
        if not isinstance(item, dict):
            continue

        question = str(item.get("question") or "").strip()
        if not question:
            continue

        traits: list[str] = []
        raw_traits = item.get("traits")

        if isinstance(raw_traits, list):
            for raw_trait in raw_traits:
                canonical = lookup.get(_normalise_key(raw_trait))
                if canonical and canonical not in traits:
                    traits.append(canonical)

        # Last-resort display integrity. The prompt contract above should make
        # this rare, but a substantive question must never lose its visible
        # focus label merely because the model omitted metadata. Distribute the
        # fallback across the saved selection instead of silently using one
        # trait for every question.
        if not traits and canonical_traits:
            traits = [
                canonical_traits[fallback_index % len(canonical_traits)]
            ]
            fallback_index += 1

        questions.append(
            {
                "question": question,
                "traits": traits,
                "why": str(item.get("why") or "").strip(),
                "listen_for": str(item.get("listen_for") or "").strip(),
            }
        )

    return questions


def install_personality_question_label_policy() -> None:
    """Require visible focus labels and raise the trait ceiling to eight."""

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import personality_questions

    original_prompt = personality_questions.build_personality_questions_prompt

    @wraps(original_prompt)
    def personality_prompt(
        invitation,
        personality_results,
        *,
        language_code=None,
    ):
        return _normalise_prompt_limits(
            original_prompt(
                invitation,
                personality_results,
                language_code=language_code,
            )
        )

    personality_questions.build_personality_questions_prompt = personality_prompt

    if hasattr(personality_questions, "_build_personality_questions_repair_prompt"):
        original_repair = personality_questions._build_personality_questions_repair_prompt

        @wraps(original_repair)
        def personality_repair(*args, **kwargs):
            return _normalise_prompt_limits(
                original_repair(*args, **kwargs)
            )

        personality_questions._build_personality_questions_repair_prompt = (
            personality_repair
        )

    personality_questions._normalise_personality_questions = (
        _normalise_questions_with_labels
    )

    original_apply_event = personality_questions.apply_personality_questions_event

    @wraps(original_apply_event)
    def apply_personality_questions_event(result, event):
        updated = original_apply_event(result, event)
        event_type = str(event.get("type") or "").strip().lower()

        if event_type == "suggested_traits":
            items = event.get("items")
            if isinstance(items, list):
                normalised = []
                for item in items[:MAX_PERSONALITY_TRAITS]:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name") or "").strip()
                    if not name:
                        continue
                    normalised.append(
                        {
                            "name": name,
                            "reason": str(item.get("reason") or "").strip(),
                        }
                    )
                updated["suggested_traits"] = normalised

        elif event_type == "selected_traits":
            items = event.get("items")
            if isinstance(items, list):
                updated["selected_traits"] = [
                    str(item).strip()
                    for item in items[:MAX_PERSONALITY_TRAITS]
                    if str(item).strip()
                ]

        return updated

    personality_questions.apply_personality_questions_event = (
        apply_personality_questions_event
    )

    _INSTALLED = True
