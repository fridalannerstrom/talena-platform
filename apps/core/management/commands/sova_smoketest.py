import os
import json
import requests
from requests.auth import HTTPBasicAuth
from django.core.management.base import BaseCommand


def _pretty_json(response, limit=4000):
    try:
        data = response.json()
        return json.dumps(data, indent=2)[:limit]
    except Exception:
        return (response.text or "")[:limit]


def _mark(status: int) -> str:
    if status == 200 or status == 201:
        return "✅"
    if status == 400:
        return "🧾"
    if status == 401:
        return "🔐"
    if status == 403:
        return "🚫"
    if status == 404:
        return "🕳️"
    return "❓"


class Command(BaseCommand):
    help = "SOVA smoke test: list accounts + projects, and optionally try order-assessment."

    def handle(self, *args, **options):
        env_base = os.getenv("SOVA_ENV_BASE", "https://api-test.sovaonline.com").rstrip("/")

        username = os.environ["SOVA_USERNAME"]
        password = os.environ["SOVA_PASSWORD"]
        auth = HTTPBasicAuth(username, password)

        # Use only first base path by default (keeps output clean)
        base_paths_raw = os.getenv("SOVA_BASE_PATHS", "integrations/cleo-test/v4")
        base_paths = [p.strip().strip("/") for p in base_paths_raw.split(",") if p.strip()]

        # Order test flags
        do_order = os.getenv("SOVA_DO_ORDER", "0").strip().lower() in ("1", "true", "yes")
        project_code = os.getenv("SOVA_PROJECT_CODE", "").strip()

        self.stdout.write("🔌 SOVA smoke test starting…")
        self.stdout.write(f"Env base: {env_base}")
        self.stdout.write(f"Base paths: {base_paths}")
        self.stdout.write(f"Order test enabled: {do_order} | Project code: {project_code or '(none)'}")

        for base_path in base_paths:
            base_url = f"{env_base}/{base_path}/"
            self.stdout.write("")
            self.stdout.write(f"🧭 Base: {base_url}")

            # 1) Accounts
            accounts_url = base_url + "accounts/"
            self.stdout.write(f"📇 GET {accounts_url}")

            try:
                r_acc = requests.get(accounts_url, auth=auth, timeout=25)
            except Exception as e:
                self.stderr.write(f"❌ GET accounts -> connection error: {e}")
                continue

            self.stdout.write(f"{_mark(r_acc.status_code)} {r_acc.status_code}")
            if r_acc.status_code != 200:
                self.stdout.write(_pretty_json(r_acc))
                continue

            accounts = (r_acc.json() or {}).get("accounts", []) or []
            if not accounts:
                self.stdout.write("ℹ️ No accounts returned.")
                continue

            self.stdout.write("✅ Accounts:")
            for a in accounts:
                self.stdout.write(f"  - id={a.get('id')} code={a.get('code')} name={a.get('name')}")
            self.stdout.write("—" * 60)

            # 2) Projects per account
            all_active_projects = []  # (account_code, project_code, project_obj)
            for a in accounts:
                account_code = (a.get("code") or "").strip()
                if not account_code:
                    continue

                projects_url = base_url + f"accounts/{account_code}/projects/"
                self.stdout.write(f"📦 GET {projects_url}")

                try:
                    r_proj = requests.get(projects_url, auth=auth, timeout=25)
                except Exception as e:
                    self.stderr.write(f"❌ GET projects for {account_code} -> connection error: {e}")
                    continue

                self.stdout.write(f"{_mark(r_proj.status_code)} {r_proj.status_code}")
                if r_proj.status_code != 200:
                    self.stdout.write(_pretty_json(r_proj))
                    self.stdout.write("—" * 60)
                    continue

                projects = (r_proj.json() or {}).get("projects", []) or []
                if not projects:
                    self.stdout.write("ℹ️ 200 OK but no projects returned.")
                    self.stdout.write("—" * 60)
                    continue

                # Print projects (active first)
                projects_sorted = sorted(projects, key=lambda p: (not p.get("active", False), (p.get("name") or "")))
                self.stdout.write(f"✅ Projects for {account_code} ({len(projects_sorted)}):")
                for p in projects_sorted:
                    p_code = p.get("code")
                    active = bool(p.get("active"))
                    self.stdout.write(f"  - id={p.get('id')} code={p_code} active={active} name={p.get('name')}")
                    if active and p_code:
                        all_active_projects.append((account_code, p_code, p))
                self.stdout.write("—" * 60)

            # 3) Optional: order-assessment test
            if do_order:
                # If not provided, pick first active project we found
                if not project_code:
                    if all_active_projects:
                        project_code = all_active_projects[0][1]
                        self.stdout.write(f"🎯 No SOVA_PROJECT_CODE set. Using first active project: {project_code}")
                    else:
                        self.stdout.write("⚠️ No active projects found to test ordering.")
                        continue

                payload = {
                    "request_id": os.getenv("SOVA_REQUEST_ID", "talena-smoke-001"),
                    "first_name": "Test",
                    "last_name": "User",
                    "email": os.getenv("SOVA_TEST_EMAIL", "test.user@example.com"),
                    "meta_data": {"source": "talena_smoketest"},
                }

                # Try common patterns. We stop on first non-404.
                order_paths = [
                    f"order-assessment/{project_code}/",
                    f"order-assessment/{project_code}",
                    f"projects/{project_code}/order-assessment/",
                    f"projects/{project_code}/order-assessment",
                    f"order-assessments/{project_code}/",
                    f"order-assessments/{project_code}",
                ]

                self.stdout.write("")
                self.stdout.write(f"🧪 Trying order-assessment variants for project: {project_code}")

                found = False
                for op in order_paths:
                    url = base_url + op
                    self.stdout.write(f"→ POST {url}")

                    try:
                        r = requests.post(url, json=payload, auth=auth, timeout=30)
                    except Exception as e:
                        self.stderr.write(f"❌ POST {url} -> connection error: {e}")
                        continue

                    self.stdout.write(f"{_mark(r.status_code)} {r.status_code}")
                    if r.status_code != 404:
                        self.stdout.write(_pretty_json(r))
                        found = True
                        break

                if not found:
                    self.stdout.write("ℹ️ All order-assessment variants returned 404 on this base path.")
                    self.stdout.write("   That usually means SOVA uses a different path/version for ordering in this environment.")
