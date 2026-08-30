from django.test import SimpleTestCase

from apps.core.ai.post_interview_role_context_policy import (
    install_post_interview_role_context_policy,
)
from apps.core.ai.post_interview_role_context_policy_v2 import (
    install_post_interview_role_context_policy_v2,
)
from apps.core.ai.prompt_templates import AI_PROMPT_REGISTRY


class PostInterviewRoleContextPolicyV2Tests(SimpleTestCase):
    def setUp(self):
        install_post_interview_role_context_policy()
        install_post_interview_role_context_policy_v2()

    def test_role_support_excludes_items_needing_validation(self):
        prompt = AI_PROMPT_REGISTRY[
            "post_interview_supported_indications"
        ]["defaults"]["sv"]

        self.assertIn(
            "behöver diskuteras, verifieras eller utforskas vidare",
            prompt,
        )
        self.assertIn(
            "INTE hemma i Stöd för rollen",
            prompt,
        )
        self.assertIn(
            "Områden att utforska",
            prompt,
        )

    def test_evidence_gaps_is_not_a_second_exploration_section(self):
        definition = AI_PROMPT_REGISTRY[
            "post_interview_remaining_uncertainties"
        ]

        self.assertEqual(
            definition["name"],
            "After interview · Evidence gaps",
        )
        self.assertIn(
            "INTE en andra lista över områden att utforska",
            definition["defaults"]["sv"],
        )
        self.assertIn(
            "NOT a second list of areas to explore",
            definition["defaults"]["en"],
        )
