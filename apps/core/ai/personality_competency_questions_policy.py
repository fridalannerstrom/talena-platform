from __future__ import annotations

from functools import wraps
from typing import Any

from apps.reports.libraries.personality.competency_framework import (
    build_supporting_personality_evidence,
    competency_label,
    get_competency,
    normalise_competency_tokens,
    parse_competency_token,
)


_INSTALLED = False


COMPETENCY_QUESTIONS_DEFAULT_SV = """
UPPGIFT

Skapa beteendebaserade intervjufrågor utifrån de kompetenser som
användaren har valt i Sovas 38-kompetensramverk.

Frågorna ska hjälpa intervjuaren att samla konkret beteendeevidens om
hur personen har agerat i relevanta situationer. De ska inte användas
för att påstå att personlighetsresultatet i sig bevisar kompetens.


KOMPETENSRAMVERK

Talena tillhandahåller namn och definition för varje vald kompetens.
Använd den tillhandahållna definitionen som den styrande betydelsen av
kompetensen. Hitta inte på alternativa kompetensdefinitioner eller
sammansatta kompetenser.


PERSONLIGHETSEVIDENS

Talena kan också tillhandahålla personlighetsresultat som är relevanta
som stödjande kontext för den valda kompetensen.

Dessa signaler är INTE ett direkt kompetensresultat och får inte beskrivas
som ett kompetensbetyg. Ett STEN-resultat på exempelvis Building Networks
är inte automatiskt samma sak som ett resultat på kompetensen Networking.

Använd personlighetsresultaten för att välja relevanta vinklar att utforska,
inte för att dra slutsatsen att personen har hög eller låg kompetens.

Om ingen relevant personlighetsindikator finns för en vald kompetens,
skapa ändå en välgrundad beteendefråga utifrån kompetensdefinitionen och
tillgänglig processkontext.


FRÅGESTIL

Använd öppna, beteendebaserade frågor som ber om konkreta exempel från
verkliga situationer.

Använd STAR-logiken som stöd för frågedesign och lyssningsvägledning:

- Situation: vilket sammanhang eller problem personen befann sig i
- Task: vilket mål, ansvar eller uppgift personen hade
- Action: vad personen själv faktiskt gjorde
- Results: vad som hände och vad personen lärde sig

Huvudfrågan behöver inte mekaniskt nämna alla fyra STAR-delar. Formulera
den naturligt och använd "Vad du ska lyssna efter" för att hjälpa
intervjuaren samla tillräckligt konkret evidens.

Undvik ledande frågor och formuleringar som avslöjar kandidatens testpoäng.


FÖRDELNING AV FRÅGOR

Talena bestämmer det exakta antalet frågor på produktnivå.

Fördela frågorna meningsfullt över de valda kompetenserna. Varje vald
kompetens ska normalt förekomma i minst en fråga.

Om bara en eller två kompetenser är valda, skapa flera olika och
icke-upprepande beteendevinklar på dessa kompetenser.

Kombinera endast kompetenser i samma fråga när kombinationen är begriplig
och relevant. Blanda inte områden bara för att minska antalet frågor.


VARFÖR DETTA ÄR VIKTIGT

För varje fråga, förklara kort vilken typ av ytterligare evidens frågan
hjälper intervjuaren att samla. Beskriv inte förklaringen som ett bevis på
kompetens eller lämplighet.


VAD DU SKA LYSSNA EFTER

Beskriv konkret vad intervjuaren kan uppmärksamma i svaret, exempelvis:

- tydlig situation och eget ansvar
- specifika handlingar och beslut
- prioriteringar eller avvägningar
- hur andra människor involverades
- hinder och hur de hanterades
- observerbart resultat
- reflektion, återkoppling och lärande

Undvik vaga formuleringar som enbart säger att intervjuaren ska lyssna
efter "god kompetens".


PROCESSENS SYFTE OCH KONTEXT

Använd processens syfte och faktisk processkontext när det är relevant.
Hitta inte på rollkrav, arbetsuppgifter, erfarenhet eller organisatoriska
förhållanden som inte finns i underlaget.


SPRÅK OCH TON

Skriv professionellt, naturligt och praktiskt. Frågorna ska fungera i en
verklig intervju och vara begripliga utan psykometrisk kunskap.

Behandla assessment-resultat som indikationer och hypoteser. Gör inte
slutliga rekryteringsbeslut och diagnostisera inte kandidaten.


KONTEXTNOTERING

Förklara kort att frågorna bygger på valda kompetenser, deras definitioner,
tillgänglig processkontext och, där relevant, stödjande personlighetsdata.
Var tydlig med att stödjande personlighetsdata inte är ett direkt
kompetensresultat.
""".strip()


