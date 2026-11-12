from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.processes.automatic_invitations import (
    automatic_invitation_enabled,
    capture_automatic_candidate_invitations,
    capture_process_automatic_invitation_setting,
    set_automatic_invitation_enabled,
)
from apps.processes.models import Candidate, TestInvitation, TestProcess
from apps.processes.process_settings_models import ProcessAutomationSettings


class AutomaticInvitationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="auto-invite-user",
            email="auto@example.com",
            password="test-password",
        )
        self.factory = RequestFactory()
        self.process = TestProcess.objects.create(
            name="Automatic invitation test",
            account_code="ACC",
            project_code="PROJECT",
            created_by=self.user,
            selected_tests=["personality"],
        )

    def _post_request(self, data=None):
        request = self.factory.post("/test/", data or {})
        request.user = self.user
        return request

    def _candidate(self, suffix):
        return Candidate.objects.create(
            first_name="Candidate",
            last_name=str(suffix),
            email=f"candidate-{suffix}@example.com",
        )

    def test_missing_setting_defaults_to_off(self):
        self.assertFalse(automatic_invitation_enabled(self.process))
        self.assertFalse(
            ProcessAutomationSettings.objects.filter(process=self.process).exists()
        )

    def test_process_create_or_update_checkbox_is_persisted(self):
        created_processes = []

        def fake_create(request):
            created_processes.append(
                TestProcess.objects.create(
                    name="Created with auto invitations",
                    account_code="ACC",
                    project_code="PROJECT-2",
                    created_by=self.user,
                )
            )
            return HttpResponse("ok")

        wrapped_create = capture_process_automatic_invitation_setting(fake_create)
        wrapped_create(
            self._post_request(
                {
                    "automatic_invitation_setting_present": "1",
                    "automatic_invitation_enabled": "on",
                }
            )
        )

        created = created_processes[0]
        self.assertTrue(automatic_invitation_enabled(created))

        def fake_update(request):
            created.name = "Updated"
            created.save(update_fields=["name"])
            return HttpResponse("ok")

        wrapped_update = capture_process_automatic_invitation_setting(fake_update)
        wrapped_update(
            self._post_request(
                {"automatic_invitation_setting_present": "1"}
            )
        )

        created.refresh_from_db()
        self.assertFalse(automatic_invitation_enabled(created))

    def test_missing_ui_marker_preserves_existing_setting(self):
        set_automatic_invitation_enabled(self.process, True)

        def fake_update(request):
            self.process.name = "Still enabled"
            self.process.save(update_fields=["name"])
            return HttpResponse("ok")

        wrapped = capture_process_automatic_invitation_setting(fake_update)
        wrapped(self._post_request({}))

        self.assertTrue(automatic_invitation_enabled(self.process))

    @patch("apps.processes.services.send_tests.send_assessments_and_emails")
    def test_enabled_process_sends_new_invitation(self, send_mock):
        send_mock.return_value = {
            "sent_count": 1,
            "skipped_count": 0,
            "errors": [],
        }
        set_automatic_invitation_enabled(self.process, True)
        candidate = self._candidate("enabled")

        def fake_add(request):
            TestInvitation.objects.get_or_create(
                process=self.process,
                candidate=candidate,
                defaults={"source": "invited", "status": "created"},
            )
            return HttpResponse("ok")

        wrapped = capture_automatic_candidate_invitations(fake_add)
        wrapped(self._post_request())

        send_mock.assert_called_once()
        kwargs = send_mock.call_args.kwargs
        self.assertEqual(kwargs["process"], self.process)
        self.assertEqual(kwargs["actor_user"], self.user)
        self.assertEqual(kwargs["context"], "customer_auto")
        self.assertEqual(len(kwargs["invitations"]), 1)
        self.assertEqual(kwargs["invitations"][0].candidate, candidate)

    @patch("apps.processes.services.send_tests.send_assessments_and_emails")
    def test_disabled_process_only_adds_candidate(self, send_mock):
        set_automatic_invitation_enabled(self.process, False)
        candidate = self._candidate("disabled")

        def fake_add(request):
            TestInvitation.objects.get_or_create(
                process=self.process,
                candidate=candidate,
                defaults={"source": "invited", "status": "created"},
            )
            return HttpResponse("ok")

        wrapped = capture_automatic_candidate_invitations(fake_add)
        wrapped(self._post_request())

        self.assertTrue(
            TestInvitation.objects.filter(
                process=self.process,
                candidate=candidate,
                status="created",
            ).exists()
        )
        send_mock.assert_not_called()

    @patch("apps.processes.services.send_tests.send_assessments_and_emails")
    def test_duplicate_add_does_not_send_duplicate_invitation(self, send_mock):
        send_mock.return_value = {
            "sent_count": 1,
            "skipped_count": 0,
            "errors": [],
        }
        set_automatic_invitation_enabled(self.process, True)
        candidate = self._candidate("duplicate")

        def fake_add(request):
            TestInvitation.objects.get_or_create(
                process=self.process,
                candidate=candidate,
                defaults={"source": "invited", "status": "created"},
            )
            return HttpResponse("ok")

        wrapped = capture_automatic_candidate_invitations(fake_add)
        wrapped(self._post_request())
        wrapped(self._post_request())

        self.assertEqual(
            TestInvitation.objects.filter(
                process=self.process,
                candidate=candidate,
            ).count(),
            1,
        )
        send_mock.assert_called_once()

    @patch("apps.processes.services.send_tests.send_assessments_and_emails")
    def test_multiple_new_candidates_are_sent_as_one_batch(self, send_mock):
        send_mock.return_value = {
            "sent_count": 2,
            "skipped_count": 0,
            "errors": [],
        }
        set_automatic_invitation_enabled(self.process, True)
        first = self._candidate("bulk-1")
        second = self._candidate("bulk-2")

        def fake_bulk_add(request):
            for candidate in (first, second):
                TestInvitation.objects.get_or_create(
                    process=self.process,
                    candidate=candidate,
                    defaults={"source": "invited", "status": "created"},
                )
            return HttpResponse("ok")

        wrapped = capture_automatic_candidate_invitations(fake_bulk_add)
        wrapped(self._post_request())

        send_mock.assert_called_once()
        invitations = send_mock.call_args.kwargs["invitations"]
        self.assertEqual(len(invitations), 2)
        self.assertEqual(
            {invitation.candidate_id for invitation in invitations},
            {first.id, second.id},
        )

    @patch("apps.processes.services.send_tests.send_assessments_and_emails")
    def test_self_registration_does_not_trigger_automatic_invitation(self, send_mock):
        set_automatic_invitation_enabled(self.process, True)
        candidate = self._candidate("self-register")

        def fake_self_register(request):
            TestInvitation.objects.create(
                process=self.process,
                candidate=candidate,
                source="self_registered",
                status="created",
            )
            return HttpResponse("ok")

        wrapped = capture_automatic_candidate_invitations(fake_self_register)
        wrapped(self._post_request())

        send_mock.assert_not_called()
