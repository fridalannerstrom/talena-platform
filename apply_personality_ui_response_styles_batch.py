#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

MARKER = "Talena personality UI and response styles language batch 1"
APPROVED_CONTENT_GIT_SHA = "3e212e48b9ca7bde0751dd88250b88df9ed94391"


@dataclass(frozen=True)
class Change:
    path: Path
    original: str | None
    updated: str


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def compile_python(source: str, path: Path) -> None:
    try:
        compile(source, str(path), "exec")
    except SyntaxError as exc:
        raise RuntimeError(f"{path}: generated Python is invalid: {exc}") from exc


def _flexible_pattern(source: str) -> re.Pattern[str]:
    """
    Match the same code or template text while allowing harmless
    differences in indentation, CRLF/LF line endings and line wrapping.
    """
    stripped = source.strip()

    tokens = re.findall(
        r'"(?:\\.|[^"\\])*"'
        r"|\'(?:\\.|[^\'\\])*\'"
        r"|[A-Za-zÀ-ÖØ-öø-ÿ0-9_]+"
        r"|[^\sA-Za-zÀ-ÖØ-öø-ÿ0-9_]",
        stripped,
    )

    if not tokens:
        raise RuntimeError(
            "Cannot create a flexible matcher for empty text."
        )

    body = r"\s*".join(
        re.escape(token)
        for token in tokens
    )

    prefix = (
        r"(?m)^[ \t]*"
        if source[:1].isspace()
        else ""
    )
    suffix = (
        r"[ \t]*(?:\r?\n)?"
        if source.endswith(("\n", "\r"))
        else ""
    )

    return re.compile(
        prefix + body + suffix
    )


def replace_once(text: str, old: str, new: str, *, path: str) -> str:
    exact_count = text.count(old)

    if exact_count == 1:
        return text.replace(old, new, 1)

    if exact_count > 1:
        raise RuntimeError(
            f"{path}: expected 1 occurrence, found {exact_count} for:\\n"
            f"{old[:320]}"
        )

    pattern = _flexible_pattern(old)
    matches = list(pattern.finditer(text))

    if len(matches) != 1:
        raise RuntimeError(
            f"{path}: expected 1 flexible occurrence, found "
            f"{len(matches)} for:\\n{old[:320]}"
        )

    return pattern.sub(
        lambda _match: new,
        text,
        count=1,
    )


def replace_required(text: str, old: str, new: str, *, path: str) -> str:
    exact_count = text.count(old)

    if exact_count:
        return text.replace(old, new)

    pattern = _flexible_pattern(old)
    matches = list(pattern.finditer(text))

    if not matches:
        raise RuntimeError(
            f"{path}: expected text was not found:\\n{old[:320]}"
        )

    return pattern.sub(
        lambda _match: new,
        text,
    )


def function_block(text: str, name: str) -> tuple[int, int, str]:
    match = re.search(rf"(?m)^def {re.escape(name)}\(", text)
    if not match:
        raise RuntimeError(f"Could not find function {name}.")
    start = match.start()
    next_match = re.search(r"(?m)^def [A-Za-z_]\w*\(", text[match.end():])
    end = match.end() + next_match.start() if next_match else len(text)
    return start, end, text[start:end]


def transform_function(text: str, name: str, transform) -> str:
    start, end, block = function_block(text, name)
    updated = transform(block)
    if updated == block:
        raise RuntimeError(f"No changes were produced in {name}.")
    return text[:start] + updated + text[end:]


def prepend_loads(text: str, load_line: str) -> str:
    if MARKER in text:
        raise RuntimeError("Template batch marker is already present.")
    return load_line + "\n{# " + MARKER + " #}\n" + text.lstrip("\n")


def translate_plain_lines(text: str, values: list[str]) -> str:
    for value in sorted(values, key=len, reverse=True):
        pattern = re.compile(
            rf"(?m)^(?P<indent>[ \t]*){re.escape(value)}[ \t]*$"
        )
        text = pattern.sub(
            lambda m: f'{m.group("indent")}{{% trans "{value}" %}}',
            text,
        )
    return text


