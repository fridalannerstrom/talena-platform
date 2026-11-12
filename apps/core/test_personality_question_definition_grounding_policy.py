from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.personality_question_definition_grounding_policy import (
    _finalise_parent_trait_prompt,
    _render_question_result_summaries,
)
from apps.reports.libraries.personality.content import (
    INDICATOR_PROFILE_CONTENT,
)


class PersonalityQuestionDefinitionGroundingPolicyTests(SimpleTestCase):
    def _owner(
        self,
        *,
        selected_traits=None,
        context_text=(
            "Role: Key Account Manager. The role involves changing customer "
            "needs, long-term customer relationships and commercial priorities."
        ),
    ):
        owner = SimpleNamespace(
            selected_personality_traits=(
                selected_traits
                if selected_traits is not None
                else ["Cooperative"]
            ),
            candidate=SimpleNamespace(
                first_name="Alex",
                last_name="Andersson",
                email="alex@example.com",
            ),
            sova_activities=[
                {
                    "activity": "Personality Assessment",
                    "competencies": [
                        {"competency": "Cooperative", "sten_rounded": 7},
                        {"competency": "Sensitivity", "sten_rounded": 9},
                        {"competency": "Teamwork", "sten_rounded": 4},
                        {"competency": "Agreeableness", "sten_rounded": 8},
                        {"competency": "Analytical", "sten_rounded": 2},
                        {"competency": "Data Focus", "sten_rounded": 2},
                        {"competency": "Evaluating", "sten_rounded": 3},
                        {"competency": "Analysing Problems", "sten_rounded": 4},
                    ],
                }
            ],
        )

        owner.process = SimpleNamespace(
            purpose="recruitment",
            is_historical=False,
            role_context=SimpleNamespace(
                get_context_for_purpose=lambda purpose: {
                    "context_text": context_text,
                }
            ),
        )

        return owner

    def test_selected_trait_receives_only_finished_result_summary(self):
        text = _render_question_result_summaries(
            owner=self._owner(),
            language_code="en",
        )

        self.assertIn("PERSONALITY TRAIT: Cooperative", text)
        self.assertNotIn("PERSONALITY TRAIT: Analytical", text)
        self.assertIn("CANDIDATE-SPECIFIC RESULT SUMMARY", text)

        for indicator_name, band in (
            ("Sensitivity", "9_10"),
            ("Teamwork", "4_7"),
            ("Agreeableness", "8"),
        ):
            self.assertIn(
                INDICATOR_PROFILE_CONTENT[indicator_name]["score_texts"][band]["en"],
                text,
            )

        # The indicator meanings are already folded into the summary. Do not
        # expose the machinery that produced it to the question model.
        self.assertNotIn("UNDERLYING INDICATOR", text)
        self.assertNotIn("Sensitivity:", text)
        self.assertNotIn("Teamwork:", text)
        self.assertNotIn("Agreeableness:", text)
        self.assertNotIn("STEN", text)
        self.assertNotIn("LOW POLE", text)
        self.assertNotIn("HIGH POLE", text)

    def test_ai_selection_receives_summaries_for_all_available_parent_traits(self):
        text = _render_question_result_summaries(
            owner=self._owner(selected_traits=[]),
            language_code="en",
        )

        self.assertIn("PERSONALITY TRAIT: Cooperative", text)
        self.assertIn("PERSONALITY TRAIT: Analytical", text)
        self.assertNotIn("STEN", text)
        self.assertNotIn("UNDERLYING INDICATOR", text)

    def test_swedish_summary_uses_same_score_band_text_as_result_summary_ui(self):
        text = _render_question_result_summaries(
            owner=self._owner(),
            language_code="sv",
        )

        self.assertIn("Cooperative / Samverkande", text)
        self.assertIn("KANDIDATENS RESULTATSAMMANFATTNING", text)
        self.assertIn(
            INDICATOR_PROFILE_CONTENT["Sensitivity"]["score_texts"]["9_10"]["sv"],
            text,
        )
        self.assertIn(
            INDICATOR_PROFILE_CONTENT["Teamwork"]["score_texts"]["4_7"]["sv"],
            text,
        )
        self.assertNotIn("STEN", text)

    def test_final_parent_trait_prompt_removes_old_score_direction_layers(self):
        prompt = """
TALENA INPUT DATA

PROCESS CONTEXT
Role context from the base prompt.

PERSONALITY ASSESSMENT DATA
- Cooperative: STEN 7 of 10

AVAILABLE TECHNICAL TRAIT NAMES
- Cooperative

ADMINISTRATOR AI GUIDANCE
Admin controls how the interview question should be written.

TALENA CANDIDATE-SPECIFIC QUESTION GROUNDING
CANDIDATE-SPECIFIC PROFILE SNAPSHOT
- Cooperative: STEN 7 of 10 (situational)
Old score-direction rules.

TALENA CANDIDATE FINGERPRINT STANDARD
Keep the question specific to this candidate and process.

TALENA PERSONALITY QUESTION PRECISION STANDARD
SELECTED CANDIDATE EVIDENCE
- Cooperative: situational behavioural pattern
Old precision rules.

TALENA PERSONALITY QUESTION LABEL CONTRACT
Every question needs a valid trait label.
""".strip()

        result = _finalise_parent_trait_prompt(
            prompt,
            owner=self._owner(),
            language_code="en",
        )

        self.assertNotIn("- Cooperative: STEN 7 of 10", result)
        self.assertNotIn("CANDIDATE-SPECIFIC PROFILE SNAPSHOT", result)
        self.assertNotIn("TALENA PERSONALITY QUESTION PRECISION STANDARD", result)
        self.assertNotIn("situational behavioural pattern", result)

        self.assertIn("ADMINISTRATOR AI GUIDANCE", result)
        self.assertIn("Admin controls how the interview question", result)
        self.assertIn("TALENA CANDIDATE FINGERPRINT STANDARD", result)
        self.assertIn("TALENA PERSONALITY QUESTION LABEL CONTRACT", result)
        self.assertIn("TALENA FINAL PERSONALITY QUESTION EVIDENCE", result)
        self.assertIn("CANDIDATE-SPECIFIC RESULT SUMMARY", result)

    def test_final_grounding_keeps_process_context_explicit_and_actionable(self):
        result = _finalise_parent_trait_prompt(
            "ADMINISTRATOR AI GUIDANCE\nAdmin text",
            owner=self._owner(),
            language_code="en",
        )

        self.assertIn(
            "Role: Key Account Manager. The role involves changing customer needs",
            result,
        )
        self.assertIn(
            "The Result Summary determines the candidate-specific behavioural hypothesis",
            result,
        )
        self.assertIn(
            "Process context determines the concrete situation",
            result,
        )
        self.assertIn(
            "Administrator guidance remains authoritative",
            result,
        )

    def test_competency_mode_keeps_existing_evidence_path_untouched(self):
        owner = self._owner(
            selected_traits=["competency::Teamwork"]
        )
        original = (
            "COMPETENCY PROMPT\n"
            "SUPPORTING PERSONALITY EVIDENCE\n"
            "Existing competency-specific evidence."
        )

        result = _finalise_parent_trait_prompt(
            original,
            owner=owner,
            language_code="en",
        )

        self.assertEqual(result, original)

    def test_goal_focused_alias_uses_finished_summary_without_indicator_rows(self):
        owner = self._owner(
            selected_traits=["Achievement Striving"]
        )
        owner.sova_activities = [
            {
                "activity": "Personality Assessment",
                "competencies": [
                    {"competency": "Achievement Striving", "sten_rounded": 8},
                    {"competency": "Competitive", "sten_rounded": 3},
                    {"competency": "Challenge", "sten_rounded": 8},
                    {"competency": "Self-Discipline", "sten_rounded": 9},
                ],
            }
        ]

        text = _render_question_result_summaries(
            owner=owner,
            language_code="en",
        )

        self.assertIn("Achievement Striving", text)
        self.assertIn(
            INDICATOR_PROFILE_CONTENT["Competitive"]["score_texts"]["3"]["en"],
            text,
        )
        self.assertNotIn("Competitive:", text)
        self.assertNotIn("STEN", text)
