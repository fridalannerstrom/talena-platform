#!/usr/bin/env python3
# Make Talena's pre-interview decision support language-aware.
#
# Files changed:
# - apps/core/ai/language.py
# - apps/core/ai/decision_support.py
# - apps/processes/views.py
#
# Run from the repository root:
#
#   python apply_pre_interview_decision_support_language.py --check
#   python apply_pre_interview_decision_support_language.py --apply

from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


MARKER = "Talena final output pre-interview language batch 1"

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
            f"Search text:\n{old[:800]}"
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


def transform_language(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            f"{LANGUAGE_PATH}: batch has already been applied."
        )

    old = '''# Talena personality language batch 1
_AI_CONTENT_RESULT_FIELDS.update({
    "personality_interpretation": "ai_personality_interpretation",
    "personality_questions": "ai_personality_questions",
})
'''

    new = old + f'''
# {MARKER}
_AI_CONTENT_RESULT_FIELDS.update({{
    "pre_interview_decision_support": (
        "ai_pre_interview_decision_support"
    ),
}})
'''

    return replace_once(
        text,
        old,
        new,
        description=(
            f"{LANGUAGE_PATH}: add pre-interview language mapping"
        ),
    )


def transform_decision_support(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            f"{DECISION_SUPPORT_PATH}: batch has already been applied."
        )

    text = replace_once(
        text,
        '''from django.utils import timezone

from .openai_client import (
''',
        f'''from django.utils import timezone

# {MARKER}
from .language import (
    get_ai_language_instruction,
    get_ai_language_update_fields,
    get_ai_system_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)

from .openai_client import (
''',
        description=(
            f"{DECISION_SUPPORT_PATH}: add language imports"
        ),
    )

    prompt_marker = '''# ============================================================
# Prompt
# ============================================================


def build_pre_interview_decision_support_prompt(
'''

    helper = f'''# ============================================================
# Prompt
# ============================================================


# {MARKER}
def _get_pre_interview_language_examples(
    language_code: str | None,
) -> dict[str, str]:
    language_code = normalize_ai_language(
        language_code
    )

    if language_code == "sv":
        return {{
            "title": "Beslutsstöd inför intervjun",
            "label": "AI-stött förberedande beslutsunderlag",
            "synthesis_1": "Första delen av den övergripande syntesen. ",
            "synthesis_2": "Nästa del av den övergripande syntesen. ",
            "indication_title": "Kort tematisk rubrik",
            "indication_interpretation": (
                "Försiktig och praktisk tolkning av temat."
            ),
            "caution_title": "Område som kräver försiktig tolkning",
            "caution_interpretation": (
                "Detta behöver valideras och sättas i rätt sammanhang."
            ),
            "caution_reason": (
                "Ytterligare beteendeexempel eller kontext saknas."
            ),
            "feedback_1": "Första konstruktiva återkopplingspunkten",
            "feedback_2": "Andra konstruktiva återkopplingspunkten",
            "focus_1": "Första fokusområdet för intervjun",
            "focus_2": "Andra fokusområdet för intervjun",
            "question": "Öppen och icke-ledande valideringsfråga",
            "why": "Varför frågan hjälper till att nyansera underlaget",
            "listen_for": (
                "Vilka konkreta exempel och nyanser som är viktiga att lyssna efter"
            ),
            "gap_1": (
                "Kandidatens exempel och intervjuunderlag har ännu inte lagts till."
            ),
            "gap_2": "Ytterligare relevant underlag som fortfarande saknas.",
            "context_note": (
                "Kort och transparent förklaring av vilket underlag som användes, "
                "vad som saknas och att det slutliga beslutet fattas av en människa."
            ),
        }}

    return {{
        "title": "Pre-interview decision support",
        "label": "AI-supported decision preparation",
        "synthesis_1": "First part of the synthesis. ",
        "synthesis_2": "Next part of the synthesis. ",
        "indication_title": "Theme title",
        "indication_interpretation": "Cautious practical interpretation",
        "caution_title": "Area requiring caution",
        "caution_interpretation": "What should be interpreted cautiously",
        "caution_reason": "Why caution is required",
        "feedback_1": "Feedback point one",
        "feedback_2": "Feedback point two",
        "focus_1": "Interview focus one",
        "focus_2": "Interview focus two",
        "question": "Open question",
        "why": "Why this helps",
        "listen_for": "What evidence or nuance to listen for",
        "gap_1": (
            "Candidate examples and interview evidence have not yet been added."
        ),
        "gap_2": "Another relevant evidence gap.",
        "context_note": (
            "Transparent explanation of the evidence used, evidence missing "
            "and the human user's responsibility for the final decision."
        ),
    }}


def build_pre_interview_decision_support_prompt(
'''

    text = replace_once(
        text,
        prompt_marker,
        helper,
        description=(
            f"{DECISION_SUPPORT_PATH}: add language examples helper"
        ),
    )

    text = replace_once(
        text,
        '''def build_pre_interview_decision_support_prompt(
    owner,
) -> str:
    shared_context = build_shared_ai_context(
''',
        '''def build_pre_interview_decision_support_prompt(
    owner,
    *,
    language_code: str | None = None,
) -> str:
    language_code = normalize_ai_language(
        language_code
    )
    language_instruction = get_ai_language_instruction(
        language_code
    )
    examples = _get_pre_interview_language_examples(
        language_code
    )

    shared_context = build_shared_ai_context(
''',
        description=(
            f"{DECISION_SUPPORT_PATH}: update prompt signature"
        ),
    )

    text = replace_once(
        text,
        '''LANGUAGE AND TONE

- Write in professional, clear English.
- Be balanced, practical and non-judgemental.
''',
        '''LANGUAGE AND TONE

{language_instruction}
- Be balanced, practical and non-judgemental.
''',
        description=(
            f"{DECISION_SUPPORT_PATH}: replace hard-coded English rule"
        ),
    )

    example_replacements = (
        (
            '''{{"type":"meta","title":"Pre-interview decision support","label":"AI-supported decision preparation"}}''',
            '''{{"type":"meta","title":"{examples['title']}","label":"{examples['label']}"}}''',
            "meta example",
        ),
        (
            '''{{"type":"overall_synthesis_delta","text":"First part of the synthesis. "}}
{{"type":"overall_synthesis_delta","text":"Next part of the synthesis. "}}''',
            '''{{"type":"overall_synthesis_delta","text":"{examples['synthesis_1']}"}}
{{"type":"overall_synthesis_delta","text":"{examples['synthesis_2']}"}}''',
            "synthesis examples",
        ),
        (
            '''{{"type":"purpose_relevant_indications","items":[{{"title":"Theme title","interpretation":"Cautious practical interpretation","evidence_sources":["AI Overview","Personality interpretation"]}}]}}''',
            '''{{"type":"purpose_relevant_indications","items":[{{"title":"{examples['indication_title']}","interpretation":"{examples['indication_interpretation']}","evidence_sources":["AI Overview","Personality interpretation"]}}]}}''',
            "indication example",
        ),
        (
            '''{{"type":"cautious_interpretations","items":[{{"title":"Area requiring caution","interpretation":"What should be interpreted cautiously","reason_for_caution":"Why caution is required"}}]}}''',
            '''{{"type":"cautious_interpretations","items":[{{"title":"{examples['caution_title']}","interpretation":"{examples['caution_interpretation']}","reason_for_caution":"{examples['caution_reason']}"}}]}}''',
            "caution example",
        ),
        (
            '''{{"type":"discussion_guidance","feedback_approach":["Feedback point one","Feedback point two"],"interview_focus":["Interview focus one","Interview focus two"]}}''',
            '''{{"type":"discussion_guidance","feedback_approach":["{examples['feedback_1']}","{examples['feedback_2']}"],"interview_focus":["{examples['focus_1']}","{examples['focus_2']}"]}}''',
            "discussion example",
        ),
        (
            '''{{"type":"validation_questions","items":[{{"question":"Open question","why":"Why this helps","listen_for":"What evidence or nuance to listen for"}}]}}''',
            '''{{"type":"validation_questions","items":[{{"question":"{examples['question']}","why":"{examples['why']}","listen_for":"{examples['listen_for']}"}}]}}''',
            "question example",
        ),
        (
            '''{{"type":"evidence_gaps","items":["Candidate examples and interview evidence have not yet been added.","Another relevant evidence gap."]}}''',
            '''{{"type":"evidence_gaps","items":["{examples['gap_1']}","{examples['gap_2']}"]}}''',
            "evidence-gap example",
        ),
        (
            '''{{"type":"context_note","text":"Transparent explanation of the evidence used, evidence missing and the human user's responsibility for the final decision."}}''',
            '''{{"type":"context_note","text":"{examples['context_note']}"}}''',
            "context-note example",
        ),
    )

    for old, new, label in example_replacements:
        text = replace_once(
            text,
            old,
            new,
            description=(
                f"{DECISION_SUPPORT_PATH}: localise {label}"
            ),
        )

    old_empty = '''def create_empty_pre_interview_decision_support(
    owner,
) -> dict[str, Any]:
    return {
        "title": (
            "Pre-interview decision support"
        ),
        "label": (
            "AI-supported decision preparation"
        ),
        "overall_synthesis": "",
        "purpose_relevant_indications": [],
        "cautious_interpretations": [],
        "discussion_guidance": {
            "feedback_approach": [],
            "interview_focus": [],
        },
        "validation_questions": [],
        "evidence_gaps": [],
        "context_note": "",
    }
'''

    new_empty = '''def create_empty_pre_interview_decision_support(
    owner,
    *,
    language_code: str | None = None,
) -> dict[str, Any]:
    language_code = normalize_ai_language(
        language_code
    )
    examples = _get_pre_interview_language_examples(
        language_code
    )

    return {
        "_language": language_code,
        "title": examples["title"],
        "label": examples["label"],
        "overall_synthesis": "",
        "purpose_relevant_indications": [],
        "cautious_interpretations": [],
        "discussion_guidance": {
            "feedback_approach": [],
            "interview_focus": [],
        },
        "validation_questions": [],
        "evidence_gaps": [],
        "context_note": "",
    }
'''

    text = replace_once(
        text,
        old_empty,
        new_empty,
        description=(
            f"{DECISION_SUPPORT_PATH}: localise empty result"
        ),
    )

    text = replace_once(
        text,
        '''def stream_pre_interview_decision_support(
    *,
    owner,
) -> Iterable[dict[str, Any]]:
    evidence = build_pre_interview_evidence(
''',
        '''def stream_pre_interview_decision_support(
    *,
    owner,
    language_code: str | None = None,
) -> Iterable[dict[str, Any]]:
    language_code = normalize_ai_language(
        language_code
    )

    evidence = build_pre_interview_evidence(
''',
        description=(
            f"{DECISION_SUPPORT_PATH}: update stream signature"
        ),
    )

    text = replace_once(
        text,
        '''        build_pre_interview_decision_support_prompt(
            owner
        )
''',
        '''        build_pre_interview_decision_support_prompt(
            owner,
            language_code=language_code,
        )
''',
        description=(
            f"{DECISION_SUPPORT_PATH}: pass language to prompt"
        ),
    )

    text = replace_once(
        text,
        '''                "content": (
                    "You are a careful and experienced "
                    "assessment synthesis consultant. "
                    "You organise evidence and uncertainty "
                    "but never make a suitability, matching, "
                    "selection, promotion or hiring decision. "
                    "Follow the requested NDJSON format exactly."
                ),
''',
        '''                "content": (
                    get_ai_system_language_instruction(
                        language_code
                    )
                    + " "
                    + "You are a careful and experienced "
                    "assessment synthesis consultant. "
                    "You organise evidence and uncertainty "
                    "but never make a suitability, matching, "
                    "selection, promotion or hiring decision. "
                    "Follow the requested NDJSON format exactly."
                ),
''',
        description=(
            f"{DECISION_SUPPORT_PATH}: add system language rule"
        ),
    )

    text = replace_once(
        text,
        '''def save_pre_interview_decision_support(
    *,
    owner,
    result: dict[str, Any],
):
    result["overall_synthesis"] = (
''',
        '''def save_pre_interview_decision_support(
    *,
    owner,
    result: dict[str, Any],
    language_code: str | None = None,
):
    language_code = normalize_ai_language(
        language_code
    )
    result["_language"] = language_code
    set_ai_content_language(
        owner,
        "pre_interview_decision_support",
        language_code,
    )

    result["overall_synthesis"] = (
''',
        description=(
            f"{DECISION_SUPPORT_PATH}: update save signature"
        ),
    )

    text = replace_once(
        text,
        '''            (
                "ai_pre_interview_"
                "decision_support_purpose"
            ),
        ]
''',
        '''            (
                "ai_pre_interview_"
                "decision_support_purpose"
            ),
            *get_ai_language_update_fields(
                owner
            ),
        ]
''',
        description=(
            f"{DECISION_SUPPORT_PATH}: save language metadata"
        ),
    )

    return text


