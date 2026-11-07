from django.test import SimpleTestCase

from apps.processes.interview_config import (
    get_interview_section_config,
)


class InterviewSectionConfigTests(SimpleTestCase):
    def test_interview_defaults_remain_centralised(self):
        cognitive = get_interview_section_config("cognitive")
        motivation = get_interview_section_config("motivation")
        personality = get_interview_section_config("personality")

        self.assertEqual(cognitive["order"], 1)
        self.assertEqual(cognitive["question_count"], 3)
        self.assertEqual(cognitive["estimated_minutes"], 10)

        self.assertEqual(motivation["order"], 2)
        self.assertEqual(motivation["question_count"], 3)
        self.assertEqual(motivation["estimated_minutes"], 10)

        self.assertEqual(personality["order"], 3)
        self.assertEqual(personality["question_count"], 8)
        self.assertEqual(personality["estimated_minutes"], 20)

    def test_section_guidance_is_localised_for_swedish(self):
        section = get_interview_section_config(
            "motivation",
            language_code="sv-SE",
        )

        self.assertEqual(
            section["guidance_label"],
            "Så använder du frågorna",
        )
        self.assertEqual(
            section["transition_label"],
            "Förslag på övergång",
        )
        self.assertIn("motivation", section["transition"].lower())

    def test_section_guidance_defaults_to_english(self):
        section = get_interview_section_config(
            "personality",
            language_code="de",
        )

        self.assertEqual(
            section["guidance_label"],
            "How to use these questions",
        )
        self.assertEqual(
            section["transition_label"],
            "Suggested transition",
        )

    def test_437_approved_opening_questions_and_labels_in_swedish(self):
        expected = "Hur kändes det att svara på formuläret - var det lätt eller svårt att ta ställning?"
        for key, heading in (
            ("personality", "Tips på personlighetsfrågor"),
            ("motivation", "Tips på motivationsfrågor"),
            ("cognitive", "Tips på färdighetsfrågor"),
        ):
            with self.subTest(key=key):
                meta = get_interview_section_config(key, "sv")
                self.assertEqual(meta["questions_label"], heading)
                self.assertEqual(meta["intro_questions_label"], "Inledande frågor")
                self.assertIn("De AI-genererade frågorna är tänkta som inspiration", meta["common_guidance"])
        self.assertEqual(get_interview_section_config("personality", "sv")["intro_questions"], [expected])
        self.assertEqual(get_interview_section_config("motivation", "sv")["intro_questions"], [expected])
        cognitive = get_interview_section_config("cognitive", "sv")
        self.assertEqual(cognitive["intro_questions"], [
            "Har du gjort något liknande test innan?",
            "Är det något typ av test du brukar ha lättare för?",
            "Hur upplevde du det här testet?",
        ])
        self.assertEqual(
            cognitive["transition"],
            "Vill påminna om att färdighetstestet är en liten pusselbit av en helhet. "
            "Dessa färdighetstester är en ögonblicksbild och din erfarenhet inom området "
            "väger också tungt. Därför skulle jag nu vilja prata om hur du tar dig an "
            "information och problemlösning i praktiken. Jag kommer att be om några "
            "konkreta exempel från din erfarenhet.",
        )

    def test_437_only_multiple_completed_cognitive_tests_trigger_comparison(self):
        from types import SimpleNamespace
        from apps.processes.interview_config import get_completed_cognitive_test_keys

        def activity(name, status="completed", percentile=50):
            return {
                "activity": f"Sova {name} Assessment",
                "status": status,
                "competencies": [{"percentile": percentile}],
            }

        single = SimpleNamespace(sova_activities=[activity("Logical Reasoning")])
        duplicate = SimpleNamespace(sova_activities=[
            activity("Logical Reasoning"), activity("Logical Reasoning"),
            activity("Numerical Reasoning", status="started"),
        ])
        multiple = SimpleNamespace(sova_activities=[
            activity("Logical Reasoning"), activity("Numerical Reasoning"),
            activity("Verbal Reasoning", status="started"),
        ])
        self.assertEqual(get_completed_cognitive_test_keys(single), {"logical"})
        self.assertEqual(get_completed_cognitive_test_keys(duplicate), {"logical"})
        self.assertEqual(get_completed_cognitive_test_keys(multiple), {"logical", "numerical"})
        self.assertEqual(len(get_interview_section_config("cognitive", "sv")["intro_questions"]), 3)
        self.assertEqual(
            get_interview_section_config(
                "cognitive", "sv", completed_cognitive_tests=2,
            )["intro_questions"][-1],
            "Kändes något lättare än det andra?",
        )

    def test_437_shared_guide_keeps_the_specific_guidance_only_once(self):
        from django.template.loader import render_to_string

        meta = get_interview_section_config("personality", "sv")
        html = render_to_string(
            "customer/processes/partials/candidate_insights/_interview_guidance.html",
            {"interview_meta": meta},
        )
        self.assertEqual(html.count("De AI-genererade frågorna är tänkta"), 1)
        self.assertEqual(html.count("Använd frågorna för att utforska hur kandidatens"), 1)
        self.assertLess(
            html.index("De AI-genererade frågorna är tänkta"),
            html.index("Använd frågorna för att utforska hur kandidatens"),
        )

    def test_437_static_html_never_requires_ai_or_has_an_ai_badge(self):
        from django.template.loader import render_to_string

        meta = get_interview_section_config("cognitive", "sv", completed_cognitive_tests=1)
        html = render_to_string(
            "customer/processes/partials/candidate_insights/_interview_static_questions.html",
            {"interview_meta": meta},
        )
        self.assertIn("Inledande frågor", html)
        self.assertIn("Har du gjort något liknande test innan?", html)
        self.assertIn('class="interview-static-questions mt-4"', html)
        self.assertIn('class="interview-static-questions__header"', html)
        self.assertEqual(html.count('class="interview-static-questions__item"'), 3)
        self.assertNotIn("Kändes något lättare än det andra?", html)
        self.assertNotIn("AI-genererat", html)

    def test_437_combined_sections_include_completed_areas_without_ai(self):
        from django.template import Context
        from types import SimpleNamespace
        from apps.processes.templatetags.interview_config import interview_combined_sections

        owner = SimpleNamespace(sova_activities=[
            {
                "activity": "Sova Motivation Questionnaire",
                "status": "completed",
                "competencies": [{"stive": 4}],
            },
            {
                "activity": "Sova Verbal Reasoning Assessment",
                "status": "completed",
                "competencies": [{"percentile": 55}],
            },
        ])
        sections = interview_combined_sections(Context({
            "invitation": owner,
            "LANGUAGE_CODE": "sv",
            "combined_question_sections": [],
        }))
        self.assertEqual([item["key"] for item in sections], ["cognitive", "motivation"])
        self.assertTrue(all(not item["questions"] for item in sections))
        self.assertEqual(sections[0]["title"], "Färdighet")
        self.assertEqual(sections[1]["title"], "Motivation")

    def test_437_english_copy_is_never_swedish(self):
        for key in ("personality", "motivation", "cognitive"):
            meta = get_interview_section_config(key, "en")
            self.assertTrue(meta["questions_label"].startswith("Suggested"))
            self.assertEqual(meta["intro_questions_label"], "Opening questions")
            self.assertIn("The AI-generated questions", meta["common_guidance"])
            self.assertTrue(meta["intro_questions"])
            self.assertNotIn("Hur kändes", " ".join(meta["intro_questions"]))

    def test_437_combined_template_renders_static_without_ai_and_no_duplicates(self):
        from django.template.loader import render_to_string
        from django.utils.translation import override
        from types import SimpleNamespace

        owner = SimpleNamespace(sova_activities=[{
            "activity": "Sova Motivation Questionnaire",
            "status": "completed",
            "competencies": [{"stive": 6}],
        }])
        context = {
            "invitation": owner,
            "combined_question_sections": [],
            "combined_question_count": 0,
            "has_combined_questions": False,
        }
        with override("sv"):
            html = render_to_string(
                "customer/processes/partials/candidate_insights/tabs/_questions.html",
                context,
            )
        self.assertEqual(html.count('data-interview-static-questions="motivation"'), 1)
        self.assertIn("Inledande frågor", html)
        self.assertIn("Hur kändes det att svara på formuläret", html)
        self.assertNotIn("No assessment questions are available yet", html)

        context["combined_question_sections"] = [{
            "key": "motivation",
            "title": "Motivation questions",
            "description": "Old description",
            "questions": [{"question": "AI-fråga", "why": "", "listen_for": ""}],
            "question_count": 1,
            "estimated_minutes": 10,
        }]
        context["has_combined_questions"] = True
        context["combined_question_count"] = 1
        with override("sv"):
            html = render_to_string(
                "customer/processes/partials/candidate_insights/tabs/_questions.html",
                context,
            )
        self.assertEqual(html.count('data-interview-static-questions="motivation"'), 1)
        self.assertEqual(html.count("De AI-genererade frågorna är tänkta"), 1)
        self.assertIn("Tips på motivationsfrågor", html)
        self.assertIn("AI-fråga", html)

    def test_437_historical_candidate_uses_imported_completed_abilities(self):
        from django.template import Context
        from apps.processes.templatetags.interview_config import (
            interview_combined_sections,
            interview_section_meta,
        )

        context = Context({
            "historical_candidate": object(),
            "invitation": None,
            "has_personality_results": True,
            "has_motivation_results": False,
            "has_completed_cognitive_results": True,
            "assessment_keys_in_process": {"logical", "numerical"},
            "candidate_insights": {"cognitive_results": [
                {"key": "logical", "completed": True},
                {"key": "numerical", "completed": True},
                {"key": "verbal", "completed": True},
            ]},
            "LANGUAGE_CODE": "sv",
            "combined_question_sections": [],
        })
        sections = interview_combined_sections(context)
        self.assertEqual(
            [section["key"] for section in sections],
            ["cognitive", "personality"],
        )
        meta = interview_section_meta(context, "cognitive")
        self.assertEqual(len(meta["intro_questions"]), 4)
