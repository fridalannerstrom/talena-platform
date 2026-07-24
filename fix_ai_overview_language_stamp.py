#!/usr/bin/env python3
'''
Add the missing _language stamp to saved AI Overview results.

This batch changes only:
    apps/core/ai/purpose_fit.py

Run from the repository root:

    python fix_ai_overview_language_stamp.py --check
    python fix_ai_overview_language_stamp.py --apply
'''

from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from pathlib import Path


TARGET_PATH = Path("apps/core/ai/purpose_fit.py")
MARKER = "# Talena AI Overview result language stamp batch 1"


def find_function_block(
    text: str,
    function_name: str,
) -> tuple[int, int, str]:
    match = re.search(
        rf"(?m)^def {re.escape(function_name)}\(",
        text,
    )

    if not match:
        raise RuntimeError(
            f"Could not find {function_name}()."
        )

    next_function = re.search(
        r"(?m)^def [A-Za-z_]\w*\(",
        text[match.end():],
    )

    end = (
        match.end() + next_function.start()
        if next_function
        else len(text)
    )

    return (
        match.start(),
        end,
        text[match.start():end],
    )


def transform(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            "The AI Overview language-stamp batch "
            "has already been applied."
        )

    if "normalize_ai_language" not in text:
        raise RuntimeError(
            "purpose_fit.py does not import "
            "normalize_ai_language."
        )

    start, end, block = find_function_block(
        text,
        "save_candidate_purpose_fit",
    )

    search = '''    purpose_fit["summary"] = (
'''

    replacement = f'''    {MARKER}
    language_code = normalize_ai_language(
        language_code
    )
    purpose_fit["_language"] = language_code

    purpose_fit["summary"] = (
'''

    count = block.count(search)

    if count != 1:
        raise RuntimeError(
            "Expected exactly one summary normalisation "
            f"inside save_candidate_purpose_fit(), found {count}."
        )

    updated_block = block.replace(
        search,
        replacement,
        1,
    )

    updated = (
        text[:start]
        + updated_block
        + text[end:]
    )

    try:
        compile(
            updated,
            str(TARGET_PATH),
            "exec",
        )
    except SyntaxError as exc:
        raise RuntimeError(
            f"Generated purpose_fit.py is invalid: {exc}"
        ) from exc

    return updated


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
        help="Apply the validated change.",
    )

    parser.add_argument(
        "--root",
        default=".",
        help="Repository root. Defaults to current directory.",
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
        "Validated AI Overview language-stamp change:"
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
        + ".bak-ai-overview-language-stamp"
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
        "APPLY OK: newly saved AI Overview results "
        "will include _language."
    )
    print(
        f"Backup: {backup.relative_to(root)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
