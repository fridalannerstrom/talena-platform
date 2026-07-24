#!/usr/bin/env python3
"""
Make Talena's post-interview decision support language-aware.

This batch expects the pre-interview language batch to have been applied.

Files changed:
- apps/core/ai/language.py
- apps/core/ai/decision_support.py
- apps/processes/views.py

Run from the repository root:

    python apply_post_interview_decision_support_language.py --check
    python apply_post_interview_decision_support_language.py --apply
"""

from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


MARKER = "Talena final output post-interview language batch 1"
PRE_MARKER = "Talena final output pre-interview language batch 1"

LANGUAGE_PATH = Path("apps/core/ai/language.py")
DECISION_SUPPORT_PATH = Path("apps/core/ai/decision_support.py")
VIEWS_PATH = Path("apps/processes/views.py")


@dataclass(frozen=True)
class Change:
    path: Path
    original: str
    updated: str


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
            f"{description}: expected exactly 1 occurrence, found {count}.\n\n"
            f"Search text:\n{old[:900]}"
        )

    return text.replace(old, new, 1)


def function_block(
    text: str,
    name: str,
) -> tuple[int, int, str]:
    match = re.search(
        rf"(?m)^def {re.escape(name)}\(",
        text,
    )

    if not match:
        raise RuntimeError(
            f"Could not find function {name}."
        )

    next_match = re.search(
        r"(?m)^(?:@[\w.]+(?:\([^\n]*\))?\n)*"
        r"def [A-Za-z_]\w*\(",
        text[match.end():],
    )

    end = (
        match.end() + next_match.start()
        if next_match
        else len(text)
    )

    return match.start(), end, text[match.start():end]


def transform_function(
    text: str,
    name: str,
    transform: Callable[[str], str],
) -> str:
    start, end, block = function_block(
        text,
        name,
    )

    updated_block = transform(block)

    if updated_block == block:
        raise RuntimeError(
            f"No changes were produced in {name}."
        )

    return text[:start] + updated_block + text[end:]


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


def ensure_pre_interview_batch(
    text: str,
    *,
    path: Path,
) -> None:
    if PRE_MARKER not in text:
        raise RuntimeError(
            f"{path}: the pre-interview language batch was not found. "
            "Apply and verify that batch before running this one."
        )


def transform_language(text: str) -> str:
    ensure_pre_interview_batch(
        text,
        path=LANGUAGE_PATH,
    )

    if MARKER in text:
        raise RuntimeError(
            f"{LANGUAGE_PATH}: batch has already been applied."
        )

    extension = f'''

# {MARKER}
_AI_CONTENT_RESULT_FIELDS.update({{
    "post_interview_decision_support": (
        "ai_post_interview_decision_support"
    ),
}})
'''

    return text.rstrip() + extension + "\n"


