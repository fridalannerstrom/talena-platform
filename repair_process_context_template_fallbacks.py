#!/usr/bin/env python3
'''
Repair translated fallback values in the process-context template.

The previous i18n batch used translated variables as arguments to
Django's default filter. Django may try to resolve those arguments as
missing context variables at render time.

This repair replaces them with explicit if/else translation blocks.

Run from the repository root:

    python repair_process_context_template_fallbacks.py --check
    python repair_process_context_template_fallbacks.py --apply
'''

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path


TARGET_PATH = Path(
    "templates/customer/processes/process_role_context.html"
)

MARKER = (
    "{# Talena process context translated fallback repair 1 #}"
)


def replace_exact(
    text: str,
    old: str,
    new: str,
    *,
    expected: int,
    description: str,
) -> str:
    count = text.count(old)

    if count != expected:
        raise RuntimeError(
            f"{description}: expected {expected} occurrence(s), "
            f"found {count}.\n\nSearch text:\n{old}"
        )

    return text.replace(
        old,
        new,
        expected,
    )


def transform(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            "The process-context fallback repair "
            "has already been applied."
        )

    translated_variable_lines = (
        '{% trans "Process context" as default_process_context %}\n'
        '{% trans "Add context to tailor Candidate Insights to this process." as default_context_intro %}\n'
        '{% trans "Flexible process" as default_flexible_process %}\n'
        '{% trans "Context" as default_context_tab %}\n'
        '{% trans "Save context" as default_save_context %}\n'
    )

    text = replace_exact(
        text,
        translated_variable_lines,
        MARKER + "\n",
        expected=1,
        description=(
            "Remove translated fallback variables"
        ),
    )

    text = replace_exact(
        text,
        (
            "{{ context_config.context_title"
            "|default:default_process_context }}"
        ),
        (
            "{% if context_config.context_title %}"
            "{{ context_config.context_title }}"
            "{% else %}"
            '{% trans "Process context" %}'
            "{% endif %}"
        ),
        expected=2,
        description=(
            "Repair context-title fallback"
        ),
    )

    text = replace_exact(
        text,
        (
            "{{ context_config.context_intro"
            "|default:default_context_intro }}"
        ),
        (
            "{% if context_config.context_intro %}"
            "{{ context_config.context_intro }}"
            "{% else %}"
            '{% trans "Add context to tailor Candidate Insights to this process." %}'
            "{% endif %}"
        ),
        expected=2,
        description=(
            "Repair context-introduction fallback"
        ),
    )

    text = replace_exact(
        text,
        (
            "{{ process_purpose.label"
            "|default:process.purpose"
            "|default:default_flexible_process }}"
        ),
        (
            "{% if process_purpose.label %}"
            "{{ process_purpose.label }}"
            "{% elif process.purpose %}"
            "{{ process.purpose }}"
            "{% else %}"
            '{% trans "Flexible process" %}'
            "{% endif %}"
        ),
        expected=1,
        description=(
            "Repair current-purpose fallback"
        ),
    )

    text = replace_exact(
        text,
        (
            "{{ context_config.tab_label"
            "|default:default_context_tab }}"
        ),
        (
            "{% if context_config.tab_label %}"
            "{{ context_config.tab_label }}"
            "{% else %}"
            '{% trans "Context" %}'
            "{% endif %}"
        ),
        expected=1,
        description=(
            "Repair context-tab fallback"
        ),
    )

    text = replace_exact(
        text,
        (
            "{{ context_config.save_button"
            "|default:default_save_context }}"
        ),
        (
            "{% if context_config.save_button %}"
            "{{ context_config.save_button }}"
            "{% else %}"
            '{% trans "Save context" %}'
            "{% endif %}"
        ),
        expected=1,
        description=(
            "Repair save-button fallback"
        ),
    )

    forbidden = (
        "default_process_context",
        "default_context_intro",
        "default_flexible_process",
        "default_context_tab",
        "default_save_context",
    )

    for name in forbidden:
        if name in text:
            raise RuntimeError(
                f"Unresolved fallback variable remains: {name}"
            )

    return text


def main() -> int:
    parser = argparse.ArgumentParser()

    mode = parser.add_mutually_exclusive_group(
        required=True
    )

    mode.add_argument(
        "--check",
        action="store_true",
        help=(
            "Validate the repair without changing files."
        ),
    )

    mode.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Apply the validated repair."
        ),
    )

    parser.add_argument(
        "--root",
        default=".",
        help=(
            "Repository root. Defaults to the current directory."
        ),
    )

    args = parser.parse_args()

    root = Path(
        args.root
    ).resolve()

    target = root / TARGET_PATH

    if not target.exists():
        raise FileNotFoundError(
            f"Missing required file: {TARGET_PATH}"
        )

    original = target.read_text(
        encoding="utf-8"
    )

    updated = transform(
        original
    )

    print(
        "Validated process-context template fallback repair:"
    )
    print(
        f"  - {TARGET_PATH}"
    )

    if args.check:
        print(
            "CHECK OK: no files were changed."
        )
        return 0

    backup = target.with_suffix(
        target.suffix
        + ".bak-context-fallback-repair"
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
            updated
        )
        temporary = Path(
            handle.name
        )

    temporary.replace(
        target
    )

    print(
        "APPLY OK: translated context fallbacks "
        "now use explicit template conditions."
    )
    print(
        f"Backup: {backup.relative_to(root)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
