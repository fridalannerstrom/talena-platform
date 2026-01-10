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
        # Environment base (domain only)
        # Example: https://api-test.sovaonline.com
        env_base = os.getenv("SOVA_ENV_BASE", "https://api-test.sovaonline.com").rstrip("/")

        username = os.environ["SOVA_USERNAME"]
        password = os.environ["SOVA_PASSWORD"]
        auth = HTTPBasicAuth(username, password)

        # Candidate base paths to try.
        # You can override with SOVA_BASE_PATHS="integrations/cleo-test/v4,integrations/partner_v4"
        base_paths = os.getenv(
            "SOVA_BASE_PATHS",
            "integrations/cleo-test/v4,integrations/partner_v4"
        )
        base_paths = [p.strip().strip("/") for p in base_paths.split(",") if p.strip()]

        # Endpoints to try (GET)
        # You can override with SOVA_SMOKETEST_ENDPOINTS="accounts,openapi.json,swagger.json"
        endpoints = os.getenv(
            "SOVA_SMOKETEST_ENDPOINTS",
            "accounts,accounts/,openapi.json,swagger.json,health,version"
        )
        endpoints = [e.strip().lstrip("/") for e in endpoints.split(",") if e.strip()]

        # Optional: do a POST order-assessment if project_code is supplied
        project_code = os.getenv("SOVA_PROJECT_CODE", "").strip()
        do_order = os.getenv("SOVA_DO_ORDER", "0").strip() in ("1", "true", "True", "yes", "YES")

        self.stdout.write("🔌 SOVA smoke test starting…")
        self.stdout.write(f"Env base: {env_base}")
        self.stdout.write(f"Base paths to try: {base_paths}")
        self.stdout.write(f"Endpoints to try: {endpoints}")

        any_success = False

        # Try GETs across base paths/endpoints
        for base_path in base_paths:
            base_url = f"{env_base}/{base_path}/"
            self.stdout.write("")
            self.stdout.write(f"🧭 Trying base: {base_url}")

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

                # If we got 200, print a bit of body
                if status == 200:
                    any_success = True
                    self.stdout.write(_pretty_json(r))
                    self.stdout.write("—" * 60)

        # Optional: POST order-assessment
        if do_order:
            if not project_code:
                self.stderr.write("⚠️ SOVA_DO_ORDER=1 but SOVA_PROJECT_CODE is missing. Skipping order test.")
                return

            # Try order endpoint on each base path
            for base_path in base_paths:
                base_url = f"{env_base}/{base_path}/"
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
                    continue

                self.stdout.write(f"POST {url} -> {r.status_code}")
                self.stdout.write(_pretty_json(r))

        if not any_success:
            self.stdout.write("")
            self.stdout.write("ℹ️ No 200 responses yet. That’s ok—next step is to confirm correct base path + endpoints with SOVA.")
