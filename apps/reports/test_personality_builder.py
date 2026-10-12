from django.test import SimpleTestCase

from apps.reports.libraries.personality.builder import build_graph_segments


class PersonalityGraphSegmentTests(SimpleTestCase):
    def test_missing_sten_keeps_graph_unselected_without_crashing(self):
        segments = build_graph_segments(None)

        self.assertEqual(len(segments), 10)
        self.assertTrue(all(not segment["selected"] for segment in segments))
        self.assertTrue(
            all(
                not segment["filled_toward_midpoint"]
                for segment in segments
            )
        )

    def test_valid_sten_still_marks_the_score_and_midpoint_fill(self):
        segments = build_graph_segments(4)
        by_score = {segment["score"]: segment for segment in segments}

        self.assertTrue(by_score[4]["selected"])
        self.assertTrue(by_score[4]["filled_toward_midpoint"])
        self.assertTrue(by_score[5]["filled_toward_midpoint"])
        self.assertFalse(by_score[6]["filled_toward_midpoint"])
