from django.test import SimpleTestCase

from apps.core.ai.pre_interview_raw_evidence_policy import (
    RAW_ASSESSMENT_SOURCE_LABEL,
    augment_pre_interview_evidence,
)


class PreInterviewRawEvidencePolicyTests(SimpleTestCase):
    def test_raw_results_are_added_before_saved_ai_interpretations(self):
        result = augment_pre_interview_evidence(
            {
                "evidence_text": (
                    "SOURCE: Personality interpretation\n"
                    "STATUS: completed\n"
                    "Interpretation:\nSaved AI summary"
                ),
                "source_names": ["Personality interpretation"],
                "source_count": 1,
                "has_evidence": True,
            },
            raw_assessment_text=(
                "Personality:\n"
                "- Social desirability: sten 2\n"
                "- Networking: sten 9"
            ),
            assessment_type_count=1,
        )

        self.assertTrue(result["has_evidence"])
        self.assertEqual(
            result["source_names"][0],
            RAW_ASSESSMENT_SOURCE_LABEL,
        )
        self.assertEqual(result["source_count"], 2)
        self.assertIn(
            "Normalized raw assessment results",
            result["evidence_text"],
        )
        self.assertIn(
            "Social desirability: sten 2",
            result["evidence_text"],
        )
        self.assertLess(
            result["evidence_text"].index("Social desirability: sten 2"),
            result["evidence_text"].index("Saved AI summary"),
        )

    def test_raw_results_can_supply_evidence_without_saved_ai_content(self):
        result = augment_pre_interview_evidence(
            {
                "evidence_text": "",
                "source_names": [],
                "source_count": 0,
                "has_evidence": False,
            },
            raw_assessment_text="Numerical reasoning:\n- Score: percentile 61",
            assessment_type_count=1,
        )

        self.assertTrue(result["has_evidence"])
        self.assertEqual(
            result["source_names"],
            [RAW_ASSESSMENT_SOURCE_LABEL],
        )
        self.assertIn("percentile 61", result["evidence_text"])

    def test_missing_raw_results_leave_existing_evidence_unchanged(self):
        original = {
            "evidence_text": "Existing evidence",
            "source_names": ["AI Overview"],
            "source_count": 1,
            "has_evidence": True,
        }

        result = augment_pre_interview_evidence(
            original,
            raw_assessment_text="",
            assessment_type_count=0,
        )

        self.assertEqual(result, original)
