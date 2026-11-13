Warning: truncated output (original token count: 94748)
Total output lines: 12950

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from apps.core.integrations.sova import SovaClient
from apps.projects.models import ProjectMeta
from apps.accounts.report_branding import get_report_branding
from .forms import TestProcessCreateForm, CandidateCreateForm
from .models import (
    TestProcess,
    Candidate,
    TestInvitation,
    SelfRegistration,
    ProcessLabel,
    HistoricalProcessCandidate,
)
from .purpose_utils import normalize_purpose_key
from apps.reports.services.candidate_insights import (
    build_general_insight_input,
    generate_general_candidate_insights,
)
from apps.reports.services.leadership_report import (
    build_leadership_report_content,
)
from apps.reports.services.derailment_report import (
    build_derailment_report_content,
)


from apps.core.utils.auth import is_admin

from apps.core.ai.decision_support import (
    create_empty_pre_interview_decision_support,
    apply_pre_interview_decision_support_event,
    stream_pre_interview_decision_support,
    save_pre_interview_decision_support,

    create_empty_post_interview_decision_support,
    apply_post_interview_decision_support_event,
    stream_post_interview_decision_support,
    save_post_interview_decision_support,
)

# Talena cognitive AI language batch 1
from apps.core.ai.cognitive_interpretation import (
    extract_cognitive_results,
    create_empty_cognitive_interpretation,
    apply_cognitive_interpretation_event,
    stream_cognitive_interpretation,
    save_cognitive_interpretation,
)

from apps.core.ai.cognitive_questions import (
    create_empty_cognitive_questions,
    apply_cognitive_questions_event,
    stream_cognitive_questions,
    save_cognitive_questions,
)

from apps.core.ai.motivation_interpretation import (
    MOTIVATION_DEFINITIONS,
    extract_motivation_results,
    create_empty_motivation_interpretation,
    apply_motivation_interpretation_event,
    stream_motivation_interpretation,
    save_motivation_interpretation,
)

from apps.core.ai.motivation_questions import (
    create_empty_motivation_questions,
    apply_motivation_questions_event,
    stream_motivation_questions,
    save_motivation_questions,
)

from apps.core.ai.response_style_guidance import (
    create_empty_response_style_guidance,
    apply_response_style_guidance_event,
    stream_response_style_guidance,
    save_response_style_guidance,
    RESPONSE_STYLE_GUIDANCE_SCHEMA_VERSION,
)

from apps.processes.services.team_styles import (
    build_team_style_profile,
)

from .services.process_recommendations import (
    PROCESS_PURPOSES,
    PURPOSE_RECOMMENDED_TESTS,
    AVAILABLE_TESTS,
    build_default_process_name,
    resolve_sova_template,
    extract_tests_from_project_name,
)

from apps.core.ai.personality_interpretation import (
    PERSONALITY_MANAGER_REPORT_THEMES,
    create_empty_personality_interpretation,
    apply_personality_interpretation_event,
    stream_personality_interpretation,
    save_personality_interpretation,
)

from apps.processes.services.candidate_insights import (
    build_candidate_insights,
)

from apps.processes.services.candidate_profile import (
    build_historical_candidate_profile,
)
from apps.processes.services.cognitive_insights import (
    build_cognitive_insight_results as _build_cognitive_insight_results,
)

from apps.processes.models import (
    HistoricalProcessCandidate,
    TestInvitation,
    TestProcess,
)

from apps.core.ai.purpose_fit import (
    purpose_supports_fit,
    build_assessment_evidence,
    create_empty_purpose_fit,
    apply_purpose_fit_event,
    generate_candidate_purpose_fit_events,
    save_candidate_purpose_fit,
)

from apps.core.ai.language import (
    ai_content_language_matches,
    get_request_ai_language,
    mark_ai_content_outdated_if_language_changed,
)

# Talena personality language batch 1

from apps.processes.services.historical_assessment_import import import_historical_assessment_file
from django.db.models import Count, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce
from apps.processes.models import HistoricalProcessCandidate
from django.contrib import messages
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.utils import IntegrityError
from apps.processes.services.process_locking import can_delete_process_safely
from apps.processes.services.project_assessment_status import (
    project_test_columns,
    attach_test_statuses,
    invitation_test_statuses,
)
from .forms import SelfRegisterForm
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _, get_language

from apps.processes.interview_config import (
    get_interview_section_config,
)
from django.views.decorators.http import require_POST
from django.core.mail import EmailMultiAlternatives
from apps.emails.models import EmailTemplate, EmailLog
from apps.emails.utils import render_placeholders
from django.core.mail import send_mail
from django.http import StreamingHttpResponse, JsonResponse
from apps.accounts.utils.org_access import get_accessible_orgunit_ids
from .purpose_context_config import get_purpose_context_config

from urllib.parse import urlparse
from django.http import HttpResponseRedirect
from django.db.models import Count, Q
from datetime import datetime, date, time

from django.http import HttpResponse
from apps.accounts.utils.permissions import filter_by_user_accounts, user_can_access_account
from apps.accounts.utils.org_access import get_effective_orgunit_permissions, user_can_view_process, user_can_edit_process, get_company_for_user
from django.http import HttpResponseForbidden

from apps.processes.services.send_tests import send_assessments_and_emails
from .purpose_context_config import get_purpose_context_config

import json
import uuid
import requests

from django.conf import settings

from apps.accounts.models import Company, CompanyMember, OrgUnit
from apps.projects.models import ProjectMeta

from apps.activity.models import ActivityEvent
from apps.activity.services import log_event, customer_visible_activity

from apps.reports.libraries.motivation.builder import (
    build_scores_by_competency,
    build_practitioner_report,
    build_motivation_report,
    build_motivation_coaching_report,
    build_manager_report,
    build_candidate_report
)

from apps.core.ai.candidate_summary import (
    stream_candidate_summary,
    save_candidate_summary,
)

from apps.reports.libraries.personality.resolver import build_personality_reports_for_candidate
from apps.reports.libraries.personality.profile_contrasts import (
    build_profile_contrast_analysis,
)
from apps.reports.libraries.personality.builder import (
    build_profile_from_resolved_report,
)
from apps.reports.libraries.personality.response_styles import (
    build_response_style_results as build_localized_response_style_results,
)

# Talena personality UI and response styles language batch 1

from apps.reports.libraries.cognitive.builder import build_cognitive_reports_for_test

from .forms import TestProcessWizardCreateForm

from apps.reports.libraries.purpose.content import get_report_mode_content

from apps.processes.services.process_recommendations import (
    PROCESS_PURPOSES,
    AVAILABLE_TESTS,
    PURPOSE_RECOMMENDED_TESTS,
    resolve_sova_template,
    build_default_process_name,
)

from apps.processes.services.process_recommendations import PROCESS_PURPOSES

from .models import ProcessRoleContext
from .forms import ProcessRoleContextForm

from apps.core.ai.personality_questions import (
    extract_personality_results,
    extract_personality_question_traits,
    normalise_selected_traits,
    create_empty_personality_questions,
    apply_personality_questions_event,
    stream_personality_questions,
    save_personality_questions,
    get_personality_question_count,
    personality_questions_cover_all_traits,
)

def build_cognitive_results_for_ai_owner(
    owner,
) -> list[dict]:
    """
    Build cognitive percentile evidence for either:

    - TestInvitation
    - HistoricalProcessCandidate
    """

    process = owner.process

    # ---------------------------------------------------------
    # ACTIVE CANDIDATE
    # ---------------------------------------------------------

    if not getattr(
        process,
        "is_historical",
        False,
    ):
        return extract_cognitive_results(
            owner
        )

    # ---------------------------------------------------------
    # HISTORICAL CANDIDATE
    # ---------------------------------------------------------

    profile = build_historical_candidate_profile(
        owner
    )

    ability_results = (
        profile.get("ability_results")
        or {}
    )

    labels = {
        "logical": "Logical reasoning",
        "numerical": "Numerical reasoning",
        "verbal": "Verbal reasoning",
    }

    results = []

    for key in (
        "logical",
        "numerical",
        "verbal",
    ):
        item = ability_results.get(key)

        if not item:
            continue

        percentile = item.get("percentile")

        if percentile is None:
            percentile = item.get("value")

        if percentile is None:
            continue

        try:
            percentile = int(
                round(float(percentile))
            )
        except (TypeError, ValueError):
            continue

        percentile = max(
            0,
            min(100, percentile),
        )

        results.append(
            {
                "key": key,
                "label": labels[key],
                "percentile": percentile,
            }
        )

    return results

def build_motivation_results_for_ai_owner(
    owner,
) -> list[dict]:
    """
    Build motivation evidence for either:

    - TestInvitation
    - HistoricalProcessCandidate

    Returns the same structure expected by the
    motivation AI generators.
    """

    process = owner.process

    # ---------------------------------------------------------
    # ACTIVE CANDIDATE
    # ---------------------------------------------------------

    if not getattr(
        process,
        "is_historical",
        False,
    ):
        return extract_motivation_results(
            owner
        )

    # ---------------------------------------------------------
    # HISTORICAL CANDIDATE
    # ---------------------------------------------------------

    profile = build_historical_candidate_profile(
        owner
    )

    motivation_competencies = (
        profile.get(
            "motivation_competencies"
        )
        or []
    )

    results_by_name = {}

    for item in motivation_competencies:
        name = str(
            item.get("competency")
            or item.get("name")
            or ""
        ).strip()

        if not name:
            continue

        # Preserve the exact imported STIVE value. Rounded
        # values are only a compatibility fallback.
        raw_score = item.get(
            "stive"
        )

        if raw_score is None:
            raw_score = item.get(
                "stive_rounded"
            )

        if raw_score is None:
            raw_score = item.get(
                "score"
            )

        score = normalise_five_point_score(
            raw_score
        )

        if score is None:
            continue

        name_key = name.casefold()

        results_by_name[name_key] = {
            "name": name,
            "score": score,
            "definition": (
                MOTIVATION_DEFINITIONS.get(
                    name_key,
                    "",
                )
            ),
        }

    return list(
        results_by_name.values()
    )

