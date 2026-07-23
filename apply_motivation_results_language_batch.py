#!/usr/bin/env python3
# Talena Motivation Results and static UI language batch.
#
# Run from the repository root:
#   python apply_motivation_results_language_batch.py --check
#   python apply_motivation_results_language_batch.py --apply

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


MARKER = "Talena motivation Results language batch 1"
FILTER_MODULE = '# Bilingual display helpers for Talena Motivation Results.\n\nfrom __future__ import annotations\n\nfrom django import template\nfrom django.utils.translation import get_language\n\n\nregister = template.Library()\n\n\nDOMAIN_CONTENT = {\n    "belonging": {\n        "title": "Samhörighet",\n        "subtitle": (\n            "Social kontakt, stöd och en känsla av tillhörighet i arbetet"\n        ),\n    },\n    "influence": {\n        "title": "Inflytande",\n        "subtitle": (\n            "Självständighet, erkännande och möjligheter att påverka resultat"\n        ),\n    },\n    "growth": {\n        "title": "Utveckling",\n        "subtitle": (\n            "Prestation, kvalitet, lärande och meningsfulla standarder"\n        ),\n    },\n    "interest": {\n        "title": "Intresse",\n        "subtitle": (\n            "Utforskande, kreativitet, arbetsglädje, variation och risktagande"\n        ),\n    },\n}\n\n\nFACTOR_CONTENT = {\n    "attachment": {\n        "name": "Samhörighet",\n        "description": (\n            "Social kontakt, stöd och att arbeta som en del av ett team."\n        ),\n    },\n    "customer_service": {\n        "name": "Kundservice",\n        "description": (\n            "Att förstå kunders behov och ge hjälpsam service."\n        ),\n    },\n    "work_life_balance": {\n        "name": "Balans mellan arbete och fritid",\n        "description": (\n            "Att upprätthålla en hållbar balans mellan arbete och "\n            "livet utanför arbetet."\n        ),\n    },\n    "people_development": {\n        "name": "Utveckla andra",\n        "description": (\n            "Att hjälpa andra människor att lära, växa och utvecklas."\n        ),\n    },\n    "stability": {\n        "name": "Stabilitet",\n        "description": (\n            "Förutsägbarhet, kontinuitet och trygghet i arbetsmiljön."\n        ),\n    },\n    "authority": {\n        "name": "Auktoritet",\n        "description": (\n            "Status, senioritet och möjligheten att påverka eller leda andra."\n        ),\n    },\n    "independence": {\n        "name": "Självständighet",\n        "description": (\n            "Frihet att fatta beslut och påverka hur arbetet genomförs."\n        ),\n    },\n    "recognition": {\n        "name": "Erkännande",\n        "description": (\n            "Synlighet, beröm och uppskattning för den egna insatsen."\n        ),\n    },\n    "making_a_difference": {\n        "name": "Göra skillnad",\n        "description": (\n            "Att bidra till ett större syfte eller skapa positiv påverkan."\n        ),\n    },\n    "acquisition": {\n        "name": "Ekonomisk belöning",\n        "description": (\n            "Ekonomisk belöning, resurser och materiella fördelar."\n        ),\n    },\n    "achievement": {\n        "name": "Prestation",\n        "description": (\n            "Tydliga mål, utmaningar och en synlig känsla av framsteg."\n        ),\n    },\n    "quality": {\n        "name": "Kvalitet",\n        "description": (\n            "Att leverera noggrant och tillförlitligt arbete med hög kvalitet."\n        ),\n    },\n    "learning": {\n        "name": "Lärande",\n        "description": (\n            "Att utveckla kunskap, förmåga och nya färdigheter."\n        ),\n    },\n    "ethics": {\n        "name": "Etik",\n        "description": (\n            "Att agera i linje med tydliga principer och etiska standarder."\n        ),\n    },\n    "commercial_focus": {\n        "name": "Kommersiellt värde",\n        "description": (\n            "Att skapa mätbart kommersiellt värde och affärsresultat."\n        ),\n    },\n    "curiosity": {\n        "name": "Nyfikenhet",\n        "description": (\n            "Att utforska ny information, frågor och obekanta problem."\n        ),\n    },\n    "creativity": {\n        "name": "Kreativitet",\n        "description": (\n            "Att skapa nya idéer och hitta originella tillvägagångssätt."\n        ),\n    },\n    "enjoyment": {\n        "name": "Arbetsglädje",\n        "description": (\n            "Positiv energi och glädje i det dagliga arbetet."\n        ),\n    },\n    "variety": {\n        "name": "Variation",\n        "description": (\n            "Förändring, olika uppgifter och varierade arbetssätt."\n        ),\n    },\n    "risk": {\n        "name": "Risktagande",\n        "description": (\n            "Att ta kalkylerade risker och agera trots osäkerhet."\n        ),\n    },\n}\n\n\ndef _is_swedish() -> bool:\n    return str(\n        get_language()\n        or "sv"\n    ).lower().startswith("sv")\n\n\ndef _item_key(value) -> str:\n    if isinstance(value, dict):\n        return str(\n            value.get("key")\n            or ""\n        ).strip()\n\n    return ""\n\n\n@register.filter\ndef motivation_profile_title(value):\n    if _is_swedish():\n        return "Motivationsprofil"\n\n    return value\n\n\n@register.filter\ndef motivation_domain_title(value):\n    if not _is_swedish() or not isinstance(value, dict):\n        return (\n            value.get("title", "")\n            if isinstance(value, dict)\n            else value\n        )\n\n    content = DOMAIN_CONTENT.get(\n        str(value.get("key") or "")\n    )\n    return (\n        content["title"]\n        if content\n        else value.get("title", "")\n    )\n\n\n@register.filter\ndef motivation_domain_subtitle(value):\n    if not _is_swedish() or not isinstance(value, dict):\n        return (\n            value.get("subtitle", "")\n            if isinstance(value, dict)\n            else value\n        )\n\n    content = DOMAIN_CONTENT.get(\n        str(value.get("key") or "")\n    )\n    return (\n        content["subtitle"]\n        if content\n        else value.get("subtitle", "")\n    )\n\n\n@register.filter\ndef motivation_name(value):\n    if not isinstance(value, dict):\n        return value\n\n    if not _is_swedish():\n        return value.get("name", "")\n\n    content = FACTOR_CONTENT.get(\n        _item_key(value)\n    )\n    return (\n        content["name"]\n        if content\n        else value.get("name", "")\n    )\n\n\n@register.filter\ndef motivation_description(value):\n    if not isinstance(value, dict):\n        return value\n\n    if not _is_swedish():\n        return value.get("description", "")\n\n    content = FACTOR_CONTENT.get(\n        _item_key(value)\n    )\n    return (\n        content["description"]\n        if content\n        else value.get("description", "")\n    )\n\n\n@register.filter\ndef motivation_top_interpretation(value):\n    if not isinstance(value, dict):\n        return value\n\n    if not _is_swedish():\n        return value.get("interpretation", "")\n\n    content = FACTOR_CONTENT.get(\n        _item_key(value)\n    )\n    description = (\n        content["description"]\n        if content\n        else value.get("description", "")\n    )\n\n    if not description:\n        return (\n            "Resultatet tyder på att detta kan vara en mer "\n            "framträdande källa till energi och engagemang."\n        )\n\n    return (\n        f"{description} Resultatet tyder på att detta kan vara en "\n        "mer framträdande källa till energi och engagemang."\n    )\n'


