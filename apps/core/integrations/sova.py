import os
import requests
from requests.auth import HTTPBasicAuth
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

DEFAULT_ENV_BASE = "https://api-test.sovaonline.com"
DEFAULT_BASE_PATH = "integrations/cleo-test/v4"
DEFAULT_ORDER_BASE_PATH = "integrations/cleo-test/v4"


class SovaClient:
    def __init__(self):
        self.env_base = os.getenv("SOVA_ENV_BASE", DEFAULT_ENV_BASE).rstrip("/")
        self.base_path = os.getenv("SOVA_BASE_PATHS", DEFAULT_BASE_PATH).split(",")[0].strip().strip("/")
        self.username = os.environ["SOVA_USERNAME"]
        self.password = os.environ["SOVA_PASSWORD"]
        self.auth = HTTPBasicAuth(self.username, self.password)
        self.order_base_path = os.getenv("SOVA_ORDER_BASE_PATH", DEFAULT_ORDER_BASE_PATH).strip().strip("/")


    @property
    def base_url(self) -> str:
        return f"{self.env_base}/{self.base_path}/"
    
    @property
    def order_base_url(self) -> str:
        return f"{self.env_base}/{self.order_base_path}/"

    def get_accounts(self) -> list[dict]:
        r = requests.get(self.base_url + "accounts/", auth=self.auth, timeout=25)
        r.raise_for_status()
        return (r.json() or {}).get("accounts", []) or []

    def get_projects_for_account(self, account_code: str) -> list[dict]:
        url = self.base_url + f"accounts/{account_code}/projects/"
        r = requests.get(url, auth=self.auth, timeout=25)
        r.raise_for_status()
        return (r.json() or {}).get("projects", []) or []

    def get_accounts_with_projects(self) -> list[dict]:
        accounts = self.get_accounts()
        for a in accounts:
            code = (a.get("code") or "").strip()
            if code:
                a["projects"] = self.get_projects_for_account(code)
            else:
                a["projects"] = []
        return accounts
    
    def order_assessment(self, project_code: str, payload: dict) -> dict:
        """
        Orders an assessment in SOVA for a given project_code.
        Uses the existing integration base_url (cleo-test/v4).
        """
        url = self.base_url + f"order-assessment/{project_code}/"

        r = requests.post(url, json=payload, auth=self.auth, timeout=25)

        print("\n=== SOVA ORDER-ASSESSMENT RAW ===")
        print("URL:", url)
        print("STATUS:", r.status_code)
        print("TEXT:", r.text)
        print("=== /SOVA ORDER-ASSESSMENT RAW ===\n")

        r.raise_for_status()
        return r.json() or {}
    
    def get_project_candidates(self, project_id: int) -> dict:
        url = self.base_url + f"project-candidates/{project_id}/"
        r = requests.get(url, auth=self.auth, timeout=25)

        print("\n=== SOVA PROJECT-CANDIDATES RAW ===")
        print("URL:", url)
        print("STATUS:", r.status_code)
        print("TEXT:", r.text[:1000])
        print("=== /SOVA PROJECT-CANDIDATES RAW ===\n")

        r.raise_for_status()
        return r.json() or {}