# Talena cognitive results language batch 1
def build_cognitive_insight_results(
    verbal_percentile=None,
    logical_percentile=None,
    numerical_percentile=None,
):
    """Keep the existing Candidate Insights API over the shared service."""
    return _build_cognitive_insight_results(
        verbal_percentile=verbal_percentile,
        logical_percentile=logical_percentile,
        numerical_percentile=numerical_percentile,
    )


def build_response_style_results(
    personality_competencies,
):
    return build_localized_response_style_results(
        personality_competencies
    )


def build_personality_results_for_ai_owner(
    owner,
) -> list[dict]:
    """
    Build personality trait evidence for either:

    - TestInvitation
    - HistoricalProcessCandidate
    """

    process = owner.process

    # ---------------------------------------------------------
    # ACTIVE CANDIDATE
    # ---------------------------------------------------------
    if not getattr(
        process,
        "is_historical",
        False,
    ):
        return extract_personality_results(
            owner
        )

    # ---------------------------------------------------------
    # HISTORICAL CANDIDATE
    # ---------------------------------------------------------
    profile = build_historical_candidate_profile(
        owner
    )

    historical_competencies = (
        profile.get(
            "personality_competencies"
        )
        or []
    )

    excluded_competencies = {
        "social desirability",
        "fillers",
        "reliability",
        "profile spread",
        "ratings spread",
    }

    results_by_name = {}

    for item in historical_competencies:
        name = str(
            item.get("competency")
            or item.get("name")
            or ""
        ).strip()

        if not name:
            continue

        name_key = name.lower()

        if name_key in excluded_competencies:
            continue

        raw_sten = item.get(
            "sten_rounded"
        )

        if raw_sten is None:
            raw_sten = item.get(
                "sten"
            )

        # Historical imports may keep the imported STEN value
        # in the generic score field.
        if raw_sten is None:
            raw_sten = item.get(
                "score"
            )

        try:
            sten = int(
                round(float(raw_sten))
            )
        except (TypeError, ValueError):
            continue

        sten = max(
            1,
            min(10, sten),
        )

        results_by_name[name_key] = {
            "name": name,
            "sten": sten,
        }

    return list(
        results_by_name.values()
    )


def build_personality_question_traits_for_ai_owner(
    owner,
) -> list[dict]:
    """
    Return the 18 parent personality traits used by
    Personality Questions for either an active or
    historical candidate.
    """

    results = build_personality_results_for_ai_owner(
        owner
    )

    allowed_trait_keys = {
        "cooperative",
        "empathy",
        "supporting",
        "connecting",
        "dynamic",
        "influential",
        "goal focused",
        "achievement striving",
        "structured",
        "analytical",
        "complex thinking",
        "creativity",
        "adaptability",
        "straightforward",
        "status avoidance",
        "modesty",
        "resilience",
        "emotional control",
        "independence",
    }

    def normalise_trait_key(value):
        text = str(
            value or ""
        ).strip().casefold()

        for character in (
            "_",
            "-",
            "–",
            "—",
            "/",
        ):
            text = text.replace(
                character,
                " ",
            )

        return " ".join(
            text.split()
        )

    return [
        result
        for result in results
        if normalise_trait_key(
            result.get("name")
        ) in allowed_trait_keys
    ]


def build_response_styles_for_guidance_owner(
    guidance_owner,
):
    """
    Build response-style results for either:

    - TestInvitation
    - HistoricalProcessCandidate

    The AI endpoint uses this helper so it does not need to build the
    entire candidate detail context before generating guidance.
    """

    process = guidance_owner.process

    # ---------------------------------------------------------
    # HISTORICAL CANDIDATE
    # ---------------------------------------------------------
    if getattr(process, "is_historical", False):
        profile = build_historical_candidate_profile(
            guidance_owner
        )

        historical_competencies = (
            profile.get("personality_competencies")
            or []
        )

        personality_competencies = []

        for item in historical_competencies:
            personality_competencies.append({
                "competency": (
                    item.get("competency")
                    or item.get("name")
                ),
                "sten": item.get("sten"),
                "sten_rounded": item.get(
                    "sten_rounded"
                ),
                "percentile": item.get("percentile"),
                "source": "historical_import",
            })

        return build_response_style_results(
            personality_competencies
        )

    # ---------------------------------------------------------
    # ACTIVE CANDIDATE
    # ---------------------------------------------------------
    payload = guidance_owner.sova_payload or {}

    activities = list(
        guidance_owner.sova_activities
        or payload.get("activities")
        or []
    )

    if not activities:
        for phase in payload.get("phases") or []:
            activities.extend(
                phase.get("activities") or []
            )

    personality_competencies = []

    for activity in activities:
        activity_name = (
            activity.get("activity")
            or ""
        ).strip().lower()

        is_personality_activity = (
            activity_name == "personality assessment"
            or activity_name == (
                "sova personality questionnaire"
            )
            or "personality" in activity_name
        )

        if not is_personality_activity:
            continue

        for competency in (
            activity.get("competencies")
            or []
        ):
            personality_competencies.append({
                "competency": competency.get(
                    "competency"
                ),
                "sten": competency.get("sten"),
                "sten_rounded": competency.get(
                    "sten_rounded"
                ),
                "percentile": competency.get(
                    "percentile"
                ),
            })

    return build_response_style_results(
        personality_competencies
    )


def build_profile_contrast_analysis_for_guidance_owner(
    guidance_owner,
    *,
    language_code="sv",
):
    """Build contrast evidence using the same canonical profile resolver."""
    process = guidance_owner.process

    if getattr(process, "is_historical", False):
        historical_profile = build_historical_candidate_profile(
            guidance_owner
        )
        source = "historical_import"
        competencies = [
            {
                "competency": item.get("competency") or item.get("name"),
                "sten": item.get("sten"),
                "sten_rounded": item.get("sten_rounded"),
            }
            for item in (historical_profile.get("personality_competencies") or [])
        ]
        activities = [{
            "activity": "Personality Assessment",
            "competencies": competencies,
        }]
    else:
        payload = guidance_owner.sova_payload or {}
        activities = list(
            guidance_owner.sova_activities
            or payload.get("activities")
            or []
        )
        if not activities:
            for phase in payload.get("phases") or []:
                activities.extend(phase.get("activities") or [])
        source = "sova_assessment"

    personality_reports = build_personality_reports_for_candidate(
        sova_activities=activities,
    )
    resolved_report = next(
        (
            report for report in personality_reports
            if report.get("report_id") == "trait_indicator_profile"
        ),
        None,
    )
    personality_profile = (
        build_profile_from_resolved_report(
            resolved_report=resolved_report,
            language=language_code,
            include_missing_traits=False,
        )
        if resolved_report
        else None
    )
    return build_profile_contrast_analysis(
        personality_profile,
        language=language_code,
        source=source,
    )


