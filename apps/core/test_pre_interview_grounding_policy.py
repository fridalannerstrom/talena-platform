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
            "Every item in discussion_guidance.feedback_approach",
            self.policy,
        )
        self.assertIn(
            "concrete interviewer action",
            self.policy,
        )

    def test_policy_rejects_generic_role_only_advice(self):
        self.assertIn(
            "must not replace candidate-specific evidence",
            self.policy,
        )
        self.assertIn(
            "Do not use generic interview best practice",
            self.policy,
        )
        self.assertIn(
            "What supplied evidence about this candidate made me choose this exact focus or conversation adjustment?",
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
        self.assertIn(
            "keep response styles conceptually separate from personality traits, motivation and ability",
            self.policy,
        )
