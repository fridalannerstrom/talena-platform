from django.test import SimpleTestCase

from apps.core.ai.pre_interview_grounding_policy import (
    PROTECTED_PRE_INTERVIEW_GROUNDING,
)


class PreInterviewGroundingPolicyTests(SimpleTestCase):
    def test_policy_requires_candidate_specific_evidence(self):
        self.assertIn(
            "Candidate assessment evidence is the basis of the briefing",
            PROTECTED_PRE_INTERVIEW_GROUNDING,
        )
        self.assertIn(
            "Every item in discussion_guidance.interview_focus",
            PROTECTED_PRE_INTERVIEW_GROUNDING,
        )
        self.assertIn(
            "Every item in cautious_interpretations",
            PROTECTED_PRE_INTERVIEW_GROUNDING,
        )

    def test_policy_rejects_generic_role_only_advice(self):
        self.assertIn(
            "must not replace candidate-specific evidence",
            PROTECTED_PRE_INTERVIEW_GROUNDING,
        )
        self.assertIn(
            "What supplied evidence about this candidate made me choose this exact focus?",
            PROTECTED_PRE_INTERVIEW_GROUNDING,
        )
        self.assertIn(
            "would fit most candidates unchanged",
            PROTECTED_PRE_INTERVIEW_GROUNDING,
        )

    def test_policy_preserves_assessment_caution(self):
        self.assertIn(
            "Do not turn high results into automatic strengths or low results into",
            PROTECTED_PRE_INTERVIEW_GROUNDING,
        )
        self.assertIn(
            "Do not diagnose, predict guaranteed behaviour",
            PROTECTED_PRE_INTERVIEW_GROUNDING,
        )