def build_motivation_insight_section(
    mq_competencies,
    candidate_name="",
):
    """
    Build the complete motivation profile used in Candidate Insights.

    Motivation results retain precise STIVE scores from 1 to 5 for ranking and display.

    The profile:
    - preserves Sova's four motivation areas
    - shows all available motivation factors
    - identifies more prominent and less central drivers
    - does not interpret low scores as weaknesses or automatic demotivators
    """
    candidate_label = (
        (candidate_name or "").strip()
        or "The candidate"
    )

    def normalise_name(value):
        text = str(value or "").strip().lower()

        replacements = {
            "_": " ",
            "-": " ",
            "–": " ",
            "/": " ",
            "&": " and ",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return " ".join(text.split())

    def get_score(item):
        """
        Motivation uses Sova's five-point STIVE scale.

        Do not fall back to percentile or STEN here, because those values
        must not be presented as scores out of five.
        """

        for key in (
            "stive",
            "score",
            "stive_rounded",
        ):
            value = item.get(key)

            if value is None:
                continue

            try:
                score = float(value)
            except (TypeError, ValueError):
                continue

            score = max(1.0, min(5.0, score))

            return int(score) if score.is_integer() else score

        return None
    
    factor_interpretations = {
        "attachment": {
            "summary_phrase": (
                "close working relationships and a clear sense of belonging"
            ),
            "support_phrase": (
                "regular collaboration, mutual support and trusted relationships"
            ),
            "top_text": (
                "{name} is likely to gain energy from close working relationships, "
                "collaboration and a clear sense of belonging. Regular interaction, "
                "mutual support and opportunities to build strong connections with "
                "colleagues may contribute to engagement over time."
            ),
        },

        "customer_service": {
            "summary_phrase": (
                "helping customers and understanding their needs"
            ),
            "support_phrase": (
                "regular customer contact and opportunities to provide useful service"
            ),
            "top_text": (
                "{name} is likely to be motivated by understanding customer needs "
                "and providing helpful service. They may gain energy from building "
                "strong customer relationships, solving customer problems and seeing "
                "that their work creates a positive customer experience."
            ),
        },

        "work_life_balance": {
            "summary_phrase": (
                "a sustainable balance between work and life outside work"
            ),
            "support_phrase": (
                "clear boundaries, a manageable workload and a sustainable pace"
            ),
            "top_text": (
                "{name} is likely to value a sustainable balance between work and "
                "life outside work. Clear expectations, reasonable boundaries and "
                "enough flexibility to manage personal commitments may help maintain "
                "energy and engagement over time."
            ),
        },

        "people_development": {
            "summary_phrase": (
                "helping other people learn and develop"
            ),
            "support_phrase": (
                "opportunities to coach, support and develop others"
            ),
            "top_text": (
                "{name} is likely to gain energy from helping other people grow and "
                "develop. They may enjoy coaching, sharing knowledge and providing "
                "support that enables colleagues or team members to strengthen their "
                "skills and confidence."
            ),
        },

        "stability": {
            "summary_phrase": (
                "continuity, predictability and a sense of security"
            ),
            "support_phrase": (
                "clear structures, continuity and a predictable working environment"
            ),
            "top_text": (
                "{name} is likely to be motivated by continuity, predictability and "
                "a sense of security at work. Clear structures, dependable conditions "
                "and confidence about what lies ahead may support sustained engagement."
            ),
        },

        "authority": {
            "summary_phrase": (
                "influence, responsibility and opportunities to lead"
            ),
            "support_phrase": (
                "decision-making responsibility and scope to shape direction"
            ),
            "top_text": (
                "{name} is likely to be motivated by having influence and meaningful "
                "responsibility. They may gain energy from leading others, shaping "
                "direction and being trusted to make decisions that affect outcomes."
            ),
        },

        "independence": {
            "summary_phrase": (
                "freedom to make decisions and shape how work is carried out"
            ),
            "support_phrase": (
                "trust, personal ownership and freedom from unnecessary control"
            ),
            "top_text": (
                "{name} is likely to value freedom in how work is planned and carried "
                "out. They may be most engaged when trusted to make decisions, organise "
                "their own workload and use their judgement without unnecessary control."
            ),
        },

        "recognition": {
            "summary_phrase": (
                "recognition and visible appreciation for personal contribution"
            ),
            "support_phrase": (
                "clear feedback and acknowledgement of effort and results"
            ),
            "top_text": (
                "{name} is likely to appreciate visible recognition for their work "
                "and contribution. Clear feedback, praise and acknowledgement of "
                "successful performance may reinforce motivation and engagement."
            ),
        },

        "making_a_difference": {
            "summary_phrase": (
                "creating a meaningful and positive impact"
            ),
            "support_phrase": (
                "a clear purpose and visible connection between work and wider impact"
            ),
            "top_text": (
                "{name} is likely to be motivated by seeing that their work contributes "
                "to something meaningful. They may gain energy from roles where the "
                "purpose is clear and where their contribution creates a visible "
                "positive impact for others or the wider organisation."
            ),
        },

        "acquisition": {
            "summary_phrase": (
                "financial reward and tangible outcomes"
            ),
            "support_phrase": (
                "clear rewards and a visible connection between contribution and gain"
            ),
            "top_text": (
                "{name} is likely to be motivated by tangible rewards and financial "
                "outcomes. They may respond positively when strong contribution is "
                "connected to clear benefits, incentives or opportunities for material gain."
            ),
        },

        "achievement": {
            "summary_phrase": (
                "challenging goals, visible progress and achievement"
            ),
            "support_phrase": (
                "clear targets, stretching objectives and visible measures of success"
            ),
            "top_text": (
                "{name} is likely to gain energy from clear and challenging goals. "
                "They may enjoy overcoming difficulties, measuring progress and seeing "
                "that sustained effort has led to a meaningful achievement."
            ),
        },

        "quality": {
            "summary_phrase": (
                "producing accurate and high-quality work"
            ),
            "support_phrase": (
                "high standards and enough time to deliver reliable results"
            ),
            "top_text": (
                "{name} is likely to be motivated by producing work of a consistently "
                "high standard. They may take pride in accuracy, reliability and "
                "ensuring that the final result meets both expectations and agreed commitments."
            ),
        },

        "learning": {
            "summary_phrase": (
                "learning, development and building new capability"
            ),
            "support_phrase": (
                "regular opportunities to develop knowledge and learn new skills"
            ),
            "top_text": (
                "{name} is likely to gain energy from learning and developing new "
                "capabilities. Opportunities to expand their knowledge, practise new "
                "skills and continue progressing may be important for longer-term engagement."
            ),
        },

        "ethics": {
            "summary_phrase": (
                "clear ethical principles and alignment with personal values"
            ),
            "support_phrase": (
                "transparent decisions and organisational standards that align with their values"
            ),
            "top_text": (
                "{name} is likely to place considerable importance on ethical standards "
                "and personal principles. They may be most engaged in environments where "
                "decisions are transparent and organisational practices align with what "
                "they consider fair and responsible."
            ),
        },

        "commercial_focus": {
            "summary_phrase": (
                "commercial impact and measurable business value"
            ),
            "support_phrase": (
                "visible business outcomes and a clear connection between work and commercial results"
            ),
            "top_text": (
                "{name} is likely to be motivated by creating visible commercial value. "
                "They may gain energy from understanding how their work contributes to "
                "revenue, growth or other measurable business outcomes."
            ),
        },

        "curiosity": {
            "summary_phrase": (
                "exploring new information and unfamiliar questions"
            ),
            "support_phrase": (
                "opportunities to investigate, discover and solve unfamiliar problems"
            ),
            "top_text": (
                "{name} is likely to gain energy from exploring new information and "
                "understanding unfamiliar topics. They may enjoy investigating questions, "
                "discovering new perspectives and solving problems that stimulate their interest."
            ),
        },

        "creativity": {
            "summary_phrase": (
                "generating ideas and finding original solutions"
            ),
            "support_phrase": (
                "room to experiment, challenge established approaches and develop new ideas"
            ),
            "top_text": (
                "{name} is likely to be motivated by opportunities to generate ideas "
                "and find original solutions. They may gain energy from experimentation, "
                "creative problem-solving and work that allows established approaches "
                "to be reconsidered."
            ),
        },

        "enjoyment": {
            "summary_phrase": (
                "an enjoyable and positive working atmosphere"
            ),
            "support_phrase": (
                "positive relationships, humour and an engaging day-to-day environment"
            ),
            "top_text": (
                "{name} is likely to value an enjoyable and positive atmosphere at work. "
                "They may gain energy from friendly relationships, humour and a working "
                "environment where day-to-day activities feel engaging and personally satisfying."
            ),
        },

        "variety": {
            "summary_phrase": (
                "variety, change and different types of work"
            ),
            "support_phrase": (
                "a changing mix of tasks, challenges and ways of working"
            ),
            "top_text": (
                "{name} is likely to be motivated by variety and change in their work. "
                "They may gain energy from moving between different tasks, encountering "
                "new challenges and using a broad range of skills rather than following "
                "the same routine for long periods."
            ),
        },

        "risk": {
            "summary_phrase": (
                "challenge, uncertainty and calculated risk"
            ),
            "support_phrase": (
                "room to make considered decisions when outcomes are not fully known"
            ),
            "top_text": (
                "{name} is likely to be motivated by situations where the outcome is "
                "not fully known and where calculated risk is part of the work. They "
                "may be comfortable making decisions without complete certainty and "
                "may gain energy from roles that offer challenge, pace and the opportunity "
                "to see whether a bold course of action pays off."
            ),
        },
    }

    motivation_model = [
        {
            "key": "belonging",
            "title": "Belonging",
            "subtitle": (
                "Social connection, support and a sense of belonging at work"
            ),
            "icon_class": "fa-solid fa-people-group",
            "factors": [
                {
                    "key": "attachment",
                    "name": "Affiliation",
                    "aliases": [
                        "attachment",
                        "affiliation",
                    ],
                    "description": (
                        "Value social interaction with others at work. This is a primary driver for them. Enjoys the feeling of belonging to a team and is driven by developing strong bonds and good working relationships."
                    ),
                },
                {
                    "key": "customer_service",
                    "name": "Customer Service",
                    "aliases": [
                        "customer service",
                        "customer focus",
                    ],
                    "description": (
                        "Thrives in a customer-oriented role where they get to help and support others. Values building relationships with customers and understanding customer needs. Places great emphasis on meeting and exceeding customer needs and expectations."
                    ),
                },
                {
                    "key": "work_life_balance",
                    "name": "Work-life Balance",
                    "aliases": [
                        "work life balance",
                        "work-life balance",
                    ],
                    "description": (
                        "Values work-life balance so they can fulfil their commitments both at work and outside. Looks for clear boundaries so they can switch off at the end of the workday and devote that time to other activities that are important."
                    ),
                },
                {
                    "key": "people_development",
                    "name": "People Development",
                    "aliases": [
                        "people development",
                        "developing people",
                    ],
                    "description": (
                        "Helps and supports others and actively contributes to their development. Enjoys guiding others through difficult times and helping others overcome adversity or challenges. Offers proactive support so others can grow."
                    ),
                },
                {
                    "key": "stability",
                    "name": "Stability",
                    "aliases": [
                        "stability",
                        "security",
                    ],
                    "description": (
                        "Wants to feel secure at work and will probably prefer to work in an industry or organisation they see as stable. Places importance on feeling that their position at work is secure and is likely to be more concerned with having stability in their role."
                    ),
                },
            ],
        },
        {
            "key": "influence",
            "title": "Impact",
            "subtitle": (
                "Autonomy, recognition and opportunities to shape outcomes"
            ),
            "icon_class": "fa-solid fa-hand-pointer",
            "factors": [
                {
                    "key": "authority",
                    "name": "Authority",
                    "aliases": [
                        "authority",
                    ],
                    "description": (
                        "Values the opportunity to take on leadership positions and the opportunity for promotion. Appreciates roles where there is room to set direction, organise others and ensure work is done properly."
                    ),
                },
                {
                    "key": "independence",
                    "name": "Autonomy",
                    "aliases": [
                        "independence",
                        "autonomy",
                        "self determination",
                        "self direction",
                    ],
                    "description": (
                        "Values the freedom to make their own decisions about how to plan their time and organise their work. Performs at their best when trusted to set their own work direction and complete their work in the way they see fit."
                    ),
                },
                {
                    "key": "recognition",
                    "name": "Recognition",
                    "aliases": [
                        "recognition",
                    ],
                    "description": (
                        "Is motivated by recognition, praise and appreciation. Prioritises activities or projects that are visible in the organisation so others can see the work they do and the value they add. Positive feedback and praise are motivating for them."
                    ),
                },
                {
                    "key": "making_a_difference",
                    "name": "Making a difference",
                    "aliases": [
                        "making a difference",
                        "make a difference",
                        "purpose",
                    ],
                    "description": (
                        "Wants to feel that they make a positive difference to others. Considers it important to be part of an organisation whose goals and purpose seem worthwhile to them, and to be able to see how their work has a beneficial impact on society at large."
                    ),
                },
                {
                    "key": "acquisition",
                    "name": "Acquisition",
                    "aliases": [
                        "acquisition",
                        "reward",
                        "financial reward",
                    ],
                    "description": (
                        "Is motivated by financial reward and by working in a well-paid role so they can afford the things they want without having to worry about costs. The focus on salary and benefits is strong; attractive remuneration is motivating."
                    ),
                },
            ],
        },
        {
            "key": "growth",
            "title": "Growth",
            "subtitle": (
                "Achievement, quality, development and meaningful standards"
            ),
            "icon_class": "fa-solid fa-arrow-trend-up",
            "factors": [
                {
                    "key": "achievement",
                    "name": "Achievement",
                    "aliases": [
                        "achievement",
                        "performance",
                    ],
                    "description": (
                        "Is energised by defined and challenging goals to work towards. Professionally challenging opportunities are important; thrives on competition and an environment where they have the opportunity to compare their performance to others."
                    ),
                },
                {
                    "key": "quality",
                    "name": "Quality",
                    "aliases": [
                        "quality",
                    ],
                    "description": (
                        "Is motivated by delivering high-quality results on a consistent basis. Takes pride in producing work that is in line with both what they have promised and what is expected of them. Ensures their work is completed as perfectly as possible."
                    ),
                },
                {
                    "key": "learning",
                    "name": "Learning",
                    "aliases": [
                        "learning",
                        "development",
                    ],
                    "description": (
                        "Is driven by the opportunity to learn and develop their expertise. Feels comfortable in an environment where there are plenty of opportunities for ongoing training and development to master new skills."
                    ),
                },
                {
                    "key": "ethics",
                    "name": "Ethics",
                    "aliases": [
                        "ethics",
                        "ethical standards",
                    ],
                    "description": (
                        "Maintains high ethical standards for themselves and the organisation they work for. Adheres to industry guidelines and best-practice requirements. Takes pride in their professional integrity and enjoys working in an organisation whose ethical values are in line with their own."
                    ),
                },
                {
                    "key": "commercial_focus",
                    "name": "Commercial Value",
                    "aliases": [
                        "commercial focus",
                        "commercial value",
                        "commercially focused",
                    ],
                    "description": (
                        "Thrives in a commercially focused role and contributes to the organisation's financial success. Values seeing the connection between their role and the organisation's results. Gains energy from seeing how their work leads to commercial profit."
                    ),
                },
            ],
        },
        {
            "key": "interest",
            "title": "Interest",
            "subtitle": (
                "Exploration, creativity, enjoyment, variety and risk"
            ),
            "icon_class": "fa-solid fa-lightbulb",
            "factors": [
                {
                    "key": "curiosity",
                    "name": "Curiosity",
                    "aliases": [
                        "curiosity",
                    ],
                    "description": (
                        "Explores and discovers new things. Pursues knowledge and experience, takes advantage of opportunities for new experiences and new information, and explores the things that capture their interest."
                    ),
                },
                {
                    "key": "creativity",
                    "name": "Creativity",
                    "aliases": [
                        "creativity",
                    ],
                    "description": (
                        "Enjoys exercising creativity, thinking outside the box, generating new ideas and identifying new solutions. Ideas and suggestions are likely to be useful, not just original for the sake of being different or unique."
                    ),
                },
                {
                    "key": "enjoyment",
                    "name": "Enjoyment",
                    "aliases": [
                        "enjoyment",
                        "joy",
                        "fun",
                    ],
                    "description": (
                        "Values an environment where they enjoy their work but can also have fun with their colleagues. Thrives in an easy-going environment where they can express their playful side, share humour with colleagues and be accepted for who they are."
                    ),
                },
                {
                    "key": "variety",
                    "name": "Variety",
                    "aliases": [
                        "variety",
                        "variation",
                    ],
                    "description": (
                        "Is motivated by a role that offers a lot of variety and the opportunity to work with many different things. Thrives in a diverse role with a mix of tasks and projects where they can focus their attention on different work demands and take advantage of their different skills."
                    ),
                },
                {
                    "key": "risk",
                    "name": "Risk",
                    "aliases": [
                        "risk",
                        "risk taking",
                    ],
                    "description": (
                        "Is motivated by risk at work and by having to face situations where the outcome is unclear. Is comfortable making risky decisions and thrives in roles that allow room to experience the thrill of taking a risk and then seeing if it pays off."
                    ),
                },
            ],
        },
    ]

    source_lookup = {}

    for item in mq_competencies or []:   
        competency_name = normalise_name(
            item.get("competency")
        )

        if competency_name:
            source_lookup[competency_name] = item

    def find_source(factor):
        for alias in factor.get("aliases", []):
            source = source_lookup.get(
                normalise_name(alias)
            )

            if source:
                return source

        return None

    def get_band(score):
        if score is None:
            return {
                "key": "missing",
                "label": "Not available",
            }

        if score <= 2:
            return {
                "key": "lower",
                "label": "Lower",
            }

        if score == 3:
            return {
                "key": "mid",
                "label": "Mid-range",
            }

        return {
            "key": "higher",
            "label": "Higher",
        }

    def build_segments(score):
        return [
            {
                "number": number,
                "filled": (
                    score is not None
                    and number <= score
                ),
            }
            for number in range(1, 6)
        ]

    used_source_ids = set()
    domains = []
    all_items = []
    item_order = 0

    for domain_index, domain_config in enumerate(motivation_model):
        domain_items = []

        for factor in domain_config["factors"]:
            source = find_source(factor)
            score = get_score(source) if source else None
            band = get_band(score)

            interpretation_config = factor_interpretations.get(
                factor["key"],
                {},
            )

            if source:
                used_source_ids.add(id(source))

            item = {
                "key": factor["key"],
                "name": factor["name"],
                "description": factor["description"],
                "domain": domain_config["title"],
                "domain_data": domain_config,
                "domain_index": domain_index,
                "score": score,
                "available": score is not None,
                "segments": build_segments(score),
                "band_key": band["key"],
                "band_label": band["label"],
                "percentile": (
                    source.get("percentile")
                    if source
                    else None
                ),
                "source_name": (
                    source.get("competency")
                    if source
                    else None
                ),
                "order": item_order,
                "summary_phrase": interpretation_config.get(
                    "summary_phrase",
                    factor["name"].lower(),
                ),

                "support_phrase": interpretation_config.get(
                    "support_phrase",
                    factor["description"].lower(),
                ),

                "top_interpretation": (
                    interpretation_config.get("top_text", "").format(
                        name=candidate_label,
                    )
                    if interpretation_config.get("top_text")
                    else (
                        f"{candidate_label} appears to be particularly motivated "
                        f"by this aspect of the working environment."
                    )
                ),
            }

            item_order += 1
            domain_items.append(item)
            all_items.append(item)

        domain_items = sorted(
            domain_items,
            key=lambda item: (
                item["score"] is None,
                -(item["score"] or 0),
                item["order"],
            ),
        )

        domains.append({
            "key": domain_config["key"],
            "title": domain_config["title"],
            "subtitle": domain_config["subtitle"],
            "icon_class": domain_config["icon_class"],
            "items": domain_items,
        })


    available_items = [
        item
        for item in all_items
        if item["available"]
    ]

    if not available_items:
        return None

    sorted_desc = sorted(
        available_items,
        key=lambda item: (
            -item["score"],
            item["order"],
        ),
    )

    sorted_asc = sorted(
        available_items,
        key=lambda item: (
            item["score"],
            item["order"],
        ),
    )

    highest_score = max(
        item["score"]
        for item in available_items
    )

    lowest_score = min(
        item["score"]
        for item in available_items
    )

    has_profile_difference = (
        highest_score != lowest_score
    )

    if has_profile_difference:
        motivators = sorted_desc[:3]
        less_central_drivers = sorted_asc[:3]
    else:
        motivators = []
        less_central_drivers = []

    def join_text(values):
        values = [
            value
            for value in values
            if value
        ]

        if not values:
            return ""

        if len(values) == 1:
            return values[0]

        if len(values) == 2:
            return " and ".join(values)

        return (
            f"{', '.join(values[:-1])} and {values[-1]}"
        )

    def join_names(items):
        names = [
            item["name"]
            for item in items
        ]

        if not names:
            return ""

        if len(names) == 1:
            return names[0]

        if len(names) == 2:
            return " and ".join(names)

        return (
            f"{', '.join(names[:-1])} and {names[-1]}"
        )

    for item in motivators:
        item["interpretation"] = item.get(
            "top_interpretation"
        ) or (
            f"{candidate_label} appears to be particularly motivated "
            f"by {item.get('name', 'this aspect of work').lower()}."
        )

    for item in less_central_drivers:
        item["interpretation"] = (
            f"{item['description']} This appears to be a less central "
            f"source of energy for the candidate."
        )

    if motivators:
        motivational_themes = join_text([
            item["summary_phrase"]
            for item in motivators
        ])

        supportive_conditions = join_text([
            item["support_phrase"]
            for item in motivators
        ])

        summary = (
            f"{candidate_label} is likely to be energised by "
            f"{motivational_themes}. A working environment that offers "
            f"{supportive_conditions} may therefore support sustained "
            f"engagement."
        )
    else:
        summary = (
            f"{candidate_label}'s motivation profile is relatively even, "
            f"with no clear separation between more prominent and less "
            f"central motivational drivers."
        )

    return {
        "title": "Motivation profile",
        "summary": summary,
        "domains": domains,
        # Flat chart data avoids relying on nested template dictionary lookup.
        # These items retain the same precise scores used for ranking.
        "chart_items": available_items,
        "motivators": motivators,
        "less_central_drivers": less_central_drivers,

        # Temporary compatibility with the previous template/data structure.
        "demotivators": less_central_drivers,

        "available_count": len(available_items),
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "has_profile_difference": has_profile_difference,
    }


def build_sova_reports_for_ui(reports):
    """
    Prepare all reports received from the Sova webhook for the UI.

    Every report with a valid URL is included.
    Known report codes receive cleaner display names.
    Unknown reports fall back to the title supplied by Sova.
    """

    title_map = {
        # Cognitive candidate reports
        "TQ_CANDIDATE_LOGICAL_REASONING": (
            "Logical Reasoning – Candidate Report"
        ),
        "TQ_CANDIDATE_NUMERICAL_REASONING": (
            "Numerical Reasoning – Candidate Report"
        ),
        "TQ_CANDIDATE_VERBAL_REASONING": (
            "Verbal Reasoning – Candidate Report"
        ),

        # Cognitive practitioner reports
        "TQ_PRACTITIONER_LOGICAL_REASONING": (
            "Logical Reasoning – Practitioner Report"
        ),
        "TQ_PRACTITIONER_NUMERICAL_REASONING": (
            "Numerical Reasoning – Practitioner Report"
        ),
        "TQ_PRACTITIONER_VERBAL_REASONING": (
            "Verbal Reasoning – Practitioner Report"
        ),

        # Personality reports
        "TQ_SOVA_PQ_CANDIDATE_TRAIT": (
            "Personality Trait Report – Candidate"
        ),
        "SOVA_PQ_Team_TQ_Nordics": (
            "Team Profile"
        ),
        "TQ_PQ38_Recruitment_Report": (
            "Competency Report and Interview Guide"
        ),
        "TQ_Sova_PQ_Career_report": (
            "Career Report"
        ),
        "TQ_Sova_PQ_Derailment": (
            "Derailment Report"
        ),
        "SOVA_PQ_FULL_TRAIT_PROFILE_TQ_Nordics": (
            "Full Personality Trait Profile"
        ),
        "TQ_Sova_PQ_Leadership": (
            "Leadership Report"
        ),
        "Sova_PQ_Leadership_Manager_TQ_Nordics_Only": (
            "Leadership Report – Manager Version"
        ),
        "TQ_Sova_PQ_Potential_DNA": (
            "Potential DNA Report"
        ),
        "TQ_PQ_Practitioner_Sales_Report": (
            "Sales Profile – Practitioner Report"
        ),
        "TQ_SOVA_PQ_SUBTRAIT_REPORT": (
            "Trait and Indicator Profile"
        ),
        "TQ_PQ_Team_Composite": (
            "Team Composite Report"
        ),
    }

    def get_category(code, title):
        text = f"{code} {title}".lower()

        if "logical" in text:
            return "Logical reasoning"

        if "numerical" in text:
            return "Numerical reasoning"

        if "verbal" in text:
            return "Verbal reasoning"

        if any(word in text for word in (
            "personality",
            "pq",
            "trait",
            "leadership",
            "career",
            "derailment",
            "potential",
            "sales",
            "team",
        )):
            return "Personality"

        if "motivation" in text or "mq" in text:
            return "Motivation"

        return "Assessment report"

    result = []

    for report in reports or []:
        if not isinstance(report, dict):
            continue

        url = (report.get("url") or "").strip()

        if not url or not _is_safe_external_url(url):
            continue

        code = (report.get("code") or "").strip()
        original_title = (report.get("title") or "").strip()

        display_title = (
            title_map.get(code)
            or original_title
            or code
            or "Assessment report"
        )

        is_candidate_report = bool(
            report.get("is_candidate_report")
        )

        result.append({
            "code": code,
            "url": url,
            "title": display_title,
            "original_title": original_title,
            "category": get_category(
                code=code,
                title=original_title,
            ),
            "audience": (
                "Candidate report"
                if is_candidate_report
                else "Practitioner report"
            ),
            "is_candidate_report": is_candidate_report,
        })

    # Candidate reports first, then practitioner reports.
    return sorted(
        result,
        key=lambda item: (
            not item["is_candidate_report"],
            item["category"].lower(),
            item["title"].lower(),
        ),
    )


def _normalise_combined_question(
    item,
) -> dict | None:
    """
    Convert questions from different AI modules into one shared shape.
    """

    if isinstance(item, str):
        question = item.strip()

        if not question:
            return None

        return {
            "question": question,
            "why": "",
            "listen_for": "",
            "traits": [],
        }

    if not isinstance(item, dict):
        return None

    questio…64748 tokens truncated…     "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),

        # ---------------------------------------------------------
        # Historical motivation AI
        # ---------------------------------------------------------

        "motivation_interpretation": (
            historical_candidate
            .ai_motivation_interpretation
            or {}
        ),

        "motivation_interpretation_status": (
            historical_candidate
            .ai_motivation_interpretation_status
            or "not_started"
        ),

        "motivation_interpretation_stream_url": reverse(
            (
                "processes:"
                "process_candidate_motivation_"
                "interpretation_stream"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),

        "motivation_interpretation_regenerate_url": reverse(
            (
                "processes:"
                "process_candidate_motivation_"
                "interpretation_regenerate"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),

        "motivation_questions": (
            historical_candidate
            .ai_motivation_questions
            or {}
        ),

        "motivation_questions_status": (
            historical_candidate
            .ai_motivation_questions_status
            or "not_started"
        ),

        "motivation_questions_stream_url": reverse(
            (
                "processes:"
                "process_candidate_motivation_"
                "questions_stream"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),

        "motivation_questions_regenerate_url": reverse(
            (
                "processes:"
                "process_candidate_motivation_"
                "questions_regenerate"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),

        "response_styles": response_styles,

        "response_style_segments": range(1, 11),

        "response_style_side_segments": range(1, 6),

        "response_style_guidance": (
            historical_candidate
            .ai_response_style_guidance
            or {}
        ),

        "response_style_guidance_status": (
            historical_candidate
            .ai_response_style_guidance_status
        ),

        "response_style_guidance_stream_url": reverse(
            (
                "processes:process_candidate_"
                "response_style_guidance_stream"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),
    }


@login_required
@require_POST
def process_candidate_summary_regenerate(
    request,
    process_id,
    candidate_id,
):
    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )

    if process.is_historical:
        summary_owner = get_object_or_404(
            HistoricalProcessCandidate.objects,
            process=process,
            candidate_id=candidate_id,
        )

    else:
        summary_owner = get_object_or_404(
            TestInvitation.objects,
            process=process,
            candidate_id=candidate_id,
        )

    summary_owner.ai_summary_status = "not_started"
    summary_owner.ai_summary_generated_at = None

    summary_owner.save(
        update_fields=[
            "ai_summary_status",
            "ai_summary_generated_at",
        ]
    )

    return JsonResponse({
        "ok": True,
        "stream_url": reverse(
            "processes:process_candidate_summary_stream",
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate_id,
            },
        ),
    })


@login_required
def process_candidate_cognitive_interpretation_stream(
    request,
    process_id,
    candidate_id,
):
    """
    Stream and save an AI-supported interpretation of the
    candidate's available cognitive assessment results.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )

    if process.is_historical:
        invitation = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
            )
            .prefetch_related(
                "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process,
            candidate_id=candidate_id,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation.objects.select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    language_code = get_request_ai_language(
        request
    )
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="cognitive_interpretation",
        result_field="ai_cognitive_interpretation",
        status_field="ai_cognitive_interpretation_status",
        language_code=language_code,
    )

    cognitive_results = (
        build_cognitive_results_for_ai_owner(
            invitation
        )
    )

    if not cognitive_results:
        return JsonResponse(
            {
                "error": (
                    "No cognitive assessment results "
                    "are available for this candidate."
                )
            },
            status=400,
        )

    current_status = (
        invitation.ai_cognitive_interpretation_status
        or "not_started"
    )

    saved_interpretation = (
        invitation.ai_cognitive_interpretation
        or {}
    )

    current_purpose = (
        process.purpose
        or ""
    ).strip().lower()

    saved_purpose = (
        invitation.ai_cognitive_interpretation_purpose
        or ""
    ).strip().lower()

    # Safety check in case the purpose changed without the normal
    # outdated-marking flow being triggered.
    if (
        saved_interpretation
        and current_status == "completed"
        and saved_purpose != current_purpose
    ):
        current_status = "outdated"

        invitation.ai_cognitive_interpretation_status = (
            "outdated"
        )

        invitation.save(update_fields=[
            "ai_cognitive_interpretation_status",
        ])

    # Return a completed saved result without a new OpenAI request.
    if (
        ai_content_language_matches(
            invitation,
            "cognitive_interpretation",
            language_code,
        )
        and should_return_saved_ai_result(
            saved_interpretation,
            current_status,
        )
    ):
        def existing_generator():
            yield json.dumps(
                {
                    "type": "saved_result",
                    "data": saved_interpretation,
                    "status": current_status,
                },
                ensure_ascii=False,
            ) + "\n"

        response = StreamingHttpResponse(
            existing_generator(),
            content_type=(
                "application/x-ndjson; charset=utf-8"
            ),
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    if current_status == "generating":
        return JsonResponse(
            {
                "error": (
                    "The cognitive interpretation is "
                    "already being generated."
                )
            },
            status=409,
        )

    invitation.ai_cognitive_interpretation_status = (
        "generating"
    )

    invitation.save(update_fields=[
        "ai_cognitive_interpretation_status",
    ])

    def generator():
        interpretation = (
            create_empty_cognitive_interpretation(
                invitation,
                language_code=language_code,
            )
        )

        received_done_event = False

        try:
            for event in stream_cognitive_interpretation(
                owner=invitation,
                cognitive_results=cognitive_results,
                language_code=language_code,
            ):
                interpretation = (
                    apply_cognitive_interpretation_event(
                        interpretation,
                        event,
                    )
                )

                if event.get("type") == "done":
                    received_done_event = True

                yield json.dumps(
                    event,
                    ensure_ascii=False,
                ) + "\n"

            # Do not save an empty or malformed AI result.
            if not (
                interpretation.get("interpretation")
                or ""
            ).strip():
                raise ValueError(
                    "The AI response did not contain "
                    "a cognitive interpretation."
                )

            if not received_done_event:
                yield json.dumps(
                    {
                        "type": "done",
                    },
                    ensure_ascii=False,
                ) + "\n"

            save_cognitive_interpretation(
                owner=invitation,
                interpretation=interpretation,
                language_code=language_code,
            )

        except Exception as error:
            invitation.ai_cognitive_interpretation_status = (
                "failed"
            )

            invitation.save(update_fields=[
                "ai_cognitive_interpretation_status",
            ])

            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                },
                ensure_ascii=False,
            ) + "\n"

    response = StreamingHttpResponse(
        generator(),
        content_type=(
            "application/x-ndjson; charset=utf-8"
        ),
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response


@login_required
@require_POST
def process_candidate_cognitive_interpretation_regenerate(
    request,
    process_id,
    candidate_id,
):
    """
    Clear the saved cognitive interpretation and return
    the stream URL for a fresh generation.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )


    if process.is_historical:
        invitation = get_object_or_404(
            HistoricalProcessCandidate,
            process=process,
            candidate_id=candidate_id,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation,
            process=process,
            candidate_id=candidate_id,
        )

    invitation.ai_cognitive_interpretation_status = (
        "not_started"
    )
    invitation.ai_cognitive_interpretation_generated_at = (
        None
    )
    invitation.ai_cognitive_interpretation_purpose = ""

    invitation.save(
        update_fields=[
            "ai_cognitive_interpretation_status",
            "ai_cognitive_interpretation_generated_at",
            "ai_cognitive_interpretation_purpose",
        ]
    )

    return JsonResponse(
        {
            "ok": True,
            "stream_url": reverse(
                (
                    "processes:"
                    "process_candidate_cognitive_"
                    "interpretation_stream"
                ),
                kwargs={
                    "process_id": process.id,
                    "candidate_id": candidate_id,
                },
            ),
        }
    )


@login_required
def process_candidate_cognitive_questions_stream(
    request,
    process_id,
    candidate_id,
):
    """
    Stream and save AI-supported cognitive questions.

    Cognitive questions are generated and stored independently
    from the cognitive interpretation.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )


    if process.is_historical:
        invitation = get_object_or_404(
            HistoricalProcessCandidate,
            process=process,
            candidate_id=candidate_id,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation,
            process=process,
            candidate_id=candidate_id,
        )

    language_code = get_request_ai_language(
        request
    )
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="cognitive_questions",
        result_field="ai_cognitive_questions",
        status_field="ai_cognitive_questions_status",
        language_code=language_code,
    )

    cognitive_results = (
        build_cognitive_results_for_ai_owner(
            invitation
        )
    )

    if not cognitive_results:
        return JsonResponse(
            {
                "error": (
                    "No cognitive assessment results "
                    "are available for this candidate."
                )
            },
            status=400,
        )

    current_status = (
        invitation.ai_cognitive_questions_status
        or "not_started"
    )

    saved_result = (
        invitation.ai_cognitive_questions
        or {}
    )

    current_purpose = (
        process.purpose
        or ""
    ).strip().lower()

    saved_purpose = (
        invitation.ai_cognitive_questions_purpose
        or ""
    ).strip().lower()

    # Safety check if the process purpose has changed.
    if (
        saved_result
        and current_status == "completed"
        and saved_purpose != current_purpose
    ):
        current_status = "outdated"

        invitation.ai_cognitive_questions_status = (
            "outdated"
        )

        invitation.save(
            update_fields=[
                "ai_cognitive_questions_status",
            ]
        )

    # Return previously generated questions when available.
    if (
        ai_content_language_matches(
            invitation,
            "cognitive_questions",
            language_code,
        )
        and should_return_saved_ai_result(
            saved_result,
            current_status,
        )
    ):
        def existing_generator():
            yield json.dumps(
                {
                    "type": "saved_result",
                    "data": saved_result,
                    "status": current_status,
                },
                ensure_ascii=False,
            ) + "\n"

        response = StreamingHttpResponse(
            existing_generator(),
            content_type=(
                "application/x-ndjson; charset=utf-8"
            ),
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    if current_status == "generating":
        return JsonResponse(
            {
                "error": (
                    "The cognitive questions are "
                    "already being generated."
                )
            },
            status=409,
        )

    invitation.ai_cognitive_questions_status = (
        "generating"
    )

    invitation.save(
        update_fields=[
            "ai_cognitive_questions_status",
        ]
    )

    def generator():
        result = create_empty_cognitive_questions(
            invitation,
            language_code=language_code,
        )

        received_done_event = False

        try:
            for event in stream_cognitive_questions(
                owner=invitation,
                cognitive_results=cognitive_results,
                language_code=language_code,
            ):
                result = apply_cognitive_questions_event(
                    result,
                    event,
                )

                if event.get("type") == "done":
                    received_done_event = True

                yield json.dumps(
                    event,
                    ensure_ascii=False,
                ) + "\n"

            questions = (
                result.get("questions")
                or []
            )

            if not questions:
                raise ValueError(
                    "The AI response did not contain "
                    "valid cognitive questions."
                )

            if not received_done_event:
                yield json.dumps(
                    {
                        "type": "done",
                    },
                    ensure_ascii=False,
                ) + "\n"

            save_cognitive_questions(
                owner=invitation,
                result=result,
                language_code=language_code,
            )

        except Exception as error:
            invitation.ai_cognitive_questions_status = (
                "failed"
            )

            invitation.save(
                update_fields=[
                    "ai_cognitive_questions_status",
                ]
            )

            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                },
                ensure_ascii=False,
            ) + "\n"

    response = StreamingHttpResponse(
        generator(),
        content_type=(
            "application/x-ndjson; charset=utf-8"
        ),
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response

@login_required
@require_POST
def process_candidate_cognitive_questions_regenerate(
    request,
    process_id,
    candidate_id,
):
    """
    Reset only the cognitive questions and return the
    stream URL for a fresh generation.

    The cognitive interpretation is not changed.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )

    if process.is_historical:
        invitation = get_object_or_404(
            HistoricalProcessCandidate,
            process=process,
            candidate_id=candidate_id,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation,
            process=process,
            candidate_id=candidate_id,
        )

    invitation.ai_cognitive_questions_status = (
        "not_started"
    )

    invitation.ai_cognitive_questions_generated_at = (
        None
    )

    invitation.ai_cognitive_questions_purpose = ""

    invitation.save(
        update_fields=[
            "ai_cognitive_questions_status",
            "ai_cognitive_questions_generated_at",
            "ai_cognitive_questions_purpose",
        ]
    )

    return JsonResponse(
        {
            "ok": True,

            "stream_url": reverse(
                (
                    "processes:"
                    "process_candidate_cognitive_"
                    "questions_stream"
                ),
                kwargs={
                    "process_id": process.id,
                    "candidate_id": candidate_id,
                },
            ),
        }
    )


@login_required
def process_candidate_motivation_interpretation_stream(
    request,
    process_id,
    candidate_id,
):
    """
    Stream and save an AI-supported interpretation of the
    candidate's motivation assessment results.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )

    if process.is_historical:
        invitation = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
            )
            .prefetch_related(
                "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process,
            candidate_id=candidate_id,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation.objects.select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    language_code = get_request_ai_language(
        request
    )
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="motivation_interpretation",
        result_field="ai_motivation_interpretation",
        status_field="ai_motivation_interpretation_status",
        language_code=language_code,
    )

    motivation_results = (
        build_motivation_results_for_ai_owner(
            invitation
        )
    )

    if not motivation_results:
        return JsonResponse(
            {
                "error": (
                    "No motivation assessment results "
                    "are available for this candidate."
                )
            },
            status=400,
        )

    current_status = (
        invitation.ai_motivation_interpretation_status
        or "not_started"
    )

    saved_interpretation = (
        invitation.ai_motivation_interpretation
        or {}
    )

    current_purpose = (
        process.purpose
        or ""
    ).strip().lower()

    saved_purpose = (
        invitation.ai_motivation_interpretation_purpose
        or ""
    ).strip().lower()

    # Extra safety if the purpose changed without the normal
    # outdated-marking flow being triggered.
    if (
        saved_interpretation
        and current_status == "completed"
        and saved_purpose != current_purpose
    ):
        current_status = "outdated"

        invitation.ai_motivation_interpretation_status = (
            "outdated"
        )

        invitation.save(update_fields=[
            "ai_motivation_interpretation_status",
        ])

    # Return an existing completed interpretation.
    if (
        ai_content_language_matches(
            invitation,
            "motivation_interpretation",
            language_code,
        )
        and should_return_saved_ai_result(
            saved_interpretation,
            current_status,
        )
    ):
        def existing_generator():
            yield json.dumps(
                {
                    "type": "saved_result",
                    "data": saved_interpretation,
                    "status": current_status,
                },
                ensure_ascii=False,
            ) + "\n"

        response = StreamingHttpResponse(
            existing_generator(),
            content_type=(
                "application/x-ndjson; charset=utf-8"
            ),
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    if current_status == "generating":
        return JsonResponse(
            {
                "error": (
                    "The motivation interpretation is "
                    "already being generated."
                )
            },
            status=409,
        )

    invitation.ai_motivation_interpretation_status = (
        "generating"
    )

    invitation.save(update_fields=[
        "ai_motivation_interpretation_status",
    ])

    def generator():
        interpretation = (
            create_empty_motivation_interpretation(
                invitation,
                language_code=language_code,
            )
        )

        received_done_event = False

        try:
            for event in stream_motivation_interpretation(
                owner=invitation,
                motivation_results=motivation_results,
                language_code=language_code,
            ):
                interpretation = (
                    apply_motivation_interpretation_event(
                        interpretation,
                        event,
                    )
                )

                if event.get("type") == "done":
                    received_done_event = True

                yield json.dumps(
                    event,
                    ensure_ascii=False,
                ) + "\n"

            if not (
                interpretation.get("interpretation")
                or ""
            ).strip():
                raise ValueError(
                    "The AI response did not contain "
                    "a motivation interpretation."
                )

            if not received_done_event:
                yield json.dumps(
                    {
                        "type": "done",
                    },
                    ensure_ascii=False,
                ) + "\n"

            save_motivation_interpretation(
                owner=invitation,
                interpretation=interpretation,
                language_code=language_code,
            )

        except Exception as error:
            invitation.ai_motivation_interpretation_status = (
                "failed"
            )

            invitation.save(update_fields=[
                "ai_motivation_interpretation_status",
            ])

            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                },
                ensure_ascii=False,
            ) + "\n"

    response = StreamingHttpResponse(
        generator(),
        content_type=(
            "application/x-ndjson; charset=utf-8"
        ),
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response


@login_required
@require_POST
def process_candidate_motivation_interpretation_regenerate(
    request,
    process_id,
    candidate_id,
):
    """
    Clear the saved motivation interpretation and return
    the stream URL for a fresh generation.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )

    if process.is_historical:
        invitation = get_object_or_404(
            HistoricalProcessCandidate,
            process=process,
            candidate_id=candidate_id,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation,
            process=process,
            candidate_id=candidate_id,
        )

    invitation.ai_motivation_interpretation_status = (
        "not_started"
    )
    invitation.ai_motivation_interpretation_generated_at = (
        None
    )
    invitation.ai_motivation_interpretation_purpose = ""


    invitation.save(update_fields=[
        "ai_motivation_interpretation_status",
        "ai_motivation_interpretation_generated_at",
        "ai_motivation_interpretation_purpose",
    ])

    return JsonResponse(
        {
            "ok": True,
            "stream_url": reverse(
                (
                    "processes:"
                    "process_candidate_motivation_"
                    "interpretation_stream"
                ),
                kwargs={
                    "process_id": process.id,
                    "candidate_id": candidate_id,
                },
            ),
        }
    )

