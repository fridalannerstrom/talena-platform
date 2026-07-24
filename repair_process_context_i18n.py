#!/usr/bin/env python3
'''
Repair and connect the complete process-context feature to Django i18n.

Files changed:
- apps/processes/purpose_context_config.py
- apps/processes/forms.py
- templates/customer/processes/process_role_context.html

Run from the repository root:

    python repair_process_context_i18n.py --check
    python repair_process_context_i18n.py --apply
'''

from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


CONFIG_PATH = Path(
    "apps/processes/purpose_context_config.py"
)
FORMS_PATH = Path(
    "apps/processes/forms.py"
)
TEMPLATE_PATH = Path(
    "templates/customer/processes/process_role_context.html"
)

MARKER = "Talena process context i18n batch 1"


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
            f"{description}: expected exactly {expected} occurrence(s), "
            f"found {count}.\n\nSearch text:\n{old[:900]}"
        )

    return text.replace(old, new, expected)


def replace_once(
    text: str,
    old: str,
    new: str,
    *,
    description: str,
) -> str:
    return replace_exact(
        text,
        old,
        new,
        description=description,
        expected=1,
    )


def compile_python(
    text: str,
    path: Path,
) -> None:
    try:
        compile(
            text,
            str(path),
            "exec",
        )
    except SyntaxError as exc:
        raise RuntimeError(
            f"{path}: generated Python is invalid: {exc}"
        ) from exc


def transform_config(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            f"{CONFIG_PATH}: batch has already been applied."
        )

    import_line = (
        "from django.utils.translation "
        "import gettext_lazy as _\n\n"
    )

    if (
        "from django.utils.translation "
        "import gettext_lazy as _"
    ) not in text:
        text = import_line + text

    start_token = "PURPOSE_CONTEXT_CONFIG = {"
    end_token = "\n\nDEFAULT_PURPOSE_CONTEXT_CONFIG"

    start = text.find(start_token)
    end = text.find(
        end_token,
        start,
    )

    if start == -1 or end == -1:
        raise RuntimeError(
            "Could not isolate PURPOSE_CONTEXT_CONFIG."
        )

    block = text[start:end]

    value_pattern = re.compile(
        r'(?m)^(\s+"[^"]+":\s+)"((?:[^"\\]|\\.)*)"(,?)$'
    )

    replaced_count = 0

    def wrap_value(match: re.Match) -> str:
        nonlocal replaced_count
        replaced_count += 1

        return (
            f'{match.group(1)}_("{match.group(2)}")'
            f"{match.group(3)}"
        )

    updated_block = value_pattern.sub(
        wrap_value,
        block,
    )

    if replaced_count < 100:
        raise RuntimeError(
            "Expected at least 100 process-context strings, "
            f"but only found {replaced_count}."
        )

    remaining = value_pattern.findall(
        updated_block
    )

    if remaining:
        raise RuntimeError(
            "Some context configuration strings were not wrapped."
        )

    updated_block = (
        f"# {MARKER}\n"
        + updated_block
    )

    updated = (
        text[:start]
        + updated_block
        + text[end:]
    )

    compile_python(
        updated,
        CONFIG_PATH,
    )

    return updated


