from __future__ import annotations

from functools import wraps
from inspect import signature
from typing import Any, Callable, Iterable


_INSTALLED = False
_MAX_GENERATION_ATTEMPTS = 3


def _target_question_count(feature: str) -> int:
    """Return the product-level question count for an interview section."""

    from apps.processes.interview_config import get_interview_section_config

    return int(
        get_interview_section_config(feature).get("question_count", 0)
        or 0
    )


def _fixed_count_instruction(feature: str) -> str:
    count = _target_question_count(feature)

    return f"""

TALENA FIXED QUESTION COUNT

This is a protected product requirement and is not administrator-editable.
Return exactly {count} complete question objects.

If any administrator guidance suggests a different number of questions,
this fixed Talena requirement takes precedence for question count only.
Administrator guidance still controls the content, interpretation,
interviewing approach, tone and explanatory fields.
"""


def _install_prompt_rule(
    module,
    function_name: str,
    feature: str,
) -> None:
    original = getattr(module, function_name)

    if getattr(original, "_talena_fixed_question_count", False):
        return

    @wraps(original)
    def wrapped(*args, **kwargs):
        prompt = original(*args, **kwargs)
        return str(prompt).rstrip() + _fixed_count_instruction(feature)

    wrapped._talena_fixed_question_count = True
    setattr(module, function_name, wrapped)


