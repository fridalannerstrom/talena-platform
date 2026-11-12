"""HTTP-level tenant and org-unit authorization regressions (issue #309).

Exercise resolved URLs, rather than calling permission helpers directly. This
catches accidental removal of central URL wrappers during future refactors.
All data is synthetic and isolated in the Django test database.
"""

import json

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess,
)
from apps.processes.interview_question_models import InterviewQuestionNote
from apps.processes.models import (
    Candidate, ProcessRoleContext, TestInvitation, TestProcess,
)


class CandidateTenantAuthorizationTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(name="Example company A")
        self.company_b = Company.objects.create(name="Example company B")
        self.unit_a = OrgUnit.objects.create(
            company=self.company_a, name="Team A", unit_code="TEAM-A",
        )
        self.unit_hidden = OrgUnit.objects.create(
            company=self.company_a, name="Separate team", unit_code="TEAM-X",
        )
        self.unit_b = OrgUnit.objects.create(
            company=self.company_b, name="Team B", unit_code="TEAM-B",
        )

        def member(username, company, unit=None, permission=None):
            user = User.objects.create_user(username=username, password="unused")
            CompanyMember.objects.create(
                company=company, user=user, primary_org_unit=unit,
            )
            if permission is not None:
                UserOrgUnitAccess.objects.create(
                    user=user, org_unit=unit, permission=permission,
                )
            return user

        self.creator = member("tenant-creator", self.company_a, self.unit_a, "editor")
        self.editor = member("tenant-editor", self.company_a, self.unit_a, "editor")
        self.viewer = member("tenant-viewer", self.company_a, self.unit_a, "viewer")
        self.own_only = member("tenant-own", self.company_a, self.unit_a, "own")
        self.unscoped = member("tenant-no-unit", self.company_a)
        self.other_unit = member(
            "tenant-other-unit", self.company_a, self.unit_hidden, "viewer"
        )
        self.other_tenant = member("tenant-other-company", self.company_b, self.unit_b, "editor")

        self.process = TestProcess.objects.create(
            name="Confidential process A", provider="sova",
            company=self.company_a, org_unit=self.unit_a,
            created_by=self.creator, project_code="PROJECT-A", account_code="A",
        )
        self.process_owned = TestProcess.objects.create(
            name="Owned by own-only user", provider="sova",
            company=self.company_a, org_unit=self.unit_a,
            created_by=self.own_only, project_code="PROJECT-OWN", account_code="A",
        )
        self.process_b = TestProcess.objects.create(
            name="Confidential process B", provider="sova",
            company=self.company_b, org_unit=self.unit_b,
            created_by=self.other_tenant, project_code="PROJECT-B", account_code="B",
        )

        self.candidate = Candidate.objects.create(
            first_name="Case", last_name="Example", email="case@example.org",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process, candidate=self.candidate, status="completed",
            ai_personality_questions={"questions": [{"question": "Describe a challenge."}]},
        )
        self.owned_invitation = TestInvitation.objects.create(
            process=self.process_owned, candidate=self.candidate, status="completed",
        )
        self.note_payload = {
            "source": "personality",
            "question": "Describe a challenge.",
            "note": "Explained how the group worked together.",
        }

    def url(self, name, *, process=None, candidate=True):
        process = process or self.process
        kwargs = {"pk": process.pk} if name in (
            "process_invitation_statuses", "process_role_context",
        ) else {"process_id": process.pk, "candidate_id": self.candidate.pk}
        return reverse("processes:" + name, kwargs=kwargs)

    def note_post(self, process=None):
        return self.client.post(
            self.url("process_candidate_interview_question_note_update", process=process),
            data=json.dumps(self.note_payload),
            content_type="application/json",
        )

    def test_other_company_cannot_read_candidate_or_ai_data(self):
        self.client.force_login(self.other_tenant)
        for route in (
            "process_candidate_interview_question_notes",
            "process_candidate_detail",
            "process_candidate_final_output",
            "process_invitation_statuses",
            "process_role_context",
        ):
            with self.subTest(route=route):
                response = self.client.get(self.url(route))
                self.assertEqual(response.status_code, 403)
                self.assertNotIn(b"Confidential process A", response.content)
        self.assertEqual(self.note_post().status_code, 403)
        self.assertFalse(InterviewQuestionNote.objects.exists())

    def test_same_company_without_org_unit_permission_cannot_read(self):
        for user in (self.unscoped, self.other_unit, self.own_only):
            self.client.force_login(user)
            for route in (
                "process_invitation_statuses",
                "process_role_context",
                "process_candidate_interview_question_notes",
                "process_candidate_final_output",
            ):
                with self.subTest(user=user.username, route=route):
                    self.assertEqual(self.client.get(self.url(route)).status_code, 403)
            with self.subTest(user=user.username, route="note_update"):
                self.assertEqual(self.note_post().status_code, 403)

        self.assertFalse(InterviewQuestionNote.objects.exists())

    def test_viewer_can_read_but_cannot_modify_process_content(self):
        self.client.force_login(self.viewer)
        self.assertEqual(
            self.client.get(self.url("process_invitation_statuses")).status_code, 200,
        )
        self.assertEqual(
            self.client.get(self.url("process_candidate_interview_question_notes")).status_code,
            200,
        )
        self.assertEqual(self.note_post().status_code, 403)
        self.assertEqual(
            self.client.post(
                self.url("process_candidate_interview_notes_update"),
                data=json.dumps({"interview_notes": "Must never be stored"}),
                content_type="application/json",
            ).status_code,
            403,
        )
        self.assertFalse(ProcessRoleContext.objects.filter(process=self.process).exists())
        self.assertEqual(
            self.client.post(self.url("process_role_context"), data={}).status_code,
            403,
        )
        self.assertFalse(ProcessRoleContext.objects.filter(process=self.process).exists())
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.interview_notes, "")
        self.assertFalse(InterviewQuestionNote.objects.exists())

    def test_editor_can_save_note_and_view_status(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.note_post().status_code, 200)
        self.assertEqual(InterviewQuestionNote.objects.count(), 1)
        self.assertEqual(
            self.client.get(self.url("process_invitation_statuses")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(self.url("process_candidate_interview_question_notes"))
            .json()["notes"][0]["note"],
            self.note_payload["note"],
        )

    def test_own_permission_allows_own_process_only(self):
        self.client.force_login(self.own_only)
        self.assertEqual(
            self.client.get(
                self.url("process_invitation_statuses", process=self.process_owned)
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                self.url(
                    "process_candidate_interview_question_notes",
                    process=self.process_owned,
                )
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(self.url("process_invitation_statuses")).status_code,
            403,
        )

    def test_authorized_process_cannot_read_candidate_from_another_process(self):
        # Even within the same tenant, the candidate must belong to the
        # process referenced in the URL.
        other_candidate = Candidate.objects.create(
            first_name="Other", last_name="Person", email="other@example.org",
        )
        TestInvitation.objects.create(
            process=self.process_b, candidate=other_candidate, status="completed",
        )
        self.client.force_login(self.editor)
        bad_url = reverse(
            "processes:process_candidate_interview_question_notes",
            kwargs={"process_id": self.process.id, "candidate_id": other_candidate.id},
        )
        response = self.client.get(bad_url)
        self.assertEqual(response.status_code, 404)
