from django.test import SimpleTestCase

from apps.core.ai.pre_interview_grounding_policy import (
    PROTECTED_PRE_INTERVIEW_GROUNDING,
)


def _normalise_whitespace(value: str) -> str:
    return " ".join(str(value or "").split())


class PreInterviewGroundingPolicyTests(SimpleTestCase):
    def setUp(self):
        self.policy = _normalise_whitespace(
            PROTECTED_PRE_INTERVIEW_GROUNDING
        )

    def test_policy_requires_candidate_specific_evidence(self):
        self.assertIn(
            "Candidate assessment evidence is the basis of the briefing",
            self.policy,
        )
        self.assertIn(
            "Every item in discussion_guidance.interview_focus",
            self.policy,
        )
        self.assertIn(
            "Every item in cautious_interpretations",
            self.policy,
        )
        self.assertIn(
            "discussion_guidance.feedback_approach is not another list of interview topics",
            self.policy,
        )

    def test_feedback_approach_is_about_communication_not_topics(self):
        self.assertIn(
            "explain HOW the interviewer can communicate with this candidate",
            self.policy,
        )
        self.assertIn(
            "tone, directness, pacing, amount of reflection time",
            self.policy,
        )
        self.assertIn(
            "must not repeat discussion_guidance.interview_focus or the 3/3/8 assessment-question topics",
            self.policy,
        )
        self.assertIn(
            "return an empty feedback_approach array rather than filling the section with generic interview advice",
            self.policy,
        )

    def test_response_style_advice_remains_cautious(self):
        self.assertIn(
            "more self-critical presentation",
            self.policy,
        )
        self.assertIn(
            "Do not label the person as humble, insecure or lacking confidence",
            self.policy,
        )
        self.assertIn(
            "more positive self-presentation",
            self.policy,
        )
        self.assertIn(
            "Do not imply dishonesty, manipulation or inflated self-worth",
            self.policy,
        )

    def test_policy_rejects_generic_role_only_advice(self):
        self.assertIn(
            "must not replace candidate-specific evidence",
            self.policy,
        )
        self.assertIn(
            "What supplied evidence about this candidate made me choose this exact focus or conversation adjustment?",
            self.policy,
        )
        self.assertIn(
            "Does this tell the interviewer how to communicate differently with this candidate, rather than merely what topic to discuss?",
            self.policy,
        )
        self.assertIn(
            "would fit most candidates unchanged",
            self.policy,
        )

    def test_policy_preserves_assessment_caution(self):
        self.assertIn(
            "Do not turn high results into automatic strengths or low results into automatic weaknesses",
            self.policy,
        )
        self.assertIn(
            "Do not diagnose, predict guaranteed behaviour",
            self.policy,
        )
