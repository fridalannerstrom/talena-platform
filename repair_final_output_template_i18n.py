#!/usr/bin/env python3
"""
Repair and apply Django i18n tags to the static Final Output interface.

This batch only updates:
    templates/customer/processes/partials/candidate_insights/tabs/_final_output.html

It does not change:
- AI prompts or generated AI content
- interview notes
- database fields
- decision-support logic

Run from the repository root:

    python repair_final_output_template_i18n.py --check
    python repair_final_output_template_i18n.py --apply
"""

from __future__ import annotations

import argparse
import re
import shutil
import textwrap
from dataclasses import dataclass
from pathlib import Path


TARGET_PATH = Path(
    "templates/customer/processes/partials/"
    "candidate_insights/tabs/_final_output.html"
)

MARKER = "{# Talena final output template i18n batch 1 #}"


@dataclass(frozen=True)
class Replacement:
    old: str
    new: str
    minimum: int = 1


def r(old: str, new: str, minimum: int = 1) -> Replacement:
    return Replacement(
        old=textwrap.dedent(old).strip("\n"),
        new=textwrap.dedent(new).strip("\n"),
        minimum=minimum,
    )


REPLACEMENTS = (
    # ---------------------------------------------------------
    # Historical state and main tabs
    # ---------------------------------------------------------
    r(
        """
        Decision support is not yet available for historical candidates.
        """,
        """
        {% trans "Decision support is not yet available for historical candidates." %}
        """,
    ),
    r(
        'aria-label="Decision support stage"',
        'aria-label="{% trans \'Decision support stage\' %}"',
    ),
    r(
        "<span>Before interview</span>",
        '<span>{% trans "Before interview" %}</span>',
    ),
    r(
        "<span>After interview</span>",
        '<span>{% trans "After interview" %}</span>',
    ),

    # ---------------------------------------------------------
    # Pre-interview header and states
    # ---------------------------------------------------------
    r(
        """
        Pre-interview decision support
        """,
        """
        {% trans "Pre-interview decision support" %}
        """,
    ),
    r(
        """
        Uses the available assessment interpretations, process
        purpose and context to prepare a focused and evidence-based
        discussion.
        """,
        """
        {% blocktrans %}Uses the available assessment interpretations, process purpose and context to prepare a focused and evidence-based discussion.{% endblocktrans %}
        """,
    ),
    r(
        """
        Needs update
        """,
        """
        {% trans "Needs update" %}
        """,
    ),
    r(
        'title="Generate updated decision support"',
        'title="{% trans \'Generate updated decision support\' %}"',
    ),
    r(
        'aria-label="Generate updated decision support"',
        'aria-label="{% trans \'Generate updated decision support\' %}"',
    ),
    r(
        """
        The process information has changed
        """,
        """
        {% trans "The process information has changed" %}
        """,
    ),
    r(
        """
        This decision support was created using an earlier
        purpose or process context. Generate an updated version
        before relying on it.
        """,
        """
        {% blocktrans %}This decision support was created using an earlier purpose or process context. Generate an updated version before relying on it.{% endblocktrans %}
        """,
    ),
    r(
        """
        Combining the available evidence and preparing decision support...
        """,
        """
        {% trans "Combining the available evidence and preparing decision support…" %}
        """,
    ),
    r(
        """
        The pre-interview decision support could not be generated.
        """,
        """
        {% trans "The pre-interview decision support could not be generated." %}
        """,
    ),
    r(
        """
        Prepare the interview
        """,
        """
        {% trans "Prepare the interview" %}
        """,
    ),
    r(
        """
        Generate a synthesis of the available assessment evidence,
        cautious interpretations, discussion guidance and priority
        validation questions.
        """,
        """
        {% blocktrans %}Generate a synthesis of the available assessment evidence, cautious interpretations, discussion guidance and priority validation questions.{% endblocktrans %}
        """,
    ),
    r(
        """
        Generate decision support
        """,
        """
        {% trans "Generate decision support" %}
        """,
    ),

    # ---------------------------------------------------------
    # Pre-interview generated content
    # ---------------------------------------------------------
    r(
        """
        Overall synthesis
        """,
        """
        {% trans "Overall synthesis" %}
        """,
    ),
    r(
        """
        Purpose-relevant indications
        """,
        """
        {% trans "Purpose-relevant indications" %}
        """,
    ),
    r(
        """
        Assessment indications that may be particularly relevant
        to the purpose and context of this process.
        """,
        """
        {% blocktrans %}Assessment indications that may be particularly relevant to the purpose and context of this process.{% endblocktrans %}
        """,
    ),
    r(
        """
        No purpose-relevant indications were identified from
        the available assessment evidence.
        """,
        """
        {% blocktrans %}No purpose-relevant indications were identified from the available assessment evidence.{% endblocktrans %}
        """,
    ),
    r(
        """
        What requires cautious interpretation
        """,
        """
        {% trans "What requires cautious interpretation" %}
        """,
    ),
    r(
        """
        Assessment indications that require validation, context
        or additional behavioural evidence.
        """,
        """
        {% blocktrans %}Assessment indications that require validation, context or additional behavioural evidence.{% endblocktrans %}
        """,
    ),
    r(
        """
        Why caution is needed
        """,
        """
        {% trans "Why caution is needed" %}
        """,
    ),
    r(
        """
        No indications requiring particular caution were
        identified from the available assessment evidence.
        """,
        """
        {% blocktrans %}No indications requiring particular caution were identified from the available assessment evidence.{% endblocktrans %}
        """,
    ),
    r(
        """
        How to approach the discussion
        """,
        """
        {% trans "How to approach the discussion" %}
        """,
    ),
    r(
        """
        Suggestions for discussing the profile constructively
        and collecting relevant behavioural evidence.
        """,
        """
        {% blocktrans %}Suggestions for discussing the profile constructively and collecting relevant behavioural evidence.{% endblocktrans %}
        """,
    ),
    r(
        """
        Feedback approach
        """,
        """
        {% trans "Feedback approach" %}
        """,
    ),
    r(
        """
        Interview focus
        """,
        """
        {% trans "Interview focus" %}
        """,
    ),
    r(
        """
        Priority questions
        """,
        """
        {% trans "Priority questions" %}
        """,
    ),
    r(
        """
        Questions selected to validate, challenge or add
        context to the overall assessment picture.
        """,
        """
        {% blocktrans %}Questions selected to validate, challenge or add context to the overall assessment picture.{% endblocktrans %}
        """,
    ),
    r(
        """
        {{ pre_interview_decision_support.validation_questions|length }}
        question{{ pre_interview_decision_support.validation_questions|length|pluralize }}
        """,
        """
        {% blocktrans count question_count=pre_interview_decision_support.validation_questions|length %}
          {{ question_count }} question
        {% plural %}
          {{ question_count }} questions
        {% endblocktrans %}
        """,
    ),
    r(
        """
        Why this matters
        """,
        """
        {% trans "Why this matters" %}
        """,
    ),
    r(
        """
        What to look for in the answer
        """,
        """
        {% trans "What to look for in the answer" %}
        """,
    ),
    r(
        """
        Evidence still missing
        """,
        """
        {% trans "Evidence still missing" %}
        """,
    ),
    r(
        """
        Decision support, not a decision
        """,
        """
        {% trans "Decision support, not a decision" %}
        """,
    ),
    r(
        """
        Talena organises and interprets available evidence but does
        not determine whether the candidate should be selected,
        rejected, promoted or placed in a role.
        """,
        """
        {% blocktrans %}Talena organises and interprets available evidence but does not determine whether the candidate should be selected, rejected, promoted or placed in a role.{% endblocktrans %}
        """,
    ),

    # ---------------------------------------------------------
    # Interview notes
    # ---------------------------------------------------------
    r(
        """
        Add interview evidence
        """,
        """
        {% trans "Add interview evidence" %}
        """,
    ),
    r(
        """
        Add relevant interview notes, behavioural examples and
        candidate reflections. Talena will compare this evidence
        with the assessment indications.
        """,
        """
        {% blocktrans %}Add relevant interview notes, behavioural examples and candidate reflections. Talena will compare this evidence with the assessment indications.{% endblocktrans %}
        """,
    ),
    r(
        """
        Interview notes and candidate examples
        """,
        """
        {% trans "Interview notes and candidate examples" %}
        """,
    ),
    r(
        """
        Include relevant examples, working methods, context and
        answers that may support, challenge or add nuance to the
        assessment profile.
        """,
        """
        {% blocktrans %}Include relevant examples, working methods, context and answers that may support, challenge or add nuance to the assessment profile.{% endblocktrans %}
        """,
    ),
    r(
        """
        Last saved {{ interview_notes_updated_at|date:"j M Y, H:i" }}
        """,
        """
        {% blocktrans with saved_at=interview_notes_updated_at|date:"j M Y, H:i" %}Last saved {{ saved_at }}{% endblocktrans %}
        """,
    ),
    r(
        'placeholder="Paste interview notes, candidate examples and relevant observations here..."',
        'placeholder="{% trans \'Paste interview notes, candidate examples and relevant observations here…\' %}"',
    ),
    r(
        """
        {{ interview_notes|length }} / 30,000 characters
        """,
        """
        {% blocktrans with character_count=interview_notes|length %}{{ character_count }} / 30,000 characters{% endblocktrans %}
        """,
    ),
    r(
        """
        Save interview notes
        """,
        """
        {% trans "Save interview notes" %}
        """,
    ),
    r(
        """
        The interview notes could not be saved.
        """,
        """
        {% trans "The interview notes could not be saved." %}
        """,
    ),

    # ---------------------------------------------------------
    # Post-interview header and states
    # ---------------------------------------------------------
    r(
        """
        Post-interview decision support
        """,
        """
        {% trans "Post-interview decision support" %}
        """,
    ),
    r(
        """
        Compares the assessment indications with the saved interview
        evidence, candidate examples and interviewer observations.
        """,
        """
        {% blocktrans %}Compares the assessment indications with the saved interview evidence, candidate examples and interviewer observations.{% endblocktrans %}
        """,
    ),
    r(
        'title="Generate updated post-interview decision support"',
        'title="{% trans \'Generate updated post-interview decision support\' %}"',
    ),
    r(
        'aria-label="Generate updated post-interview decision support"',
        'aria-label="{% trans \'Generate updated post-interview decision support\' %}"',
    ),
    r(
        """
        The interview evidence has changed
        """,
        """
        {% trans "The interview evidence has changed" %}
        """,
    ),
    r(
        """
        This synthesis was generated using an earlier version of
        the interview notes or process information. Generate an
        updated version before relying on it.
        """,
        """
        {% blocktrans %}This synthesis was generated using an earlier version of the interview notes or process information. Generate an updated version before relying on it.{% endblocktrans %}
        """,
    ),
    r(
        """
        Comparing the assessment evidence with the interview notes...
        """,
        """
        {% trans "Comparing the assessment evidence with the interview notes…" %}
        """,
    ),
    r(
        """
        The post-interview decision support could not be generated.
        """,
        """
        {% trans "The post-interview decision support could not be generated." %}
        """,
    ),
    r(
        """
        Post-interview synthesis
        """,
        """
        {% trans "Post-interview synthesis" %}
        """,
    ),
    r(
        """
        The interview evidence has been saved. Generate a synthesis
        to compare it with the assessment indications and identify
        remaining uncertainties.
        """,
        """
        {% blocktrans %}The interview evidence has been saved. Generate a synthesis to compare it with the assessment indications and identify remaining uncertainties.{% endblocktrans %}
        """,
    ),
    r(
        """
        Generate post-interview decision support
        """,
        """
        {% trans "Generate post-interview decision support" %}
        """,
    ),
    r(
        """
        Add and save interview evidence before generating the
        post-interview synthesis.
        """,
        """
        {% blocktrans %}Add and save interview evidence before generating the post-interview synthesis.{% endblocktrans %}
        """,
    ),

    # ---------------------------------------------------------
    # Post-interview generated content
    # ---------------------------------------------------------
    r(
        """
        Evidence supporting assessment indications
        """,
        """
        {% trans "Evidence supporting assessment indications" %}
        """,
    ),
    r(
        """
        Interview evidence that supports patterns identified
        in the assessment results.
        """,
        """
        {% blocktrans %}Interview evidence that supports patterns identified in the assessment results.{% endblocktrans %}
        """,
    ),
    r(
        """
        Assessment indication
        """,
        """
        {% trans "Assessment indication" %}
        """,
    ),
    r(
        """
        Interview evidence
        """,
        """
        {% trans "Interview evidence" %}
        """,
    ),
    r(
        """
        Combined interpretation
        """,
        """
        {% trans "Combined interpretation" %}
        """,
    ),
    r(
        """
        No assessment indications received sufficient support
        from the available interview evidence.
        """,
        """
        {% blocktrans %}No assessment indications received sufficient support from the available interview evidence.{% endblocktrans %}
        """,
    ),
    r(
        """
        What the interview adds or nuances
        """,
        """
        {% trans "What the interview adds or nuances" %}
        """,
    ),
    r(
        """
        Areas where the interview adds context or suggests
        a more nuanced interpretation.
        """,
        """
        {% blocktrans %}Areas where the interview adds context or suggests a more nuanced interpretation.{% endblocktrans %}
        """,
    ),
    r(
        """
        No additional nuance was identified from the
        available interview evidence.
        """,
        """
        {% blocktrans %}No additional nuance was identified from the available interview evidence.{% endblocktrans %}
        """,
    ),
    r(
        """
        Contradictions or tensions to consider
        """,
        """
        {% trans "Contradictions or tensions to consider" %}
        """,
    ),
    r(
        """
        These differences should be explored rather than resolved
        automatically in favour of either source.
        """,
        """
        {% blocktrans %}These differences should be explored rather than resolved automatically in favour of either source.{% endblocktrans %}
        """,
    ),
    r(
        """
        Assessment evidence:
        """,
        """
        {% trans "Assessment evidence:" %}
        """,
    ),
    r(
        """
        Interview evidence:
        """,
        """
        {% trans "Interview evidence:" %}
        """,
    ),
    r(
        """
        What remains to be explored
        """,
        """
        {% trans "What remains to be explored" %}
        """,
    ),
    r(
        """
        Areas where additional evidence may help the responsible
        decision-maker form a more complete judgement.
        """,
        """
        {% blocktrans %}Areas where additional evidence may help the responsible decision-maker form a more complete judgement.{% endblocktrans %}
        """,
    ),
    r(
        """
        Remaining uncertainties
        """,
        """
        {% trans "Remaining uncertainties" %}
        """,
    ),
    r(
        """
        Suggested follow-up
        """,
        """
        {% trans "Suggested follow-up" %}
        """,
    ),
)


