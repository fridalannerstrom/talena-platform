from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai.personality_question_context_quality_policy import (
    _apply_repairs,
    _duplicate_question_indices,
    _role_specificity_failures,
    _failed_indices,
    _quality_check_events,
    is_personality_question_context_outdated,
    personality_question_context_fingerprint,
)
from apps.core.ai.personality_question_role_anchors import (
    extract_role_task_anchors,
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
    # Distinct source-backed work scenarios, so a test that expects valid
    # questions does not accidentally contain eight near-duplicates.
    contexts = (
        "stakeholder expectations in an early discovery workshop",
        "conflicting priorities during a remote usability study",
        "research synthesis for a management review",
        "design iteration following accessibility feedback",
        "planning a prototype test across teams",
        "handoff between clinical project stakeholders",
        "challenging assumptions in a product planning meeting",
        "facilitating feedback from student participants",
    )
    detail = contexts[(number - 1) % len(contexts)]
    return {
        "question": (
            f"Tell me about a time when you had to {scenario.lower()} "
            f"while adapting your collaboration approach in {detail}."
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

    def test_extract_role_anchors_from_realistic_ux_advert(self):
        context = (
            "Vi utvecklar virtuella patienter för kliniker och studenter.\n"
            "Arbetsuppgifter\n"
            "Designa användarcentrerade lösningar på den AI-baserade plattformen\n"
            "Ta fram flöden för relevanta användarupplevelser\n"
            "Koordinera, leda och utföra användartester av plattformen\n"
            "Analysera, sammanställa och presentera resultat från användartester\n"
            "Koordinera olika utvecklingsdelar inom projektet\n"
            "Kvalifikationer\n"
            "Krav på god svensk språkförmåga."
        )
        anchors = extract_role_task_anchors(context)
        self.assertGreaterEqual(len(anchors), 4)
        self.assertTrue(any("användartester" in item for item in anchors))
        self.assertTrue(any("flöden" in item for item in anchors))
        self.assertTrue(any("användarcentrerade" in item for item in anchors))
        self.assertFalse(any("språkförmåga" in item for item in anchors))

    def test_extract_role_anchors_from_short_coordinator_context(self):
        context = (
            "Rollen är intern projektkoordinator. Arbetet innebär att planera "
            "och koordinera leveranser mellan flera funktioner, skapa struktur "
            "i komplexa projekt, kommunicera med olika intressenter och hantera "
            "förändrade prioriteringar. Begränsad numerisk analys ingår."
        )
        anchors = extract_role_task_anchors(context)
        self.assertTrue(any("koordinera leveranser" in item for item in anchors))
        self.assertTrue(any("struktur i komplexa projekt" in item for item in anchors))
        self.assertTrue(any("förändrade prioriteringar" in item for item in anchors))
        self.assertFalse(any("numerisk analys" in item for item in anchors))

    def test_detects_duplicate_questions_from_project_coordinator_example(self):
        questions = [
            {"question": "Berätta om ett tillfälle då du skapade struktur i ett projekt."},
            {"question": "Berätta om ett tillfälle då du kommunicerade med flera intressenter."},
            {"question": "Kan du beskriva en situation där du behövde vara måldriven trots distraktioner i ett projekt? Hur lyckades du hålla fokus?"},
            {"question": "Berätta om en gång när du behövde vara måldriven trots distraktioner i ett projekt med flera parallella leveranser. Hur lyckades du hålla fokus?"},
            {"question": "Kan du ge ett exempel på när du behövde växla mellan att fokusera på detaljer och att se den större bilden i ett projekt? Hur hanterade du det?"},
            {"question": "Kan du ge ett exempel på när du behövde växla mellan att fokusera på detaljer och att se den större bilden i ett komplext projekt? Hur hanterade du det?"},
        ]
        self.assertEqual(_duplicate_question_indices(questions), [4, 6])

    def test_ux_questions_without_a_role_duty_are_flagged_for_repair(self):
        role_anchors = [
            "Designa användarcentrerade lösningar på plattformen",
            "Koordinera, leda och utföra användartester av plattformen",
            "Analysera och presentera resultat från användartester",
        ]
        questions = [
            {"question": "Berätta om när du behövde involvera andra i ett projekt."},
            {"question": "När planerade du användartester av plattformen tillsammans med utvecklare?"},
            {"question": "Hur arbetar du med olika människors perspektiv i en grupp?"}
        ]
        self.assertEqual(
            _role_specificity_failures(questions, role_anchors),
            [1, 3],
        )

    def test_actual_generic_ux_question_patterns_all_trigger_role_repair(self):
        anchors = [
            "Designa användarcentrerade lösningar på den AI-baserade plattformen",
            "Ta fram flöden för relevanta användarupplevelser",
            "Koordinera, leda och utföra användartester av plattformen",
            "Analysera, sammanställa och presentera resultat från användartester",
            "Koordinera olika utvecklingsdelar inom projektet",
        ]
        questions = [
            {"question": "Berätta om en situation där du behövde involvera andra i ett projekt."},
            {"question": "Kan du ge ett exempel då du behövde lyssna på andras perspektiv?"},
            {"question": "Berätta om när du behövde nätverka med nya personer."},
            {"question": "Beskriv när du behövde övertyga andra om en åsikt i en gruppdiskussion."},
            {"question": "Berätta om en situation där du behövde skapa struktur i ett projekt."},
            {"question": "När använde du både analytiska och intuitiva metoder för ett problem?"},
            {"question": "Berätta om när du behövde tänka kreativt för att lösa ett problem."},
            {"question": "Beskriv när du växlade mellan detaljer och den större bilden."},
        ]
        self.assertEqual(
            _role_specificity_failures(questions, anchors),
            list(range(1, 9)),
        )

    def test_role_specificity_allows_different_inflections_and_real_recruitment(self):
        role_anchors = [
            "Koordinera användartester av plattformen",
            "Analysera och sammanställa resultat från användartester",
        ]
        questions = [
            {"question": "Beskriv en användartestning där olika målgrupper behövde höras."},
            {"question": "Vad lärde du dig när du sammanställde användartesters resultat?"},
        ]
        self.assertEqual(
            _role_specificity_failures(questions, role_anchors),
            [],
        )
        recruiter = ["Genomföra rekryteringsprocesser för flera säljchefer"]
        recruiter_questions = [
            {"question": "Hur prioriterade du parallella rekryteringsprocesser?"},
            {"question": "När behövde du presentera kandidater för säljchefer?"},
        ]
        self.assertEqual(
            _role_specificity_failures(recruiter_questions, recruiter),
            [],
        )

    def test_initial_prompt_exposes_concrete_role_anchors(self):
        from apps.core.ai.personality_question_definition_grounding_policy import (
            _build_final_result_summary_grounding,
        )
        owner = owner_for(UX_CONTEXT)
        with patch(
            "apps.core.ai.personality_question_definition_grounding_policy."
            "_render_question_result_summaries",
            return_value="Cooperative: a candidate-specific summary.",
        ), patch(
            "apps.core.ai.personality_question_definition_grounding_policy."
            "build_shared_ai_context",
            return_value={"context_text": UX_CONTEXT, "has_context": True},
        ):
            prompt = _build_final_result_summary_grounding(
                owner=owner, language_code="sv",
            )
        self.assertIn("ROLE TASK ANCHORS", prompt)
        self.assertIn("Coordinate and execute user testing", prompt)
        self.assertIn("EVERY question must have", prompt)

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
            return_value=review_for(questions, "Coordinate and execute user testing on an AI-based training platform", failing=(1,)),
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
                review_for(questions, "Coordinate and execute user testing on an AI-based training platform", failing=(1,)),
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