@login_required
def process_candidate_motivation_questions_stream(
    request,
    process_id,
    candidate_id,
):
    """
    Stream and save AI-supported motivation questions.

    Motivation questions are generated and stored independently
    from the motivation interpretation.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )

    if process.is_historical:
        invitation = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
            )
            .prefetch_related(
                "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process,
            candidate_id=candidate_id,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation.objects.select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    language_code = get_request_ai_language(
        request
    )
    mark_ai_content_outdated_if_language_changed(
        invitation,
        content_key="motivation_questions",
        result_field="ai_motivation_questions",
        status_field="ai_motivation_questions_status",
        language_code=language_code,
    )

    motivation_results = (
        build_motivation_results_for_ai_owner(
            invitation
        )
    )

    if not motivation_results:
        return JsonResponse(
            {
                "error": (
                    "No motivation assessment results "
                    "are available for this candidate."
                )
            },
            status=400,
        )

    current_status = (
        invitation.ai_motivation_questions_status
        or "not_started"
    )

    saved_result = (
        invitation.ai_motivation_questions
        or {}
    )

    current_purpose = (
        process.purpose
        or ""
    ).strip().lower()

    saved_purpose = (
        invitation.ai_motivation_questions_purpose
        or ""
    ).strip().lower()

    # Safety check if the process purpose has changed.
    if (
        saved_result
        and current_status == "completed"
        and saved_purpose != current_purpose
    ):
        current_status = "outdated"

        invitation.ai_motivation_questions_status = (
            "outdated"
        )

        invitation.save(
            update_fields=[
                "ai_motivation_questions_status",
            ]
        )

    # Return previously generated questions when available.
    if (
        ai_content_language_matches(
            invitation,
            "motivation_questions",
            language_code,
        )
        and should_return_saved_ai_result(
            saved_result,
            current_status,
        )
    ):
        def existing_generator():
            yield json.dumps(
                {
                    "type": "saved_result",
                    "data": saved_result,
                    "status": current_status,
                },
                ensure_ascii=False,
            ) + "\n"

        response = StreamingHttpResponse(
            existing_generator(),
            content_type=(
                "application/x-ndjson; charset=utf-8"
            ),
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    if current_status == "generating":
        return JsonResponse(
            {
                "error": (
                    "The motivation questions are "
                    "already being generated."
                )
            },
            status=409,
        )

    invitation.ai_motivation_questions_status = (
        "generating"
    )

    invitation.save(
        update_fields=[
            "ai_motivation_questions_status",
        ]
    )

    def generator():
        result = create_empty_motivation_questions(
            invitation,
            language_code=language_code,
        )

        received_done_event = False

        try:
            for event in stream_motivation_questions(
                owner=invitation,
                motivation_results=motivation_results,
                language_code=language_code,
            ):
                result = apply_motivation_questions_event(
                    result,
                    event,
                )

                if event.get("type") == "done":
                    received_done_event = True

                yield json.dumps(
                    event,
                    ensure_ascii=False,
                ) + "\n"

            questions = (
                result.get("questions")
                or []
            )

            if not questions:
                raise ValueError(
                    "The AI response did not contain "
                    "valid motivation questions."
                )

            if not received_done_event:
                yield json.dumps(
                    {
                        "type": "done",
                    },
                    ensure_ascii=False,
                ) + "\n"

            save_motivation_questions(
                owner=invitation,
                result=result,
                language_code=language_code,
            )

        except Exception as error:
            invitation.ai_motivation_questions_status = (
                "failed"
            )

            invitation.save(
                update_fields=[
                    "ai_motivation_questions_status",
                ]
            )

            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                },
                ensure_ascii=False,
            ) + "\n"

    response = StreamingHttpResponse(
        generator(),
        content_type=(
            "application/x-ndjson; charset=utf-8"
        ),
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response


def get_candidate_ai_owner(
    process,
    candidate_id,
):
    """
    Return the model instance that owns candidate AI content.

    Active process:
        TestInvitation

    Historical process:
        HistoricalProcessCandidate
    """

    if process.is_historical:
        return get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    return get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )


@login_required
@require_POST
def process_candidate_motivation_questions_regenerate(
    request,
    process_id,
    candidate_id,
):
    """
    Reset only the motivation questions and return the
    stream URL for a fresh generation.

    The motivation interpretation is not changed.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )


    if process.is_historical:
        invitation = get_object_or_404(
            HistoricalProcessCandidate,
            process=process,
            candidate_id=candidate_id,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation,
            process=process,
            candidate_id=candidate_id,
        )

    invitation.ai_motivation_questions_status = (
        "not_started"
    )

    invitation.ai_motivation_questions_generated_at = (
        None
    )

    invitation.ai_motivation_questions_purpose = ""

    invitation.save(
        update_fields=[
            "ai_motivation_questions_status",
            "ai_motivation_questions_generated_at",
            "ai_motivation_questions_purpose",
        ]
    )

    return JsonResponse(
        {
            "ok": True,
            "stream_url": reverse(
                (
                    "processes:"
                    "process_candidate_motivation_"
                    "questions_stream"
                ),
                kwargs={
                    "process_id": process.id,
                    "candidate_id": candidate_id,
                },
            ),
        }
    )


