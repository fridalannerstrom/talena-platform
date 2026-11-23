"""Refresh assessment interview questions only through Prepare for interview.

The button is visible to editors, hidden from viewers/historical candidates,
and reuses the existing per-assessment generation and derived-view sync.
"""
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override


class PreInterviewQuestionRefreshUITests(SimpleTestCase):
    def source(self, name):
        return (Path(settings.BASE_DIR) / name).read_text(encoding="utf-8")

    def render_questions(self, language, can_edit=True, historical=False):
        with override(language):
            return render_to_string(
                "customer/processes/partials/candidate_insights/tabs/_questions.html",
                {
                    "combined_question_sections": [],
                    "combined_question_count": 0,
                    "has_combined_questions": False,
                    "combined_questions_refresh_url": "/test/combined/",
                    "can_manage_candidate_results": can_edit,
                    "is_historical": historical,
                },
            )

    def test_refresh_action_is_bilingual_and_only_visible_to_editors(self):
        for language, title in (
            ("sv", "Uppdatera intervjufrågor"),
            ("en", "Regenerate interview questions"),
        ):
            with self.subTest(language=language):
                html = self.render_questions(language)
                self.assertIn("data-pre-interview-questions-regenerate", html)
                self.assertIn("pre-interview-question-actions", html)
                self.assertIn(title, html)
                self.assertIn("data-pre-interview-questions-refresh-status", html)
                self.assertIn("data-combined-questions-root", html)

        for can_edit, historical in ((False, False), (True, True), (False, True)):
            with self.subTest(can_edit=can_edit, historical=historical):
                html = self.render_questions(
                    "sv", can_edit=can_edit, historical=historical
                )
                self.assertNotIn("data-pre-interview-questions-regenerate", html)

    def test_admin_mirror_stays_read_only_without_customer_refresh_controls(self):
        html = self.render_questions("sv", can_edit=False)
        self.assertNotIn("data-pre-interview-questions-regenerate", html)
        self.assertNotIn("data-pre-interview-questions-edit-link", html)

    def test_pdf_button_is_inserted_alongside_refresh_action(self):
        script = self.source("static/js/talena/candidate-report-export.js")
        self.assertIn('item.id === "combined-interview-questions"', script)
        self.assertIn('source.querySelector(".pre-interview-question-actions")', script)
        self.assertIn("actions.append(toolbar)", script)

    def test_only_existing_generation_handlers_are_reused(self):
        script = self.source("static/js/talena/pre-interview-question-refresh.js")
        self.assertIn("data-personality-questions-regenerate", script)
        self.assertIn("data-motivation-questions-regenerate", script)
        self.assertIn("data-cognitive-questions-regenerate", script)
        self.assertIn('action.click()', script)
        self.assertIn("candidate-ai-content-updated", script)
        self.assertIn("confirmQuestionReplacement(workspace, trigger)", script)
        self.assertIn('dialog.showModal()', script)
        self.assertIn('dialog.close("confirm")', script)
        self.assertIn('dialog.close("cancel")', script)
        self.assertIn('resolve(dialog.returnValue === "confirm")', script)
        self.assertNotIn("window.confirm(", script)
        self.assertIn("data-interview-question-note-field", script)
        self.assertNotIn('method: "POST"', script)
        self.assertIn("dataset.preInterviewQuestionsUpdating", script)

    def test_confirm_modal_explains_notes_and_new_questions_in_both_languages(self):
        for language, title, retained, location, action in (
            (
                "sv",
                "Uppdatera intervjufrågorna?",
                "Dina sparade svar och anteckningar behålls",
                "Efter intervju",
                "Uppdatera frågor",
            ),
            (
                "en",
                "Regenerate interview questions?",
                "Your saved answers and notes are kept",
                "After interview",
                "Regenerate questions",
            ),
        ):
            with self.subTest(language=language):
                html = self.render_questions(language)
                self.assertIn("data-pre-interview-refresh-dialog", html)
                self.assertIn('class="talena-question-refresh-dialog"', html)
                self.assertIn("data-pre-interview-refresh-confirm", html)
                self.assertIn("data-pre-interview-refresh-cancel", html)
                self.assertIn(title, html)
                self.assertIn(retained, html)
                self.assertIn(location, html)
                self.assertIn(action, html)

        # Viewers and archived projects do not get a confirmation action.
        for can_edit, historical in ((False, False), (True, True)):
            html = self.render_questions("sv", can_edit=can_edit, historical=historical)
            self.assertNotIn("data-pre-interview-refresh-dialog", html)

    def test_dialog_styles_and_cache_busting_are_loaded(self):
        css = self.source("static/css/talena/pages/candidate-insight-tabs.css")
        self.assertIn(".talena-question-refresh-dialog::backdrop", css)
        self.assertIn(".talena-question-refresh-dialog__notice", css)
        self.assertIn(".talena-question-refresh-dialog__actions", css)
        for path in (
            "templates/customer/processes/_process_header.html",
            "templates/admin/accounts/partials/_candidate_customer_styles.html",
        ):
            self.assertIn("20261123-confirm-dialog-v4", self.source(path))
        for path in (
            "templates/customer/processes/process_base.html",
            "templates/customer/core/layouts/customer_base.html",
        ):
            self.assertIn("20261123-confirm-dialog-v2", self.source(path))

    def test_ajax_refreshed_html_preserves_permissions_and_correct_root(self):
        view = self.source("apps/processes/views.py")
        start = view.index("def process_candidate_combined_questions(")
        end = view.index("\n\n@login_required", start)
        section = view[start:end]
        self.assertIn('"can_manage_candidate_results": (', section)
        self.assertIn("user_can_edit_process(", section)
        self.assertIn('"is_historical": process.is_historical,', section)

        # This is the actual candidate-card bug: the parent interview panel
        # refreshes independently from the combined questions endpoint.
        # Both endpoints must pass the edit permission into _questions.html.
        final_start = view.index("def process_candidate_final_output(")
        final_end = view.index("\n\n@login_required", final_start)
        final_section = view[final_start:final_end]
        self.assertIn('"can_manage_candidate_results": (', final_section)
        self.assertIn("user_can_edit_process(", final_section)
        self.assertIn('"is_historical": process.is_historical,', final_section)

        base = self.source("templates/customer/processes/process_base.html")
        start = base.index("async function refreshCandidateCombinedQuestions(")
        end = base.index("</script>", start)
        section = base[start:end]
        self.assertIn(
            'template.content.querySelector("[data-combined-questions-root]")',
            section,
        )
        self.assertNotIn("template.content.firstElementChild", section)

    def test_final_output_refresh_keeps_prepare_for_interview_tab_open(self):
        # The final-output endpoint replaces both the Prepare for interview
        # and After interview panels. Fresh HTML defaults both to hidden, so
        # the active interview tab must be reactivated after every refresh.
        source = self.source("templates/customer/processes/process_base.html")
        start = source.index("async function refreshCandidateFinalOutput(")
        end = source.index("</script>", start)
        refresh = source[start:end]

        self.assertIn('activeInsightsTabKey === "prepare-interview"', refresh)
        self.assertIn('activeInsightsTabKey === "after-interview"', refresh)
        self.assertIn("currentRoot.replaceWith(", refresh)
        self.assertIn("refreshedInsightsTab?.click()", refresh)
        self.assertLess(
            refresh.index("currentRoot.replaceWith("),
            refresh.index("refreshedInsightsTab?.click()"),
        )
        # Do not reopen a tab the user left during an async network request.
        self.assertLess(
            refresh.index("await response.text()"),
            refresh.index("const activeInsightsTabKey ="),
        )

    def test_script_and_styles_are_loaded_in_both_candidate_views(self):
        for path in (
            "templates/customer/core/layouts/customer_base.html",
            "templates/customer/processes/process_base.html",
        ):
            source = self.source(path)
            self.assertIn("js/talena/pre-interview-question-refresh.js", source)
        for path in (
            "templates/customer/processes/_process_header.html",
            "templates/admin/accounts/partials/_candidate_customer_styles.html",
        ):
            self.assertIn("candidate-insight-tabs.css", self.source(path))

    def test_header_help_text_no_longer_claims_other_question_tabs_exist(self):
        source = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_questions.html"
        )
        self.assertNotIn("Frågorna finns också i respektive testområde", source)
        self.assertNotIn("also available within each assessment area", source)
        self.assertNotIn("regenerated within each assessment category", source)
