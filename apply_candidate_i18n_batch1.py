#!/usr/bin/env python3
'''
Apply Talena candidate-view i18n batch 1 safely.

This script performs targeted, verified string replacements only.
It does not reformat or replace entire templates.

Run from the repository root:

    python apply_candidate_i18n_batch1.py --check
    python apply_candidate_i18n_batch1.py --apply
'''

from __future__ import annotations

import argparse
import re
import shutil
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path


MARKER = "{# Talena candidate i18n batch 1 #}"


@dataclass(frozen=True)
class Replacement:
    old: str
    new: str
    minimum: int = 1


@dataclass(frozen=True)
class FilePlan:
    path: str
    preamble: str
    replacements: tuple[Replacement, ...]


def r(old: str, new: str, minimum: int = 1) -> Replacement:
    return Replacement(old=old, new=new, minimum=minimum)


PLANS = (
    FilePlan(
        path="templates/customer/processes/_candidate_detail_sheet.html",
        preamble='''{% trans "Candidate" as candidate_fallback %}
{% trans "Copied!" as candidate_js_copied %}
{% trans "Could not copy." as candidate_js_could_not_copy %}
''',
        replacements=(
            r('{{ candidate.email|default:"Candidate" }}', '{{ candidate.email|default:candidate_fallback }}'),
            r('<span class="candidate-status-badge is-muted">Historical</span>', '<span class="candidate-status-badge is-muted">{% trans "Historical" %}</span>'),
            r('<span class="candidate-status-badge is-success">Completed</span>', '<span class="candidate-status-badge is-success">{% trans "Completed" %}</span>'),
            r('<span class="candidate-status-badge is-info">Started</span>', '<span class="candidate-status-badge is-info">{% trans "Started" %}</span>'),
            r('<span class="candidate-status-badge is-warning">Sent</span>', '<span class="candidate-status-badge is-warning">{% trans "Sent" %}</span>'),
            r('<span class="candidate-status-badge is-muted">Not sent</span>', '<span class="candidate-status-badge is-muted">{% trans "Not sent" %}</span>'),
            r('<span class="candidate-status-badge is-muted">Imported SOVA data</span>', '<span class="candidate-status-badge is-muted">{% trans "Imported SOVA data" %}</span>'),
            r('aria-label="Candidate header tabs"', 'aria-label="{% trans \'Candidate header tabs\' %}"'),
            r('                  Overview', '                  {% trans "Overview" %}'),
            r('                  Sent assessments', '                  {% trans "Sent assessments" %}'),
            r('                  Assessment link', '                  {% trans "Assessment link" %}'),
            r('                  Activity', '                  {% trans "Activity" %}'),
            r('<div class="candidate-overview-label">Invited</div>', '<div class="candidate-overview-label">{% trans "Invited" %}</div>'),
            r('<div class="candidate-overview-label">Completed</div>', '<div class="candidate-overview-label">{% trans "Completed" %}</div>'),
            r('                        Not completed', '                        {% trans "Not completed" %}'),
            r('<div class="candidate-overview-label">Assessments sent</div>', '<div class="candidate-overview-label">{% trans "Assessments sent" %}</div>'),
            r('<div class="candidate-overview-label">Assessments completed</div>', '<div class="candidate-overview-label">{% trans "Assessments completed" %}</div>'),
            r('<div class="candidate-inline-meta">Assessment included in this test process</div>', '<div class="candidate-inline-meta">{% trans "Assessment included in this test process" %}</div>'),
            r('<span class="candidate-status-badge is-warning">Not started</span>', '<span class="candidate-status-badge is-warning">{% trans "Not started" %}</span>'),
            r('<div class="text-muted small">No assessments found yet.</div>', '<div class="text-muted small">{% trans "No assessments found yet." %}</div>'),
            r('<div class="candidate-inline-title">Assessment link</div>', '<div class="candidate-inline-title">{% trans "Assessment link" %}</div>'),
            r('<div class="candidate-inline-meta">Click to highlight the link, or press Copy.</div>', '<div class="candidate-inline-meta">{% trans "Click to highlight the link, or press Copy." %}</div>'),
            r('                        Copy', '                        {% trans "Copy" %}'),
            r('<div class="text-muted small">No assessment link available yet.</div>', '<div class="text-muted small">{% trans "No assessment link available yet." %}</div>'),
            r('                              View email', '                              {% trans "View email" %}'),
            r('<div class="activity-empty-title">No activity yet</div>', '<div class="activity-empty-title">{% trans "No activity yet" %}</div>'),
            r(
                '''                        Events will appear here when invitations are sent and assessments are started or completed.''',
                '''                        {% blocktrans %}Events will appear here when invitations are sent and assessments are started or completed.{% endblocktrans %}'''
            ),
            r('             Ask about', '             {% trans "Ask about" %}'),
            r('               this candidate', '               {% trans "this candidate" %}'),
            r('          aria-label="Close Talena AI"', '          aria-label="{% trans \'Close Talena AI\' %}"'),
            r(
                '            The assistant uses imported assessment data and general insight mode.',
                '            {% trans "The assistant uses imported assessment data and general insight mode." %}'
            ),
            r('               Ask Talena AI', '               {% trans "Ask Talena AI" %}'),
            r(
                '               Ask about strengths, areas to explore or interview questions.',
                '               {% trans "Ask about strengths, areas to explore or interview questions." %}'
            ),
            r('             Ask Talena AI about the candidate', '             {% trans "Ask Talena AI about the candidate" %}'),
            r('               placeholder="Ask a question about this candidate..."', '               placeholder="{% trans \'Ask a question about this candidate...\' %}"'),
            r('               aria-label="Send question"', '               aria-label="{% trans \'Send question\' %}"'),
            r('       aria-label="Open Talena AI"', '       aria-label="{% trans \'Open Talena AI\' %}"'),
            r('         Ask Talena AI', '         {% trans "Ask Talena AI" %}'),
            r('buttonEl.innerText = "Copied!";', 'buttonEl.innerText = "{{ candidate_js_copied|escapejs }}";'),
            r('buttonEl.innerText = "Could not copy";', 'buttonEl.innerText = "{{ candidate_js_could_not_copy|escapejs }}";'),
        ),
    ),
    FilePlan(
        path="templates/customer/processes/partials/candidate_insights/_workspace.html",
        preamble='''{% trans "context" as context_fallback %}
{% trans "Add context" as add_context_fallback %}
''',
        replacements=(
            r('             Improve candidate insights', '             {% trans "Improve candidate insights" %}'),
            r('{{ context_config.tab_label|default:"context"|lower }}', '{{ context_config.tab_label|default:context_fallback|lower }}'),
            r(
                '''            Add context to make the candidate insights more relevant
            to this process.''',
                '''            {% blocktrans %}Add context to make the candidate insights more relevant to this process.{% endblocktrans %}'''
            ),
            r('{{ context_config.add_cta|default:"Add context" }}', '{{ context_config.add_cta|default:add_context_fallback }}'),
            r('       No results yet', '       {% trans "No results yet" %}'),
            r(
                '''       Candidate insights will appear here when assessment data
       becomes available.''',
                '''       {% blocktrans %}Candidate insights will appear here when assessment data becomes available.{% endblocktrans %}'''
            ),
            r('       Candidate insights are not available yet', '       {% trans "Candidate insights are not available yet" %}'),
            r(
                '''       The candidate insights will appear when all assessments
       included in the process have been completed.''',
                '''       {% blocktrans %}The candidate insights will appear when all assessments included in the process have been completed.{% endblocktrans %}'''
            ),
            r('           Reports', '           {% trans "Reports" %}'),
            r('{{ historical_reports|length }} available', '{{ historical_reports|length }} {% trans "available" %}'),
            r('{{ sova_reports_for_ui|length }} available', '{{ sova_reports_for_ui|length }} {% trans "available" %}'),
            r('                     Uploaded historical assessment report', '                     {% trans "Uploaded historical assessment report" %}'),
            r('                     Open report', '                     {% trans "Open report" %}'),
            r('                 No historical reports have been uploaded.', '                 {% trans "No historical reports have been uploaded." %}'),
            r('                   Open report', '                   {% trans "Open report" %}'),
            r('                 No assessment reports are currently available.', '                 {% trans "No assessment reports are currently available." %}'),
        ),
    ),
    FilePlan(
        path="templates/customer/processes/partials/candidate_insights/_navigation.html",
        preamble="",
        replacements=(
            r('aria-label="Candidate insight areas"', 'aria-label="{% trans \'Candidate insight areas\' %}"'),
            r('        Summary', '        {% trans "Summary" %}'),
            r('        Personality', '        {% trans "Personality" %}'),
            r('        Motivation', '        {% trans "Motivation" %}'),
            r('        Cognitive abilities', '        {% trans "Cognitive abilities" %}'),
            r('        Team styles', '        {% trans "Team styles" %}'),
            r('        Questions', '        {% trans "Questions" %}'),
            r('        Final output', '        {% trans "Final output" %}'),
        ),
    ),
    FilePlan(
        path="templates/customer/processes/partials/candidate_insights/_global_ai_update.html",
        preamble="",
        replacements=(
            r('         Process information has changed', '         {% trans "Process information has changed" %}'),
            r(
                '''         The process purpose and/or context have changed since
         some AI insights were generated. Update them to reflect
         the latest information.''',
                '''         {% blocktrans %}The process purpose and/or context have changed since some AI insights were generated. Update them to reflect the latest information.{% endblocktrans %}'''
            ),
            r('         Update all AI insights', '         {% trans "Update all AI insights" %}'),
            r('             Update all AI insights?', '             {% trans "Update all AI insights?" %}'),
            r('aria-label="Close"', 'aria-label="{% trans \'Close\' %}"'),
            r('                   Existing AI-generated content will be replaced', '                   {% trans "Existing AI-generated content will be replaced" %}'),
            r(
                '''                   The affected interpretations, guidance and questions
                   will be regenerated using the current process purpose
                   and context.''',
                '''                   {% blocktrans %}The affected interpretations, guidance and questions will be regenerated using the current process purpose and context.{% endblocktrans %}'''
            ),
            r(
                '''                   {{ outdated_ai_section_count }}
                   section{{ outdated_ai_section_count|pluralize }}
                   will be updated:''',
                '''                   {% blocktrans count section_count=outdated_ai_section_count %}
                     {{ section_count }} section will be updated:
                   {% plural %}
                     {{ section_count }} sections will be updated:
                   {% endblocktrans %}'''
            ),
            r(
                '''                   Assessment results, PDF reports, interview notes and
                   other source data will not be changed.''',
                '''                   {% blocktrans %}Assessment results, PDF reports, interview notes and other source data will not be changed.{% endblocktrans %}'''
            ),
            r('                 Preparing AI insights...', '                 {% trans "Preparing AI insights…" %}'),
            r('                 0 of 0', '                 {% trans "0 of 0" %}'),
            r('aria-label="AI insight update progress"', 'aria-label="{% trans \'AI insight update progress\' %}"'),
            r('               AI insights updated', '               {% trans "AI insights updated" %}'),
            r(
                '''               The candidate insights have been updated using the latest
               process information.''',
                '''               {% blocktrans %}The candidate insights have been updated using the latest process information.{% endblocktrans %}'''
            ),
            r('             Keep existing insights', '             {% trans "Keep existing insights" %}'),
            r('             Update all AI insights', '             {% trans "Update all AI insights" %}'),
            r('             Reload candidate insights', '             {% trans "Reload candidate insights" %}'),
        ),
    ),
    FilePlan(
        path="templates/customer/processes/partials/candidate_insights/tabs/_overview.html",
        preamble="",
        replacements=(
            r('       ✨ AI-generated insight', '       ✨ {% trans "AI-generated insight" %}'),
            r('       AI Summary', '       {% trans "AI Summary" %}'),
            r(
                '''       A combined interpretation of the candidate’s available assessment
       results, selected process purpose and any added process context.''',
                '''       {% blocktrans %}A combined interpretation of the candidate’s available assessment results, selected process purpose and any added process context.{% endblocktrans %}'''
            ),
            r('         Needs update', '         {% trans "Needs update" %}'),
            r('title="Generate a new overview using the latest assessment results, purpose and process context."', 'title="{% trans \'Generate a new overview using the latest assessment results, purpose and process context.\' %}"'),
            r('aria-label="Generate a new AI overview"', 'aria-label="{% trans \'Generate a new AI overview\' %}"'),
            r('               Analysing assessment results and process context...', '               {% trans "Analysing assessment results and process context…" %}'),
            r('       Overall interpretation', '       {% trans "Overall interpretation" %}'),
            r('<span>What supports the purpose</span>', '<span>{% trans "What supports the purpose" %}</span>'),
            r('title="Assessment patterns that may be relevant to and support the selected purpose. They are not guarantees of performance."', 'title="{% trans \'Assessment patterns that may be relevant to and support the selected purpose. They are not guarantees of performance.\' %}"'),
            r('aria-label="More information about supporting evidence"', 'aria-label="{% trans \'More information about supporting evidence\' %}"'),
            r('<span>What to explore or consider</span>', '<span>{% trans "What to explore or consider" %}</span>'),
            r('title="Topics that may be useful to explore, consider or follow up through relevant conversations or other evidence. They are not confirmed weaknesses."', 'title="{% trans \'Topics that may be useful to explore, consider or follow up through relevant conversations or other evidence. They are not confirmed weaknesses.\' %}"'),
            r('aria-label="More information about areas to explore"', 'aria-label="{% trans \'More information about areas to explore\' %}"'),
            r('     How Talena created this summary', '     {% trans "How Talena created this summary" %}'),
            r('         Based on', '         {% trans "Based on" %}'),
            r('         Assessment results', '         {% trans "Assessment results" %}'),
            r('         Selected purpose', '         {% trans "Selected purpose" %}'),
            r('           Process context', '           {% trans "Process context" %}'),
            r('title="No additional process context has been added."', 'title="{% trans \'No additional process context has been added.\' %}"'),
            r('           No added context', '           {% trans "No added context" %}'),
            r(
                '''       This is an AI-generated interpretation of assessment evidence,
       not a final decision or prediction of future performance.
       Use it together with relevant conversations, experience and
       other available information.''',
                '''       {% blocktrans %}This is an AI-generated interpretation of assessment evidence, not a final decision or prediction of future performance. Use it together with relevant conversations, experience and other available information.{% endblocktrans %}'''
            ),
            r(
                '''           The purpose-fit interpretation could not be generated.
           Use the refresh button to try again.''',
                '''           {% blocktrans %}The purpose-fit interpretation could not be generated. Use the refresh button to try again.{% endblocktrans %}'''
            ),
            r('           Assessment overview', '           {% trans "Assessment overview" %}'),
            r('           No purpose-specific overview available', '           {% trans "No purpose-specific overview available" %}'),
            r(
                '''           A combined AI overview requires a specific process purpose.
           The available assessment results can still be explored through
           the Personality, Motivation, Cognitive abilities and Team styles tabs.''',
                '''           {% blocktrans %}A combined AI overview requires a specific process purpose. The available assessment results can still be explored through the Personality, Motivation, Cognitive abilities and Team styles tabs.{% endblocktrans %}'''
            ),
            r('           Imported assessment data', '           {% trans "Imported assessment data" %}'),
            r('           Historical candidate overview', '           {% trans "Historical candidate overview" %}'),
            r(
                '''           This candidate uses imported assessment data. Explore the available
           assessment areas through the tabs above.''',
                '''           {% blocktrans %}This candidate uses imported assessment data. Explore the available assessment areas through the tabs above.{% endblocktrans %}'''
            ),
        ),
    ),
    FilePlan(
        path="templates/customer/processes/partials/candidate_insights/tabs/_personality.html",
        preamble='''{% trans "No personality assessment available" as no_personality_title %}
{% trans "Include a Personality assessment in future processes to unlock a detailed trait profile, response-style guidance, team-style insights, AI-supported interpretation and tailored follow-up questions." as no_personality_description %}
{% trans "Available with Personality assessment" as personality_unlock_label %}
''',
        replacements=(
            r('aria-label="Personality insight areas"', 'aria-label="{% trans \'Personality insight areas\' %}"'),
            r('<span>Results</span>', '<span>{% trans "Results" %}</span>'),
            r('<span>Interpretation</span>', '<span>{% trans "Interpretation" %}</span>'),
            r('<span>Questions</span>', '<span>{% trans "Questions" %}</span>'),
            r('     Personality results exist, but the personality profile could not be built.', '     {% trans "Personality results exist, but the personality profile could not be built." %}'),
            r(
                '{% include "customer/processes/partials/candidate_insights/_missing_assessment.html" with missing_icon="user" missing_title="No personality assessment available" missing_description="Include a Personality assessment in future processes to unlock a detailed trait profile, response-style guidance, team-style insights, AI-supported interpretation and tailored follow-up questions." missing_unlock_label="Available with Personality assessment" %}',
                '{% include "customer/processes/partials/candidate_insights/_missing_assessment.html" with missing_icon="user" missing_title=no_personality_title missing_description=no_personality_description missing_unlock_label=personality_unlock_label %}'
            ),
        ),
    ),
    FilePlan(
        path="templates/customer/processes/partials/candidate_insights/tabs/_motivation.html",
        preamble='''{% trans "No motivation assessment available" as no_motivation_title %}
{% trans "A motivation assessment could provide additional insight into likely sources of energy, engagement and preferred working conditions." as no_motivation_description %}
''',
        replacements=(
            r('aria-label="Motivation insight areas"', 'aria-label="{% trans \'Motivation insight areas\' %}"'),
            r('<span>Results</span>', '<span>{% trans "Results" %}</span>'),
            r('<span>Interpretation</span>', '<span>{% trans "Interpretation" %}</span>'),
            r('<span>Questions</span>', '<span>{% trans "Questions" %}</span>'),
            r('           ✨ AI-generated insight', '           ✨ {% trans "AI-generated insight" %}'),
            r('           Motivation interpretation', '           {% trans "Motivation interpretation" %}'),
            r(
                '''           A practical interpretation of the motivation profile
           in relation to the selected purpose and process context.''',
                '''           {% blocktrans %}A practical interpretation of the motivation profile in relation to the selected purpose and process context.{% endblocktrans %}'''
            ),
            r('           Needs update', '           {% trans "Needs update" %}'),
            r('title="Generate a new motivation interpretation"', 'title="{% trans \'Generate a new motivation interpretation\' %}"'),
            r('aria-label="Generate a new motivation interpretation"', 'aria-label="{% trans \'Generate a new motivation interpretation\' %}"'),
            r('           Interpreting the motivation profile...', '           {% trans "Interpreting the motivation profile…" %}'),
            r('       The motivation interpretation could not be generated.', '       {% trans "The motivation interpretation could not be generated." %}'),
            r('           ✨ AI-supported questions', '           ✨ {% trans "AI-supported questions" %}'),
            r('           Motivation questions', '           {% trans "Motivation questions" %}'),
            r(
                '''           Practical questions for exploring how the motivation
           profile may appear in relevant work situations.''',
                '''           {% blocktrans %}Practical questions for exploring how the motivation profile may appear in relevant work situations.{% endblocktrans %}'''
            ),
            r('title="Generate new motivation questions"', 'title="{% trans \'Generate new motivation questions\' %}"'),
            r('aria-label="Generate new motivation questions"', 'aria-label="{% trans \'Generate new motivation questions\' %}"'),
            r('             The process information has changed', '             {% trans "The process information has changed" %}'),
            r(
                '''             These questions were generated using an earlier
             process purpose or context. Refresh them to include
             the latest information.''',
                '''             {% blocktrans %}These questions were generated using an earlier process purpose or context. Refresh them to include the latest information.{% endblocktrans %}'''
            ),
            r('           Generating motivation questions...', '           {% trans "Generating motivation questions…" %}'),
            r('       The motivation questions could not be generated.', '       {% trans "The motivation questions could not be generated." %}'),
            r('     Motivation results exist, but the motivation profile could not be built.', '     {% trans "Motivation results exist, but the motivation profile could not be built." %}'),
            r(
                '{% include "customer/processes/partials/candidate_insights/_missing_assessment.html" with missing_title="No motivation assessment available" missing_description="A motivation assessment could provide additional insight into likely sources of energy, engagement and preferred working conditions." %}',
                '{% include "customer/processes/partials/candidate_insights/_missing_assessment.html" with missing_title=no_motivation_title missing_description=no_motivation_description %}'
            ),
        ),
    ),
    FilePlan(
        path="templates/customer/processes/partials/candidate_insights/tabs/_cognitive.html",
        preamble='''{% trans "No cognitive assessment results available" as no_cognitive_title %}
{% trans "Cognitive assessments could provide additional evidence about performance on specific reasoning and problem-solving tasks." as no_cognitive_description %}
''',
        replacements=(
            r('aria-label="Cognitive insight areas"', 'aria-label="{% trans \'Cognitive insight areas\' %}"'),
            r('<span>Results</span>', '<span>{% trans "Results" %}</span>'),
            r('<span>Interpretation</span>', '<span>{% trans "Interpretation" %}</span>'),
            r('<span>Questions</span>', '<span>{% trans "Questions" %}</span>'),
            r('             ✨ AI-generated insight', '             ✨ {% trans "AI-generated insight" %}'),
            r('             Cognitive interpretation', '             {% trans "Cognitive interpretation" %}'),
            r(
                '''             A practical interpretation of the available cognitive
             results in relation to the selected purpose and process context.''',
                '''             {% blocktrans %}A practical interpretation of the available cognitive results in relation to the selected purpose and process context.{% endblocktrans %}'''
            ),
            r('             Needs update', '             {% trans "Needs update" %}'),
            r('title="Generate a new cognitive interpretation"', 'title="{% trans \'Generate a new cognitive interpretation\' %}"'),
            r('aria-label="Generate a new cognitive interpretation"', 'aria-label="{% trans \'Generate a new cognitive interpretation\' %}"'),
            r('             Interpreting the cognitive assessment results...', '             {% trans "Interpreting the cognitive assessment results…" %}'),
            r('         The cognitive interpretation could not be generated.', '         {% trans "The cognitive interpretation could not be generated." %}'),
            r('         ✨ AI-supported questions', '         ✨ {% trans "AI-supported questions" %}'),
            r('         Cognitive questions', '         {% trans "Cognitive questions" %}'),
            r(
                '''         Practical questions for exploring how the cognitive results
         may relate to relevant work situations.''',
                '''         {% blocktrans %}Practical questions for exploring how the cognitive results may relate to relevant work situations.{% endblocktrans %}'''
            ),
            r('title="Generate new cognitive questions"', 'title="{% trans \'Generate new cognitive questions\' %}"'),
            r('aria-label="Generate new cognitive questions"', 'aria-label="{% trans \'Generate new cognitive questions\' %}"'),
            r('         Generating cognitive questions...', '         {% trans "Generating cognitive questions…" %}'),
            r('     The cognitive questions could not be generated.', '     {% trans "The cognitive questions could not be generated." %}'),
            r(
                '{% include "customer/processes/partials/candidate_insights/_missing_assessment.html" with missing_title="No cognitive assessment results available" missing_description="Cognitive assessments could provide additional evidence about performance on specific reasoning and problem-solving tasks." %}',
                '{% include "customer/processes/partials/candidate_insights/_missing_assessment.html" with missing_title=no_cognitive_title missing_description=no_cognitive_description %}'
            ),
        ),
    ),
    FilePlan(
        path="templates/customer/processes/partials/candidate_insights/tabs/_team_styles.html",
        preamble='''{% trans "No team-style profile available" as no_team_style_title %}
{% trans "Team-style insights are generated from the Personality assessment. Include it in future processes to explore how the candidate may contribute, communicate, build trust and collaborate within a team." as no_team_style_description %}
{% trans "Available with Personality assessment" as team_style_unlock_label %}
''',
        replacements=(
            r(
                '{% include "customer/processes/partials/candidate_insights/_missing_assessment.html" with missing_icon="users" missing_title="No team-style profile available" missing_description="Team-style insights are generated from the Personality assessment. Include it in future processes to explore how the candidate may contribute, communicate, build trust and collaborate within a team." missing_unlock_label="Available with Personality assessment" %}',
                '{% include "customer/processes/partials/candidate_insights/_missing_assessment.html" with missing_icon="users" missing_title=no_team_style_title missing_description=no_team_style_description missing_unlock_label=team_style_unlock_label %}'
            ),
        ),
    ),
    FilePlan(
        path="templates/customer/processes/partials/candidate_insights/tabs/_questions.html",
        preamble="",
        replacements=(
            r('   All assessment questions', '   {% trans "All assessment questions" %}'),
            r(
                '''   This page brings together all saved questions from Personality,
   Motivation and Cognitive in one place. The same questions are also
   available inside each assessment category.''',
                '''   {% blocktrans %}This page brings together all saved questions from Personality, Motivation and Cognitive in one place. The same questions are also available inside each assessment category.{% endblocktrans %}'''
            ),
            r(
                '''        {{ combined_question_count }}
        question{{ combined_question_count|pluralize }}''',
                '''        {% blocktrans count question_count=combined_question_count %}
          {{ question_count }} question
        {% plural %}
          {{ question_count }} questions
        {% endblocktrans %}'''
            ),
            r('             How to use these questions', '             {% trans "How to use these questions" %}'),
            r(
                '''             Use the questions to explore assessment indications through
             concrete examples, reflections and practical experience.
             They should support a structured conversation rather than
             replace professional judgement.''',
                '''             {% blocktrans %}Use the questions to explore assessment indications through concrete examples, reflections and practical experience. They should support a structured conversation rather than replace professional judgement.{% endblocktrans %}'''
            ),
            r(
                '''    {{ section.question_count }}
    question{{ section.question_count|pluralize }}''',
                '''    {% blocktrans count question_count=section.question_count %}
      {{ question_count }} question
    {% plural %}
      {{ question_count }} questions
    {% endblocktrans %}'''
            ),
            r('                             Why this matters', '                             {% trans "Why this matters" %}'),
            r('                             What to listen for', '                             {% trans "What to listen for" %}'),
            r(
                '''   These questions bring together the currently saved question sets
   from the available assessment areas. Use them to explore and
   validate assessment indications rather than as standalone evidence.''',
                '''   {% blocktrans %}These questions bring together the currently saved question sets from the available assessment areas. Use them to explore and validate assessment indications rather than as standalone evidence.{% endblocktrans %}'''
            ),
            r('         No assessment questions are available yet', '         {% trans "No assessment questions are available yet" %}'),
            r(
                '''   This page brings together the candidate’s currently saved questions
   from Personality, Motivation and Cognitive abilities. Questions can
   be changed or regenerated within each assessment category.''',
                '''   {% blocktrans %}This page brings together the candidate’s currently saved questions from Personality, Motivation and Cognitive abilities. Questions can be changed or regenerated within each assessment category.{% endblocktrans %}'''
            ),
        ),
    ),
)


