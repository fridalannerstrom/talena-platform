PURPOSE_ALIASES = {
    "hiring": "recruitment",
    "recruiting": "recruitment",
    "recruitment": "recruitment",
    "selection": "recruitment",

    "role_match": "role_match",
    "role match": "role_match",

    "leadership_potential": "leadership_potential",
    "leadership potential": "leadership_potential",

    "leader_development": "leader_development",
    "leader development": "leader_development",
    "leadership_development": "leader_development",
    "leadership development": "leader_development",

    "employee_development": "employee_development",
    "employee development": "employee_development",
    "development": "employee_development",

    "career_path": "career_path",
    "career path": "career_path",

    "onboarding": "onboarding",

    "team_development": "team_development",
    "team development": "team_development",

    "reorganisation": "reorganisation",
    "reorganization": "reorganisation",

    "flexible": "flexible",
    "unsure": "flexible",
    "flexible_process": "flexible",
    "flexible process": "flexible",
}


def normalize_purpose_key(purpose):
    if not purpose:
        return "flexible"

    key = str(purpose).strip().lower()
    key = key.replace("-", "_")

    return PURPOSE_ALIASES.get(key, key)