DECISION_SUPPORT_EXTENSION = f'''

# ============================================================
# {MARKER}
# Post-interview language support
# ============================================================

from .language import (
    get_ai_language_instruction as _post_get_ai_language_instruction,
    get_ai_language_update_fields as _post_get_ai_language_update_fields,
    get_ai_system_language_instruction as _post_get_ai_system_language_instruction,
    normalize_ai_language as _post_normalize_ai_language,
    set_ai_content_language as _post_set_ai_content_language,
)

_original_build_post_interview_decision_support_prompt = (
    build_post_interview_decision_support_prompt
)
_original_save_post_interview_decision_support = (
    save_post_interview_decision_support
)


def _get_post_interview_language_examples(
    language_code: str | None,
) -> dict[str, Any]:
    language_code = _post_normalize_ai_language(
        language_code
    )

    if language_code == "sv":
        return {{
            "title": "Beslutsstöd efter intervjun",
            "label": "Syntes av test- och intervjuunderlag",
            "synthesis": "Första delen av den sammanvägda syntesen. ",
            "supported": {{
                "title": "Indikation med stöd i intervjun",
                "assessment_indication": (
                    "Relevant indikation från testresultaten"
                ),
                "interview_evidence": (
                    "Relevant exempel eller observation från intervjun"
                ),
                "interpretation": "Försiktig sammanvägd tolkning",
            }},
            "nuance": {{
                "title": "Viktig nyans från intervjun",
                "assessment_indication": (
                    "Relevant indikation från testresultaten"
                ),
                "interview_evidence": (
                    "Relevant intervjuunderlag som tillför sammanhang"
                ),
                "interpretation": (
                    "Hur intervjuunderlaget nyanserar tolkningen"
                ),
            }},
            "contradiction": {{
                "title": "Spänning som behöver utforskas",
                "assessment_evidence": "Underlag från testresultaten",
                "interview_evidence": "Underlag från intervjun",
                "interpretation": (
                    "Balanserad förklaring av den möjliga spänningen"
                ),
            }},
            "uncertainties": [
                "Första kvarstående osäkerheten",
                "Andra kvarstående osäkerheten",
            ],
            "follow_up": [
                "Första föreslagna uppföljningen",
                "Andra föreslagna uppföljningen",
            ],
            "context_note": (
                "Transparent förklaring av vilket underlag som användes, "
                "dess begränsningar och människans ansvar för det slutliga beslutet."
            ),
        }}

    return {{
        "title": "Post-interview decision support",
        "label": "Assessment and interview synthesis",
        "synthesis": "First part of the synthesis. ",
        "supported": {{
            "title": "Theme title",
            "assessment_indication": "Relevant assessment indication",
            "interview_evidence": "Relevant interview example",
            "interpretation": "Cautious synthesis",
        }},
        "nuance": {{
            "title": "Theme title",
            "assessment_indication": "Relevant assessment indication",
            "interview_evidence": "Relevant interview evidence",
            "interpretation": "How the interview evidence adds nuance",
        }},
        "contradiction": {{
            "title": "Tension title",
            "assessment_evidence": "Assessment evidence",
            "interview_evidence": "Interview evidence",
            "interpretation": "Balanced explanation of the tension",
        }},
        "uncertainties": [
            "Uncertainty one",
            "Uncertainty two",
        ],
        "follow_up": [
            "Follow-up action one",
            "Follow-up action two",
        ],
        "context_note": (
            "Transparent explanation of the evidence used, limitations "
            "and human responsibility for the final decision."
        ),
    }}


def _replace_post_prompt_once(
    prompt: str,
    old: str,
    new: str,
    *,
    label: str,
) -> str:
    count = prompt.count(old)

    if count != 1:
        raise RuntimeError(
            "Could not localise the post-interview prompt "
            f"example {{label!r}}. Expected 1 occurrence, found {{count}}."
        )

    return prompt.replace(
        old,
        new,
        1,
    )


def build_post_interview_decision_support_prompt(
    owner,
    *,
    language_code: str | None = None,
) -> str:
    language_code = _post_normalize_ai_language(
        language_code
    )
    examples = _get_post_interview_language_examples(
        language_code
    )

    prompt = (
        _original_build_post_interview_decision_support_prompt(
            owner
        )
    )

    prompt = _replace_post_prompt_once(
        prompt,
        "- Write in professional, clear English.",
        _post_get_ai_language_instruction(
            language_code
        ),
        label="language instruction",
    )

    replacements = [
        (
            '{{"type":"meta","title":"Post-interview decision support","label":"Assessment and interview synthesis"}}',
            json.dumps(
                {{
                    "type": "meta",
                    "title": examples["title"],
                    "label": examples["label"],
                }},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "meta",
        ),
        (
            '{{"type":"overall_synthesis_delta","text":"First part of the synthesis. "}}',
            json.dumps(
                {{
                    "type": "overall_synthesis_delta",
                    "text": examples["synthesis"],
                }},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "overall synthesis",
        ),
        (
            '{{"type":"supported_indications","items":[{{"title":"Theme title","assessment_indication":"Relevant assessment indication","interview_evidence":"Relevant interview example","interpretation":"Cautious synthesis"}}]}}',
            json.dumps(
                {{
                    "type": "supported_indications",
                    "items": [examples["supported"]],
                }},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "supported indications",
        ),
        (
            '{{"type":"added_nuance","items":[{{"title":"Theme title","assessment_indication":"Relevant assessment indication","interview_evidence":"Relevant interview evidence","interpretation":"How the interview evidence adds nuance"}}]}}',
            json.dumps(
                {{
                    "type": "added_nuance",
                    "items": [examples["nuance"]],
                }},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "added nuance",
        ),
        (
            '{{"type":"contradictions","items":[{{"title":"Tension title","assessment_evidence":"Assessment evidence","interview_evidence":"Interview evidence","interpretation":"Balanced explanation of the tension"}}]}}',
            json.dumps(
                {{
                    "type": "contradictions",
                    "items": [examples["contradiction"]],
                }},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "contradictions",
        ),
        (
            '{{"type":"remaining_uncertainties","items":["Uncertainty one","Uncertainty two"]}}',
            json.dumps(
                {{
                    "type": "remaining_uncertainties",
                    "items": examples["uncertainties"],
                }},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "remaining uncertainties",
        ),
        (
            '{{"type":"suggested_follow_up","items":["Follow-up action one","Follow-up action two"]}}',
            json.dumps(
                {{
                    "type": "suggested_follow_up",
                    "items": examples["follow_up"],
                }},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "suggested follow-up",
        ),
        (
            '{{"type":"context_note","text":"Transparent explanation of the evidence used, limitations and human responsibility for the final decision."}}',
            json.dumps(
                {{
                    "type": "context_note",
                    "text": examples["context_note"],
                }},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "context note",
        ),
    ]

    for old, new, label in replacements:
        prompt = _replace_post_prompt_once(
            prompt,
            old,
            new,
            label=label,
        )

    return prompt


def create_empty_post_interview_decision_support(
    owner,
    *,
    language_code: str | None = None,
) -> dict[str, Any]:
    language_code = _post_normalize_ai_language(
        language_code
    )
    examples = _get_post_interview_language_examples(
        language_code
    )

    return {{
        "_language": language_code,
        "title": examples["title"],
        "label": examples["label"],
        "overall_synthesis": "",
        "supported_indications": [],
        "added_nuance": [],
        "contradictions": [],
        "remaining_uncertainties": [],
        "suggested_follow_up": [],
        "context_note": "",
    }}


def stream_post_interview_decision_support(
    *,
    owner,
    language_code: str | None = None,
) -> Iterable[dict[str, Any]]:
    language_code = _post_normalize_ai_language(
        language_code
    )

    interview_notes = _clean_text(
        owner.interview_notes
    )

    if not interview_notes:
        raise ValueError(
            "Interview notes must be added before "
            "post-interview decision support can be generated."
        )

    evidence = build_pre_interview_evidence(
        owner
    )

    if not evidence["has_evidence"]:
        raise ValueError(
            "No completed Talena interpretations "
            "are available for decision support."
        )

    client = get_openai_client()

    prompt = build_post_interview_decision_support_prompt(
        owner,
        language_code=language_code,
    )

    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {{
                "role": "system",
                "content": (
                    _post_get_ai_system_language_instruction(
                        language_code
                    )
                    + " "
                    + "You are a careful assessment synthesis "
                    "consultant. Compare assessment indications "
                    "with interview evidence without making a "
                    "matching, suitability, selection, promotion "
                    "or hiring decision. Follow the requested "
                    "NDJSON format exactly."
                ),
            }},
            {{
                "role": "user",
                "content": prompt,
            }},
        ],
        temperature=0.2,
        stream=True,
    )

    buffer = ""

    for response_event in stream:
        delta = response_event.choices[0].delta

        if not delta or not delta.content:
            continue

        buffer += delta.content

        parsed_events, buffer = (
            _extract_json_events_from_buffer(
                buffer
            )
        )

        for parsed_event in parsed_events:
            yield parsed_event

    parsed_events, buffer = (
        _extract_json_events_from_buffer(
            buffer
        )
    )

    for parsed_event in parsed_events:
        yield parsed_event

    trailing_content = (
        buffer
        .replace("```json", "")
        .replace("```ndjson", "")
        .replace("```", "")
        .strip()
    )

    if trailing_content:
        final_event = _parse_event_line(
            trailing_content
        )

        if final_event:
            yield final_event


def save_post_interview_decision_support(
    *,
    owner,
    result: dict[str, Any],
    language_code: str | None = None,
):
    language_code = _post_normalize_ai_language(
        language_code
    )
    result["_language"] = language_code

    _post_set_ai_content_language(
        owner,
        "post_interview_decision_support",
        language_code,
    )

    _original_save_post_interview_decision_support(
        owner=owner,
        result=result,
    )

    language_update_fields = (
        _post_get_ai_language_update_fields(
            owner
        )
    )

    if language_update_fields:
        owner.save(
            update_fields=language_update_fields
        )
'''


