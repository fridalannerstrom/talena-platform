#!/usr/bin/env python3
"""Apply bilingual Personality Results, Interpretation and Questions safely."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

MARKER = "Talena personality language batch 1"
APPROVED_CONTENT_GIT_SHA = "3e212e48b9ca7bde0751dd88250b88df9ed94391"


@dataclass(frozen=True)
class Change:
    path: Path
    original: str
    updated: str


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def replace_once(text: str, old: str, new: str, *, path: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{path}: expected 1 occurrence, found {count} for:\n{old[:320]}"
        )
    return text.replace(old, new, 1)


def function_block(text: str, name: str) -> tuple[int, int, str]:
    match = re.search(rf"(?m)^def {re.escape(name)}\(", text)
    if not match:
        raise RuntimeError(f"Could not find function {name}.")

    next_match = re.search(
        r"(?m)^(?:@[\w.]+(?:\([^\n]*\))?\n)*def [A-Za-z_]\w*\(",
        text[match.end():],
    )
    end = match.end() + next_match.start() if next_match else len(text)
    return match.start(), end, text[match.start():end]


def transform_function(text: str, name: str, fn) -> str:
    start, end, block = function_block(text, name)
    updated = fn(block)
    if updated == block:
        raise RuntimeError(f"No changes produced in {name}.")
    return text[:start] + updated + text[end:]


def compile_source(source: str, path: Path) -> None:
    try:
        compile(source, str(path), "exec")
    except SyntaxError as exc:
        raise RuntimeError(f"{path}: generated Python is invalid: {exc}") from exc


def replace_personality_profile_language_argument(
    text: str,
    *,
    function_name: str,
    path: str,
) -> str:
    """
    Replace only the language argument belonging to
    build_profile_from_resolved_report() inside the named context builder.

    This avoids relying on indentation and avoids touching the new
    language="sv" default argument in the function signature.
    """
    start, end, block = function_block(
        text,
        function_name,
    )

    call_name = "build_profile_from_resolved_report("
    call_index = block.find(call_name)

    if call_index < 0:
        raise RuntimeError(
            f"{path}: {function_name} does not contain "
            "build_profile_from_resolved_report()."
        )

    before_call = block[:call_index]
    call_and_after = block[call_index:]

    hardcoded_pattern = re.compile(
        r'(?m)^(?P<indent>[ \t]+)'
        r'language\s*=\s*["\']sv["\']\s*,[ \t]*$'
    )
    dynamic_pattern = re.compile(
        r'(?m)^[ \t]+language\s*=\s*language\s*,[ \t]*$'
    )

    hardcoded_matches = list(
        hardcoded_pattern.finditer(
            call_and_after
        )
    )
    dynamic_matches = list(
        dynamic_pattern.finditer(
            call_and_after
        )
    )

    if len(hardcoded_matches) == 1:
        call_and_after = hardcoded_pattern.sub(
            lambda match: (
                f'{match.group("indent")}'
                "language=language,"
            ),
            call_and_after,
            count=1,
        )
    elif (
        not hardcoded_matches
        and len(dynamic_matches) == 1
    ):
        pass
    else:
        raise RuntimeError(
            f"{path}: expected one personality profile language "
            f"argument in {function_name}; found "
            f"{len(hardcoded_matches)} hard-coded and "
            f"{len(dynamic_matches)} dynamic occurrence(s)."
        )

    updated_block = before_call + call_and_after
    return text[:start] + updated_block + text[end:]


LANGUAGE_EXTENSION = r'''

# Talena personality language batch 1
_AI_CONTENT_RESULT_FIELDS.update({
    "personality_interpretation": "ai_personality_interpretation",
    "personality_questions": "ai_personality_questions",
})


def get_saved_ai_content_language(
    owner: Any,
    content_key: str,
) -> str:
    """Read shared metadata, then fall back to _language in saved JSON."""
    languages = getattr(owner, "ai_content_languages", None)

    if isinstance(languages, dict):
        explicit = languages.get(content_key)
        if explicit:
            return normalize_ai_language(explicit)

    result_field = _AI_CONTENT_RESULT_FIELDS.get(content_key)
    if result_field:
        saved_result = getattr(owner, result_field, None)
        if isinstance(saved_result, dict):
            embedded = saved_result.get("_language")
            if embedded:
                return normalize_ai_language(embedded)

    return LEGACY_AI_LANGUAGE


def set_ai_content_language(
    owner: Any,
    content_key: str,
    language_code: str | None,
) -> dict[str, str]:
    """Store shared metadata only on models that provide the field."""
    if not hasattr(owner, "ai_content_languages"):
        return {}

    languages = getattr(owner, "ai_content_languages", None)
    if not isinstance(languages, dict):
        languages = {}

    updated = dict(languages)
    updated[content_key] = normalize_ai_language(language_code)
    owner.ai_content_languages = updated
    return updated
'''


INTERPRETATION_EXTENSION = r'''

# Talena personality language batch 1
from contextvars import ContextVar as _ContextVar
from .language import (
    get_ai_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)

_personality_interpretation_language = _ContextVar(
    "personality_interpretation_language",
    default="en",
)

_original_build_personality_interpretation_prompt = (
    build_personality_interpretation_prompt
)
_original_create_empty_personality_interpretation = (
    create_empty_personality_interpretation
)
_original_stream_personality_interpretation = (
    stream_personality_interpretation
)
_original_save_personality_interpretation = (
    save_personality_interpretation
)


def _personality_interpretation_examples(language_code: str) -> dict[str, str]:
    if normalize_ai_language(language_code) == "sv":
        return {
            "title": "Personlighetstolkning",
            "label": "AI-stödd tolkning",
            "first": "Första delen av tolkningen. ",
            "next": "Nästa del av tolkningen. ",
            "dynamics": (
                "En praktisk förklaring av hur viktiga "
                "personlighetspreferenser kan samverka."
            ),
            "support": [
                "Första potentiellt stödjande mönstret",
                "Andra potentiellt stödjande mönstret",
                "Tredje potentiellt stödjande mönstret",
            ],
            "explore": [
                "Första området att utforska",
                "Andra området att utforska",
                "Tredje området att utforska",
            ],
            "context": (
                "Kort förklaring av underlaget, kontexten "
                "och tolkningens begränsningar."
            ),
        }

    return {
        "title": "Personality interpretation",
        "label": "AI-supported interpretation",
    }


def build_personality_interpretation_prompt(
    owner,
    personality_results: list[dict[str, Any]],
    *,
    language_code: str | None = None,
) -> str:
    language_code = normalize_ai_language(
        language_code or _personality_interpretation_language.get()
    )
    prompt = _original_build_personality_interpretation_prompt(
        owner,
        personality_results,
    )
    prompt = prompt.replace(
        "- Write in professional, clear English.",
        get_ai_language_instruction(language_code),
        1,
    )

    if language_code == "sv":
        examples = _personality_interpretation_examples(language_code)
        replacements = {
            '"title":"Personality interpretation"': (
                f'"title":"{examples["title"]}"'
            ),
            '"label":"AI-supported interpretation"': (
                f'"label":"{examples["label"]}"'
            ),
            "First part of the interpretation. ": examples["first"],
            "Next part of the interpretation. ": examples["next"],
            (
                "A practical explanation of how important personality "
                "preferences may work together."
            ): examples["dynamics"],
            "Pattern one": examples["support"][0],
            "Pattern two": examples["support"][1],
            "Pattern three": examples["support"][2],
            "Area one": examples["explore"][0],
            "Area two": examples["explore"][1],
            "Area three": examples["explore"][2],
            (
                "Brief explanation of the evidence, context and limitations."
            ): examples["context"],
        }
        for old, new in replacements.items():
            prompt = prompt.replace(old, new)

    return prompt


def create_empty_personality_interpretation(
    owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
    result = _original_create_empty_personality_interpretation(owner)
    examples = _personality_interpretation_examples(language_code)
    result["title"] = examples["title"]
    result["label"] = examples["label"]
    return result


def stream_personality_interpretation(
    *,
    owner,
    personality_results: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
    language_code = normalize_ai_language(language_code)
    token = _personality_interpretation_language.set(language_code)
    try:
        yield from _original_stream_personality_interpretation(
            owner=owner,
            personality_results=personality_results,
        )
    finally:
        _personality_interpretation_language.reset(token)


def save_personality_interpretation(
    *,
    owner,
    interpretation: dict[str, Any],
    language_code: str = "en",
):
    language_code = normalize_ai_language(language_code)
    interpretation["_language"] = language_code
    set_ai_content_language(
        owner,
        "personality_interpretation",
        language_code,
    )
    _original_save_personality_interpretation(
        owner=owner,
        interpretation=interpretation,
    )
    if hasattr(owner, "ai_content_languages"):
        owner.save(update_fields=["ai_content_languages"])
'''


QUESTIONS_EXTENSION = r'''

# Talena personality language batch 1
from contextvars import ContextVar as _ContextVar
from .language import (
    get_ai_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)

_personality_questions_language = _ContextVar(
    "personality_questions_language",
    default="en",
)

_original_build_personality_questions_prompt = build_personality_questions_prompt
_original_build_personality_questions_repair_prompt = (
    _build_personality_questions_repair_prompt
)
_original_build_safe_personality_questions_event = (
    _build_safe_personality_questions_event
)
_original_create_empty_personality_questions = create_empty_personality_questions
_original_stream_personality_questions = stream_personality_questions
_original_save_personality_questions = save_personality_questions


def _question_examples(language_code: str) -> dict[str, str]:
    if normalize_ai_language(language_code) == "sv":
        return {
            "title": "Personlighetsfrågor",
            "label": "AI-stödda frågor",
            "reason": "Varför personlighetsdraget kan vara relevant att utforska",
            "q1": "Första frågan",
            "q2": "Andra frågan",
            "q3": "Tredje frågan",
            "why": "Varför frågan är relevant",
            "listen": "Vad du kan lyssna efter",
            "context": (
                "Kort förklaring av underlaget, kontexten "
                "och valet av personlighetsdrag."
            ),
        }
    return {
        "title": "Personality questions",
        "label": "AI-supported questions",
    }


def _localize_question_prompt(prompt: str, language_code: str) -> str:
    language_code = normalize_ai_language(language_code)
    prompt = prompt.replace(
        "- Write in professional, clear English.",
        get_ai_language_instruction(language_code),
        1,
    )

    if language_code != "sv":
        return prompt

    examples = _question_examples(language_code)
    replacements = {
        '"title":"Personality questions"': f'"title":"{examples["title"]}"',
        '"label":"AI-supported questions"': f'"label":"{examples["label"]}"',
        "Why this trait may be relevant": examples["reason"],
        "Question one": examples["q1"],
        "Question two": examples["q2"],
        "Question three": examples["q3"],
        "Why it matters": examples["why"],
        "What to listen for": examples["listen"],
        (
            "Brief explanation of the evidence, context and trait selection used."
        ): examples["context"],
    }
    for old, new in replacements.items():
        prompt = prompt.replace(old, new)

    return prompt


def build_personality_questions_prompt(
    invitation,
    personality_results: list[dict[str, Any]],
    *,
    language_code: str | None = None,
) -> str:
    language_code = normalize_ai_language(
        language_code or _personality_questions_language.get()
    )
    prompt = _original_build_personality_questions_prompt(
        invitation,
        personality_results,
    )
    prompt = _localize_question_prompt(prompt, language_code)
    prompt = prompt.replace(
        "LANGUAGE AND TONE\n",
        (
            "LANGUAGE AND TONE\n"
            "- Keep trait names in the technical name and traits fields "
            "exactly as supplied.\n"
        ),
        1,
    )
    return prompt


def _build_personality_questions_repair_prompt(
    *,
    owner,
    personality_results: list[dict[str, Any]],
    selected_traits: list[str],
) -> str:
    language_code = normalize_ai_language(
        _personality_questions_language.get()
    )
    prompt = _original_build_personality_questions_repair_prompt(
        owner=owner,
        personality_results=personality_results,
        selected_traits=selected_traits,
    )
    language_rule = get_ai_language_instruction(language_code)
    prompt = (
        f"LANGUAGE REQUIREMENT\n{language_rule}\n"
        "Keep trait names in the technical traits field exactly as supplied.\n\n"
        + prompt
    )
    return _localize_question_prompt(prompt, language_code)


_SAFE_SWEDISH = {
    "Tell me about a situation where your usual way of approaching work was particularly effective. What did you do, and what was the outcome?": (
        "Berätta om en situation där ditt vanliga sätt att ta dig an arbetet "
        "var särskilt effektivt. Vad gjorde du och vad blev resultatet?"
    ),
    "This helps compare the assessment indication with a concrete example of workplace behaviour.": (
        "Detta hjälper till att jämföra testindikationen med ett konkret "
        "exempel på beteende i arbetet."
    ),
    "Specific actions, situational context and evidence of how the person used their natural preferences.": (
        "Konkreta handlingar, situationens förutsättningar och hur personen "
        "använde sina naturliga preferenser."
    ),
    "Describe a situation where you needed to adjust your normal approach. What made the adjustment necessary, and what did you do?": (
        "Beskriv en situation där du behövde anpassa ditt vanliga arbetssätt. "
        "Vad gjorde anpassningen nödvändig och hur agerade du?"
    ),
    "This explores how behavioural preferences may change across different situations.": (
        "Detta utforskar hur beteendepreferenser kan förändras mellan olika situationer."
    ),
    "Self-awareness, deliberate adaptation and the effect of the surrounding context.": (
        "Självinsikt, medveten anpassning och hur omgivande förutsättningar påverkade agerandet."
    ),
    "Tell me about a challenging situation involving other people. How did you decide what approach to take?": (
        "Berätta om en utmanande situation som involverade andra människor. "
        "Hur avgjorde du vilket tillvägagångssätt du skulle använda?"
    ),
    "This provides evidence about how preferences may influence collaboration and judgement.": (
        "Detta ger underlag om hur preferenser kan påverka samarbete och bedömningar."
    ),
    "Perspective-taking, communication choices and the reasoning behind the person's actions.": (
        "Perspektivtagande, kommunikationsval och resonemanget bakom personens agerande."
    ),
    "What feedback have you received about your way of working, and what did you learn from it?": (
        "Vilken återkoppling har du fått om ditt sätt att arbeta och vad lärde du dig av den?"
    ),
    "This adds external behavioural evidence that may confirm or add nuance to the personality profile.": (
        "Detta tillför extern beteendeevidens som kan bekräfta eller nyansera personlighetsprofilen."
    ),
    "Concrete feedback, reflection and changes made in response.": (
        "Konkret återkoppling, reflektion och förändringar som genomförts utifrån återkopplingen."
    ),
    "Describe a situation where you had to balance different priorities or expectations. How did you approach it?": (
        "Beskriv en situation där du behövde balansera olika prioriteringar "
        "eller förväntningar. Hur tog du dig an situationen?"
    ),
    "This explores how several behavioural preferences may interact in a practical situation.": (
        "Detta utforskar hur flera beteendepreferenser kan samverka i en praktisk situation."
    ),
    "Prioritisation, trade-offs and awareness of how the situation affected the chosen approach.": (
        "Prioriteringar, avvägningar och medvetenhet om hur situationen påverkade det valda arbetssättet."
    ),
    "Tell me about a situation that required you to work outside your preferred style. What was difficult, and what helped?": (
        "Berätta om en situation där du behövde arbeta utanför ditt föredragna "
        "arbetssätt. Vad var utmanande och vad hjälpte dig?"
    ),
    "This explores flexibility and the conditions that support effective behaviour.": (
        "Detta utforskar flexibilitet och vilka förutsättningar som stödjer ett effektivt agerande."
    ),
    "Adaptation, support needs, learning and awareness of personal preferences.": (
        "Anpassning, stödbehov, lärande och medvetenhet om personliga preferenser."
    ),
}


def _translate_safe_value(value):
    if isinstance(value, str):
        return _SAFE_SWEDISH.get(value, value)
    if isinstance(value, list):
        return [_translate_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _translate_safe_value(item) for key, item in value.items()}
    return value


def _build_safe_personality_questions_event(
    *,
    selected_traits: list[str],
    personality_results: list[dict[str, Any]],
) -> dict[str, Any]:
    result = _original_build_safe_personality_questions_event(
        selected_traits=selected_traits,
        personality_results=personality_results,
    )
    if normalize_ai_language(_personality_questions_language.get()) == "sv":
        return _translate_safe_value(result)
    return result


def create_empty_personality_questions(
    owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
    result = _original_create_empty_personality_questions(owner)
    examples = _question_examples(language_code)
    result["title"] = examples["title"]
    result["label"] = examples["label"]
    return result


def stream_personality_questions(
    *,
    owner,
    personality_results: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
    language_code = normalize_ai_language(language_code)
    token = _personality_questions_language.set(language_code)
    try:
        yield from _original_stream_personality_questions(
            owner=owner,
            personality_results=personality_results,
        )
    finally:
        _personality_questions_language.reset(token)


def save_personality_questions(
    *,
    owner,
    result: dict[str, Any],
    language_code: str = "en",
):
    language_code = normalize_ai_language(language_code)
    result["_language"] = language_code
    set_ai_content_language(
        owner,
        "personality_questions",
        language_code,
    )
    _original_save_personality_questions(
        owner=owner,
        result=result,
    )
    if hasattr(owner, "ai_content_languages"):
        owner.save(update_fields=["ai_content_languages"])
'''


def transform_language(text: str) -> str:
    path = "apps/core/ai/language.py"
    if MARKER in text:
        raise RuntimeError(f"{path}: batch already applied.")
    if "_AI_CONTENT_RESULT_FIELDS" not in text:
        # The first batch did not define the mapping. Create it before the extension.
        prefix = "\n\n_AI_CONTENT_RESULT_FIELDS = {\n    \"purpose_fit\": \"ai_purpose_fit\",\n}\n"
        text = text.rstrip() + prefix
    return text.rstrip() + LANGUAGE_EXTENSION + "\n"


def transform_interpretation(text: str) -> str:
    path = "apps/core/ai/personality_interpretation.py"
    if MARKER in text:
        raise RuntimeError(f"{path}: batch already applied.")
    return text.rstrip() + INTERPRETATION_EXTENSION + "\n"


def transform_questions(text: str) -> str:
    path = "apps/core/ai/personality_questions.py"
    if MARKER in text:
        raise RuntimeError(f"{path}: batch already applied.")
    return text.rstrip() + QUESTIONS_EXTENSION + "\n"


def transform_candidate_detail(block: str) -> str:
    path = "apps/processes/views.py"
    block = replace_once(
        block,
        '    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"\n',
        '    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"\n'
        '    language_code = get_request_ai_language(request)\n',
        path=path,
    )
    block = replace_once(
        block,
        '''        ctx = build_historical_candidate_detail_context(
            process=process,
            historical_candidate=historical_candidate,
        )
''',
        '''        mark_ai_content_outdated_if_language_changed(
            historical_candidate,
            content_key="personality_interpretation",
            result_field="ai_personality_interpretation",
            status_field="ai_personality_interpretation_status",
            language_code=language_code,
        )

        ctx = build_historical_candidate_detail_context(
            process=process,
            historical_candidate=historical_candidate,
            language=language_code,
        )
''',
        path=path,
    )
    block = replace_once(
        block,
        '''        ctx = build_candidate_detail_context(
            process=process,
            invitation=invitation,
        )
''',
        '''        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="personality_interpretation",
            result_field="ai_personality_interpretation",
            status_field="ai_personality_interpretation_status",
            language_code=language_code,
        )
        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="personality_questions",
            result_field="ai_personality_questions",
            status_field="ai_personality_questions_status",
            language_code=language_code,
        )

        ctx = build_candidate_detail_context(
            process=process,
            invitation=invitation,
            language=language_code,
        )
''',
        path=path,
    )
    return block


def transform_interpretation_stream(block: str) -> str:
    path = "apps/processes/views.py"
    block = replace_once(
        block,
        '''    # ---------------------------------------------------------
    # BUILD PERSONALITY EVIDENCE
''',
        '''    language_code = get_request_ai_language(request)
    mark_ai_content_outdated_if_language_changed(
        owner,
        content_key="personality_interpretation",
        result_field="ai_personality_interpretation",
        status_field="ai_personality_interpretation_status",
        language_code=language_code,
    )

    # ---------------------------------------------------------
    # BUILD PERSONALITY EVIDENCE
''',
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
            owner,
            "personality_interpretation",
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
        '''            create_empty_personality_interpretation(
                owner
            )
''',
        '''            create_empty_personality_interpretation(
                owner,
                language_code=language_code,
            )
''',
        path=path,
    )
    block = replace_once(
        block,
        '''                personality_results=personality_results,
            ):
''',
        '''                personality_results=personality_results,
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


def transform_questions_stream(block: str) -> str:
    path = "apps/processes/views.py"
    block = replace_once(
        block,
        '''    if invitation.status != "completed":
''',
        '''    language_code = get_request_ai_language(request)
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="personality_questions",
        result_field="ai_personality_questions",
        status_field="ai_personality_questions_status",
        language_code=language_code,
    )

    if invitation.status != "completed":
''',
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
            "personality_questions",
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
        '''        result = create_empty_personality_questions(
            invitation
        )
''',
        '''        result = create_empty_personality_questions(
            invitation,
            language_code=language_code,
        )
''',
        path=path,
    )
    block = replace_once(
        block,
        '''                personality_results=personality_results,
            ):
''',
        '''                personality_results=personality_results,
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


def transform_views(text: str) -> str:
    path = "apps/processes/views.py"
    if MARKER in text:
        raise RuntimeError(f"{path}: batch already applied.")
    if "get_request_ai_language" not in text:
        raise RuntimeError(f"{path}: apply the AI Overview language batch first.")

    # Add the marker without altering the existing imports from the first batch.
    anchor = "from apps.core.ai.language import ("
    index = text.find(anchor)
    if index < 0:
        raise RuntimeError(f"{path}: language import not found.")
    closing = text.find("\n)\n", index)
    if closing < 0:
        raise RuntimeError(f"{path}: language import closing line not found.")
    closing += len("\n)\n")
    text = text[:closing] + f"\n# {MARKER}\n" + text[closing:]

    text = replace_once(
        text,
        "def build_candidate_detail_context(process, invitation):\n",
        '''def build_candidate_detail_context(
    process,
    invitation,
    language="sv",
):
''',
        path=path,
    )
    text = replace_once(
        text,
        '''def build_historical_candidate_detail_context(
    process,
    historical_candidate,
):
''',
        '''def build_historical_candidate_detail_context(
    process,
    historical_candidate,
    language="sv",
):
''',
        path=path,
    )

    text = replace_personality_profile_language_argument(
        text,
        function_name="build_candidate_detail_context",
        path=path,
    )
    text = replace_personality_profile_language_argument(
        text,
        function_name=(
            "build_historical_candidate_detail_context"
        ),
        path=path,
    )

    text = transform_function(text, "process_candidate_detail", transform_candidate_detail)
    text = transform_function(
        text,
        "process_candidate_personality_interpretation_stream",
        transform_interpretation_stream,
    )
    text = transform_function(
        text,
        "process_candidate_personality_questions_stream",
        transform_questions_stream,
    )
    return text


def prepare(root: Path) -> list[Change]:
    content_path = root / "apps/reports/libraries/personality/content.py"
    paths = {
        "language": root / "apps/core/ai/language.py",
        "interpretation": root / "apps/core/ai/personality_interpretation.py",
        "questions": root / "apps/core/ai/personality_questions.py",
        "views": root / "apps/processes/views.py",
    }

    for path in (content_path, *paths.values()):
        if not path.exists():
            raise FileNotFoundError(f"Required file is missing: {path}")

    protected = content_path.read_text(encoding="utf-8")
    found_sha = git_blob_sha(protected)
    if found_sha != APPROVED_CONTENT_GIT_SHA:
        raise RuntimeError(
            "The approved Swedish personality content differs from the protected "
            "GitHub version. The batch stopped before changing anything.\n"
            f"Expected: {APPROVED_CONTENT_GIT_SHA}\nFound: {found_sha}"
        )

    originals = {key: path.read_text(encoding="utf-8") for key, path in paths.items()}
    updated = {
        "language": transform_language(originals["language"]),
        "interpretation": transform_interpretation(originals["interpretation"]),
        "questions": transform_questions(originals["questions"]),
        "views": transform_views(originals["views"]),
    }

    for key, source in updated.items():
        compile_source(source, paths[key])

    if git_blob_sha(content_path.read_text(encoding="utf-8")) != APPROVED_CONTENT_GIT_SHA:
        raise RuntimeError("Protected personality content changed during validation.")

    return [
        Change(paths[key], originals[key], updated[key])
        for key in ("language", "interpretation", "questions", "views")
    ]


def apply_atomically(changes: list[Change], protected_path: Path) -> None:
    protected_before = git_blob_sha(protected_path.read_text(encoding="utf-8"))
    prepared = []

    for change in changes:
        backup = change.path.with_suffix(change.path.suffix + ".bak-personality-language")
        temp = change.path.with_suffix(change.path.suffix + ".tmp-personality-language")
        if not backup.exists():
            shutil.copy2(change.path, backup)
        temp.write_text(change.updated, encoding="utf-8")
        prepared.append((change.path, backup, temp))

    replaced = []
    try:
        for path, backup, temp in prepared:
            temp.replace(path)
            replaced.append((path, backup))
        protected_after = git_blob_sha(protected_path.read_text(encoding="utf-8"))
        if protected_after != protected_before:
            raise RuntimeError("Protected approved personality wording changed.")
    except Exception:
        for path, backup in reversed(replaced):
            shutil.copy2(backup, path)
        raise
    finally:
        for _path, _backup, temp in prepared:
            if temp.exists():
                temp.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    protected_path = root / "apps/reports/libraries/personality/content.py"

    try:
        changes = prepare(root)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print("No project files were changed.", file=sys.stderr)
        return 1

    print("Validated files:")
    for change in changes:
        print(f"- {change.path.relative_to(root)}")
    print("- apps/reports/libraries/personality/content.py (protected and unchanged)")

    if args.check:
        print("\nSuccess: Personality language support validated.")
        print("No project files were changed.")
        return 0

    try:
        apply_atomically(changes, protected_path)
    except Exception as exc:
        print(f"\nERROR while writing files: {exc}", file=sys.stderr)
        print("Written files were restored from backups.", file=sys.stderr)
        return 1

    print("\nSuccess: Personality language support was applied.")
    print("The approved Swedish Personality Results wording was not modified.")
    print("Backups end with .bak-personality-language")
    print("\nNext commands:")
    print("python manage.py check")
    print("python manage.py runserver")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
