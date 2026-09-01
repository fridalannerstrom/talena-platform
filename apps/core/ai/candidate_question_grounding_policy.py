from __future__ import annotations

from functools import wraps
from typing import Any


_INSTALLED = False


def _normalise_name(value: Any) -> str:
    text = str(value or "").strip().casefold()
    for character in ("_", "-", "–", "—", "/"):
        text = text.replace(character, " ")
    return " ".join(text.split())


def _sten_band(value: Any) -> str:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return "unknown"

    if score <= 3:
        return "low"
    if score >= 8:
        return "high"
    return "mid-range"


def _motivation_band(value: Any) -> str:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return "unknown"

    if score <= 2:
        return "less central"
    if score >= 4:
        return "prominent"
    return "mid-range"


def _cognitive_band(value: Any) -> str:
    try:
        percentile = int(round(float(value)))
    except (TypeError, ValueError):
        return "unknown"

    if percentile <= 9:
        return "very low relative to the reference group"
    if percentile <= 24:
        return "low relative to the reference group"
    if percentile <= 74:
        return "within the typical range"
    if percentile <= 90:
        return "high relative to the reference group"
    return "very high relative to the reference group"


def _personality_snapshot(owner, personality_results: list[dict[str, Any]]) -> str:
    result_lookup = {
        _normalise_name(item.get("name")): item
        for item in personality_results or []
        if _normalise_name(item.get("name"))
    }

    selected = [
        str(item or "").strip()
        for item in getattr(owner, "selected_personality_traits", None) or []
        if str(item or "").strip()
    ]

    if any(item.casefold().startswith("competency::") for item in selected):
        return (
            "Question basis: user-selected competencies.\n"
            "Use the SUPPORTING PERSONALITY EVIDENCE supplied under each "
            "competency in the original prompt as the candidate-specific "
            "profile evidence. When supporting rows exist, their actual "
            "direction and pattern must materially affect the question angle."
        )

    selected_keys = {_normalise_name(item) for item in selected}
    relevant_results = [
        item
        for key, item in result_lookup.items()
        if not selected_keys or key in selected_keys
    ]

    if not relevant_results:
        relevant_results = list(personality_results or [])

    rows = []
    for item in relevant_results:
        name = str(item.get("name") or "").strip()
        sten = item.get("sten")
        if not name or sten is None:
            continue
        rows.append(f"- {name}: STEN {sten} of 10 ({_sten_band(sten)})")

    if not rows:
        return "No usable personality score snapshot is available."

    return "\n".join(rows)


def _personality_grounding_instruction(
    owner,
    personality_results: list[dict[str, Any]],
) -> str:
    snapshot = _personality_snapshot(owner, personality_results)

    return f"""

TALENA CANDIDATE-SPECIFIC QUESTION GROUNDING

This is a protected product requirement. The user's selection controls WHAT
area the interview should explore. The candidate's actual assessment profile
controls WHICH ANGLE the question takes.

CANDIDATE-SPECIFIC PROFILE SNAPSHOT
{snapshot}

REQUIRED GROUNDING BEHAVIOUR

- Every question must be materially grounded in this candidate's supplied
  personality evidence, not only in the selected trait or competency label.
- Use actual score direction, relative prominence and meaningful profile
  contrasts to decide what hypothesis or behaviour is worth exploring.
- Two candidates with the same popup selection but meaningfully different
  assessment results should normally receive meaningfully different questions.
- Do not write a generic question that would be equally suitable if the
  candidate had the opposite result pattern. If it would, rewrite it so the
  candidate's actual profile changes the angle being explored.
- Keep the main question neutral and non-leading. Do not reveal STEN values or
  tell the candidate that the assessment proves a behaviour.
- Ask for concrete examples that can confirm, nuance or contradict the
  assessment indication.
- The why field must explain the candidate-specific reason for asking the
  question. Connect the selected area to the actual profile pattern without
  making the score sound deterministic.
- The listen_for field must describe evidence that would help the interviewer
  validate, qualify or challenge the specific hypothesis behind the question.
- Use process purpose and supplied context to make the situation relevant, but
  never let process context replace the candidate's assessment evidence as the
  basis for the question.
- In competency mode, supporting personality evidence is contextual evidence,
  not a competency score. When supporting evidence exists, it must materially
  shape the angle. If no mapped supporting personality evidence exists for a
  selected competency, do not invent a connection. Build the question from the
  competency definition and supplied process context and keep that evidence
  limitation clear in why/context guidance.

QUALITY CHECK BEFORE RETURNING

For each question, silently ask: "What exact candidate result made me choose
this angle?" If supporting assessment evidence exists but there is no concrete
answer, rewrite the question.
"""


