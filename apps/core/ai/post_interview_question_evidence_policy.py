from __future__ import annotations

from functools import wraps


_INSTALLED = False

NO_GENERAL_INTERVIEW_NOTES = (
    "No additional general interview notes were added."
)

_ADMIN_DEFAULT_MARKER = "QUESTION-SPECIFIC INTERVIEW EVIDENCE IN AFTER INTERVIEW"

_ADMIN_DEFAULT_QUESTION_EVIDENCE_GUIDANCE = {
    "sv": """

FRÅGESPECIFIKT INTERVJUUNDERLAG I EFTER INTERVJU

Sparade svar och anteckningar som hör till en specifik intervjufråga är
intervjuunderlag på samma sätt som den separata fritextrutan
Intervjuunderlag.

När frågespecifikt intervjuunderlag finns:

- använd den exakta frågan som kontext när svaret eller anteckningen tolkas
- väg in konkreta beteendeexempel när de är relevanta för syntesen
- låt inte frågespecifika svar försvinna bara för att annat underlag är längre
- skriv inte att intervjuunderlag saknas
- om den separata fritextrutan är tom får du endast beskriva att ytterligare
  allmänna fritextanteckningar saknas
- context note ska tydliggöra att frågespecifikt intervjuunderlag användes

Ett sparat svar eller en anteckning kan vara kandidatens svar,
intervjuarens sammanfattning eller observation. Presentera det därför inte
automatiskt som ett ordagrant kandidatcitat.
""".strip(),
    "en": """

QUESTION-SPECIFIC INTERVIEW EVIDENCE IN AFTER INTERVIEW

Saved answers and notes attached to a specific interview question are
interview evidence in the same way as the separate general Interview notes
field.

When question-specific interview evidence is available:

- use the exact question as context when interpreting the saved answer or note
- incorporate concrete behavioural examples when they are relevant to the synthesis
- do not let question-specific answers disappear merely because other evidence is longer
- do not state that interview evidence is missing
- if the separate general notes field is empty, only state that additional general
  free-text interview notes were not supplied
- the context note should make clear that question-specific interview evidence was used

A saved answer or note may contain a candidate answer, an interviewer summary
or an observation. Do not automatically present it as a verbatim candidate quote.
""".strip(),
}


PROTECTED_QUESTION_EVIDENCE_GUIDANCE = """
QUESTION-SPECIFIC INTERVIEW EVIDENCE RULES

The QUESTION-SPECIFIC INTERVIEW EVIDENCE above contains structured records
with the exact generated interview question and the answer or interviewer
note saved against that question.

Question-specific saved answers/notes ARE interview evidence. They are not a
secondary metadata source and they do not become "missing interview evidence"
merely because the separate general Interview notes field is empty.

This is a protected evidence relationship:

- Always interpret a saved answer/note in the context of its exact question.
- Never detach a saved answer/note from its question and infer that it answered
  a different topic.
- Preserve the distinction between the question asked and the text saved by the
  interviewer.
- The field saved_answer_or_note may contain a candidate answer, an interviewer
  summary, an observation, or a mixture of these. Do not automatically present
  it as a verbatim candidate statement.
- Do not assume that a saved note fully answers the question merely because it
  is attached to it. Treat incomplete notes as incomplete evidence.
- When a question-specific note provides the evidence for an interpretation,
  use the question context to determine what the note can and cannot support.
- General interview notes and question-specific evidence are complementary
  sources. Do not silently merge them into a single supposed candidate quote.
- Do not invent an answer for any generated question without a saved note.

INTERVIEW EVIDENCE AVAILABILITY

The INTERVIEW EVIDENCE STATUS block above is authoritative for whether
interview evidence exists.

- If Question-specific interview evidence is AVAILABLE, never say that
  interview evidence, interview material, candidate examples or interview
  input is entirely missing or unavailable.
- If General interview notes are NOT PROVIDED while question-specific evidence
  is AVAILABLE, you may only say that additional general free-text interview
  notes were not provided.
- The context_note must accurately name question-specific interview evidence
  as a source whenever it is available.
- Evidence gaps may still describe unanswered questions or missing examples,
  but must not erase or deny interview evidence that was actually supplied.

EVIDENCE PRIORITY AND TRACEABILITY

Question-specific evidence must not become background noise merely because a
large general interview-notes field or a large amount of assessment evidence
is also present.

When a saved question answer/note contains concrete behavioural evidence that
is materially relevant to an assessment indication, process-context area or
post-interview interpretation:

- actively consider that evidence during the synthesis
- prefer the concrete behavioural detail over a vague or generic statement
  about the same theme
- retain enough distinguishing detail about the action, situation, condition
  or outcome for the user to understand which interview evidence supports the
  interpretation
- use that evidence in the most appropriate output section, such as the overall
  synthesis, Role support, Additional nuance or Areas to explore

When question-specific evidence is the ONLY interview evidence and at least one
saved answer/note contains a relevant concrete behavioural example, the final
post-interview output MUST surface at least one distinguishing concrete detail
from that evidence in the overall synthesis or another substantive evidence
section. A generic restatement of the assessment profile is not sufficient.

Do not force an irrelevant question-specific note into the output merely to
prove it was read. Relevance still matters. If every saved question note is
clearly irrelevant to the available assessment/process themes, do not invent a
connection. In that exceptional case, the context_note must still state that
question-specific interview evidence was available but did not materially
change the synthesis.

Before finalising the post-interview output, silently check:

1. "Did any saved question-specific answer contain concrete evidence that
   materially changes, strengthens or nuances the interpretation?"
2. "If question-specific evidence exists, have I avoided incorrectly saying
   that interview evidence is missing?"
3. "Does the context note accurately describe which interview evidence sources
   were actually available?"

If the answer to any applicable check is no, revise the output before returning it.

The exact question/answer pairing and the fact that question-specific notes
count as interview evidence are protected evidence provenance. Administrator
prompt guidance may control interpretation, emphasis and wording but must not
change those facts.
""".strip()