def normalise_key(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.strip(),
    )


def flexible_replace(
    text: str,
    replacement: Replacement,
) -> tuple[str, int]:
    """
    Replace exact text first.

    If formatting or line wrapping differs, retry while treating
    whitespace as flexible. Non-whitespace characters must still
    appear in the same order.
    """
    exact_count = text.count(replacement.old)

    if exact_count:
        return (
            text.replace(
                replacement.old,
                replacement.new,
            ),
            exact_count,
        )

    source = replacement.old.strip()

    if not source:
        return text, 0

    tokens = re.split(
        r"\s+",
        source,
    )

    pattern = re.compile(
        r"\s+".join(
            re.escape(token)
            for token in tokens
        )
    )

    return pattern.subn(
        replacement.new,
        text,
    )


def add_i18n_preamble(text: str) -> str:
    if MARKER in text:
        raise RuntimeError(
            "The Final Output template i18n batch "
            "has already been applied."
        )

    if "{% load i18n %}" in text:
        return text.replace(
            "{% load i18n %}",
            "{% load i18n %}\n" + MARKER,
            1,
        )

    return (
        "{% load i18n %}\n"
        + MARKER
        + "\n"
        + text
    )


def validate_translation_blocks(text: str) -> None:
    """
    Django does not allow trans/blocktrans tags inside blocktrans.
    """
    block_pattern = re.compile(
        r"{%\\s*blocktrans\\b.*?%}(.*?){%\\s*endblocktrans\\s*%}",
        re.DOTALL,
    )

    for match in block_pattern.finditer(text):
        body = match.group(1)

        if re.search(
            r"{%\\s*(?:trans|blocktrans)\\b",
            body,
        ):
            line_number = (
                text.count(
                    "\\n",
                    0,
                    match.start(),
                )
                + 1
            )

            raise RuntimeError(
                "Nested translation tag found inside "
                f"blocktrans near line {line_number}."
            )


