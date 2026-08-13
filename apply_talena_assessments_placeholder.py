
from pathlib import Path

ROOT = Path.cwd()
changes = []

def replace_once(path_str, old, new, marker=None):
    path = ROOT / path_str
    if not path.exists():
        raise SystemExit(
            f"ERROR: Could not find {path_str}. "
            "Run this script from the talena-platform root folder."
        )

    text = path.read_text(encoding="utf-8")

    if marker and marker in text:
        print(f"SKIP: {path_str} already contains the change.")
        return

    if old not in text:
        raise SystemExit(
            f"ERROR: Expected code was not found in {path_str}. "
            "Your local file may differ from main."
        )

    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    changes.append(path_str)
    print(f"OK:   {path_str}")


# 1) apps/emails/utils.py
replace_once(
    "apps/emails/utils.py",
    '''from django.utils.translation import (
    gettext as _,
    override,
)


class SafeDict(dict):
''',
    '''from django.utils.translation import (
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
''',
    marker="ASSESSMENT_DISPLAY_NAMES = {",
)

replace_once(
    "apps/emails/utils.py",
    '''def get_default_invitation_template(
    language_code="sv",
):
''',
    '''def format_assessment_names(selected_tests) -> str:
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
''',
    marker="def format_assessment_names(selected_tests)",
)

# 2) apps/emails/views.py
replace_once(
    "apps/emails/views.py",
    '''        "{email}",
        "{process_name}",
        "{assessment_url}",
''',
    '''        "{email}",
        "{process_name}",
        "{assessments}",
        "{assessment_url}",
''',
    marker='        "{assessments}",',
)

# 3) templates/emails/edit_invitation_template.html
replace_once(
    "templates/emails/edit_invitation_template.html",
    '''            <button type="button" class="merge-field-item" data-copy="{process_name}">
              <code>{process_name}</code>
              <span>{% trans "Name of this test process" %}</span>
            </button>

            <button type="button" class="merge-field-item" data-copy="{assessment_url}">
''',
    '''            <button type="button" class="merge-field-item" data-copy="{process_name}">
              <code>{process_name}</code>
              <span>{% trans "Name of this test process" %}</span>
            </button>

            <button type="button" class="merge-field-item" data-copy="{assessments}">
              <code>{assessments}</code>
              <span>{% trans "Assessments" %}</span>
            </button>

            <button type="button" class="merge-field-item" data-copy="{assessment_url}">
''',
    marker='data-copy="{assessments}"',
)

# 4) apps/processes/services/send_tests.py
replace_once(
    "apps/processes/services/send_tests.py",
    '''from apps.emails.utils import (
    render_placeholders,
    get_default_invitation_template,
)
''',
    '''from apps.emails.utils import (
    render_placeholders,
    get_default_invitation_template,
    format_assessment_names,
)
''',
    marker="    format_assessment_names,",
)

replace_once(
    "apps/processes/services/send_tests.py",
    '''                "email": candidate.email or "",
                "process_name": process.name or "",
                "job_title": process.job_title or "",
''',
    '''                "email": candidate.email or "",
                "process_name": process.name or "",
                "assessments": format_assessment_names(process.selected_tests),
                "job_title": process.job_title or "",
''',
    marker='"assessments": format_assessment_names(process.selected_tests)',
)

print()
if changes:
    print("Done! Updated:")
    for item in changes:
        print(f"  - {item}")
else:
    print("Nothing to do. The changes already appear to be present.")

print()
print("Next:")
print("  git diff")
print("Then test {assessments} in an invitation email template.")