def transform_views(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            f"{VIEWS_PATH}: batch has already been applied."
        )

    def update_candidate_detail(block: str) -> str:
        old = '''        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="personality_questions",
            result_field="ai_personality_questions",
            status_field="ai_personality_questions_status",
            language_code=language_code,
        )

        ctx = build_candidate_detail_context(
'''

        new = f'''        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="personality_questions",
            result_field="ai_personality_questions",
            status_field="ai_personality_questions_status",
            language_code=language_code,
        )
        # {MARKER}
        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="pre_interview_decision_support",
            result_field="ai_pre_interview_decision_support",
            status_field=(
                "ai_pre_interview_decision_support_status"
            ),
            language_code=language_code,
        )

        ctx = build_candidate_detail_context(
'''

        return replace_once(
            block,
            old,
            new,
            description=(
                f"{VIEWS_PATH}: mark pre-interview content outdated "
                "when candidate detail language changes"
            ),
        )

    text = transform_function(
        text,
        "process_candidate_detail",
        update_candidate_detail,
    )

    def update_pre_stream(block: str) -> str:
        block = replace_once(
            block,
            '''    current_status = (
        invitation
        .ai_pre_interview_decision_support_status
        or "not_started"
    )
''',
            f'''    # {MARKER}
    language_code = get_request_ai_language(
        request
    )
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="pre_interview_decision_support",
        result_field="ai_pre_interview_decision_support",
        status_field=(
            "ai_pre_interview_decision_support_status"
        ),
        language_code=language_code,
    )

    current_status = (
        invitation
        .ai_pre_interview_decision_support_status
        or "not_started"
    )
''',
            description=(
                f"{VIEWS_PATH}: read language in pre-interview stream"
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
            "pre_interview_decision_support",
            language_code,
        )
        and should_return_saved_ai_result(
            saved_result,
            current_status,
        )
    ):
