from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.core.ai.prompt_templates import (
    get_ai_prompt_definition,
    get_default_ai_prompt,
)
from apps.processes.models import AIPromptTemplate


class AdminAIPromptRestoreTests(TestCase):
    prompt_key = "candidate_chat"
    language = "sv"

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="prompt-restore-admin",
            email="prompt-restore@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)

        definition = get_ai_prompt_definition(self.prompt_key)

        self.override = AIPromptTemplate.objects.create(
            key=self.prompt_key,
            name=definition["name"],
            description=definition["description"],
            language=self.language,
            prompt_text="CUSTOM PROMPT THAT MUST NOT REMAIN IN THE EDITOR",
            is_active=True,
            updated_by=self.user,
        )

        self.url = reverse(
            "core:admin_ai_prompt_edit",
            args=[self.prompt_key, self.language],
        )

    def test_reset_disables_override_and_editor_shows_default_prompt(self):
        response = self.client.post(
            self.url,
            {"action": "reset"},
            follow=True,
        )

        self.override.refresh_from_db()
        default_prompt = get_default_ai_prompt(
            key=self.prompt_key,
            language=self.language,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.override.is_active)
        self.assertFalse(response.context["has_active_override"])
        self.assertEqual(response.context["editing_text"], default_prompt)
        self.assertEqual(response.context["effective_prompt"], default_prompt)

    def test_inactive_override_does_not_replace_default_in_editor(self):
        self.override.is_active = False
        self.override.save(update_fields=["is_active"])

        response = self.client.get(self.url)
        default_prompt = get_default_ai_prompt(
            key=self.prompt_key,
            language=self.language,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["has_active_override"])
        self.assertEqual(response.context["editing_text"], default_prompt)
        self.assertEqual(response.context["effective_prompt"], default_prompt)