def transform_decision_support(text: str) -> str:
    ensure_pre_interview_batch(
        text,
        path=DECISION_SUPPORT_PATH,
    )

    if MARKER in text:
        raise RuntimeError(
            f"{DECISION_SUPPORT_PATH}: batch has already been applied."
        )

    required_functions = (
        "build_post_interview_decision_support_prompt",
        "create_empty_post_interview_decision_support",
        "stream_post_interview_decision_support",
        "save_post_interview_decision_support",
    )

    for function_name in required_functions:
        function_block(
            text,
            function_name,
        )

    return text.rstrip() + DECISION_SUPPORT_EXTENSION + "\n"


def transform_views(text: str) -> str:
    ensure_pre_interview_batch(
        text,
        path=VIEWS_PATH,
    )

    if MARKER in text:
        raise RuntimeError(
            f"{VIEWS_PATH}: batch has already been applied."
        )

    def update_candidate_detail(block: str) -> str:
        anchor = '''        ctx = build_candidate_detail_context(
'''

        insertion = f'''        # {MARKER}
        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="post_interview_decision_support",
            result_field="ai_post_interview_decision_support",
            status_field=(
                "ai_post_interview_decision_support_status"
            ),
            language_code=language_code,
        )

        ctx = build_candidate_detail_context(
'''

        return replace_once(
            block,
            anchor,
            insertion,
            description=(
                f"{VIEWS_PATH}: mark post-interview content outdated "
                "when candidate detail language changes"
            ),
        )

    text = transform_function(
        text,
        "process_candidate_detail",
        update_candidate_detail,
    )

    def update_post_stream(block: str) -> str:
        block = replace_once(
            block,
            '''    current_status = (
        invitation
        .ai_post_interview_decision_support_status
        or "not_started"
    )
''',
            f'''    # {MARKER}
    language_code = get_request_ai_language(
        request
    )
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="post_interview_decision_support",
        result_field="ai_post_interview_decision_support",
        status_field=(
            "ai_post_interview_decision_support_status"
        ),
        language_code=language_code,
    )

    current_status = (
        invitation
        .ai_post_interview_decision_support_status
        or "not_started"
    )
''',
            description=(
                f"{VIEWS_PATH}: read language in post-interview stream"
            ),
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
            "post_interview_decision_support",
            language_code,
        )
        and should_return_saved_ai_result(
            saved_result,
            current_status,
        )
    ):
