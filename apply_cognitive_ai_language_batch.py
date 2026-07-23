#!/usr/bin/env python3
# Talena Cognitive AI language batch.
#
# Run from the repository root:
#   python apply_cognitive_ai_language_batch.py --check
#   python apply_cognitive_ai_language_batch.py --apply

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


MARKER = "Talena cognitive AI language batch 1"


@dataclass(frozen=True)
class Change:
    path: Path
    original: str
    updated: str


def compile_python(source: str, path: Path) -> None:
    try:
        compile(source, str(path), "exec")
    except SyntaxError as error:
        lines = source.splitlines()
        line_number = error.lineno or 1
        start = max(1, line_number - 6)
        end = min(len(lines), line_number + 6)
        context = "\n".join(
            f"{number:>5}: {lines[number - 1]}"
            for number in range(start, end + 1)
        )
        raise RuntimeError(
            f"{path}: generated Python syntax is invalid: {error}\n\n"
            f"Generated context:\n{context}"
        ) from error


def function_block(
    text: str,
    function_name: str,
) -> tuple[int, int, str]:
    match = re.search(
        rf"(?m)^def {re.escape(function_name)}\(",
        text,
    )
    if not match:
        raise RuntimeError(
            f"Could not find function {function_name}."
        )

    start = match.start()
    next_match = re.search(
        r"(?m)^def [A-Za-z_]\w*\(",
        text[match.end():],
    )
    end = (
        match.end() + next_match.start()
        if next_match
        else len(text)
    )
    return start, end, text[start:end]


def transform_function(
    text: str,
    function_name: str,
    transformer,
) -> str:
    start, end, block = function_block(
        text,
        function_name,
    )
    updated = transformer(block)

    if updated == block:
        raise RuntimeError(
            f"No changes were produced in {function_name}."
        )

    return text[:start] + updated + text[end:]


def token_pattern(source: str) -> re.Pattern[str]:
    tokens = re.findall(
        r'"(?:\\.|[^"\\])*"'
        r"|'(?:\\.|[^'\\])*'"
        r"|[A-Za-zÀ-ÖØ-öø-ÿ0-9_]+"
        r"|[^\sA-Za-zÀ-ÖØ-öø-ÿ0-9_]",
        source.strip(),
    )

    if not tokens:
        raise RuntimeError(
            "Cannot create a matcher for empty text."
        )

    return re.compile(
        r"\s*".join(
            re.escape(token)
            for token in tokens
        )
    )


def replace_once(
    text: str,
    old: str,
    new: str,
    *,
    path: str,
) -> str:
    exact_count = text.count(old)

    if exact_count == 1:
        return text.replace(
            old,
            new,
            1,
        )

    if exact_count > 1:
        raise RuntimeError(
            f"{path}: expected 1 occurrence, found "
            f"{exact_count} for:\n{old[:500]}"
        )

    pattern = token_pattern(old)
    matches = list(
        pattern.finditer(text)
    )

    if len(matches) != 1:
        raise RuntimeError(
            f"{path}: expected 1 flexible occurrence, found "
            f"{len(matches)} for:\n{old[:500]}"
        )

    match = matches[0]
    line_start = text.rfind(
        "\n",
        0,
        match.start(),
    ) + 1
    leading_text = text[
        line_start:match.start()
    ]
    replacement_start = (
        line_start
        if not leading_text.strip()
        else match.start()
    )

    return (
        text[:replacement_start]
        + new.strip("\n")
        + text[match.end():]
    )


