from django.utils.translation import (
    gettext as _,
    override,
)


ASSESSMENT_DISPLAY_NAMES = {
    "personality": "Personality",
    "motivation": "Motivation",
    "verbal": "Verbal Reasoning",
    "logical": "Logical Reasoning",
    "numerical": "Numerical Reasoning",
}


class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def render_placeholders(
    text: str,
    context: dict,
) -> str:
    return (text or "").format_map(
        SafeDict(**context)
    )


def format_assessment_names(selected_tests) -> str:
    # Return process assessments as an English comma-separated list.
    names = []

    for test in selected_tests or []:
        key = str(test or "").strip()

        if not key:
            continue

        normalized_key = key.lower()
        names.append(
            ASSESSMENT_DISPLAY_NAMES.get(
                normalized_key,
                key.replace("_", " ").title(),
            )
        )

    return ", ".join(names)


def get_default_invitation_template(
    language_code="sv",
):
    language_code = (
        language_code
        or "sv"
    ).strip().lower()

    if language_code not in {
        "sv",
        "en",
    }:
        language_code = "sv"

    with override(language_code):
        return {
            "subject": _(
                "Invitation to assessment process"
            ),
            "body": _(
                "Hi {first_name},\n\n"
                "You have been invited to complete assessments.\n\n"
                "Click the link below to start:\n"
                "{assessment_url}\n\n"
                "Best regards,\n"
                "{sender_full_name}"
            ),
        }