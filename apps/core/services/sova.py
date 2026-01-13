import os
import requests
from requests.auth import HTTPBasicAuth

DEFAULT_ENV_BASE = "https://api-test.sovaonline.com"
DEFAULT_BASE_PATH = "integrations/cleo-test/v4"


class SovaClient:
    def __init__(self):
        self.env_base = os.getenv("SOVA_ENV_BASE", DEFAULT_ENV_BASE).rstrip("/")
        self.base_path = os.getenv("SOVA_BASE_PATHS", DEFAULT_BASE_PATH).split(",")[0].strip().strip("/")
        self.username = os.environ["SOVA_USERNAME"]
        self.password = os.environ["SOVA_PASSWORD"]
        self.auth = HTTPBasicAuth(self.username, self.password)

    @property
    def base_url(self) -> str:
        return f"{self.env_base}/{self.base_path}/"

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