def _motivation_snapshot(motivation_results: list[dict[str, Any]]) -> str:
    valid = []

    for item in motivation_results or []:
        name = str(item.get("name") or "").strip()
        score = item.get("score")
        if not name or score is None:
            continue
        valid.append((name, score))

    valid.sort(key=lambda item: (-float(item[1]), item[0].casefold()))

    rows = [
        f"- {name}: STIVE {score} of 5 ({_motivation_band(score)})"
        for name, score in valid
    ]

    if not rows:
        return "No usable motivation score snapshot is available."

    return "\n".join(rows)


def _motivation_grounding_instruction(
    motivation_results: list[dict[str, Any]],
) -> str:
    snapshot = _motivation_snapshot(motivation_results)

    return f"""

TALENA CANDIDATE-SPECIFIC QUESTION GROUNDING

This is a protected product requirement. Motivation questions must be built
from the shape of this candidate's actual motivation profile, not from generic
motivation topics or process context alone.

CANDIDATE-SPECIFIC MOTIVATION SNAPSHOT
{snapshot}

REQUIRED GROUNDING BEHAVIOUR

- Every question must be traceable to one or more actual motivation factors in
  the supplied candidate data.
- Let the candidate's relative pattern determine the angle: prominent drivers,
  less central drivers, mid-range factors and meaningful contrasts should lead
  to different questions.
- When the evidence permits, distribute the question set across distinct parts
  of the profile rather than asking several versions of the same high-level
  motivation question.
- Two candidates with the same process purpose but different motivation
  profiles should normally receive meaningfully different questions.
- Do not write a generic question that would be equally suitable if the factor
  pattern were reversed. If it would, rewrite it.
- Do not reveal STIVE values or phrase the main question as "your test says".
  Ask neutrally for examples, preferences, conditions or trade-offs that can
  validate or nuance the assessment indication.
- A low or less-central motivation score is not low ability, poor performance
  or absence of the quality named by the factor.
- The why field must state the candidate-specific profile reason for asking the
  question without making the assessment sound deterministic.
- The listen_for field must identify evidence that would confirm, nuance or
  challenge the specific motivation hypothesis being explored.
- Use purpose and supplied process context to make questions practical, but do
  not let that context replace the candidate's motivation results as the basis.

QUALITY CHECK BEFORE RETURNING

For each question, silently ask: "Which exact motivation result or contrast
made me choose this angle?" If the answer is only the process purpose or a
common interview topic, rewrite the question.
"""


def _cognitive_snapshot(cognitive_results: list[dict[str, Any]]) -> str:
    rows = []

    for item in cognitive_results or []:
        label = str(item.get("label") or item.get("key") or "").strip()
        percentile = item.get("percentile")
        if not label or percentile is None:
            continue
        rows.append(
            f"- {label}: percentile {percentile} ({_cognitive_band(percentile)})"
        )

    if not rows:
        return "No usable cognitive score snapshot is available."

    return "\n".join(rows)


def _cognitive_grounding_instruction(
    cognitive_results: list[dict[str, Any]],
) -> str:
    snapshot = _cognitive_snapshot(cognitive_results)

    return f"""

TALENA CANDIDATE-SPECIFIC QUESTION GROUNDING

This is a protected product requirement. Cognitive follow-up questions must
be shaped by this candidate's actual completed reasoning results.

CANDIDATE-SPECIFIC COGNITIVE SNAPSHOT
{snapshot}

REQUIRED GROUNDING BEHAVIOUR

- Every question must be traceable to at least one completed cognitive result.
- The actual percentile position and the pattern across completed abilities
  must materially affect what is worth exploring.
- When several abilities are available, use meaningful differences or
  contrasts where useful instead of producing interchangeable questions.
- Two candidates with the same process purpose but different cognitive result
  patterns should normally receive meaningfully different questions.
- Do not write a generic question that would be equally suitable for a very
  high and a very low result on the same ability. If it would, rewrite it.
- Do not reveal percentile values in the main question and do not frame lower
  results as personal deficits or higher results as guaranteed performance.
- Keep questions behavioural and practical. Explore examples, strategies,
  conditions, complexity, pace, checking approaches or support needs where
  these are genuinely relevant to the supplied result and context.
- Do not infer personality, motivation or work ethic from cognitive scores.
- The why field must explain why this candidate's specific cognitive result
  pattern makes the question useful without turning the result into a final
  judgement.
- The listen_for field must identify evidence that can add practical context
  to the exact reasoning result being explored.
- Use purpose and supplied process context to make the question relevant, but
  never let context replace the cognitive assessment result as the basis.

QUALITY CHECK BEFORE RETURNING

For each question, silently ask: "Which exact cognitive result made me choose
this angle?" If there is no concrete answer in the supplied assessment data,
rewrite the question.
"""


