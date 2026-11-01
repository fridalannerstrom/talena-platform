"""Ticket #367: assessment-specific statuses, without global-status inference."""
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.processes.models import TestProcess, Candidate, TestInvitation, AssessmentUsage
from apps.processes.services.project_assessment_status import (
    project_test_columns, invitation_test_statuses, test_key,
)


class ProjectAssessmentStatusUnitTests(SimpleTestCase):
    def process(self, selected_tests, name=""):
        return SimpleNamespace(
            selected_tests=selected_tests, project_name_snapshot=name,
            sova_project_name="", account_code="A", project_code="PQ_MQ",
        )

    def invitation(self, *, status="sent", activities=None, usages=()):
        return SimpleNamespace(
            status=status, invited_at=None, sova_activities=activities or [],
            sova_payload=None, sova_phases=None, status_usages=list(usages),
        )

    def result(self, invitation, tests=("personality", "motivation"), language="sv"):
        cols = project_test_columns(self.process(list(tests)))
        return {cell["key"]: cell for cell in
                invitation_test_statuses(invitation, cols, language)}

    def test_project_has_exact_dynamic_columns(self):
        self.assertEqual([c["key"] for c in project_test_columns(
            self.process(["PQ", "MQ", "L", "N", "V"])
        )], ["personality", "motivation", "verbal", "logical", "numerical"])
        self.assertEqual([c["key"] for c in project_test_columns(
            self.process(["logical", "personality"])
        )], ["personality", "logical"])
        self.assertEqual(project_test_columns(self.process([])), [])

    def test_modern_projects_snapshot_fallback(self):
        self.assertEqual([c["key"] for c in project_test_columns(
            self.process([], "Personality + Numerical + Logical")
        )], ["personality", "logical", "numerical"])

    def test_independent_completion_order_and_no_global_inference(self):
        # The overall invitation may already be completed even when the
        # individual test's status is not reported by Sova.
        inv = self.invitation(status="completed", activities=[
            {"activity": "Personality Questionnaire", "status": "completed"},
            {"activity": "Motivation Questionnaire", "status": "started"},
            {"activity": "Numerical reasoning", "status": "not started"},
        ])
        data = self.result(inv, ("personality", "motivation", "numerical", "logical"))
        self.assertEqual({k: v["state"] for k, v in data.items()}, {
            "personality": "completed", "motivation": "started",
            "logical": "unknown", "numerical": "not_started",
        })

    def test_synthetic_sova_callback_overrides_older_activity(self):
        inv = self.invitation(activities=[
            {"activity": "PQ", "status": "started"},
            {"activity": "PQ", "status": "finished"},
            {"activity": "MQ", "status": "in_progress"},
        ])
        state = self.result(inv)
        self.assertEqual(state["personality"]["state"], "completed")
        self.assertEqual(state["motivation"]["state"], "started")

    def test_unsent_expired_failed_unknown_and_missing_states(self):
        for invitation_status, wanted in (
            ("created", "not_sent"), ("sent", "unknown"),
            ("completed", "unknown"), ("expired", "expired"), ("failed", "failed"),
        ):
            with self.subTest(status=invitation_status):
                data = self.result(self.invitation(status=invitation_status))
                self.assertEqual(data["personality"]["state"], wanted)

    def test_sova_explicit_not_assigned_is_not_guessed_from_missing_data(self):
        data = self.result(self.invitation(activities=[
            {"activity": "personality", "status": "not_assigned"}
        ]))
        self.assertEqual(data["personality"]["state"], "not_assigned")
        self.assertEqual(data["motivation"]["state"], "unknown")

    def test_sova_per_activity_failure_is_not_interpreted_as_completed(self):
        data = self.result(self.invitation(activities=[
            {"activity": "personality", "status": "failed"}
        ]))
        self.assertEqual(data["personality"]["state"], "activity_failed")

    def test_stored_usage_status_is_not_global_invitation_status(self):
        person = SimpleNamespace(
            assessment_type="personality", status="started",
            completed_at_is_estimated=False,
        )
        motivation = SimpleNamespace(
            assessment_type="motivation", status="completed",
            completed_at_is_estimated=True,
        )
        data = self.result(self.invitation(status="completed", usages=[person, motivation]))
        self.assertEqual(data["personality"]["state"], "started")
        self.assertEqual(data["motivation"]["state"], "unknown")

    def test_phase_fallback_and_english_labels(self):
        inv = self.invitation()
        inv.sova_phases = [
            {"activities": [{"name": "Verbal reasoning", "status": "complete"}]},
        ]
        data = self.result(inv, ("verbal",), "en")
        self.assertEqual(data["verbal"]["label"], "Completed")
        self.assertEqual(data["verbal"]["state"], "completed")
        self.assertIn("Sova", data["verbal"]["title"])

    def test_per_test_status_no_cross_test_name_match(self):
        self.assertEqual(test_key("Numerical reasoning"), "numerical")
        self.assertEqual(test_key("L"), "logical")
        self.assertIsNone(test_key("Unrelated general activity"))


class ProjectAssessmentStatusIntegrationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="A")
        self.other = Company.objects.create(name="B")
        self.unit = OrgUnit.objects.create(company=self.company, name="Sweden", unit_code="A-SE")
        self.other_unit = OrgUnit.objects.create(company=self.other, name="Other", unit_code="B-SE")
        self.user = User.objects.create_user(username="pertest-editor", password="x")
        self.outsider = User.objects.create_user(username="pertest-other", password="x")
        for u, co, unit in ((self.user, self.company, self.unit),
                            (self.outsider, self.other, self.other_unit)):
            CompanyMember.objects.create(user=u, company=co, primary_org_unit=unit)
            UserOrgUnitAccess.objects.create(user=u, org_unit=unit, permission="editor")
        self.project = TestProcess.objects.create(
            name="Sales", company=self.company, org_unit=self.unit,
            created_by=self.user, account_code="TALENA", project_code="PQ_MQ",
            selected_tests=["personality", "motivation"],
        )
        self.foreign_project = TestProcess.objects.create(
            name="Other", company=self.other, org_unit=self.other_unit,
            created_by=self.outsider, account_code="TALENA",
            project_code="PQ", selected_tests=["personality"],
        )
        candidate = Candidate.objects.create(
            first_name="Alex", last_name="Case", email="status-alex@example.test",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.project, candidate=candidate, status="completed",
            sova_activities=[
                {"activity": "Personality Questionnaire", "status": "completed"},
                {"activity": "Motivation Questionnaire", "status": "started"},
            ],
        )
        self.foreign_invitation = TestInvitation.objects.create(
            process=self.foreign_project, candidate=candidate, status="completed",
            sova_activities=[{"activity": "Personality", "status": "started"}],
        )
        self.client.force_login(self.user)

    def test_customer_table_has_dynamic_tests_and_no_global_status(self):
        response = self.client.get(
            reverse("processes:process_detail", args=[self.project.pk]),
            HTTP_ACCEPT_LANGUAGE="sv",
        )
        self.assertEqual(response.status_code, 200)
        markup = response.content.decode("utf8")
        self.assertIn('data-test-header', markup)
        self.assertIn("Personlighet", markup)
        self.assertIn("Motivation", markup)
        self.assertIn("Genomfört", markup)
        self.assertIn("Påbörjat", markup)
        # The parent layout retains a legacy JavaScript selector as a
        # fallback, but the actual candidate table has no total-status cell.
        table = markup.split(
            '<table class="table table-hover align-middle mb-0 process-table">',
            1,
        )[1].split("</table>", 1)[0]
        self.assertNotIn('data-status-badge="1"', table)
        self.assertIn('data-test-key="personality"', markup)

    def test_customer_statuses_use_icons_with_accessible_sv_tooltips(self):
        response = self.client.get(
            reverse("processes:process_detail", args=[self.project.pk]),
            HTTP_ACCEPT_LANGUAGE="sv",
        )
        self.assertEqual(response.status_code, 200)
        markup = response.content.decode("utf8")
        self.assertIn('data-state="completed"', markup)
        self.assertIn('data-state="started"', markup)
        self.assertIn('class="talena-assessment-state__symbol"', markup)
        self.assertIn('title="Genomfört: ', markup)
        self.assertIn('aria-label="Påbörjat. ', markup)
        self.assertIn('<span class="visually-hidden talena-assessment-state__label">', markup)
        self.assertNotIn('class="talena-assessment-state__icon"', markup)

    def test_icons_and_english_tooltips_are_present_in_polling_data(self):
        response = self.client.get(
            reverse("processes:process_invitation_statuses", args=[self.project.pk]),
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 200)
        assessments = response.json()["invitations"][0]["assessments"]
        self.assertEqual([cell["label"] for cell in assessments], ["Completed", "Started"])
        self.assertTrue(all(cell["icon_path"].startswith("M") for cell in assessments))
        self.assertNotEqual(assessments[0]["icon_path"], assessments[1]["icon_path"])

    def test_polling_api_reflects_updated_per_activity_status(self):
        url = reverse("processes:process_invitation_statuses", args=[self.project.pk])
        response = self.client.get(url, HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 200)
        first = response.json()["invitations"][0]["assessments"]
        self.assertEqual({row["key"]: row["state"] for row in first},
                         {"personality": "completed", "motivation": "started"})
        self.invitation.sova_activities = [
            {"activity": "Personality", "status": "completed"},
            {"activity": "Motivation", "status": "completed"},
        ]
        self.invitation.save(update_fields=["sova_activities"])
        updated = self.client.get(url, HTTP_ACCEPT_LANGUAGE="sv").json()
        self.assertEqual([s["label"] for s in updated["invitations"][0]["assessments"]],
                         ["Genomfört", "Genomfört"])

    def test_never_expose_another_company_or_project_status(self):
        url = reverse("processes:process_invitation_statuses", args=[self.foreign_project.pk])
        response = self.client.get(url, HTTP_ACCEPT_LANGUAGE="sv")
        self.assertIn(response.status_code, (403, 404))
        self.assertNotIn("assessments", response.content.decode("utf8"))

    def test_same_candidate_can_have_two_different_project_statuses(self):
        result = self.client.get(reverse(
            "processes:process_invitation_statuses", args=[self.project.pk]
        )).json()
        self.assertEqual(result["invitations"][0]["assessments"][0]["state"], "completed")
        self.client.force_login(self.outsider)
        result = self.client.get(reverse(
            "processes:process_invitation_statuses", args=[self.foreign_project.pk]
        )).json()
        self.assertEqual(result["invitations"][0]["assessments"][0]["state"], "started")

    def test_admin_mirrors_have_per_test_headers(self):
        self.client.force_login(self.user)
        from pathlib import Path
        from django.conf import settings
        for path in (
            "templates/admin/accounts/customer/process_detail.html",
            "templates/admin/accounts/companies/company_process_detail.html",
        ):
            text = (Path(settings.BASE_DIR) / path).read_text(encoding="utf-8")
            self.assertIn('data-test-header', text)
            self.assertIn('data-project-test-statuses', text)
            self.assertIn('_assessment_status_cell.html', text)
