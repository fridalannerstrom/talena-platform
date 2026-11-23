"""Regression tests for staff working in a real customer candidate workspace.

All fixtures are synthetic. No Sova/OpenAI calls are needed.
"""
import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.processes.models import Candidate, TestInvitation, TestProcess
from apps.emails.models import EmailTemplate


class AdminCustomerWorkspaceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Workspace Customer")
        self.other_company = Company.objects.create(name="Other Customer")
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Recruitment", unit_code="WS-117"
        )
        self.other_unit = OrgUnit.objects.create(
            company=self.other_company, name="Other", unit_code="WS-OTHER"
        )
        self.admin = User.objects.create_superuser(
            username="workspace-admin", email="workspace-admin@example.test",
            password="not-used",
        )
        self.customer = User.objects.create_user(
            username="workspace-customer", email="workspace-customer@example.test",
            password="not-used",
        )
        CompanyMember.objects.create(
            company=self.company, user=self.customer, primary_org_unit=self.unit,
        )
        UserOrgUnitAccess.objects.create(
            user=self.customer, org_unit=self.unit, permission="editor",
        )
        self.other_user = User.objects.create_user(
            username="workspace-outsider", email="workspace-outsider@example.test",
            password="not-used",
        )
        CompanyMember.objects.create(
            company=self.other_company, user=self.other_user,
            primary_org_unit=self.other_unit,
        )
        UserOrgUnitAccess.objects.create(
            user=self.other_user, org_unit=self.other_unit, permission="editor",
        )
        self.process = TestProcess.objects.create(
            company=self.company, org_unit=self.unit, created_by=self.customer,
            name="Customer recruitment", purpose="hiring",
            account_code="MODERN", project_code="PQ-MQ",
            selected_tests=["personality", "motivation"], candidate_language="sv",
        )
        self.candidate = Candidate.objects.create(
            first_name="Synthetic", last_name="Candidate",
            email="synthetic-workspace@example.test",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process, candidate=self.candidate,
            status="created", source="invited",
        )
        self.detail_url = reverse(
            "processes:process_detail", args=[self.process.pk],
        )
        self.candidate_admin_url = reverse(
            "accounts:company_process_candidate_detail",
            args=[self.company.pk, self.process.pk, self.candidate.pk],
        )
        self.notes_url = reverse(
            "processes:process_candidate_interview_notes_update",
            args=[self.process.pk, self.candidate.pk],
        )

    def test_admin_project_links_open_shared_workspace_by_default(self):
        self.client.force_login(self.admin)
        admin_project_url = reverse(
            "accounts:company_process_detail",
            args=[self.company.pk, self.process.pk],
        )
        response = self.client.get(admin_project_url)
        self.assertRedirects(response, self.detail_url, fetch_redirect_response=False)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin_tools=1")
        self.assertContains(response, reverse(
            "accounts:company_processes", args=[self.company.pk],
        ))

    def test_integrity_guard_switch_is_only_shown_in_admin_project_workspace(self):
        self.client.force_login(self.admin)
        admin_page = self.client.get(self.detail_url)
        self.assertEqual(admin_page.status_code, 200)
        self.assertContains(admin_page, 'class="card admin-project-ig-card"')
        self.assertContains(admin_page, 'aria-label="Integrity Guard visibility in Talena"')
        self.assertContains(admin_page, reverse(
            "accounts:project_integrity_guard_visibility", args=[self.process.pk],
        ))
        self.assertContains(admin_page, "Integrity Guard")

        # The same real project is rendered to customers, without admin controls.
        self.client.force_login(self.customer)
        customer_page = self.client.get(self.detail_url)
        self.assertEqual(customer_page.status_code, 200)
        self.assertNotContains(customer_page, "admin-project-ig-card")
        self.assertNotContains(customer_page, reverse(
            "accounts:project_integrity_guard_visibility", args=[self.process.pk],
        ))
        self.assertNotContains(customer_page, "Company default")

    def test_admin_can_still_open_internal_project_tools(self):
        self.client.force_login(self.admin)
        admin_project_url = reverse(
            "accounts:company_process_detail",
            args=[self.company.pk, self.process.pk],
        )
        response = self.client.get(admin_project_url + "?admin_tools=1")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "admin/accounts/companies/company_process_detail.html"
        )
        self.assertContains(response, self.detail_url)
        self.assertContains(response, "talena-admin")

    def test_customer_cannot_open_internal_admin_tools(self):
        self.client.force_login(self.customer)
        admin_project_url = reverse(
            "accounts:company_process_detail",
            args=[self.company.pk, self.process.pk],
        )
        for path in (admin_project_url, admin_project_url + "?admin_tools=1"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertIn(response.status_code, (302, 403, 404))
                self.assertNotEqual(response.get("Location"), self.detail_url)

    def test_admin_without_company_membership_gets_real_customer_workspace(self):
        self.assertFalse(CompanyMember.objects.filter(user=self.admin).exists())
        self.client.force_login(self.admin)
        response = self.client.get(
            self.detail_url + "?focus_candidate=" + str(self.candidate.pk)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["process_base_layout"],
            "admin/core/layouts/admin_base.html",
        )
        self.assertTrue(response.context["can_edit"])
        markup = response.content.decode("utf-8")
        self.assertIn("talena-admin", markup)
        self.assertIn("focus_candidate", markup)
        self.assertIn('data-candidate-id="%s"' % self.candidate.pk, markup)

    def test_role_context_is_accessible_in_admin_work_mode(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("processes:process_role_context", args=[self.process.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["process_base_layout"],
            "admin/core/layouts/admin_base.html",
        )
        self.assertTrue(response.context["can_edit"])

    def test_saving_role_context_stays_on_role_tab_and_reselects_all_eight_traits(self):
        """Editing role context replaces prior manual picks with new project AI picks."""
        from unittest.mock import Mock
        from apps.processes.models import ProcessRoleContext
        from apps.processes.project_personality_trait_selection import (
            CACHE_KEY,
            get_project_personality_trait_options,
            get_project_personality_trait_selection,
        )

        available = [
            item["name"] for item in get_project_personality_trait_options("sv")
        ]
        original = available[:8]
        recommended = available[8:16]
        url = reverse(
            "processes:process_role_context", args=[self.process.pk],
        )
        self.client.force_login(self.customer)
        selection = self.client.post(url, {
            "context_text": "Recruiter for customer service.",
            "personality_question_traits": original,
            "save_personality_traits": "1",
        })
        self.assertRedirects(selection, url)
        context = ProcessRoleContext.objects.get(process=self.process)
        self.assertEqual(context.context_text, "Recruiter for customer service.")

        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertTemplateUsed(page, "customer/processes/process_role_context.html")
        self.assertEqual(page.context["active"], "context")
        self.assertEqual(set(page.context["selected_personality_traits"]), set(original))
        self.assertEqual(len(page.context["selected_project_trait_options"]), 8)

        # Previously generated candidate questions must remain available
        # while the new project selection makes them eligible for refresh.
        old_questions = {"questions": [{"question": "Earlier interview example"}]}
        self.invitation.ai_personality_questions = old_questions
        self.invitation.ai_personality_questions_status = "completed"
        self.invitation.save(
            update_fields=[
                "ai_personality_questions",
                "ai_personality_questions_status",
            ]
        )

        client = Mock()
        client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "items": [
                    {"name": name, "reason_sv": "Relevant för rollen",
                     "reason_en": "Relevant for the role"}
                    for name in recommended
                ],
            })))],
        )

        # Changing the role context must discard earlier manual picks and
        # regenerate a shared set, rather than carrying old traits forward.
        with (
            patch(
                "apps.processes.project_personality_trait_selection.get_openai_client",
                return_value=client,
            ),
            patch(
                "apps.processes.project_personality_trait_selection.get_chat_model",
                return_value="synthetic-model",
            ),
            patch(
                "apps.processes.project_personality_trait_selection.get_ai_feature_prompt_instructions",
                return_value="",
            ),
        ):
            saved = self.client.post(url, {
                "context_text": "Updated recruiter context and responsibilities.",
            })
        self.assertRedirects(saved, url)
        client.chat.completions.create.assert_called_once()
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.ai_personality_questions, old_questions)
        self.assertEqual(self.invitation.ai_personality_questions_status, "outdated")
        context.refresh_from_db()
        self.assertEqual(
            context.get_current_context_text(),
            "Updated recruiter context and responsibilities.",
        )
        self.assertEqual(context.purpose_data["hiring"]["personality_question_traits"], [])
        self.assertEqual(
            set(item["name"] for item in context.purpose_data["hiring"][CACHE_KEY]["items"]),
            set(recommended),
        )
        reopened = self.client.get(url)
        self.assertEqual(reopened.context["form"]["context_text"].value(),
                         "Updated recruiter context and responsibilities.")
        self.assertEqual(
            set(reopened.context["selected_personality_traits"]), set(recommended),
        )
        self.assertEqual(len(reopened.context["selected_project_trait_options"]), 8)
        self.assertEqual(
            reopened.context["personality_trait_selection_source"], "recommended",
        )
        self.assertEqual(
            set(item["name"] for item in get_project_personality_trait_selection(
                self.process, generate=False
            )), set(recommended),
        )

        # Re-saving the SAME text is not an update; preserve the selection
        # and avoid another paid AI call.
        with patch(
            "apps.processes.project_personality_trait_selection.get_openai_client",
            side_effect=AssertionError("Unexpected OpenAI call for unchanged context"),
        ):
            unchanged = self.client.post(url, {
                "context_text": "Updated recruiter context and responsibilities.",
            })
            self.assertRedirects(unchanged, url)
        context.refresh_from_db()
        self.assertEqual(
            set(item["name"] for item in context.purpose_data["hiring"][CACHE_KEY]["items"]),
            set(recommended),
        )

    def test_saving_role_context_ignores_old_next_redirect(self):
        """A candidate-page 'next' value must not navigate away after save."""
        from apps.processes.project_personality_trait_selection import (
            get_project_personality_trait_options,
        )

        url = reverse(
            "processes:process_role_context", args=[self.process.pk],
        )
        traits = [
            item["name"] for item in get_project_personality_trait_options("sv")[:8]
        ]
        self.client.force_login(self.customer)
        # Candidate pages sometimes open this form with a next URL back to
        # the candidate's project. Save should still stay in Role context.
        response = self.client.post(url, {
            "context_text": "Context from candidate workspace",
            "personality_question_traits": traits,
            "save_personality_traits": "1",
            "next": self.detail_url + "?focus_candidate=" + str(self.candidate.pk),
        })
        self.assertRedirects(response, url)

    def test_admin_save_role_context_stays_in_admin_work_mode(self):
        from apps.processes.project_personality_trait_selection import (
            get_project_personality_trait_options,
        )

        url = reverse(
            "processes:process_role_context", args=[self.process.pk],
        )
        traits = [
            item["name"] for item in get_project_personality_trait_options("sv")[:8]
        ]
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(url, {
            "context_text": "Admin role context update.",
            "personality_question_traits": traits,
            "save_personality_traits": "1",
        }), url)
        page = self.client.get(url)
        self.assertEqual(page.context["process_base_layout"],
                         "admin/core/layouts/admin_base.html")
        self.assertEqual(page.context["active"], "context")
        self.assertEqual(len(page.context["selected_project_trait_options"]), 8)

    def test_invalid_eight_trait_choice_does_not_redirect(self):
        from apps.processes.project_personality_trait_selection import (
            get_project_personality_trait_options,
        )

        url = reverse(
            "processes:process_role_context", args=[self.process.pk],
        )
        traits = [
            item["name"] for item in get_project_personality_trait_options("sv")[:7]
        ]
        self.client.force_login(self.customer)
        response = self.client.post(url, {
            "context_text": "Context with incomplete trait selection",
            "personality_question_traits": traits,
            "save_personality_traits": "1",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "customer/processes/process_role_context.html")
        self.assertIn("personality_question_traits", response.context["form"].errors)

    def test_admin_candidate_preview_links_to_edit_without_enabling_preview_writes(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            self.candidate_admin_url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        markup = response.content.decode("utf-8")
        self.assertTrue("Work with candidate" in markup or "Arbeta med kandidaten" in markup)
        self.assertTrue("Role context and traits" in markup or "Rollkontext och personlighetsdrag" in markup)
        self.assertIn(
            "?focus_candidate=%s" % self.candidate.pk, markup,
        )
        self.assertIn('data-read-only="true"', markup)

    def test_admin_work_mode_uses_write_enabled_candidate_endpoints(self):
        self.client.force_login(self.admin)
        candidate_url = reverse(
            "processes:process_candidate_detail",
            args=[self.process.pk, self.candidate.pk],
        )
        response = self.client.get(
            candidate_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_manage_candidate_results"])
        self.assertEqual(
            response.context["interview_notes_update_url"], self.notes_url,
        )
        self.assertTrue(response.context["personality_questions_stream_url"])
        self.assertTrue(response.context["post_interview_decision_support_stream_url"])
        self.invitation.refresh_from_db()
        self.assertFalse(self.invitation.interview_notes)

    def test_admin_interview_notes_update_real_candidate_owner(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.notes_url,
            data=json.dumps({"interview_notes": "Synthetic interview notes"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.interview_notes, "Synthetic interview notes")
        # The customer's view reads the same candidate record, not a staff copy.
        self.client.force_login(self.customer)
        customer_candidate_url = reverse(
            "processes:process_candidate_detail",
            args=[self.process.pk, self.candidate.pk],
        )
        customer_response = self.client.get(
            customer_candidate_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(customer_response.status_code, 200)
        self.assertEqual(
            customer_response.context["interview_notes"],
            "Synthetic interview notes",
        )

    def test_other_company_member_cannot_view_or_edit(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.detail_url)
        self.assertIn(response.status_code, (403, 404))
        response = self.client.post(
            self.notes_url,
            data=json.dumps({"interview_notes": "Must not save"}),
            content_type="application/json",
        )
        self.assertIn(response.status_code, (403, 404))
        self.invitation.refresh_from_db()
        self.assertFalse(self.invitation.interview_notes)

    def test_customer_keeps_original_shell_and_editor_permissions(self):
        self.client.force_login(self.customer)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["process_base_layout"], "")
        self.assertTrue(response.context["can_edit"])
        self.assertNotIn("Administrator workspace:", response.content.decode("utf-8"))

    def test_admin_can_edit_process_email_template_without_company_membership(self):
        email_url = reverse(
            "emails:edit_process_invitation_template", args=[self.process.pk],
        )
        self.client.force_login(self.admin)
        response = self.client.get(email_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["process_base_layout"],
            "admin/core/layouts/admin_base.html",
        )
        self.assertContains(response, "talena-admin")
        self.assertContains(response, reverse(
            "processes:process_update", args=[self.process.pk],
        ))

        response = self.client.post(email_url, {
            "action": "save",
            "subject": "Synthetic interview invitation",
            "body": "Hej {first_name}! {assessment_url}",
        })
        self.assertEqual(response.status_code, 302)
        template = EmailTemplate.objects.get(
            process=self.process, template_type="invitation", language="sv",
        )
        self.assertEqual(template.subject, "Synthetic interview invitation")
        self.assertEqual(template.body, "Hej {first_name}! {assessment_url}")
        self.assertTrue(template.is_active)

        self.client.force_login(self.customer)
        response = self.client.get(email_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["process_base_layout"], "")
        self.assertEqual(response.context["form"].initial["subject"], template.subject)

    def test_admin_can_edit_project_settings_in_shared_workspace(self):
        settings_url = reverse("processes:process_update", args=[self.process.pk])
        self.client.force_login(self.admin)
        with patch("apps.processes.views.SovaClient") as sova:
            sova.return_value.get_template_accounts_with_projects.return_value = []
            response = self.client.get(settings_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.context["process_base_layout"],
                "admin/core/layouts/admin_base.html",
            )
            self.assertContains(response, "talena-admin")
            self.assertContains(response, reverse(
                "emails:edit_process_invitation_template", args=[self.process.pk],
            ))

            with patch("apps.processes.views.resolve_sova_template") as resolve:
                resolve.return_value = {
                    "account_code": "MODERN",
                    "project_code": "PQ-MQ",
                }
                response = self.client.post(settings_url, {
                    "name": "Updated by Talena admin",
                    "purpose": "hiring",
                    "selected_tests": ["personality", "motivation"],
                    "candidate_language": "sv",
                    "labels_text": "Internal check",
                    "project_completion_notifications_enabled": "on",
                })
        self.assertEqual(response.status_code, 302)
        self.process.refresh_from_db()
        self.assertEqual(self.process.name, "Updated by Talena admin")
        self.assertEqual(self.process.company_id, self.company.pk)
        self.assertEqual(self.process.account_code, "MODERN")
        self.assertEqual(list(self.process.labels.values_list("name", flat=True)),
                         ["Internal check"])

        self.client.force_login(self.customer)
        with patch("apps.processes.views.SovaClient") as sova:
            sova.return_value.get_template_accounts_with_projects.return_value = []
            response = self.client.get(settings_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["process_base_layout"], "")
        self.assertEqual(response.context["process"].name, "Updated by Talena admin")

    def _save_project_integrity_guard_setting(self, selection=None):
        url = reverse("processes:process_update", args=[self.process.pk])
        data = {
            "name": self.process.name,
            "purpose": "hiring",
            "selected_tests": ["personality", "motivation"],
            "candidate_language": "sv",
            "project_completion_notifications_enabled": "on",
        }
        if selection is not None:
            data["integrity_guard_visibility"] = selection

        with patch("apps.processes.views.SovaClient") as sova, patch(
            "apps.processes.views.resolve_sova_template"
        ) as resolve:
            sova.return_value.get_template_accounts_with_projects.return_value = []
            resolve.return_value = {
                "account_code": "MODERN",
                "project_code": "PQ-MQ",
            }
            return self.client.post(url, data)

    def test_customer_can_update_project_integrity_guard_and_restore_company_default(self):
        self.client.force_login(self.customer)
        settings_url = reverse("processes:process_update", args=[self.process.pk])
        with patch("apps.processes.views.SovaClient") as sova:
            sova.return_value.get_template_accounts_with_projects.return_value = []
            response = self.client.get(settings_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="integrity_guard_visibility"', count=3)
        self.assertContains(response, "process-ig-setting")
        self.assertEqual(
            response.context["form"]["integrity_guard_visibility"].value(), "default"
        )

        self.company.integrity_guard_visible = False
        self.company.save(update_fields=["integrity_guard_visible"])
        self.assertFalse(self.process.integrity_guard_visible_in_talena)

        response = self._save_project_integrity_guard_setting("on")
        self.assertEqual(response.status_code, 302)
        self.process.refresh_from_db()
        self.assertIs(self.process.integrity_guard_visible_override, True)
        self.assertTrue(self.process.integrity_guard_visible_in_talena)

        with patch("apps.processes.views.SovaClient") as sova:
            sova.return_value.get_template_accounts_with_projects.return_value = []
            response = self.client.get(settings_url)
        self.assertEqual(response.context["form"]["integrity_guard_visibility"].value(), "on")

        response = self._save_project_integrity_guard_setting("off")
        self.assertEqual(response.status_code, 302)
        self.process.refresh_from_db()
        self.assertIs(self.process.integrity_guard_visible_override, False)
        self.assertFalse(self.process.integrity_guard_visible_in_talena)

        response = self._save_project_integrity_guard_setting("default")
        self.assertEqual(response.status_code, 302)
        self.process.refresh_from_db()
        self.assertIsNone(self.process.integrity_guard_visible_override)
        self.assertFalse(self.process.integrity_guard_visible_in_talena)

        self.company.integrity_guard_visible = True
        self.company.save(update_fields=["integrity_guard_visible"])
        self.process.refresh_from_db()
        self.assertTrue(self.process.integrity_guard_visible_in_talena)

    def test_omitted_project_integrity_guard_value_does_not_reset_existing_override(self):
        self.process.integrity_guard_visible_override = False
        self.process.save(update_fields=["integrity_guard_visible_override"])
        self.client.force_login(self.customer)
        response = self._save_project_integrity_guard_setting()
        self.assertEqual(response.status_code, 302)
        self.process.refresh_from_db()
        self.assertIs(self.process.integrity_guard_visible_override, False)

    def test_project_integrity_guard_edit_rejects_invalid_selection(self):
        self.client.force_login(self.customer)
        response = self._save_project_integrity_guard_setting("invalid")
        self.assertEqual(response.status_code, 200)
        self.assertIn("integrity_guard_visibility", response.context["form"].errors)
        self.process.refresh_from_db()
        self.assertIsNone(self.process.integrity_guard_visible_override)

    def test_other_company_cannot_change_project_integrity_guard(self):
        self.client.force_login(self.other_user)
        response = self._save_project_integrity_guard_setting("off")
        self.assertIn(response.status_code, (403, 404))
        self.process.refresh_from_db()
        self.assertIsNone(self.process.integrity_guard_visible_override)

    def test_other_customer_cannot_edit_templates_or_settings(self):
        self.client.force_login(self.other_user)
        template_url = reverse(
            "emails:edit_process_invitation_template", args=[self.process.pk],
        )
        settings_url = reverse("processes:process_update", args=[self.process.pk])
        for url in (template_url, settings_url):
            with self.subTest(url=url):
                self.assertIn(self.client.get(url).status_code, (403, 404))
                self.assertIn(self.client.post(url, {
                    "action": "save",
                    "subject": "Unauthorized",
                    "body": "{assessment_url}",
                    "name": "Unauthorized",
                    "purpose": "hiring",
                    "candidate_language": "sv",
                }).status_code, (403, 404))
        self.assertFalse(EmailTemplate.objects.filter(process=self.process).exists())
        self.process.refresh_from_db()
        self.assertEqual(self.process.name, "Customer recruitment")
