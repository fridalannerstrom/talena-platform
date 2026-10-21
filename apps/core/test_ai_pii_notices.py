"""Guard the bilingual, inline free-text privacy notices added in #299."""

from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override


class AIPersonalDataNoticesTests(SimpleTestCase):
    def test_interview_notice_is_swedish(self):
        with override("sv"):
            html = render_to_string(
                "shared/ai_pii_notice.html",
                {"kind": "interview", "notice_id": "test-interview-pii"},
            )
        self.assertIn("Skriv inte kandidatens namn", html)
        self.assertIn("andra personuppgifter", html)
        self.assertIn('id="test-interview-pii"', html)

    def test_interview_notice_is_english(self):
        with override("en"):
            html = render_to_string(
                "shared/ai_pii_notice.html",
                {"kind": "interview"},
            )
        self.assertIn("Do not enter the candidate's name", html)
        self.assertIn("other personal data", html)

    def test_general_notice_is_swedish_and_english(self):
        with override("sv"):
            swedish = render_to_string(
                "shared/ai_pii_notice.html",
                {"kind": "general"},
            )
        with override("en"):
            english = render_to_string(
                "shared/ai_pii_notice.html",
                {"kind": "general"},
            )
        self.assertIn("Ange inte namn, kontaktuppgifter", swedish)
        self.assertIn("Do not enter names, contact details", english)

    def test_relevant_templates_render_inline_notices(self):
        root = Path(settings.BASE_DIR)
        templates = {
            "templates/customer/processes/partials/candidate_insights/tabs/_final_output.html": 1,
            "templates/customer/processes/process_role_context.html": 1,
            "templates/customer/teams/team_form.html": 2,
            "templates/admin/core/ai_prompts/prompt_edit.html": 2,
            # Candidate-chat fields were removed for launch (#302). Do not
            # require warning markup in UI that is intentionally absent.
            "templates/customer/chat/chat.html": 1,
        }
        for filename, expected_count in templates.items():
            with self.subTest(filename=filename):
                source = (root / filename).read_text(encoding="utf-8")
                self.assertEqual(
                    source.count('{% include "shared/ai_pii_notice.html"'),
                    expected_count,
                )

    def test_removed_candidate_chat_fields_do_not_reappear(self):
        root = Path(settings.BASE_DIR)
        for filename in (
            "templates/customer/processes/_candidate_detail_sheet.html",
            "templates/admin/accounts/companies/company_candidate_sheet.html",
        ):
            with self.subTest(filename=filename):
                content = (root / filename).read_text(encoding="utf-8")
                self.assertNotIn("js-candidate-ai-form", content)
                self.assertNotIn("data-chat-stream-url", content)

    def test_interview_notes_warnings_are_explicit(self):
        root = Path(settings.BASE_DIR)
        interview = (
            root
            / "templates/customer/processes/partials/candidate_insights/tabs/_final_output.html"
        ).read_text(encoding="utf-8")
        question_notes = (
            root / "static/js/talena/interview-question-notes.js"
        ).read_text(encoding="utf-8")
        self.assertIn('kind="interview"', interview)
        self.assertIn('aria-describedby="interview-notes-pii-notice"', interview)
        self.assertIn("Skriv inte kandidatens namn", question_notes)
        self.assertIn("Do not enter the candidate's name", question_notes)
        self.assertIn(
            'wrapper.append(header, field, piiNotice, privacyNotice, footer)',
            question_notes,
        )
        self.assertIn(
            'field.setAttribute("aria-describedby", `${privacyNotice.id} ${piiNotice.id}`)',
            question_notes,
        )
        self.assertIn('piiNotice.setAttribute("role", "status")', question_notes)
        self.assertIn('piiInfoTitle: "Möjliga personuppgifter upptäckta"', question_notes)
