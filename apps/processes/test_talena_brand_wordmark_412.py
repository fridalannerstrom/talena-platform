"""Ticket #412: Talena's shared system logo is consistently used and legible."""
from pathlib import Path
from xml.etree import ElementTree as ET

from django.conf import settings
from django.test import SimpleTestCase


class TalenaSystemWordmarkTests(SimpleTestCase):
    def test_logo_is_valid_vector_with_original_corallogo_and_serif_wordmark(self):
        logo = (Path(settings.BASE_DIR) / "static/images/talena-logo.svg").read_text(
            encoding="utf-8"
        )
        root = ET.fromstring(logo)
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertEqual(root.attrib["viewBox"], "0 0 526 174")
        ns = {"svg": "http://www.w3.org/2000/svg"}
        paths = root.findall(".//svg:path", ns)
        self.assertTrue(any(p.attrib.get("fill") == "#be5f56" for p in paths))
        # The wordmark is based on Google Fonts Sora Bold outlines rather
        # than SVG <text>. Images loaded via <img> do not inherit page fonts.
        self.assertEqual(root.findall(".//svg:text", ns), [])
        glyphs = [p for p in paths if p.attrib.get("data-sora-glyph")]
        self.assertEqual("".join(p.attrib["data-sora-glyph"] for p in glyphs), "Talena")
        self.assertEqual(len(glyphs), 6)
        self.assertTrue(all(p.attrib["fill"] == "#171312" for p in glyphs))
        self.assertTrue(all(p.attrib["d"].startswith("M") for p in glyphs))
        self.assertTrue(all("scale(0.109 -0.109)" in p.attrib["transform"] for p in glyphs))
        self.assertIn("Sora Bold (Google Fonts)", logo)
        self.assertNotIn("Georgia", logo)
        self.assertNotIn("font-family", logo)
        # Individual x positions guarantee the last glyph stays within the
        # 526px viewBox, even without browser font availability.
        self.assertIn("translate(451 124)", glyphs[-1].attrib["transform"])

    def test_customer_admin_login_and_candidate_views_share_one_brand_asset(self):
        base = Path(settings.BASE_DIR) / "templates"
        paths = (
            "customer/core/partials/customer_sidebar.html",
            "admin/core/partials/admin_sidebar.html",
            "accounts/login.html",
            "accounts/accept_invite.html",
            "candidate_results/verify.html",
            "candidate_results/result.html",
        )
        for path in paths:
            with self.subTest(template=path):
                template = (base / path).read_text(encoding="utf-8")
                self.assertIn("images/talena-logo.svg", template)
                self.assertNotIn("talena-wordmark-other.svg", template)

    def test_customer_and_admin_keep_responsive_logo_and_company_branding_separate(self):
        base = Path(settings.BASE_DIR)
        layout = (base / "static/css/talena/layout.css").read_text(encoding="utf-8")
        admin = (base / "static/css/talena/admin-shell.css").read_text(encoding="utf-8")
        self.assertIn(".talena-sidebar .talena-sidebar-logo", layout)
        self.assertIn("object-fit: contain", layout)
        self.assertIn(".talena-admin .talena-admin-brand .talena-sidebar-logo", admin)
        self.assertIn("width: 108px", admin)
        # Never substitute Talena's own mark for customer-uploaded branding.
        team = (base / "templates/customer/teams/team_detail.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("report_branding.logo_url", team)