def _install_admin_default_question_evidence_guidance() -> None:
    """Keep Talena's reset/default post-interview admin prompt aligned with #164."""

    from apps.core.ai.prompt_templates import AI_PROMPT_REGISTRY

    registry_item = AI_PROMPT_REGISTRY.get(
        "post_interview_decision_support"
    )

    if not isinstance(registry_item, dict):
        return

    defaults = registry_item.get("defaults")
    if not isinstance(defaults, dict):
        return

    for language, addition in _ADMIN_DEFAULT_QUESTION_EVIDENCE_GUIDANCE.items():
        current = str(defaults.get(language) or "").strip()

        if _ADMIN_DEFAULT_MARKER in current:
            continue

        defaults[language] = (
            f"{current}\n\n{addition}".strip()
            if current
            else addition
        )


def get_post_interview_note_evidence(owner) -> dict:
    """Return general notes plus structured question-level interview evidence."""

    general_notes = str(
        getattr(owner, "interview_notes", "")
        or ""
    ).strip()

    if general_notes == NO_GENERAL_INTERVIEW_NOTES:
        general_notes = ""

    # Keep the processes import lazy so core AI startup remains acyclic.
    from apps.processes.interview_question_evidence import (
        build_interview_question_evidence,
    )

    question_evidence = build_interview_question_evidence(owner)
    has_question_evidence = bool(
        question_evidence.get("has_evidence")
    )

    return {
        "general_notes": general_notes,
        "has_general_notes": bool(general_notes),
        "question_evidence": question_evidence,
        "has_question_evidence": has_question_evidence,
        "has_evidence": bool(
            general_notes
            or has_question_evidence
        ),
    }


def _build_evidence_status_block(
    *,
    general_notes: str,
    question_evidence: dict,
) -> str:
    question_count = int(
        question_evidence.get("count") or 0
    )
    has_question_evidence = bool(
        question_evidence.get("has_evidence")
    )

    return "\n".join([
        "INTERVIEW EVIDENCE STATUS",
        (
            "General interview notes: AVAILABLE"
            if general_notes
            else "General interview notes: NOT PROVIDED"
        ),
        (
            "Question-specific interview evidence: "
            f"AVAILABLE ({question_count} saved answer/note record(s))"
            if has_question_evidence
            else "Question-specific interview evidence: NOT PROVIDED"
        ),
        (
            "Overall interview evidence: AVAILABLE"
            if general_notes or has_question_evidence
            else "Overall interview evidence: NOT PROVIDED"
        ),
    ])


