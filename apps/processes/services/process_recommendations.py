PROCESS_PURPOSES = [
    {
        "key": "hiring",
        "label": "Recruitment",
        "description": "Assess candidates for selection and role fit.",
    },
    {
        "key": "internal_role_match",
        "label": "Role match",
        "description": "Assess how well an employee matches a new or existing role.",
    },
    {
        "key": "leadership_potential",
        "label": "Leadership potential",
        "description": "Explore potential for future leadership roles.",
    },
    {
        "key": "career_path",
        "label": "Career path",
        "description": "Understand possible development and career directions.",
    },
    {
        "key": "onboarding",
        "label": "Onboarding",
        "description": "Understand how to support a person from the start.",
    },
    {
        "key": "employee_development",
        "label": "Employee development",
        "description": "Create a foundation for coaching and individual growth.",
    },
    {
        "key": "leader_development",
        "label": "Leader development",
        "description": "Create a foundation for leadership development and reflection.",
    },
    {
        "key": "team_development",
        "label": "Team development",
        "description": "Explore drivers, behaviours and team patterns.",
    },
    {
        "key": "reorganisation",
        "label": "Reorganisation",
        "description": "Support change, role distribution or internal transition.",
    },
    {
        "key": "unsure",
        "label": "Flexible process",
        "description": "Create a process without a defined purpose.",
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


def get_recommended_tests_for_purpose(purpose):
    return PURPOSE_RECOMMENDED_TESTS.get(purpose, [])


TEST_ORDER = (
    "personality",
    "motivation",
    "verbal",
    "logical",
    "numerical",
)


TEST_ALIASES = {
    # English
    "personality": "personality",
    "motivation": "motivation",
    "verbal": "verbal",
    "logical": "logical",
    "numerical": "numerical",

    # Swedish fallbacks, in case ProjectMeta contains Swedish names
    "personlighet": "personality",
    "motivationstest": "motivation",
    "verbal förmåga": "verbal",
    "logisk": "logical",
    "logisk förmåga": "logical",
    "numerisk": "numerical",
    "numerisk förmåga": "numerical",

    # Possible abbreviations
    "pq": "personality",
    "mq": "motivation",
}


def normalize_test_name(test_name):
    """
    Convert a test name from Talena or ProjectMeta to Talena's
    canonical lowercase test key.
    """
    normalized = str(test_name or "").strip().lower()

    return TEST_ALIASES.get(normalized, normalized)


def normalize_test_combination(tests):
    """
    Create a stable tuple for a test combination.

    The order in which tests were selected does not matter.
    Duplicates and empty values are removed.
    """
    normalized_tests = {
        normalize_test_name(test)
        for test in (tests or [])
        if str(test or "").strip()
    }

    return tuple(
        test_key
        for test_key in TEST_ORDER
        if test_key in normalized_tests
    )


def resolve_sova_template(selected_tests, template_cards):
    """
    Find the Sova project whose ProjectMeta tests match
    the tests selected by the user.

    Returns the matching template card, or None if no match exists.
    Raises ValueError if several Sova projects match the same combination.
    """
    selected_combination = normalize_test_combination(selected_tests)

    if not selected_combination:
        return None

    matches = []

    for template in template_cards:
        template_combination = normalize_test_combination(
            template.get("tests") or []
        )

        if template_combination == selected_combination:
            matches.append(template)

    if len(matches) > 1:
        project_names = ", ".join(
            match.get("title") or match.get("project_code") or "Unknown project"
            for match in matches
        )

        raise ValueError(
            "Several Sova projects match the selected test combination: "
            f"{project_names}"
        )

    return matches[0] if matches else None


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