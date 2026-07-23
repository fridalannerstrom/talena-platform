#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


MARKER = "Talena cognitive results language batch 1"


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


def function_bounds(source: str, function_name: str) -> tuple[int, int]:
    match = re.search(
        rf"(?m)^def {re.escape(function_name)}\(",
        source,
    )
    if not match:
        raise RuntimeError(f"Could not find function {function_name}.")

    start = match.start()
    next_definition = re.search(
        r"(?m)^(?:def|class) [A-Za-z_]\w*",
        source[match.end():],
    )
    end = (
        match.end() + next_definition.start()
        if next_definition
        else len(source)
    )
    return start, end


def ensure_translation_import(source: str) -> str:
    import_line = "from django.utils.translation import gettext as _"

    if import_line in source:
        return source

    anchors = (
        "from django.utils import timezone\n",
        "from django.urls import reverse\n",
        "from django.shortcuts import render, redirect, get_object_or_404\n",
    )

    for anchor in anchors:
        if anchor in source:
            return source.replace(
                anchor,
                anchor + import_line + "\n",
                1,
            )

    raise RuntimeError(
        "apps/processes/views.py: could not find a safe "
        "location for the gettext import."
    )


COGNITIVE_RESULTS_FUNCTION = 'def build_cognitive_insight_results(\n    verbal_percentile=None,\n    logical_percentile=None,\n    numerical_percentile=None,\n):\n    """\n    Build the three cognitive result cards used in Candidate Insights.\n\n    All three assessment types are always returned so the template can show\n    a grey placeholder when an assessment has not been completed.\n\n    Percentile calculations and thresholds are intentionally unchanged.\n    """\n\n    def normalise_percentile(value):\n        if value is None:\n            return None\n\n        try:\n            return int(round(float(value)))\n        except (TypeError, ValueError):\n            return None\n\n    def get_level(percentile):\n        """\n        Translate a percentile result into a display level and interpretation.\n        Adjust the thresholds later if Sova uses different norm bands.\n        """\n\n        if percentile is None:\n            return {\n                "completed": False,\n                "level_key": "missing",\n                "level_label": _("Not completed"),\n            }\n\n        if percentile <= 9:\n            return {\n                "completed": True,\n                "level_key": "very-low",\n                "level_label": _("Very low"),\n            }\n\n        if percentile <= 24:\n            return {\n                "completed": True,\n                "level_key": "low",\n                "level_label": _("Low"),\n            }\n\n        if percentile <= 74:\n            return {\n                "completed": True,\n                "level_key": "average",\n                "level_label": _("Typical range"),\n            }\n\n        if percentile <= 90:\n            return {\n                "completed": True,\n                "level_key": "high",\n                "level_label": _("High"),\n            }\n\n        return {\n            "completed": True,\n            "level_key": "very-high",\n            "level_label": _("Very high"),\n        }\n\n    def get_interpretation(test_key, percentile):\n        if percentile is None:\n            return _(\n                "This candidate has not completed this assessment."\n            )\n\n        ability_labels = {\n            "verbal": _(\n                "understand and evaluate written information"\n            ),\n            "logical": _(\n                "identify patterns and reach logical conclusions"\n            ),\n            "numerical": _(\n                "understand and work with numerical information"\n            ),\n        }\n\n        ability_text = ability_labels[test_key]\n\n        if percentile <= 9:\n            return _(\n                "The candidate may find it considerably more difficult "\n                "than most people in the reference group to %(ability)s."\n            ) % {\n                "ability": ability_text,\n            }\n\n        if percentile <= 24:\n            return _(\n                "The candidate may find it more difficult than many "\n                "others in the reference group to %(ability)s."\n            ) % {\n                "ability": ability_text,\n            }\n\n        if percentile <= 74:\n            return _(\n                "The candidate is likely to find it about as easy as "\n                "most people in the reference group to %(ability)s."\n            ) % {\n                "ability": ability_text,\n            }\n\n        if percentile <= 90:\n            return _(\n                "The candidate may find it easier than many others in "\n                "the reference group to %(ability)s."\n            ) % {\n                "ability": ability_text,\n            }\n\n        return _(\n            "The candidate may find it considerably easier than most "\n            "people in the reference group to %(ability)s."\n        ) % {\n            "ability": ability_text,\n        }\n\n    test_config = [\n        {\n            "key": "logical",\n            "title": _("Logical reasoning"),\n            "measure_label": _("Logical reasoning ability"),\n            "percentile": normalise_percentile(\n                logical_percentile\n            ),\n        },\n        {\n            "key": "numerical",\n            "title": _("Numerical reasoning"),\n            "measure_label": _("Numerical reasoning ability"),\n            "percentile": normalise_percentile(\n                numerical_percentile\n            ),\n        },\n        {\n            "key": "verbal",\n            "title": _("Verbal reasoning"),\n            "measure_label": _("Verbal reasoning ability"),\n            "percentile": normalise_percentile(\n                verbal_percentile\n            ),\n        },\n    ]\n\n    results = []\n\n    for test in test_config:\n        percentile = test["percentile"]\n        level = get_level(percentile)\n\n        if percentile is None:\n            percentile_aria_label = ""\n            missing_aria_label = _(\n                "%(title)s assessment not completed"\n            ) % {\n                "title": test["title"],\n            }\n        else:\n            percentile_aria_label = _(\n                "%(title)s percentile %(percentile)s"\n            ) % {\n                "title": test["title"],\n                "percentile": percentile,\n            }\n            missing_aria_label = ""\n\n        results.append({\n            "key": test["key"],\n            "title": test["title"],\n            "measure_label": test["measure_label"],\n            "percentile": percentile,\n            "completed": level["completed"],\n            "level_key": level["level_key"],\n            "level_label": level["level_label"],\n            "interpretation": get_interpretation(\n                test_key=test["key"],\n                percentile=percentile,\n            ),\n            "percentile_aria_label": percentile_aria_label,\n            "missing_aria_label": missing_aria_label,\n        })\n\n    return results\n'