COMPETENCY_QUESTIONS_DEFAULT_EN = """
TASK

Create behavioural interview questions based on the competencies selected
by the user from Sova's 38-competency framework.

The questions should help the interviewer gather concrete behavioural
evidence about how the person has acted in relevant situations. Do not use
personality results as proof of competence.


COMPETENCY FRAMEWORK

Talena supplies the name and definition of each selected competency. Treat
the supplied definition as the controlling meaning of that competency. Do
not invent alternative definitions or composite competencies.


PERSONALITY EVIDENCE

Talena may also supply personality results that are relevant as supporting
context for a selected competency.

These signals are NOT a direct competency result and must not be described
as a competency rating. For example, a STEN result for Building Networks is
not automatically the same as a result for the Networking competency.

Use personality results to choose useful angles to explore, not to conclude
that the person has high or low competence.

When no relevant personality signal exists for a selected competency, still
create a sound behavioural question from the competency definition and any
available process context.


QUESTION STYLE

Use open behavioural questions that ask for concrete examples from real
situations.

Use STAR as a guide to question design and listening guidance:

- Situation: the context or challenge
- Task: the person's objective, responsibility or task
- Action: what the person actually did
- Results: what happened and what the person learned

The main question does not need to mechanically mention all four STAR parts.
Write naturally and use the listen_for field to help the interviewer gather
sufficiently concrete evidence.

Avoid leading questions and wording that reveals assessment scores.


QUESTION DISTRIBUTION

Talena controls the exact question count as a protected product rule.

Distribute the questions meaningfully across the selected competencies. Each
selected competency should normally be represented in at least one question.

When only one or two competencies are selected, create several distinct,
non-repetitive behavioural angles on those competencies.

Only combine competencies in one question when the combination is coherent
and relevant. Do not combine unrelated areas merely to reduce question count.


WHY THIS MATTERS

For each question, briefly explain what kind of additional evidence the
question helps the interviewer gather. Do not present the explanation as
proof of competence or suitability.


WHAT TO LISTEN FOR

Describe concrete evidence the interviewer can notice, such as:

- a clear situation and personal responsibility
- specific actions and decisions
- priorities or trade-offs
- how other people were involved
- obstacles and how they were handled
- observable outcomes
- reflection, feedback and learning

Avoid vague instructions that merely say to listen for "good competence".


PROCESS PURPOSE AND CONTEXT

Use the selected purpose and actual process context where relevant. Do not
invent role requirements, job tasks, candidate experience or organisational
conditions that are not supplied.


LANGUAGE AND TONE

Write professionally, naturally and practically. Questions should work in a
real interview and be understandable without psychometric knowledge.

Treat assessment results as indications and hypotheses. Do not make final
hiring decisions and do not diagnose the candidate.


CONTEXT NOTE

Briefly explain that the questions were based on selected competencies,
their definitions, supplied process context and, where relevant, supporting
personality data. Make clear that supporting personality data is not a direct
competency result.
""".strip()


def _has_competency_selection(owner) -> bool:
    return bool(
        normalise_competency_tokens(
            getattr(owner, "selected_personality_traits", None) or []
        )
    )


def _format_competency_input(owner, selected_tokens: list[str], language_code: str) -> str:
    evidence = build_supporting_personality_evidence(
        owner,
        selected_tokens,
    )
    blocks = []

    for token in selected_tokens:
        item = get_competency(token)
        if not item:
            continue

        rows = evidence.get(token) or []
        if rows:
            evidence_lines = []
            for row in rows:
                score_bits = []
                if row.get("sten") is not None:
                    score_bits.append(f"STEN {row['sten']} of 10")
                if row.get("percentile") is not None:
                    score_bits.append(f"percentile {row['percentile']}")
                suffix = f" ({', '.join(score_bits)})" if score_bits else ""
                evidence_lines.append(f"  - {row['name']}{suffix}")
            evidence_text = "\n".join(evidence_lines)
        else:
            evidence_text = "  - No mapped supporting personality signal is available."

        blocks.append(
            "\n".join([
                f"TECHNICAL TOKEN: {token}",
                f"COMPETENCY: {item['name']}",
                f"DISPLAY LABEL: {competency_label(item['name'], language_code)}",
                f"DOMAIN: {item['domain']}",
                f"DEFINITION: {item['definition']}",
                "SUPPORTING PERSONALITY EVIDENCE:",
                evidence_text,
            ])
        )

    return "\n\n".join(blocks)