def transform_language_module(text: str) -> str:
    path = "apps/core/ai/language.py"
    if '"response_style_guidance"' in text:
        raise RuntimeError(f"{path}: support already exists.")
    pattern = re.compile(r"(?s)(_AI_CONTENT_RESULT_FIELDS\s*=\s*\{.*?)(\n\})")
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f"{path}: _AI_CONTENT_RESULT_FIELDS was not found.")
    replacement = (
        match.group(1)
        + '\n    "response_style_guidance": (\n'
        + '        "ai_response_style_guidance"\n'
        + "    ),"
        + match.group(2)
    )
    return text[:match.start()] + replacement + text[match.end():]


def transform_response_style_guidance(text: str) -> str:
    path = "apps/core/ai/response_style_guidance.py"
    if MARKER in text:
        raise RuntimeError(f"{path}: batch already applied.")

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


# Talena personality UI and response styles language batch 1
def _get_response_style_output_examples(language_code: str) -> dict[str, str]:
    language_code = normalize_ai_language(language_code)
    if language_code == "sv":
        return {
            "title": "Så kan profilen tolkas",
            "label": "AI-stödd tolkning",
            "summary_1": "Första delen av tolkningen. ",
            "summary_2": "Nästa del av tolkningen. ",
            "how": "Vad som bör finnas i åtanke när personlighetsprofilen läses.",
            "approach": "Hur intervju- eller återkopplingssamtalet kan genomföras.",
            "question_1": "Första öppna frågan",
            "question_2": "Andra öppna frågan",
            "question_3": "Tredje öppna frågan",
            "combination": "Om ett känt kombinationsmönster är relevant och vad som kan utforskas.",
            "context": "Hur råden anpassades till syfte och eventuell processkontext.",
        }
    return {
        "title": "How to approach this profile",
        "label": "AI-supported interpretation",
        "summary_1": "First part of the interpretation. ",
        "summary_2": "Next part of the interpretation. ",
        "how": "What should be kept in mind when reading the personality traits.",
        "approach": "How to approach the interview or feedback conversation.",
        "question_1": "Question one",
        "question_2": "Question two",
        "question_3": "Question three",
        "combination": "Whether a known combination applies and what may be useful to explore.",
        "context": "Whether the advice was adapted to purpose or added context.",
    }

''',
        path=path,
    )

    text = replace_once(
        text,
        '''def build_response_style_guidance_prompt(
    *,
    guidance_owner,
    response_styles: list[dict[str, Any]],
) -> str:
''',
        '''def build_response_style_guidance_prompt(
    *,
    guidance_owner,
    response_styles: list[dict[str, Any]],
    language_code: str = "en",
) -> str:
''',
        path=path,
    )
    text = replace_once(
        text,
        '''    shared_context = build_shared_ai_context(
        guidance_owner
    )
''',
        '''    language_code = normalize_ai_language(language_code)
    language_instruction = get_ai_language_instruction(language_code)
    output_examples = _get_response_style_output_examples(language_code)

    shared_context = build_shared_ai_context(
        guidance_owner
    )