@dataclass(frozen=True)
class Change:
    path: Path
    original: str | None
    updated: str


def compile_python(source: str, path: Path) -> None:
    try:
        compile(source, str(path), "exec")
    except SyntaxError as error:
        raise RuntimeError(
            f"{path}: generated Python syntax is invalid: {error}"
        ) from error


def token_pattern(source: str) -> re.Pattern[str]:
    tokens = re.findall(
        r'"(?:\\.|[^"\\])*"'
        r"|\'(?:\\.|[^\'\\])*\'"
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
        return text.replace(old, new, 1)

    if exact_count > 1:
        raise RuntimeError(
            f"{path}: expected 1 occurrence, found "
            f"{exact_count} for:\n{old[:350]}"
        )

    pattern = token_pattern(old)
    matches = list(pattern.finditer(text))

    if len(matches) != 1:
        raise RuntimeError(
            f"{path}: expected 1 flexible occurrence, found "
            f"{len(matches)} for:\n{old[:350]}"
        )

    return pattern.sub(
        lambda _match: new.strip("\n"),
        text,
        count=1,
    )


def prepend_load(
    text: str,
    load_line: str,
) -> str:
    if "motivation_i18n" in text:
        raise RuntimeError(
            "Motivation template tags are already loaded."
        )

    return (
        load_line
        + "\n"
        + "{# "
        + MARKER
        + " #}\n"
        + text.lstrip("\n")
    )


def transform_results(text: str) -> str:
    path = (
        "templates/customer/processes/partials/"
        "candidate_insights/motivation/_results.html"
    )
    text = prepend_load(
        text,
        '''{% load i18n motivation_i18n %}
{% trans "The candidate" as motivation_candidate_fallback %}''',
    )

    dynamic_replacements = [
        (
            "{{ motivation_insights.title }}",
            "{{ motivation_insights.title|motivation_profile_title }}",
        ),
        (
            'data-factor-name="{{ item.name|escape }}"',
            'data-factor-name="{{ item|motivation_name|escape }}"',
        ),
        (
            'data-factor-domain="{{ domain.title|escape }}"',
            'data-factor-domain="{{ domain|motivation_domain_title|escape }}"',
        ),
        (
            "{{ item.interpretation }}",
            "{{ item|motivation_top_interpretation }}",
        ),
        (
            "{{ domain.title }}",
            "{{ domain|motivation_domain_title }}",
        ),
        (
            "{{ domain.subtitle }}",
            "{{ domain|motivation_domain_subtitle }}",
        ),
        (
            "{{ item.description }}",
            "{{ item|motivation_description }}",
        ),
        (
            "{{ item.name }}",
            "{{ item|motivation_name }}",
        ),
        (
            'aria-label="{{ item.name }}: {{ item.score }} out of 5"',
            'aria-label="{% blocktrans with factor_name=item|motivation_name factor_score=item.score %}{{ factor_name }}: {{ factor_score }} out of 5{% endblocktrans %}"',
        ),
    ]

    # Replace aria-label before the shorter item.name pattern.
    dynamic_replacements = sorted(
        dynamic_replacements,
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for old, new in dynamic_replacements:
        count = text.count(old)
        if count < 1:
            raise RuntimeError(
                f"{path}: expected dynamic text was not found: {old}"
            )
        text = text.replace(
            old,
            new,
        )

    static_replacements = [
        (
            '''          The profile highlights the candidate's more prominent and less
          central motivational drivers, followed by the complete motivation
          profile. Results use Sova's rounded five-point STIVE scale.
''',
            '''          {% blocktrans %}The profile highlights the candidate's more prominent and less central motivational drivers, followed by the complete motivation profile. Results use Sova's rounded five-point STIVE scale.{% endblocktrans %}
''',
        ),
        (
            '      aria-label="Circular overview of the candidate\'s motivation profile"\n',
            '      aria-label="{% blocktrans %}Circular overview of the candidate\'s motivation profile{% endblocktrans %}"\n',
        ),
        (
            "    Preparing motivation overview...\n",
            '    {% trans "Preparing motivation overview…" %}\n',
        ),
        (
            '  {{ candidate.first_name|default:"The candidate" }}’s most prominent drivers\n',
            '  {% blocktrans with candidate_name=candidate.first_name|default:motivation_candidate_fallback %}{{ candidate_name }}’s most prominent drivers{% endblocktrans %}\n',
        ),
        (
            "                  Factors more likely to provide energy and engagement\n",
            '                  {% trans "Factors more likely to provide energy and engagement" %}\n',
        ),
        (
            "            All motivation factors\n",
            '            {% trans "All motivation factors" %}\n',
        ),
        (
            '''            Results are grouped according to the four areas in the
            motivation model.
''',
            '''            {% blocktrans %}Results are grouped according to the four areas in the motivation model.{% endblocktrans %}
''',
        ),
        (
            "                        N/A\n",
            '                        {% trans "N/A" %}\n',
        ),
        (
            "                        <span>Less central</span>\n",
            '                        <span>{% trans "Less central" %}</span>\n',
        ),
        (
            "                        <span>Mid-range</span>\n",
            '                        <span>{% trans "Mid-range" %}</span>\n',
        ),
        (
            "                        <span>More prominent</span>\n",
            '                        <span>{% trans "More prominent" %}</span>\n',
        ),
        (
            '''        Motivation scores describe relative sources of energy and preference.
        Lower results do not indicate poor performance, weak values or limited
        capability. Results should be considered alongside role context,
        interview evidence and the candidate's own reflections.
''',
            '''        {% blocktrans %}Motivation scores describe relative sources of energy and preference. Lower results do not indicate poor performance, weak values or limited capability. Results should be considered alongside role context, interview evidence and the candidate's own reflections.{% endblocktrans %}
''',
        ),
    ]

    for old, new in static_replacements:
        text = replace_once(
            text,
            old,
            new,
            path=path,
        )

    return text


def transform_interpretation(text: str) -> str:
    path = (
        "templates/customer/processes/partials/"
        "candidate_insights/motivation/_interpretation.html"
    )
    text = prepend_load(
        text,
        "{% load i18n %}",
    )

    replacements = [
        (
            "    Overall motivation interpretation\n",
            '    {% trans "Overall motivation interpretation" %}\n',
        ),
        (
            "        Realistic expectation setting\n",
            '        {% trans "Realistic expectation setting" %}\n',
        ),
        (
            "        Conditions likely to support engagement\n",
            '        {% trans "Conditions likely to support engagement" %}\n',
        ),
        (
            "        What to explore or clarify\n",
            '        {% trans "What to explore or clarify" %}\n',
        ),
        (
            "    How Talena created this interpretation\n",
            '    {% trans "How Talena created this interpretation" %}\n',
        ),
        (
            '''    Motivation results describe possible sources of energy,
    engagement and preference. Less central factors are not
    weaknesses and do not indicate limited capability or poor values.
''',
            '''    {% blocktrans %}Motivation results describe possible sources of energy, engagement and preference. Less central factors are not weaknesses and do not indicate limited capability or poor values.{% endblocktrans %}
''',
        ),
    ]

    for old, new in replacements:
        text = replace_once(
            text,
            old,
            new,
            path=path,
        )

    return text


def transform_questions(text: str) -> str:
    path = (
        "templates/customer/processes/partials/"
        "candidate_insights/motivation/_questions.html"
    )
    text = prepend_load(
        text,
        "{% load i18n %}",
    )

    replacements = [
        (
            "                  Why this matters\n",
            '                  {% trans "Why this matters" %}\n',
        ),
        (
            "                  What to look for in the answer\n",
            '                  {% trans "What to look for in the answer" %}\n',
        ),
        (
            '''    Motivation results indicate possible sources of energy and preference.
    Use these questions to gather concrete examples and the candidate’s own
    perspective rather than treating assessment indications as confirmed facts.
''',
            '''    {% blocktrans %}Motivation results indicate possible sources of energy and preference. Use these questions to gather concrete examples and the candidate’s own perspective rather than treating assessment indications as confirmed facts.{% endblocktrans %}
''',
        ),
    ]

    for old, new in replacements:
        text = replace_once(
            text,
            old,
            new,
            path=path,
        )

    return text


def prepare_changes(root: Path) -> list[Change]:
    filter_path = (
        root
        / "apps/processes/templatetags/motivation_i18n.py"
    )
    init_path = (
        root
        / "apps/processes/templatetags/__init__.py"
    )
    results_path = (
        root
        / "templates/customer/processes/partials/"
        "candidate_insights/motivation/_results.html"
    )
    interpretation_path = (
        root
        / "templates/customer/processes/partials/"
        "candidate_insights/motivation/_interpretation.html"
    )
    questions_path = (
        root
        / "templates/customer/processes/partials/"
        "candidate_insights/motivation/_questions.html"
    )

    for path in (
        results_path,
        interpretation_path,
        questions_path,
    ):
        if not path.exists():
            raise FileNotFoundError(
                f"Required file is missing: {path}"
            )

    if filter_path.exists():
        raise RuntimeError(
            f"{filter_path}: file already exists."
        )

    originals = {
        results_path: results_path.read_text(
            encoding="utf-8"
        ),
        interpretation_path: interpretation_path.read_text(
            encoding="utf-8"
        ),
        questions_path: questions_path.read_text(
            encoding="utf-8"
        ),
    }
    updated = {
        results_path: transform_results(
            originals[results_path]
        ),
        interpretation_path: transform_interpretation(
            originals[interpretation_path]
        ),
        questions_path: transform_questions(
            originals[questions_path]
        ),
        filter_path: FILTER_MODULE,
    }

    compile_python(
        updated[filter_path],
        filter_path,
    )

    changes = [
        Change(
            path=path,
            original=originals.get(path),
            updated=source,
        )
        for path, source in updated.items()
    ]

    if not init_path.exists():
        changes.append(
            Change(
                path=init_path,
                original=None,
                updated="",
            )
        )

    return changes


def apply_changes(changes: list[Change]) -> None:
    prepared = []

    for change in changes:
        change.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        backup = change.path.with_suffix(
            change.path.suffix
            + ".bak-motivation-results-language"
        )
        temporary = change.path.with_suffix(
            change.path.suffix
            + ".tmp-motivation-results-language"
        )

        if (
            change.original is not None
            and not backup.exists()
        ):
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
            if change.original is None:
                if change.path.exists():
                    change.path.unlink()
            elif backup.exists():
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
            "\nSuccess: Motivation Results and static UI "
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
        "\nSuccess: Motivation Results and static UI "
        "language support was applied."
    )
    print(
        "The existing rounded STIVE 1–5 score logic was not changed."
    )
    print(
        "Backups end with .bak-motivation-results-language"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
