from django.test import SimpleTestCase

from apps.core.ai.prompt_templates import AI_PROMPT_REGISTRY


class TeamAIPromptRegistryTests(SimpleTestCase):
    def test_team_insights_have_independent_swedish_and_english_prompts(self):
        communication = AI_PROMPT_REGISTRY["team_communication_styles"]
        collaboration = AI_PROMPT_REGISTRY["team_collaboration"]

        self.assertEqual(communication["category"], "Teams")
        self.assertEqual(collaboration["category"], "Teams")
        self.assertEqual(set(communication["defaults"]), {"sv", "en"})
        self.assertEqual(set(collaboration["defaults"]), {"sv", "en"})
        self.assertNotEqual(
            communication["defaults"]["en"],
            collaboration["defaults"]["en"],
        )
        self.assertIn("communication styles", communication["defaults"]["en"])
        self.assertIn("collaboration", collaboration["defaults"]["en"])

    def test_prompts_prohibit_individual_claims_and_fabricated_missing_data(self):
        for key in ("team_communication_styles", "team_collaboration"):
            for language in ("sv", "en"):
                prompt = AI_PROMPT_REGISTRY[key]["defaults"][language].lower()
                self.assertTrue(
                    "enskilda personer" in prompt or "individuals" in prompt
                )
                self.assertTrue(
                    "saknade resultat" in prompt or "missing results" in prompt
                )
