"""
Read-only pre-release check for Talena's 31 Sova assessment combinations.

Run in the intended Azure environment:
    python manage.py audit_sova_template_coverage

The command never creates assessment orders or modifies stored processes.
"""
from collections import defaultdict
from itertools import combinations

from django.core.management.base import BaseCommand, CommandError

from apps.core.integrations.sova import SovaClient
from apps.processes.services.process_recommendations import (
    TEST_ORDER,
    extract_tests_from_project_name,
    normalize_test_combination,
)
from apps.projects.models import ProjectMeta


class Command(BaseCommand):
    help = "Verify that Modern Projects supplies every unique Sova test combination."

    def handle(self, *args, **options):
        accounts = SovaClient().get_template_accounts_with_projects()
        account = accounts[0]
        account_code = str(account["code"]).strip()
        projects = account["projects"]

        metadata = {
            item.project_code: item
            for item in ProjectMeta.objects.filter(
                provider="sova", account_code=account_code
            )
        }
        found = defaultdict(list)
        unrecognized = []

        for project in projects:
            project_code = str(project.get("code") or "").strip()
            name = str(project.get("name") or project_code).strip()
            meta = metadata.get(project_code)
            tests = (
                [part.strip() for part in (meta.tests or "").split(",") if part.strip()]
                if meta else []
            )
            if not tests:
                tests = extract_tests_from_project_name(name)

            key = normalize_test_combination(tests)
            if not project_code or not key:
                unrecognized.append(name)
                continue
            found[key].append(name)

        expected = {
            tuple(combo)
            for size in range(1, len(TEST_ORDER) + 1)
            for combo in combinations(TEST_ORDER, size)
        }
        missing = sorted(expected - found.keys())
        duplicates = {key: names for key, names in found.items() if len(names) > 1}

        self.stdout.write(
            f"Sova account: {account.get('name')} ({account_code}); "
            f"{len(projects)} projects; {len(found)} unique combinations "
            f"(expected {len(expected)})."
        )
        if missing:
            self.stderr.write("Missing: " + ", ".join(" + ".join(key) for key in missing))
        if duplicates:
            for key, names in sorted(duplicates.items()):
                self.stderr.write(f"Duplicate {' + '.join(key)}: {names}")
        if unrecognized:
            self.stderr.write("Unrecognized: " + ", ".join(unrecognized))

        if missing or duplicates or unrecognized:
            raise CommandError("Modern Projects is not ready for Talena template selection.")

        self.stdout.write(self.style.SUCCESS(
            "OK: all 31 combinations match one project, and Test pictures is excluded."
        ))
