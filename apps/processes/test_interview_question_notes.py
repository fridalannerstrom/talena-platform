import json

from django.apps import apps
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    Company,
    CompanyMember,
    OrgUnit,
    User,
    UserOrgUnitAccess,
)
from apps.processes.interview_question_models import (
    InterviewQuestionNote,
    ManagerReportTextEdit,
    ManagerReportTextEditEvent,
)
from apps.processes.interview_note_privacy import contains_interview_note_personal_data
from apps.processes.interview_question_notes import (
    _question_texts_from_result,
    get_current_question_texts,
    interview_question_key,
    normalize_question_text,
)
from apps.processes.models import Candidate, TestInvitation, TestProcess


class InterviewQuestionNoteHelperTests(TestCase):
    def test_question_normalisation_collapses_rendering_whitespace(self):
        self.assertEqual(
            normalize_question_text("  Tell me\n  about   a challenge.  "),
            "Tell me about a challenge.",
        )

    def test_question_key_is_stable_after_whitespace_normalisation(self):
        compact = interview_question_key(
            "personality",
            "Tell me about a challenge.",
        )
        rendered = interview_question_key(
            " personality ",
            " Tell me\n about   a challenge. ",
        )
        other_source = interview_question_key(
            "motivation",
            "Tell me about a challenge.",
        )

        self.assertEqual(compact, rendered)
        self.assertNotEqual(compact, other_source)

    def test_question_text_extraction_supports_string_and_object_items(self):
        result = {
            "questions": [
                " First question? ",
                {"question": "Second\n question?"},
                {"question": ""},
                None,
            ]
        }

        self.assertEqual(
            _question_texts_from_result(result),
            {
                "First question?",
                "Second question?",
            },
        )

    def test_motivation_and_cognitive_can_use_interpretation_question_fallback(self):
        owner = type(
            "Owner",
            (),
            {
                "ai_motivation_questions": {},
                "ai_motivation_interpretation": {
                    "questions": [
                        {"question": "What gives you energy?"},
                    ]
                },
                "ai_cognitive_questions": {},
                "ai_cognitive_interpretation": {
                    "questions": [
                        {"question": "How do you approach unfamiliar problems?"},
                    ]
                },
            },
        )()

        self.assertEqual(
            get_current_question_texts(owner, "motivation"),
            {"What gives you energy?"},
        )
        self.assertEqual(
            get_current_question_texts(owner, "cognitive"),
            {"How do you approach unfamiliar problems?"},
        )

    def test_model_is_registered_with_processes_app(self):
        self.assertIs(
            apps.get_model("processes", "InterviewQuestionNote"),
            InterviewQuestionNote,
        )


class InterviewNotePrivacyDetectorTests(TestCase):
    def test_identifies_pii_without_remote_ner_or_network(self):
        candidate = type(
            "CandidateStub", (), {"first_name": "Taylor", "last_name": "Candidate"},
        )()
        for value in (
            "Anna Exempelson har telefonnummer 0701234567",
            "Contact name@example.org for details.",
            "Call +46701234567 instead.",
            "Personnummer 19900101-1234",
            "The interviewer was John Smith.",
            "I spoke with Taylor.",
            "taylor candidate completed the interview.",
        ):
            with self.subTest(value=value):
                self.assertTrue(
                    contains_interview_note_personal_data(value, candidate)
                )

    def test_allows_non_identifying_interview_content(self):
        candidate = type(
            "CandidateStub", (), {"first_name": "Taylor", "last_name": "Candidate"},
        )()
        for value in (
            "Used a concrete stakeholder example.",
            "Customer Service and Talent Qode are team contexts.",
            "STEN 8 and score 71 are assessment results.",
            "The candidate may need clear instructions.",
            "",
        ):
            with self.subTest(value=value):
                self.assertFalse(
                    contains_interview_note_personal_data(value, candidate)
                )


class InterviewQuestionNoteEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="question-notes-admin",
            email="question-notes-admin@example.com",
            password="test-password",
        )
        self.company = Company.objects.create(name="Question notes company")
        self.unit = OrgUnit.objects.create(
            company=self.company,
            name="Question notes unit",
            unit_code="QUESTION-NOTES",
        )
        self.process = TestProcess.objects.create(
            name="Question notes process",
            provider="sova",
            company=self.company,
            project_code="QUESTION-NOTES-PROJECT",
            account_code="QUESTION-NOTES-ACCOUNT",
            org_unit=self.unit,
            created_by=self.user,
        )
        self.candidate = Candidate.objects.create(
            first_name="Taylor",
            last_name="Candidate",
            email="taylor-question-notes@example.com",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process,
            candidate=self.candidate,
            status="completed",
            ai_personality_questions={
                "questions": [
                    {
                        "question": (
                            "Tell me about a time when you had to "
                            "adapt your usual working style."
                        )
                    }
                ]
            },
            ai_motivation_questions={
                "questions": [
                    {"question": "What gives you energy at work?"}
                ]
            },
            ai_post_interview_decision_support={
                "overall_synthesis": "Existing synthesis",
                "content_blocks": {
                    "wellbeing_tips": "Existing manager advice.",
                },
            },
            ai_post_interview_decision_support_status="completed",
        )
        self.client.force_login(self.user)

        self.list_url = reverse(
            "processes:process_candidate_interview_question_notes",
            kwargs={
                "process_id": self.process.id,
                "candidate_id": self.candidate.id,
            },
        )
        self.update_url = reverse(
            "processes:process_candidate_interview_question_note_update",
            kwargs={
                "process_id": self.process.id,
                "candidate_id": self.candidate.id,
            },
        )
        self.regenerate_url = reverse(
            "processes:process_candidate_post_interview_decision_support_regenerate",
            kwargs={
                "process_id": self.process.id,
                "candidate_id": self.candidate.id,
            },
        )
        self.manager_report_edits_url = reverse(
            "processes:process_candidate_manager_report_text_edits",
            kwargs={
                "process_id": self.process.id,
                "candidate_id": self.candidate.id,
            },
        )
        self.manager_report_edit_save_url = reverse(
            "processes:process_candidate_manager_report_text_edit_update",
            kwargs={
                "process_id": self.process.id,
                "candidate_id": self.candidate.id,
            },
        )

    def post_note(self, **overrides):
        payload = {
            "source": "personality",
            "question": (
                "Tell me about a time when you had to "
                "adapt your usual working style."
            ),
            "note": "Used a concrete stakeholder example.",
        }
        payload.update(overrides)
        return self.client.post(
            self.update_url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_saves_note_against_exact_generated_question(self):
        response = self.post_note(
            question=(
                " Tell me about a time when you had to\n"
                "adapt your usual   working style. "
            ),
        )

        self.assertEqual(response.status_code, 200)
        note = InterviewQuestionNote.objects.get()
        self.assertEqual(note.source, "personality")
        self.assertEqual(
            note.question_text,
            (
                "Tell me about a time when you had to "
                "adapt your usual working style."
            ),
        )
        self.assertEqual(note.note, "Used a concrete stakeholder example.")
        self.assertEqual(note.updated_by, self.user)

    def test_saved_notes_are_available_from_candidate_endpoint(self):
        self.post_note()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["notes"]), 1)
        self.assertEqual(payload["notes"][0]["source"], "personality")
        self.assertEqual(
            payload["notes"][0]["note"],
            "Used a concrete stakeholder example.",
        )

    def test_rejects_note_for_question_not_in_current_generated_questions(self):
        response = self.post_note(
            question="Invented question that was never generated.",
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(InterviewQuestionNote.objects.exists())

    def test_empty_note_removes_existing_saved_note(self):
        self.post_note()
        self.assertTrue(InterviewQuestionNote.objects.exists())

        response = self.post_note(note="   ")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(InterviewQuestionNote.objects.exists())

    def test_editing_question_note_marks_existing_post_interview_result_outdated(self):
        response = self.post_note()

        self.assertEqual(response.status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(
            self.invitation.ai_post_interview_decision_support_status,
            "outdated",
        )
        self.assertEqual(response.json()["post_interview_status"], "outdated")

    def test_regeneration_stream_is_forced_past_saved_result(self):
        self.post_note()

        response = self.client.post(self.regenerate_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.json()["stream_url"].endswith("?force=1")
        )

    def test_manager_report_text_edit_is_saved_per_block_language_and_version(self):
        first_text = "Clarify the next step with the candidate."
        response = self.client.post(
            self.manager_report_edit_save_url,
            data=json.dumps({
                "action": "save",
                "block_key": "wellbeing_tips",
                "language": "en",
                "expected_version": 0,
                "text": first_text,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["edit"]["version"], 1)
        edit = ManagerReportTextEdit.objects.get()
        self.assertEqual(edit.process, self.process)
        self.assertEqual(edit.candidate, self.candidate)
        self.assertEqual(edit.block_key, "wellbeing_tips")
        self.assertEqual(edit.language_code, "en")
        self.assertEqual(edit.text, first_text)
        self.assertEqual(edit.updated_by, self.user)
        self.invitation.refresh_from_db()
        self.assertEqual(
            self.invitation.ai_post_interview_decision_support["content_blocks"]["wellbeing_tips"],
            "Existing manager advice.",
        )

        audit_event = ManagerReportTextEditEvent.objects.get()
        self.assertEqual(audit_event.actor, self.user)
        self.assertEqual(audit_event.version, 1)
        self.assertEqual(audit_event.action, ManagerReportTextEditEvent.Action.SAVED)
        self.assertFalse(hasattr(audit_event, "text"))
        self.assertNotIn(first_text, str(audit_event.__dict__))

        listed = self.client.get(self.manager_report_edits_url)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["language"], "en")
        self.assertEqual(listed.json()["edits"], [response.json()["edit"]])

        updated_text = "Use a specific follow-up question."
        update = self.client.post(
            self.manager_report_edit_save_url,
            data=json.dumps({
                "action": "save",
                "block_key": "wellbeing_tips",
                "language": "en",
                "expected_version": 1,
                "text": updated_text,
            }),
            content_type="application/json",
        )
        self.assertEqual(update.status_code, 200)
        edit.refresh_from_db()
        self.assertEqual(edit.version, 2)
        self.assertEqual(edit.text, updated_text)
        self.assertEqual(ManagerReportTextEditEvent.objects.count(), 2)

    def test_manager_report_text_edits_are_separate_by_language(self):
        english = self.client.post(
            self.manager_report_edit_save_url,
            data=json.dumps({
                "block_key": "wellbeing_tips",
                "language": "en",
                "expected_version": 0,
                "text": "English adjustment.",
            }),
            content_type="application/json",
        )
        self.assertEqual(english.status_code, 200)

        swedish = self.client.post(
            self.manager_report_edit_save_url,
            data=json.dumps({
                "block_key": "wellbeing_tips",
                "language": "sv",
                "expected_version": 0,
                "text": "Svensk justering.",
            }),
            content_type="application/json",
            HTTP_ACCEPT_LANGUAGE="sv",
        )
        self.assertEqual(swedish.status_code, 200)
        self.assertEqual(
            self.client.get(self.manager_report_edits_url).json()["edits"][0]["text"],
            "English adjustment.",
        )
        self.assertEqual(
            self.client.get(
                self.manager_report_edits_url,
                HTTP_ACCEPT_LANGUAGE="sv",
            ).json()["edits"][0]["text"],
            "Svensk justering.",
        )

    def test_manager_report_text_edit_rejects_stale_version_and_non_narrative_blocks(self):
        save = {
            "action": "save",
            "block_key": "wellbeing_tips",
            "language": "en",
            "expected_version": 0,
            "text": "Saved text.",
        }
        self.assertEqual(
            self.client.post(
                self.manager_report_edit_save_url,
                data=json.dumps(save),
                content_type="application/json",
            ).status_code,
            200,
        )

        stale = dict(save, text="Stale text.")
        conflict = self.client.post(
            self.manager_report_edit_save_url,
            data=json.dumps(stale),
            content_type="application/json",
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(ManagerReportTextEdit.objects.get().text, "Saved text.")

        invalid = dict(save, block_key="numerical_score")
        rejected = self.client.post(
            self.manager_report_edit_save_url,
            data=json.dumps(invalid),
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 400)

    def test_manager_report_text_can_be_restored_to_latest_ai_text(self):
        save = self.client.post(
            self.manager_report_edit_save_url,
            data=json.dumps({
                "block_key": "wellbeing_tips",
                "language": "en",
                "expected_version": 0,
                "text": "Manual adjustment.",
            }),
            content_type="application/json",
        )
        self.assertEqual(save.status_code, 200)

        restore = self.client.post(
            self.manager_report_edit_save_url,
            data=json.dumps({
                "action": "restore_ai",
                "block_key": "wellbeing_tips",
                "language": "en",
                "expected_version": 1,
            }),
            content_type="application/json",
        )
        self.assertEqual(restore.status_code, 200)
        self.assertFalse(ManagerReportTextEdit.objects.exists())
        self.assertEqual(ManagerReportTextEditEvent.objects.count(), 2)
        self.assertEqual(
            ManagerReportTextEditEvent.objects.order_by("created_at", "pk").last().action,
            ManagerReportTextEditEvent.Action.RESTORED_AI,
        )

    def test_manager_report_text_edit_respects_tenant_and_editor_permissions(self):
        other_company_user = User.objects.create_user(
            username="other-company-member",
            password="test-password",
        )
        self.client.force_login(other_company_user)
        self.assertEqual(self.client.get(self.manager_report_edits_url).status_code, 403)

        viewer = User.objects.create_user(
            username="question-notes-viewer",
            password="test-password",
        )
        CompanyMember.objects.create(
            company=self.company,
            user=viewer,
            primary_org_unit=self.unit,
            role=CompanyMember.ROLE_VIEWER,
        )
        UserOrgUnitAccess.objects.create(
            user=viewer,
            org_unit=self.unit,
            permission=UserOrgUnitAccess.PERM_VIEWER,
        )
        self.client.force_login(viewer)
        self.assertEqual(self.client.get(self.manager_report_edits_url).status_code, 200)
        denied = self.client.post(
            self.manager_report_edit_save_url,
            data=json.dumps({
                "block_key": "wellbeing_tips",
                "language": "en",
                "expected_version": 0,
                "text": "Viewer should not save this.",
            }),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertFalse(ManagerReportTextEdit.objects.exists())

    def test_existing_note_can_be_edited_or_removed_after_question_regeneration(self):
        self.post_note(note="Original answer")

        self.invitation.ai_personality_questions = {
            "questions": [
                {"question": "A newly generated question?"},
            ]
        }
        self.invitation.save(update_fields=["ai_personality_questions"])

        edit_response = self.post_note(note="Edited answer")
        self.assertEqual(edit_response.status_code, 200)
        self.assertEqual(
            InterviewQuestionNote.objects.get().note,
            "Edited answer",
        )

        delete_response = self.post_note(note="   ")
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(InterviewQuestionNote.objects.exists())

    def test_personal_data_is_saved_with_privacy_advisory(self):
        for value in (
            "Anna Exempelson har telefonnummer 0701234567",
            "Email name@example.org after the interview.",
            "Call 0701234567.",
            "Contact +46701234567.",
            "Swedish personal ID: 19900101-1234",
            "Met John Smith during the interview.",
            "Taylor is available for work.",
        ):
            with self.subTest(value=value):
                response = self.post_note(note=value)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data["ok"])
                self.assertIs(data["possible_personal_data"], True)
                self.assertEqual(InterviewQuestionNote.objects.get().note, value)
                self.invitation.refresh_from_db()
                self.assertEqual(
                    self.invitation.ai_post_interview_decision_support_status,
                    "outdated",
                )
                InterviewQuestionNote.objects.all().delete()

    def test_normal_notes_save_without_privacy_advisory(self):
        response = self.post_note(note="Described a concrete example from work.")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()["possible_personal_data"], False)
        self.assertEqual(
            InterviewQuestionNote.objects.get().note,
            "Described a concrete example from work.",
        )

    def test_empty_note_removal_does_not_trigger_privacy_advisory(self):
        self.post_note(note="Met Anna Exempelson in the new team.")
        response = self.post_note(note="  ")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()["possible_personal_data"], False)
        self.assertFalse(InterviewQuestionNote.objects.exists())

    def test_flagged_edits_save_normally_and_can_be_corrected(self):
        first = self.post_note(note="Worked well in a new team.")
        self.assertEqual(first.status_code, 200)
        self.assertIs(first.json()["possible_personal_data"], False)

        changed = self.post_note(note="Met Anna Exempelson in the new team.")
        self.assertEqual(changed.status_code, 200)
        self.assertIs(changed.json()["possible_personal_data"], True)
        self.assertEqual(
            InterviewQuestionNote.objects.get().note,
            "Met Anna Exempelson in the new team.",
        )

        fixed = self.post_note(note="Met a colleague in the new team.")
        self.assertEqual(fixed.status_code, 200)
        self.assertIs(fixed.json()["possible_personal_data"], False)
        self.assertEqual(
            InterviewQuestionNote.objects.get().note,
            "Met a colleague in the new team.",
        )

        removed = self.post_note(note="   ")
        self.assertEqual(removed.status_code, 200)
        self.assertIs(removed.json()["possible_personal_data"], False)
        self.assertFalse(InterviewQuestionNote.objects.exists())