RESULTS_TEMPLATE = '{% load i18n %}\n\n<!-- COGNITIVE ASSESSMENT RESULTS -->\n{% if candidate_insights.cognitive_results %}\n  <section class="purpose-fit-card">\n\n    <div class="cognitive-results-grid mt-4">\n\n      {% for result in candidate_insights.cognitive_results %}\n\n        {% if result.completed %}\n\n          <!-- COMPLETED TEST -->\n          <article class="cognitive-result-card">\n\n            <div class="cognitive-result-card__header">\n              <div>\n                <h3 class="cognitive-result-card__title">\n                  {{ result.title }}\n                </h3>\n\n                <div class="cognitive-result-card__subtitle">\n                  {% trans "Cognitive assessment" %}\n                </div>\n              </div>\n            </div>\n\n            <div class="cognitive-chart-wrapper">\n\n              <div\n                class="cognitive-doughnut"\n                style="--percentile: {{ result.percentile }};"\n                role="img"\n                aria-label="{{ result.percentile_aria_label }}"\n              >\n                <div class="cognitive-doughnut__inner">\n                  <div class="cognitive-doughnut__value">\n                    {{ result.percentile }}\n                  </div>\n\n                  <div class="cognitive-doughnut__label">\n                    {% trans "Percentile" %}\n                  </div>\n                </div>\n              </div>\n\n            </div>\n\n            <div class="cognitive-result-card__content">\n\n              {% if result.interpretation %}\n                <p class="cognitive-result-card__interpretation">\n                  {{ result.interpretation }}\n                </p>\n              {% endif %}\n\n            </div>\n\n            <div class="cognitive-comparison">\n\n              <div class="cognitive-comparison__label">\n                {% trans "Compared with the reference group" %}\n              </div>\n\n              <div class="cognitive-comparison__bar">\n                <div\n                  class="cognitive-comparison__fill"\n                  style="width: {{ result.percentile }}%;"\n                ></div>\n              </div>\n\n              <div class="cognitive-comparison__labels">\n                <span>{% trans "Lower" %}</span>\n                <span>{% trans "Typical range" %}</span>\n                <span>{% trans "Higher" %}</span>\n              </div>\n\n            </div>\n\n          </article>\n\n        {% else %}\n\n          <!-- NOT COMPLETED -->\n          <article\n            class="cognitive-result-card cognitive-result-card--missing"\n          >\n\n            <div class="cognitive-result-card__header">\n              <div>\n                <h3 class="cognitive-result-card__title">\n                  {{ result.title }}\n                </h3>\n\n                <div class="cognitive-result-card__subtitle">\n                  {% trans "Cognitive assessment" %}\n                </div>\n              </div>\n            </div>\n\n            <div class="cognitive-chart-wrapper">\n\n              <div\n                class="cognitive-doughnut cognitive-doughnut--missing"\n                role="img"\n                aria-label="{{ result.missing_aria_label }}"\n              >\n                <div class="cognitive-doughnut__inner">\n\n                  <div class="cognitive-doughnut__missing-icon">\n                    —\n                  </div>\n\n                  <div class="cognitive-doughnut__label">\n                    {% trans "No result" %}\n                  </div>\n\n                </div>\n              </div>\n\n            </div>\n\n            <div class="cognitive-result-card__content">\n\n              {% if result.measure_label %}\n                <div class="cognitive-result-card__measure">\n                  {{ result.measure_label }}\n                </div>\n              {% endif %}\n\n              {% if result.interpretation %}\n                <p class="cognitive-result-card__interpretation">\n                  {{ result.interpretation }}\n                </p>\n              {% endif %}\n\n            </div>\n\n            <div class="cognitive-missing-note">\n              {% trans "No percentile result is available." %}\n            </div>\n\n          </article>\n\n        {% endif %}\n\n      {% endfor %}\n\n    </div>\n\n    <div class="small text-muted border-top pt-3 mt-4">\n      {% blocktrans trimmed %}\n        Percentiles describe relative performance compared with a reference\n        group. They are not percentages of questions answered correctly.\n      {% endblocktrans %}\n    </div>\n\n  </section>\n{% endif %}\n<!-- /COGNITIVE ASSESSMENT RESULTS -->\n'

