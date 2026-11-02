"""Regression tests for safe project/candidate removal (issue #307 quick fixes).

These tests deliberately do NOT test GDPR erasure: the global Candidate,
protected AssessmentUsage, Sova records and unrelated tenant links are retained.
"""
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import gettext, override

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.processes.models import AssessmentUsage, Candidate, TestInvitation, TestProcess


class ScopedRemovalTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Alpha")
        self.other_company = Company.objects.create(name="Bravo")
        self.unit = OrgUnit.objects.create(company=self.company, name="Team A", unit_code="A")
        self.other_unit = OrgUnit.objects.create(
            company=self.other_company, name="Team B", unit_code="B"
        )

        def member(username, company, unit, permission):
            user = User.objects.create_user(username=username, password="unused")
            CompanyMember.objects.create(
                company=company, user=user, primary_org_unit=unit
            )
            UserOrgUnitAccess.objects.create(
                user=user, org_unit=unit, permission=permission
            )
            return user

        self.owner = member("removal-owner", self.company, self.unit, "editor")
        self.editor = member("removal-editor", self.company, self.unit, "editor")
        self.viewer = member("removal-viewer", self.company, self.unit, "viewer")
        self.own_only = member("removal-own-only", self.company, self.unit, "own")
        self.outsider = member(
            "removal-other-company", self.other_company, self.other_unit, "editor"
        )
        self.project = TestProcess.objects.create(
            name="Hiring",
            company=self.company,
            org_unit=self.unit,
            created_by=self.owner,
            account_code="A",
            project_code="PQ",
        )
        self.second_project = TestProcess.objects.create(
            name="Team",
            company=self.company,
            org_unit=self.unit,
            created_by=self.owner,
            account_code="A",
            project_code="PQ",
        )
        self.candidate = Candidate.objects.create(
            first_name="Alex", last_name="Example", email="removal-alex@example.org"
        )
        self.invitation = TestInvitation.objects.create(
            process=self.project, candidate=self.candidate, status="created"
        )
        self.other_invitation = TestInvitation.objects.create(
            process=self.second_project, candidate=self.candidate, status="created"
        )
        self.remove_url = reverse(
            "processes:remove_candidate_from_process",
            args=[self.project.pk, self.candidate.pk],
        )
        self.delete_url = reverse("processes:process_delete", args=[self.project.pk])

    def test_editor_can_remove_unsent_candidate_from_colleagues_project(self):
        self.client.force_login(self.editor)
        response = self.client.post(self.remove_url, HTTP_ACCEPT_LANGUAGE="sv")
        self.assertRedirects(
            response,
            reverse("processes:process_detail", args=[self.project.pk]),
            fetch_redirect_response=False,
        )
        self.assertTrue(TestInvitation.objects.filter(pk=self.invitation.pk).exists())
        self.assertIsNotNone(TestInvitation.objects.get(pk=self.invitation.pk).removed_from_process_at)
        self.assertTrue(Candidate.objects.filter(pk=self.candidate.pk).exists())
        self.assertTrue(TestInvitation.objects.filter(pk=self.other_invitation.pk).exists())
        self.assertIn(
            "Den oskickade inbjudan har tagits bort från den aktiva projektlistan",
            " ".join(str(m) for m in get_messages(response.wsgi_request)),
        )

    def test_viewer_own_only_and_other_tenant_are_denied(self):
        for user in (self.viewer, self.own_only, self.outsider):
            self.client.force_login(user)
            self.assertEqual(self.client.post(self.remove_url).status_code, 403)
            self.assertEqual(self.client.post(self.delete_url).status_code, 403)
        self.assertTrue(TestInvitation.objects.filter(pk=self.invitation.pk).exists())
        self.assertTrue(TestProcess.objects.filter(pk=self.project.pk).exists())

    def test_remove_candidate_requires_post(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(self.remove_url).status_code, 405)
        self.assertTrue(TestInvitation.objects.filter(pk=self.invitation.pk).exists())

    def test_ordered_assessment_is_not_removed(self):
        self.invitation.status = "failed"
        self.invitation.assessment_url = "https://example.org/assessment"
        self.invitation.save(update_fields=["status", "assessment_url"])
        self.client.force_login(self.editor)
        response = self.client.post(self.remove_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TestInvitation.objects.filter(pk=self.invitation.pk).exists())

    def test_sova_reference_is_not_removed_even_without_assessment_url(self):
        self.invitation.status = "failed"
        self.invitation.sova_request_id = "sova-order-123"
        self.invitation.save(update_fields=["status", "sova_request_id"])
        self.client.force_login(self.editor)
        self.assertEqual(self.client.post(self.remove_url).status_code, 302)
        self.assertTrue(TestInvitation.objects.filter(pk=self.invitation.pk).exists())

    def test_billing_usage_blocks_candidate_removal(self):
        usage = AssessmentUsage.objects.create(
            company=self.company,
            org_unit=self.unit,
            process=self.project,
            candidate=self.candidate,
            invitation=self.invitation,
            assessment_type="personality",
        )
        self.client.force_login(self.editor)
        response = self.client.post(self.remove_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TestInvitation.objects.filter(pk=self.invitation.pk).exists())
        self.assertTrue(AssessmentUsage.objects.filter(pk=usage.pk).exists())

    def test_removed_unsent_candidate_remains_blocked_from_readding(self):
        self.client.force_login(self.editor)
        self.client.post(self.remove_url)
        inv = TestInvitation.objects.get(pk=self.invitation.pk)
        self.assertIsNotNone(inv.removed_from_process_at)
        self.assertEqual(inv.sova_revocation_state, "not_required")
        self.client.post(
            reverse("processes:process_add_candidate", args=[self.project.pk]),
            {"first_name": self.candidate.first_name,
             "last_name": self.candidate.last_name, "email": self.candidate.email},
        )
        inv.refresh_from_db()
        self.assertIsNotNone(inv.removed_from_process_at)

    def test_ordered_removal_hides_from_project_but_retains_billing_and_sova_reference(self):
        usage = AssessmentUsage.objects.create(
            company=self.company, org_unit=self.unit, process=self.project,
            candidate=self.candidate, invitation=self.invitation,
            assessment_type="personality",
        )
        self.invitation.status = "sent"
        self.invitation.assessment_url = "https://example.org/assessment"
        self.invitation.save(update_fields=["status", "assessment_url"])
        self.client.force_login(self.editor)
        response = self.client.post(self.remove_url, HTTP_ACCEPT_LANGUAGE="sv")
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertIsNotNone(self.invitation.removed_from_process_at)
        self.assertEqual(self.invitation.sova_revocation_state, "manual_pending")
        self.assertEqual(self.invitation.assessment_url, "https://example.org/assessment")
        self.assertTrue(AssessmentUsage.objects.filter(pk=usage.pk).exists())
        self.assertTrue(TestInvitation.objects.filter(pk=self.other_invitation.pk).exists())
        self.assertIn(
            "Sova-testlänken kan fortfarande fungera",
            " ".join(str(m) for m in get_messages(response.wsgi_request)),
        )
        active = self.client.get(reverse("processes:process_detail", args=[self.project.pk]), HTTP_ACCEPT_LANGUAGE="sv")
        self.assertNotContains(active, 'data-candidate-id="' + str(self.candidate.pk) + '"')
        self.assertContains(active, "Sova-åtkomst ej bekräftat spärrad")
        detail = reverse("processes:process_candidate_detail", args=[self.project.pk, self.candidate.pk])
        self.assertEqual(self.client.get(detail).status_code, 404)
        polling = self.client.get(reverse("processes:process_invitation_statuses", args=[self.project.pk]))
        self.assertEqual(polling.json()["invitations"], [])

    def test_removal_revokes_candidate_result_link_without_deleting_snapshot(self):
        from apps.candidate_results.models import CandidateResultAccess, CandidateResultSnapshot
        from apps.candidate_results.services import create_candidate_result_access
        self.invitation.status = "completed"
        self.invitation.save(update_fields=["status"])
        snapshot = CandidateResultSnapshot.objects.create(
            invitation=self.invitation, candidate=self.candidate,
            process=self.project, content={"sections": []},
        )
        access, _token, _code = create_candidate_result_access(snapshot)
        self.client.force_login(self.editor)
        self.client.post(self.remove_url)
        access.refresh_from_db()
        self.assertIsNotNone(access.revoked_at)
        self.assertTrue(CandidateResultSnapshot.objects.filter(pk=snapshot.pk).exists())

    def test_removed_sova_invitation_cannot_be_readded_as_active_candidate(self):
        self.invitation.status = "sent"
        self.invitation.save(update_fields=["status"])
        self.client.force_login(self.editor)
        self.client.post(self.remove_url)
        self.assertEqual(
            TestInvitation.objects.get(pk=self.invitation.pk).sova_revocation_state,
            "manual_pending",
        )
        self.client.post(
            reverse("processes:process_add_candidate", args=[self.project.pk]),
            {"first_name": self.candidate.first_name,
             "last_name": self.candidate.last_name, "email": self.candidate.email},
        )
        self.assertIsNotNone(TestInvitation.objects.get(pk=self.invitation.pk).removed_from_process_at)
        self.assertEqual(
            TestInvitation.objects.filter(
                process=self.project, removed_from_process_at__isnull=True,
            ).count(), 0
        )

    def test_active_project_delete_url_archives_not_purges(self):
        self.client.force_login(self.editor)
        response = self.client.post(self.delete_url)
        self.assertRedirects(
            response, reverse("processes:process_list"),
            fetch_redirect_response=False,
        )
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_archived)
        self.assertTrue(TestInvitation.objects.filter(pk=self.invitation.pk).exists())

    def test_archived_project_without_orders_can_be_deleted(self):
        self.project.archive()
        self.client.force_login(self.editor)
        response = self.client.post(self.delete_url)
        self.assertRedirects(
            response, reverse("processes:process_list") + "?archived=1",
            fetch_redirect_response=False,
        )
        self.assertFalse(TestProcess.objects.filter(pk=self.project.pk).exists())
        self.assertTrue(TestProcess.objects.filter(pk=self.second_project.pk).exists())
        self.assertTrue(Candidate.objects.filter(pk=self.candidate.pk).exists())
        self.assertTrue(TestInvitation.objects.filter(pk=self.other_invitation.pk).exists())

    def test_archived_ordered_project_remains_archived_without_http_error(self):
        self.project.archive()
        self.invitation.status = "failed"
        self.invitation.assessment_url = "https://example.org/assessment"
        self.invitation.save(update_fields=["status", "assessment_url"])
        self.client.force_login(self.editor)
        response = self.client.post(self.delete_url)
        self.assertRedirects(
            response, reverse("processes:process_list") + "?archived=1",
            fetch_redirect_response=False,
        )
        self.assertTrue(TestProcess.objects.filter(pk=self.project.pk).exists())
        self.assertIn(
            "cannot be permanently deleted",
            " ".join(str(m) for m in get_messages(response.wsgi_request)),
        )

    def test_expired_order_without_url_still_blocks_permanent_deletion(self):
        self.project.archive()
        self.invitation.status = "expired"
        self.invitation.save(update_fields=["status"])
        self.client.force_login(self.editor)
        self.assertEqual(self.client.post(self.delete_url).status_code, 302)
        self.assertTrue(TestProcess.objects.filter(pk=self.project.pk).exists())

    def test_billing_usage_blocks_project_removal(self):
        self.project.archive()
        usage = AssessmentUsage.objects.create(
            company=self.company,
            org_unit=self.unit,
            process=self.project,
            candidate=self.candidate,
            invitation=self.invitation,
            assessment_type="personality",
        )
        self.client.force_login(self.editor)
        self.assertEqual(self.client.post(self.delete_url).status_code, 302)
        self.assertTrue(AssessmentUsage.objects.filter(pk=usage.pk).exists())
        self.assertTrue(TestProcess.objects.filter(pk=self.project.pk).exists())

    def test_historical_project_cannot_be_purged(self):
        self.project.archive()
        self.project.is_historical = True
        self.project.save(update_fields=["is_historical"])
        self.client.force_login(self.editor)
        self.assertEqual(self.client.post(self.delete_url).status_code, 302)
        self.assertTrue(TestProcess.objects.filter(pk=self.project.pk).exists())

    def test_project_list_has_one_delete_confirmation_modal(self):
        self.project.archive()
        self.client.force_login(self.editor)
        response = self.client.get(
            reverse("processes:process_list") + "?archived=1"
        )
        self.assertContains(response, 'id="removeProjectModal"', count=1)
        self.assertContains(response, 'data-remove-project')
        self.assertContains(response, 'data-can-delete="true"')

    def test_candidate_detail_has_modal_not_direct_delete_submit(self):
        self.client.force_login(self.editor)
        response = self.client.get(
            reverse("processes:process_detail", args=[self.project.pk])
        )
        self.assertContains(response, 'id="removeCandidateModal"', count=1)
        self.assertContains(response, 'data-remove-candidate')
        self.assertContains(response, 'data-ordered="false"')

    def test_candidate_removal_modal_uses_active_swedish_language(self):
        self.client.force_login(self.editor)
        response = self.client.get(
            reverse("processes:process_detail", args=[self.project.pk]),
            HTTP_ACCEPT_LANGUAGE="sv",
        )
        self.assertEqual(response.status_code, 200)
        markup = response.content.decode("utf-8")
        modal = markup.split('id="removeCandidateModal"', 1)[1]
        self.assertIn("Ta bort från projekt", modal)
        self.assertNotIn("Sova-testlänken spärras INTE automatiskt", modal)
        self.assertIn("Avbryt", modal)
        self.assertIn('class="btn btn-dark" id="removeCandidateSubmit"', modal)
        self.assertNotIn("This candidate has ordered assessments", modal)
        self.assertNotIn("Remove from project", modal)

    def test_candidate_removal_modal_uses_active_english_language(self):
        self.client.force_login(self.editor)
        response = self.client.get(
            reverse("processes:process_detail", args=[self.project.pk]),
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 200)
        modal = response.content.decode("utf-8").split('id="removeCandidateModal"', 1)[1]
        self.assertIn("Remove from project", modal)
        self.assertNotIn("Sova assessment link is NOT automatically revoked", modal)
        self.assertIn("Cancel", modal)
        self.assertNotIn("Sova-testlänken spärras INTE automatiskt", modal)

    def test_project_list_archive_and_restore_have_localized_modal(self):
        self.client.force_login(self.editor)
        for lang, archive, restore in (
            ("sv", "Arkivera projekt", "Återställ projekt"),
            ("en", "Archive project", "Restore project"),
        ):
            for archived in (False, True):
                if archived:
                    self.project.archive()
                else:
                    self.project.unarchive()
                url = reverse("processes:process_list")
                if archived:
                    url += "?archived=1"
                response = self.client.get(url, HTTP_ACCEPT_LANGUAGE=lang)
                self.assertEqual(response.status_code, 200)
                markup = response.content.decode("utf-8")
                self.assertEqual(markup.count('id="projectStatusModal"'), 1)
                self.assertIn('data-project-status-form', markup)
                self.assertIn('data-project-status-action="restore"' if archived
                              else 'data-project-status-action="archive"', markup)
                self.assertIn(archive, markup)
                self.assertIn(restore, markup)
                self.assertNotIn('data-confirm="Archive this project?', markup)
                self.assertIn('id="projectStatusForm"', markup)

    def test_missing_project_list_swedish_translations_are_available(self):
        with override("sv"):
            self.assertEqual(gettext("Assessment workflows"), "Testflöden")
            self.assertEqual(
                gettext("Search by title, purpose or assessment..."),
                "Sök på namn, syfte eller test...",
            )
            self.assertEqual(gettext("Filter by purpose"), "Filtrera på syfte")
            self.assertEqual(gettext("All purposes"), "Alla syften")

    def test_archive_and_restore_messages_match_selected_language(self):
        self.client.force_login(self.editor)
        archive_url = reverse("processes:process_archive", args=[self.project.pk])
        restore_url = reverse("processes:process_unarchive", args=[self.project.pk])

        response = self.client.post(archive_url, HTTP_ACCEPT_LANGUAGE="sv")
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "Projektet arkiverades.",
            " ".join(str(m) for m in get_messages(response.wsgi_request)),
        )
        response = self.client.post(restore_url, HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "The project was restored.",
            " ".join(str(m) for m in get_messages(response.wsgi_request)),
        )
