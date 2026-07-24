#!/usr/bin/env python3
'''
Connect Talena's invitation email-template feature to Django i18n.

Files changed:
- apps/emails/views.py
- templates/emails/edit_invitation_template.html
- templates/emails/admin_edit_invitation_template.html

Existing Swedish templates are upgraded only when their subject and body
still exactly match Talena's old English default. Custom content is untouched.

Run from the repository root:

    python apply_invitation_email_template_i18n.py --check
    python apply_invitation_email_template_i18n.py --apply
'''

from __future__ import annotations

import argparse
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


VIEWS_PATH = Path("apps/emails/views.py")
CUSTOMER_TEMPLATE_PATH = Path(
    "templates/emails/edit_invitation_template.html"
)
ADMIN_TEMPLATE_PATH = Path(
    "templates/emails/admin_edit_invitation_template.html"
)

MARKER = "Talena invitation email template i18n batch 1"


@dataclass(frozen=True)
class Change:
    path: Path
    original: str
    updated: str


def replace_exact(
    text: str,
    old: str,
    new: str,
    *,
    description: str,
    expected: int = 1,
) -> str:
    count = text.count(old)

    if count != expected:
        raise RuntimeError(
            f"{description}: expected {expected} occurrence(s), "
            f"found {count}.\n\nSearch text:\n{old[:1000]}"
        )

    return text.replace(old, new, expected)


def compile_python(text: str, path: Path) -> None:
    try:
        compile(text, str(path), "exec")
    except SyntaxError as exc:
        raise RuntimeError(
            f"{path}: generated Python is invalid: {exc}"
        ) from exc


def transform_views(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            f"{VIEWS_PATH}: batch has already been applied."
        )

    text = replace_exact(
        text,
        "from django.contrib import messages\n",
        (
            "from django.contrib import messages\n"
            "from django.utils.translation import gettext as _\n"
            "from django.utils.translation import override\n"
        ),
        description="Add Django translation imports",
    )

    insertion = (
        "from apps.processes.purpose_context_config "
        "import get_purpose_context_config\n\n\n"
    )

    helpers = f'''from apps.processes.purpose_context_config import get_purpose_context_config


# {MARKER}
LEGACY_DEFAULT_INVITATION_SUBJECT = (
    "Invitation to assessment process"
)

LEGACY_DEFAULT_INVITATION_BODY = (
    "Hi {{first_name}},\\n\\n"
    "You have been invited to complete assessments for "
    "{{process_name}}.\\n\\n"
    "Click the link below to start:\\n"
    "{{assessment_url}}\\n\\n"
    "Best regards,\\n"
    "{{sender_full_name}}"
)


def get_default_invitation_template(
    language_code="sv",
):
    with override(language_code):
        return {{
            "subject": _(
                "Invitation to assessment process"
            ),
            "body": _(
                "Hi {{first_name}},\\n\\n"
                "You have been invited to complete assessments "
                "for {{process_name}}.\\n\\n"
                "Click the link below to start:\\n"
                "{{assessment_url}}\\n\\n"
                "Best regards,\\n"
                "{{sender_full_name}}"
            ),
        }}


def upgrade_legacy_default_invitation_template(
    template,
):
    if (
        template.subject
        != LEGACY_DEFAULT_INVITATION_SUBJECT
        or template.body
        != LEGACY_DEFAULT_INVITATION_BODY
    ):
        return False

    defaults = get_default_invitation_template(
        template.language or "sv"
    )

    if (
        template.subject == defaults["subject"]
        and template.body == defaults["body"]
    ):
        return False

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


'''

    text = replace_exact(
        text,
        insertion,
        helpers,
        description="Add translated defaults and safe legacy upgrade",
    )

    text = replace_exact(
        text,
        '        return HttpResponseForbidden("No access.")\n',
        (
            "        return HttpResponseForbidden(\n"
            '            _("No access.")\n'
            "        )\n"
        ),
        description="Translate no-access response",
    )

    text = replace_exact(
        text,
        (
            '        return HttpResponseForbidden("You do not have '
            'permission to edit this email template.")\n'
        ),
        (
            "        return HttpResponseForbidden(\n"
            "            _(\n"
            '                "You do not have permission to edit "\n'
            '                "this email template."\n'
            "            )\n"
            "        )\n"
        ),
        description="Translate permission response",
    )

    old_get_or_create = '''    tpl, _ = EmailTemplate.objects.get_or_create(
        process=process,
        template_type="invitation",
        language="sv",
        defaults=get_default_invitation_template(),
    )
'''

    new_get_or_create = '''    tpl, _created = EmailTemplate.objects.get_or_create(
        process=process,
        template_type="invitation",
        language="sv",
        defaults=get_default_invitation_template(
            "sv"
        ),
    )

    if not _created:
        upgrade_legacy_default_invitation_template(
            tpl
        )
'''

    text = replace_exact(
        text,
        old_get_or_create,
        new_get_or_create,
        description="Upgrade invitation templates safely",
        expected=2,
    )

    text = replace_exact(
        text,
        (
            '            messages.success(request, '
            '"Invitation email template updated.")\n'
        ),
        (
            "            messages.success(\n"
            "                request,\n"
            '                _("Invitation email template updated."),\n'
            "            )\n"
        ),
        description="Translate save success messages",
        expected=2,
    )

    old_helper = '''def get_default_invitation_template():
    return {
        "subject": "Invitation to assessment process",
        "body": (
            "Hi {first_name},\\n\\n"
            "You have been invited to complete assessments for {process_name}.\\n\\n"
            "Click the link below to start:\\n"
            "{assessment_url}\\n\\n"
            "Best regards,\\n"
            "{sender_full_name}"
        ),
    }


'''

    text = replace_exact(
        text,
        old_helper,
        "",
        description="Remove old English-only default helper",
    )

    compile_python(text, VIEWS_PATH)
    return text


