#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


MARKER = "Talena team styles language batch 1"
SERVICE_IMPORT_BLOCK = 'import math\n\nfrom django.utils.translation import gettext as _, gettext_noop\n\n# Talena team styles language batch 1\n\n_TEAM_STYLE_TRANSLATION_STRINGS = (\n    gettext_noop(\'Catalyst\'),\n    gettext_noop(\'Director\'),\n    gettext_noop(\'Energiser\'),\n    gettext_noop(\'Architect\'),\n    gettext_noop(\'Harmoniser\'),\n    gettext_noop(\'Analyst\'),\n    gettext_noop(\'Auditor\'),\n    gettext_noop(\'Connector\'),\n    gettext_noop(\'Explore\'),\n    gettext_noop(\'Lead\'),\n    gettext_noop(\'Deliver\'),\n    gettext_noop(\'Critically review\'),\n    gettext_noop(\'Looks for creative and innovative solutions and ideas. Brings new insight and new approaches to the team.\'),\n    gettext_noop(\'May dismiss established approaches too quickly, overcomplicate issues or develop solutions that are more complex than necessary.\'),\n    gettext_noop(\'May communicate spontaneously and move quickly between ideas.\'),\n    gettext_noop(\'Show genuine interest, allow room for creativity and ask questions that help develop the idea.\'),\n    gettext_noop(\'Rejecting ideas before exploring them, or moving immediately into detailed facts and restrictions.\'),\n    gettext_noop(\'Coordinates the group, clarifies needs and goals, and delegates accordingly. Brings clarity and decisiveness to the team.\'),\n    gettext_noop(\'May become overly directive, move ahead too quickly or pursue their own agenda without giving enough space to other views.\'),\n    gettext_noop(\'May focus on tasks, direction and strategy and can sometimes appear relatively businesslike or distant.\'),\n    gettext_noop(\'Be clear, rational and businesslike. Focus on the task, expected outcomes and areas of responsibility.\'),\n    gettext_noop(\'Losing focus on the task, becoming overly personal or failing to deliver what has been agreed.\'),\n    gettext_noop(\'Gets things done and drives the team forward. Brings energy and a sense of motivation to the team.\'),\n    gettext_noop(\'May weaken focus by pursuing too many things at once or changing direction quickly. Can appear forceful or impatient with people who work at a slower pace.\'),\n    gettext_noop(\'May communicate quickly, directly and with a strong sense of pace.\'),\n    gettext_noop(\'Maintain momentum, focus on the most important details, show confidence and involve them in decisions.\'),\n    gettext_noop(\'Responding too slowly, being excessively cautious or spending too much time on minor details.\'),\n    gettext_noop(\'Turns ideas into practical actions and plans. Brings efficiency, planning and organisation to the team.\'),\n    gettext_noop(\'May delay delivery through too much planning and preparation, and may find it difficult to adapt plans when requirements or priorities change.\'),\n    gettext_noop(\'May prefer concrete discussions about how ideas will be turned into actions.\'),\n    gettext_noop(\'Be specific, present a clear plan and describe the actions, responsibilities and practical next steps.\'),\n    gettext_noop(\'Discussing strategy without a practical plan, changing direction after work has started or setting unrealistic timelines.\'),\n    gettext_noop("Considers other people\'s needs and feelings. Brings cohesion and a sense of belonging to the team."),\n    gettext_noop(\'May try too hard to please others, find it difficult to say no or set realistic boundaries, and may be less comfortable working independently.\'),\n    gettext_noop(\'May pay close attention to relationships, inclusion and how other people are feeling.\'),\n    gettext_noop(\'Show consideration, recognise individual needs and offer sincere appreciation and support.\'),\n    gettext_noop(\'Ignoring relationship concerns, communicating impersonally or placing excessive demands on people who are already under strain.\'),\n    gettext_noop(\'Considers alternatives and takes a critical view of ideas and plans. Brings objectivity and critical analysis to the team.\'),\n    gettext_noop(\'May spend so much time analysing and evaluating that decisions are delayed or opportunities pass. May appear overly negative or reluctant to accept other perspectives.\'),\n    gettext_noop(\'May focus on facts, evidence, sources and the reliability of available information.\'),\n    gettext_noop(\'Be factual and well prepared, provide sufficient detail and allow time to examine or verify important information.\'),\n    gettext_noop(\'Making unsupported claims, appearing careless or disorganised, withholding relevant information or setting unrealistic deadlines.\'),\n    gettext_noop(\'Looks for inaccuracies and shortcomings and focuses on delivering what was promised. Brings quality awareness and attention to detail to the team.\'),\n    gettext_noop(\'May devote too much time to minor details, overwork to maintain standards or follow rules and procedures so closely that delivery becomes less flexible.\'),\n    gettext_noop(\'May communicate carefully and methodically and prefer time to consider information before responding.\'),\n    gettext_noop(\'Be calm and systematic, explain the reasons for changes and be clear about deadlines, safety and follow-up.\'),\n    gettext_noop(\'Leaving deadlines unclear, demanding immediate answers or using a forceful approach without explaining why.\'),\n    gettext_noop(\'Builds, develops and uses networks and other useful resources. Brings new contacts and connections to the team.\'),\n    gettext_noop(\'May spend too much time interacting and networking at the expense of other goals, or involve others before the process is sufficiently clear.\'),\n    gettext_noop(\'May communicate in a friendly and relationship-focused way and place value on personal connection.\'),\n    gettext_noop(\'Explain what you want clearly, allow time for conversation, show appreciation and ask about their perspective.\'),\n    gettext_noop(\'Taking over the conversation, withholding information, showing little engagement or using a cold or dismissive tone.\'),\n)\n'
RELEVANCE_FUNCTION = 'def _build_team_style_relevance(display_value):\n    """\n    Determine how strongly the practical guidance should be applied.\n\n    Sova provides fixed guidance for each team style, rather than separate\n    low-, middle- and high-score interpretations. The STIVE result therefore\n    controls how the source guidance is presented, not its content.\n    """\n    if display_value is None:\n        return {\n            "key": "unavailable",\n            "label": None,\n            "show_guidance": False,\n            "guidance_intro": None,\n        }\n\n    if display_value >= 4:\n        return {\n            "key": "prominent",\n            "label": _("Prominent style"),\n            "show_guidance": True,\n            "guidance_intro": _(\n                "This is a prominent preference in the candidate\'s profile. "\n                "The guidance below is therefore likely to be particularly "\n                "relevant."\n            ),\n        }\n\n    if display_value == 3:\n        return {\n            "key": "situational",\n            "label": _("Situational style"),\n            "show_guidance": True,\n            "guidance_intro": _(\n                "This preference is around the middle of the scale. "\n                "The guidance may be relevant depending on the situation "\n                "and team context."\n            ),\n        }\n\n    return {\n        "key": "less_likely",\n        "label": _("Less likely style"),\n        "show_guidance": True,\n        "guidance_intro": _(\n            "This is a less prominent preference in the candidate\'s profile. "\n            "The guidance below may therefore be less characteristic of their "\n            "usual approach, but can still be relevant in certain situations."\n        ),\n    }\n'
LOCALIZE_CONFIG_BLOCK = '        config = {\n            **config,\n            "title": _(config["title"]),\n            "quadrant_label": _(config["quadrant_label"]),\n            "contribution": _(config["contribution"]),\n            "possible_overuse": _(config["possible_overuse"]),\n            "communication_tendency": _(\n                config["communication_tendency"]\n            ),\n            "build_trust": _(config["build_trust"]),\n            "avoid": _(config["avoid"]),\n        }\n'
TEAM_STYLES_TEMPLATE = '{% load i18n %}\n\n{% if team_style_profile.available %}\n  <section class="mb-4 purpose-fit-card team-styles-section">\n    <div>\n\n      <!-- HEADER -->\n      <header class="team-styles-header mb-4">\n\n        <h2 class="insight-summary-title mb-1">\n          {% trans "Team styles" %}\n        </h2>\n\n        <p class="text-muted small mb-0">\n          {% blocktrans trimmed %}\n            The profile shows how the candidate may approach eight roles\n            commonly observed in teams. Results use Sova\'s five-point\n            team-style scale.\n          {% endblocktrans %}\n        </p>\n      </header>\n\n      <!-- FULL-WIDTH POLAR CHART -->\n      <div class="team-style-chart-card mb-4">\n        <div class="team-style-polar-wrap">\n          <canvas\n            id="teamStylePolarChart"\n            aria-label="{% trans \'Team role profile chart\' %}"\n          ></canvas>\n        </div>\n      </div>\n\n      {{ team_style_profile.chart.labels|json_script:"team-style-chart-labels" }}\n      {{ team_style_profile.chart.values|json_script:"team-style-chart-values" }}\n      {{ team_style_profile.chart.backgrounds|json_script:"team-style-chart-backgrounds" }}\n      {{ team_style_profile.chart.border_colors|json_script:"team-style-chart-borders" }}\n\n      <!-- ALL TEAM STYLES, RANKED -->\n      <div class="response-style-card team-style-ranked-list">\n\n        {% for style in team_style_profile.styles %}\n\n          {% blocktrans with title=style.title value=style.display_value asvar team_style_aria %}\n            {{ title }}: {{ value }} out of 5\n          {% endblocktrans %}\n\n          <article class="insight-summary-content mb-4">\n\n            <!-- STYLE HEADER -->\n            <div class="response-style-item__header">\n\n              <div>\n                <h4 class="response-style-item__title">\n                  {{ style.title }}\n                </h4>\n\n                <div class="response-style-item__subtitle">\n                  {% blocktrans with quadrant=style.quadrant_label %}\n                    {{ quadrant }} team style\n                  {% endblocktrans %}\n                </div>\n              </div>\n\n            </div>\n\n            <!-- RESULT -->\n            <div class="team-style-result">\n\n              <div class="team-style-result__header">\n                <div>\n                  <div class="team-style-result__label">\n                    {% trans "Team style result" %}\n                  </div>\n                </div>\n\n                <div class="team-style-result__value">\n                  {{ style.display_value }}/5\n                </div>\n              </div>\n\n              <div\n                class="\n                  response-style-scale\n                  response-style-scale--linear\n                  team-style-result__scale\n                "\n                role="meter"\n                aria-label="{{ team_style_aria|trim }}"\n                aria-valuemin="1"\n                aria-valuemax="5"\n                aria-valuenow="{{ style.display_value }}"\n              >\n\n                <div class="response-style-scale__segments">\n\n                  {% for segment in style.scale_segments %}\n                    <span\n                      class="\n                        response-style-scale__segment\n\n                        {% if segment == style.display_value %}\n                          response-style-scale__segment--marker\n                        {% endif %}\n\n                        {% if segment <= style.display_value %}\n                          response-style-scale__segment--filled\n                        {% endif %}\n                      "\n                    ></span>\n                  {% endfor %}\n\n                </div>\n\n                <div class="response-style-scale__labels">\n                  <span>{% trans "Less likely" %}</span>\n                  <span>{% trans "Typical" %}</span>\n                  <span>{% trans "More likely" %}</span>\n                </div>\n\n              </div>\n\n            </div>\n\n            <!-- TEAM STYLE DESCRIPTION -->\n            <div class="team-style-description">\n\n              <div>\n                <div class="team-style-description__label">\n                  {% trans "About this team style" %}\n                </div>\n\n                <p class="team-style-description__text">\n                  {{ style.contribution }}\n                </p>\n              </div>\n\n            </div>\n\n            <!-- PRACTICAL GUIDANCE -->\n            <div class="team-style-guidance">\n\n              <div class="team-style-guidance__header">\n                <div class="team-style-guidance__label">\n                  {% trans "Practical guidance" %}\n                </div>\n\n                {% if style.relevance.guidance_intro %}\n                  <p>\n                    {{ style.relevance.guidance_intro }}\n                  </p>\n                {% else %}\n                  <p>\n                    {% trans "Points to consider when working and communicating with this candidate." %}\n                  </p>\n                {% endif %}\n              </div>\n\n              <div class="team-style-guidance__grid">\n\n                <div class="team-style-guidance__item">\n\n                  <div class="team-style-guidance__item-header">\n                    <i\n                      data-feather="message-circle"\n                      aria-hidden="true"\n                    ></i>\n                    <span>{% trans "Communication style" %}</span>\n                  </div>\n\n                  <p>\n                    {{ style.communication_tendency }}\n                  </p>\n\n                </div>\n\n                <div class="team-style-guidance__item">\n\n                  <div class="team-style-guidance__item-header">\n                    <i\n                      data-feather="alert-circle"\n                      aria-hidden="true"\n                    ></i>\n                    <span>{% trans "Possible limitations" %}</span>\n                  </div>\n\n                  <p>\n                    {{ style.possible_overuse }}\n                  </p>\n\n                </div>\n\n                <div class="team-style-guidance__item">\n\n                  <div class="team-style-guidance__item-header">\n                    <i\n                      data-feather="shield"\n                      aria-hidden="true"\n                    ></i>\n                    <span>{% trans "Build trust by" %}</span>\n                  </div>\n\n                  <p>\n                    {{ style.build_trust }}\n                  </p>\n\n                </div>\n\n                <div class="team-style-guidance__item">\n\n                  <div class="team-style-guidance__item-header">\n                    <i\n                      data-feather="x-circle"\n                      aria-hidden="true"\n                    ></i>\n                    <span>{% trans "Try to avoid" %}</span>\n                  </div>\n\n                  <p>\n                    {{ style.avoid }}\n                  </p>\n\n                </div>\n\n              </div>\n\n            </div>\n\n          </article>\n        {% endfor %}\n\n      </div>\n\n      <footer class="team-styles-footer">\n        {% blocktrans trimmed %}\n          Team-style results describe likely preferences rather than fixed\n          behaviour or ability. Ordering uses the underlying Sova result,\n          while the displayed values are rounded. Small score differences\n          should not be overinterpreted.\n        {% endblocktrans %}\n      </footer>\n\n    </div>\n  </section>\n{% endif %}\n'


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