def _trait_fallback_text(*, trait: str, band: str, language_code: str, index: int):
    variant = index % 3

    if language_code == "sv":
        if band == "high":
            questions = [
                "Berätta om en situation där ditt naturliga sätt att ta dig an arbetet blev särskilt tydligt. Vad fungerade bra, och när behövde du justera ditt sätt?",
                "Ge ett konkret exempel där en tydlig personlig preferens påverkade hur du agerade. Vilken effekt fick ditt sätt att arbeta och vilka avvägningar behövde du göra?",
                "Beskriv ett tillfälle där ditt vanliga arbetssätt var en tydlig tillgång. Fanns det någon del av situationen där du behövde medvetet balansera eller anpassa det?",
            ]
            why = (
                f"{trait} är en tydligare hög indikation i kandidatens profil. "
                "Frågan utforskar hur preferensen faktiskt visar sig, vilken nytta "
                "den kan ha och när situationsanpassning blir viktig."
            )
        elif band == "low":
            questions = [
                "Berätta om en situation där kraven gjorde att du behövde arbeta på ett sätt som inte kändes helt naturligt för dig. Hur märkte du det och vad gjorde du?",
                "Ge ett konkret exempel på när du behövde använda ett arbetssätt som du inte spontant brukar välja. Vad hjälpte dig att anpassa dig?",
                "Beskriv ett tillfälle där situationen krävde ett annat beteende än det du normalt föredrar. Hur hanterade du det och vad blev resultatet?",
            ]
            why = (
                f"{trait} är en tydligare låg indikation i kandidatens profil. "
                "Frågan utforskar hur personen agerar när situationen kan kräva "
                "ett beteende utanför den naturliga preferensen."
            )
        else:
            questions = [
                "Beskriv två liknande situationer där du valde olika sätt att agera. Vad i sammanhanget påverkade hur du tog dig an dem?",
                "Berätta om ett område där ditt sätt att arbeta varierar ganska mycket beroende på situation. Vad avgör vilken väg du väljer?",
                "Ge exempel på när du har anpassat samma typ av uppgift på olika sätt. Vilka signaler i situationen styrde ditt beteende?",
            ]
            why = (
                f"{trait} ligger närmare mitten av kandidatens profil. Frågan "
                "utforskar därför situationsvariation i stället för att anta en "
                "starkt föredragen beteenderiktning."
            )

        return (
            questions[variant],
            why,
            "Lyssna efter konkreta situationer, egna handlingar, medvetna val, "
            "avvägningar och hur beteendet påverkades av sammanhanget.",
        )

    if band == "high":
        questions = [
            "Tell me about a situation where your natural way of approaching the work became particularly clear. What worked well, and when did you need to adjust it?",
            "Give me a concrete example where a strong personal preference shaped how you acted. What effect did your approach have, and what trade-offs did you need to make?",
            "Describe a time when your usual working approach was a clear asset. Was there any part of the situation where you had to deliberately balance or adapt it?",
        ]
        why = (
            f"{trait} is a clearer high-side indication in the candidate's profile. "
            "The question explores how the preference actually appears, the value it "
            "may bring and when situational adjustment matters."
        )
    elif band == "low":
        questions = [
            "Tell me about a situation where the demands required you to work in a way that did not feel entirely natural. How did you recognise that, and what did you do?",
            "Give me a concrete example of when you needed to use an approach you would not normally choose instinctively. What helped you adapt?",
            "Describe a time when the situation required behaviour different from what you would usually prefer. How did you handle it, and what happened?",
        ]
        why = (
            f"{trait} is a clearer low-side indication in the candidate's profile. "
            "The question explores how the person responds when the situation may "
            "require behaviour outside that natural preference."
        )
    else:
        questions = [
            "Describe two similar situations where you chose different ways of responding. What in the context influenced how you approached them?",
            "Tell me about an area where your way of working varies quite a lot depending on the situation. What determines which approach you choose?",
            "Give examples of when you have handled the same type of task in different ways. Which situational signals shaped your behaviour?",
        ]
        why = (
            f"{trait} sits closer to the middle of the candidate's profile. The "
            "question therefore explores situational variation rather than assuming "
            "one strongly preferred behavioural direction."
        )

    return (
        questions[variant],
        why,
        "Listen for concrete situations, personal actions, deliberate choices, "
        "trade-offs and how behaviour changed with the context.",
    )


