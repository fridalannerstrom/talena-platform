from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Company
from apps.processes.models import Candidate, TestInvitation, TestProcess

from .models import (
    CandidateResultAccess,
    CandidateResultSnapshot,
    create_candidate_result_access,
)


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