def ensure_result_map_entries(text: str) -> str:
    path = "apps/core/ai/language.py"

    for helper in (
        "get_request_ai_language",
        "get_ai_language_instruction",
        "get_ai_system_language_instruction",
        "ai_content_language_matches",
        "mark_ai_content_outdated_if_language_changed",
        "set_ai_content_language",
        "get_ai_language_update_fields",
    ):
        if f"def {helper}" not in text:
            raise RuntimeError(
                f"{path}: missing helper {helper}. "
                "Apply the earlier language batches first."
            )

    entries = (
        (
            "cognitive_interpretation",
            "ai_cognitive_interpretation",
        ),
        (
            "cognitive_questions",
            "ai_cognitive_questions",
        ),
    )

    missing = [
        entry
        for entry in entries
        if f'"{entry[0]}"' not in text
    ]

    if not missing:
        return text

    match = re.search(
        r"(?s)(_AI_CONTENT_RESULT_FIELDS\s*=\s*\{.*?)(\n\})",
        text,
    )
    if not match:
        raise RuntimeError(
            f"{path}: _AI_CONTENT_RESULT_FIELDS was not found."
        )

    addition = "".join(
        (
            f'\n    "{key}": (\n'
            f'        "{field}"\n'
            f"    ),"
        )
        for key, field in missing
    )

    replacement = (
        match.group(1)
        + addition
        + match.group(2)
    )

    return (
        text[:match.start()]
        + replacement
        + text[match.end():]
    )


def transform_interpretation(text: str) -> str:
    path = "apps/core/ai/cognitive_interpretation.py"

    if MARKER in text:
        raise RuntimeError(
            f"{path}: batch already applied."
        )

    text = replace_once(
        text,
        '''from .openai_client import (
    get_openai_client,
    get_chat_model,
)
''',
        '''from .openai_client import (
    get_openai_client,
    get_chat_model,
)
from .language import (
    get_ai_language_instruction,
    get_ai_language_update_fields,
    get_ai_system_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)

# Talena cognitive AI language batch 1
''',
        path=path,
    )

    def prompt(block: str) -> str:
        block = replace_once(
            block,
            '''def build_cognitive_interpretation_prompt(
    invitation,
    cognitive_results: list[dict[str, Any]],
) -> str:
''',
            '''def build_cognitive_interpretation_prompt(
    invitation,
    cognitive_results: list[dict[str, Any]],
    *,
    language_code: str = "en",
) -> str:
''',
            path=path,
        )
        block = replace_once(
            block,
            '''    shared_context = build_shared_ai_context(
        invitation
    )
''',
            '''    language_code = normalize_ai_language(
        language_code
    )
    language_instruction = get_ai_language_instruction(
        language_code
    )

    shared_context = build_shared_ai_context(
        invitation
    )
''',
            path=path,
        )
        block = replace_once(
            block,
            "- Write in professional, clear English.\n",
            (
                "{language_instruction}\n"
                "- Translate every user-facing JSON string, "
                "including title and label.\n"
            ),
            path=path,
        )
        return block

    text = transform_function(
        text,
        "build_cognitive_interpretation_prompt",
        prompt,
    )

    def empty_result(block: str) -> str:
        block = replace_once(
            block,
            '''def create_empty_cognitive_interpretation(
    owner,
) -> dict[str, Any]:
''',
            '''def create_empty_cognitive_interpretation(
    owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
''',
            path=path,
        )
        block = replace_once(
            block,
            '''    return {
        "title": "Cognitive interpretation",
        "label": "AI-supported interpretation",
''',
            '''    language_code = normalize_ai_language(
        language_code
    )

    return {
        "title": (
            "Kognitiv tolkning"
            if language_code == "sv"
            else "Cognitive interpretation"
        ),
        "label": (
            "AI-stödd tolkning"
            if language_code == "sv"
            else "AI-supported interpretation"
        ),
''',
            path=path,
        )
        return block

    text = transform_function(
        text,
        "create_empty_cognitive_interpretation",
        empty_result,
    )

    def stream(block: str) -> str:
        block = replace_once(
            block,
            '''def stream_cognitive_interpretation(
    *,
    owner,
    cognitive_results: list[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
''',
            '''def stream_cognitive_interpretation(
    *,
    owner,
    cognitive_results: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
''',
            path=path,
        )
        block = replace_once(
            block,
            '''    client = get_openai_client()

    prompt = build_cognitive_interpretation_prompt(
        invitation=owner,
        cognitive_results=cognitive_results,
    )
''',
            '''    language_code = normalize_ai_language(
        language_code
    )
    system_language_instruction = (
        get_ai_system_language_instruction(
            language_code
        )
    )

    client = get_openai_client()

    prompt = build_cognitive_interpretation_prompt(
        invitation=owner,
        cognitive_results=cognitive_results,
        language_code=language_code,
    )
''',
            path=path,
        )
        block = replace_once(
            block,
            '''                    "streaming format exactly."
''',
            '''                    "streaming format exactly. "
                    f"{system_language_instruction}"
''',
            path=path,
        )
        return block

    text = transform_function(
        text,
        "stream_cognitive_interpretation",
        stream,
    )

    def save(block: str) -> str:
        block = replace_once(
            block,
            '''def save_cognitive_interpretation(
    *,
    owner,
    interpretation: dict[str, Any],
):
''',
            '''def save_cognitive_interpretation(
    *,
    owner,
    interpretation: dict[str, Any],
    language_code: str = "en",
):
''',
            path=path,
        )
        block = replace_once(
            block,
            '''    interpretation["interpretation"] = (
''',
            '''    language_code = normalize_ai_language(
        language_code
    )
    interpretation["_language"] = language_code

    set_ai_content_language(
        owner,
        "cognitive_interpretation",
        language_code,
    )

    interpretation["interpretation"] = (
''',
            path=path,
        )
        block = replace_once(
            block,
            '''    owner.save(update_fields=[
        "ai_cognitive_interpretation",
        "ai_cognitive_interpretation_status",
        "ai_cognitive_interpretation_generated_at",
        "ai_cognitive_interpretation_purpose",
    ])
''',
            '''    owner.save(update_fields=[
        "ai_cognitive_interpretation",
        "ai_cognitive_interpretation_status",
        "ai_cognitive_interpretation_generated_at",
        "ai_cognitive_interpretation_purpose",
    ])

    language_update_fields = (
        get_ai_language_update_fields(
            owner
        )
    )
    if language_update_fields:
        owner.save(
            update_fields=language_update_fields
        )
''',
            path=path,
        )
        return block

    return transform_function(
        text,
        "save_cognitive_interpretation",
        save,
    )