def _build_competency_prompt(
    *,
    owner,
    personality_results: list[dict[str, Any]],
    language_code: str,
) -> str:
    from apps.core.ai import personality_questions as pq
    from apps.core.ai import prompt_templates

    language_code = pq.normalize_ai_language(language_code)
    selected_tokens = normalise_competency_tokens(
        getattr(owner, "selected_personality_traits", None) or []
    )

    if not selected_tokens:
        raise ValueError("No competency selection is available for personality questions.")

    shared_context = pq.build_shared_ai_context(owner)
    candidate = shared_context["candidate"]
    question_count = pq.get_personality_question_count(selected_tokens)

    admin_instructions = prompt_templates.get_ai_prompt_instructions(
        key="personality_competency_questions",
        language=language_code,
    )

    competency_input = _format_competency_input(
        owner,
        selected_tokens,
        language_code,
    )

    selected_tokens_text = "\n".join(
        f"- {token}"
        for token in selected_tokens
    )

    return f"""
TALENA INPUT DATA

CANDIDATE
Name: {candidate.first_name} {candidate.last_name}

SELECTED PROCESS PURPOSE
Purpose: {shared_context["purpose_label"]}

PROCESS CONTEXT
{shared_context["context_text"] or "No additional process context supplied."}

QUESTION BASIS
COMPETENCIES

SELECTED COMPETENCIES AND SUPPORTING EVIDENCE
{competency_input}

IMPORTANT EVIDENCE BOUNDARY
The supporting personality rows above are contextual personality signals.
They are not direct competency scores. Sova's flat personality payload can
contain several report outputs with duplicate display names and no row-level
report provenance. Do not aggregate these rows into a competency score and
do not describe them as a measured level of the selected competency.

EXPLICIT USER-SELECTED TECHNICAL TOKENS
{selected_tokens_text}

ADMINISTRATOR AI GUIDANCE
{admin_instructions}

TALENA PROTECTED PRODUCT REQUIREMENTS
- Return exactly {question_count} complete question objects.
- Preserve the user's selected competency tokens exactly.
- Every selected competency token must appear in at least one question's
  traits array.
- Do not add personality traits or competencies that the user did not select.
- When one competency is selected, create {question_count} distinct angles
  rather than repeating the same question.

OUTPUT LANGUAGE
{pq.get_ai_language_instruction(language_code)}

Translate user-facing question, why, listen_for and context-note text.
Do NOT translate or alter strings beginning with "competency::" inside
technical selected_traits or traits arrays.

STREAMING FORMAT
Return newline-delimited JSON (NDJSON). Every JSON object must be on one
single line. Do not use Markdown or code fences. Do not add text outside the
JSON objects.

REQUIRED EVENT STRUCTURE

1. META
{{"type":"meta","title":"Personality questions","label":"AI-supported questions"}}

2. SUGGESTED TRAITS
Competency mode uses an explicit user selection. Return an empty list:
{{"type":"suggested_traits","items":[]}}

3. SELECTED TRAITS
Return exactly the selected technical tokens supplied above:
{{"type":"selected_traits","items":["competency::Competency name"]}}

4. QUESTIONS
Return exactly {question_count} objects. Every object must contain:
- question
- traits
- why
- listen_for

The traits array may contain only the exact selected competency tokens.

{{"type":"questions","items":[{{"question":"Question text","traits":["competency::Competency name"],"why":"Why this matters","listen_for":"What to listen for"}}]}}

5. CONTEXT NOTE
{{"type":"context_note","text":"Brief explanation of evidence and context used."}}

6. DONE
{{"type":"done"}}
""".strip()


