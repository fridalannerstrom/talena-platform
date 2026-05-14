PROCESS_PURPOSES = [
    {
        "key": "hiring",
        "label": "Anställa en kandidat",
        "description": "Skapa en testprocess inför rekrytering och urval.",
    },
    {
        "key": "internal_role_match",
        "label": "Bedöma en intern rollmatch",
        "description": "Bedöm hur väl en medarbetare matchar en ny eller befintlig roll.",
    },
    {
        "key": "leadership_potential",
        "label": "Identifiera ledarpotential",
        "description": "Utforska potential för framtida ledarroller.",
    },
    {
        "key": "career_path",
        "label": "Identifiera karriärväg",
        "description": "Få stöd i att förstå möjliga utvecklings- och karriärvägar.",
    },
    {
        "key": "onboarding",
        "label": "Inför onboarding",
        "description": "Förstå hur en person bäst introduceras och får rätt stöd från start.",
    },
    {
        "key": "employee_development",
        "label": "Utveckla en medarbetare",
        "description": "Skapa underlag för utvecklingssamtal, coaching och individuell utveckling.",
    },
    {
        "key": "leader_development",
        "label": "Utveckla en ledare",
        "description": "Skapa underlag för ledarutveckling och reflektion.",
    },
    {
        "key": "team_development",
        "label": "Förstå och utveckla team",
        "description": "Utforska drivkrafter, beteenden och möjliga teammönster.",
    },
    {
        "key": "reorganisation",
        "label": "Stötta vid omorganisering",
        "description": "Få stöd vid förändring, ny rollfördelning eller intern omställning.",
    },
    {
        "key": "unsure",
        "label": "Jag är osäker / fri testprocess",
        "description": "Skapa en flexibel process utan ett bestämt syfte.",
    },
]

PURPOSE_RECOMMENDED_TESTS = {
    "hiring": ["personality", "motivation"],
    "internal_role_match": ["personality", "motivation"],
    "leadership_potential": ["personality", "motivation", "verbal", "logical", "numerical"],
    "career_path": ["personality", "motivation", "verbal", "logical", "numerical"],
    "onboarding": ["personality", "motivation"],
    "employee_development": ["personality", "motivation"],
    "leader_development": ["personality", "motivation"],
    "team_development": ["personality", "motivation"],
    "reorganisation": ["personality", "motivation"],
    "unsure": [],
}

AVAILABLE_TESTS = [
    {
        "key": "personality",
        "label": "Personality",
        "short_label": "PQ",
        "description": "Understand behavioural style, strengths, risks and role fit.",
    },
    {
        "key": "motivation",
        "label": "Motivation",
        "short_label": "MQ",
        "description": "Understand what drives the person and what environment supports performance.",
    },
    {
        "key": "verbal",
        "label": "Verbal",
        "short_label": "Verbal",
        "description": "Useful when the role requires reading, interpreting or communicating complex information.",
    },
    {
        "key": "logical",
        "label": "Logical",
        "short_label": "Logical",
        "description": "Useful when the role requires problem-solving, structure and analytical thinking.",
    },
    {
        "key": "numerical",
        "label": "Numerical",
        "short_label": "Numerical",
        "description": "Useful when the role involves numbers, data, finance, reporting or analysis.",
    },
]

DEV_SOVA_TEMPLATE_MAP = {
    "personality": {
        "account_code": "TQ_SWEDEN_ACCOUNT",
        "project_code": "OTS_Test_Project",
    },
    "motivation": {
        "account_code": "TQ_SWEDEN_ACCOUNT",
        "project_code": "TQ_IHP_TEST_PROJECT",
    },
}

def get_recommended_tests_for_purpose(purpose):
    return PURPOSE_RECOMMENDED_TESTS.get(purpose, [])


def resolve_dev_sova_template(selected_tests):
    selected = set(selected_tests or [])

    if "personality" in selected:
        return DEV_SOVA_TEMPLATE_MAP["personality"]

    if "motivation" in selected:
        return DEV_SOVA_TEMPLATE_MAP["motivation"]

    return None


def build_default_process_name(purpose, selected_tests):
    purpose_lookup = {item["key"]: item["label"] for item in PROCESS_PURPOSES}
    purpose_label = purpose_lookup.get(purpose, "Test process")

    test_labels = []
    for test in AVAILABLE_TESTS:
        if test["key"] in selected_tests:
            test_labels.append(test["short_label"])

    if test_labels:
        return f"{purpose_label} · {' + '.join(test_labels)}"

    return purpose_label