from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.candidate_results.content import (
    CANDIDATE_PERSONALITY_CONTENT_EN,
    CANDIDATE_PERSONALITY_CONTENT_SV,
    build_candidate_result_content,
)
from apps.core.ai.motivation_interpretation import MOTIVATION_DEFINITIONS
from apps.reports.libraries.cognitive.candidate_result_content import (
    CANDIDATE_SKILL_ABILITIES,
    CANDIDATE_SKILL_COPY,
    CANDIDATE_SKILL_TITLES,
    candidate_cognitive_level_key,
    resolve_candidate_skill_text,
)
from apps.reports.libraries.motivation.candidate_result_content import (
    CANDIDATE_RESULT_COPY,
)
from apps.reports.libraries.personality.definitions import (
    TRAIT_AND_INDICATOR_PROFILE,
)


class CandidateResultStaticContentQATests(SimpleTestCase):
    def _invitation(self, sova_activities):
        return SimpleNamespace(
            process=SimpleNamespace(is_historical=False),
            sova_activities=sova_activities,
        )

    def test_approved_static_libraries_cover_all_results_in_both_languages(self):
        expected_indicators = {
            indicator
            for section in TRAIT_AND_INDICATOR_PROFILE["sections"]
            for trait in section["traits"]
            for indicator in trait["indicators"]
        }
        swedish_traits = {
            indicator["key"]: indicator
            for trait in CANDIDATE_PERSONALITY_CONTENT_SV["traits"]
            for indicator in trait["indicators"]
        }
        english_indicators = CANDIDATE_PERSONALITY_CONTENT_EN["indicators"]
        score_bands = CANDIDATE_PERSONALITY_CONTENT_SV["score_bands"]

        self.assertEqual(set(swedish_traits), expected_indicators)
        self.assertEqual(set(english_indicators), expected_indicators)
        self.assertEqual(
            CANDIDATE_PERSONALITY_CONTENT_EN["score_bands"],
            score_bands,
        )
        for indicator_key in expected_indicators:
            with self.subTest(indicator=indicator_key):
                swedish_texts = swedish_traits[indicator_key]["score_texts"]
                english_texts = english_indicators[indicator_key]
                self.assertEqual(set(swedish_texts), set(score_bands))
                self.assertEqual(len(english_texts), len(score_bands))
                self.assertTrue(all(text.strip() for text in swedish_texts.values()))
                self.assertTrue(all(text.strip() for text in english_texts))

        self.assertEqual(set(CANDIDATE_RESULT_COPY["sv"]), set(MOTIVATION_DEFINITIONS))
        self.assertEqual(set(CANDIDATE_RESULT_COPY["en"]), set(MOTIVATION_DEFINITIONS))
        for language in ("sv", "en"):
            self.assertTrue(
                all(text.strip() for text in CANDIDATE_RESULT_COPY[language].values())
            )

        expected_skills = {"logical", "numerical", "verbal"}
        expected_levels = {"very-low", "low", "average", "high", "very-high"}
        for language in ("sv", "en"):
            self.assertEqual(set(CANDIDATE_SKILL_ABILITIES[language]), expected_skills)
            self.assertEqual(set(CANDIDATE_SKILL_TITLES[language]), expected_skills)
            self.assertEqual(set(CANDIDATE_SKILL_COPY[language]), expected_levels)
            self.assertTrue(
                all(text.strip() for text in CANDIDATE_SKILL_ABILITIES[language].values())
            )
            self.assertTrue(
                all(text.strip() for text in CANDIDATE_SKILL_TITLES[language].values())
            )
            self.assertTrue(
                all(text.strip() for text in CANDIDATE_SKILL_COPY[language].values())
            )

    def test_personality_results_use_the_matching_static_band_in_both_languages(self):
        english_titles = {
            "leading_and_working_with_others": "Leading and Working with Others",
            "organisation_and_thinking_style": "Organising and Thought Patterns",
            "interacting_and_managing_emotions": "Interaction and Emotional Regulation",
        }
        swedish_titles = {
            "leading_and_working_with_others": "Leda och arbeta med andra",
            "organisation_and_thinking_style": "Organisering och tankemönster",
            "interacting_and_managing_emotions": "Interaktion och känslohantering",
        }
        score_bands = {
            1: "1_2",
            2: "1_2",
            3: "3",
            4: "4_7",
            5: "4_7",
            6: "4_7",
            7: "4_7",
            8: "8",
            9: "9_10",
            10: "9_10",
        }
        english_texts = {
            key: dict(zip(
                CANDIDATE_PERSONALITY_CONTENT_EN["score_bands"],
                sentences,
            ))
            for key, sentences in CANDIDATE_PERSONALITY_CONTENT_EN[
                "indicators"
            ].items()
        }
        swedish_texts = {
            indicator["key"]: indicator["score_texts"]
            for trait in CANDIDATE_PERSONALITY_CONTENT_SV["traits"]
            for indicator in trait["indicators"]
        }

        for section in TRAIT_AND_INDICATOR_PROFILE["sections"]:
            for trait in section["traits"]:
                for indicator_key in trait["indicators"]:
                    for language, titles, texts in (
                        ("sv", swedish_titles, swedish_texts),
                        ("en", english_titles, english_texts),
                    ):
                        for sten, score_band in score_bands.items():
                            with self.subTest(
                                indicator=indicator_key,
                                language=language,
                                sten=sten,
                            ):
                                invitation = self._invitation([
                                    {
                                        "activity": "Personality",
                                        "competencies": [
                                            {
                                                "competency": indicator_key,
                                                "sten": sten,
                                            },
                                        ],
                                    },
                                ])
                                content, _metadata, _fingerprint = (
                                    build_candidate_result_content(
                                        invitation,
                                        language_code=language,
                                    )
                                )

                                groups = content["personality"]["groups"]
                                self.assertEqual(len(groups), 1)
                                self.assertEqual(
                                    groups[0]["title"],
                                    titles[section["section_key"]],
                                )
                                self.assertEqual(
                                    groups[0]["body"],
                                    texts[indicator_key][score_band],
                                )

    def test_skill_text_covers_all_ability_and_percentile_boundaries(self):
        boundaries = (
            (0, "very-low"),
            (9, "very-low"),
            (10, "low"),
            (24, "low"),
            (25, "average"),
            (74, "average"),
            (75, "high"),
            (90, "high"),
            (91, "very-high"),
            (100, "very-high"),
        )

        for language in ("sv", "en"):
            for ability_key, ability in CANDIDATE_SKILL_ABILITIES[language].items():
                for percentile, expected_level in boundaries:
                    with self.subTest(
                        language=language,
                        ability=ability_key,
                        percentile=percentile,
                    ):
                        self.assertEqual(
                            candidate_cognitive_level_key(percentile),
                            expected_level,
                        )
                        self.assertEqual(
                            resolve_candidate_skill_text(
                                ability_key,
                                percentile,
                                language_code=language,
                            ),
                            CANDIDATE_SKILL_COPY[language][expected_level].format(
                                ability=ability,
                            ),
                        )

    def test_generic_skills_activity_maps_all_ability_texts(self):
        percentiles = {
            "logical": 9,
            "numerical": 74,
            "verbal": 91,
        }
        invitation = self._invitation([
            {
                "activity": "Skills",
                "competencies": [
                    {
                        "competency": "Logical reasoning",
                        "percentile": percentiles["logical"],
                    },
                    {
                        "competency": "Numerical reasoning",
                        "percentile": percentiles["numerical"],
                    },
                    {
                        "competency": "Verbal reasoning",
                        "percentile": percentiles["verbal"],
                    },
                ],
            },
        ])

        for language in ("sv", "en"):
            with self.subTest(language=language):
                content, _metadata, _fingerprint = build_candidate_result_content(
                    invitation,
                    language_code=language,
                )
                groups = content["skills"]["groups"]
                self.assertEqual(
                    [group["title"] for group in groups],
                    [
                        CANDIDATE_SKILL_TITLES[language][key]
                        for key in ("logical", "numerical", "verbal")
                    ],
                )
                self.assertEqual(
                    [group["items"][0]["text"] for group in groups],
                    [
                        resolve_candidate_skill_text(
                            key,
                            percentiles[key],
                            language_code=language,
                        )
                        for key in ("logical", "numerical", "verbal")
                    ],
                )

    def test_motivation_results_select_the_matching_static_texts_in_both_languages(self):
        for language in ("sv", "en"):
            for factor_key in MOTIVATION_DEFINITIONS:
                with self.subTest(language=language, factor=factor_key):
                    invitation = self._invitation([
                        {
                            "activity": "Motivation",
                            "competencies": [
                                {"competency": factor_key, "stive": 5},
                            ],
                        },
                    ])
                    content, _metadata, _fingerprint = build_candidate_result_content(
                        invitation,
                        language_code=language,
                    )
                    self.assertEqual(
                        content["motivation"]["groups"][0]["items"][0]["text"],
                        CANDIDATE_RESULT_COPY[language][factor_key],
                    )

        invitation = self._invitation([
            {
                "activity": "Motivation",
                "competencies": [
                    {"competency": "Affiliation", "stive": 5},
                    {"competency": "Achievement", "stive": 4},
                    {"competency": "Autonomy", "stive": 3},
                    {"competency": "Learning", "stive": 2},
                ],
            },
        ])
        expected_keys = ("attachment", "achievement", "independence")

        for language in ("sv", "en"):
            with self.subTest(language=language):
                content, _metadata, _fingerprint = build_candidate_result_content(
                    invitation,
                    language_code=language,
                )
                items = content["motivation"]["groups"][0]["items"]
                self.assertEqual(
                    [item["text"] for item in items],
                    [CANDIDATE_RESULT_COPY[language][key] for key in expected_keys],
                )
                self.assertTrue(all(set(item) == {"label", "text"} for item in items))

    def test_missing_result_areas_are_omitted_in_both_languages(self):
        invitation = self._invitation([
            {
                "activity": "Skills",
                "competencies": [
                    {"competency": "Numerical reasoning", "percentile": 62},
                ],
            },
        ])

        for language in ("sv", "en"):
            with self.subTest(language=language):
                content, _metadata, _fingerprint = build_candidate_result_content(
                    invitation,
                    language_code=language,
                )
                self.assertIn("skills", content)
                self.assertNotIn("personality", content)
                self.assertNotIn("motivation", content)