def transform_customer_template(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            f"{CUSTOMER_TEMPLATE_PATH}: batch already applied."
        )

    text = replace_exact(
        text,
        "{% load static %}\n",
        (
            "{% load static i18n %}\n"
            f"{{# {MARKER} #}}\n"
        ),
        description="Load i18n in customer template",
    )

    replacements = [
        (
            '<div class="fw-semibold mb-1">Merge fields</div>',
            '<div class="fw-semibold mb-1">{% trans "Merge fields" %}</div>',
            "Merge fields",
        ),
        (
            "            Click a field to copy it, then paste it into the subject line or message.",
            '            {% trans "Click a field to copy it, then paste it into the subject line or message." %}',
            "Merge instructions",
        ),
        (
            "<span>Candidate’s first name</span>",
            '<span>{% trans "Candidate’s first name" %}</span>',
            "Candidate first name",
        ),
        (
            "<span>Candidate’s last name</span>",
            '<span>{% trans "Candidate’s last name" %}</span>',
            "Candidate last name",
        ),
        (
            "<span>Candidate’s email address</span>",
            '<span>{% trans "Candidate’s email address" %}</span>',
            "Candidate email",
        ),
        (
            "<span>Name of this test process</span>",
            '<span>{% trans "Name of this test process" %}</span>',
            "Process name",
        ),
        (
            "<span>Candidate’s personal assessment link</span>",
            '<span>{% trans "Candidate’s personal assessment link" %}</span>',
            "Assessment link",
        ),
        (
            "<span>Your first name</span>",
            '<span>{% trans "Your first name" %}</span>',
            "Sender first name",
        ),
        (
            "<span>Your last name</span>",
            '<span>{% trans "Your last name" %}</span>',
            "Sender last name",
        ),
        (
            "<span>Your full name</span>",
            '<span>{% trans "Your full name" %}</span>',
            "Sender full name",
        ),
        (
            '<div class="fw-semibold mb-1">Example</div>',
            '<div class="fw-semibold mb-1">{% trans "Example" %}</div>',
            "Example",
        ),
        (
            "              <code>Hi {first_name}</code> becomes <strong>Hi Anna</strong> when the email is sent.",
            '              {% blocktrans %}<code>Hi {first_name}</code> becomes <strong>Hi Anna</strong> when the email is sent.{% endblocktrans %}',
            "Example sentence",
        ),
        (
            '<div class="fw-semibold mb-1">Invitation email template</div>',
            '<div class="fw-semibold mb-1">{% trans "Invitation email template" %}</div>',
            "Invitation heading",
        ),
        (
            "              Personalise the email candidates receive when assessments are sent.",
            '              {% trans "Personalise the email candidates receive when assessments are sent." %}',
            "Invitation intro",
        ),
        (
            '<label class="form-label">Subject line</label>',
            '<label class="form-label">{% trans "Subject line" %}</label>',
            "Subject line",
        ),
        (
            '<label class="form-label">Message</label>',
            '<label class="form-label">{% trans "Message" %}</label>',
            "Message",
        ),
        (
            '<div class="fw-semibold mb-1">Tip</div>',
            '<div class="fw-semibold mb-1">{% trans "Tip" %}</div>',
            "Tip",
        ),
        (
            '''              Make sure the message always includes <code>{assessment_url}</code>.
              Without it, the candidate will not receive their personal assessment link in the email.''',
            '              {% blocktrans %}Make sure the message always includes <code>{assessment_url}</code>. Without it, the candidate will not receive their personal assessment link in the email.{% endblocktrans %}',
            "Assessment URL warning",
        ),
        (
            "              Save template",
            '              {% trans "Save template" %}',
            "Save template",
        ),
        (
            "              Cancel",
            '              {% trans "Cancel" %}',
            "Cancel",
        ),
        (
            '    const status = document.getElementById("phCopyStatus");\n',
            (
                '    const status = document.getElementById("phCopyStatus");\n'
                '    const copiedPrefix = \'{% trans "Copied:" %}\';\n'
                '    const copyFailedMessage = \'{% trans "Could not copy. Please select and copy manually." %}\';\n'
            ),
            "JavaScript translations",
        ),
        (
            "          setStatus(`Copied: ${val}`);",
            "          setStatus(`${copiedPrefix} ${val}`);",
            "Copied status",
        ),
        (
            '          setStatus("Could not copy. Please select and copy manually.");',
            "          setStatus(copyFailedMessage);",
            "Copy error status",
        ),
    ]

    for old, new, description in replacements:
        text = replace_exact(
            text,
            old,
            new,
            description=description,
        )

    return text


