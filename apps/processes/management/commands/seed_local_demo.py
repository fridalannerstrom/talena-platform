from __future__ import annotations

import getpass
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction

from apps.accounts.models import Company, CompanyMember, OrgUnit, UserOrgUnitAccess
from apps.processes.models import TestProcess
from apps.teams.models import Team


DEMO_USERNAME = "demo@talena.local"
DEMO_COMPANY_NAME = "Talena Local Demo"
DEMO_UNIT_CODE = "LOCAL-DEMO"
DEMO_PROCESS_CODE = "LOCAL-TEAM-DEMO"
DEMO_TEAM_NAME = "Demo team — communication styles"


class Command(BaseCommand):
    help = (
        "Create a complete, synthetic Talena workspace on local SQLite for "
        "manual development. No Sova requests or emails are sent."
    )

    def handle(self, *args, **options):
        self._assert_local_database()
        User = get_user_model()
        existing_user = User.objects.filter(username=DEMO_USERNAME).first()
        password = None

        if existing_user is None:
            password = os.environ.get("TALENA_LOCAL_DEMO_PASSWORD", "")
            if not password:
                password = getpass.getpass(
                    "Choose a password for the local demo login: "
                )
            if not password:
                raise CommandError("A password is required to create the demo login.")

        with transaction.atomic():
            user, _ = self._get_or_create_user(
                User,
                password=password,
            )
            company, _ = Company.objects.get_or_create(
                name=DEMO_COMPANY_NAME,
            )
            org_unit, _ = OrgUnit.objects.get_or_create(
                company=company,
                unit_code=DEMO_UNIT_CODE,
                defaults={"name": "Local demo unit"},
            )
            CompanyMember.objects.update_or_create(
                company=company,
                user=user,
                defaults={
                    "primary_org_unit": org_unit,
                    "role": CompanyMember.ROLE_ADMIN,
                },
            )
            UserOrgUnitAccess.objects.update_or_create(
                user=user,
                org_unit=org_unit,
                defaults={"permission": UserOrgUnitAccess.PERM_EDITOR},
            )

            process, _ = TestProcess.objects.get_or_create(
                company=company,
                project_code=DEMO_PROCESS_CODE,
                account_code=DEMO_PROCESS_CODE,
                defaults={
                    "name": "Demo project — team communication",
                    "project_name_snapshot": "Demo project — team communication",
                    "provider": "sova",
                    "org_unit": org_unit,
                    "created_by": user,
                    "created_by_admin": user,
                    "candidate_language": "sv",
                    "source": "sova_import",
                    "is_historical": True,
                    "sova_sync_enabled": False,
                    "sova_account_name": "LOCAL DEMO",
                    "sova_project_name": "LOCAL DEMO",
                    "sova_import_notes": (
                        "Synthetic local demo data. No real Sova project."
                    ),
                },
            )
            team, _ = Team.objects.get_or_create(
                company=company,
                name=DEMO_TEAM_NAME,
                defaults={
                    "org_unit": org_unit,
                    "created_by": user,
                    "goals": [
                        "understand_collaboration",
                        "develop_communication",
                    ],
                    "description": (
                        "A fictional team with varied communication preferences."
                    ),
                    "context": (
                        "Synthetic data for local product testing only."
                    ),
                },
            )

            # Reuse the existing, idempotent generator for three fully
            # synthetic candidate profiles and their historical assessment data.
            call_command(
                "seed_team_report_demo",
                process_id=process.pk,
                team_id=team.pk,
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Local demo workspace is ready."))
        self.stdout.write(f"Login: {DEMO_USERNAME}")
        self.stdout.write("Password: the one entered when this login was first created.")
        self.stdout.write(f"Company: {company.name}")
        self.stdout.write(f"Project: {process.name} (id {process.pk})")
        self.stdout.write(f"Team: {team.name} (id {team.pk})")
        self.stdout.write(
            "Three synthetic candidates have completed assessment results. "
            "Their names and emails are clearly marked as demo data."
        )

    def _assert_local_database(self):
        environment = str(getattr(settings, "ENVIRONMENT", "")).strip().lower()
        engine = settings.DATABASES["default"]["ENGINE"]

        if environment not in {"local", "development", "test", "testing"}:
            raise CommandError(
                "This command is restricted to local/development/test settings."
            )
        if engine != "django.db.backends.sqlite3":
            raise CommandError(
                "This command only runs on SQLite. Select "
                "DJANGO_SETTINGS_MODULE=config.settings_local first."
            )
        if not settings.DEBUG:
            raise CommandError(
                "DEBUG must be enabled for this local demo command."
            )

    def _get_or_create_user(self, User, password):
        user = User.objects.filter(username=DEMO_USERNAME).first()
        if user is not None:
            changed_fields = []
            if not user.is_active:
                user.is_active = True
                changed_fields.append("is_active")
            if user.role != "customer":
                user.role = "customer"
                changed_fields.append("role")
            if changed_fields:
                user.save(update_fields=changed_fields)
            return user, False

        user = User.objects.create_user(
            username=DEMO_USERNAME,
            email=DEMO_USERNAME,
            password=password,
            first_name="Talena",
            last_name="Demo",
            role="customer",
            is_active=True,
        )
        return user, True
