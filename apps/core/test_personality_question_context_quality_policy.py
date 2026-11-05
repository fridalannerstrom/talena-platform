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

    def test_short_distinctive_role_quote_can_pass(self):
        # Swedish job adverts often use single compound words to name
        # a concrete duty. Previously four words were required.
        questions = [sample_question(1, scenario="coordinate användartester")]
        review = review_for(questions, "användartester")
        self.assertEqual(
            _failed_indices(
                review,
                questions,
                ["Cooperative"],
                "Rollen omfattar planering av användartester och UX-flöden.",
            ),
            [],
        )

    def test_source_excerpt_matches_quotation_punctuation(self):
        questions = [sample_question(1)]
        review = review_for(
            questions, "Koordinera, leda och utföra användartester",
        )
        self.assertEqual(
            _failed_indices(
                review,
                questions,
                ["Cooperative"],
                "Koordinera leda och utföra användartester av plattformen.",
            ),
            [],
        )

    def test_reviewer_translation_of_trait_does_not_invalidate_correct_tag(self):
        questions = [sample_question(1)]
        review = review_for(questions, "användartester")
        review["checks"][0]["trait"] = "Samverkande"
        self.assertEqual(
            _failed_indices(
                review,
                questions,
                ["Cooperative"],
                "Rollen innehåller koordination av användartester.",
            ),
            [],
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

    def test_audit_keeps_best_available_questions_if_reviewer_still_disagrees(self):
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
                review_for(questions, role_quote, failing=(1,)),
            ],
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._repair_questions",
            return_value={"replacements": [{"index": 1, **corrected}]},
        ):
            result = _quality_check_events(
                self._events(questions), owner=owner, language_code="en",
            )
        self.assertEqual(len(result[2]["items"]), 8)
        self.assertEqual(result[2]["items"][0], corrected)
        self.assertEqual(result[2]["items"][1:], questions[1:])

    def test_short_swedish_coordinator_context_never_blocks_valid_questions(self):
        context = (
            "Rollen är intern projektkoordinator. Arbetet innebär att planera "
            "och koordinera leveranser mellan flera funktioner, skapa struktur "
            "i komplexa projekt, kommunicera med olika intressenter och hantera "
            "förändrade prioriteringar. Begränsad numerisk analys ingår."
        )
        owner = owner_for(context)
        questions = [sample_question(i, scenario="coordinate deliverables") for i in range(1, 9)]
        # When the critic keeps rejecting questions, the user still receives
        # valid interview material rather than a full-page error.
        initial = review_for(questions, "", failing=range(1, 9))
        corrected = [
            {"index": i, **sample_question(i, scenario="coordinate deliverables across teams")}
            for i in range(1, 9)
        ]
        with patch(
            "apps.core.ai.personality_question_definition_grounding_policy."
            "_render_question_result_summaries",
            return_value="Cooperative: candidate-specific Result Summary.",
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._review_questions",
            return_value=initial,
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._repair_questions",
            return_value={"replacements": corrected},
        ) as repair:
            result = _quality_check_events(
                self._events(questions), owner=owner, language_code="sv",
            )
        self.assertEqual(len(result[2]["items"]), 8)
        self.assertEqual(repair.call_count, 2)
        self.assertEqual(result[2]["items"][0]["question"], corrected[0]["question"])
        self.assertEqual(result[-1], {"type": "done"})

    def test_initial_review_api_failure_returns_original_questions(self):
        owner = owner_for(UX_CONTEXT)
        questions = [sample_question(i) for i in range(1, 9)]
        events = self._events(questions)
        with patch(
            "apps.core.ai.personality_question_definition_grounding_policy."
            "_render_question_result_summaries",
            return_value="Cooperative: result summary.",
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._review_questions",
            side_effect=RuntimeError("external reviewer unavailable"),
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._repair_questions",
        ) as repair:
            self.assertIs(
                _quality_check_events(events, owner=owner, language_code="en"),
                events,
            )
        repair.assert_not_called()

    def test_failed_repair_returns_unmodified_original_questions(self):
        owner = owner_for(UX_CONTEXT)
        questions = [sample_question(i) for i in range(1, 9)]
        events = self._events(questions)
        with patch(
            "apps.core.ai.personality_question_definition_grounding_policy."
            "_render_question_result_summaries",
            return_value="Cooperative: result summary.",
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._review_questions",
            return_value=review_for(questions, "", failing=(1,)),
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._repair_questions",
            side_effect=RuntimeError("repair failed"),
        ):
            result = _quality_check_events(
                events, owner=owner, language_code="sv",
            )
        self.assertEqual(result[2]["items"], questions)

    def test_recheck_api_failure_keeps_structurally_valid_improvement(self):
        owner = owner_for(UX_CONTEXT)
        questions = [sample_question(i) for i in range(1, 9)]
        corrected = sample_question(1, scenario="coordinate user testing")
        with patch(
            "apps.core.ai.personality_question_definition_grounding_policy."
            "_render_question_result_summaries",
            return_value="Cooperative: result summary.",
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._review_questions",
            side_effect=[
                review_for(questions, "", failing=(1,)),
                RuntimeError("review unavailable"),
            ],
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._repair_questions",
            return_value={"replacements": [{"index": 1, **corrected}]},
        ):
            result = _quality_check_events(
                self._events(questions), owner=owner, language_code="sv",
            )
        self.assertEqual(result[2]["items"][0], corrected)
        self.assertEqual(result[2]["items"][1:], questions[1:])

    def test_missing_result_summary_keeps_original_questions(self):
        owner = owner_for(UX_CONTEXT)
        questions = [sample_question(i) for i in range(1, 9)]
        events = self._events(questions)
        with patch(
            "apps.core.ai.personality_question_definition_grounding_policy."
            "_render_question_result_summaries", return_value="",
        ), patch(
            "apps.core.ai.personality_question_context_quality_policy._review_questions",
        ) as review:
            self.assertIs(
                _quality_check_events(events, owner=owner, language_code="sv"),
                events,
            )
        review.assert_not_called()

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
