from datetime import timedelta
from unittest.mock import patch
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Company
from apps.processes.models import Candidate, TestInvitation, TestProcess

from .models import (
    CandidateResultAccess,
    CandidateResultSnapshot,
)
from .services import create_candidate_result_access


class CandidateResultFoundationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="foundation@example.com",
            email="foundation@example.com",
            password="test-password",
        )
        self.company = Company.objects.create(name="Foundation Company")
        self.process = TestProcess.objects.create(
            name="Foundation project",
            company=self.company,
            project_code="foundation-project",
            account_code="foundation-account",
            created_by=self.user,
        )
        self.candidate = Candidate.objects.create(
            first_name="Test",
            last_name="Candidate",
            email="candidate@example.com",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process,
            candidate=self.candidate,
        )

    def _snapshot(self):
        return CandidateResultSnapshot.objects.create(
            invitation=self.invitation,
            candidate=self.candidate,
            process=self.process,
            locale="sv",
            content={
                "introduction": "Detta är ett diskussionsunderlag.",
                "personality": "Kandidattext.",
            },
            prompt_versions={
                "candidate_personality": {"id": 1},
            },
        )

    def test_existing_processes_default_to_disabled(self):
        self.assertFalse(self.process.candidate_results_enabled)

    def test_snapshot_and_access_store_only_digests(self):
        snapshot = self._snapshot()

        access, raw_token, raw_code = create_candidate_result_access(
            snapshot,
            expires_at=timezone.now() + timedelta(days=30),
        )

        self.assertTrue(access.matches_token(raw_token))
        self.assertNotEqual(access.token_digest, raw_token)
        self.assertNotEqual(access.verification_code_hash, raw_code)
        self.assertTrue(access.verify_code(raw_code))

    def test_access_expires_and_can_be_revoked(self):
        snapshot = self._snapshot()
        access, _, raw_code = create_candidate_result_access(
            snapshot,
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        self.assertFalse(access.is_active())
        self.assertFalse(access.verify_code(raw_code))

        access.revoked_at = timezone.now()
        access.save(update_fields=["revoked_at"])
        self.assertFalse(access.is_active())

    def test_wrong_codes_are_rate_limited(self):
        snapshot = self._snapshot()
        access, _, raw_code = create_candidate_result_access(snapshot)

        for _ in range(4):
            self.assertFalse(access.verify_code("000000"))

        self.assertFalse(access.verify_code("000000"))
        self.assertTrue(access.is_rate_limited())
        self.assertFalse(access.verify_code(raw_code))

    def test_snapshot_is_immutable(self):
        snapshot = self._snapshot()
        snapshot.content = {"changed": True}

        with self.assertRaises(ValidationError):
            snapshot.save()

    def test_snapshot_links_must_match_invitation(self):
        other_candidate = Candidate.objects.create(
            first_name="Other",
            last_name="Candidate",
            email="other@example.com",
        )

        with self.assertRaises(ValidationError):
            CandidateResultSnapshot.objects.create(
                invitation=self.invitation,
                candidate=other_candidate,
                process=self.process,
                content={},
                prompt_versions={},
            )


class CandidateResultInterpretationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="interpretation@example.com",
            email="interpretation@example.com",
            password="test-password",
        )
        self.company = Company.objects.create(name="Interpretation Company")
        self.process = TestProcess.objects.create(
            name="Interpretation project",
            company=self.company,
            project_code="interpretation-project",
            account_code="interpretation-account",
            created_by=self.user,
            purpose="flexible",
        )
        self.candidate = Candidate.objects.create(
            first_name="Test",
            last_name="Candidate",
            email="interpretation-candidate@example.com",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process,
            candidate=self.candidate,
            ai_summary="The customer-facing summary.",
            ai_personality_interpretation={
                "interpretation": "The customer personality meaning.",
            },
            ai_motivation_interpretation={
                "interpretation": "The customer motivation meaning.",
            },
            ai_cognitive_interpretation={
                "interpretation": "The customer cognitive meaning.",
            },
            sova_activities=[
                {
                    "activity": "Personality",
                    "competencies": [
                        {"competency": "Structure", "sten": 7},
                    ],
                },
                {
                    "activity": "Skills",
                    "competencies": [
                        {"competency": "Numerical reasoning", "percentile": 62},
                    ],
                },
            ],
        )

    def test_prompt_uses_customer_evidence_and_candidate_rules(self):
        from apps.candidate_results.interpretation import (
            build_candidate_result_prompt,
        )

        prompt, metadata = build_candidate_result_prompt(
            self.invitation,
            language_code="en",
        )

        self.assertIn("The customer-facing summary.", prompt)
        self.assertIn("The customer personality meaning.", prompt)
        self.assertIn("Do not expose raw scores", prompt)
        self.assertEqual(
            set(metadata),
            {"introduction", "personality", "skills", "motivation"},
        )
        self.assertEqual(metadata["personality"]["language"], "en")

    @patch("apps.candidate_results.interpretation.get_openai_client")
    def test_generation_normalises_exact_candidate_sections(self, get_client):
        from types import SimpleNamespace

        from apps.candidate_results.interpretation import (
            generate_candidate_result_content,
        )

        get_client.return_value.chat.completions.create.return_value = (
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=json.dumps({
                                "introduction": {
                                    "title": "Välkommen",
                                    "body": "Ett reflektionsunderlag.",
                                },
                                "personality": {
                                    "title": "Personlighet",
                                    "body": "Möjliga preferenser.",
                                    "points": ["Punkt 1"],
                                },
                                "skills": "Beskrivande färdighetstext.",
                                "motivation": {
                                    "title": "Motivation",
                                    "body": "Möjliga drivkrafter.",
                                },
                            })
                        )
                    )
                ]
            )
        )

        content, metadata, fingerprint = generate_candidate_result_content(
            self.invitation,
            language_code="sv",
        )

        self.assertEqual(
            set(content),
            {"introduction", "personality", "skills", "motivation"},
        )
        self.assertEqual(
            content["skills"]["body"],
            "Beskrivande färdighetstext.",
        )
        self.assertTrue(fingerprint)
        self.assertEqual(metadata["introduction"]["language"], "sv")
