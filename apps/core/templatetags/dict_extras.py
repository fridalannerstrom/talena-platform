from django import template
from django.utils.translation import get_language
import re

from apps.processes.purpose_utils import normalize_purpose_key


register = template.Library()


@register.filter
def get_item(d, key):
    return d.get(key) if d else None


@register.filter
def split_tests(value):
    """
    Split values such as "PQ, MQ", "PQ · MQ" or "['PQ', 'MQ']"
    into a clean list.
    """
    if not value:
        return []

    s = str(value).strip()

    if s.startswith("[") and s.endswith("]"):
        items = re.findall(r'["\']([^"\']+)["\']', s)
        if items:
            return [x.strip() for x in items if x.strip()]

        s = s[1:-1]

    parts = re.split(r"\s*(?:,|·)\s*", s)
    return [p.strip() for p in parts if p.strip()]


PURPOSE_LABELS = {
    "en": {
        "recruitment": "Recruitment",
        "role_match": "Role match",
        "leadership_potential": "Leadership potential",
        "leader_development": "Leadership development",
        "employee_development": "Employee development",
        "career_path": "Career development",
        "onboarding": "Onboarding",
        "team_development": "Team development",
        "reorganisation": "Reorganisation",
        "internal_mobility": "Internal mobility",
        "flexible": "Flexible process",
        "sandbox": "Sandbox",
    },
    "sv": {
        "recruitment": "Rekrytering",
        "role_match": "Rollmatchning",
        "leadership_potential": "Ledarskapspotential",
        "leader_development": "Ledarutveckling",
        "employee_development": "Medarbetarutveckling",
        "career_path": "Karriärutveckling",
        "onboarding": "Onboarding",
        "team_development": "Teamutveckling",
        "reorganisation": "Omorganisation",
        "internal_mobility": "Intern rörlighet",
        "flexible": "Flexibel process",
        "sandbox": "Sandbox",
    },
}


@register.filter
def purpose_label(value):
    """Return a compact process-purpose label in the active UI language."""
    language = "sv" if (get_language() or "").startswith("sv") else "en"

    if not value:
        return "Ej angivet" if language == "sv" else "Not specified"

    key = normalize_purpose_key(value)
    label = PURPOSE_LABELS.get(language, {}).get(key)

    if label:
        return label

    return str(key).replace("_", " ").strip().capitalize()
