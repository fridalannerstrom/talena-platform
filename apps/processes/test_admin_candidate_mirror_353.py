"""Ticket #353: the internal candidate detail is a read-only customer mirror.

Synthetic data only; HTTP and persistence regressions, no Sova/OpenAI calls.
"""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.processes.models import Candidate, TestInvitation, TestProcess


class AdminCandidateMirror353Tests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Mirror Test Company")
        self.other_company = Company.objects.create(name="Other Mirror Company")
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Mirror Unit", unit_code="M-353",
        )
        self.customer = User.objects.create_user(
            username="mirror-customer", email="customer-353@example.test", password="unused",
        )
        CompanyMember.objects.create(
            company=self.company, user=self.customer, primary_org_unit=self.unit,
        )
        UserOrgUnitAccess.objects.create(
            user=self.customer, org_unit=self.unit, permission="editor",
        )
        self.admin = User.objects.create_superuser(
            username="mirror-admin", email="admin-353@example.test", password="unused",
        )
        self.process = TestProcess.objects.create(
            company=self.company, org_unit=self.unit, created_by=self.customer,
            name="Customer's original recruitment", purpose="hiring",
            account_code="MODERN", project_code="PQ-MQ",
            selected_tests=["personality", "motivation"],
            candidate_language="sv",
        )
        self.candidate = Candidate.objects.create(
            first_name="Synthetic", last_name="Candidate",
            email="candidate-353@example.test",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process, candidate=self.candidate, status="created",
            source="invited",
        )
        self.customer_url = reverse(
            "processes:process_candidate_detail",
            args=[self.process.pk, self.candidate.pk],
        )
        self.company_admin_url = reverse(
            "accounts:company_process_candidate_detail",
            args=[self.company.pk, self.process.pk, self.candidate.pk],
        )
        self.direct_admin_url = reverse(
            "accounts:admin_candidate_detail", args=[self.process.pk, self.candidate.pk],
        )

    def _get(self, user, url, language="sv"):
        self.client.force_login(user)
        return self.client.get(
            url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT_LANGUAGE=language,
        )

    def test_admin_and_customer_render_the_same_candidate_sheet(self):
        customer = self._get(self.customer, self.customer_url)
        admin = self._get(self.admin, self.company_admin_url)
        self.assertEqual(customer.status_code, 200)
        self.assertEqual(admin.status_code, 200)
        for response in (customer, admin):
            with self.subTest(user=response.wsgi_request.user.username):
                html = response.content.decode("utf-8")
                self.assertIn("candidate-sheet-layout--floating-ai", html)
                self.assertIn('data-tab-target="tests"', html)
                self.assertIn('data-tab-target="result"', html)
                self.assertIn('data-tab-target="overview"', html)
                self.assertIn(self.candidate.first_name, html)
                self.assertIn(self.candidate.email, html)
        self.assertIn(
            'data-admin-candidate-mirror', admin.content.decode("utf-8"),
        )
        self.assertIs(
            admin.context["invitation"].pk == customer.context["invitation"].pk,
            True,
        )
        self.assertEqual(
            admin.context["sent_assessments"], customer.context["sent_assessments"],
        )
        self.assertEqual(
            admin.context["personality_interpretation_status"],
            customer.context["personality_interpretation_status"],
        )
        self.assertEqual(
            admin.context["can_manage_candidate_results"], False,
        )

    def test_missing_ai_and_missing_results_are_identical_states(self):
        self.process.purpose = "flexible"
        self.process.save(update_fields=["purpose"])
        customer = self._get(self.customer, self.customer_url)
        admin = self._get(self.admin, self.company_admin_url)
        self.assertEqual(admin.status_code, 200)
        for response in (customer, admin):
            self.assertFalse(response.context["has_any_results"])
            self.assertEqual(
                response.context["personality_interpretation_status"],
                "not_started",
            )
            self.assertNotIn(
                "Unrequested AI text", response.content.decode("utf-8"),
            )
        self.invitation.refresh_from_db()
        self.assertEqual(
            self.invitation.ai_personality_interpretation_status, "not_started",
        )
        self.assertEqual(self.invitation.ai_personality_interpretation, {})

    def test_saved_ai_is_shared_not_regenerated_for_admin(self):
        self.invitation.ai_personality_interpretation = {
            "summary": "Synthetic saved interpretation only",
        }
        self.invitation.ai_personality_interpretation_status = "completed"
        self.invitation.save(update_fields=[
            "ai_personality_interpretation", "ai_personality_interpretation_status",
        ])
        customer = self._get(self.customer, self.customer_url)
        admin = self._get(self.admin, self.company_admin_url)
        self.assertEqual(
            admin.context["personality_interpretation"],
            customer.context["personality_interpretation"],
        )
        self.assertEqual(
            admin.context["personality_interpretation_status"],
            "completed",
        )
        self.invitation.refresh_from_db()
        self.assertEqual(
            self.invitation.ai_personality_interpretation["summary"],
            "Synthetic saved interpretation only",
        )

    def test_just_opening_admin_does_not_mutate_ai_or_trigger_orders(self):
        self.client.force_login(self.admin)
        before = (
            self.invitation.ai_personality_interpretation,
            self.invitation.ai_personality_interpretation_status,
            self.invitation.ai_summary,
            self.invitation.ai_summary_status,
            self.invitation.assessment_url,
            self.invitation.request_id,
        )
        for url in (self.company_admin_url, self.direct_admin_url):
            response = self.client.get(
                url, HTTP_X_REQUESTED_WITH="XMLHttpRequest",
                HTTP_ACCEPT_LANGUAGE="sv",
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "candidate-sheet-layout--floating-ai")
        self.invitation.refresh_from_db()
        after = (
            self.invitation.ai_personality_interpretation,
            self.invitation.ai_personality_interpretation_status,
            self.invitation.ai_summary,
            self.invitation.ai_summary_status,
            self.invitation.assessment_url,
            self.invitation.request_id,
        )
        self.assertEqual(before, after)

    def test_admin_is_scoped_to_given_company_process_and_invitation(self):
        other_process = TestProcess.objects.create(
            company=self.other_company, created_by=self.customer,
            name="Other recruitment", account_code="MODERN", project_code="MQ",
        )
        # Same global candidate in two independent projects: data must not mix.
        other_invitation = TestInvitation.objects.create(
            process=other_process, candidate=self.candidate, status="completed",
            ai_personality_interpretation={
                "summary": "SENTINEL_OTHER_COMPANY_353",
            },
            ai_personality_interpretation_status="completed",
        )
        self.client.force_login(self.admin)
        mismatch = reverse(
            "accounts:company_process_candidate_detail",
            args=[self.company.pk, other_process.pk, self.candidate.pk],
        )
        self.assertEqual(self.client.get(mismatch).status_code, 404)
        response = self.client.get(
            self.company_admin_url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.context["invitation"].pk, self.invitation.pk)
        self.assertNotIn(
            "SENTINEL_OTHER_COMPANY_353", response.content.decode("utf-8"),
        )
        self.assertNotEqual(response.context["invitation"].pk, other_invitation.pk)

    def test_removed_candidate_not_exposed_as_active_mirror(self):
        self.invitation.removed_from_process_at = timezone.now()
        self.invitation.save(update_fields=["removed_from_process_at"])
        self.client.force_login(self.admin)
        for url in (self.company_admin_url, self.direct_admin_url):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_customer_cannot_open_internal_admin_mirror(self):
        self.client.force_login(self.customer)
        for url in (self.company_admin_url, self.direct_admin_url):
            self.assertEqual(
                self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code,
                403,
            )

    def test_company_page_candidate_links_stay_in_internal_admin_route(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse(
            "accounts:company_process_detail",
            args=[self.company.pk, self.process.pk],
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.company_admin_url)
        self.assertNotContains(response,
            'data-sheet-url="' + self.customer_url + '"')


class AdminCandidateMirrorSource353Tests(SimpleTestCase):
    def test_admin_templates_include_the_actual_customer_sheet(self):
        root = Path(settings.BASE_DIR)
        source = (root / "templates/admin/accounts/companies/company_candidate_sheet.html"
                  ).read_text(encoding="utf-8")
        direct = (root / "templates/admin/accounts/customer/candidate_detail.html"
                  ).read_text(encoding="utf-8")
        self.assertIn("customer/processes/_candidate_detail_sheet.html", source)
        self.assertIn("admin/accounts/companies/company_candidate_sheet.html", direct)
        self.assertNotIn("js-regenerate-summary", source)
        self.assertNotIn('data-insights-panel="personality"', source)
        self.assertIn("data-admin-candidate-mirror", source)
        self.assertIn("data-manager-report-activity-panel", source)

    def test_admin_does_not_auto_generate_on_open(self):
        root = Path(settings.BASE_DIR)
        source = (root / "templates/admin/accounts/companies/company_process_detail.html"
                  ).read_text(encoding="utf-8")
        self.assertNotIn("initCandidateSheetAiObserver()", source)
        self.assertNotIn("initCandidatePurposeFitStream(", source)
        self.assertNotIn("initCandidateSummaryStream(", source)
        self.assertIn("admin-candidate-mirror-353.js", source)
        view_source = (root / "apps/accounts/views.py").read_text(encoding="utf-8")
        self.assertIn("build_shared_candidate_detail_context", view_source)
        self.assertNotIn("generate_general_candidate_insights(", view_source)
