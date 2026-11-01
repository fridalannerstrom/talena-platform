"""Issue #362: Sent assessments and assessment link share a single tab.

Do not log candidate-specific Sova links or credentials in these tests.
"""
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.processes.models import Candidate, TestInvitation, TestProcess


class AssessmentLinkStateTests(SimpleTestCase):
    def _invitation(self, url, status="sent"):
        return TestInvitation(assessment_url=url, status=status)

    def test_valid_https_link_can_be_displayed(self):
        self.assertEqual(
            self._invitation("https://assessment.example.test/start?key=abc").assessment_link_state,
            "available",
        )

    def test_missing_invalid_and_expired_links_are_not_shareable(self):
        cases = [
            (None, "sent", "missing"),
            ("", "sent", "missing"),
            ("https://assessment.example.test/start?key=abc", "expired", "expired"),
            ("javascript:alert(1)", "sent", "invalid"),
            ("http://assessment.example.test/start?key=abc", "sent", "invalid"),
            ("https:///missing-host", "sent", "invalid"),
            ("https://user:password@assessment.example.test/", "sent", "invalid"),
            ("https://assessment.example.test:invalid/start", "sent", "invalid"),
            ("https://assessment.example.test/start\n", "sent", "invalid"),
        ]
        for url, status, expected in cases:
            with self.subTest(status=status, expected=expected):
                self.assertEqual(
                    self._invitation(url, status).assessment_link_state,
                    expected,
                )


class AssessmentTabTemplateTests(SimpleTestCase):
    PATHS = (
        "templates/customer/processes/_candidate_detail_sheet.html",
        "templates/admin/accounts/companies/company_candidate_sheet.html",
        "templates/admin/accounts/customer/candidate_detail.html",
    )

    def test_merged_tab_in_customer_and_both_admin_mirrors(self):
        for path in self.PATHS:
            with self.subTest(path=path):
                source = (Path(settings.BASE_DIR) / path).read_text(encoding="utf-8")
                self.assertEqual(source.count('data-tab-target="tests"'), 1)
                self.assertEqual(source.count('data-tab-panel="tests"'), 1)
                self.assertNotIn('data-tab-target="link"', source)
                self.assertNotIn('data-tab-panel="link"', source)
                self.assertEqual(source.count("data-candidate-assessment-link"), 1)
                self.assertLess(
                    source.index("data-candidate-assessment-link"),
                    source.index('data-tab-panel="activity"'),
                )
                self.assertIn('invitation.assessment_link_state == "available"', source)
                self.assertIn('invitation.assessment_link_state == "expired"', source)
                self.assertIn('invitation.assessment_link_state == "invalid"', source)
                self.assertIn('value="{{ invitation.assessment_url }}"', source)

    def test_old_customer_tab_api_maps_link_to_tests(self):
        source = (
            Path(settings.BASE_DIR) / "templates/customer/processes/process_base.html"
        ).read_text(encoding="utf-8")
        self.assertIn('if (tabTarget === "link") tabTarget = "tests";', source)


class CandidateAssessmentLinkAccessTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Candidate company")
        self.foreign_company = Company.objects.create(name="Other company")
        self.unit = OrgUnit.objects.create(company=self.company, name="Division A", unit_code="DIV-A")
        self.foreign_unit = OrgUnit.objects.create(
            company=self.foreign_company, name="Division B", unit_code="DIV-B"
        )
        self.user = User.objects.create_user(username="assessment-tab-user", password="unused")
        self.other_user = User.objects.create_user(username="assessment-tab-other", password="unused")
        CompanyMember.objects.create(
            company=self.company, user=self.user, primary_org_unit=self.unit,
        )
        UserOrgUnitAccess.objects.create(
            user=self.user, org_unit=self.unit, permission="editor",
        )
        CompanyMember.objects.create(
            company=self.foreign_company, user=self.other_user, primary_org_unit=self.foreign_unit,
        )
        UserOrgUnitAccess.objects.create(
            user=self.other_user, org_unit=self.foreign_unit, permission="editor",
        )
        self.project = TestProcess.objects.create(
            name="Sales", company=self.company, org_unit=self.unit,
            created_by=self.user, account_code="SOVA", project_code="PQ",
        )
        self.foreign_project = TestProcess.objects.create(
            name="Foreign", company=self.foreign_company, org_unit=self.foreign_unit,
            created_by=self.other_user, account_code="SOVA", project_code="PQ",
        )
        self.candidate = Candidate.objects.create(
            first_name="Alex", last_name="Test", email="tab-alex@example.test",
        )
        self.foreign_candidate = Candidate.objects.create(
            first_name="Sam", last_name="Test", email="tab-sam@example.test",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.project, candidate=self.candidate,
            status="sent", assessment_url="https://sova.example.test/start?key=for-alex",
        )
        self.foreign_invitation = TestInvitation.objects.create(
            process=self.foreign_project, candidate=self.foreign_candidate,
            status="sent", assessment_url="https://sova.example.test/start?key=for-sam",
        )
        self.client.force_login(self.user)

    def _get(self, process=None, candidate=None, lang="sv"):
        # Avoid unrelated AI/assessment rendering while keeping the actual
        # authenticated view, project/invitation scope, and Django template.
        process = process or self.project
        candidate = candidate or self.candidate
        target = reverse(
            "processes:process_candidate_detail",
            args=[process.pk, candidate.pk],
        )
        with patch("apps.processes.views.build_candidate_detail_context") as context:
            context.return_value = {
                "process": process,
                "candidate": candidate,
                "invitation": self.invitation,
                "sent_assessments": [
                    {"activity": "Personality", "status": "sent"},
                ],
                "tests_sent_count": 1,
                "tests_completed_count": 0,
                "activity_events": [],
                "is_historical": False,
            }
            return self.client.get(
                target, HTTP_X_REQUESTED_WITH="XMLHttpRequest", HTTP_ACCEPT_LANGUAGE=lang,
            )

    def test_link_above_assessments_in_one_swedish_tab(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("Skickade tester", html)
        self.assertIn("https://sova.example.test/start?key=for-alex", html)
        self.assertIn("Personality", html)
        self.assertLess(html.index("data-candidate-assessment-link"), html.index("Personality"))
        self.assertNotIn('data-tab-target="link"', html)

    def test_unavailable_link_is_not_in_rendered_markup(self):
        for url, status, hint in (
            ("", "created", "Ingen testlänk finns ännu"),
            ("javascript:alert(1)", "sent", "Testlänken är ogiltig"),
            ("https://sova.example.test/start?key=for-alex", "expired", "Testlänken har gått ut"),
        ):
            with self.subTest(status=status, url_kind=hint):
                self.invitation.assessment_url = url
                self.invitation.status = status
                self.invitation.save(update_fields=["assessment_url", "status"])
                response = self._get()
                self.assertEqual(response.status_code, 200)
                html = response.content.decode("utf-8")
                self.assertIn(hint, html)
                self.assertNotIn('id="candidateAssessmentUrl"', html)
                self.assertNotIn('data-tab-target="link"', html)
                self.assertNotIn('key=for-alex', html)

    def test_cannot_fetch_foreign_candidate_link(self):
        response = self._get(
            process=self.foreign_project, candidate=self.foreign_candidate,
        )
        self.assertIn(response.status_code, (403, 404))
        self.assertNotIn("for-sam", response.content.decode("utf-8"))

    def test_cross_project_candidate_id_does_not_return_assessment_link(self):
        response = self._get(candidate=self.foreign_candidate)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("for-alex", response.content.decode("utf-8"))
        self.assertNotIn("for-sam", response.content.decode("utf-8"))
