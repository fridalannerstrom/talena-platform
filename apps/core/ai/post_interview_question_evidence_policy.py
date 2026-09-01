from __future__ import annotations

from functools import wraps


_INSTALLED = False

NO_GENERAL_INTERVIEW_NOTES = (
    "No additional general interview notes were added."
)

PROTECTED_QUESTION_EVIDENCE_GUIDANCE = """
QUESTION-SPECIFIC INTERVIEW EVIDENCE RULES

The QUESTION-SPECIFIC INTERVIEW EVIDENCE above contains structured records
with the exact generated interview question and the answer or interviewer
note saved against that question.

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

EVIDENCE PRIORITY AND TRACEABILITY

Question-specific evidence must not become background noise merely because a
large general interview-notes field is also present.

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

Do not force an irrelevant question-specific note into the output merely to
prove it was read. Relevance still matters. However, do not ignore a relevant,
concrete saved answer merely because the same broad topic appears elsewhere in
general interview notes.

Before finalising the post-interview output, silently check: "Did any saved
question-specific answer contain concrete evidence that materially changes or
strengthens the interpretation?" If yes, ensure that evidence is represented
in the relevant synthesis rather than being discarded.

The exact question/answer pairing is evidence provenance and must not be
changed by administrator prompt guidance.
""".strip()


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

    return {
        "general_notes": general_notes,
        "question_evidence": question_evidence,
        "has_evidence": bool(
            general_notes
            or question_evidence.get("has_evidence")
        ),
    }


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

    new_block = f"""
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