def transform_questions(text: str) -> str:
    path = "apps/core/ai/cognitive_questions.py"

    if MARKER in text:
        raise RuntimeError(
            f"{path}: batch already applied."
        )

    text = replace_once(
        text,
        '''from .openai_client import (
    get_openai_client,
    get_chat_model,
)
''',
        '''from .openai_client import (
    get_openai_client,
    get_chat_model,
)
from .language import (
    get_ai_language_instruction,
    get_ai_language_update_fields,
    get_ai_system_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)

# Talena cognitive AI language batch 1
''',
        path=path,
    )

    def prompt(block: str) -> str:
        block = replace_once(
            block,
            '''def build_cognitive_questions_prompt(
    *,
    owner,
    cognitive_results: list[dict[str, Any]],
) -> str:
''',
            '''def build_cognitive_questions_prompt(
    *,
    owner,
    cognitive_results: list[dict[str, Any]],
    language_code: str = "en",
) -> str:
''',
            path=path,
        )
        block = replace_once(
            block,
            '''    shared_context = build_shared_ai_context(
        owner
    )
''',
            '''    language_code = normalize_ai_language(
        language_code
    )
    language_instruction = get_ai_language_instruction(
        language_code
    )

    shared_context = build_shared_ai_context(
        owner
    )
''',
            path=path,
        )
        block = replace_once(
            block,
            '''STREAMING OUTPUT FORMAT
Return newline-delimited JSON, also called NDJSON.
''',
            '''LANGUAGE
{language_instruction}
Translate every user-facing JSON string, including title and label.

STREAMING OUTPUT FORMAT
Return newline-delimited JSON, also called NDJSON.
''',
            path=path,
        )
        return block

    text = transform_function(
        text,
        "build_cognitive_questions_prompt",
        prompt,
    )

    def empty_result(block: str) -> str:
        block = replace_once(
            block,
            '''def create_empty_cognitive_questions(
    owner,
) -> dict[str, Any]:
''',
            '''def create_empty_cognitive_questions(
    owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
''',
            path=path,
        )
        block = replace_once(
            block,
            '''    return {
        "title": "Cognitive questions",
        "label": "AI-supported questions",
''',
            '''    language_code = normalize_ai_language(
        language_code
    )

    return {
        "title": (
            "Kognitiva frågor"
            if language_code == "sv"
            else "Cognitive questions"
        ),
        "label": (
            "AI-stödda frågor"
            if language_code == "sv"
            else "AI-supported questions"
        ),
''',
            path=path,
        )
        return block

    text = transform_function(
        text,
        "create_empty_cognitive_questions",
        empty_result,
    )

    def stream(block: str) -> str:
        block = replace_once(
            block,
            '''def stream_cognitive_questions(
    *,
    owner,
    cognitive_results: list[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
''',
            '''def stream_cognitive_questions(
    *,
    owner,
    cognitive_results: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
''',
            path=path,
        )
        block = replace_once(
            block,
            '''    client = get_openai_client()

    prompt = build_cognitive_questions_prompt(
        owner=owner,
        cognitive_results=cognitive_results,
    )
''',
            '''    language_code = normalize_ai_language(
        language_code
    )
    system_language_instruction = (
        get_ai_system_language_instruction(
            language_code
        )
    )

    client = get_openai_client()

    prompt = build_cognitive_questions_prompt(
        owner=owner,
        cognitive_results=cognitive_results,
        language_code=language_code,
    )
''',
            path=path,
        )
        block = replace_once(
            block,
            '''        "JSON output format exactly."
''',
            '''        "JSON output format exactly. "
        f"{system_language_instruction}"
''',
            path=path,
        )
        block = replace_once(
            block,
            '''    if meta_event is None:
        meta_event = {
            "type": "meta",
            "title": "Cognitive questions",
            "label": "AI-supported questions",
        }
''',
            '''    if meta_event is None:
        meta_event = {
            "type": "meta",
            "title": (
                "Kognitiva frågor"
                if language_code == "sv"
                else "Cognitive questions"
            ),
            "label": (
                "AI-stödda frågor"
                if language_code == "sv"
                else "AI-supported questions"
            ),
        }
''',
            path=path,
        )
        return block

    text = transform_function(
        text,
        "stream_cognitive_questions",
        stream,
    )

    def save(block: str) -> str:
        block = replace_once(
            block,
            '''def save_cognitive_questions(
    *,
    owner,
    result: dict[str, Any],
):
''',
            '''def save_cognitive_questions(
    *,
    owner,
    result: dict[str, Any],
    language_code: str = "en",
):
''',
            path=path,
        )
        block = replace_once(
            block,
            '''    questions = (
''',
            '''    language_code = normalize_ai_language(
        language_code
    )
    result["_language"] = language_code

    set_ai_content_language(
        owner,
        "cognitive_questions",
        language_code,
    )

    questions = (
''',
            path=path,
        )
        block = replace_once(
            block,
            '''    owner.save(
        update_fields=[
            "ai_cognitive_questions",
            "ai_cognitive_questions_status",
            "ai_cognitive_questions_generated_at",
            "ai_cognitive_questions_purpose",
        ]
    )
''',
            '''    owner.save(
        update_fields=[
            "ai_cognitive_questions",
            "ai_cognitive_questions_status",
            "ai_cognitive_questions_generated_at",
            "ai_cognitive_questions_purpose",
        ]
    )

    language_update_fields = (
        get_ai_language_update_fields(
            owner
        )
    )
    if language_update_fields:
        owner.save(
            update_fields=language_update_fields
        )
''',
            path=path,
        )
        return block

    return transform_function(
        text,
        "save_cognitive_questions",
        save,
    )