def _question_items(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the final normalised questions event items."""

    for event in reversed(events):
        if str(event.get("type") or "").strip().lower() != "questions":
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


def _selected_traits(events: list[dict[str, Any]]) -> list[str]:
    for event in reversed(events):
        if str(event.get("type") or "").strip().lower() != "selected_traits":
            continue

        items = event.get("items")

        if not isinstance(items, list):
            return []

        return [
            str(item).strip()
            for item in items
            if str(item).strip()
        ]

    return []


def _replace_questions(
    events: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Replace the questions event while preserving event order."""

    replacement = {
        "type": "questions",
        "items": questions,
    }

    output: list[dict[str, Any]] = []
    inserted = False

    for event in events:
        event_type = str(
            event.get("type")
            or ""
        ).strip().lower()

        if event_type == "questions":
            if not inserted:
                output.append(replacement)
                inserted = True
            continue

        if event_type == "done" and not inserted:
            output.append(replacement)
            inserted = True

        output.append(event)

    if not inserted:
        output.append(replacement)
        output.append({"type": "done"})

    return output


def _generate_events(
    original_stream: Callable[..., Iterable[dict[str, Any]]],
    *args,
    **kwargs,
) -> list[dict[str, Any]]:
    return [
        event
        for event in original_stream(*args, **kwargs)
        if isinstance(event, dict)
    ]


def _personality_fallback(
    module,
    events: list[dict[str, Any]],
    kwargs: dict[str, Any],
) -> list[dict[str, Any]]:
    """Use the safe personality fallback when AI under-produces."""

    selected_traits = _selected_traits(events)

    owner = kwargs.get("owner")
    personality_results = kwargs.get("personality_results") or []

    if not selected_traits and owner is not None:
        selected_traits = list(
            getattr(owner, "selected_personality_traits", None)
            or []
        )

    language_code = str(
        kwargs.get("language_code")
        or "en"
    )

    language_context = getattr(
        module,
        "_personality_questions_language",
        None,
    )

    token = None

    if language_context is not None:
        token = language_context.set(language_code)

    try:
        # A valid question event can still contain the wrong number of items.
        # Give the model one focused repair opportunity with the selected traits
        # and the same admin guidance before silently replacing its work with
        # deterministic fallback questions.
        repair_builder = getattr(
            module,
            "_generate_repaired_personality_questions_event",
            None,
        )
        if callable(repair_builder) and owner is not None:
            try:
                repaired_event = repair_builder(
                    owner=owner,
                    personality_results=personality_results,
                    selected_traits=selected_traits,
                )
                repaired_items = repaired_event.get("items")
                repaired_questions = [
                    item
                    for item in repaired_items or []
                    if isinstance(item, dict)
                    and str(item.get("question") or "").strip()
                ]
                if (
                    repaired_event.get("type") == "questions"
                    and len(repaired_questions)
                    == _target_question_count("personality")
                ):
                    return repaired_questions
            except Exception:
                # Keep the existing deterministic fallback as the last resort.
                pass

        is_competency_selection = any(
            str(item or "").strip().casefold().startswith("competency::")
            for item in selected_traits
        )
        if not is_competency_selection:
            from .personality_ai_evidence import build_personality_ai_evidence

            summary_evidence = build_personality_ai_evidence(
                personality_results,
                language_code=language_code,
                include_traits=selected_traits or None,
            )
            if any(
                str(item.get("summary") or "").strip()
                for item in summary_evidence
            ):
                raise ValueError(
                    "Personality question generation did not produce the "
                    "required question count after focused repair. Generic "
                    "fallback questions are disabled when candidate-specific "
                    "Result Summary evidence is available."
                )

        fallback_builder = module._build_safe_personality_questions_event
        fallback_kwargs = {
            "selected_traits": selected_traits,
            "personality_results": personality_results,
        }

        # Candidate-specific fallback policies may need the complete owner to
        # resolve supporting personality evidence for competency selections.
        # Preserve compatibility with the original two-argument fallback.
        if "owner" in signature(fallback_builder).parameters:
            fallback_kwargs["owner"] = owner

        fallback_event = fallback_builder(**fallback_kwargs)
    finally:
        if language_context is not None and token is not None:
            language_context.reset(token)

    items = fallback_event.get("items")

    if not isinstance(items, list):
        return []

    return [
        item
        for item in items
        if isinstance(item, dict)
        and str(item.get("question") or "").strip()
    ]


def _install_stream_rule(
    module,
    function_name: str,
    feature: str,
) -> None:
    original_stream = getattr(module, function_name)

    if getattr(original_stream, "_talena_fixed_question_count", False):
        return

    @wraps(original_stream)
    def wrapped(*args, **kwargs):
        target_count = _target_question_count(feature)
        last_events: list[dict[str, Any]] = []
        last_error: Exception | None = None

        # Reserve one request for a focused exact-count repair on personality
        # questions. This keeps the total request budget the same while giving a
        # count-mismatch response a chance to retain candidate-specific content.
        max_attempts = (
            max(1, _MAX_GENERATION_ATTEMPTS - 1)
            if feature == "personality"
            else _MAX_GENERATION_ATTEMPTS
        )

        for _attempt in range(max_attempts):
            try:
                events = _generate_events(
                    original_stream,
                    *args,
                    **kwargs,
                )
            except Exception as exc:
                last_error = exc
                continue

            last_events = events
            questions = _question_items(events)

            if len(questions) == target_count:
                yield from events
                return

        if last_events:
            questions = _question_items(last_events)

            # Over-generation is safe to normalise for cognitive and
            # motivation questions. Personality is regenerated/fallbacked
            # so trait coverage is not accidentally lost by slicing.
            if (
                feature in {"cognitive", "motivation"}
                and len(questions) > target_count
            ):
                yield from _replace_questions(
                    last_events,
                    questions[:target_count],
                )
                return

            if feature == "personality":
                fallback_questions = _personality_fallback(
                    module,
                    last_events,
                    kwargs,
                )

                if len(fallback_questions) == target_count:
                    yield from _replace_questions(
                        last_events,
                        fallback_questions,
                    )
                    return

        message = (
            f"Talena requires exactly {target_count} {feature} "
            "interview questions, but generation did not produce "
            "the required count."
        )

        if last_error is not None:
            raise ValueError(message) from last_error

        raise ValueError(message)

    wrapped._talena_fixed_question_count = True
    setattr(module, function_name, wrapped)


def install_question_count_policy() -> None:
    """
    Enforce Talena's fixed 3 / 3 / 8 interview-question policy.

    The AI prompt remains administrator-configurable for substance, while
    the number of generated questions is a protected product contract.
    """

    global _INSTALLED

    if _INSTALLED:
        return

    from apps.core.ai import cognitive_questions
    from apps.core.ai import motivation_questions
    from apps.core.ai import personality_questions

    _install_prompt_rule(
        cognitive_questions,
        "build_cognitive_questions_prompt",
        "cognitive",
    )
    _install_prompt_rule(
        motivation_questions,
        "build_motivation_questions_prompt",
        "motivation",
    )
    _install_prompt_rule(
        personality_questions,
        "build_personality_questions_prompt",
        "personality",
    )

    # Personality's internal repair/fallback helpers also use this function.
    # Keeping it fixed at eight ensures every code path follows the same rule.
    personality_questions.get_personality_question_count = (
        lambda _selected_traits: _target_question_count("personality")
    )

    if hasattr(
        personality_questions,
        "_build_personality_questions_repair_prompt",
    ):
        _install_prompt_rule(
            personality_questions,
            "_build_personality_questions_repair_prompt",
            "personality",
        )

    _install_stream_rule(
        cognitive_questions,
        "stream_cognitive_questions",
        "cognitive",
    )
    _install_stream_rule(
        motivation_questions,
        "stream_motivation_questions",
        "motivation",
    )
    _install_stream_rule(
        personality_questions,
        "stream_personality_questions",
        "personality",
    )

    _INSTALLED = True