INTERPRETATION_TEMPLATE = '{% load i18n %}\n\n<!-- PRACTICAL INTERPRETATION -->\n<section class="cognitive-ai-section purpose-fit-section">\n\n  <h3 class="cognitive-ai-section__title">\n    {% trans "Practical interpretation" %}\n  </h3>\n\n  <div\n    class="cognitive-ai-interpretation"\n    data-cognitive-ai-interpretation\n  >\n    {{ cognitive_interpretation.interpretation }}\n  </div>\n\n</section>\n\n\n<!-- RELEVANT CONSIDERATIONS -->\n<section\n  class="cognitive-ai-section mt-4"\n  data-cognitive-ai-considerations-section\n>\n\n  <h3 class="cognitive-ai-section__title">\n    {% trans "Relevant considerations" %}\n  </h3>\n\n  <ul\n    class="cognitive-ai-considerations"\n    data-cognitive-ai-considerations\n  >\n    {% for item in cognitive_interpretation.considerations %}\n      <li>\n        <span class="cognitive-ai-list-icon">\n          <i data-feather="search"></i>\n        </span>\n\n        <span>{{ item }}</span>\n      </li>\n    {% endfor %}\n  </ul>\n\n</section>\n\n\n<!-- CONTEXT NOTE -->\n<div class="cognitive-ai-context-note mt-4">\n\n  <div class="cognitive-ai-context-note__title">\n    {% trans "How Talena created this interpretation" %}\n  </div>\n\n  <div data-cognitive-ai-context-note>\n    {{ cognitive_interpretation.context_note }}\n  </div>\n\n</div>\n\n\n<!-- DISCLAIMER -->\n<div class="purpose-fit-disclaimer border-top pt-3 mt-4">\n\n  <i data-feather="info"></i>\n\n  <div>\n    {% blocktrans trimmed %}\n      Cognitive assessment results describe relative performance on specific\n      reasoning tasks. They do not measure personality, motivation, experience\n      or overall intelligence, and should be considered together with other\n      relevant evidence.\n    {% endblocktrans %}\n  </div>\n\n</div>\n'

QUESTIONS_TEMPLATE = '{% load i18n %}\n\n<div\n  class="personality-question-list"\n  data-cognitive-questions-list\n>\n\n  {% for item in cognitive_questions.questions %}\n\n    <article\n      class="purpose-fit-section"\n      data-cognitive-question-card\n    >\n\n      <div class="personality-question-card__header">\n\n        <div class="personality-question-card__number">\n          {{ forloop.counter }}\n        </div>\n\n        <div class="personality-question-card__heading">\n\n          <div class="personality-question-card__text">\n            {{ item.question }}\n          </div>\n\n        </div>\n\n      </div>\n\n      {% if item.why or item.listen_for %}\n\n        <div class="personality-question-card__details">\n\n          {% if item.why %}\n\n            <div class="personality-question-card__detail">\n\n              <div class="personality-question-card__detail-icon">\n                <i data-feather="compass"></i>\n              </div>\n\n              <div>\n\n                <div class="personality-question-card__detail-title">\n                  {% trans "Why this matters" %}\n                </div>\n\n                <div class="personality-question-card__detail-text">\n                  {{ item.why }}\n                </div>\n\n              </div>\n\n            </div>\n\n          {% endif %}\n\n          {% if item.listen_for %}\n\n            <div class="personality-question-card__detail">\n\n              <div class="personality-question-card__detail-icon">\n                <i data-feather="headphones"></i>\n              </div>\n\n              <div>\n\n                <div class="personality-question-card__detail-title">\n                  {% trans "What to look for in the answer" %}\n                </div>\n\n                <div class="personality-question-card__detail-text">\n                  {{ item.listen_for }}\n                </div>\n\n              </div>\n\n            </div>\n\n          {% endif %}\n\n        </div>\n\n      {% endif %}\n\n    </article>\n\n  {% endfor %}\n\n</div>\n\n\n<div class="purpose-fit-disclaimer border-top pt-3 mt-4">\n\n  <i data-feather="info"></i>\n\n  <div>\n    {% blocktrans trimmed %}\n      Use these questions to gather concrete examples of how the candidate\n      works with information and approaches problems. Cognitive assessment\n      results provide supporting evidence and should not replace information\n      from relevant experience, structured interviews or other assessment\n      methods.\n    {% endblocktrans %}\n  </div>\n\n</div>\n'


