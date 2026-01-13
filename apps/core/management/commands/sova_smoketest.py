import os
import json
import requests
from requests.auth import HTTPBasicAuth
from django.core.management.base import BaseCommand


def _pretty_json(response, limit=2000):
    try:
        data = response.json()
        return json.dumps(data, indent=2)[:limit]
    except Exception:
        return (response.text or "")[:limit]


class Command(BaseCommand):
    help = "Smoke test SOVA API connection (tries multiple base paths/endpoints)"

    def handle(self, *args, **options):
        env_base = os.getenv("SOVA_ENV_BASE", "https://api-test.sovaonline.com").rstrip("/")

        username = os.environ["SOVA_USERNAME"]
        password = os.environ["SOVA_PASSWORD"]
        auth = HTTPBasicAuth(username, password)

        base_paths = os.getenv(
            "SOVA_BASE_PATHS",
            "integrations/cleo-test/v4,integrations/partner_v4"
        )
        base_paths = [p.strip().strip("/") for p in base_paths.split(",") if p.strip()]

        endpoints = os.getenv(
            "SOVA_SMOKETEST_ENDPOINTS",
            "accounts/,health,version,openapi.json,swagger.json"
        )
        endpoints = [e.strip().lstrip("/") for e in endpoints.split(",") if e.strip()]

        project_code = os.getenv("SOVA_PROJECT_CODE", "").strip()
        do_order = os.getenv("SOVA_DO_ORDER", "0").strip() in ("1", "true", "True", "yes", "YES")

        self.stdout.write("🔌 SOVA smoke test starting…")
        self.stdout.write(f"Env base: {env_base}")
        self.stdout.write(f"Base paths to try: {base_paths}")
        self.stdout.write(f"Endpoints to try: {endpoints}")

        any_success = False

        for base_path in base_paths:
            base_url = f"{env_base}/{base_path}/"
            self.stdout.write("")
            self.stdout.write(f"🧭 Trying base: {base_url}")

            # 1) Run your generic GET endpoints
            for endpoint in endpoints:
                url = base_url + endpoint
                try:
                    r = requests.get(url, auth=auth, timeout=25)
                except Exception as e:
                    self.stderr.write(f"❌ GET {url} -> connection error: {e}")
                    continue

                status = r.status_code
                mark = "✅" if status == 200 else ("🔐" if status == 401 else ("🚫" if status == 403 else "❓"))
                self.stdout.write(f"{mark} GET {url} -> {status}")

                if status == 200:
                    any_success = True
                    self.stdout.write(_pretty_json(r))
                    self.stdout.write("—" * 60)

            # 2) Fetch accounts (we want codes)
            accounts_url = base_url + "accounts/"
            self.stdout.write("")
            self.stdout.write(f"📇 Fetching accounts: {accounts_url}")

            try:
                r_acc = requests.get(accounts_url, auth=auth, timeout=25)
            except Exception as e:
                self.stderr.write(f"❌ GET {accounts_url} -> connection error: {e}")
                continue

            self.stdout.write(f"{'✅' if r_acc.status_code == 200 else '❓'} GET {accounts_url} -> {r_acc.status_code}")

            if r_acc.status_code != 200:
                self.stdout.write(_pretty_json(r_acc))
                continue

            any_success = True
            data = r_acc.json() if r_acc.content else {}
            accounts = (data or {}).get("accounts", []) or []

            if not accounts:
                self.stdout.write("ℹ️ accounts/ returned 200 but no accounts in response.")
                continue

            # Print a compact list
            self.stdout.write("✅ Accounts found:")
            for a in accounts:
                self.stdout.write(f"  - id={a.get('id')} code={a.get('code')} name={a.get('name')}")

            self.stdout.write("—" * 60)

            # 3) For each account, fetch projects
            for a in accounts:
                account_code = (a.get("code") or "").strip()
                if not account_code:
                    continue

                projects_url = base_url + f"accounts/{account_code}/projects/"
                self.stdout.write("")
                self.stdout.write(f"📦 Fetching projects for {account_code}: {projects_url}")

                try:
                    r_proj = requests.get(projects_url, auth=auth, timeout=25)
                except Exception as e:
                    self.stderr.write(f"❌ GET {projects_url} -> connection error: {e}")
                    continue

                status = r_proj.status_code
                mark = "✅" if status == 200 else ("🔐" if status == 401 else ("🚫" if status == 403 else "❓"))
                self.stdout.write(f"{mark} GET {projects_url} -> {status}")

                if status == 200:
                    any_success = True
                    proj_data = r_proj.json() if r_proj.content else {}
                    projects = (proj_data or {}).get("projects", []) or []
                    if not projects:
                        self.stdout.write("ℹ️ 200 OK but no projects returned for this account.")
                    else:
                        self.stdout.write(f"✅ Projects ({len(projects)}):")
                        for p in projects:
                            self.stdout.write(
                                f"  - id={p.get('id')} code={p.get('code')} active={p.get('active')} name={p.get('name')}"
                            )
                else:
                    self.stdout.write(_pretty_json(r_proj))

                self.stdout.write("—" * 60)

            # Optional: POST order-assessment (unchanged)
            if do_order and project_code:
                url = base_url + f"order-assessment/{project_code}"
                payload = {
                    "request_id": os.getenv("SOVA_REQUEST_ID", "talena-smoke-001"),
                    "first_name": "Test",
                    "last_name": "User",
                    "email": os.getenv("SOVA_TEST_EMAIL", "test.user@example.com"),
                    "meta_data": {"source": "talena_smoketest"},
                }

                self.stdout.write("")
                self.stdout.write(f"🧪 POST order-assessment test: {url}")

                try:
                    r = requests.post(url, json=payload, auth=auth, timeout=30)
                except Exception as e:
                    self.stderr.write(f"❌ POST {url} -> connection error: {e}")
                else:
                    self.stdout.write(f"POST {url} -> {r.status_code}")
                    self.stdout.write(_pretty_json(r))

        if not any_success:
            self.stdout.write("")
            self.stdout.write("ℹ️ No 200 responses yet. Next step: confirm correct base path + endpoints with SOVA.")