def transform_forms(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            f"{FORMS_PATH}: batch has already been applied."
        )

    text = replace_once(
        text,
        '''class ProcessRoleContextForm(forms.ModelForm):
''',
        f'''# {MARKER}
class ProcessRoleContextForm(forms.ModelForm):
''',
        description="Add forms marker",
    )

    text = replace_once(
        text,
        '''                "placeholder": (
                    "Describe the role, situation or development context.\\n\\n"
                    "You can include:\\n"
                    "• responsibilities and expectations\\n"
                    "• important requirements or behaviours\\n"
                    "• team or organisational context\\n"
                    "• priorities, challenges or success criteria\\n"
                    "• areas you want Talena to explore"
                ),
''',
        '''                "placeholder": _(
                    "Describe the role, situation or development context.\\n\\n"
                    "You can include:\\n"
                    "• responsibilities and expectations\\n"
                    "• important requirements or behaviours\\n"
                    "• team or organisational context\\n"
                    "• priorities, challenges or success criteria\\n"
                    "• areas you want Talena to explore"
                ),
''',
        description="Translate context textarea placeholder",
    )

    text = replace_once(
        text,
        '''            config.get("context_field_label")
            or "Process context"
''',
        '''            config.get("context_field_label")
            or _("Process context")
''',
        description="Translate context field label fallback",
    )

    text = replace_once(
        text,
        '''            config.get("context_field_help")
            or (
                "Add the information that would help Talena interpret "
                "the assessment results in relation to this process."
            )
''',
        '''            config.get("context_field_help")
            or _(
                "Add the information that would help Talena interpret "
                "the assessment results in relation to this process."
            )
''',
        description="Translate context field help fallback",
    )

    compile_python(
        text,
        FORMS_PATH,
    )

    return text


def transform_template(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            f"{TEMPLATE_PATH}: batch has already been applied."
        )

    text = replace_once(
        text,
        '''{% load static %}
''',
        f'''{{% load static i18n %}}
{{# {MARKER} #}}
{{% trans "Process context" as default_process_context %}}
{{% trans "Add context to tailor Candidate Insights to this process." as default_context_intro %}}
{{% trans "Flexible process" as default_flexible_process %}}
{{% trans "Context" as default_context_tab %}}
{{% trans "Save context" as default_save_context %}}
''',
        description="Load template i18n and define translated defaults",
    )

    replacements = (
        (
            'context_config.context_title|default:"Process context"',
            "context_config.context_title|default:default_process_context",
            "Translate context title fallback",
        ),
        (
            'context_config.context_intro|default:"Add context to tailor Candidate Insights to this process."',
            "context_config.context_intro|default:default_context_intro",
            "Translate context intro fallback",
        ),
        (
            'process_purpose.label|default:process.purpose|default:"Flexible process"',
            "process_purpose.label|default:process.purpose|default:default_flexible_process",
            "Translate current-purpose fallback",
        ),
        (
            'context_config.tab_label|default:"Context"',
            "context_config.tab_label|default:default_context_tab",
            "Translate context tab fallback",
        ),
        (
            'context_config.save_button|default:"Save context"',
            "context_config.save_button|default:default_save_context",
            "Translate save-button fallback",
        ),
        (
            "                  Describe the situation",
            '                  {% trans "Describe the situation" %}',
            "Translate guide heading 1",
        ),
        (
            '''                  Explain the role, team, development goal or other
                  situation the assessment results should be considered in.''',
            '''                  {% trans "Explain the role, team, development goal or other situation the assessment results should be considered in." %}''',
            "Translate guide text 1",
        ),
        (
            "                  Explain what matters",
            '                  {% trans "Explain what matters" %}',
            "Translate guide heading 2",
        ),
        (
            '''                  Include important expectations, behaviours,
                  requirements, priorities or success criteria.''',
            '''                  {% trans "Include important expectations, behaviours, requirements, priorities or success criteria." %}''',
            "Translate guide text 2",
        ),
        (
            "                  Add useful nuance",
            '                  {% trans "Add useful nuance" %}',
            "Translate guide heading 3",
        ),
        (
            '''                  Include team context, current challenges or anything
                  Talena should take into account when generating insights.''',
            '''                  {% trans "Include team context, current challenges or anything Talena should take into account when generating insights." %}''',
            "Translate guide text 3",
        ),
        (
            "              You can paste existing material",
            '              {% trans "You can paste existing material" %}',
            "Translate paste-material heading",
        ),
        (
            '''              A job advertisement, requirement profile, development plan
              or internal notes can be pasted directly into the field.''',
            '''              {% trans "A job advertisement, requirement profile, development plan or internal notes can be pasted directly into the field." %}''',
            "Translate paste-material text",
        ),
        (
            "              Current purpose",
            '              {% trans "Current purpose" %}',
            "Translate current-purpose heading",
        ),
        (
            "                Existing context has been reused",
            '                {% trans "Existing context has been reused" %}',
            "Translate reused-context heading",
        ),
        (
            '''                This purpose does not have its own saved context yet.
                The previous context has been added as a starting point.
                Review it before saving.''',
            '''                {% trans "This purpose does not have its own saved context yet. The previous context has been added as a starting point. Review it before saving." %}''',
            "Translate reused-context text",
        ),
        (
            "              How Talena uses this",
            '              {% trans "How Talena uses this" %}',
            "Translate Talena usage heading",
        ),
        (
            '''              The context can be used together with the selected purpose
              and available assessment results when generating summaries,
              interpretations, questions and recommended next steps.''',
            '''              {% trans "The context can be used together with the selected purpose and available assessment results when generating summaries, interpretations, questions and recommended next steps." %}''',
            "Translate Talena usage text",
        ),
        (
            "              Cancel",
            '              {% trans "Cancel" %}',
            "Translate cancel button",
        ),
    )

    expected_counts = {
        "Translate context title fallback": 2,
        "Translate context intro fallback": 2,
    }

    for old, new, description in replacements:
        text = replace_exact(
            text,
            old,
            new,
            description=description,
            expected=expected_counts.get(
                description,
                1,
            ),
        )

    forbidden_phrases = (
        ">Describe the situation<",
        ">Explain what matters<",
        ">Add useful nuance<",
        ">How Talena uses this<",
    )

    for phrase in forbidden_phrases:
        if phrase in text:
            raise RuntimeError(
                f"Untranslated context template phrase remains: {phrase}"
            )

    return text


