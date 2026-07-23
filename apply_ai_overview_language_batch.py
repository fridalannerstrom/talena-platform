#!/usr/bin/env python3
"""
Apply Talena AI language support for the AI Overview safely.

Run from the repository root:

    python apply_ai_overview_language_batch.py --check
    python apply_ai_overview_language_batch.py --apply
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


MARKER = "Talena AI Overview language batch 1"


LANGUAGE_FILE_CONTENT = r'''from __future__ import annotations

from typing import Any


SUPPORTED_AI_LANGUAGES = {
    "en": "English",
    "sv": "Swedish",
}

DEFAULT_AI_LANGUAGE = "en"
LEGACY_AI_LANGUAGE = "en"


def normalize_ai_language(language_code: str | None) -> str:
    """Return a supported two-letter language code."""
    normalised = (
        str(language_code or "")
        .strip()
        .lower()
        .replace("_", "-")
        .split("-", 1)[0]
    )

    if normalised in SUPPORTED_AI_LANGUAGES:
        return normalised

    return DEFAULT_AI_LANGUAGE


def get_request_ai_language(request) -> str:
    """Read the active Django language from the current request."""
    return normalize_ai_language(
        getattr(request, "LANGUAGE_CODE", None)
    )


def get_ai_language_instruction(language_code: str | None) -> str:
    """Return prompt instructions for user-facing AI prose."""
    language_code = normalize_ai_language(language_code)

    if language_code == "sv":
        return (
            "- Write every user-facing sentence in professional, clear Swedish.\n"
            "- Use natural Swedish assessment terminology and cautious "
            "formulations such as \"kan indikera\", \"tyder på\", "
            "\"kan vara relevant\" and \"kan vara värdefullt att utforska\".\n"
            "- Keep JSON keys, event type values, and the fixed legacy "
            "recommendation and confidence values exactly as specified in English."
        )

    return (
        "- Write every user-facing sentence in professional, clear English.\n"
        "- Use cautious formulations such as \"may indicate\", \"suggests\", "
        "\"appears to\", \"could mean\", \"may be relevant\" and "
        "\"could be useful to explore\".\n"
        "- Keep JSON keys, event type values, and the fixed legacy "
        "recommendation and confidence values exactly as specified in English."
    )


def get_ai_system_language_instruction(
    language_code: str | None,
) -> str:
    """Return the language rule used in the OpenAI system message."""
    language_code = normalize_ai_language(language_code)

    if language_code == "sv":
        return (
            "Write all user-facing prose in Swedish. Keep technical JSON "
            "keys, event type values, and fixed legacy values in English."
        )

    return (
        "Write all user-facing prose in English. Keep technical JSON "
        "keys, event type values, and fixed legacy values in English."
    )


def get_purpose_fit_output_examples(
    language_code: str | None,
) -> dict[str, str]:
    """Return language-matched placeholder values for NDJSON examples."""
    language_code = normalize_ai_language(language_code)

    if language_code == "sv":
        return {
            "title": "AI-sammanfattning",
            "summary_1": "Första delen av tolkningen. ",
            "summary_2": "Nästa del av tolkningen. ",
            "support_1": "Första stödjande punkten",
            "support_2": "Andra stödjande punkten",
            "support_3": "Tredje stödjande punkten",
            "consider_1": "Första området att utforska",
            "consider_2": "Andra området att utforska",
            "consider_3": "Tredje området att utforska",
            "next_step": "Ett praktiskt och syftesrelevant nästa steg.",
            "context_note": (
                "Kort förklaring av vilka testresultat och vilken "
                "processkontext som användes."
            ),
        }

    return {
        "title": "AI Overview",
        "summary_1": "First part of the interpretation. ",
        "summary_2": "Next part of the interpretation. ",
        "support_1": "Supporting point one",
        "support_2": "Supporting point two",
        "support_3": "Supporting point three",
        "consider_1": "Consideration one",
        "consider_2": "Consideration two",
        "consider_3": "Consideration three",
        "next_step": "One practical and purpose-relevant next step.",
        "context_note": (
            "Brief explanation of the assessment evidence and "
            "process context used."
        ),
    }


def get_saved_ai_content_language(
    owner: Any,
    content_key: str,
) -> str:
    """Return the saved language, treating legacy content as English."""
    languages = getattr(owner, "ai_content_languages", None)

    if not isinstance(languages, dict):
        languages = {}

    return normalize_ai_language(
        languages.get(content_key) or LEGACY_AI_LANGUAGE
    )


def ai_content_language_matches(
    owner: Any,
    content_key: str,
    language_code: str | None,
) -> bool:
    """Return whether saved AI content matches the requested language."""
    return get_saved_ai_content_language(
        owner,
        content_key,
    ) == normalize_ai_language(language_code)


def set_ai_content_language(
    owner: Any,
    content_key: str,
    language_code: str | None,
) -> dict[str, str]:
    """Store the generation language on the model instance in memory."""
    languages = getattr(owner, "ai_content_languages", None)

    if not isinstance(languages, dict):
        languages = {}

    updated_languages = dict(languages)
    updated_languages[content_key] = normalize_ai_language(
        language_code
    )

    owner.ai_content_languages = updated_languages
    return updated_languages


def mark_ai_content_outdated_if_language_changed(
    owner: Any,
    *,
    content_key: str,
    result_field: str,
    status_field: str,
    language_code: str | None,
) -> bool:
    """Mark completed saved content outdated when its language differs."""
    saved_result = getattr(owner, result_field, None)
    current_status = (
        getattr(owner, status_field, None)
        or "not_started"
    )

    if not saved_result or current_status != "completed":
        return False

    if ai_content_language_matches(
        owner,
        content_key,
        language_code,
    ):
        return False

    setattr(owner, status_field, "outdated")
    owner.save(update_fields=[status_field])
    return True
'''


@dataclass(frozen=True)
class Replacement:
    old: str
    new: str
    expected_count: int = 1


def replace_exact(
    text: str,
    replacement: Replacement,
    *,
    path: str,
) -> str:
    """
    Prefer an exact replacement. If the local file only differs in
    indentation, line wrapping, CRLF/LF endings or spaces between tokens,
    retry with whitespace-tolerant matching.
    """
    count = text.count(replacement.old)

    if count == replacement.expected_count:
        return text.replace(
            replacement.old,
            replacement.new,
            replacement.expected_count,
        )

    source = replacement.old.strip()

    if source:
        tokens = re.findall(
            r'"(?:\\.|[^"\\])*"'
            r"|\'(?:\\.|[^\'\\])*\'"
            r"|[A-Za-z0-9_]+"
            r"|[^\sA-Za-z0-9_]",
            source,
        )

        pattern = re.compile(
            r"\s*".join(
                re.escape(token)
                for token in tokens
            )
        )

        flexible_count = len(pattern.findall(text))

        if flexible_count == replacement.expected_count:
            return pattern.sub(
                lambda _match: replacement.new.strip("\n"),
                text,
                count=replacement.expected_count,
            )

    raise RuntimeError(
        f"{path}: expected {replacement.expected_count} occurrence(s), "
        f"found {count} exact occurrence(s) for:\n"
        f"{replacement.old[:300]}"
    )


def transform_models(text: str) -> str:
    path = "apps/processes/models.py"

    if "ai_content_languages = models.JSONField(" in text:
        raise RuntimeError(f"{path}: batch appears to be applied already.")

    return replace_exact(
        text,
        Replacement(
            old='''    ai_summary_status = models.CharField(max_length=30, blank=True, default="not_started")

    # ------------------------------------------------------------
    # AI purpose fit
''',
            new='''    ai_summary_status = models.CharField(max_length=30, blank=True, default="not_started")

    # ------------------------------------------------------------
    # AI content language metadata
    # ------------------------------------------------------------
    ai_content_languages = models.JSONField(
        default=dict,
        blank=True,
    )

    # ------------------------------------------------------------
    # AI purpose fit
''',
        ),
        path=path,
    )


def transform_purpose_fit(text: str) -> str:
    path = "apps/core/ai/purpose_fit.py"

    if MARKER in text:
        raise RuntimeError(f"{path}: batch appears to be applied already.")

    replacements = [
        Replacement(
            old='''from .openai_client import get_openai_client, get_chat_model
''',
            new='''from .openai_client import get_openai_client, get_chat_model
from .language import (
    get_ai_language_instruction,
    get_ai_system_language_instruction,
    get_purpose_fit_output_examples,
    normalize_ai_language,
    set_ai_content_language,
)

# Talena AI Overview language batch 1
''',
        ),
        Replacement(
            old='''def build_purpose_fit_prompt(invitation) -> str:
''',
            new='''def build_purpose_fit_prompt(
    invitation,
    *,
    language_code: str = "en",
) -> str:
''',
        ),
        Replacement(
            old='''    shared_context = build_shared_ai_context(
        invitation
    )

    candidate = shared_context["candidate"]
''',
            new='''    language_code = normalize_ai_language(
        language_code
    )
    language_instruction = get_ai_language_instruction(
        language_code
    )
    output_examples = get_purpose_fit_output_examples(
        language_code
    )

    shared_context = build_shared_ai_context(
        invitation
    )

    candidate = shared_context["candidate"]
''',
        ),
        Replacement(
            old='''LANGUAGE AND TONE
- Write in professional, clear English.
- Use cautious formulations such as:
  "may indicate",
  "suggests",
  "appears to",
  "could mean",
  "may be relevant",
  "could be useful to explore".
- Avoid repeatedly writing "the candidate is".
''',
            new='''LANGUAGE AND TONE
{language_instruction}
- Avoid repeatedly writing "the candidate is".
''',
        ),
        Replacement(
            old='''{{"type":"meta","title":"AI Overview","recommendation":"Insufficient context","confidence":"Low"}}
''',
            new='''{{"type":"meta","title":"{output_examples["title"]}","recommendation":"Insufficient context","confidence":"Low"}}
''',
        ),
        Replacement(
            old='''{{"type":"summary_delta","text":"First part of the interpretation. "}}
{{"type":"summary_delta","text":"Next part of the interpretation. "}}
''',
            new='''{{"type":"summary_delta","text":"{output_examples["summary_1"]}"}}
{{"type":"summary_delta","text":"{output_examples["summary_2"]}"}}
''',
        ),
        Replacement(
            old='''{{"type":"key_alignment","items":["Supporting point one","Supporting point two","Supporting point three"]}}
''',
            new='''{{"type":"key_alignment","items":["{output_examples["support_1"]}","{output_examples["support_2"]}","{output_examples["support_3"]}"]}}
''',
        ),
        Replacement(
            old='''{{"type":"areas_to_verify","items":["Consideration one","Consideration two","Consideration three"]}}
''',
            new='''{{"type":"areas_to_verify","items":["{output_examples["consider_1"]}","{output_examples["consider_2"]}","{output_examples["consider_3"]}"]}}
''',
        ),
        Replacement(
            old='''{{"type":"suggested_next_step","text":"One practical and purpose-relevant next step."}}
''',
            new='''{{"type":"suggested_next_step","text":"{output_examples["next_step"]}"}}
''',
        ),
        Replacement(
            old='''{{"type":"context_note","text":"Brief explanation of the assessment evidence and process context used."}}
''',
            new='''{{"type":"context_note","text":"{output_examples["context_note"]}"}}
''',
        ),
        Replacement(
            old='''def stream_candidate_purpose_fit(
    invitation,
) -> Iterable[dict[str, Any]]:
''',
            new='''def stream_candidate_purpose_fit(
    invitation,
    *,
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
''',
        ),
        Replacement(
            old='''    client = get_openai_client()

    prompt = build_purpose_fit_prompt(invitation)
''',
            new='''    language_code = normalize_ai_language(
        language_code
    )
    system_language_instruction = (
        get_ai_system_language_instruction(
            language_code
        )
    )

    client = get_openai_client()

    prompt = build_purpose_fit_prompt(
        invitation,
        language_code=language_code,
    )
''',
        ),
        Replacement(
            old='''                    "and follow the requested NDJSON streaming format exactly."
''',
            new='''                    "and follow the requested NDJSON streaming format exactly. "
                    f"{system_language_instruction}"
''',
        ),
        Replacement(
            old='''def save_candidate_purpose_fit(
    invitation,
    purpose_fit: dict[str, Any],
):
''',
            new='''def save_candidate_purpose_fit(
    invitation,
    purpose_fit: dict[str, Any],
    *,
    language_code: str = "en",
):
''',
        ),
        Replacement(
            old='''    invitation.ai_purpose_fit = purpose_fit
    invitation.ai_purpose_fit_status = "completed"
''',
            new='''    set_ai_content_language(
        invitation,
        "purpose_fit",
        language_code,
    )

    invitation.ai_purpose_fit = purpose_fit
    invitation.ai_purpose_fit_status = "completed"
''',
        ),
        Replacement(
            old='''        "ai_purpose_fit_purpose",
    ])
''',
            new='''        "ai_purpose_fit_purpose",
        "ai_content_languages",
    ])
''',
        ),
    ]

    for replacement in replacements:
        text = replace_exact(text, replacement, path=path)

    return text


def transform_views(text: str) -> str:
    path = "apps/processes/views.py"

    if "get_request_ai_language" in text:
        raise RuntimeError(f"{path}: batch appears to be applied already.")

    replacements = [
        Replacement(
            old='''from apps.core.ai.purpose_fit import (
    purpose_supports_fit,
    create_empty_purpose_fit,
    apply_purpose_fit_event,
    stream_candidate_purpose_fit,
    save_candidate_purpose_fit,
)
''',
            new='''from apps.core.ai.purpose_fit import (
    purpose_supports_fit,
    create_empty_purpose_fit,
    apply_purpose_fit_event,
    stream_candidate_purpose_fit,
    save_candidate_purpose_fit,
)
from apps.core.ai.language import (
    ai_content_language_matches,
    get_request_ai_language,
    mark_ai_content_outdated_if_language_changed,
)
''',
        ),
        Replacement(
            old='''        invitation = get_object_or_404(
            TestInvitation.objects.select_related("candidate"),
            process=process,
            candidate_id=candidate_id,
        )

        ctx = build_candidate_detail_context(
''',
            new='''        invitation = get_object_or_404(
            TestInvitation.objects.select_related("candidate"),
            process=process,
            candidate_id=candidate_id,
        )

        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="purpose_fit",
            result_field="ai_purpose_fit",
            status_field="ai_purpose_fit_status",
            language_code=get_request_ai_language(request),
        )

        ctx = build_candidate_detail_context(
''',
        ),
        Replacement(
            old='''    invitation = get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )

    print(
        f"[PURPOSE FIT] Invitation found: "
''',
            new='''    invitation = get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )

    language_code = get_request_ai_language(request)

    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="purpose_fit",
        result_field="ai_purpose_fit",
        status_field="ai_purpose_fit_status",
        language_code=language_code,
    )

    print(
        f"[PURPOSE FIT] Invitation found: "
''',
        ),
        Replacement(
            old='''    if should_return_saved_ai_result(
        invitation.ai_purpose_fit,
        invitation.ai_purpose_fit_status,
    ):
''',
            new='''    if (
        ai_content_language_matches(
            invitation,
            "purpose_fit",
            language_code,
        )
        and should_return_saved_ai_result(
            invitation.ai_purpose_fit,
            invitation.ai_purpose_fit_status,
        )
    ):
''',
        ),
        Replacement(
            old='''            for event in stream_candidate_purpose_fit(
                invitation
            ):
''',
            new='''            for event in stream_candidate_purpose_fit(
                invitation,
                language_code=language_code,
            ):
''',
        ),
        Replacement(
            old='''            save_candidate_purpose_fit(
                invitation,
                purpose_fit,
            )
''',
            new='''            save_candidate_purpose_fit(
                invitation,
                purpose_fit,
                language_code=language_code,
            )
''',
        ),
    ]

    for replacement in replacements:
        text = replace_exact(text, replacement, path=path)

    return text


def compile_source(source: str, path: Path) -> None:
    try:
        compile(source, str(path), "exec")
    except SyntaxError as error:
        raise RuntimeError(
            f"{path}: generated Python syntax is invalid: {error}"
        ) from error


def prepare_changes(root: Path):
    models_path = root / "apps/processes/models.py"
    views_path = root / "apps/processes/views.py"
    purpose_fit_path = root / "apps/core/ai/purpose_fit.py"
    language_path = root / "apps/core/ai/language.py"

    for path in (models_path, views_path, purpose_fit_path):
        if not path.exists():
            raise FileNotFoundError(f"Required file is missing: {path}")

    if language_path.exists():
        raise RuntimeError(
            f"{language_path}: file already exists. "
            "The batch will not overwrite it."
        )

    original_models = models_path.read_text(encoding="utf-8")
    original_views = views_path.read_text(encoding="utf-8")
    original_purpose_fit = purpose_fit_path.read_text(encoding="utf-8")

    updated_models = transform_models(original_models)
    updated_views = transform_views(original_views)
    updated_purpose_fit = transform_purpose_fit(original_purpose_fit)

    compile_source(updated_models, models_path)
    compile_source(updated_views, views_path)
    compile_source(updated_purpose_fit, purpose_fit_path)
    compile_source(LANGUAGE_FILE_CONTENT, language_path)

    return [
        (models_path, original_models, updated_models),
        (views_path, original_views, updated_views),
        (purpose_fit_path, original_purpose_fit, updated_purpose_fit),
        (language_path, None, LANGUAGE_FILE_CONTENT),
    ]


def apply_changes_atomically(changes) -> None:
    prepared = []

    for path, original, updated in changes:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp-ai-language")
        backup = None

        if original is not None:
            backup = path.with_suffix(path.suffix + ".bak-ai-language")
            if not backup.exists():
                shutil.copy2(path, backup)

        temporary.write_text(updated, encoding="utf-8")
        prepared.append((path, backup, temporary))

    replaced = []

    try:
        for path, backup, temporary in prepared:
            temporary.replace(path)
            replaced.append((path, backup))
    except Exception:
        for path, backup in reversed(replaced):
            if backup and backup.exists():
                shutil.copy2(backup, path)
            elif path.exists():
                path.unlink()
        raise
    finally:
        for _path, _backup, temporary in prepared:
            if temporary.exists():
                temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="Validate the batch without changing files.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply the validated batch.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root. Defaults to the current directory.",
    )

    args = parser.parse_args()
    root = Path(args.root).resolve()

    try:
        changes = prepare_changes(root)
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        print("No project files were changed.", file=sys.stderr)
        return 1

    print("Validated files:")
    for path, _original, _updated in changes:
        print(f"- {path.relative_to(root)}")

    if args.check:
        print(
            "\nSuccess: the AI Overview language batch "
            "validated without changing files."
        )
        return 0

    try:
        apply_changes_atomically(changes)
    except Exception as error:
        print(f"\nERROR while writing files: {error}", file=sys.stderr)
        print("Previously written files were restored.", file=sys.stderr)
        return 1

    print("\nSuccess: AI Overview language support was applied.")
    print("Backups for modified files end with .bak-ai-language")
    print("\nNext commands:")
    print("python manage.py makemigrations processes")
    print("python manage.py migrate")
    print("python manage.py check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
