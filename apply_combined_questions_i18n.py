#!/usr/bin/env python3
'''
Connect Combined Questions section labels to Django i18n.

This batch changes only:
    apps/processes/views.py

It updates the dynamic section titles and descriptions used by:
    build_combined_candidate_questions()

Run from the repository root:

    python apply_combined_questions_i18n.py --check
    python apply_combined_questions_i18n.py --apply
'''

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path


TARGET_PATH = Path("apps/processes/views.py")
MARKER = "# Talena combined questions i18n batch 1"


def replace_once(
    text: str,
    old: str,
    new: str,
    *,
    description: str,
) -> str:
    count = text.count(old)

    if count != 1:
        raise RuntimeError(
            f"{description}: expected exactly 1 occurrence, "
            f"found {count}.\n\nSearch text:\n{old}"
        )

    return text.replace(old, new, 1)


def transform(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            "The Combined Questions i18n batch has already been applied."
        )

    if "from django.utils.translation import gettext as _" not in text:
        raise RuntimeError(
            "views.py does not import gettext as _. "
            "The batch cannot safely continue."
        )

    old_header = '''def build_combined_candidate_questions(
    invitation,
) -> dict:
'''

    new_header = f'''{MARKER}
def build_combined_candidate_questions(
    invitation,
) -> dict:
'''

    text = replace_once(
        text,
        old_header,
        new_header,
        description="Add Combined Questions i18n marker",
    )

    replacements = (
        (
            '''            "title": "Personality questions",''',
            '''            "title": _("Personality questions"),''',
            "Translate Personality questions title",
        ),
        (
            '''            "description": (
                "Explore how relevant personality preferences "
                "appear in practical situations."
            ),''',
            '''            "description": _(
                "Explore how relevant personality preferences "
                "appear in practical situations."
            ),''',
            "Translate Personality questions description",
        ),
        (
            '''            "title": "Motivation questions",''',
            '''            "title": _("Motivation questions"),''',
            "Translate Motivation questions title",
        ),
        (
            '''            "description": (
                "Explore what may create energy, engagement "
                "and sustainable motivation."
            ),''',
            '''            "description": _(
                "Explore what may create energy, engagement "
                "and sustainable motivation."
            ),''',
            "Translate Motivation questions description",
        ),
        (
            '''            "title": "Cognitive questions",''',
            '''            "title": _("Cognitive questions"),''',
            "Translate Cognitive questions title",
        ),
        (
            '''            "description": (
                "Explore how the cognitive assessment results "
                "relate to practical demands and working methods."
            ),''',
            '''            "description": _(
                "Explore how the cognitive assessment results "
                "relate to practical demands and working methods."
            ),''',
            "Translate Cognitive questions description",
        ),
    )

    for old, new, description in replacements:
        text = replace_once(
            text,
            old,
            new,
            description=description,
        )

    try:
        compile(
            text,
            str(TARGET_PATH),
            "exec",
        )
    except SyntaxError as exc:
        raise RuntimeError(
            f"Generated views.py is invalid Python: {exc}"
        ) from exc

    return text


def main() -> int:
    parser = argparse.ArgumentParser()

    mode = parser.add_mutually_exclusive_group(
        required=True
    )

    mode.add_argument(
        "--check",
        action="store_true",
        help="Validate the change without writing files.",
    )

    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply the validated change.",
    )

    parser.add_argument(
        "--root",
        default=".",
        help="Repository root. Defaults to the current directory.",
    )

    args = parser.parse_args()
    root = Path(args.root).resolve()
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
        "Validated Combined Questions i18n changes:"
    )
    print(
        f"  - {TARGET_PATH}"
    )
    print(
        "Generated Python compilation: OK"
    )

    if args.check:
        print(
            "CHECK OK: no files were changed."
        )
        return 0

    backup = target.with_suffix(
        target.suffix
        + ".bak-combined-questions-i18n"
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
        temporary_path = Path(
            handle.name
        )

    temporary_path.replace(
        target
    )

    print(
        "APPLY OK: Combined Questions dynamic labels "
        "are now connected to Django i18n."
    )
    print(
        f"Backup: {backup.relative_to(root)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
