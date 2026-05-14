PROCESS_PURPOSES = [
    {
        "key": "hiring",
        "label": "Hire a candidate",
        "description": "Create an assessment process for recruitment and selection.",
    },
    {
        "key": "internal_role_match",
        "label": "Assess internal role match",
        "description": "Assess how well an employee matches a new or existing role.",
    },
    {
        "key": "leadership_potential",
        "label": "Identify leadership potential",
        "description": "Explore potential for future leadership roles.",
    },
    {
        "key": "career_path",
        "label": "Identify career path",
        "description": "Gain support in understanding possible development and career paths.",
    },
    {
        "key": "onboarding",
        "label": "Prepare for onboarding",
        "description": "Understand how a person can be introduced and supported in the best way from the start.",
    },
    {
        "key": "employee_development",
        "label": "Develop an employee",
        "description": "Create a foundation for development conversations, coaching and individual growth.",
    },
    {
        "key": "leader_development",
        "label": "Develop a leader",
        "description": "Create a foundation for leadership development and reflection.",
    },
    {
        "key": "team_development",
        "label": "Understand and develop a team",
        "description": "Explore drivers, behaviours and possible team patterns.",
    },
    {
        "key": "reorganisation",
        "label": "Support reorganisation",
        "description": "Gain support during change, new role distribution or internal transition.",
    },
    {
        "key": "unsure",
        "label": "I am unsure / free assessment process",
        "description": "Create a flexible process without a defined purpose.",
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