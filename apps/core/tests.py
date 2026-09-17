from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.motivation_interpretation import (
    build_motivation_evidence_text,
    extract_motivation_results,
)
from apps.core.ai.decision_support import (
    POST_INTERVIEW_CONTENT_BLOCK_KEYS,
    apply_post_interview_decision_support_event,
    create_empty_post_interview_decision_support,
)
from apps.core.ai.post_interview_role_context_policy import (
    install_post_interview_role_context_policy,
)
from apps.core.ai.prompt_templates import AI_PROMPT_REGISTRY


class MotivationAIEvidenceTests(SimpleTestCase):
    def setUp(self):
        # Samma profil som kandidaten vi jämförde med SOVA-rapporten.
        self.expected_scores = {
            "Affiliation": 4,
            "Customer Service": 4,
            "Work-life Balance": 1,
            "People Development": 4,
            "Stability": 1,
            "Authority": 3,
            "Acquisition": 3,
            "Autonomy": 1,
            "Recognition": 1,
            "Making a Difference": 3,
            "Achievement": 4,
            "Quality": 2,
            "Learning": 2,
            "Ethics": 2,
            "Commercial Value": 4,
            "Curiosity": 1,
            "Creativity": 2,
            "Enjoyment": 4,
            "Variety": 5,
            "Risk": 3,
        }

        self.invitation = SimpleNamespace(
            sova_activities=[
                {
                    "activity": "Motivation Questionnaire",
                    "competencies": [
                        {
                            "competency": name,
                            "stive_rounded": score,
                        }
                        for name, score in self.expected_scores.items()
                    ],
                }
            ]
        )

    def test_extracts_correct_motivation_scores_for_ai(self):
        results = extract_motivation_results(
            self.invitation
        )

        actual_scores = {
            item["name"]: item["score"]
            for item in results
        }

        self.assertEqual(
            actual_scores,
            self.expected_scores,
        )

    def test_ai_evidence_contains_correct_scores(self):
        results = extract_motivation_results(
            self.invitation
        )

        evidence = build_motivation_evidence_text(
            results
        )

        for name, score in self.expected_scores.items():
            self.assertIn(
                f"{name}: STIVE {score} of 5",
                evidence,
            )

    def test_ai_receives_correct_scale_interpretation(self):
        results = extract_motivation_results(
            self.invitation
        )

        evidence = build_motivation_evidence_text(
            results
        )

        self.assertIn(
            "A higher score means that the factor is more likely to be "
            "a prominent source of motivation",
            evidence,
        )

        self.assertIn(
            "A lower score means that the factor is less central",
            evidence,
        )

        self.assertIn(
            "A low score does NOT mean poor performance.",
            evidence,
        )

        self.assertIn(
            "A low score does NOT mean low ability or competence.",
            evidence,
        )

    def test_ai_receives_factor_definitions(self):
        results = extract_motivation_results(
            self.invitation
        )

        evidence = build_motivation_evidence_text(
            results
        )

        self.assertIn(
            "Affiliation: STIVE 4 of 5",
            evidence,
        )
        self.assertIn(
            "Meaning: Social interaction, support and a sense of belonging at work.",
            evidence,
        )

        self.assertIn(
            "Work-life Balance: STIVE 1 of 5",
            evidence,
        )
        self.assertIn(
            "Score meaning: Less central motivational driver.",
            evidence,
        )

        self.assertIn(
            "Variety: STIVE 5 of 5",
            evidence,
        )
        self.assertIn(
            "Score meaning: More prominent motivational driver.",
            evidence,
        )


class PostInterviewRoleContextPolicyTests(SimpleTestCase):
    def setUp(self):
        install_post_interview_role_context_policy()

    def test_role_support_prompt_is_exposed_to_admin(self):
        definition = AI_PROMPT_REGISTRY[
            "post_interview_supported_indications"
        ]

        self.assertEqual(
            definition["name"],
            "After interview · Role support",
        )
        self.assertIn(
            "processkontext",
            definition["defaults"]["sv"].lower(),
        )
        self.assertIn(
            "process context",
            definition["defaults"]["en"].lower(),
        )

    def test_areas_to_explore_prompt_is_role_context_focused(self):
        definition = AI_PROMPT_REGISTRY[
            "post_interview_contradictions"
        ]

        self.assertEqual(
            definition["name"],
            "After interview · Areas to explore",
        )
        self.assertIn(
            "roll- eller kontextområde",
            definition["defaults"]["sv"].lower(),
        )
        self.assertIn(
            "role or context area",
            definition["defaults"]["en"].lower(),
        )

    def test_next_steps_stays_decision_support_not_decision(self):
        definition = AI_PROMPT_REGISTRY[
            "post_interview_suggested_follow_up"
        ]

        self.assertEqual(
            definition["name"],
            "After interview · Next steps",
        )
        self.assertIn(
            "anställning",
            definition["defaults"]["sv"].lower(),
        )
        self.assertIn(
            "hiring",
            definition["defaults"]["en"].lower(),
        )

class PostInterviewContentBlockTests(SimpleTestCase):
    def test_all_after_interview_blocks_have_admin_prompts(self):
        for key in POST_INTERVIEW_CONTENT_BLOCK_KEYS:
            self.assertIn(key, AI_PROMPT_REGISTRY)
            definition = AI_PROMPT_REGISTRY[key]
            self.assertEqual(definition["category"], "After interview")
            self.assertIn("sv", definition["defaults"])
            self.assertIn("en", definition["defaults"])

    def test_content_blocks_are_part_of_saved_result_contract(self):
        result = create_empty_post_interview_decision_support(
            SimpleNamespace()
        )

        self.assertEqual(
            set(result["content_blocks"]),
            set(POST_INTERVIEW_CONTENT_BLOCK_KEYS),
        )

        apply_post_interview_decision_support_event(
            result,
            {
                "type": "content_blocks",
                "blocks": {
                    key: f"Generated {key}"
                    for key in POST_INTERVIEW_CONTENT_BLOCK_KEYS
                },
            },
        )

        self.assertEqual(
            result["content_blocks"]["overall_picture"],
            "Generated overall_picture",
        )
        self.assertEqual(
            result["content_blocks"]["test_results_candidate"],
            "Generated test_results_candidate",
        )

