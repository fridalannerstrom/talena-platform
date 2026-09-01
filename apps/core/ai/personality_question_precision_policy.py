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
- The candidate's result pattern must materially change the hypothesis. A
  clearer low-side indication, a mid-range indication and a clearer high-side
  indication should not produce interchangeable behavioural angles.
- Do not over-focus the full question set on the most extreme results. When the
  selected evidence permits, create a varied set that can include clear
  directional signals, mid-range or situational patterns, meaningful contrasts,
  profile tensions and context-specific applications.
- Variation is a quality requirement. Across the full set, avoid repeating the
  same explanatory pattern such as "low result means explore X" or "high result
  means explore Y". Candidate specificity should come from the hypothesis and
  the chosen angle, not from repeatedly announcing score direction.
- The main question must stay neutral and behavioural. Do not reveal raw STEN
  values and do not tell the candidate that the assessment has established a
  fact about them.
- Process purpose and context should make the scenario concrete and useful,
  but they must not turn the question into a generic role competency question.

VISIBLE WHY FIELD REQUIREMENT

Every why field must leave a visible candidate fingerprint, but it does NOT
need to explicitly say "low result", "high result" or equivalent every time.
The interviewer should understand why THIS question was chosen for THIS
candidate without the interface reading like a score report.

A valid why must do the following when evidence is available:

1. Identify the relevant personality trait, indication or supporting
   personality signal in plain language, either explicitly or unmistakably.
2. Explain the candidate-specific behavioural hypothesis created by the
   supplied profile evidence. This may use direction, balance, contrast,
   situational variation or interaction with another relevant profile signal.
3. Connect that hypothesis to the supplied purpose/context when relevant.

Across a multi-question set, vary how the candidate fingerprint is expressed.
Some why fields may explicitly mention a clearer preference or a less
pronounced preference. Others should instead explain a profile tension, a
balanced or context-dependent pattern, a contrast between signals, or why a
specific behaviour is useful to validate in this process.

Do not make most why fields begin with or revolve around phrases such as
"low result", "high result", "higher score", "lower score" or direct
equivalents. Use explicit direction when it genuinely adds interpretive value,
not as a mandatory template.

A why is INVALID if it only says things such as:
- "this is important for the role";
- "this explores collaboration";
- "this explores structure";
- "this explores communication";
- "this is central for a project coordinator";
without also explaining the candidate-specific personality evidence or
hypothesis that made this angle relevant.

The why field must not overclaim. Use language such as "profile indicates",
"suggests", "may point to" or "makes it relevant to explore" rather than
stating that the candidate definitely behaves in a certain way.

Do not include raw assessment scores in user-facing question, why or listen_for
text unless administrator guidance explicitly requires it.

FINAL SILENT CHECK FOR EACH QUESTION

Before returning each item, verify all four answers are concrete:
- Which exact personality construct or profile signal is this question about?
- What candidate-specific pattern or hypothesis made this angle worth asking?
- How did that evidence change the question compared with a generic interview
  question?
- Which supplied process detail made the scenario relevant?

Then review the full set once more:
- Does it feel varied rather than dominated by high/low commentary?
- Are both clear signals and useful nuances represented when available?
- Would an interviewer still recognise that the questions belong to this
  candidate even if explicit score-direction words were removed?

If any answer is missing, if the set feels repetitive, or if the trait name/tag
and question wording refer to different constructs, rewrite before returning.
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
