from __future__ import annotations

from functools import wraps
from typing import Any, Iterable


_INSTALLED = False
MAX_PERSONALITY_TRAITS = 8


def _question_label_contract() -> str:
    return f"""

TALENA PERSONALITY QUESTION LABEL CONTRACT

This is a protected product requirement.

- The application supports up to {MAX_PERSONALITY_TRAITS} selected personality traits.
- Every generated personality question must contain a traits array.
- When a question clearly explores one or more selected traits, copy the
  selected_traits value exactly; do not translate, paraphrase or localize it,
  even when the output language differs.
- If the question cannot be mapped reliably to a selected trait, use an empty
  array rather than guessing.
- Missing or unusable trait labels are metadata gaps. They must never invalidate
  or replace an otherwise complete candidate-grounded question.
- When the mapping is clear and fewer traits than questions are selected, a
  selected trait may be reused for a distinct behavioural angle.
- If eight traits are selected and eight questions are generated, normally give
  every selected trait coverage before repeating a trait when the questions
  support that mapping.
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
        "string as appropriate. Always include traits as an array, using exact\n"
        "selected trait labels where the mapping is clear and an empty array\n"
        "when it is not reliable to assign a label."
    )
    text = text.replace(legacy_optional, required_metadata)

    return text.rstrip() + "\n\n" + _question_label_contract()


def _ensure_question_labels(
    questions: list[dict[str, Any]],
    selected_traits: list[str],
) -> list[dict[str, Any]]:
    """Only fill a missing label when there is exactly one unambiguous focus."""

    canonical_traits = [
        str(trait).strip()
        for trait in selected_traits or []
        if str(trait).strip()
    ]

    if len(canonical_traits) != 1:
        return questions

    only_trait = canonical_traits[0]

    for question in questions:
        if not isinstance(question, dict):
            continue

        traits = question.get("traits")
        if not isinstance(traits, list) or not any(
            str(item or "").strip()
            for item in traits
        ):
            question["traits"] = [only_trait]

    return questions


def _selected_traits_from_events(events: list[dict[str, Any]]) -> list[str]:
    for event in reversed(events):
        if str(event.get("type") or "").strip().casefold() != "selected_traits":
            continue
        items = event.get("items")
        if not isinstance(items, list):
            return []
        return [
            str(item).strip()
            for item in items[:MAX_PERSONALITY_TRAITS]
            if str(item).strip()
        ]
    return []


def _questions_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for event in reversed(events):
        if str(event.get("type") or "").strip().casefold() != "questions":
            continue
        items = event.get("items")
        if not isinstance(items, list):
            return []
        return [
            item
            for item in items
            if isinstance(item, dict)
            and str(item.get("question") or "").strip()
        ]
    return []


def _questions_have_valid_labels(events: list[dict[str, Any]]) -> bool:
    selected_traits = _selected_traits_from_events(events)
    questions = _questions_from_events(events)

    if not selected_traits or not questions:
        return False

    selected_keys = {
        str(item).strip().casefold()
        for item in selected_traits
        if str(item).strip()
    }

    for question in questions:
        traits = question.get("traits")
        if not isinstance(traits, list) or not traits:
            return False

        valid = [
            str(item).strip().casefold()
            for item in traits
            if str(item).strip().casefold() in selected_keys
        ]
        if not valid:
            return False

    return True


def _replace_selected_traits_and_questions(
    events: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Use the fallback questions' own traits as the authoritative selection."""

    selected_traits: list[str] = []
    seen = set()

    for question in questions:
        for trait in question.get("traits") or []:
            text = str(trait or "").strip()
            key = text.casefold()
            if text and key not in seen:
                seen.add(key)
                selected_traits.append(text)

    selected_traits = selected_traits[:MAX_PERSONALITY_TRAITS]

    output: list[dict[str, Any]] = []
    selected_inserted = False
    questions_inserted = False

    for event in events:
        event_type = str(event.get("type") or "").strip().casefold()

        if event_type == "selected_traits":
            if not selected_inserted:
                output.append(
                    {
                        "type": "selected_traits",
                        "items": selected_traits,
                    }
                )
                selected_inserted = True
            continue

        if event_type == "questions":
            if not questions_inserted:
                output.append(
                    {
                        "type": "questions",
                        "items": questions,
                    }
                )
                questions_inserted = True
            continue

        if event_type == "done":
            if not selected_inserted:
                output.append(
                    {
                        "type": "selected_traits",
                        "items": selected_traits,
                    }
                )
                selected_inserted = True
            if not questions_inserted:
                output.append(
                    {
                        "type": "questions",
                        "items": questions,
                    }
                )
                questions_inserted = True

        output.append(event)

    if not selected_inserted:
        output.append(
            {
                "type": "selected_traits",
                "items": selected_traits,
            }
        )
    if not questions_inserted:
        output.append(
            {
                "type": "questions",
                "items": questions,
            }
        )

    return output


def install_personality_question_label_policy() -> None:
    """Require accurate visible focus labels and allow up to eight traits."""

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

    original_normalise_questions = (
        personality_questions._normalise_personality_questions
    )

    @wraps(original_normalise_questions)
    def normalise_personality_questions(items, selected_traits):
        questions = original_normalise_questions(
            items,
            selected_traits,
        )
        return _ensure_question_labels(
            questions,
            selected_traits,
        )

    personality_questions._normalise_personality_questions = (
        normalise_personality_questions
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

    original_stream = personality_questions.stream_personality_questions

    @wraps(original_stream)
    def stream_personality_questions(*args, **kwargs) -> Iterable[dict[str, Any]]:
        events = [
            event
            for event in original_stream(*args, **kwargs)
            if isinstance(event, dict)
        ]

        # Trait labels are optional metadata. Keep the generated questions
        # even when a label is missing or cannot be matched safely; the
        # personality normalizer already preserves exact selected labels and
        # discards unrecognized values.
        yield from events

    personality_questions.stream_personality_questions = (
        stream_personality_questions
    )

    _INSTALLED = True
