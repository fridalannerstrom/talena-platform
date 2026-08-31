from __future__ import annotations

from functools import wraps


_INSTALLED = False


PROTECTED_PRE_INTERVIEW_GROUNDING = """

TALENA CANDIDATE-SPECIFIC INTERVIEW BRIEFING GROUNDING

This is a protected product requirement. The pre-interview briefing must feel
like preparation for this specific candidate, not generic interview guidance
with the candidate's name inserted into it.

REQUIRED GROUNDING BEHAVIOUR

- Candidate assessment evidence is the basis of the briefing. Process purpose,
  role context and other supplied context determine relevance, but must not
  replace candidate-specific evidence as the basis for an insight.
- The overall synthesis must prioritise a small number of concrete patterns,
  tensions, contrasts or uncertainties that are actually present in the
  supplied candidate evidence.
- Every item in purpose_relevant_indications must be traceable to one or more
  candidate-specific evidence sources supplied in the prompt.
- Every item in cautious_interpretations must identify a real candidate-specific
  hypothesis or uncertainty that is useful to validate. Do not create generic
  cautions that would apply to most candidates.
- Every item in discussion_guidance.interview_focus must state a concrete focus
  that follows from this candidate's evidence. It must not merely repeat a
  common interview competency or the role title.
- If the available evidence does not support a candidate-specific conclusion,
  state the uncertainty or evidence gap instead of inventing one.
- Do not turn high results into automatic strengths or low results into
  automatic weaknesses. Preserve the meaning and limitations of the underlying
  assessment evidence.
- Do not diagnose, predict guaranteed behaviour or present assessment
  indications as facts about the person.
- Avoid generic phrases such as "explore strengths and development areas" unless
  the sentence immediately specifies which candidate evidence makes that focus
  relevant.

CANDIDATE-UNIQUENESS CHECK

Before returning each substantive briefing item, silently ask:

"What supplied evidence about this candidate made me choose this exact focus?"

If the answer is only the process purpose, role context, a common interview
practice or wording that would fit most candidates unchanged, rewrite the item
so the candidate's actual evidence materially changes the content.

The administrator guidance still controls tone, wording, prioritisation and
number of items within Talena's protected evidence and output contract.
""".rstrip()


def install_pre_interview_grounding_policy() -> None:
    """Require candidate-specific grounding in pre-interview decision support."""

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import decision_support

    original_prompt = decision_support.build_pre_interview_decision_support_prompt

    @wraps(original_prompt)
    def grounded_prompt(owner, *, language_code=None):
        prompt = original_prompt(owner, language_code=language_code)
        return str(prompt).rstrip() + "\n" + PROTECTED_PRE_INTERVIEW_GROUNDING

    decision_support.build_pre_interview_decision_support_prompt = grounded_prompt
    _INSTALLED = True
