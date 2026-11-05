from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai.personality_question_context_quality_policy import (
    _apply_repairs,
    _failed_indices,
    _quality_check_events,
    is_personality_question_context_outdated,
    personality_question_context_fingerprint,
)


UX_CONTEXT = (
    "Coordinate and execute user testing on an AI-based training platform. "
    "Analyse and present results from user testing to project stakeholders. "
    "Design user-centred solutions and coordinate different development groups."
)
RECRUITMENT_CONTEXT = (
    "Manage multiple recruitment processes for sales roles in parallel. "
    "Present qualified candidates to sales managers and conduct phone interviews. "
    "Build candidate networks using LinkedIn and follow up recruitment KPIs."
)


def owner_for(context: str, *, purpose="recruitment"):
    role_context = SimpleNamespace(
        get_context_for_purpose=lambda _purpose: {"context_text": context},
    )
    process = SimpleNamespace(
        purpose=purpose, is_historical=False, role_context=role_context,
    )
    return SimpleNamespace(process=process, selected_personality_traits=["Cooperative"])


def sample_question(number, *, scenario="Coordinate and execute user testing"):
    return {
        "question": (
            f"Tell me about a time when you had to {scenario.lower()} "
            f"while adapting your collaboration approach (example {number})."
        ),
        "traits": ["Cooperative"],
        "why": "Explore the candidate's profile-specific collaboration approach.",
        "listen_for": "Concrete actions, feedback and reflection.",
    }


def review_for(questions, quote, *, failing=()):
    return {
        "checks": [
            {
                "index": number,
                "passed": number not in failing,
                "trait": "Cooperative",
                "context_quote": quote if number not in failing else "",
            }
            for number in range(1, len(questions) + 1)
        ]
    }


