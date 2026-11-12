"""Regression tests for the TestProcess Django Admin change form.

The process form must reference only real TestProcess model fields. In
particular sova_project_id belongs to TestInvitation, not TestProcess.
"""
from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.processes.models import TestProcess


class TestProcessAdminChangeFormTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="testprocess-admin-fix",
            email="testprocess-admin@example.test",
            password="synthetic-test-password",
        )
        self.client.force_login(self.admin_user)
        self.process = TestProcess.objects.create(
            name="Synthetic Integrity Guard process",
            created_by=self.admin_user,
            account_code="SOVA",
            project_code="SYNTHETIC-PQ",
        )

    def test_change_form_renders_without_field_error(self):
        response = self.client.get(
            reverse("admin:processes_testprocess_change", args=[self.process.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Synthetic Integrity Guard process")
        self.assertContains(response, "SOVA information")

    def test_add_form_renders_without_field_error(self):
        response = self.client.get(reverse("admin:processes_testprocess_add"))
        self.assertEqual(response.status_code, 200)

    def test_every_admin_fieldset_field_exists_on_process(self):
        model_admin = admin.site._registry[TestProcess]
        valid_fields = {
            field.name for field in TestProcess._meta.get_fields()
        } | set(model_admin.readonly_fields)
        listed_fields = [
            field
            for _, data in model_admin.fieldsets
            for row in data["fields"]
            for field in (row if isinstance(row, (list, tuple)) else (row,))
        ]
        self.assertEqual(set(listed_fields) - valid_fields, set())
        self.assertNotIn("sova_project_id", listed_fields)
        self.assertIn("sova_project_name", listed_fields)
