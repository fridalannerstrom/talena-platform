from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.processes.models import PinnedProject, TestProcess


class PinnedProjectTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme")
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Sweden", unit_code="SE"
        )
        self.creator = User.objects.create_user(
            username="creator", password="test-password"
        )
        self.viewer = User.objects.create_user(
            username="viewer", password="test-password"
        )
        self.own_only = User.objects.create_user(
            username="own-only", password="test-password"
        )
        for user, permission in (
            (self.creator, "editor"),
            (self.viewer, "viewer"),
            (self.own_only, "own"),
        ):
            CompanyMember.objects.create(
                company=self.company, user=user, primary_org_unit=self.unit
            )
            UserOrgUnitAccess.objects.create(
                user=user, org_unit=self.unit, permission=permission
            )
        self.process = self._project("Shared project", self.creator)

    def _project(self, name, creator):
        return TestProcess.objects.create(
            name=name,
            company=self.company,
            org_unit=self.unit,
            created_by=creator,
            account_code="A",
            project_code=name,
        )

    def _toggle(self, process):
        return self.client.post(
            reverse("processes:toggle_pinned_project", args=[process.pk]),
            {"next": reverse("processes:process_list")},
        )

    def test_viewer_can_pin_from_list_and_unpin_from_sidebar(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self._toggle(self.process).status_code, 302)
        self.assertEqual(
            list(PinnedProject.objects.values_list("process_id", flat=True)),
            [self.process.pk],
        )

        page = self.client.get(reverse("processes:process_list"))
        self.assertContains(page, "Pinned projects")
        with override("sv"):
            self.assertContains(
                self.client.get(reverse("processes:process_list")),
                "Fästa projekt",
            )
        self.assertContains(page, "talena-pinned-link")
        self.assertContains(page, 'aria-pressed="true"')
        self.assertContains(
            page, reverse("processes:process_detail", args=[self.process.pk])
        )

        self.assertEqual(self._toggle(self.process).status_code, 302)
        self.assertFalse(PinnedProject.objects.filter(user=self.viewer).exists())
        page = self.client.get(reverse("processes:process_list"))
        self.assertNotContains(page, "talena-pinned-link")

    def test_pins_are_private_and_stale_permissions_do_not_leak(self):
        PinnedProject.objects.create(user=self.own_only, process=self.process)
        self.client.force_login(self.own_only)
        page = self.client.get(reverse("processes:process_list"))
        self.assertNotContains(page, "talena-pinned-link")
        self.assertEqual(self._toggle(self.process).status_code, 404)

        own_process = self._project("Own project", self.own_only)
        self.assertEqual(self._toggle(own_process).status_code, 302)
        self.assertContains(
            self.client.get(reverse("processes:process_list")),
            "talena-pinned-link",
        )

        self.client.force_login(self.viewer)
        self.assertNotContains(
            self.client.get(reverse("processes:process_list")),
            "talena-pinned-link",
        )

    def test_limit_archive_and_method_guard(self):
        self.client.force_login(self.viewer)
        projects = [self.process] + [
            self._project(f"Project {i}", self.creator) for i in range(1, 6)
        ]
        for project in projects[:5]:
            self.assertEqual(self._toggle(project).status_code, 302)
        self.assertEqual(self._toggle(projects[5]).status_code, 302)
        self.assertEqual(PinnedProject.objects.filter(user=self.viewer).count(), 5)
        self.assertEqual(
            len(self.client.get(reverse("processes:process_list")).context["pinned_projects"]),
            5,
        )

        projects[0].archive()
        self.assertFalse(PinnedProject.objects.filter(process=projects[0]).exists())
        self._toggle(projects[5])
        self.assertEqual(PinnedProject.objects.filter(user=self.viewer).count(), 5)
        self.assertEqual(
            self.client.get(
                reverse("processes:toggle_pinned_project", args=[projects[5].pk])
            ).status_code,
            405,
        )

    def test_external_next_url_is_rejected(self):
        self.client.force_login(self.viewer)
        response = self.client.post(
            reverse("processes:toggle_pinned_project", args=[self.process.pk]),
            {"next": "https://example.com/other"},
        )
        self.assertRedirects(
            response, reverse("processes:process_list"), fetch_redirect_response=False
        )