def ensure_i18n_and_marker(text: str, preamble: str) -> str:
    if MARKER in text:
        return text

    load_line = "{% load i18n %}"
    if load_line not in text:
        text = load_line + "\n" + text

    insertion = load_line + "\n" + MARKER + "\n"
    if preamble:
        insertion += preamble

    text = text.replace(load_line + "\n", insertion, 1)
    return text



def _flexible_replace(
    text: str,
    replacement: Replacement,
) -> tuple[str, int]:
    """
    Replace exact text first. If formatting differs, retry while treating
    whitespace and line wrapping as flexible.

    The fallback still requires all non-whitespace characters from the
    expected source text to appear in the same order.
    """
    exact_count = text.count(replacement.old)

    if exact_count:
        return (
            text.replace(replacement.old, replacement.new),
            exact_count,
        )

    source = replacement.old.strip()

    if not source:
        return text, 0

    tokens = re.split(r"\s+", source)
    flexible_source = r"\s+".join(
        re.escape(token)
        for token in tokens
    )

    starts_as_indented_line = (
        replacement.old[:1].isspace()
    )

    if starts_as_indented_line:
        pattern = re.compile(
            r"(?m)^([ \t]*)"
            + flexible_source
            + r"[ \t]*$"
        )

        replacement_body = textwrap.dedent(
            replacement.new
        ).strip("\n")

        def replace_indented(match: re.Match[str]) -> str:
            base_indent = match.group(1)

            return "\n".join(
                (
                    base_indent + line
                    if line
                    else ""
                )
                for line in replacement_body.splitlines()
            )

        return pattern.subn(replace_indented, text)

    pattern = re.compile(flexible_source)
    return pattern.subn(
        lambda _match: replacement.new,
        text,
    )


