"""Ticket #182: company branding is isolated, validated and safe to reuse."""
import io
import os
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from apps.accounts.models import Company, CompanyBranding, CompanyMember
from apps.accounts.report_branding import (
    DEFAULT_PRIMARY, brand_palette, get_report_branding, normalize_brand_image,
)


def uploaded_image(name="logo.png", color="#143352", *, metadata=False):
    buffer = io.BytesIO()
    image = Image.new("RGB", (320, 200), color=color)
    extra = {}
    if metadata:
        info = PngInfo()
        info.add_text("Author", "Sensitive synthetic metadata")
        extra["pnginfo"] = info
    image.save(buffer, format="PNG", **extra)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class ReportBrandingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_dir = tempfile.TemporaryDirectory()
        cls.media_override = override_settings(
            MEDIA_ROOT=cls.media_dir.name, USE_AZURE_STORAGE=False,
        )
        cls.media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_override.disable()
        cls.media_dir.cleanup()

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="branding-admin", email="branding-admin@example.test",
            password="testing-password",
        )
        self.member = User.objects.create_user(
            username="branding-member", email="branding-member@example.test",
            password="testing-password",
        )
        self.other = User.objects.create_user(
            username="other-company-member", email="other-member@example.test",
            password="testing-password",
        )
        self.company = Company.objects.create(name="Company A")
        self.other_company = Company.objects.create(name="Company B")
        CompanyMember.objects.create(user=self.member, company=self.company)
        CompanyMember.objects.create(user=self.other, company=self.other_company)
        self.editor_url = reverse("accounts:company_branding_settings", args=[self.company.pk])

    def asset(self, company, kind):
        return reverse("accounts:company_branding_asset", args=[company.pk, kind])

    def post_form(self, **changes):
        data = {
            "primary_color": "#123456",
            "cover_focus_y": "35",
        }
        data.update(changes.pop("data", {}))
        return self.client.post(self.editor_url, data=data, **changes)

    def test_empty_company_uses_talena_fallback_and_get_does_not_save(self):
        profile = get_report_branding(self.company)
        self.assertFalse(profile["is_custom"])
        self.assertEqual(profile["palette"]["primary"], DEFAULT_PRIMARY)
        self.assertIsNone(profile["logo_url"])
        self.assertIsNone(profile["cover_url"])
        self.client.force_login(self.admin)
        response = self.client.get(self.editor_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Company A")
        self.assertContains(response, "Synthetic")
        self.assertFalse(CompanyBranding.objects.exists())

    def test_admin_can_save_branding_and_preview_without_candidate_data(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.editor_url, {
            "primary_color": "#164A6D", "cover_focus_y": "22",
            "logo": uploaded_image(),
            "cover_image": uploaded_image("cover.png"),
        })
        self.assertEqual(response.status_code, 302)
        brand = CompanyBranding.objects.get(company=self.company)
        self.assertEqual(brand.primary_color, "#164A6D")
        self.assertEqual(brand.cover_focus_y, 22)
        self.assertTrue(brand.logo)
        self.assertTrue(brand.cover_image)
        profile = get_report_branding(self.company)
        self.assertTrue(profile["is_custom"])
        self.assertEqual(profile["cover_focus_y"], 22)
        self.assertEqual(profile["logo_url"], self.asset(self.company, "logo"))
        self.assertNotIn("/media/", profile["logo_url"])
        self.assertNotIn("blob.core.windows.net", profile["logo_url"])
        self.assertContains(self.client.get(self.editor_url), "Team report")

    def test_uploads_are_normalized_and_source_metadata_removed(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.editor_url, {
            "primary_color": "#335577",
            "cover_focus_y": "50",
            "logo": uploaded_image("client-logo.png", metadata=True),
            "cover_image": uploaded_image("presentation.jpg", metadata=True),
        })
        self.assertEqual(response.status_code, 302)
        brand = CompanyBranding.objects.get(company=self.company)
        self.assertTrue(brand.logo.name.startswith(f"company-branding/{self.company.pk}/"))
        self.assertTrue(brand.logo.name.endswith(".png"))
        self.assertTrue(brand.cover_image.name.endswith(".jpg"))
        self.assertNotIn("client-logo", brand.logo.name)
        with brand.logo.open("rb") as src:
            img = Image.open(src)
            self.assertEqual(img.format, "PNG")
            self.assertNotIn("Author", img.info)
        with brand.cover_image.open("rb") as src:
            self.assertEqual(Image.open(src).format, "JPEG")

    def test_invalid_color_or_image_rejected_without_overwriting_existing(self):
        self.client.force_login(self.admin)
        self.client.post(self.editor_url, {
            "primary_color": "#112233", "cover_focus_y": "50",
            "logo": uploaded_image(),
        })
        brand = CompanyBranding.objects.get(company=self.company)
        old_name = brand.logo.name
        response = self.client.post(self.editor_url, {
            "primary_color": "red; background:url()", "cover_focus_y": "50",
            "logo": SimpleUploadedFile("bad.svg", b"<svg></svg>", content_type="image/svg+xml"),
        })
        self.assertEqual(response.status_code, 200)
        brand.refresh_from_db()
        self.assertEqual(brand.logo.name, old_name)
        self.assertEqual(brand.primary_color, "#112233")
        self.assertTrue(brand.logo.storage.exists(old_name))
        self.assertFalse(CompanyBranding.objects.filter(primary_color__contains="url").exists())

    def test_file_size_and_focal_point_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.editor_url, {
            "primary_color": "#112233", "cover_focus_y": "200",
            "logo": SimpleUploadedFile("oversized.png", b"x" * (5 * 1024 * 1024 + 1), content_type="image/png"),
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CompanyBranding.objects.exists())

    def test_admin_only_and_company_isolation_for_uploaded_images(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(self.editor_url).status_code, 403)
        self.assertEqual(self.post_form().status_code, 403)
        self.assertFalse(CompanyBranding.objects.exists())

        self.client.force_login(self.admin)
        self.client.post(self.editor_url, {
            "primary_color": "#225588", "cover_focus_y": "50",
            "logo": uploaded_image(),
        })
        a_logo = self.asset(self.company, "logo")
        self.assertEqual(self.client.get(a_logo).status_code, 200)

        self.client.force_login(self.member)
        self.assertEqual(self.client.get(a_logo).status_code, 200)
        self.assertEqual(self.client.get(a_logo)["Content-Type"], "image/png")
        self.assertEqual(self.client.get(a_logo)["Cache-Control"], "private, no-store")

        self.client.force_login(self.other)
        self.assertEqual(self.client.get(a_logo).status_code, 404)
        self.assertEqual(self.client.get(self.editor_url).status_code, 403)
        self.assertEqual(self.client.get(self.asset(self.other_company, "logo")).status_code, 404)

    def test_replacing_removing_and_resetting_branding(self):
        self.client.force_login(self.admin)
        self.client.post(self.editor_url, {
            "primary_color": "#335577", "cover_focus_y": "50",
            "logo": uploaded_image(),
            "cover_image": uploaded_image("cover.png"),
        })
        brand = CompanyBranding.objects.get(company=self.company)
        old_logo = brand.logo.name
        cover_name = brand.cover_image.name

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.editor_url, {
                "primary_color": "#8899AA", "cover_focus_y": "51",
                "logo": uploaded_image("replacement.png", color="#445577"),
                "remove_cover_image": "on",
            })
        self.assertEqual(response.status_code, 302)
        brand.refresh_from_db()
        self.assertTrue(brand.logo)
        self.assertNotEqual(brand.logo.name, old_logo)
        self.assertFalse(brand.cover_image)
        self.assertFalse(brand.logo.storage.exists(old_logo))
        self.assertFalse(brand.cover_image.storage.exists(cover_name))

        new_logo = brand.logo.name
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.editor_url, {"action": "reset"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CompanyBranding.objects.filter(company=self.company).exists())
        self.assertFalse(brand.logo.storage.exists(new_logo))
        self.assertEqual(get_report_branding(self.company)["palette"]["primary"], DEFAULT_PRIMARY)
        self.assertEqual(self.client.get(self.asset(self.company, "logo")).status_code, 404)

    def test_derived_palette_is_readable_for_extreme_colors(self):
        for primary in ("#000000", "#FFFFFF", "#FDF101", "#14253F", "#FF6F61"):
            palette = brand_palette(primary)
            self.assertEqual(palette["primary"], primary)
            self.assertEqual(len(palette["chart_colors"]), 4)
            self.assertIn(palette["on_primary"], ("#141414", "#FFFFFF"))

    def test_standalone_image_normalizer_strips_metadata(self):
        normalized = normalize_brand_image(uploaded_image(metadata=True), "logo")
        self.assertEqual(normalized.name, "logo.png")
        img = Image.open(normalized)
        self.assertNotIn("Author", img.info)
