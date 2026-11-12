from datetime import timedelta
from unittest.mock import patch
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Company
from apps.processes.models import Candidate, TestInvitation, TestProcess

from .models import (
    CandidateResultAccess,
    CandidateResultFeedback,
    CandidateResultSnapshot,
    CandidateTestExperienceFeedback,
)
from .services import (
    create_candidate_result_access,
    revoke_candidate_result_access_for_process,
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

    def test_disabling_a_process_revokes_its_issued_links_only(self):
        self.process.candidate_results_enabled = True
        self.process.save(update_fields=["candidate_results_enabled"])
        access, _, _ = create_candidate_result_access(self._snapshot())

        other_process = TestProcess.objects.create(
            name="Other project",
            company=self.company,
            project_code="other-project",
            account_code="other-account",
            created_by=self.user,
            candidate_results_enabled=True,
        )
        other_invitation = TestInvitation.objects.create(
            process=other_process,
            candidate=self.candidate,
        )
        other_snapshot = CandidateResultSnapshot.objects.create(
            invitation=other_invitation,
            candidate=self.candidate,
            process=other_process,
            locale="sv",
            content={"introduction": "Test"},
            prompt_versions={"candidate_personality": {"id": 1}},
        )
        other_access, _, _ = create_candidate_result_access(other_snapshot)

        self.process.candidate_results_enabled = False
        self.process.save(update_fields=["candidate_results_enabled"])
        self.assertEqual(revoke_candidate_result_access_for_process(self.process), 1)
        access.refresh_from_db()
        other_access.refresh_from_db()
        self.assertFalse(access.is_active())
        self.assertTrue(other_access.is_active())

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
                prompt_versions={"candidate_result": {"version": "test"}},
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
                        {"competency": "Teamwork", "sten": 7},
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

    @patch(
        "apps.core.ai.openai_client.get_openai_client",
        side_effect=AssertionError("Candidate results must not call OpenAI."),
    )
    def test_generation_uses_static_workbook_copy_without_scores_or_ai(
        self, get_client
    ):
        from apps.candidate_results.content import (
            build_candidate_result_content,
        )

        content, metadata, fingerprint = build_candidate_result_content(
            self.invitation,
            language_code="sv",
        )

        serialised_content = json.dumps(content, ensure_ascii=False)
        self.assertIn(
            "Du är vanligtvis samarbetsvillig och bekväm med att jobba både självständigt och i team.",
            serialised_content,
        )
        self.assertEqual(metadata["content_version"], "candidate-static-v5")
        self.assertTrue(fingerprint)
        self.assertNotIn("sten", serialised_content.casefold())
        self.assertNotIn("percentile", serialised_content.casefold())
        get_client.assert_not_called()


    @patch("apps.candidate_results.content.build_candidate_result_content")
    def test_snapshot_creation_is_idempotent(self, generate):
        from apps.candidate_results.content import (
            create_candidate_result_snapshot,
        )

        self.process.candidate_results_enabled = True
        self.process.save(update_fields=["candidate_results_enabled"])
        self.invitation.status = "completed"
        self.invitation.save(update_fields=["status"])

        generate.return_value = (
            {
                "introduction": {
                    "title": "Välkommen",
                    "body": "Resultat.",
                    "points": [],
                },
                "personality": {
                    "title": "Personlighet",
                    "body": "Preferenser.",
                    "points": [],
                },
                "skills": {
                    "title": "Färdigheter",
                    "body": "Färdigheter.",
                    "points": [],
                },
                "motivation": {
                    "title": "Motivation",
                    "body": "Drivkrafter.",
                    "points": [],
                },
            },
            {"personality": {"version_id": 1}},
            "fingerprint",
        )

        first, created = create_candidate_result_snapshot(
            self.invitation,
            language_code="sv",
        )
        second, created_again = create_candidate_result_snapshot(
            self.invitation,
            language_code="sv",
        )

        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.prompt_versions, {})
        generate.assert_called_once()

    def test_legacy_ai_snapshot_is_archived_when_replaced(self):
        from apps.candidate_results.content import (
            CANDIDATE_RESULT_CONTENT_VERSION,
            ensure_candidate_result_snapshot_current,
        )

        old_content = {
            "introduction": {"body": "Old generated text."},
        }
        old_prompts = {"personality": {"version_id": 3}}
        snapshot = CandidateResultSnapshot.objects.create(
            invitation=self.invitation,
            candidate=self.candidate,
            process=self.process,
            locale="sv",
            content=old_content,
            content_version="ai-v1",
            prompt_versions=old_prompts,
        )

        current, upgraded = ensure_candidate_result_snapshot_current(snapshot)

        self.assertTrue(upgraded)
        self.assertEqual(current.content_version, CANDIDATE_RESULT_CONTENT_VERSION)
        self.assertEqual(current.legacy_content, old_content)
        self.assertEqual(current.legacy_prompt_versions, old_prompts)
        self.assertEqual(current.prompt_versions, {})
        self.assertNotEqual(current.content, old_content)


    def test_generation_omits_unavailable_result_areas(self):
        from apps.candidate_results.content import (
            build_candidate_result_content,
        )

        self.invitation.sova_activities = [
            {
                "activity": "Numerical reasoning",
                "competencies": [
                    {"competency": "Numerical reasoning", "percentile": 62},
                ],
            },
        ]
        content, _, _ = build_candidate_result_content(
            self.invitation,
            language_code="sv",
        )

        self.assertIn("skills", content)
        self.assertNotIn("personality", content)
        self.assertNotIn("motivation", content)


class CandidateResultAccessViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="view@example.com",
            email="view@example.com",
            password="test-password",
        )
        self.company = Company.objects.create(name="View Company")
        self.process = TestProcess.objects.create(
            name="View project",
            company=self.company,
            project_code="view-project",
            account_code="view-account",
            created_by=self.user,
            candidate_results_enabled=True,
        )
        self.candidate = Candidate.objects.create(
            first_name="View",
            last_name="Candidate",
            email="view-candidate@example.com",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process,
            candidate=self.candidate,
            status="completed",
            completed_at=timezone.now(),
        )
        self.snapshot = CandidateResultSnapshot.objects.create(
            invitation=self.invitation,
            candidate=self.candidate,
            process=self.process,
            locale="sv",
            content={
                "introduction": {
                    "title": "Välkommen",
                    "body": "Detta är ditt resultat.",
                    "points": [],
                },
                "personality": {
                    "title": "Personlighet",
                    "body": "Möjliga preferenser.",
                    "points": [],
                },
            },
            prompt_versions={"candidate_result": {"version": "test"}},
        )
        self.access, self.raw_token, self.raw_code = (
            create_candidate_result_access(self.snapshot)
        )

    def test_candidate_must_verify_before_result_is_visible(self):
        response = self.client.get(
            f"/candidate-results/{self.raw_token}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visa ditt resultat")
        self.assertNotContains(response, "Detta är ditt resultat.")

        response = self.client.post(
            f"/candidate-results/{self.raw_token}/",
            {"verification_code": self.raw_code},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detta är ditt resultat.")
        self.assertContains(response, "view-candidate@example.com")

    def test_candidate_can_save_feedback_for_an_available_area(self):
        result_url = f"/candidate-results/{self.raw_token}/"
        self.client.post(result_url, {"verification_code": self.raw_code})

        response = self.client.post(
            result_url,
            {
                "action": "save_feedback",
                "result_area": "personality",
                "response": CandidateResultFeedback.RECOGNISES,
                "comment": "Det här stämmer bra med min upplevelse.",
            },
        )

        self.assertEqual(response.status_code, 302)
        feedback = CandidateResultFeedback.objects.get(
            snapshot=self.snapshot,
            result_area="personality",
        )
        self.assertEqual(feedback.response, CandidateResultFeedback.RECOGNISES)
        self.assertEqual(feedback.comment, "Det här stämmer bra med min upplevelse.")

        response = self.client.get(result_url)
        self.assertContains(response, "Redigera kommentar")
        self.assertContains(response, '<div class="candidate-comment__label">Din kommentar:</div>', html=True)
        self.assertContains(response, '<p class="candidate-comment__text">Det här stämmer bra med min upplevelse.</p>', html=True)
        self.assertContains(response, "Jag känner igen mig")

    def test_candidate_feedback_replaces_the_existing_area_response(self):
        result_url = f"/candidate-results/{self.raw_token}/"
        self.client.post(result_url, {"verification_code": self.raw_code})

        for response_value in (
            CandidateResultFeedback.RECOGNISES,
            CandidateResultFeedback.DOES_NOT_RECOGNISE,
        ):
            self.client.post(
                result_url,
                {
                    "action": "save_feedback",
                    "result_area": "personality",
                    "response": response_value,
                    "comment": "",
                },
            )

        feedback = CandidateResultFeedback.objects.get(
            snapshot=self.snapshot,
            result_area="personality",
        )
        self.assertEqual(
            feedback.response,
            CandidateResultFeedback.DOES_NOT_RECOGNISE,
        )
        self.assertEqual(
            CandidateResultFeedback.objects.filter(
                snapshot=self.snapshot,
                result_area="personality",
            ).count(),
            1,
        )

    def test_candidate_cannot_submit_feedback_for_an_unavailable_area(self):
        result_url = f"/candidate-results/{self.raw_token}/"
        self.client.post(result_url, {"verification_code": self.raw_code})

        response = self.client.post(
            result_url,
            {
                "action": "save_feedback",
                "result_area": "motivation",
                "response": CandidateResultFeedback.RECOGNISES,
                "comment": "",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            CandidateResultFeedback.objects.filter(snapshot=self.snapshot).exists()
        )

    def test_test_experience_requires_verified_access_and_valid_rating(self):
        url = f"/candidate-results/{self.raw_token}/"
        data = {"action": "save_experience", "rating": "5", "comment": "Smidigt."}
        self.client.post(url, data)
        self.assertFalse(CandidateTestExperienceFeedback.objects.exists())

        self.client.post(url, {"verification_code": self.raw_code})
        for invalid in ("0", "6", "hello", "3.5"):
            response = self.client.post(url, {**data, "rating": invalid})
            self.assertEqual(response.status_code, 400)
        response = self.client.post(url, {**data, "comment": "x" * 2001})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CandidateTestExperienceFeedback.objects.exists())

    def test_candidate_can_submit_and_update_general_feedback(self):
        url = f"/candidate-results/{self.raw_token}/"
        self.client.post(url, {"verification_code": self.raw_code})

        response = self.client.post(url, {
            "action": "save_experience", "rating": "4", "comment": "Tydliga instruktioner.",
        })
        self.assertRedirects(response, f"{url}?experience_saved=1#test-experience")
        feedback = CandidateTestExperienceFeedback.objects.get(snapshot=self.snapshot)
        self.assertEqual((feedback.rating, feedback.locale), (4, "sv"))
        self.assertEqual(feedback.comment, "Tydliga instruktioner.")
        self.assertIsNotNone(feedback.created_at)
        self.assertContains(self.client.get(response.url), "Din feedback om testupplevelsen har sparats")

        self.client.post(url, {"action": "save_experience", "rating": "2", "comment": ""})
        feedback.refresh_from_db()
        self.assertEqual(feedback.rating, 2)
        self.assertEqual(feedback.comment, "")
        self.assertEqual(CandidateTestExperienceFeedback.objects.filter(snapshot=self.snapshot).count(), 1)

    def test_customer_sees_general_feedback_separate_from_area_reflections(self):
        CandidateTestExperienceFeedback.objects.create(
            snapshot=self.snapshot, rating=5, comment="Bra testupplevelse.", locale="sv",
        )
        self.user.role = "admin"
        self.user.save(update_fields=["role"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("processes:process_candidate_detail", kwargs={
            "process_id": self.process.pk, "candidate_id": self.candidate.pk,
        }), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(response, "Test experience")
        self.assertContains(response, "Very good")
        self.assertContains(response, "Bra testupplevelse.")
        self.assertContains(response, "0 / 1")

    def test_customer_result_link_shows_candidate_reflection_and_test_experience_separately(self):
        CandidateResultFeedback.objects.create(
            snapshot=self.snapshot,
            result_area="personality",
            response=CandidateResultFeedback.RECOGNISES,
            comment="Jag känner igen mig i beskrivningen.",
            locale="sv",
        )
        CandidateTestExperienceFeedback.objects.create(
            snapshot=self.snapshot,
            rating=5,
            comment="Testerna var tydliga.",
            locale="sv",
        )
        self.user.role = "admin"
        self.user.save(update_fields=["role"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("processes:process_candidate_detail", kwargs={
            "process_id": self.process.pk, "candidate_id": self.candidate.pk,
        }), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertContains(response, "Candidate reflections")
        self.assertContains(response, "I recognise myself")
        self.assertContains(response, "Candidate comment")
        self.assertContains(response, "Jag känner igen mig i beskrivningen.")
        self.assertContains(response, "Test experience")
        self.assertContains(response, "Very good")
        self.assertContains(response, "Testerna var tydliga.")
        self.assertNotContains(response, "<strong>5 / 5</strong>")

    def test_revoked_access_returns_gone(self):
        self.access.revoked_at = timezone.now()
        self.access.save(update_fields=["revoked_at"])

        response = self.client.get(
            f"/candidate-results/{self.raw_token}/"
        )

        self.assertEqual(response.status_code, 410)


    def test_disabled_sharing_denies_previously_issued_link(self):
        self.process.candidate_results_enabled = False
        self.process.save(update_fields=["candidate_results_enabled"])

        response = self.client.get(f"/candidate-results/{self.raw_token}/")

        self.assertEqual(response.status_code, 410)

    def test_authorised_preview_shows_snapshot_without_code(self):
        self.user.role = "admin"
        self.user.save(update_fields=["role"])
        self.client.force_login(self.user)

        response = self.client.get(
            f"/candidate-results/preview/{self.snapshot.pk}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detta är ditt resultat.")
        self.assertContains(response, "Förhandsvisning för behörig användare")
        self.assertNotContains(response, "Visa ditt resultat")

    def test_candidate_view_and_internal_preview_use_the_same_snapshot_content(self):
        self.client.post(
            f"/candidate-results/{self.raw_token}/",
            {"verification_code": self.raw_code},
        )
        candidate_response = self.client.get(
            f"/candidate-results/{self.raw_token}/"
        )
        self.assertEqual(candidate_response.status_code, 200)

        self.user.role = "admin"
        self.user.save(update_fields=["role"])
        self.client.force_login(self.user)
        preview_response = self.client.get(
            f"/candidate-results/preview/{self.snapshot.pk}/"
        )

        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(
            candidate_response.context["sections"],
            preview_response.context["sections"],
        )

    def test_preview_is_not_public(self):
        User = get_user_model()
        other_user = User.objects.create_user(
            username="unauthorised-preview@example.com",
            email="unauthorised-preview@example.com",
            password="test-password",
        )
        self.client.force_login(other_user)

        response = self.client.get(
            f"/candidate-results/preview/{self.snapshot.pk}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_customer_candidate_view_contains_result_link(self):
        self.user.role = "admin"
        self.user.save(update_fields=["role"])
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "accounts:company_process_candidate_detail",
                kwargs={
                    "company_pk": self.company.pk,
                    "process_pk": self.process.pk,
                    "candidate_pk": self.candidate.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f"/candidate-results/preview/{self.snapshot.pk}/",
        )
        self.assertContains(response, "View candidate result")

    def test_customer_portal_sheet_contains_result_link(self):
        self.user.role = "admin"
        self.user.save(update_fields=["role"])
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "processes:process_candidate_detail",
                kwargs={
                    "process_id": self.process.pk,
                    "candidate_id": self.candidate.pk,
                },
            ),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f"/candidate-results/preview/{self.snapshot.pk}/",
        )
        self.assertContains(response, "data-candidate-result-status")
        self.assertContains(response, "0 / 1")
        self.assertContains(response, "Not started")
        self.assertNotContains(response, "Latest response:")


    def test_customer_portal_result_tab_follows_selected_language(self):
        self.user.role = "admin"
        self.user.save(update_fields=["role"])
        self.client.force_login(self.user)
        url = reverse(
            "processes:process_candidate_detail",
            kwargs={
                "process_id": self.process.pk,
                "candidate_id": self.candidate.pk,
            },
        )

        for language, tab, heading, description in (
            (
                "sv",
                "Kandidatrapport",
                "Kandidatrapport",
                "Delning är aktiverad. Statusen nedan bygger på faktisk e-post, åtkomst och feedback.",
            ),
            (
                "en",
                "Candidate Report",
                "Candidate Report",
                "Sharing is enabled. The status below reflects actual email, access and feedback data.",
            ),
        ):
            with self.subTest(language=language):
                response = self.client.get(
                    url,
                    HTTP_ACCEPT_LANGUAGE=language,
                    HTTP_X_REQUESTED_WITH="XMLHttpRequest",
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, tab)
                self.assertContains(response, heading)
                self.assertContains(response, description)


    def test_customer_portal_sheet_updates_reflection_status(self):
        self.user.role = "admin"
        self.user.save(update_fields=["role"])
        self.client.force_login(self.user)

        CandidateResultFeedback.objects.create(
            snapshot=self.snapshot,
            result_area="personality",
            response=CandidateResultFeedback.RECOGNISES,
            comment="Stämmer.",
            locale="sv",
        )

        response = self.client.get(
            reverse(
                "processes:process_candidate_detail",
                kwargs={
                    "process_id": self.process.pk,
                    "candidate_id": self.candidate.pk,
                },
            ),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1 / 1")
        self.assertContains(response, "Submitted")
        self.assertContains(response, "Latest response:")
        self.assertContains(response, "Answered")

    def test_customer_portal_sheet_shows_partial_reflection_progress(self):
        candidate = Candidate.objects.create(
            first_name="Second",
            last_name="Candidate",
            email="second-candidate@example.com",
        )
        invitation = TestInvitation.objects.create(
            process=self.process,
            candidate=candidate,
            status="completed",
            completed_at=timezone.now(),
        )
        snapshot = CandidateResultSnapshot.objects.create(
            invitation=invitation,
            candidate=candidate,
            process=self.process,
            locale="sv",
            content={
                "personality": {
                    "title": "Personlighet",
                    "body": "Möjliga preferenser.",
                    "points": [],
                },
                "skills": {
                    "title": "Färdigheter",
                    "body": "Beskrivning av färdigheter.",
                    "points": [],
                },
            },
            prompt_versions={"candidate_result": {"version": "test"}},
        )
        self.user.role = "admin"
        self.user.save(update_fields=["role"])
        self.client.force_login(self.user)
        url = reverse("processes:process_candidate_detail", kwargs={
            "process_id": self.process.pk, "candidate_id": candidate.pk,
        })

        response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(response, "0 / 2")
        self.assertContains(response, "Not started")

        CandidateResultFeedback.objects.create(
            snapshot=snapshot,
            result_area="personality",
            response=CandidateResultFeedback.RECOGNISES,
        )
        response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(response, "1 / 2")
        self.assertContains(response, "In progress")
        self.assertContains(response, "Latest response:")
        self.assertContains(response, "Answered")
        self.assertNotContains(response, "Submitted")

        CandidateResultFeedback.objects.create(
            snapshot=snapshot,
            result_area="skills",
            response=CandidateResultFeedback.PARTLY_RECOGNISES,
        )
        response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(response, "2 / 2")
        self.assertContains(response, "Submitted")

class CandidateResultEmailTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="email-result@example.com",
            email="email-result@example.com",
            password="test-password",
        )
        self.company = Company.objects.create(name="Email Company")
        self.process = TestProcess.objects.create(
            name="Email project",
            company=self.company,
            project_code="email-project",
            account_code="email-account",
            created_by=self.user,
            candidate_results_enabled=True,
            candidate_language="en",
        )
        self.candidate = Candidate.objects.create(
            first_name="Email",
            last_name="Candidate",
            email="email-candidate@example.com",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process,
            candidate=self.candidate,
            status="completed",
            completed_at=timezone.now(),
        )
        self.snapshot = CandidateResultSnapshot.objects.create(
            invitation=self.invitation,
            candidate=self.candidate,
            process=self.process,
            locale="en",
            content={
                "introduction": {
                    "title": "Test",
                    "body": "Test result.",
                    "points": [],
                },
            },
            prompt_versions={"candidate_result": {"version": "test"}},
        )

    @patch("apps.candidate_results.email.EmailMultiAlternatives")
    @patch("apps.candidate_results.email.create_candidate_result_snapshot")
    def test_email_contains_link_and_separate_code(
        self,
        create_snapshot,
        email_class,
    ):
        from apps.emails.models import EmailLog

        create_snapshot.return_value = (self.snapshot, False)
        email_class.return_value.send.return_value = 1

        from apps.candidate_results.email import send_candidate_result_email

        email_log, access, raw_code = send_candidate_result_email(
            self.invitation,
            base_url="https://talena.io",
        )

        self.assertEqual(email_log.status, "sent")
        self.assertEqual(email_log.template_type, "candidate_result")
        sent_body = email_class.call_args.kwargs["body"]
        self.assertIn("https://talena.io/candidate-results/", sent_body)
        self.assertIn(raw_code, sent_body)
        self.assertIn("[redacted candidate result link]", email_log.body_snapshot)
        self.assertIn("[redacted verification code]", email_log.body_snapshot)
        self.assertNotIn("https://talena.io/candidate-results/", email_log.body_snapshot)
        self.assertNotIn(raw_code, email_log.body_snapshot)
        self.assertNotIn(self.process.name, email_log.body_snapshot)
        self.assertEqual(CandidateResultAccess.objects.count(), 1)
        result_url = next(
            line
            for line in sent_body.splitlines()
            if line.startswith("https://talena.io/candidate-results/")
        )
        raw_token = result_url.rstrip("/").rsplit("/", 1)[-1]
        self.assertTrue(access.matches_token(raw_token))
        self.assertNotIn(raw_token, email_log.body_snapshot)

    @patch("apps.candidate_results.email.EmailMultiAlternatives")
    @patch("apps.candidate_results.email.create_candidate_result_snapshot")
    def test_resend_rotates_same_access_record(
        self,
        create_snapshot,
        email_class,
    ):
        create_snapshot.return_value = (self.snapshot, False)
        email_class.return_value.send.return_value = 1

        from apps.candidate_results.email import send_candidate_result_email

        first_log, access, first_code = send_candidate_result_email(
            self.invitation,
            base_url="https://talena.io",
        )
        first_digest = access.token_digest

        second_log, same_access, second_code = send_candidate_result_email(
            self.invitation,
            base_url="https://talena.io",
            replace_code=True,
        )

        self.assertEqual(first_log.status, "sent")
        self.assertEqual(second_log.status, "sent")
        self.assertEqual(access.pk, same_access.pk)
        self.assertNotEqual(first_digest, same_access.token_digest)
        self.assertNotEqual(first_code, second_code)
        self.assertEqual(CandidateResultAccess.objects.count(), 1)


class CandidateResultWebhookTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="webhook@example.com",
            email="webhook@example.com",
            password="test-password",
        )
        self.company = Company.objects.create(name="Webhook Company")
        self.process = TestProcess.objects.create(
            name="Webhook project",
            company=self.company,
            project_code="webhook-project",
            account_code="webhook-account",
            created_by=self.user,
            candidate_results_enabled=True,
        )
        self.candidate = Candidate.objects.create(
            first_name="Webhook",
            last_name="Candidate",
            email="webhook-candidate@example.com",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process,
            candidate=self.candidate,
            request_id="webhook-request",
            status="sent",
        )

    def _post(self, overall_status):
        return self.client.post(
            "/integrations/sova/ingest/",
            data=json.dumps({
                "request_id": "webhook-request",
                "overall_status": overall_status,
                "activities": [],
            }),
            content_type="application/json",
            HTTP_X_TALENA_WEBHOOK_SECRET="webhook-secret",
        )

    @override_settings(SOVA_WEBHOOK_TEST_SECRET="webhook-secret")
    @patch("apps.candidate_results.email.send_candidate_result_email")
    def test_completed_webhook_delivers_enabled_result(self, send):
        response = self._post("completed")

        self.assertEqual(response.status_code, 200)
        send.assert_called_once()
        self.assertEqual(
            send.call_args.kwargs["base_url"],
            "http://testserver/",
        )

    @override_settings(SOVA_WEBHOOK_TEST_SECRET="webhook-secret")
    @patch("apps.candidate_results.email.send_candidate_result_email")
    def test_in_progress_webhook_does_not_deliver_result(self, send):
        response = self._post("in progress")

        self.assertEqual(response.status_code, 200)
        send.assert_not_called()

    @override_settings(SOVA_WEBHOOK_TEST_SECRET="webhook-secret")
    @patch("apps.candidate_results.email.send_candidate_result_email")
    def test_completed_webhook_respects_disabled_sharing(self, send):
        self.process.candidate_results_enabled = False
        self.process.save(update_fields=["candidate_results_enabled"])

        response = self._post("completed")

        self.assertEqual(response.status_code, 200)
        send.assert_not_called()