class PersonalityQuestionContextQualityTests(SimpleTestCase):
    def _events(self, questions):
        return [
            {"type": "meta", "title": "Personality questions"},
            {"type": "selected_traits", "items": ["Cooperative"]},
            {"type": "questions", "items": questions},
            {"type": "done"},
        ]

    def test_recruitment_questions_pass_without_unnecessary_repair(self):
        owner = owner_for(RECRUITMENT_CONTEXT)
        questions = [
            sample_question(i, scenario="manage multiple recruitment processes")
            for i in range(1, 9)
        ]
        quote = "Manage multiple recruitment processes for sales roles in parallel"
        with patch(
            "apps.core.ai.personality_question_definition_grounding_policy."
            "_render_question_result_summaries",
            return_value="Cooperative: prefers autonomy, explores how to involve others.",
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._review_questions",
            return_value=review_for(questions, quote),
        ) as review, patch(
            "apps.core.ai.personality_question_context_quality_policy._repair_questions",
        ) as repair:
            events = _quality_check_events(
                self._events(questions), owner=owner, language_code="sv",
            )
        self.assertEqual(events[2]["items"], questions)
        self.assertEqual(review.call_count, 1)
        repair.assert_not_called()

    def test_generic_ux_question_is_repaired_but_valid_questions_are_preserved(self):
        owner = owner_for(UX_CONTEXT)
        questions = [
            sample_question(i, scenario="coordinate and execute user testing")
            for i in range(1, 9)
        ]
        questions[1] = sample_question(2, scenario="work on a project")
        role_quote = "Coordinate and execute user testing on an AI-based training platform"
        corrected = sample_question(
            2, scenario="analyse and present results from user testing"
        )
        repaired = {"replacements": [{"index": 2, **corrected}]}
        with patch(
            "apps.core.ai.personality_question_definition_grounding_policy."
            "_render_question_result_summaries",
            return_value="Cooperative: candidate-specific result summary.",
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._review_questions",
            side_effect=[
                review_for(questions, role_quote, failing=(2,)),
                review_for(questions, role_quote),
            ],
        ) as review, patch(
            "apps.core.ai.personality_question_context_quality_policy._repair_questions",
            return_value=repaired,
        ) as repair:
            result = _quality_check_events(
                self._events(questions), owner=owner, language_code="sv",
            )
        self.assertEqual(result[2]["items"][1], corrected)
        self.assertEqual(result[2]["items"][0], questions[0])
        self.assertEqual(result[2]["items"][2:], questions[2:])
        self.assertEqual(review.call_count, 2)
        self.assertEqual(repair.call_args.kwargs["failed_indices"], [2])
        self.assertEqual(result[-1], {"type": "done"})

    def test_hallucinated_context_quote_cannot_pass_even_if_model_approves(self):
        questions = [sample_question(1)]
        check = review_for(questions, "Manage recruitment processes for sales roles")
        self.assertEqual(
            _failed_indices(check, questions, ["Cooperative"], UX_CONTEXT),
            [1],
        )

    def test_missing_selected_trait_cannot_pass(self):
        questions = [sample_question(1)]
        questions[0]["traits"] = []
        check = review_for(
            questions,
            "Coordinate and execute user testing on an AI-based training platform",
        )
        self.assertEqual(
            _failed_indices(check, questions, ["Cooperative"], UX_CONTEXT),
            [1],
        )

    def test_audit_stops_if_repair_does_not_pass_second_check(self):
        owner = owner_for(UX_CONTEXT)
        questions = [sample_question(i) for i in range(1, 9)]
        role_quote = "Coordinate and execute user testing on an AI-based training platform"
        corrected = sample_question(1, scenario="analyse and present results")
        with patch(
            "apps.core.ai.personality_question_definition_grounding_policy."
            "_render_question_result_summaries",
            return_value="Cooperative: candidate-specific result summary.",
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._review_questions",
            side_effect=[
                review_for(questions, role_quote, failing=(1,)),
                review_for(questions, role_quote, failing=(1,)),
            ],
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._repair_questions",
            return_value={"replacements": [{"index": 1, **corrected}]},
        ):
            with self.assertRaisesMessage(
                ValueError, "did not pass role-context quality control",
            ):
                _quality_check_events(
                    self._events(questions), owner=owner, language_code="en",
                )

    def test_no_process_context_preserves_current_generation_behaviour(self):
        owner = owner_for("")
        questions = [sample_question(1)]
        events = self._events(questions)
        with patch(
            "apps.core.ai.personality_question_context_quality_policy._review_questions",
        ) as review:
            self.assertIs(
                _quality_check_events(events, owner=owner, language_code="sv"),
                events,
            )
        review.assert_not_called()

    def test_repairs_cannot_modify_approved_questions(self):
        questions = [sample_question(i) for i in range(1, 9)]
        corrected = sample_question(2, scenario="analyse user testing")
        with self.assertRaisesMessage(
            ValueError, "Unexpected personality question quality repair index",
        ):
            _apply_repairs(
                questions,
                {"replacements": [{"index": 1, **corrected}]},
                [2],
                ["Cooperative"],
            )

    def test_context_fingerprint_tracks_purpose_and_content(self):
        original = owner_for(UX_CONTEXT).process
        same = owner_for(UX_CONTEXT).process
        changed = owner_for(RECRUITMENT_CONTEXT).process
        other_purpose = owner_for(UX_CONTEXT, purpose="team_development").process
        fingerprint = personality_question_context_fingerprint(original)
        self.assertEqual(fingerprint, personality_question_context_fingerprint(same))
        self.assertNotEqual(fingerprint, personality_question_context_fingerprint(changed))
        self.assertNotEqual(fingerprint, personality_question_context_fingerprint(other_purpose))
        self.assertFalse(is_personality_question_context_outdated(
            same, {"questions": [sample_question(1)], "context_fingerprint": fingerprint}
        ))
        self.assertTrue(is_personality_question_context_outdated(
            changed, {"questions": [sample_question(1)], "context_fingerprint": fingerprint}
        ))
        self.assertTrue(is_personality_question_context_outdated(
            same, {"questions": [sample_question(1)]}
        ))