def transform_admin_template(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            f"{ADMIN_TEMPLATE_PATH}: batch already applied."
        )

    text = replace_exact(
        text,
        '{% extends "admin/accounts/companies/company_base.html" %}\n',
        (
            '{% extends "admin/accounts/companies/company_base.html" %}\n'
            "{% load i18n %}\n"
            f"{{# {MARKER} #}}\n"
        ),
        description="Load i18n in admin template",
    )

    replacements = [
        (
            "    ← Back to process",
            '    ← {% trans "Back to process" %}',
            "Back to process",
            1,
        ),
        (
            '<div class="text-muted small mb-1">Email template</div>',
            '<div class="text-muted small mb-1">{% trans "Email template" %}</div>',
            "Email template",
            1,
        ),
        (
            '<h1 class="h3 mb-1">Invitation email</h1>',
            '<h1 class="h3 mb-1">{% trans "Invitation email" %}</h1>',
            "Invitation email",
            1,
        ),
        (
            '''        Editing template for <strong>{{ process.name|default:"Untitled process" }}</strong>''',
            '''        {% if process.name %}{% blocktrans with process_name=process.name %}Editing template for <strong>{{ process_name }}</strong>{% endblocktrans %}{% else %}{% blocktrans %}Editing template for <strong>Untitled process</strong>{% endblocktrans %}{% endif %}''',
            "Editing template",
            1,
        ),
        (
            '''      {{ process.project_name_snapshot|default:process.project_code|default:"Assessment" }}''',
            '''      {% if process.project_name_snapshot %}{{ process.project_name_snapshot }}{% elif process.project_code %}{{ process.project_code }}{% else %}{% trans "Assessment" %}{% endif %}''',
            "Assessment fallback",
            1,
        ),
        (
            '<div class="fw-semibold">Template content</div>',
            '<div class="fw-semibold">{% trans "Template content" %}</div>',
            "Template content",
            1,
        ),
        (
            "          This email will be used when candidates are invited to this process.",
            '          {% trans "This email will be used when candidates are invited to this process." %}',
            "Admin intro",
            1,
        ),
        (
            '<label class="form-label">Subject</label>',
            '<label class="form-label">{% trans "Subject" %}</label>',
            "Subject",
            1,
        ),
        (
            '<label class="form-label">Body</label>',
            '<label class="form-label">{% trans "Body" %}</label>',
            "Body",
            1,
        ),
        (
            "              Cancel",
            '              {% trans "Cancel" %}',
            "Admin cancel",
            1,
        ),
        (
            "              Save template",
            '              {% trans "Save template" %}',
            "Admin save",
            1,
        ),
        (
            '<div class="fw-semibold">Available placeholders</div>',
            '<div class="fw-semibold">{% trans "Available placeholders" %}</div>',
            "Available placeholders",
            1,
        ),
        (
            "          Use these in the subject or body.",
            '          {% trans "Use these in the subject or body." %}',
            "Placeholder intro",
            1,
        ),
        (
            '<span class="text-muted small">Copy</span>',
            '<span class="text-muted small">{% trans "Copy" %}</span>',
            "Copy label",
            1,
        ),
        (
            "          Example: <code>Hi {first_name}</code> will use the candidate’s first name.",
            '          {% blocktrans %}Example: <code>Hi {first_name}</code> will use the candidate’s first name.{% endblocktrans %}',
            "Admin example",
            1,
        ),
        (
            '  document.addEventListener("DOMContentLoaded", () => {\n',
            (
                '  document.addEventListener("DOMContentLoaded", () => {\n'
                '    const copyLabel = \'{% trans "Copy" %}\';\n'
                '    const copiedLabel = \'{% trans "Copied" %}\';\n'
                '    const copyFailedLabel = \'{% trans "Could not copy" %}\';\n'
            ),
            "Admin JavaScript strings",
            1,
        ),
        (
            '            label.textContent = "Copied";',
            "            label.textContent = copiedLabel;",
            "Copied label",
            1,
        ),
        (
            '              label.textContent = "Copy";',
            "              label.textContent = copyLabel;",
            "Reset copy labels",
            2,
        ),
        (
            '            label.textContent = "Could not copy";',
            "            label.textContent = copyFailedLabel;",
            "Failed copy label",
            1,
        ),
    ]

    for old, new, description, expected in replacements:
        text = replace_exact(
            text,
            old,
            new,
            description=description,
            expected=expected,
        )

    return text


