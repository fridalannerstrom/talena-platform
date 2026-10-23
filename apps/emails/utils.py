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


# Candidate invitation copy for Swedish test processes.
# Preserve the placeholders so each message has the candidate's name and Sova link.
SWEDISH_DEFAULT_INVITATION_BODY = (
    "Hej {first_name},\n\n"
    "Du har blivit inbjuden att genomföra TQ:s tester.\n\n"
    "Testerna är ett sätt att få en bättre förståelse för dina personliga "
    "förutsättningar och kan bidra med värdefulla insikter som en del av "
    "en större helhetsbild.\n\n"
    "När du klickar på länken nedan kommer du till testmiljön, där du får "
    "mer information om vilka tester du ska genomföra, hur de går till "
    "och vad som kan vara bra att tänka på innan du börjar.\n\n"
    "Ta gärna dig tid att läsa igenom instruktionerna i lugn och ro "
    "innan du sätter igång.\n\n"
    "{assessment_url}"
)

# Only automatically migrate saved templates that exactly match an earlier
# Talena default. Never overwrite a process's customized invitation.
LEGACY_DEFAULT_INVITATION_TEMPLATES = (
    {
        "subject": "Invitation to assessment process",
        "body": (
            "Hi {first_name},\n\n"
            "You have been invited to complete assessments for "
            "{process_name}.\n\n"
            "Click the link below to start:\n"
            "{assessment_url}\n\n"
            "Best regards,\n"
            "{sender_full_name}"
        ),
    },
    {
        "subject": "Inbjudan till testprocess",
        "body": (
            "Hej {first_name},\n\n"
            "Du har blivit inbjuden att genomföra tester för "
            "{process_name}.\n\n"
            "Klicka på länken nedan för att börja:\n"
            "{assessment_url}\n\n"
            "Vänliga hälsningar,\n"
            "{sender_full_name}"
        ),
    },
    {
        "subject": "Inbjudan till testprocess",
        "body": (
            "Hej {first_name},\n\n"
            "Du har blivit inbjuden att genomföra tester.\n\n"
            "Klicka på länken nedan för att börja:\n"
            "{assessment_url}\n\n"
            "Vänliga hälsningar,\n"
            "{sender_full_name}"
        ),
    },
)


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
        subject = _("Invitation to assessment process")
        if language_code == "sv":
            # Explicit Swedish default so deployed .mo files cannot cause
            # the older wording to be sent after this copy change.
            body = SWEDISH_DEFAULT_INVITATION_BODY
        else:
            body = _(
                "Hi {first_name},\n\n"
                "You have been invited to complete assessments.\n\n"
                "Click the link below to start:\n"
                "{assessment_url}\n\n"
                "Best regards,\n"
                "{sender_full_name}"
            )

    return {
        "subject": subject,
        "body": body,
    }


def upgrade_legacy_default_invitation_template(template):
    """Refresh an untouched earlier default without replacing custom copy."""
    is_legacy_default = any(
        template.subject == legacy["subject"]
        and template.body == legacy["body"]
        for legacy in LEGACY_DEFAULT_INVITATION_TEMPLATES
    )
    if not is_legacy_default:
        return False

    defaults = get_default_invitation_template(
        template.language or "sv"
    )
    template.subject = defaults["subject"]
    template.body = defaults["body"]
    template.save(
        update_fields=[
            "subject",
            "body",
            "updated_at",
        ]
    )
    return True
