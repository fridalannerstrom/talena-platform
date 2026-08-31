from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.processes.services.process_locking import (
    can_delete_process_safely,
    has_ordered_assessments,
    is_test_package_locked,
)


class ProcessLockingTests(SimpleTestCase):
    def _process(self, *, has_assessment_url=False, model_locked=False, model_can_delete=True):
        invitations = MagicMock()
        invitations.exclude.return_value.exclude.return_value.exists.return_value = (
            has_assessment_url
        )

        return SimpleNamespace(
            pk=123,
            invitations=invitations,
            is_template_locked=lambda: model_locked,
            can_delete=lambda: model_can_delete,
        )

    def test_persisted_sova_url_locks_package_even_if_model_status_lock_is_false(self):
        process = self._process(
            has_assessment_url=True,
            model_locked=False,
        )

        self.assertTrue(has_ordered_assessments(process))
        self.assertTrue(is_test_package_locked(process))

    def test_process_with_persisted_sova_url_cannot_be_deleted(self):
        process = self._process(
            has_assessment_url=True,
            model_can_delete=True,
        )

        self.assertFalse(can_delete_process_safely(process))

    def test_unstarted_process_keeps_existing_model_rules(self):
        process = self._process(
            has_assessment_url=False,
            model_locked=False,
            model_can_delete=True,
        )

        self.assertFalse(is_test_package_locked(process))
        self.assertTrue(can_delete_process_safely(process))