''',
        path=path,
    )
    text = replace_once(
        text,
        '- Write in clear, professional English.\n',
        '{language_instruction}\n',
        path=path,
    )

    examples = [
        (
            '{{"type":"meta","title":"How to approach this profile","label":"AI-supported interpretation"}}\n',
            '{{"type":"meta","title":"{output_examples["title"]}","label":"{output_examples["label"]}"}}\n',
        ),
        (
            '{{"type":"summary_delta","text":"First part of the interpretation. "}}\n{{"type":"summary_delta","text":"Next part of the interpretation. "}}\n',
            '{{"type":"summary_delta","text":"{output_examples["summary_1"]}"}}\n{{"type":"summary_delta","text":"{output_examples["summary_2"]}"}}\n',
        ),
        (
            '{{"type":"how_to_interpret","text":"One or two concise sentences explaining what should be kept in mind when reading the personality traits."}}\n',
            '{{"type":"how_to_interpret","text":"{output_examples["how"]}"}}\n',
        ),
        (
            '{{"type":"recommended_approach","text":"One or two concise sentences describing how to approach the interview or feedback conversation."}}\n',
            '{{"type":"recommended_approach","text":"{output_examples["approach"]}"}}\n',
        ),
        (
            '{{"type":"questions","items":["Question one","Question two","Question three"]}}\n',
            '{{"type":"questions","items":["{output_examples["question_1"]}","{output_examples["question_2"]}","{output_examples["question_3"]}"]}}\n',
        ),
        (
            '{{"type":"combination_note","text":"Explain whether a known combination pattern applies and what it may be useful to explore. If no known combination applies, provide a short neutral note."}}\n',
            '{{"type":"combination_note","text":"{output_examples["combination"]}"}}\n',
        ),
        (
            '{{"type":"context_note","text":"Briefly explain whether the advice was adapted to process purpose or added context."}}\n',
            '{{"type":"context_note","text":"{output_examples["context"]}"}}\n',
        ),
    ]
    for old, new in examples:
        text = replace_once(text, old, new, path=path)

    text = replace_once(
        text,
        '''def create_empty_response_style_guidance(
    guidance_owner,
) -> dict[str, Any]:
    return {
        "title": "How to approach this profile",
        "label": "AI-supported interpretation",
''',
        '''def create_empty_response_style_guidance(
    guidance_owner,
    *,
    language_code: str = "en",
) -> dict[str, Any]:
    output_examples = _get_response_style_output_examples(language_code)
    return {
        "title": output_examples["title"],
        "label": output_examples["label"],
''',
        path=path,
    )
    text = replace_once(
        text,
        '''def stream_response_style_guidance(
    *,
    guidance_owner,
    response_styles: list[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
''',
        '''def stream_response_style_guidance(
    *,
    guidance_owner,
    response_styles: list[dict[str, Any]],
    language_code: str = "en",
) -> Iterable[dict[str, Any]]:
''',
        path=path,
    )
    text = replace_once(
        text,
        '''    prompt = build_response_style_guidance_prompt(
        guidance_owner=guidance_owner,
        response_styles=response_styles,
    )

    client = get_openai_client()
''',
        '''    language_code = normalize_ai_language(language_code)
    system_language_instruction = get_ai_system_language_instruction(language_code)
    prompt = build_response_style_guidance_prompt(
        guidance_owner=guidance_owner,
        response_styles=response_styles,
        language_code=language_code,
    )

    client = get_openai_client()
''',
        path=path,
    )
    text = replace_once(
        text,
        '''                    "NDJSON format exactly and do not make unsupported "
                    "claims."
''',
        '''                    "NDJSON format exactly and do not make unsupported "
                    "claims. "
                    f"{system_language_instruction}"
''',
        path=path,
    )
    text = replace_once(
        text,
        '''def save_response_style_guidance(
    *,
    guidance_owner,
    guidance: dict[str, Any],
):
''',
        '''def save_response_style_guidance(
    *,
    guidance_owner,
    guidance: dict[str, Any],
    language_code: str = "en",
):
''',
        path=path,
    )
    text = replace_once(
        text,
        '    guidance["summary"] = (\n',
        '''    language_code = normalize_ai_language(language_code)
    guidance["_language"] = language_code
    set_ai_content_language(
        guidance_owner,
        "response_style_guidance",
        language_code,
    )

    guidance["summary"] = (
''',
        path=path,
    )
    text = replace_once(
        text,
        '''    guidance_owner.save(update_fields=[
        "ai_response_style_guidance",
        "ai_response_style_guidance_status",
        "ai_response_style_guidance_generated_at",
        "ai_response_style_guidance_purpose",
    ])
''',
        '''    update_fields = [
        "ai_response_style_guidance",
        "ai_response_style_guidance_status",
        "ai_response_style_guidance_generated_at",
        "ai_response_style_guidance_purpose",
    ]
    update_fields.extend(get_ai_language_update_fields(guidance_owner))
    guidance_owner.save(update_fields=update_fields)
''',
        path=path,
    )
    return text


def transform_views(text: str) -> str:
    path = "apps/processes/views.py"
    if MARKER in text:
        raise RuntimeError(f"{path}: batch already applied.")
    if "get_request_ai_language" not in text:
        raise RuntimeError(f"{path}: earlier AI language batches are missing.")

    text = replace_once(
        text,
        '''from apps.reports.libraries.personality.builder import (
    build_profile_from_resolved_report,
)
''',
        '''from apps.reports.libraries.personality.builder import (
    build_profile_from_resolved_report,
)
from apps.reports.libraries.personality.response_styles import (
    build_response_style_results as build_localized_response_style_results,
)

# Talena personality UI and response styles language batch 1
''',
        path=path,
    )

    def replace_builder(_block: str) -> str:
        return '''def build_response_style_results(
    personality_competencies,
):
    return build_localized_response_style_results(
        personality_competencies
    )


'''

    text = transform_function(text, "build_response_style_results", replace_builder)

    def candidate_detail(block: str) -> str:
        anchor = '''        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="personality_interpretation",
'''
        if anchor not in block:
            raise RuntimeError(
                f"{path}: personality language anchor was not found in process_candidate_detail."
            )
        addition = '''        mark_ai_content_outdated_if_language_changed(
            invitation,
            content_key="response_style_guidance",
            result_field="ai_response_style_guidance",
            status_field="ai_response_style_guidance_status",
            language_code=language_code,
        )
'''
        return block.replace(anchor, addition + anchor, 1)

    text = transform_function(text, "process_candidate_detail", candidate_detail)

    def guidance_stream(block: str) -> str:
        marker = '''    # ---------------------------------------------------------
    # BUILD RESPONSE-STYLE RESULTS
'''
        if marker not in block:
            raise RuntimeError(f"{path}: response-style build section was not found.")
        language_block = '''    language_code = get_request_ai_language(request)
    mark_ai_content_outdated_if_language_changed(
        guidance_owner,
        content_key="response_style_guidance",
        result_field="ai_response_style_guidance",
        status_field="ai_response_style_guidance_status",
        language_code=language_code,
    )

'''
        block = block.replace(marker, language_block + marker, 1)
        block = replace_once(
            block,
            '''    if (
        saved_guidance
        and current_status == "completed"
    ):
''',
            '''    if (
        saved_guidance
        and current_status == "completed"
        and ai_content_language_matches(
            guidance_owner,
            "response_style_guidance",
            language_code,
        )
    ):
''',
            path=path,
        )
        block = replace_once(
            block,
            '''            create_empty_response_style_guidance(
                guidance_owner
            )
''',
            '''            create_empty_response_style_guidance(
                guidance_owner,
                language_code=language_code,
            )
''',
            path=path,
        )
        block = replace_once(
            block,
            '''                response_styles=available_response_styles,
            ):
''',
            '''                response_styles=available_response_styles,
                language_code=language_code,
            ):
''',
            path=path,
        )
        block = replace_once(
            block,
            '''                guidance=guidance,
            )
''',
            '''                guidance=guidance,
                language_code=language_code,
            )
''',
            path=path,
        )
        return block

    return transform_function(
        text,
        "process_candidate_response_style_guidance_stream",
        guidance_stream,
    )


def transform_template(path: str, text: str) -> str:
    if path.endswith("_results.html"):
        text = prepend_loads(text, "{% load i18n %}")
        pairs = [
            ("             Response styles\n", '             {% trans "Response styles" %}\n'),
            ("                   Questionnaire response pattern\n", '                   {% trans "Questionnaire response pattern" %}\n'),
            ("                   Not available\n", '                   {% trans "Not available" %}\n'),
            ("       ✨ AI-generated insight\n", '       ✨ {% trans "AI-generated insight" %}\n'),
            ("             What does this mean for {{ candidate.first_name }}?\n", '             {% blocktrans with candidate_name=candidate.first_name %}What does this mean for {{ candidate_name }}?{% endblocktrans %}\n'),
            ("             Analysing the response pattern and preparing practical guidance...\n", '             {% trans "Analysing the response pattern and preparing practical guidance…" %}\n'),
            ("             The interpretation could not be generated.\n", '             {% trans "The interpretation could not be generated." %}\n'),
            ("             Try again\n", '             {% trans "Try again" %}\n'),
            ("       Keep in mind when reading the profile\n", '       {% trans "Keep in mind when reading the profile" %}\n'),
            ("       Practical approach\n", '       {% trans "Practical approach" %}\n'),
            ("       Questions to explore\n", '       {% trans "Questions to explore" %}\n'),
            ("             Personality profile\n", '             {% trans "Personality profile" %}\n'),
            ("     <span>Trait Profile</span>\n", '     <span>{% trans "Trait Profile" %}</span>\n'),
            ("     <span>Trait &amp; Indicator Profile</span>\n", '     <span>{% trans "Trait & Indicator Profile" %}</span>\n'),
            ("   <span>Trait Descriptions</span>\n", '   <span>{% trans "Trait Descriptions" %}</span>\n'),
            ("         Description is not yet available.\n", '         {% trans "Description is not yet available." %}\n'),
            ("                   Description is not yet available.\n", '                   {% trans "Description is not yet available." %}\n'),
        ]
        for old, new in pairs:
            text = replace_required(text, old, new, path=path)
        text = replace_once(
            text,
            '''             These indicators describe how {{ candidate.first_name }} used the
             questionnaire response scale. They provide context for interpreting
             the personality profile and are not personality traits themselves.
''',
            '''             {% blocktrans with candidate_name=candidate.first_name %}These indicators describe how {{ candidate_name }} used the questionnaire response scale. They provide context for interpreting the personality profile and are not personality traits themselves.{% endblocktrans %}
''',
            path=path,
        )
        text = replace_once(
            text,
            '''         Response-style indicators should be used as interpretive context rather
         than as measures of ability, suitability or honesty.
''',
            '''         {% blocktrans %}Response-style indicators should be used as interpretive context rather than as measures of ability, suitability or honesty.{% endblocktrans %}
''',
            path=path,
        )
        text = replace_once(
            text,
            '''   Explore the candidate’s overall personality traits and the
   detailed indicators that contribute to each result.
''',
            '''   {% blocktrans %}Explore the candidate’s overall personality traits and the detailed indicators that contribute to each result.{% endblocktrans %}
''',
            path=path,
        )
        text = replace_once(
            text,
            "       How this trait may show up for {{ candidate.first_name }}\n",
            '       {% blocktrans with candidate_name=candidate.first_name %}How this trait may show up for {{ candidate_name }}{% endblocktrans %}\n',
            path=path,
        )
        return translate_plain_lines(
            text,
            ["Left score", "Right score", "Left Score", "Right Score", "Left", "Typical", "Average", "Right"],
        )

    if path.endswith("_interpretation.html"):
        text = prepend_loads(
            text,
            '{% load i18n %}\n{% trans "Personality interpretation" as personality_interpretation_fallback %}',
        )
        pairs = [
            ("       ✨ AI-generated insight\n", '       ✨ {% trans "AI-generated insight" %}\n'),
            ('             {{ personality_interpretation.title|default:"Personality interpretation" }}\n', '             {{ personality_interpretation.title|default:personality_interpretation_fallback }}\n'),
            ("             Needs update\n", '             {% trans "Needs update" %}\n'),
            ("             Interpreting the personality profile...\n", '             {% trans "Interpreting the personality profile…" %}\n'),
            ("         The personality interpretation could not be generated.\n", '         {% trans "The personality interpretation could not be generated." %}\n'),
            ("             Overall personality interpretation\n", '             {% trans "Overall personality interpretation" %}\n'),
            ("                 Combined trait dynamics\n", '                 {% trans "Combined trait dynamics" %}\n'),
            ("         Potentially supportive patterns\n", '         {% trans "Potentially supportive patterns" %}\n'),
            ("         What to explore or validate\n", '         {% trans "What to explore or validate" %}\n'),
            ('             title="Generate a new personality interpretation"\n', '             title="{% trans \'Generate a new personality interpretation\' %}"\n'),
            ('             aria-label="Generate a new personality interpretation"\n', '             aria-label="{% trans \'Generate a new personality interpretation\' %}"\n'),
        ]
        for old, new in pairs:
            text = replace_once(text, old, new, path=path)

        # "Personality questions" appears twice in this template:
        # once in the page section and once in the trait-selection modal.
        # Translate both visible lines while preserving their indentation.
        text = translate_plain_lines(
            text,
            ["Personality questions"],
        )

        text = replace_once(
            text,
            '''             A combined interpretation of the personality profile in
             relation to the selected purpose and available process context.
''',
            '''             {% blocktrans %}A combined interpretation of the personality profile in relation to the selected purpose and available process context.{% endblocktrans %}
''',
            path=path,
        )
        return text

    if path.endswith("_questions.html"):
        text = prepend_loads(text, "{% load i18n personality_i18n %}")
        pairs = [
            ("             ✨ AI-supported questions\n", '             ✨ {% trans "AI-supported questions" %}\n'),
            ("  Needs update\n", '  {% trans "Needs update" %}\n'),
            ("             Selecting relevant traits and creating questions...\n", '             {% trans "Selecting relevant traits and creating questions…" %}\n'),
            ("        The personality questions could not be generated.\n", '        {% trans "The personality questions could not be generated." %}\n'),
            ("                Traits used for these questions\n", '                {% trans "Traits used for these questions" %}\n'),
            ("              Change traits\n", '              {% trans "Change traits" %}\n'),
            ("            Questions to explore\n", '            {% trans "Questions to explore" %}\n'),
            ("              Why this matters\n", '              {% trans "Why this matters" %}\n'),
            ("              What to listen for\n", '              {% trans "What to listen for" %}\n'),
            ("            How Talena created these questions\n", '            {% trans "How Talena created these questions" %}\n'),
            ("          Select traits to explore\n", '          {% trans "Select traits to explore" %}\n'),
            ("        Select up to 6 traits\n", '        {% trans "Select up to 6 traits" %}\n'),
            ("        0 selected\n", '        {% trans "0 selected" %}\n'),
            ("  Cancel\n", '  {% trans "Cancel" %}\n'),
            ("  Save and generate\n", '  {% trans "Save and generate" %}\n'),
        ]
        for old, new in pairs:
            text = replace_once(text, old, new, path=path)
        text = replace_once(
            text,
            '''             Explore selected personality traits through practical,
             purpose-aware questions.
''',
            '''             {% blocktrans %}Explore selected personality traits through practical, purpose-aware questions.{% endblocktrans %}
''',
            path=path,
        )
        text = replace_once(
            text,
            '''                    Talena generated the questions below using these personality traits,
    the process purpose and any available context. Change the selection
    to shape the next set of questions.
''',
            '''                    {% blocktrans %}Talena generated the questions below using these personality traits, the process purpose and any available context. Change the selection to shape the next set of questions.{% endblocktrans %}
''',
            path=path,
        )
        count = text.count("{{ trait }}")
        if count != 2:
            raise RuntimeError(f"{path}: expected 2 trait displays, found {count}.")
        return text.replace("{{ trait }}", "{{ trait|personality_label }}")

    if path.endswith("_trait_descriptions.html"):
        text = prepend_loads(text, "{% load i18n %}")
        return replace_once(
            text,
            '''      Personality descriptions summarise likely behavioural preferences.
      They should be interpreted alongside the full profile, response-style
      indicators and other available assessment information.
''',
            '''      {% blocktrans %}Personality descriptions summarise likely behavioural preferences. They should be interpreted alongside the full profile, response-style indicators and other available assessment information.{% endblocktrans %}
''',
            path=path,
        )

    raise RuntimeError(f"Unsupported template: {path}")


def prepare_changes(root: Path) -> list[Change]:
    script_dir = Path(__file__).resolve().parent
    payload = script_dir / "payload"

    protected = root / "apps/reports/libraries/personality/content.py"
    language = root / "apps/core/ai/language.py"
    guidance = root / "apps/core/ai/response_style_guidance.py"
    views = root / "apps/processes/views.py"
    response_styles = root / "apps/reports/libraries/personality/response_styles.py"
    filter_file = root / "apps/processes/templatetags/personality_i18n.py"
    init_file = root / "apps/processes/templatetags/__init__.py"

    templates = [
        root / "templates/customer/processes/partials/candidate_insights/personality/_results.html",
        root / "templates/customer/processes/partials/candidate_insights/personality/_interpretation.html",
        root / "templates/customer/processes/partials/candidate_insights/personality/_questions.html",
        root / "templates/customer/processes/partials/candidate_insights/personality/_trait_descriptions.html",
    ]

    payload_response_styles = payload / "apps/reports/libraries/personality/response_styles.py"
    payload_filter = payload / "apps/processes/templatetags/personality_i18n.py"

    required = [protected, language, guidance, views, payload_response_styles, payload_filter, *templates]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Required file is missing: {path}")

    if git_blob_sha(protected.read_text(encoding="utf-8")) != APPROVED_CONTENT_GIT_SHA:
        raise RuntimeError("The approved Swedish personality source differs from the protected GitHub version.")

    if response_styles.exists() or filter_file.exists():
        raise RuntimeError("One of the new batch files already exists.")

    originals = {
        language: language.read_text(encoding="utf-8"),
        guidance: guidance.read_text(encoding="utf-8"),
        views: views.read_text(encoding="utf-8"),
    }
    for path in templates:
        originals[path] = path.read_text(encoding="utf-8")

    updated = {
        language: transform_language_module(originals[language]),
        guidance: transform_response_style_guidance(originals[guidance]),
        views: transform_views(originals[views]),
        response_styles: payload_response_styles.read_text(encoding="utf-8"),
        filter_file: payload_filter.read_text(encoding="utf-8"),
    }
    for path in templates:
        updated[path] = transform_template(str(path.relative_to(root)), originals[path])

    for path in [language, guidance, views, response_styles, filter_file]:
        compile_python(updated[path], path)

    changes = [Change(path, originals.get(path), text) for path, text in updated.items()]
    if not init_file.exists():
        changes.append(Change(init_file, None, ""))
    return changes


def apply_changes(changes: list[Change]) -> None:
    prepared = []
    for change in changes:
        change.path.parent.mkdir(parents=True, exist_ok=True)
        backup = change.path.with_suffix(change.path.suffix + ".bak-personality-ui-language")
        temporary = change.path.with_suffix(change.path.suffix + ".tmp-personality-ui-language")
        if change.original is not None and not backup.exists():
            shutil.copy2(change.path, backup)
        temporary.write_text(change.updated, encoding="utf-8")
        prepared.append((change, backup, temporary))

    written = []
    try:
        for change, backup, temporary in prepared:
            temporary.replace(change.path)
            written.append((change, backup))
    except Exception:
        for change, backup in reversed(written):
            if change.original is None:
                if change.path.exists():
                    change.path.unlink()
            elif backup.exists():
                shutil.copy2(backup, change.path)
        raise
    finally:
        for _change, _backup, temporary in prepared:
            if temporary.exists():
                temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    try:
        changes = prepare_changes(root)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print("No project files were changed.", file=sys.stderr)
        return 1

    print("Validated files:")
    for change in changes:
        print(f"- {change.path.relative_to(root)}")
    print("- apps/reports/libraries/personality/content.py (protected and unchanged)")

    if args.check:
        print("\nSuccess: Personality UI and Response Styles language support validated.")
        print("No project files were changed.")
        return 0

    try:
        apply_changes(changes)
    except Exception as exc:
        print(f"\nERROR while writing files: {exc}", file=sys.stderr)
        print("Files already written were restored.", file=sys.stderr)
        return 1

    print("\nSuccess: Personality UI and Response Styles language support was applied.")
    print("The approved Swedish personality result wording was not modified.")
    print("Backups end with .bak-personality-ui-language")
    print("\nNext commands:")
    print("python manage.py makemessages -l sv")
    print("python manage.py check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
