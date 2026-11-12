from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.integrations.sova import SovaClient


class SovaTemplateAccountTests(SimpleTestCase):
    @patch.dict(
        "os.environ",
        {"SOVA_USERNAME": "fake-user", "SOVA_PASSWORD": "fake-password"},
    )
    def setUp(self):
        self.sova = SovaClient()

    def test_only_modern_account_projects_are_used(self):
        accounts = [
            {"name": "Talena Main Account", "code": "MAIN"},
            {"name": "  talena MODERN projects ", "code": "MODERN"},
        ]
        projects = [
            {"id": 1, "code": "PQ", "name": "Personality"},
            {"id": 2, "code": "PIC", "name": " Test pictures "},
            {"id": 3, "code": "MQ", "name": "Motivation"},
        ]
        with patch.object(self.sova, "get_accounts", return_value=accounts), patch.object(
            self.sova, "get_projects_for_account", return_value=projects
        ) as get_projects:
            selected = self.sova.get_template_accounts_with_projects()

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["code"], "MODERN")
        self.assertEqual([p["code"] for p in selected[0]["projects"]], ["PQ", "MQ"])
        get_projects.assert_called_once_with("MODERN")

    def test_missing_modern_account_never_falls_back_to_main(self):
        with patch.object(
            self.sova,
            "get_accounts",
            return_value=[{"name": "Talena Main Account", "code": "MAIN"}],
        ), patch.object(self.sova, "get_projects_for_account") as get_projects:
            with self.assertRaisesRegex(ValueError, "No template fallback"):
                self.sova.get_template_accounts_with_projects()
        get_projects.assert_not_called()

    def test_duplicate_modern_account_is_rejected(self):
        with patch.object(
            self.sova,
            "get_accounts",
            return_value=[
                {"name": "Talena Modern Projects", "code": "FIRST"},
                {"name": "Talena Modern Projects", "code": "SECOND"},
            ],
        ):
            with self.assertRaisesRegex(ValueError, "found 2"):
                self.sova.get_template_accounts_with_projects()

    def test_missing_account_code_is_rejected(self):
        with patch.object(
            self.sova,
            "get_accounts",
            return_value=[{"name": "Talena Modern Projects"}],
        ):
            with self.assertRaisesRegex(ValueError, "has no code"):
                self.sova.get_template_accounts_with_projects()