''',
            description=(
                f"{VIEWS_PATH}: prevent returning saved result "
                "in the wrong language"
            ),
        )

        block = replace_once(
            block,
            '''            create_empty_pre_interview_decision_support(
                invitation
            )
''',
            '''            create_empty_pre_interview_decision_support(
                invitation,
                language_code=language_code,
            )
''',
            description=(
                f"{VIEWS_PATH}: pass language to empty pre-interview result"
            ),
        )

        block = replace_once(
            block,
            '''                stream_pre_interview_decision_support(
                    owner=invitation,
                )
''',
            '''                stream_pre_interview_decision_support(
                    owner=invitation,
                    language_code=language_code,
                )
''',
            description=(
                f"{VIEWS_PATH}: pass language to pre-interview stream"
            ),
        )

        block = replace_once(
            block,
            '''            save_pre_interview_decision_support(
                owner=invitation,
                result=result,
            )
''',
            '''            save_pre_interview_decision_support(
                owner=invitation,
                result=result,
                language_code=language_code,
            )
''',
            description=(
                f"{VIEWS_PATH}: save pre-interview result language"
            ),
        )

        return block

    text = transform_function(
        text,
        "process_candidate_pre_interview_decision_support_stream",
        update_pre_stream,
    )

    def update_final_output(block: str) -> str:
        old = '''    pre_interview_decision_support = (
        invitation.ai_pre_interview_decision_support
        or {}
    )
'''

        new = f'''    # {MARKER}
    language_code = get_request_ai_language(
        request
    )
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="pre_interview_decision_support",
        result_field="ai_pre_interview_decision_support",
        status_field=(
            "ai_pre_interview_decision_support_status"
        ),
        language_code=language_code,
    )

    pre_interview_decision_support = (
        invitation.ai_pre_interview_decision_support
        or {{}}
    )
'''

        return replace_once(
            block,
            old,
            new,
            description=(
                f"{VIEWS_PATH}: mark language mismatch in final-output refresh"
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
            + ".bak-pre-interview-language"
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
        "Validated pre-interview decision-support language changes:"
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
        "APPLY OK: pre-interview decision support "
        "is now language-aware."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