def _replace_interview_evidence_block(
    prompt: str,
    *,
    effective_general_notes: str,
    general_notes: str,
    question_evidence: dict,
) -> str:
    old_block = (
        "INTERVIEW NOTES AND CANDIDATE EXAMPLES\n"
        f"{effective_general_notes}"
    )

    question_text = (
        str(question_evidence.get("text") or "").strip()
        or "No question-specific answers or notes were saved."
    )

    evidence_status = _build_evidence_status_block(
        general_notes=general_notes,
        question_evidence=question_evidence,
    )

    new_block = f"""
{evidence_status}

GENERAL INTERVIEW NOTES AND CANDIDATE EXAMPLES
{general_notes or NO_GENERAL_INTERVIEW_NOTES}

QUESTION-SPECIFIC INTERVIEW EVIDENCE
{question_text}

{PROTECTED_QUESTION_EVIDENCE_GUIDANCE}
""".strip()

    if old_block in prompt:
        return prompt.replace(
            old_block,
            new_block,
            1,
        )

    # Defensive fallback for future prompt refactors. The evidence still reaches
    # the model even if the surrounding label changes.
    return (
        str(prompt).rstrip()
        + "\n\n"
        + new_block
    )


def install_post_interview_question_evidence_policy() -> None:
    """
    Make exact interview question + saved answer pairs available to After interview.

    Question-specific notes are valid interview evidence even when the separate
    free-text Interview notes field is empty.
    """

    global _INSTALLED
    if _INSTALLED:
        return

    _install_admin_default_question_evidence_guidance()

    from apps.core.ai import decision_support

    original_prompt = (
        decision_support.build_post_interview_decision_support_prompt
    )
    original_stream = (
        decision_support.stream_post_interview_decision_support
    )

    @wraps(original_prompt)
    def prompt_with_question_evidence(
        owner,
        *,
        language_code=None,
    ):
        note_evidence = get_post_interview_note_evidence(owner)

        if not note_evidence["has_evidence"]:
            raise ValueError(
                "Interview notes or saved interview question answers must be "
                "added before post-interview decision support can be generated."
            )

        general_notes = note_evidence["general_notes"]
        effective_general_notes = (
            general_notes
            or NO_GENERAL_INTERVIEW_NOTES
        )

        original_value = getattr(
            owner,
            "interview_notes",
            "",
        )

        if not general_notes:
            # The legacy builder historically requires the free-text notes field.
            # Supply an in-memory placeholder only while it builds the prompt.
            # Nothing is written to the database.
            owner.interview_notes = effective_general_notes

        try:
            prompt = original_prompt(
                owner,
                language_code=language_code,
            )
        finally:
            if not general_notes:
                owner.interview_notes = original_value

        return _replace_interview_evidence_block(
            prompt,
            effective_general_notes=effective_general_notes,
            general_notes=general_notes,
            question_evidence=note_evidence[
                "question_evidence"
            ],
        )

    @wraps(original_stream)
    def stream_with_question_evidence(
        *,
        owner,
        language_code=None,
    ):
        note_evidence = get_post_interview_note_evidence(owner)

        if not note_evidence["has_evidence"]:
            raise ValueError(
                "Interview notes or saved interview question answers must be "
                "added before post-interview decision support can be generated."
            )

        if note_evidence["general_notes"]:
            yield from original_stream(
                owner=owner,
                language_code=language_code,
            )
            return

        # The legacy stream performs the same free-text-notes guard before it
        # calls the now-patched prompt builder. Satisfy that guard in memory so
        # question-level evidence can stand on its own. Never persist it.
        original_value = getattr(
            owner,
            "interview_notes",
            "",
        )
        owner.interview_notes = NO_GENERAL_INTERVIEW_NOTES

        try:
            yield from original_stream(
                owner=owner,
                language_code=language_code,
            )
        finally:
            owner.interview_notes = original_value

    decision_support.build_post_interview_decision_support_prompt = (
        prompt_with_question_evidence
    )
    decision_support.stream_post_interview_decision_support = (
        stream_with_question_evidence
    )

    _INSTALLED = True
