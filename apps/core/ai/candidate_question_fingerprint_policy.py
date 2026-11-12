from __future__ import annotations

from functools import wraps
from typing import Any

from .shared_context import build_shared_ai_context


_INSTALLED = False


def _context_status(owner) -> tuple[str, str]:
    shared = build_shared_ai_context(owner)
    purpose = str(shared.get("purpose_label") or "").strip()
    context = str(shared.get("context_text") or "").strip()
    return purpose, context


def _personality_fingerprint_instruction(owner) -> str:
    purpose, context = _context_status(owner)

    return f"""

TALENA CANDIDATE FINGERPRINT STANDARD

This protected requirement is applied after administrator guidance and after
Talena's normal candidate-grounding rules.

PROCESS PURPOSE
{purpose or "No process purpose supplied."}

PROCESS CONTEXT
{context or "No additional process context supplied."}

The question set must feel written for THIS candidate in THIS process, not like
a reusable interview-question bank.

PERSONALITY QUESTION CONTRACT

- Every question must have a candidate-specific personality hypothesis behind
  it. A role topic by itself is never enough.
- The candidate's actual personality direction must materially change the
  question angle. If the opposite personality result would lead to essentially
  the same question, rewrite the question.
- When meaningful process context exists, use concrete situations, demands or
  language from that context to make the question practical. Context sets the
  scene; personality evidence determines what is being tested.
- Do not manufacture role requirements that are not present in the supplied
  context.
- Keep questions neutral and behavioural. Do not reveal raw STEN values and do
  not tell the candidate that the assessment proves a behaviour.

WHY FIELD CONTRACT

The why field is Talena's visible evidence trace. It must make the
candidate-specific reason understandable to the interviewer.

A valid why must:
1. identify the relevant personality indication, trait or supporting
   personality signal in plain language;
2. explain the hypothesis created by that candidate-specific pattern; and
3. connect that hypothesis to the supplied purpose/context when relevant.

Do not output a generic why such as "this is important for the role",
"this explores teamwork", "this explores prioritisation" or equivalent unless
it also states WHY this candidate's personality evidence makes that area worth
exploring.

Do not include raw assessment scores in user-facing question, why or listen_for
text unless administrator guidance explicitly requires it.

FINAL CANDIDATE-FINGERPRINT CHECK

For every question, silently complete both sentences:
- "I chose this angle because this candidate's personality evidence indicates ..."
- "I made it relevant to this process by using ..."

If either sentence cannot be completed from supplied evidence and context,
rewrite the question before returning it.
"""


def _motivation_fingerprint_instruction(owner) -> str:
    purpose, context = _context_status(owner)

    return f"""

TALENA CANDIDATE FINGERPRINT STANDARD

This protected requirement is applied after administrator guidance and after
Talena's normal candidate-grounding rules.

PROCESS PURPOSE
{purpose or "No process purpose supplied."}

PROCESS CONTEXT
{context or "No additional process context supplied."}

The motivation question set must feel written for THIS candidate in THIS
process.

MOTIVATION QUESTION CONTRACT

- Every question must be anchored to an actual supplied motivation factor,
  factor contrast or profile pattern.
- Prominent, mid-range and less-central factors must lead to meaningfully
  different hypotheses and question angles.
- If the factor pattern were reversed and the same question would still work,
  the question is too generic and must be rewritten.
- When meaningful process context exists, use relevant situations or demands
  from that context. Context sets the scene; the motivation profile determines
  what is being explored.
- Do not turn a less-central driver into a claim about low skill, weak
  performance or absence of a quality.

WHY FIELD CONTRACT

The why field must identify the motivation factor or contrast that made this
question relevant for this candidate, explain the non-deterministic hypothesis,
and connect it to purpose/context where useful.

A generic why that only says an area is important for the role or process is
invalid when candidate-specific motivation evidence is available.

FINAL CANDIDATE-FINGERPRINT CHECK

For every question, silently complete both sentences:
- "I chose this angle because this candidate's motivation profile shows ..."
- "I made it relevant to this process by using ..."

If either cannot be completed from supplied evidence and context, rewrite the
question before returning it.
"""


def _usable_cognitive_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in results or []
        if (
            str(item.get("label") or item.get("key") or "").strip()
            and item.get("percentile") is not None
        )
    ]