def function_bounds(
    source: str,
    function_name: str,
) -> tuple[int, int]:
    match = re.search(
        rf"(?m)^def {re.escape(function_name)}\(",
        source,
    )
    if not match:
        raise RuntimeError(
            f"Could not find function {function_name}."
        )

    start = match.start()
    next_definition = re.search(
        r"(?m)^def [A-Za-z_]\w*\(",
        source[match.end():],
    )
    end = (
        match.end() + next_definition.start()
        if next_definition
        else len(source)
    )
    return start, end


def replace_function(
    source: str,
    function_name: str,
    replacement: str,
) -> str:
    start, end = function_bounds(
        source,
        function_name,
    )
    return (
        source[:start]
        + replacement.rstrip()
        + "\n\n\n"
        + source[end:].lstrip("\n")
    )


def transform_service(source: str) -> str:
    path = "apps/processes/services/team_styles.py"

    if MARKER in source:
        raise RuntimeError(
            f"{path}: batch already applied."
        )

    if not source.startswith("import math"):
        raise RuntimeError(
            f"{path}: expected the file to begin with import math."
        )

    source = source.replace(
        "import math",
        SERVICE_IMPORT_BLOCK.rstrip(),
        1,
    )

    source = replace_function(
        source,
        "_build_team_style_relevance",
        RELEVANCE_FUNCTION,
    )

    loop_anchor = (
        "    for config_index, config in "
        "enumerate(TEAM_STYLE_CONFIG):\n"
    )

    if loop_anchor not in source:
        raise RuntimeError(
            f"{path}: team style configuration loop was not found."
        )

    source = source.replace(
        loop_anchor,
        loop_anchor + LOCALIZE_CONFIG_BLOCK,
        1,
    )

    compile_python(
        source,
        Path(path),
    )
    return source