def transform(text: str) -> tuple[str, list[str]]:
    """
    Transform the original template using placeholders.

    The placeholders are expanded only after every source string has
    been located. This prevents a short translation such as
    "Interview evidence" from being inserted inside a blocktrans
    created for a longer sentence.
    """
    working = text
    notes: list[str] = []

    ordered = sorted(
        REPLACEMENTS,
        key=lambda item: len(item.old),
        reverse=True,
    )

    unique: list[Replacement] = []
    seen: dict[str, str] = {}

    for replacement in ordered:
        source_key = normalise_key(
            replacement.old
        )
        target_key = normalise_key(
            replacement.new
        )

        previous_target = seen.get(
            source_key
        )

        if previous_target is not None:
            if previous_target != target_key:
                raise RuntimeError(
                    "Conflicting replacement targets "
                    f"for {source_key!r}."
                )
            continue

        seen[source_key] = target_key
        unique.append(replacement)

    placeholders: dict[str, str] = {}

    for index, replacement in enumerate(
        unique,
        start=1,
    ):
        placeholder = (
            f"__TALENA_FINAL_OUTPUT_I18N_{index:04d}__"
        )

        placeholder_replacement = Replacement(
            old=replacement.old,
            new=placeholder,
            minimum=replacement.minimum,
        )

        working, count = flexible_replace(
            working,
            placeholder_replacement,
        )

        if count < replacement.minimum:
            raise RuntimeError(
                "Expected text was not found:\n\n"
                + replacement.old[:500]
            )

        placeholders[placeholder] = replacement.new

        notes.append(
            f"Replaced {count} occurrence(s): "
            f"{normalise_key(replacement.old)[:90]}"
        )

    updated = add_i18n_preamble(
        working
    )

    for placeholder, translated_markup in placeholders.items():
        updated = updated.replace(
            placeholder,
            translated_markup,
        )

    unresolved = [
        placeholder
        for placeholder in placeholders
        if placeholder in updated
    ]

    if unresolved:
        raise RuntimeError(
            "Unresolved translation placeholders remain: "
            + ", ".join(unresolved[:5])
        )

    validate_translation_blocks(
        updated
    )

    if updated == text:
        raise RuntimeError(
            "No changes were produced."
        )

    return updated, notes


