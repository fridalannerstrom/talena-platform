from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.processes.access_control import (
    process_edit_access_required,
    process_view_access_required,
)
from apps.processes.models import TestProcess


def _ok_view(request, process_id, candidate_id=None):
    return HttpResponse("ok")


class ProcessCandidateAccessTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.company = Company.objects.create(name="Acme")
        self.unit = OrgUnit.objects.create(
            company=self.company,
            name="Sweden",
            unit_code="SE",
        )

        self.creator = User.objects.create_user(
            username="creator",
            password="test-password",
        )
        self.viewer = User.objects.create_user(
            username="viewer",
            password="test-password",
        )
        self.editor = User.objects.create_user(
            username="editor",
            password="test-password",
        )
        self.own_only = User.objects.create_user(
            username="own-only",
            password="test-password",
        )

        for user in (self.creator, self.viewer, self.editor, self.own_only):
            CompanyMember.objects.create(
                company=self.company,
                user=user,
                primary_org_unit=self.unit,
            )

        UserOrgUnitAccess.objects.create(
            user=self.creator,
            org_unit=self.unit,
            permission="editor",
        )
        UserOrgUnitAccess.objects.create(
            user=self.viewer,
            org_unit=self.unit,
            permission="viewer",
        )
        UserOrgUnitAccess.objects.create(
            user=self.editor,
            org_unit=self.unit,
            permission="editor",
        )
        UserOrgUnitAccess.objects.create(
            user=self.own_only,
            org_unit=self.unit,
            permission="own",
        )

        self.shared_process = TestProcess.objects.create(
            name="Shared process",
            company=self.company,
            org_unit=self.unit,
            created_by=self.creator,
            provider="sova",
            account_code="A",
            project_code="P",
        )
        self.own_process = TestProcess.objects.create(
            name="Own process",
            company=self.company,
            org_unit=self.unit,
            created_by=self.own_only,
            provider="sova",
            account_code="A",
            project_code="P2",
        )

    def _request_for(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_viewer_can_open_colleague_process_candidate_endpoint(self):
        protected = process_view_access_required(_ok_view)
        response = protected(
            self._request_for(self.viewer),
            process_id=self.shared_process.id,
            candidate_id=1,
        )
        self.assertEqual(response.status_code, 200)

    def test_own_user_cannot_open_colleague_process_candidate_endpoint(self):
        protected = process_view_access_required(_ok_view)
        response = protected(
            self._request_for(self.own_only),
            process_id=self.shared_process.id,
            candidate_id=1,
        )
        self.assertEqual(response.status_code, 403)

    def test_own_user_can_open_own_process_candidate_endpoint(self):
        protected = process_view_access_required(_ok_view)
        response = protected(
            self._request_for(self.own_only),
            process_id=self.own_process.id,
            candidate_id=1,
        )
        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_call_edit_endpoint(self):
        protected = process_edit_access_required(_ok_view)
        response = protected(
            self._request_for(self.viewer),
            process_id=self.shared_process.id,
            candidate_id=1,
        )
        self.assertEqual(response.status_code, 403)

    def test_editor_can_call_edit_endpoint(self):
        protected = process_edit_access_required(_ok_view)
        response = protected(
            self._request_for(self.editor),
            process_id=self.shared_process.id,
            candidate_id=1,
        )
        self.assertEqual(response.status_code, 200)