def _competency_fallback_questions(
    *,
    owner,
    selected_tokens: list[str],
    personality_results: list[dict[str, Any]],
    question_count: int,
    language_code: str,
) -> list[dict[str, Any]]:
    from apps.reports.libraries.personality.competency_framework import (
        build_supporting_personality_evidence,
        competency_label,
        get_competency,
    )

    supporting = (
        build_supporting_personality_evidence(owner, selected_tokens)
        if owner is not None
        else {}
    )

    result_lookup = {
        _normalise_name(item.get("name")): item
        for item in personality_results or []
        if _normalise_name(item.get("name"))
    }

    questions = []

    for index in range(question_count):
        token = selected_tokens[index % len(selected_tokens)]
        competency = get_competency(token) or {}
        label = competency_label(token, language_code)
        rows = list(supporting.get(token) or [])

        if not rows:
            wanted = {
                _normalise_name(name)
                for name in competency.get("evidence_names") or []
            }
            rows = [
                item
                for key, item in result_lookup.items()
                if key in wanted
            ]

        rows_with_sten = [row for row in rows if row.get("sten") is not None]
        strongest = None
        if rows_with_sten:
            strongest = max(
                rows_with_sten,
                key=lambda row: abs(float(row.get("sten")) - 5.5),
            )

        if language_code == "sv":
            if strongest:
                evidence_name = str(strongest.get("name") or "").strip()
                band = _sten_band(strongest.get("sten"))
                if band == "high":
                    question = (
                        f"Berätta om ett konkret tillfälle där {label} var viktigt "
                        "och där ditt naturliga sätt att agera blev en tydlig del av "
                        "hur du hanterade situationen. Vad gjorde du och vilka "
                        "avvägningar behövde du göra?"
                    )
                elif band == "low":
                    question = (
                        f"Berätta om ett konkret tillfälle där {label} ställde krav "
                        "på ett arbetssätt som krävde medveten anpassning från din "
                        "sida. Vad gjorde du och vad lärde du dig?"
                    )
                else:
                    question = (
                        f"Ge två exempel där {label} var viktigt men där du valde "
                        "olika sätt att agera. Vad i situationerna påverkade ditt val?"
                    )
                why = (
                    f"Frågan gäller den valda kompetensen {label} och vinkeln har "
                    f"anpassats utifrån den stödjande personlighetssignalen {evidence_name}. "
                    "Signalen är inte ett direkt kompetensmått och behöver valideras "
                    "med konkret beteendeevidens."
                )
            else:
                question = (
                    f"Berätta om ett konkret tillfälle där {label} var viktigt. "
                    "Vilket ansvar hade du själv, vad gjorde du och vad blev resultatet?"
                )
                why = (
                    f"Frågan samlar beteendeevidens om den valda kompetensen {label}. "
                    "Ingen tydligt mappad stödjande personlighetssignal finns i det "
                    "tillgängliga underlaget, så Talena ska inte hitta på en sådan koppling."
                )
            listen_for = (
                "Lyssna efter tydlig situation, eget ansvar, specifika handlingar, "
                "avvägningar, observerbart resultat och reflektion."
            )
        else:
            if strongest:
                evidence_name = str(strongest.get("name") or "").strip()
                band = _sten_band(strongest.get("sten"))
                if band == "high":
                    question = (
                        f"Tell me about a concrete time when {label} mattered and "
                        "your natural way of responding became an important part of "
                        "how you handled the situation. What did you do, and what "
                        "trade-offs did you need to make?"
                    )
                elif band == "low":
                    question = (
                        f"Tell me about a concrete time when {label} required an "
                        "approach that called for deliberate adaptation from you. "
                        "What did you do, and what did you learn?"
                    )
                else:
                    question = (
                        f"Give me two examples where {label} mattered but you chose "
                        "different ways of responding. What in each situation shaped "
                        "your choice?"
                    )
                why = (
                    f"The question concerns the selected competency {label}, and the "
                    f"angle is adapted using the supporting personality signal {evidence_name}. "
                    "That signal is not a direct competency measure and therefore needs "
                    "validation through concrete behavioural evidence."
                )
            else:
                question = (
                    f"Tell me about a concrete time when {label} mattered. What was "
                    "your own responsibility, what did you do, and what happened?"
                )
                why = (
                    f"The question gathers behavioural evidence about the selected "
                    f"competency {label}. No clearly mapped supporting personality "
                    "signal is available, so Talena should not invent one."
                )
            listen_for = (
                "Listen for a clear situation, personal responsibility, specific "
                "actions, trade-offs, observable outcomes and reflection."
            )

        questions.append(
            {
                "question": question,
                "traits": [token],
                "why": why,
                "listen_for": listen_for,
            }
        )

    return questions