def transform_file(
    root: Path,
    plan: FilePlan,
) -> tuple[Path, str, str, list[str]] | None:
    path = root / plan.path

    if not path.exists():
        raise FileNotFoundError(
            f"Missing file: {plan.path}"
        )

    original = path.read_text(encoding="utf-8")

    if MARKER in original:
        print(f"SKIP already applied: {plan.path}")
        return None

    updated = ensure_i18n_and_marker(
        original,
        plan.preamble,
    )

    notes: list[str] = []

    # Process longer source strings first so a short phrase cannot
    # modify part of a longer sentence that is translated later.
    ordered_replacements = sorted(
        plan.replacements,
        key=lambda item: len(item.old),
        reverse=True,
    )

    # Some visible phrases occur more than once with different indentation.
    # A single flexible replacement can update every occurrence, so duplicate
    # source patterns must not be treated as separate mandatory operations.
    unique_replacements = []
    seen_sources = {}

    for replacement in ordered_replacements:
        source_key = re.sub(
            r"\s+",
            " ",
            replacement.old.strip(),
        )
        target_key = re.sub(
            r"\s+",
            " ",
            replacement.new.strip(),
        )

        previous_target = seen_sources.get(source_key)

        if previous_target is not None:
            if previous_target != target_key:
                raise RuntimeError(
                    "Conflicting translations were configured for "
                    f"{source_key!r} in {plan.path}"
                )

            continue

        seen_sources[source_key] = target_key
        unique_replacements.append(replacement)

    for replacement in unique_replacements:
        updated, count = _flexible_replace(
            updated,
            replacement,
        )

        if count < replacement.minimum:
            raise RuntimeError(
                "Expected text was not found in "
                f"{plan.path}:\n"
                f"{replacement.old[:240]}"
            )

        notes.append(
            f"{plan.path}: replaced "
            f"{count} occurrence(s)"
        )

    if updated == original:
        raise RuntimeError(
            f"No changes produced for {plan.path}"
        )

    return path, original, updated, notes