@login_required
def process_candidate_personality_interpretation_stream(
    request,
    process_id,
    candidate_id,
):
    """
    Stream and save an AI-supported interpretation of the
    candidate's personality trait profile.

    Supports both:
    - active TestInvitation candidates
    - imported HistoricalProcessCandidate candidates
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )

    # ---------------------------------------------------------
    # FIND THE CORRECT OWNER
    # ---------------------------------------------------------

    if process.is_historical:
        owner = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
            )
            .prefetch_related(
                "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    else:
        owner = get_object_or_404(
            TestInvitation.objects.select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    language_code = get_request_ai_language(request)
    mark_ai_content_outdated_if_language_changed(
        owner,
        content_key="personality_interpretation",
        result_field="ai_personality_interpretation",
        status_field="ai_personality_interpretation_status",
        language_code=language_code,
    )

    # ---------------------------------------------------------
    # BUILD PERSONALITY EVIDENCE
    # ---------------------------------------------------------

    personality_results = (
        build_personality_results_for_ai_owner(
            owner
        )
    )

    if not personality_results:
        return JsonResponse(
            {
                "error": (
                    "No personality assessment results "
                    "are available for this candidate."
                )
            },
            status=400,
        )

    # ---------------------------------------------------------
    # CURRENT SAVED STATE
    # ---------------------------------------------------------

    current_status = (
        owner.ai_personality_interpretation_status
        or "not_started"
    )

    saved_interpretation = (
        owner.ai_personality_interpretation
        or {}
    )

    # Older saved personality interpretations predate the manager-report
    # personality sections. Regenerate them once so all six report texts
    # are available, even when the main interpretation was already saved.
    if (
        saved_interpretation
        and current_status == "completed"
        and saved_interpretation.get(
            "manager_report_personality_schema_version"
        ) != 1
    ):
        current_status = "outdated"
        owner.ai_personality_interpretation_status = "outdated"
        owner.save(update_fields=["ai_personality_interpretation_status"])

    current_purpose = normalize_purpose_key(
        process.purpose
    )

    saved_purpose = normalize_purpose_key(
        owner.ai_personality_interpretation_purpose
    )

    # Safety check in case the purpose changed without the normal
    # outdated-marking flow being triggered.
    if (
        saved_interpretation
        and current_status == "completed"
        and saved_purpose != current_purpose
    ):
        current_status = "outdated"

        owner.ai_personality_interpretation_status = (
            "outdated"
        )

        owner.save(update_fields=[
            "ai_personality_interpretation_status",
        ])

    # ---------------------------------------------------------
    # RETURN SAVED RESULT
    # ---------------------------------------------------------

    if (
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
        def existing_generator():
            yield json.dumps(
                {
                    "type": "saved_result",
                    "data": saved_interpretation,
                    "status": current_status,
                },
                ensure_ascii=False,
            ) + "\n"

        response = StreamingHttpResponse(
            existing_generator(),
            content_type=(
                "application/x-ndjson; charset=utf-8"
            ),
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    # ---------------------------------------------------------
    # PREVENT DUPLICATE GENERATION
    # ---------------------------------------------------------

    if current_status == "generating":
        return JsonResponse(
            {
                "error": (
                    "The personality interpretation is "
                    "already being generated."
                )
            },
            status=409,
        )

    owner.ai_personality_interpretation_status = (
        "generating"
    )

    owner.save(update_fields=[
        "ai_personality_interpretation_status",
    ])

    # ---------------------------------------------------------
    # STREAM GENERATION
    # ---------------------------------------------------------

    def generator():
        interpretation = (
            create_empty_personality_interpretation(
                owner,
                language_code=language_code,
            )
        )

        received_done_event = False
        received_manager_report_texts = set()

        try:
            for event in stream_personality_interpretation(
                owner=owner,
                personality_results=personality_results,
                language_code=language_code,
            ):
                interpretation = (
                    apply_personality_interpretation_event(
                        interpretation,
                        event,
                    )
                )

                if event.get("type") == "done":
                    received_done_event = True
                elif event.get("type") == "personality_report_text":
                    received_manager_report_texts.add(
                        (event.get("theme"), event.get("part"))
                    )

                yield json.dumps(
                    event,
                    ensure_ascii=False,
                ) + "\n"

            expected_manager_report_texts = {
                (theme["key"], part)
                for theme in PERSONALITY_MANAGER_REPORT_THEMES
                for part in ("testbild", "candidate_describes")
            }
            if received_manager_report_texts != expected_manager_report_texts:
                raise ValueError(
                    "The AI response did not contain all six "
                    "manager-report personality texts."
                )

            if not (
                interpretation.get(
                    "interpretation"
                )
                or ""
            ).strip():
                raise ValueError(
                    "The AI response did not contain "
                    "a personality interpretation."
                )

            if not received_done_event:
                yield json.dumps(
                    {
                        "type": "done",
                    },
                    ensure_ascii=False,
                ) + "\n"

            save_personality_interpretation(
                owner=owner,
                interpretation=interpretation,
                language_code=language_code,
            )

        except Exception as error:
            owner.ai_personality_interpretation_status = (
                "failed"
            )

            owner.save(update_fields=[
                "ai_personality_interpretation_status",
            ])

            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                },
                ensure_ascii=False,
            ) + "\n"

    response = StreamingHttpResponse(
        generator(),
        content_type=(
            "application/x-ndjson; charset=utf-8"
        ),
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response


@login_required
@require_POST
def process_candidate_personality_interpretation_regenerate(
    request,
    process_id,
    candidate_id,
):
    """
    Clear the saved personality interpretation and return
    the stream URL for a fresh generation.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )

    if process.is_historical:
        owner = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    else:
        owner = get_object_or_404(
            TestInvitation.objects.select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    owner.ai_personality_interpretation_status = (
        "not_started"
    )

    owner.ai_personality_interpretation_generated_at = (
        None
    )

    owner.ai_personality_interpretation_purpose = ""

    owner.save(update_fields=[
        "ai_personality_interpretation_status",
        "ai_personality_interpretation_generated_at",
        "ai_personality_interpretation_purpose",
    ])

    return JsonResponse(
        {
            "ok": True,

            "stream_url": reverse(
                (
                    "processes:"
                    "process_candidate_personality_"
                    "interpretation_stream"
                ),
                kwargs={
                    "process_id": process.id,
                    "candidate_id": candidate_id,
                },
            ),
        }
    )

@login_required
def process_candidate_personality_questions_stream(
    request,
    process_id,
    candidate_id,
):
    """
    Stream and save AI-supported personality trait suggestions
    and purpose-aware questions.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )

    if process.is_historical:
        invitation = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
            )
            .prefetch_related(
                "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process,
            candidate_id=candidate_id,
        )
    else:
        invitation = get_object_or_404(
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
        content_key="personality_questions",
        result_field="ai_personality_questions",
        status_field="ai_personality_questions_status",
        language_code=language_code,
    )

    personality_results = (
        build_personality_question_traits_for_ai_owner(
            invitation
        )
    )

    if not personality_results:
        return JsonResponse(
            {
                "error": (
                    "No personality assessment results "
                    "are available for this candidate."
                )
            },
            status=400,
        )

    current_status = (
        invitation.ai_personality_questions_status
        or "not_started"
    )

    saved_result = (
        invitation.ai_personality_questions
        or {}
    )

    current_purpose = (
        process.purpose
        or ""
    ).strip().lower()

    saved_purpose = (
        invitation.ai_personality_questions_purpose
        or ""
    ).strip().lower()

    if (
        saved_result
        and current_status == "completed"
        and saved_purpose != current_purpose
    ):
        current_status = "outdated"

        invitation.ai_personality_questions_status = (
            "outdated"
        )

        invitation.save(update_fields=[
            "ai_personality_questions_status",
        ])

    if (
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
        def existing_generator():
            yield json.dumps(
                {
                    "type": "saved_result",
                    "data": saved_result,
                    "status": current_status,
                },
                ensure_ascii=False,
            ) + "\n"

        response = StreamingHttpResponse(
            existing_generator(),
            content_type=(
                "application/x-ndjson; charset=utf-8"
            ),
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    if current_status == "generating":
        return JsonResponse(
            {
                "error": (
                    "The personality questions are "
                    "already being generated."
                )
            },
            status=409,
        )

    invitation.ai_personality_questions_status = (
        "generating"
    )

    invitation.save(update_fields=[
        "ai_personality_questions_status",
    ])

    def generator():
        result = create_empty_personality_questions(
            invitation,
            language_code=language_code,
        )

        received_done_event = False

        try:
            for event in stream_personality_questions(
                owner=invitation,
                personality_results=personality_results,
                language_code=language_code,
            ):
                result = apply_personality_questions_event(
                    result,
                    event,
                )

                if event.get("type") == "done":
                    received_done_event = True

                yield json.dumps(
                    event,
                    ensure_ascii=False,
                ) + "\n"

            selected_traits = (
                result.get("selected_traits")
                or []
            )

            questions = (
                result.get("questions")
                or []
            )

            # ---------------------------------------------------------
            # Validate only Talena's technical/product requirements.
            #
            # Administrators control:
            # - how many questions are generated
            # - how traits are used across questions
            # - whether every selected trait needs question coverage
            #
            # Talena only requires:
            # - at least one valid selected trait
            # - no more than six selected traits because the UI
            #   currently supports a maximum of six
            # - at least one valid question
            # ---------------------------------------------------------

            if not (
                1 <= len(selected_traits) <= 6
            ):
                raise ValueError(
                    "The personality trait selection was invalid."
                )

            if not questions:
                raise ValueError(
                    "The AI response did not contain "
                    "valid personality questions."
                )

            if not received_done_event:
                yield json.dumps(
                    {
                        "type": "done",
                    },
                    ensure_ascii=False,
                ) + "\n"

            save_personality_questions(
                owner=invitation,
                result=result,
                language_code=language_code,
            )

        except Exception as error:
            invitation.ai_personality_questions_status = (
                "failed"
            )

            invitation.save(update_fields=[
                "ai_personality_questions_status",
            ])

            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                },
                ensure_ascii=False,
            ) + "\n"

    response = StreamingHttpResponse(
        generator(),
        content_type=(
            "application/x-ndjson; charset=utf-8"
        ),
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response


@login_required
@require_POST
def process_candidate_personality_questions_regenerate(
    request,
    process_id,
    candidate_id,
):
    """
    Clear the saved personality questions and return
    the stream URL for a fresh generation.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )

    if process.is_historical:
        invitation = get_object_or_404(
            HistoricalProcessCandidate,
            process=process,
            candidate_id=candidate_id,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation,
            process=process,
            candidate_id=candidate_id,
        )

    invitation.ai_personality_questions_status = (
        "not_started"
    )
    invitation.ai_personality_questions_generated_at = (
        None
    )
    invitation.ai_personality_questions_purpose = ""

    invitation.save(update_fields=[
        "ai_personality_questions_status",
        "ai_personality_questions_generated_at",
        "ai_personality_questions_purpose",
    ])

    return JsonResponse(
        {
            "ok": True,
            "stream_url": reverse(
                (
                    "processes:"
                    "process_candidate_personality_"
                    "questions_stream"
                ),
                kwargs={
                    "process_id": process.id,
                    "candidate_id": candidate_id,
                },
            ),
        }
    )