def _build_competency_repair_prompt(
    *,
    owner,
    personality_results: list[dict[str, Any]],
    selected_traits: list[str],
) -> str:
    from apps.core.ai import personality_questions as pq
    from apps.core.ai import prompt_templates

    language_code = pq.normalize_ai_language(
        pq._personality_questions_language.get()
    )
    selected_tokens = normalise_competency_tokens(selected_traits)
    if not selected_tokens:
        selected_tokens = normalise_competency_tokens(
            getattr(owner, "selected_personality_traits", None) or []
        )

    admin_instructions = prompt_templates.get_ai_prompt_instructions(
        key="personality_competency_questions",
        language=language_code,
    )
    shared_context = pq.build_shared_ai_context(owner)
    question_count = pq.get_personality_question_count(selected_tokens)
    competency_input = _format_competency_input(
        owner,
        selected_tokens,
        language_code,
    )
    selected_tokens_text = "\n".join(
        f"- {token}"
        for token in selected_tokens
    )

    return f"""
The previous competency-based personality questions response did not contain
a technically valid questions event.

CANDIDATE
Name: {shared_context["candidate_name"]}

PROCESS PURPOSE
{shared_context["purpose_label"]}

PROCESS CONTEXT
{shared_context["context_text"] or "No additional process context supplied."}

SELECTED COMPETENCIES
{competency_input}

SELECTED TECHNICAL TOKENS
{selected_tokens_text}

ADMINISTRATOR AI GUIDANCE
{admin_instructions}

TECHNICAL REPAIR TASK
Return exactly {question_count} complete question objects in exactly one JSON
object on one line:

{{"type":"questions","items":[{{"question":"Question text","traits":["competency::Competency name"],"why":"Why this matters","listen_for":"What to listen for"}}]}}

Every selected technical token must be represented in at least one traits
array. traits may contain only the selected technical tokens above.

Supporting personality evidence is not a direct competency score. Do not
turn it into one or reveal raw assessment values in the question text.

{pq.get_ai_language_instruction(language_code)}

Do not use Markdown. Do not use code fences. Do not add explanatory text
outside the JSON object.
""".strip()


def install_personality_competency_questions_policy() -> None:
    """Add competency-based personality questions without breaking trait mode."""

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import personality_questions as pq
    from apps.core.ai import prompt_templates

    prompt_templates.AI_PROMPT_REGISTRY.setdefault(
        "personality_competency_questions",
        {
            "name": "Personality · Competency-based interview questions",
            "category": "Personality",
            "description": (
                "Controls interview questions created from selected competencies "
                "in the 38-competency framework."
            ),
            "defaults": {
                "sv": COMPETENCY_QUESTIONS_DEFAULT_SV,
                "en": COMPETENCY_QUESTIONS_DEFAULT_EN,
            },
        },
    )

    original_normalise_selected_traits = pq.normalise_selected_traits
    original_build_prompt = pq.build_personality_questions_prompt
    original_repair_prompt = pq._build_personality_questions_repair_prompt

    @wraps(original_normalise_selected_traits)
    def normalise_selected_traits(*, selected_traits, available_results):
        raw_items = [
            str(item or "").strip()
            for item in selected_traits or []
            if str(item or "").strip()
        ]
        competency_items = [
            item
            for item in raw_items
            if parse_competency_token(item)
        ]

        if competency_items:
            # Competency and trait selections are intentionally mutually exclusive.
            if len(competency_items) != len(raw_items):
                return []
            return normalise_competency_tokens(competency_items)

        return original_normalise_selected_traits(
            selected_traits=selected_traits,
            available_results=available_results,
        )

    @wraps(original_build_prompt)
    def build_personality_questions_prompt(
        invitation,
        personality_results,
        *,
        language_code=None,
    ):
        if _has_competency_selection(invitation):
            resolved_language = pq.normalize_ai_language(
                language_code or pq._personality_questions_language.get()
            )
            return _build_competency_prompt(
                owner=invitation,
                personality_results=personality_results,
                language_code=resolved_language,
            )

        return original_build_prompt(
            invitation,
            personality_results,
            language_code=language_code,
        )

    @wraps(original_repair_prompt)
    def build_personality_questions_repair_prompt(
        *,
        owner,
        personality_results,
        selected_traits,
    ):
        if (
            _has_competency_selection(owner)
            or normalise_competency_tokens(selected_traits)
        ):
            return _build_competency_repair_prompt(
                owner=owner,
                personality_results=personality_results,
                selected_traits=selected_traits,
            )

        return original_repair_prompt(
            owner=owner,
            personality_results=personality_results,
            selected_traits=selected_traits,
        )

    pq.normalise_selected_traits = normalise_selected_traits
    pq.build_personality_questions_prompt = build_personality_questions_prompt
    pq._build_personality_questions_repair_prompt = (
        build_personality_questions_repair_prompt
    )

    _INSTALLED = True