def main() -> int:
    parser = argparse.ArgumentParser()

    mode = parser.add_mutually_exclusive_group(
        required=True
    )

    mode.add_argument(
        "--check",
        action="store_true",
        help="Validate all replacements without writing.",
    )

    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply the validated replacements.",
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
            f"Missing template: {TARGET_PATH}"
        )

    backup = target.with_suffix(
        target.suffix
        + ".bak-final-output-i18n"
    )

    current = target.read_text(
        encoding="utf-8"
    )

    if backup.exists():
        original = backup.read_text(
            encoding="utf-8"
        )
        source_description = backup.relative_to(
            root
        )
    elif MARKER in current:
        raise RuntimeError(
            "The current template has already been modified, "
            "but the original backup is missing."
        )
    else:
        original = current
        source_description = target.relative_to(
            root
        )

    updated, notes = transform(
        original
    )

    print(
        f"Source used: {source_description}"
    )

    print(
        f"Validated {len(notes)} translation operations "
        f"for {TARGET_PATH}."
    )

    for note in notes:
        print(f"  - {note}")

    if args.check:
        print(
            "\nCHECK OK: no files were changed."
        )
        return 0

    temporary = target.with_suffix(
        target.suffix
        + ".tmp-final-output-i18n"
    )

    broken_copy = target.with_suffix(
        target.suffix
        + ".broken-final-output-i18n"
    )

    if MARKER in current and not broken_copy.exists():
        shutil.copy2(
            target,
            broken_copy,
        )

    if not backup.exists():
        shutil.copy2(
            target,
            backup,
        )

    temporary.write_text(
        updated,
        encoding="utf-8",
    )

    temporary.replace(
        target
    )

    print(
        "\nAPPLY OK: Final Output template "
        "is now connected to Django i18n."
    )
    print(
        f"Backup: {backup.relative_to(root)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
