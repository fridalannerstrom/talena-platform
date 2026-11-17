"""#478: trustworthy, human confirmation of saved candidate comments."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Company
from apps.candidate_results.content import CANDIDATE_RESULT_CONTENT_VERSION
from apps.candidate_results.models import (
    CandidateResultAccess,
    CandidateResultFeedback,
    CandidateResultSnapshot,
)
from apps.candidate_results.services import create_candidate_result_access
from apps.processes.models import Candidate, TestInvitation, TestProcess


class CandidateCommentAcknowledgementTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="candidate-ack-478", password="not-used",
        )
        self.company = Company.objects.create(name="Candidate acknowledgement test")
        self.process = TestProcess.objects.create(
            company=self.company,
            created_by=self.user,
            name="Candidate result feedback",
            project_code="comment-test",
            account_code="comment-test",
            candidate_results_enabled=True,
            candidate_language="sv",
        )
        self.candidate = Candidate.objects.create(
            first_name="Test", last_name="Candidate",
            email="comment-feedback@example.test",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process, candidate=self.candidate, status="completed",
        )
        self.snapshot = CandidateResultSnapshot.objects.create(
            process=self.process,
            candidate=self.candidate,
            invitation=self.invitation,
            locale="sv",
            content_version=CANDIDATE_RESULT_CONTENT_VERSION,
            content={
                "introduction": {"title": "Ditt resultat", "body": "Inledning."},
                "personality": {
                    "title": "Personlighet",
                    "body": "Ett underlag för reflektion.",
                    "points": [],
                    "groups": [],
                },
            },
            prompt_versions={},
        )
        self.access, self.raw_token, self.code = (
            create_candidate_result_access(self.snapshot)
        )
        self.url = reverse(
            "candidate_results:result", kwargs={"token": self.raw_token},
        )

    def verify(self):
        response = self.client.post(
            self.url, {"verification_code": self.code},
        )
        self.assertEqual(response.status_code, 200)

    def submit(self, **overrides):
        payload = {
            "action": "save_feedback",
            "result_area": "personality",
            "response": CandidateResultFeedback.RECOGNISES,
            "comment": "Jag vill gärna förtydliga mitt resultat.",
        }
        payload.update(overrides)
        return self.client.post(self.url, payload)

    def test_accepted_comment_gets_warm_thank_you_once(self):
        self.verify()
        response = self.submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertTrue(CandidateResultFeedback.objects.filter(
            snapshot=self.snapshot,
            comment="Jag vill gärna förtydliga mitt resultat.",
        ).exists())

        visible = self.client.get(response.url)
        self.assertContains(
            visible,
            "Tack för din kommentar. En person i rekryteringsteamet kommer att läsa den.",
        )
        self.assertContains(visible, "data-feedback-comment-confirmation")
        self.assertContains(visible, 'role="status"')

        second_get = self.client.get(self.url)
        self.assertNotContains(second_get, "data-feedback-comment-confirmation")
        self.assertNotContains(second_get, "Tack för din kommentar.")

    def test_rating_without_comment_uses_neutral_acknowledgement(self):
        self.verify()
        response = self.submit(comment="")
        self.assertEqual(response.status_code, 302)
        visible = self.client.get(response.url)
        self.assertContains(visible, "Din reflektion har sparats.")
        self.assertNotContains(visible, "Tack för din kommentar.")

    def test_query_string_cannot_fake_a_saved_comment(self):
        self.verify()
        response = self.client.get(self.url + "?feedback_saved=1")
        self.assertNotContains(response, "Tack för din kommentar.")
        self.assertNotContains(response, "Din reflektion har sparats.")

    def test_invalid_response_is_recoverable_without_fake_success(self):
        self.verify()
        response = self.submit(
            response="invalid", comment="Det här vill jag spara.",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Det här svaret är inte giltigt.", status_code=400)
        self.assertContains(response, "Försök gärna igen.", status_code=400)
        self.assertContains(
            response, "Det här vill jag spara.", status_code=400,
        )
        self.assertContains(
            response, "data-feedback-error-dialog", status_code=400,
        )
        self.assertNotContains(response, "data-feedback-comment-confirmation", status_code=400)
        self.assertFalse(CandidateResultFeedback.objects.exists())

        success = self.submit(comment="Det här vill jag spara.")
        self.assertEqual(success.status_code, 302)
        self.assertContains(self.client.get(success.url), "Tack för din kommentar.")

    def test_too_long_comment_is_preserved_for_retry(self):
        self.verify()
        response = self.submit(comment="X" * 2001)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "2 000 tecken", status_code=400)
        self.assertContains(response, "X" * 2001, status_code=400)
        self.assertFalse(CandidateResultFeedback.objects.exists())
        self.assertNotContains(response, "data-feedback-comment-confirmation", status_code=400)

    def test_database_error_shows_recoverable_message_not_thank_you(self):
        self.verify()
        with patch(
            "apps.candidate_results.views._save_candidate_feedback",
            side_effect=DatabaseError("synthetic transient failure"),
        ):
            response = self.submit(comment="Spara gärna min kommentar.")
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "Försök gärna igen.", status_code=503)
        self.assertContains(
            response, "Spara gärna min kommentar.", status_code=503,
        )
        self.assertNotContains(
            response, "data-feedback-comment-confirmation", status_code=503,
        )
        self.assertFalse(CandidateResultFeedback.objects.exists())

    def test_english_comment_is_acknowledged_in_english(self):
        CandidateResultSnapshot.objects.filter(pk=self.snapshot.pk).update(locale="en")
        CandidateResultAccess.objects.filter(pk=self.access.pk).update(locale="en")
        self.verify()
        response = self.submit(comment="A note on the result.")
        self.assertEqual(response.status_code, 302)
        visible = self.client.get(response.url)
        self.assertContains(
            visible,
            "Thank you for your comment. Someone on the recruitment team will read it.",
        )
        self.assertNotContains(visible, "Tack för din kommentar.")

    def test_unverified_candidate_cannot_submit_or_get_confirmation(self):
        response = self.submit()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ange den personliga verifieringskod")
        self.assertNotContains(response, "Tack för din kommentar.")
        self.assertFalse(CandidateResultFeedback.objects.exists())