def transform_views(source: str) -> str:
    if MARKER in source:
        raise RuntimeError(
            "apps/processes/views.py: batch already applied."
        )

    source = ensure_translation_import(source)
    start, end = function_bounds(
        source,
        "build_cognitive_insight_results",
    )

    updated = (
        source[:start]
        + f"# {MARKER}\n"
        + COGNITIVE_RESULTS_FUNCTION.rstrip()
        + "\n\n\n"
        + source[end:].lstrip("\n")
    )

    compile_python(
        updated,
        Path("apps/processes/views.py"),
    )
    return updated


def validate_template_source(
    source: str,
    *,
    path: str,
    required_markers: tuple[str, ...],
) -> None:
    for marker in required_markers:
        if marker not in source:
            raise RuntimeError(
                f"{path}: expected marker was not found: {marker}"
            )


def prepare_changes(root: Path) -> list[Change]:
    paths = {
        "views": root / "apps/processes/views.py",
        "results": (
            root
            / "templates/customer/processes/partials/"
            "candidate_insights/cognitive/_results.html"
        ),
        "interpretation": (
            root
            / "templates/customer/processes/partials/"
            "candidate_insights/cognitive/_interpretation.html"
        ),
        "questions": (
            root
            / "templates/customer/processes/partials/"
            "candidate_insights/cognitive/_questions.html"
        ),
    }

    for path in paths.values():
        if not path.exists():
            raise FileNotFoundError(f"Required file is missing: {path}")

    originals = {
        key: path.read_text(encoding="utf-8")
        for key, path in paths.items()
    }

    validate_template_source(
        originals["results"],
        path=str(paths["results"]),
        required_markers=(
            "candidate_insights.cognitive_results",
            "cognitive-results-grid",
            "result.percentile",
        ),
    )
    validate_template_source(
        originals["interpretation"],
        path=str(paths["interpretation"]),
        required_markers=(
            "cognitive_interpretation.interpretation",
            "data-cognitive-ai-context-note",
        ),
    )
    validate_template_source(
        originals["questions"],
        path=str(paths["questions"]),
        required_markers=(
            "cognitive_questions.questions",
            "data-cognitive-question-card",
        ),
    )

    updated = {
        "views": transform_views(originals["views"]),
        "results": RESULTS_TEMPLATE,
        "interpretation": INTERPRETATION_TEMPLATE,
        "questions": QUESTIONS_TEMPLATE,
    }

    return [
        Change(
            path=paths[key],
            original=originals[key],
            updated=updated[key],
        )
        for key in (
            "views",
            "results",
            "interpretation",
            "questions",
        )
    ]


def apply_changes(changes: list[Change]) -> None:
    prepared = []

    for change in changes:
        backup = change.path.with_suffix(
            change.path.suffix + ".bak-cognitive-results-language"
        )
        temporary = change.path.with_suffix(
            change.path.suffix + ".tmp-cognitive-results-language"
        )

        if not backup.exists():
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
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        print("No project files were changed.", file=sys.stderr)
        return 1

    print("Validated files:")
    for change in changes:
        print(f"- {change.path.relative_to(root)}")

    if args.check:
        print(
            "\nSuccess: Cognitive Results language support validated."
        )
        print("No project files were changed.")
        return 0

    try:
        apply_changes(changes)
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
        "\nSuccess: Cognitive Results language support was applied."
    )
    print("Backups end with .bak-cognitive-results-language")
    print("\nNext command:")
    print("python manage.py makemessages -l sv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
