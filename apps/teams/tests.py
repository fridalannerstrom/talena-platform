from django.test import TestCase

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.teams.models import Team
from apps.teams.views import _team_visibility_queryset, _user_can_edit_team


class TeamAccessTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme")
        self.unit = OrgUnit.objects.create(
            company=self.company,
            name="Sweden",
            unit_code="SE",
        )

        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="test-password",
        )
        self.viewer = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="test-password",
        )
        self.editor = User.objects.create_user(
            username="editor",
            email="editor@example.com",
            password="test-password",
        )
        self.own_only = User.objects.create_user(
            username="own-only",
            email="own@example.com",
            password="test-password",
        )

        for user in (self.owner, self.viewer, self.editor, self.own_only):
            CompanyMember.objects.create(
                company=self.company,
                user=user,
                primary_org_unit=self.unit,
            )

        UserOrgUnitAccess.objects.create(
            user=self.owner,
            org_unit=self.unit,
            permission="editor",
        )
        UserOrgUnitAccess.objects.create(
            user=self.viewer,
            org_unit=self.unit,
            permission="viewer",
        )
        UserOrgUnitAccess.objects.create(
            user=self.editor,
            org_unit=self.unit,
            permission="editor",
        )
        UserOrgUnitAccess.objects.create(
            user=self.own_only,
            org_unit=self.unit,
            permission="own",
        )

        self.shared_team = Team.objects.create(
            company=self.company,
            org_unit=self.unit,
            created_by=self.owner,
            name="Shared team",
        )
        self.own_team = Team.objects.create(
            company=self.company,
            org_unit=self.unit,
            created_by=self.own_only,
            name="Own team",
        )

    def test_viewer_and_editor_see_shared_team(self):
        viewer_ids = set(
            _team_visibility_queryset(self.viewer, self.company)
            .values_list("id", flat=True)
        )
        editor_ids = set(
            _team_visibility_queryset(self.editor, self.company)
            .values_list("id", flat=True)
        )

        self.assertIn(self.shared_team.id, viewer_ids)
        self.assertIn(self.shared_team.id, editor_ids)

    def test_own_user_sees_only_own_team(self):
        team_ids = set(
            _team_visibility_queryset(self.own_only, self.company)
            .values_list("id", flat=True)
        )

        self.assertEqual(team_ids, {self.own_team.id})

    def test_viewer_cannot_edit_but_editor_can(self):
        self.assertFalse(
            _user_can_edit_team(self.viewer, self.company, self.shared_team)
        )
        self.assertTrue(
            _user_can_edit_team(self.editor, self.company, self.shared_team)
        )

    def test_own_user_can_edit_own_team_only(self):
        self.assertTrue(
            _user_can_edit_team(self.own_only, self.company, self.own_team)
        )
        self.assertFalse(
            _user_can_edit_team(self.own_only, self.company, self.shared_team)
        )
