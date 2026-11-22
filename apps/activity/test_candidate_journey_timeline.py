"""Candidate card shows meaningful candidate milestones, not staff-generated PDFs."""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase

from apps.activity.models import ActivityEvent
from apps.activity.services import (
    CANDIDATE_TIMELINE_VERBS,
    candidate_journey_activity,
    customer_visible_activity,
)


class CandidateJourneyTimelineTests(TestCase):
    def _event(self, verb):
        return ActivityEvent.objects.create(verb=verb)

    def test_journey_events_are_shown_but_report_and_internal_events_are_hidden(self):
        relevant = (
            ActivityEvent.Verb.CANDIDATE_ADDED,
            ActivityEvent.Verb.INVITE_SENT,
            ActivityEvent.Verb.TEST_STARTED,
            ActivityEvent.Verb.TEST_COMPLETED,
            ActivityEvent.Verb.ALL_TESTS_COMPLETED,
            ActivityEvent.Verb.STATUS_CHANGED,
            ActivityEvent.Verb.CANDIDATE_RESULT_EMAIL_SENT,
            ActivityEvent.Verb.CANDIDATE_RESULT_EMAIL_FAILED,
            ActivityEvent.Verb.CANDIDATE_RESULT_LINK_OPENED,
            ActivityEvent.Verb.CANDIDATE_RESULT_FEEDBACK_SUBMITTED,
        )
        excluded = (
            ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED,
            ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED,
            ActivityEvent.Verb.REPORT_EXPORT_GENERATED,
            ActivityEvent.Verb.CANDIDATE_RESULT_SNAPSHOT_CREATED,
            ActivityEvent.Verb.CANDIDATE_RESULT_CODE_VERIFIED,
            ActivityEvent.Verb.CANDIDATE_RESULT_CODE_FAILED,
            ActivityEvent.Verb.CANDIDATE_RESULT_CODE_REPLACED,
            ActivityEvent.Verb.CANDIDATE_RESULT_ACCESS_REVOKED,
            ActivityEvent.Verb.AI_CALL_SUCCEEDED,
            ActivityEvent.Verb.PROCESS_ARCHIVED,
        )
        self.assertEqual(CANDIDATE_TIMELINE_VERBS, frozenset(relevant))
        expected = [self._event(verb).pk for verb in relevant]
        hidden = [self._event(verb).pk for verb in excluded]

        visible = set(
            candidate_journey_activity(ActivityEvent.objects.all())
            .values_list("pk", flat=True)
        )
        self.assertEqual(visible, set(expected))
        self.assertTrue(set(hidden).isdisjoint(visible))
        # Suppressed in this *tab*, never deleted or suppressed in admin audit.
        self.assertTrue(ActivityEvent.objects.filter(pk__in=hidden).count() == len(hidden))

    def test_filter_before_fifty_event_limit_preserves_old_test_milestones(self):
        completed = self._event(ActivityEvent.Verb.TEST_COMPLETED)
        invited = self._event(ActivityEvent.Verb.INVITE_SENT)
        for index in range(75):
            self._event(
                ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED
                if index % 2 else ActivityEvent.Verb.REPORT_EXPORT_GENERATED
            )
        recent_feedback = self._event(ActivityEvent.Verb.CANDIDATE_RESULT_FEEDBACK_SUBMITTED)
        timeline = list(
            candidate_journey_activity(ActivityEvent.objects.all())
            .order_by("-created_at", "-pk")[:50]
        )
        self.assertEqual([event.pk for event in timeline], [
            recent_feedback.pk, invited.pk, completed.pk,
        ])
        self.assertEqual(ActivityEvent.objects.count(), 78)

    def test_global_customer_activity_filter_is_not_changed(self):
        pdf = self._event(ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED)
        visible_project_event_ids = set(
            customer_visible_activity(ActivityEvent.objects.all())
            .values_list("pk", flat=True)
        )
        self.assertIn(pdf.pk, visible_project_event_ids)


class CandidateTimelineWiringTests(SimpleTestCase):
    def test_candidate_context_filters_before_limiting_to_fifty(self):
        source = (
            Path(settings.BASE_DIR) / "apps/processes/views.py"
        ).read_text(encoding="utf-8")
        start = source.index("    # The candidate card follows the candidate's journey.")
        segment = source[start:start + 750]
        self.assertIn("candidate_journey_activity(", segment)
        self.assertIn("candidate=candidate", segment)
        self.assertIn('.order_by("-created_at", "-pk")[:50]', segment)
        self.assertLess(
            segment.index("candidate_journey_activity("),
            segment.index('[:50]'),
        )