@login_required
@require_POST
def process_candidate_personality_traits_update(
    request,
    process_id,
    candidate_id,
):
    """
    Save the user's personality trait selection.

    An empty list means that Talena should choose relevant
    traits automatically when questions are generated.
    """

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(
        request.user,
        process,
    ):
        return HttpResponseForbidden(
            "You do not have access to this project."
        )

    if process.is_historical:
        invitation = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
            )
            .prefetch_related(
                "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process,
            candidate_id=candidate_id,
        )
    else:
        invitation = get_object_or_404(
            TestInvitation.objects.select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    try:
        payload = json.loads(
            request.body.decode("utf-8")
            or "{}"
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "error": "Invalid JSON payload."
            },
            status=400,
        )

    raw_traits = payload.get("traits")

    if not isinstance(raw_traits, list):
        return JsonResponse(
            {
                "error": (
                    "Traits must be supplied as a list."
                )
            },
            status=400,
        )
    
    personality_results = (
        build_personality_question_traits_for_ai_owner(
            invitation
        )
    )

    selected_traits = (
        normalise_selected_traits(
            selected_traits=raw_traits,
            available_results=personality_results,
        )
    )

    # Zero selected traits means automatic selection.
    # A manual selection may contain no more than six traits.
    if len(selected_traits) > 6:
        return JsonResponse(
            {
                "error": (
                    "Select no more than six "
                    "available personality traits."
                )
            },
            status=400,
        )

    invitation.selected_personality_traits = (
        selected_traits
    )

    invitation.ai_personality_questions_status = (
        "outdated"
        if invitation.ai_personality_questions
        else "not_started"
    )

    invitation.save(
        update_fields=[
            "selected_personality_traits",
            "ai_personality_questions_status",
        ]
    )

    return JsonResponse(
        {
            "ok": True,
            "selected_traits": selected_traits,
            "selection_mode": (
                "manual"
                if selected_traits
                else "automatic"
            ),
            "questions_status": (
                invitation
                .ai_personality_questions_status
            ),
        }
    )