def prepare_changes(root: Path) -> list[Change]:
    service_path = (
        root / "apps/processes/services/team_styles.py"
    )
    template_path = (
        root / "templates/customer/processes/partials/"
        "_team_styles.html"
    )

    for path in (
        service_path,
        template_path,
    ):
        if not path.exists():
            raise FileNotFoundError(
                f"Required file is missing: {path}"
            )

    service_source = service_path.read_text(
        encoding="utf-8"
    )
    template_source = template_path.read_text(
        encoding="utf-8"
    )

    for expected in (
        "TEAM_STYLE_CONFIG",
        "_build_team_style_relevance",
        "build_team_style_profile",
        "stive_rounded",
        "max(1, min(5",
    ):
        if expected not in service_source:
            raise RuntimeError(
                f"{service_path}: expected marker not found: "
                f"{expected}"
            )

    for expected in (
        "team_style_profile.available",
        "teamStylePolarChart",
        "style.display_value",
        "style.build_trust",
        "style.avoid",
    ):
        if expected not in template_source:
            raise RuntimeError(
                f"{template_path}: expected marker not found: "
                f"{expected}"
            )

    updated_service = transform_service(
        service_source
    )

    return [
        Change(
            path=service_path,
            original=service_source,
            updated=updated_service,
        ),
        Change(
            path=template_path,
            original=template_source,
            updated=TEAM_STYLES_TEMPLATE,
        ),
    ]


def apply_changes(changes: list[Change]) -> None:
    prepared = []

    for change in changes:
        backup = change.path.with_suffix(
            change.path.suffix
            + ".bak-team-styles-language"
        )
        temporary = change.path.with_suffix(
            change.path.suffix
            + ".tmp-team-styles-language"
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
        for change, backup in reversed(
            written
        ):
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
    mode.add_argument(
        "--check",
        action="store_true",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
    )
    parser.add_argument(
        "--root",
        default=".",
    )
    args = parser.parse_args()

    root = Path(
        args.root
    ).resolve()

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
            "\nSuccess: Team Styles language support validated."
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
        "\nSuccess: Team Styles language support was applied."
    )
    print(
        "Backups end with .bak-team-styles-language"
    )
    print(
        "\nNext command:"
    )
    print(
        "python manage.py makemessages -l sv"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