def apply_changes_atomically(
    changes: list[
        tuple[Path, str, str, list[str]]
    ],
) -> None:
    """
    Prepare all temporary files first. If a later write fails,
    restore every file already replaced from its backup.
    """
    prepared: list[
        tuple[Path, Path, Path]
    ] = []

    for path, _original, updated, _notes in changes:
        backup = path.with_suffix(
            path.suffix + ".bak-i18n-batch1"
        )
        temporary = path.with_suffix(
            path.suffix + ".tmp-i18n-batch1"
        )

        if not backup.exists():
            shutil.copy2(path, backup)

        temporary.write_text(
            updated,
            encoding="utf-8",
        )

        prepared.append(
            (path, backup, temporary)
        )

    replaced: list[
        tuple[Path, Path]
    ] = []

    try:
        for path, backup, temporary in prepared:
            temporary.replace(path)
            replaced.append((path, backup))

    except Exception:
        for path, backup in reversed(replaced):
            shutil.copy2(backup, path)

        raise

    finally:
        for _path, _backup, temporary in prepared:
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
        help="Validate without writing",
    )

    mode.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Apply changes after every file has "
            "validated successfully"
        ),
    )

    parser.add_argument(
        "--root",
        default=".",
        help=(
            "Repository root. Defaults to the "
            "current directory."
        ),
    )

    args = parser.parse_args()
    root = Path(args.root).resolve()

    changes: list[
        tuple[Path, str, str, list[str]]
    ] = []

    try:
        for plan in PLANS:
            result = transform_file(root, plan)

            if result is None:
                continue

            changes.append(result)

            for note in result[3]:
                print(note)

    except Exception as exc:
        print(
            f"\nERROR: {exc}",
            file=sys.stderr,
        )
        print(
            "Validation stopped. No template "
            "files were changed.",
            file=sys.stderr,
        )
        return 1

    if args.check:
        print(
            "\nSuccess: all expected text was "
            f"validated in {len(changes)} "
            "template file(s)."
        )
        print(
            "No template files were changed."
        )
        return 0

    try:
        apply_changes_atomically(changes)

    except Exception as exc:
        print(
            f"\nERROR while writing files: {exc}",
            file=sys.stderr,
        )
        print(
            "Files already written were restored "
            "from their backups.",
            file=sys.stderr,
        )
        return 1

    print(
        "\nSuccess: updated "
        f"{len(changes)} template file(s)."
    )
    print(
        "Backup files end with "
        ".bak-i18n-batch1"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