def ensure_views_language_import(text: str) -> str:
    path = "apps/processes/views.py"
    match = re.search(
        r"(?s)from apps\.core\.ai\.language import \((.*?)\)",
        text,
    )
    if not match:
        raise RuntimeError(
            f"{path}: language import block was not found."
        )

    names = [
        line.strip().rstrip(",")
        for line in match.group(1).splitlines()
        if line.strip()
    ]

    for required in (
        "ai_content_language_matches",
        "get_request_ai_language",
        "mark_ai_content_outdated_if_language_changed",
    ):
        if required not in names:
            names.append(required)

    replacement = (
        "from apps.core.ai.language import (\n"
        + "".join(
            f"    {name},\n"
            for name in names
        )
        + ")"
    )

    return (
        text[:match.start()]
        + replacement
        + text[match.end():]
    )


def transform_views(text: str) -> str:
    path = "apps/processes/views.py"

    if MARKER in text:
        raise RuntimeError(
            f"{path}: batch already applied."
        )

    text = ensure_views_language_import(
        text
    )

    marker_anchor = (
        "from apps.core.ai.cognitive_interpretation import ("
    )
    if marker_anchor not in text:
        raise RuntimeError(
            f"{path}: cognitive import block was not found."
        )

    text = text.replace(
        marker_anchor,
        "# Talena cognitive AI language batch 1\n"
        + marker_anchor,
        1,
    )

    def candidate_detail(block: str) -> str:
        if 'content_key="cognitive_interpretation"' in block:
            raise RuntimeError(
                f"{path}: Cognitive language checks already exist."
            )

        anchor = '''        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="motivation_interpretation",
'''
        if anchor not in block:
            anchor = '''        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="personality_interpretation",
'''
        if anchor not in block:
            raise RuntimeError(
                f"{path}: no existing AI language anchor was found "
                "in process_candidate_detail."
            )

        addition = '''        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="cognitive_interpretation",
            result_field="ai_cognitive_interpretation",
            status_field="ai_cognitive_interpretation_status",
            language_code=language_code,
        )
        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="cognitive_questions",
            result_field="ai_cognitive_questions",
            status_field="ai_cognitive_questions_status",
            language_code=language_code,
        )
'''

        return block.replace(
            anchor,
            addition + anchor,
            1,
        )

    text = transform_function(
        text,
        "process_candidate_detail",
        candidate_detail,
    )

    def interpretation_stream(block: str) -> str:
        anchor = '''    cognitive_results = extract_cognitive_results(
        invitation
    )
'''
        block = replace_once(
            block,
            anchor,
            '''    language_code = get_request_ai_language(
        request
    )
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="cognitive_interpretation",
        result_field="ai_cognitive_interpretation",
        status_field="ai_cognitive_interpretation_status",
        language_code=language_code,
    )

''' + anchor,
            path=path,
        )
        block = replace_once(
            block,
            '''    if should_return_saved_ai_result(
        saved_interpretation,
        current_status,
    ):
''',
            '''    if (
        ai_content_language_matches(
            invitation,
            "cognitive_interpretation",
            language_code,
        )
        and should_return_saved_ai_result(
            saved_interpretation,
            current_status,
        )
    ):
''',
            path=path,
        )
        block = replace_once(
            block,
            '''            create_empty_cognitive_interpretation(
                invitation
            )
''',
            '''            create_empty_cognitive_interpretation(
                invitation,
                language_code=language_code,
            )
''',
            path=path,
        )
        block = replace_once(
            block,
            '''                cognitive_results=cognitive_results,
            ):
''',
            '''                cognitive_results=cognitive_results,
                language_code=language_code,
            ):
''',
            path=path,
        )
        block = replace_once(
            block,
            '''                interpretation=interpretation,
            )
''',
            '''                interpretation=interpretation,
                language_code=language_code,
            )
''',
            path=path,
        )
        return block

    text = transform_function(
        text,
        "process_candidate_cognitive_interpretation_stream",
        interpretation_stream,
    )

    def questions_stream(block: str) -> str:
        anchor = '''    cognitive_results = extract_cognitive_results(
        invitation
    )
'''
        block = replace_once(
            block,
            anchor,
            '''    language_code = get_request_ai_language(
        request
    )
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="cognitive_questions",
        result_field="ai_cognitive_questions",
        status_field="ai_cognitive_questions_status",
        language_code=language_code,
    )

''' + anchor,
            path=path,
        )
        block = replace_once(
            block,
            '''    if should_return_saved_ai_result(
        saved_result,
        current_status,
    ):
''',
            '''    if (
        ai_content_language_matches(
            invitation,
            "cognitive_questions",
            language_code,
        )
        and should_return_saved_ai_result(
            saved_result,
            current_status,
        )
    ):
''',
            path=path,
        )
        block = replace_once(
            block,
            '''        result = create_empty_cognitive_questions(
            invitation
        )
''',
            '''        result = create_empty_cognitive_questions(
            invitation,
            language_code=language_code,
        )
''',
            path=path,
        )
        block = replace_once(
            block,
            '''                cognitive_results=cognitive_results,
            ):
''',
            '''                cognitive_results=cognitive_results,
                language_code=language_code,
            ):
''',
            path=path,
        )
        block = replace_once(
            block,
            '''                result=result,
            )
''',
            '''                result=result,
                language_code=language_code,
            )
''',
            path=path,
        )
        return block

    return transform_function(
        text,
        "process_candidate_cognitive_questions_stream",
        questions_stream,
    )