def _cognitive_fingerprint_instruction(
    owner,
    cognitive_results: list[dict[str, Any]],
) -> str:
    purpose, context = _context_status(owner)
    usable = _usable_cognitive_results(cognitive_results)
    labels = [
        str(item.get("label") or item.get("key") or "").strip()
        for item in usable
    ]
    label_text = ", ".join(labels) or "None"

    if len(usable) == 1:
        coverage_rule = f"""
ONLY ONE COMPLETED COGNITIVE RESULT IS AVAILABLE: {labels[0]}.

Therefore EVERY generated cognitive question must remain explicitly anchored
to the practical demands of {labels[0]}. The three questions may explore
different manifestations, for example approach, checking strategy, complexity,
pace, support, trade-offs or use of information, but they may not drift into
standalone questions about collaboration, change, prioritisation, leadership or
another generic role competency.

A contextual topic such as a changing customer need or project priority is
valid only when the question explicitly explores the {labels[0]} reasoning
demand inside that situation.
"""
    elif len(usable) > 1:
        coverage_rule = """
Several completed cognitive abilities are available. Every question must be
traceable to at least one of them. When the requested question count permits,
cover the distinct completed abilities before repeating the same ability, and
use meaningful contrasts between results when useful.
"""
    else:
        coverage_rule = """
No usable cognitive result is available. Do not invent cognitive evidence.
"""

    return f"""

TALENA CANDIDATE FINGERPRINT STANDARD

This protected requirement is applied after administrator guidance and after
Talena's normal candidate-grounding rules.

PROCESS PURPOSE
{purpose or "No process purpose supplied."}

PROCESS CONTEXT
{context or "No additional process context supplied."}

COMPLETED COGNITIVE RESULT TYPES
Count: {len(usable)}
Types: {label_text}

{coverage_rule}

COGNITIVE QUESTION CONTRACT

- A cognitive question is valid only if a specific supplied cognitive result
  explains why that exact question was selected.
- Process context may make the situation realistic, but context must never
  replace the cognitive result as the subject of the question.
- If a question could be asked unchanged without knowing the candidate's
  cognitive result, it is too generic and must be rewritten.
- If a very high and a very low result on the same ability would produce the
  same question angle, it is too generic and must be rewritten.
- Keep lower-result questions neutral. Explore strategies, checking,
  structuring, support, pace, complexity or practical handling rather than
  implying inability.
- Keep higher-result questions neutral. Explore how the reasoning capability is
  used in practice rather than implying guaranteed performance.

WHY FIELD CONTRACT

The why field is Talena's visible evidence trace. It must state which cognitive
ability/result pattern made the question useful for THIS candidate and explain
what practical hypothesis the interviewer is validating.

A why that only says the topic is important for the role, customers, projects,
change, teamwork or prioritisation is invalid when cognitive evidence is
available.

Do not expose raw percentile values in user-facing question, why or listen_for
text unless administrator guidance explicitly requires it.

FINAL CANDIDATE-FINGERPRINT CHECK

For every question, silently complete both sentences:
- "I chose this angle because this candidate's cognitive result in [ability] ..."
- "I made it relevant to this process by using ..."

If the first sentence cannot name an actual completed cognitive ability, the
question must be rewritten. If context exists and the second sentence cannot be
completed, make the scenario more process-specific without changing the
cognitive evidence being explored.
"""


def install_candidate_question_fingerprint_policy() -> None:
    """Apply the final candidate-fingerprint quality bar to question prompts."""

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import cognitive_questions
    from apps.core.ai import motivation_questions
    from apps.core.ai import personality_questions

    original_personality_prompt = personality_questions.build_personality_questions_prompt

    @wraps(original_personality_prompt)
    def personality_prompt(
        invitation,
        personality_results,
        *,
        language_code=None,
    ):
        prompt = original_personality_prompt(
            invitation,
            personality_results,
            language_code=language_code,
        )
        return str(prompt).rstrip() + _personality_fingerprint_instruction(invitation)

    personality_questions.build_personality_questions_prompt = personality_prompt

    if hasattr(personality_questions, "_build_personality_questions_repair_prompt"):
        original_personality_repair = (
            personality_questions._build_personality_questions_repair_prompt
        )

        @wraps(original_personality_repair)
        def personality_repair(
            *,
            owner,
            personality_results,
            selected_traits,
        ):
            prompt = original_personality_repair(
                owner=owner,
                personality_results=personality_results,
                selected_traits=selected_traits,
            )
            return str(prompt).rstrip() + _personality_fingerprint_instruction(owner)

        personality_questions._build_personality_questions_repair_prompt = (
            personality_repair
        )

    original_motivation_prompt = motivation_questions.build_motivation_questions_prompt

    @wraps(original_motivation_prompt)
    def motivation_prompt(
        *,
        owner,
        motivation_results,
        language_code="en",
    ):
        prompt = original_motivation_prompt(
            owner=owner,
            motivation_results=motivation_results,
            language_code=language_code,
        )
        return str(prompt).rstrip() + _motivation_fingerprint_instruction(owner)

    motivation_questions.build_motivation_questions_prompt = motivation_prompt

    original_cognitive_prompt = cognitive_questions.build_cognitive_questions_prompt

    @wraps(original_cognitive_prompt)
    def cognitive_prompt(
        *,
        owner,
        cognitive_results,
        language_code="en",
    ):
        prompt = original_cognitive_prompt(
            owner=owner,
            cognitive_results=cognitive_results,
            language_code=language_code,
        )
        return str(prompt).rstrip() + _cognitive_fingerprint_instruction(
            owner,
            cognitive_results,
        )

    cognitive_questions.build_cognitive_questions_prompt = cognitive_prompt

    _INSTALLED = True
