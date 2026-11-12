from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.processes import automatic_invitations as auto
from apps.processes.models import TestInvitation
from apps.processes.process_settings_models import ProcessAutomationSettings


class _MissingAutomationSettingsProcess:
    @property
    def automation_settings(self):
        raise ProcessAutomationSettings.DoesNotExist


class AutomaticInvitationSettingTests(SimpleTestCase):
    def test_missing_process_setting_preserves_legacy_off_behaviour(self):
        self.assertFalse(
            auto.automatic_invitation_enabled(
                _MissingAutomationSettingsProcess()
            )
        )

    def test_saved_process_setting_is_returned(self):
        enabled_process = SimpleNamespace(
            automation_settings=SimpleNamespace(
                automatic_invitation_enabled=True,
            )
        )
        disabled_process = SimpleNamespace(
            automation_settings=SimpleNamespace(
                automatic_invitation_enabled=False,
            )
        )

        self.assertTrue(auto.automatic_invitation_enabled(enabled_process))
        self.assertFalse(auto.automatic_invitation_enabled(disabled_process))

    def test_process_form_checkbox_is_persisted_when_process_saves(self):
        request = SimpleNamespace(
            method="POST",
            POST={
                "automatic_invitation_setting_present": "1",
                "automatic_invitation_enabled": "on",
            },
        )
        process = SimpleNamespace(pk=123)

        def view(req):
            auto._persist_process_automatic_invitation_setting(
                sender=None,
                instance=process,
            )
            return SimpleNamespace(status_code=302)

        wrapped = auto.capture_process_automatic_invitation_setting(view)

        with patch.object(auto, "set_automatic_invitation_enabled") as setter:
            wrapped(request)

        setter.assert_called_once_with(process, True)

    def test_unchecked_process_form_checkbox_is_persisted_as_off(self):
        request = SimpleNamespace(
            method="POST",
            POST={
                "automatic_invitation_setting_present": "1",
            },
        )
        process = SimpleNamespace(pk=123)

        def view(req):
            auto._persist_process_automatic_invitation_setting(
                sender=None,
                instance=process,
            )
            return SimpleNamespace(status_code=302)

        wrapped = auto.capture_process_automatic_invitation_setting(view)

        with patch.object(auto, "set_automatic_invitation_enabled") as setter:
            wrapped(request)

        setter.assert_called_once_with(process, False)

    def test_missing_presence_marker_never_overwrites_saved_setting(self):
        request = SimpleNamespace(method="POST", POST={})
        process = SimpleNamespace(pk=123)

        def view(req):
            auto._persist_process_automatic_invitation_setting(
                sender=None,
                instance=process,
            )
            return SimpleNamespace(status_code=302)

        wrapped = auto.capture_process_automatic_invitation_setting(view)

        with patch.object(auto, "set_automatic_invitation_enabled") as setter:
            wrapped(request)

        setter.assert_not_called()


class AutomaticCandidateInvitationTests(SimpleTestCase):
    def _queue_context(self, actor=None):
        actor = actor or SimpleNamespace(pk=77)
        actor_token = auto._AUTO_INVITATION_ACTOR.set(actor)
        pending_token = auto._PENDING_INVITATION_IDS.set([])
        return actor, actor_token, pending_token

    def test_only_new_invited_candidates_are_queued_when_enabled(self):
        process = SimpleNamespace(pk=10)
        invitation = SimpleNamespace(
            pk=55,
            source="invited",
            process=process,
        )
        _, actor_token, pending_token = self._queue_context()

        try:
            with patch.object(
                auto,
                "automatic_invitation_enabled",
                return_value=True,
            ):
                auto._queue_new_automatic_invitation(
                    sender=None,
                    instance=invitation,
                    created=True,
                )
                auto._queue_new_automatic_invitation(
                    sender=None,
                    instance=invitation,
                    created=False,
                )

            self.assertEqual(auto._PENDING_INVITATION_IDS.get(), [55])
        finally:
            auto._PENDING_INVITATION_IDS.reset(pending_token)
            auto._AUTO_INVITATION_ACTOR.reset(actor_token)

    def test_disabled_process_does_not_queue_invitation(self):
        process = SimpleNamespace(pk=10)
        invitation = SimpleNamespace(
            pk=55,
            source="invited",
            process=process,
        )
        _, actor_token, pending_token = self._queue_context()

        try:
            with patch.object(
                auto,
                "automatic_invitation_enabled",
                return_value=False,
            ):
                auto._queue_new_automatic_invitation(
                    sender=None,
                    instance=invitation,
                    created=True,
                )

            self.assertEqual(auto._PENDING_INVITATION_IDS.get(), [])
        finally:
            auto._PENDING_INVITATION_IDS.reset(pending_token)
            auto._AUTO_INVITATION_ACTOR.reset(actor_token)

    def test_add_candidate_flushes_only_after_successful_response(self):
        request = SimpleNamespace(
            method="POST",
            POST={},
            user=SimpleNamespace(pk=77),
        )

        with patch.object(auto, "_flush_pending_automatic_invitations") as flush:
            success_view = auto.capture_automatic_candidate_invitations(
                lambda req: SimpleNamespace(status_code=302)
            )
            success_view(request)
            flush.assert_called_once()

            flush.reset_mock()

            failed_view = auto.capture_automatic_candidate_invitations(
                lambda req: SimpleNamespace(status_code=400)
            )
            failed_view(request)
            flush.assert_not_called()

    def test_batch_flush_deduplicates_ids_and_uses_existing_send_flow(self):
        process = SimpleNamespace(pk=10)
        invitation_one = SimpleNamespace(
            pk=1,
            source="invited",
            process=process,
        )
        invitation_two = SimpleNamespace(
            pk=2,
            source="invited",
            process=process,
        )
        actor = SimpleNamespace(pk=77)

        actor_token = auto._AUTO_INVITATION_ACTOR.set(actor)
        pending_token = auto._PENDING_INVITATION_IDS.set([1, 1, 2])
        context_token = auto._AUTO_INVITATION_CONTEXT.set("customer_auto")

        try:
            with (
                patch.object(TestInvitation.objects, "filter") as filter_mock,
                patch.object(
                    auto,
                    "automatic_invitation_enabled",
                    return_value=True,
                ),
                patch(
                    "apps.processes.services.send_tests.send_assessments_and_emails",
                    return_value={"sent_count": 2, "errors": []},
                ) as send,
            ):
                filter_mock.return_value.select_related.return_value.order_by.return_value = [
                    invitation_one,
                    invitation_two,
                ]

                auto._flush_pending_automatic_invitations()

            filter_mock.assert_called_once_with(pk__in=[1, 2])
            send.assert_called_once_with(
                process=process,
                invitations=[invitation_one, invitation_two],
                actor_user=actor,
                context="customer_auto",
            )
        finally:
            auto._AUTO_INVITATION_CONTEXT.reset(context_token)
            auto._PENDING_INVITATION_IDS.reset(pending_token)
            auto._AUTO_INVITATION_ACTOR.reset(actor_token)