def prepare_changes(root: Path) -> list[Change]:
    paths = {
        "language": root / "apps/core/ai/language.py",
        "interpretation": (
            root / "apps/core/ai/cognitive_interpretation.py"
        ),
        "questions": (
            root / "apps/core/ai/cognitive_questions.py"
        ),
        "views": root / "apps/processes/views.py",
    }

    for path in paths.values():
        if not path.exists():
            raise FileNotFoundError(
                f"Required file is missing: {path}"
            )

    originals = {
        key: path.read_text(encoding="utf-8")
        for key, path in paths.items()
    }

    updated = {
        "language": ensure_result_map_entries(
            originals["language"]
        ),
        "interpretation": transform_interpretation(
            originals["interpretation"]
        ),
        "questions": transform_questions(
            originals["questions"]
        ),
        "views": transform_views(
            originals["views"]
        ),
    }

    for key, source in updated.items():
        compile_python(
            source,
            paths[key],
        )

    return [
        Change(
            path=paths[key],
            original=originals[key],
            updated=updated[key],
        )
        for key in (
            "language",
            "interpretation",
            "questions",
            "views",
        )
    ]


def apply_changes(changes: list[Change]) -> None:
    prepared = []

    for change in changes:
        backup = change.path.with_suffix(
            change.path.suffix
            + ".bak-cognitive-ai-language"
        )
        temporary = change.path.with_suffix(
            change.path.suffix
            + ".tmp-cognitive-ai-language"
        )

        if not backup.exists():
            shutil.copy2(
                change.path,
                backup,
            )

        temporary.write_text(
            change.updated,
            encoding="utf-8",
        )
        prepared.append(
            (
                change,
                backup,
                temporary,
            )
        )

    written = []

    try:
        for change, backup, temporary in prepared:
            temporary.replace(
                change.path
            )
            written.append(
                (
                    change,
                    backup,
                )
            )
    except Exception:
        for change, backup in reversed(written):
            shutil.copy2(
                backup,
                change.path,
            )
        raise
    finally:
        for _change, _backup, temporary in prepared:
            if temporary.exists():
                temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(
        required=True
    )
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()

    try:
        changes = prepare_changes(
            root
        )
    except Exception as error:
        print(
            f"\nERROR: {error}",
            file=sys.stderr,
        )
        print(
            "No project files were changed.",
            file=sys.stderr,
        )
        return 1

    print("Validated files:")
    for change in changes:
        print(
            f"- {change.path.relative_to(root)}"
        )

    if args.check:
        print(
            "\nSuccess: Cognitive Interpretation and Questions "
            "language support validated."
        )
        print(
            "No project files were changed."
        )
        return 0

    try:
        apply_changes(
            changes
        )
    except Exception as error:
        print(
            f"\nERROR while writing files: {error}",
            file=sys.stderr,
        )
        print(
            "Written files were restored from backups.",
            file=sys.stderr,
        )
        return 1

    print(
        "\nSuccess: Cognitive AI language support was applied."
    )
    print(
        "Backups end with .bak-cognitive-ai-language"
    )
    print("\nNext commands:")
    print("python manage.py check")
    print("git diff --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