def _fallback_personality_questions(
    *,
    selected_traits: list[str],
    personality_results: list[dict[str, Any]],
    owner=None,
) -> dict[str, Any]:
    """Build an evidence-aware last-resort personality question set."""

    from apps.core.ai import personality_questions as pq
    from apps.processes.interview_config import get_interview_section_config
    from apps.reports.libraries.personality.competency_framework import (
        normalise_competency_tokens,
    )

    language_code = pq.normalize_ai_language(
        pq._personality_questions_language.get()
    )

    traits = [
        str(item or "").strip()
        for item in selected_traits or []
        if str(item or "").strip()
    ]

    question_count = int(
        get_interview_section_config("personality").get("question_count", 8)
        or 8
    )

    competency_tokens = normalise_competency_tokens(traits)
    if competency_tokens:
        return {
            "type": "questions",
            "items": _competency_fallback_questions(
                owner=owner,
                selected_tokens=competency_tokens,
                personality_results=personality_results,
                question_count=question_count,
                language_code=language_code,
            ),
        }

    result_lookup = {
        _normalise_name(item.get("name")): item
        for item in personality_results or []
        if _normalise_name(item.get("name"))
    }

    if not traits:
        ranked = sorted(
            [
                item
                for item in personality_results or []
                if item.get("name") and item.get("sten") is not None
            ],
            key=lambda item: abs(float(item.get("sten")) - 5.5),
            reverse=True,
        )
        traits = [str(item.get("name")).strip() for item in ranked[:6]]

    if not traits:
        raise ValueError("No personality traits are available for the questions.")

    questions = []

    for index in range(question_count):
        trait = traits[index % len(traits)]
        result = result_lookup.get(_normalise_name(trait)) or {}
        sten = result.get("sten")

        if sten is None:
            raise ValueError(
                f"No assessment result is available for selected trait {trait!r}."
            )

        question, why, listen_for = _trait_fallback_text(
            trait=trait,
            band=_sten_band(sten),
            language_code=language_code,
            index=index,
        )

        questions.append(
            {
                "question": question,
                "traits": [trait],
                "why": why,
                "listen_for": listen_for,
            }
        )

    return {"type": "questions", "items": questions}


def install_candidate_question_grounding_policy() -> None:
    """Require candidate-specific assessment grounding for all question sets."""

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
        return str(prompt).rstrip() + _personality_grounding_instruction(
            invitation,
            personality_results,
        )

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
            return str(prompt).rstrip() + _personality_grounding_instruction(
                owner,
                personality_results,
            )

        personality_questions._build_personality_questions_repair_prompt = (
            personality_repair
        )

    personality_questions._build_safe_personality_questions_event = (
        _fallback_personality_questions
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
        return str(prompt).rstrip() + _motivation_grounding_instruction(
            motivation_results
        )

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
        return str(prompt).rstrip() + _cognitive_grounding_instruction(
            cognitive_results
        )

    cognitive_questions.build_cognitive_questions_prompt = cognitive_prompt

    _INSTALLED = True