''',
            description=(
                f"{VIEWS_PATH}: prevent returning post-interview "
                "content in the wrong language"
            ),
        )

        block = replace_once(
            block,
            '''            create_empty_post_interview_decision_support(
                invitation
            )
''',
            '''            create_empty_post_interview_decision_support(
                invitation,
                language_code=language_code,
            )
''',
            description=(
                f"{VIEWS_PATH}: pass language to empty post-interview result"
            ),
        )

        block = replace_once(
            block,
            '''                stream_post_interview_decision_support(
                    owner=invitation,
                )
''',
            '''                stream_post_interview_decision_support(
                    owner=invitation,
                    language_code=language_code,
                )
''',
            description=(
                f"{VIEWS_PATH}: pass language to post-interview stream"
            ),
        )

        block = replace_once(
            block,
            '''            save_post_interview_decision_support(
                owner=invitation,
                result=result,
            )
''',
            '''            save_post_interview_decision_support(
                owner=invitation,
                result=result,
                language_code=language_code,
            )
''',
            description=(
                f"{VIEWS_PATH}: save post-interview result language"
            ),
        )

        return block

    text = transform_function(
        text,
        "process_candidate_post_interview_decision_support_stream",
        update_post_stream,
    )

    def update_final_output(block: str) -> str:
        anchor = '''    post_interview_decision_support = (
        invitation.ai_post_interview_decision_support
        or {}
    )
'''

        insertion = f'''    # {MARKER}
    language_code = get_request_ai_language(
        request
    )
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="post_interview_decision_support",
        result_field="ai_post_interview_decision_support",
        status_field=(
            "ai_post_interview_decision_support_status"
        ),
        language_code=language_code,
    )

    post_interview_decision_support = (
        invitation.ai_post_interview_decision_support
        or {{}}
    )
'''

        return replace_once(
            block,
            anchor,
            insertion,
            description=(
                f"{VIEWS_PATH}: mark post-interview language mismatch "
                "in Final Output refresh"
            ),
        )

    text = transform_function(
        text,
        "process_candidate_final_output",
        update_final_output,
    )

    return text


def build_changes(root: Path) -> list[Change]:
    transforms = (
        (LANGUAGE_PATH, transform_language),
        (DECISION_SUPPORT_PATH, transform_decision_support),
        (VIEWS_PATH, transform_views),
    )

    changes: list[Change] = []

    for relative_path, transform in transforms:
        path = root / relative_path

        if not path.exists():
            raise FileNotFoundError(
                f"Missing required file: {relative_path}"
            )

        original = path.read_text(
            encoding="utf-8"
        )
        updated = transform(
            original
        )

        if updated == original:
            raise RuntimeError(
                f"{relative_path}: no changes were produced."
            )

        compile_python(
            updated,
            relative_path,
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
            + ".bak-post-interview-language"
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
            temporary_path = Path(
                handle.name
            )

        temporary_path.replace(
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
        help=(
            "Validate replacements and compile all generated "
            "Python without changing files."
        ),
    )

    mode.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Apply the validated language changes."
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

    changes = build_changes(
        root
    )

    print(
        "Validated post-interview decision-support language changes:"
    )

    for change in changes:
        print(
            f"  - {change.path}"
        )

    print(
        "\nGenerated Python compilation: OK"
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
        "APPLY OK: post-interview decision support "
        "is now language-aware."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
