from __future__ import annotations

from functools import wraps
from typing import Any


_INSTALLED = False


def _normalise(value: Any) -> str:
    text = str(value or "").strip().casefold()
    for character in ("_", "-", "–", "—", "/"):
        text = text.replace(character, " ")
    return " ".join(text.split())


def _sten_direction(value: Any) -> str:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return "unknown direction"

    if score <= 3:
        return "clearer low-side indication"
    if score >= 8:
        return "clearer high-side indication"
    return "more mid-range indication"


def _selected_personality_snapshot(owner, personality_results: list[dict[str, Any]]) -> str:
    selected = [
        str(item or "").strip()
        for item in getattr(owner, "selected_personality_traits", None) or []
        if str(item or "").strip()
    ]

    if any(item.casefold().startswith("competency::") for item in selected):
        return (
            "Competency mode is active. Preserve the selected competency as the visible "
            "question topic and use only the supporting personality evidence already "
            "supplied in the earlier prompt to shape the candidate-specific angle."
        )

    lookup = {
        _normalise(item.get("name")): item
        for item in personality_results or []
        if _normalise(item.get("name"))
    }

    rows = []
    for selected_name in selected:
        item = lookup.get(_normalise(selected_name))
        if not item or item.get("sten") is None:
            continue
        rows.append(
            f"- {selected_name}: {_sten_direction(item.get('sten'))}"
        )

    if not rows:
        ranked = sorted(
            [
                item
                for item in personality_results or []
                if item.get("name") and item.get("sten") is not None
            ],
            key=lambda item: abs(float(item.get("sten")) - 5.5),
            reverse=True,
        )
        for item in ranked[:6]:
            rows.append(
                f"- {str(item.get('name')).strip()}: "
                f"{_sten_direction(item.get('sten'))}"
            )

    return "\n".join(rows) if rows else "No usable selected personality evidence."


def _personality_precision_instruction(owner, personality_results: list[dict[str, Any]]) -> str:
    snapshot = _selected_personality_snapshot(owner, personality_results)

    return f"""

TALENA PERSONALITY QUESTION PRECISION STANDARD

This is the final protected quality check for personality interview questions.
It is applied after administrator guidance, normal grounding and the candidate
fingerprint standard.

SELECTED CANDIDATE EVIDENCE
{snapshot}

QUESTION PRECISION CONTRACT

- Preserve construct fidelity. The question must explore the actual selected
  personality construct or the exact supporting personality evidence supplied
  for a competency. Do not silently replace it with a nearby but different
  construct.
- Examples of invalid semantic drift include treating Conceptual as Analytical,
  treating Networking as Teamwork, treating Adaptability as Resilience, or
  treating Emotional stability as Stress tolerance unless the supplied Talena
  definition explicitly establishes that connection.
- Use the Talena trait definition already supplied earlier in the prompt as the
  source of truth for what each construct means.
- The candidate's result direction must change the hypothesis. A clearer
  low-side indication, a mid-range indication and a clearer high-side
  indication should not produce the same behavioural angle.
- The main question must stay neutral and behavioural. Do not reveal raw STEN
  values and do not tell the candidate that the assessment has established a
  fact about them.
- Process purpose and context should make the scenario concrete and useful,
  but they must not turn the question into a generic role competency question.

VISIBLE WHY FIELD REQUIREMENT

Every why field must leave a visible candidate fingerprint. It must contain all
three elements below when the evidence is available:

1. Name the relevant personality trait, indication or supporting personality
   signal in plain language.
2. State the direction or pattern qualitatively, for example that the profile
   suggests a clearer preference toward one side, a less pronounced preference,
   or a more balanced/mid-range pattern. Do not show the raw STEN value.
3. Explain why THAT candidate-specific pattern makes the question worth
   validating in the supplied process context.

A why is INVALID if it only says things such as:
- "this is important for the role";
- "this explores collaboration";
- "this explores structure";
- "this explores communication";
- "this is central for a project coordinator";
without also explaining the candidate-specific personality indication that made
this angle relevant.

The why field must not overclaim. Use language such as "profile indicates",
"suggests", "may point to" or "makes it relevant to explore" rather than
stating that the candidate definitely behaves in a certain way.

FINAL SILENT CHECK FOR EACH QUESTION

Before returning each item, verify all four answers are concrete:
- Which exact personality construct is this question about?
- What is this candidate's qualitative result direction/pattern on that evidence?
- How did that direction change the question angle?
- Which supplied process detail made the scenario relevant?

If any answer is missing, or if the trait name/tag and question wording refer to
different constructs, rewrite the item before returning it.
"""


def install_personality_question_precision_policy() -> None:
    """Apply a final construct-fidelity and candidate-specific why requirement."""

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
        prompt = original_prompt(
            invitation,
            personality_results,
            language_code=language_code,
        )
        return str(prompt).rstrip() + _personality_precision_instruction(
            invitation,
            personality_results,
        )

    personality_questions.build_personality_questions_prompt = personality_prompt

    if hasattr(personality_questions, "_build_personality_questions_repair_prompt"):
        original_repair = personality_questions._build_personality_questions_repair_prompt

        @wraps(original_repair)
        def personality_repair(
            *,
            owner,
            personality_results,
            selected_traits,
        ):
            prompt = original_repair(
                owner=owner,
                personality_results=personality_results,
                selected_traits=selected_traits,
            )
            return str(prompt).rstrip() + _personality_precision_instruction(
                owner,
                personality_results,
            )

        personality_questions._build_personality_questions_repair_prompt = personality_repair

    _INSTALLED = True