def build_changes(
    root: Path,
) -> list[Change]:
    transforms: tuple[
        tuple[Path, Callable[[str], str]],
        ...,
    ] = (
        (
            CONFIG_PATH,
            transform_config,
        ),
        (
            FORMS_PATH,
            transform_forms,
        ),
        (
            TEMPLATE_PATH,
            transform_template,
        ),
    )

    changes: list[Change] = []

    for relative_path, transform in transforms:
        target = root / relative_path

        if not target.exists():
            raise FileNotFoundError(
                f"Missing required file: {relative_path}"
            )

        original = target.read_text(
            encoding="utf-8"
        )
        updated = transform(
            original
        )

        if updated == original:
            raise RuntimeError(
                f"{relative_path}: no changes were produced."
            )

        changes.append(
            Change(
                path=relative_path,
                original=original,
                updated=updated,
            )
        )

    return changes


def write_changes(
    root: Path,
    changes: list[Change],
) -> None:
    for change in changes:
        target = root / change.path
        backup = target.with_suffix(
            target.suffix
            + ".bak-process-context-i18n"
        )

        if not backup.exists():
            shutil.copy2(
                target,
                backup,
            )

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=target.name + ".",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(
                change.updated
            )
            temporary = Path(
                handle.name
            )

        temporary.replace(
            target
        )


def main() -> int:
    parser = argparse.ArgumentParser()

    mode = parser.add_mutually_exclusive_group(
        required=True
    )

    mode.add_argument(
        "--check",
        action="store_true",
        help="Validate without changing files.",
    )

    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply the validated i18n changes.",
    )

    parser.add_argument(
        "--root",
        default=".",
        help="Repository root. Defaults to current directory.",
    )

    args = parser.parse_args()
    root = Path(
        args.root
    ).resolve()

    changes = build_changes(
        root
    )

    print(
        "Validated process-context i18n changes:"
    )

    for change in changes:
        print(
            f"  - {change.path}"
        )

    print(
        "Python compilation: OK"
    )

    if args.check:
        print(
            "CHECK OK: no files were changed."
        )
        return 0

    write_changes(
        root,
        changes,
    )

    print(
        "APPLY OK: the complete process-context "
        "feature is connected to Django i18n."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