def build_changes(root: Path) -> list[Change]:
    transforms: tuple[
        tuple[Path, Callable[[str], str]],
        ...,
    ] = (
        (VIEWS_PATH, transform_views),
        (CUSTOMER_TEMPLATE_PATH, transform_customer_template),
        (ADMIN_TEMPLATE_PATH, transform_admin_template),
    )

    changes = []

    for relative_path, transform in transforms:
        target = root / relative_path

        if not target.exists():
            raise FileNotFoundError(
                f"Missing required file: {relative_path}"
            )

        original = target.read_text(encoding="utf-8")
        updated = transform(original)

        if updated == original:
            raise RuntimeError(
                f"{relative_path}: no changes produced."
            )

        changes.append(
            Change(
                path=relative_path,
                original=original,
                updated=updated,
            )
        )

    return changes


def write_changes(root: Path, changes: list[Change]) -> None:
    for change in changes:
        target = root / change.path
        backup = target.with_suffix(
            target.suffix
            + ".bak-invitation-email-i18n"
        )

        if not backup.exists():
            shutil.copy2(target, backup)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=target.name + ".",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(change.updated)
            temporary = Path(handle.name)

        temporary.replace(target)


def main() -> int:
    parser = argparse.ArgumentParser()

    mode = parser.add_mutually_exclusive_group(
        required=True
    )
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")

    parser.add_argument(
        "--root",
        default=".",
        help="Repository root. Defaults to current directory.",
    )

    args = parser.parse_args()
    root = Path(args.root).resolve()

    changes = build_changes(root)

    print(
        "Validated invitation email-template i18n changes:"
    )
    for change in changes:
        print(f"  - {change.path}")

    print("Python compilation: OK")

    if args.check:
        print("CHECK OK: no files were changed.")
        return 0

    write_changes(root, changes)

    print(
        "APPLY OK: invitation email-template pages and "
        "default content are connected to Django i18n."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
