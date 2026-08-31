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

COMMUNICATION APPROACH

- discussion_guidance.feedback_approach is NOT another list of interview topics.
  It has a separate job: explain HOW the interviewer can communicate with this
  candidate to obtain a fair, nuanced and useful conversation.
- Do not use feedback_approach to say "discuss", "explore", "ask about" or
  otherwise name subject matter that belongs in interview_focus or the 3/3/8
  assessment-question plan.
- Ground feedback_approach primarily in relevant personality and response-style
  evidence. Use other assessment evidence only when it genuinely changes how
  the conversation should be conducted.
- Each feedback_approach item should connect a candidate-specific signal or
  hypothesis to a concrete interviewer adjustment. The practical adjustment is
  the point of the item.
- Useful adjustments may concern tone, directness, pacing, amount of reflection
  time, how strongly to probe, whether to request concrete examples or
  counterexamples, how to invite nuance, and how to avoid over- or
  under-weighting the candidate's self-presentation.
- When response-style evidence is available, translate it into practical
  communication guidance. Do not merely repeat the technical response-style
  label or raw score.
- Where response-style evidence suggests a more self-critical presentation,
  guidance may recommend creating space for concrete strength examples and
  checking whether the candidate understates their own contribution. Do not
  label the person as humble, insecure or lacking confidence unless independent
  evidence supports that conclusion.
- Where response-style evidence suggests a more positive self-presentation,
  guidance may recommend asking for specific behavioural examples,
  counterexamples or outcomes to add nuance. Do not imply dishonesty,
  manipulation or inflated self-worth.
- Personality preferences may shape the suggested communication style when the
  evidence supports it, but do not turn a trait score into a fixed rule about
  how the person must be spoken to.
- feedback_approach must not repeat discussion_guidance.interview_focus or the
  3/3/8 assessment-question topics. It describes interviewer stance and
  interaction strategy, not what subject matter to cover.
- Generic best practice such as "create an open and supportive climate",
  "listen actively" or "ask follow-up questions" is not sufficient unless the
  item immediately states the candidate-specific reason and adjustment.
- If the evidence does not support any meaningful candidate-specific
  communication adjustment, return an empty feedback_approach array rather than
  filling the section with generic interview advice.

GENERAL CAUTION

- If the available evidence does not support a candidate-specific conclusion or
  a special conversation adjustment, state the uncertainty or evidence gap
  instead of inventing specificity.
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

"What supplied evidence about this candidate made me choose this exact focus
or conversation adjustment?"

For every feedback_approach item, also silently ask:

"Does this tell the interviewer how to communicate differently with this
candidate, rather than merely what topic to discuss?"

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
