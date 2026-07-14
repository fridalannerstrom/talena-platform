from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from apps.core.integrations.sova import SovaClient
from apps.projects.models import ProjectMeta
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

from apps.core.ai.cognitive_interpretation import (
    extract_cognitive_results,
    create_empty_cognitive_interpretation,
    apply_cognitive_interpretation_event,
    stream_cognitive_interpretation,
    save_cognitive_interpretation,
)

from apps.core.ai.motivation_interpretation import (
    extract_motivation_results,
    create_empty_motivation_interpretation,
    apply_motivation_interpretation_event,
    stream_motivation_interpretation,
    save_motivation_interpretation,
)

from apps.core.ai.response_style_guidance import (
    create_empty_response_style_guidance,
    apply_response_style_guidance_event,
    stream_response_style_guidance,
    save_response_style_guidance,
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

from apps.processes.models import (
    HistoricalProcessCandidate,
    TestInvitation,
    TestProcess,
)

from apps.processes.services.historical_candidate_summary import (
    stream_historical_candidate_summary,
)

from apps.core.ai.purpose_fit import (
    purpose_supports_fit,
    create_empty_purpose_fit,
    apply_purpose_fit_event,
    stream_candidate_purpose_fit,
    save_candidate_purpose_fit,
)

from apps.processes.services.historical_assessment_import import import_historical_assessment_file
from django.db.models import Count, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce
from apps.processes.models import HistoricalProcessCandidate
from django.contrib import messages
from django.db import transaction
from .forms import SelfRegisterForm
from django.urls import reverse
from django.utils import timezone
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

from apps.accounts.models import Company, CompanyMember
from apps.projects.models import ProjectMeta

from apps.activity.models import ActivityEvent
from apps.activity.services import log_event

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
from apps.reports.libraries.personality.builder import (
    build_profile_from_resolved_report,
)

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
    normalise_selected_traits,
    create_empty_personality_questions,
    apply_personality_questions_event,
    stream_personality_questions,
    save_personality_questions,
)

def build_cognitive_insight_results(
    verbal_percentile=None,
    logical_percentile=None,
    numerical_percentile=None,
):
    """
    Build the three cognitive result cards used in Candidate Insights.

    All three assessment types are always returned so the template can show
    a grey placeholder when an assessment has not been completed.
    """

    def normalise_percentile(value):
        if value is None:
            return None

        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    def get_level(percentile):
        """
        Translate a percentile result into a display level and interpretation.
        Adjust the thresholds later if Sova uses different norm bands.
        """

        if percentile is None:
            return {
                "completed": False,
                "level_key": "missing",
                "level_label": "Not completed",
            }

        if percentile <= 9:
            return {
                "completed": True,
                "level_key": "very-low",
                "level_label": "Very low",
            }

        if percentile <= 24:
            return {
                "completed": True,
                "level_key": "low",
                "level_label": "Low",
            }

        if percentile <= 74:
            return {
                "completed": True,
                "level_key": "average",
                "level_label": "Typical",
            }

        if percentile <= 90:
            return {
                "completed": True,
                "level_key": "high",
                "level_label": "High",
            }

        return {
            "completed": True,
            "level_key": "very-high",
            "level_label": "Very high",
        }

    def get_interpretation(test_key, percentile):
        if percentile is None:
            return "This candidate has not completed this assessment."

        ability_labels = {
            "verbal": "understand and evaluate written information",
            "logical": "identify patterns and reach logical conclusions",
            "numerical": "understand and work with numerical information",
        }

        ability_text = ability_labels[test_key]

        if percentile <= 9:
            return (
                f"The candidate may find it considerably more difficult than "
                f"most people in the reference group to {ability_text}."
            )

        if percentile <= 24:
            return (
                f"The candidate may find it more difficult than many others "
                f"in the reference group to {ability_text}."
            )

        if percentile <= 74:
            return (
                f"The candidate is likely to find it about as easy as most "
                f"people in the reference group to {ability_text}."
            )

        if percentile <= 90:
            return (
                f"The candidate may find it easier than many others in the "
                f"reference group to {ability_text}."
            )

        return (
            f"The candidate may find it considerably easier than most people "
            f"in the reference group to {ability_text}."
        )

    test_config = [
        {
            "key": "logical",
            "title": "Logical reasoning",
            "measure_label": "Logical reasoning ability",
            "percentile": normalise_percentile(logical_percentile),
        },
        {
            "key": "numerical",
            "title": "Numerical reasoning",
            "measure_label": "Numerical reasoning ability",
            "percentile": normalise_percentile(numerical_percentile),
        },
        {
            "key": "verbal",
            "title": "Verbal reasoning",
            "measure_label": "Verbal reasoning ability",
            "percentile": normalise_percentile(verbal_percentile),
        },
    ]

    results = []

    for test in test_config:
        percentile = test["percentile"]
        level = get_level(percentile)

        results.append({
            "key": test["key"],
            "title": test["title"],
            "measure_label": test["measure_label"],
            "percentile": percentile,
            "completed": level["completed"],
            "level_key": level["level_key"],
            "level_label": level["level_label"],
            "interpretation": get_interpretation(
                test_key=test["key"],
                percentile=percentile,
            ),
        })

    return results


def build_response_style_results(personality_competencies):
    """
    Build response-style results from Sova personality competencies.

    Sova/API mapping:
    - Social Desirability -> Social Desirability
    - Fillers -> Profile Spread
    - Reliability -> Ratings Spread

    Values are displayed using rounded STEN scores from 1 to 10.

    The scale starts from the centre:
    - 1-5 extend towards the left
    - 6-10 extend towards the right
    """

    competency_lookup = {
        (item.get("competency") or "").strip().lower(): item
        for item in personality_competencies
    }

    style_config = [
        {
            "key": "social_desirability",
            "title": "Social Desirability",
            "source_name": "social desirability",

            "low_pole": (
                "Tends to respond in a self-critical way. "
                "May have clearer preferences than the results suggest."
            ),
            "high_pole": (
                "Presented themselves in a positive way. "
                "Some preferences may be less distinct than the results suggest."
            ),

            "low_text": (
                "The response pattern suggests a relatively self-critical "
                "presentation. Some preferences may be more pronounced than "
                "the results indicate."
            ),
            "middle_text": (
                "The response pattern appears reasonably balanced, with no "
                "clear tendency towards either self-critical or overly "
                "positive self-presentation."
            ),
            "high_text": (
                "The response pattern suggests a positive self-presentation. "
                "Some preferences may be less pronounced than the results "
                "indicate."
            ),
        },
        {
            "key": "profile_spread",
            "title": "Profile Spread",
            "source_name": "fillers",

            "low_pole": (
                "The responses show less differentiation between personality "
                "traits. This may reflect less consistency or limited "
                "self-insight."
            ),
            "high_pole": (
                "The responses show clear strengths and development needs, "
                "with a broad spread of scores across personality traits."
            ),

            "low_text": (
                "The responses show less differentiation across personality "
                "traits. This may reflect a more general response pattern or "
                "less consistency between related responses."
            ),
            "middle_text": (
                "The profile contains a mixture of differentiated and less "
                "differentiated responses. The candidate is likely to recognise "
                "some parts of the profile more strongly than others."
            ),
            "high_text": (
                "The responses show clear differentiation across personality "
                "traits, producing a profile with distinct strengths and areas "
                "that may be more demanding."
            ),
        },
        {
            "key": "ratings_spread",
            "title": "Ratings Spread",
            "source_name": "reliability",

            "low_pole": (
                "The questionnaire responses show less use of extreme options "
                "and a tendency to choose from a relatively narrow range of ratings."
            ),
            "high_pole": (
                "The questionnaire responses show clear differentiation, "
                "with greater use of extreme response options."
            ),

            "low_text": (
                "The candidate used fewer extreme response options and tended "
                "to select a relatively narrow range of ratings."
            ),
            "middle_text": (
                "The candidate appears to have used the full response scale "
                "without a strong preference for either middle or extreme "
                "response options."
            ),
            "high_text": (
                "The candidate used a wide range of response options, with "
                "greater use of the extreme ends of the rating scale."
            ),
        },
    ]

    response_styles = []

    for config in style_config:
        source = competency_lookup.get(config["source_name"])

        raw_value = (
            source.get("sten_rounded")
            if source
            else None
        )

        try:
            value = (
                int(round(float(raw_value)))
                if raw_value is not None
                else None
            )
        except (TypeError, ValueError):
            value = None

        if value is not None:
            value = max(1, min(10, value))

        # -------------------------------------------------
        # RESULT BAND AND INTERPRETATION
        # -------------------------------------------------

        if value is None:
            band_key = "missing"
            band_label = "Not available"
            interpretation = (
                "No response-style result is available for this assessment."
            )

        elif value <= 3:
            band_key = "low"
            band_label = "Low"
            interpretation = config["low_text"]

        elif value <= 7:
            band_key = "middle"
            band_label = "Typical"
            interpretation = config["middle_text"]

        else:
            band_key = "high"
            band_label = "High"
            interpretation = config["high_text"]

        # -------------------------------------------------
        # CENTRED SCALE
        #
        # 1  = five segments towards the left
        # 5  = one segment towards the left
        # 6  = one segment towards the right
        # 10 = five segments towards the right
        # -------------------------------------------------

        if value is None:
            scale_side = None
            scale_strength = 0

        elif value <= 5:
            scale_side = "left"
            scale_strength = 6 - value

        else:
            scale_side = "right"
            scale_strength = value - 5

        response_styles.append({
            "key": config["key"],
            "title": config["title"],

            # Static descriptions of both sides of the scale.
            "low_pole": config["low_pole"],
            "high_pole": config["high_pole"],

            # Candidate-specific result.
            "value": value,
            "available": value is not None,
            "band_key": band_key,
            "band_label": band_label,
            "interpretation": interpretation,

            # Used by the centred scale in the template.
            "scale_side": scale_side,
            "scale_strength": scale_strength,

            # Original Sova information.
            "source_name": (
                source.get("competency")
                if source
                else None
            ),
            "percentile": (
                source.get("percentile")
                if source
                else None
            ),
        })

    return response_styles

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


def build_motivation_insight_section(
    mq_competencies,
    candidate_name="",
):
    """
    Build the complete motivation profile used in Candidate Insights.

    Motivation results are displayed using rounded STIVE scores from 1 to 5.

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
            "stive_rounded",
            "score",
            "stive",
        ):
            value = item.get(key)

            if value is None:
                continue

            try:
                score = int(round(float(value)))
            except (TypeError, ValueError):
                continue

            return max(1, min(5, score))

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
                    "name": "Attachment",
                    "aliases": [
                        "attachment",
                        "affiliation",
                    ],
                    "description": (
                        "Social interaction, support and working as part "
                        "of a team."
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
                        "Understanding customer needs and providing "
                        "helpful service."
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
                        "Maintaining a sustainable balance between work "
                        "and life outside work."
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
                        "Helping other people learn, grow and develop."
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
                        "Predictability, continuity and security in the "
                        "working environment."
                    ),
                },
            ],
        },
        {
            "key": "influence",
            "title": "Influence",
            "subtitle": (
                "Independence, recognition and opportunities to shape outcomes"
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
                        "Status, seniority and the opportunity to influence "
                        "or lead others."
                    ),
                },
                {
                    "key": "independence",
                    "name": "Independence",
                    "aliases": [
                        "independence",
                        "autonomy",
                        "self determination",
                        "self direction",
                    ],
                    "description": (
                        "Freedom to make decisions and shape how work "
                        "is carried out."
                    ),
                },
                {
                    "key": "recognition",
                    "name": "Recognition",
                    "aliases": [
                        "recognition",
                    ],
                    "description": (
                        "Visibility, praise and acknowledgement for "
                        "personal contribution."
                    ),
                },
                {
                    "key": "making_a_difference",
                    "name": "Making a Difference",
                    "aliases": [
                        "making a difference",
                        "make a difference",
                        "purpose",
                    ],
                    "description": (
                        "Contributing to a wider purpose or creating "
                        "positive impact."
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
                        "Financial reward, resources and tangible gain."
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
                        "Clear goals, challenge and a visible sense of progress."
                    ),
                },
                {
                    "key": "quality",
                    "name": "Quality",
                    "aliases": [
                        "quality",
                    ],
                    "description": (
                        "Producing accurate and reliable work to a high standard."
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
                        "Developing knowledge, capability and new skills."
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
                        "Acting in line with clear principles and "
                        "ethical standards."
                    ),
                },
                {
                    "key": "commercial_focus",
                    "name": "Commercial Focus",
                    "aliases": [
                        "commercial focus",
                        "commercial value",
                        "commercially focused",
                    ],
                    "description": (
                        "Creating measurable commercial value and "
                        "business results."
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
                        "Exploring new information, questions and "
                        "unfamiliar problems."
                    ),
                },
                {
                    "key": "creativity",
                    "name": "Creativity",
                    "aliases": [
                        "creativity",
                    ],
                    "description": (
                        "Generating new ideas and finding original approaches."
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
                        "Positive energy and enjoyment in day-to-day work."
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
                        "Change, different tasks and varied ways of working."
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
                        "Taking calculated risks and acting despite uncertainty."
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

    for domain_config in motivation_model:
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

    # Safety net:
    # Show any result returned by Sova that was not matched by the model above.
    unmatched_items = []

    for source in mq_competencies or []:
        if id(source) in used_source_ids:
            continue

        score = get_score(source)
        source_name = (
            source.get("competency") or ""
        ).strip()

        if score is None or not source_name:
            continue

        band = get_band(score)

        item = {
            "key": normalise_name(source_name).replace(" ", "_"),
            "name": source_name,
            "description": (
                "An additional motivation factor returned by the "
                "assessment provider."
            ),
            "score": score,
            "available": True,
            "segments": build_segments(score),
            "band_key": band["key"],
            "band_label": band["label"],
            "percentile": source.get("percentile"),
            "source_name": source_name,
            "order": item_order,

            # Fallback interpretation data for motivation results
            # that were not matched against motivation_model.
            "summary_phrase": (
                f"the motivational factor {source_name.lower()}"
            ),
            "support_phrase": (
                f"opportunities connected to {source_name.lower()}"
            ),
            "top_interpretation": (
                f"{candidate_label} appears to place relatively high importance "
                f"on {source_name.lower()}. This result should be explored further "
                f"with the candidate to understand what it means in their working "
                f"context."
            ),
        }

        item_order += 1
        unmatched_items.append(item)
        all_items.append(item)

    if unmatched_items:
        domains.append({
            "key": "other",
            "title": "Other Results",
            "subtitle": (
                "Additional factors returned by the assessment"
            ),
            "icon_class": "fa-solid fa-circle-nodes",
            "items": unmatched_items,
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

    question = str(
        item.get("question")
        or ""
    ).strip()

    if not question:
        return None

    why = str(
        item.get("why")
        or ""
    ).strip()

    listen_for = str(
        item.get("listen_for")
        or ""
    ).strip()

    raw_traits = item.get("traits")
    traits = []

    if isinstance(raw_traits, list):
        traits = [
            str(trait).strip()
            for trait in raw_traits
            if str(trait).strip()
        ]

    return {
        "question": question,
        "why": why,
        "listen_for": listen_for,
        "traits": traits,
    }


def build_combined_candidate_questions(
    invitation,
) -> dict:
    """
    Collect saved questions from Personality, Motivation and Cognitive.

    No additional AI generation happens here.
    """

    question_sources = [
        {
            "key": "personality",
            "title": "Personality questions",
            "description": (
                "Explore how relevant personality preferences "
                "appear in practical situations."
            ),
            "result_field": "ai_personality_questions",
            "status_field": (
                "ai_personality_questions_status"
            ),
        },
        {
            "key": "motivation",
            "title": "Motivation questions",
            "description": (
                "Explore what may create energy, engagement "
                "and sustainable motivation."
            ),
            "result_field": (
                "ai_motivation_interpretation"
            ),
            "status_field": (
                "ai_motivation_interpretation_status"
            ),
        },
        {
            "key": "cognitive",
            "title": "Cognitive questions",
            "description": (
                "Explore how the cognitive assessment results "
                "relate to practical demands and working methods."
            ),
            "result_field": (
                "ai_cognitive_interpretation"
            ),
            "status_field": (
                "ai_cognitive_interpretation_status"
            ),
        },
    ]

    sections = []
    total_count = 0

    for source in question_sources:
        saved_result = (
            getattr(
                invitation,
                source["result_field"],
                {},
            )
            or {}
        )

        raw_questions = (
            saved_result.get("questions")
            or []
        )

        questions = []

        if isinstance(raw_questions, list):
            for raw_question in raw_questions:
                question = (
                    _normalise_combined_question(
                        raw_question
                    )
                )

                if question:
                    questions.append(question)

        if not questions:
            continue

        status = (
            getattr(
                invitation,
                source["status_field"],
                "not_started",
            )
            or "not_started"
        )

        sections.append({
            "key": source["key"],
            "title": source["title"],
            "description": source["description"],
            "status": status,
            "is_outdated": status == "outdated",
            "questions": questions,
            "question_count": len(questions),
        })

        total_count += len(questions)

    return {
        "sections": sections,
        "total_count": total_count,
        "has_questions": total_count > 0,
    }

def _normalise_final_output_list(
    value,
    *,
    limit=3,
) -> list[str]:
    """
    Return a clean and limited list of displayable strings.
    """

    if not isinstance(value, list):
        return []

    items = []

    for item in value:
        text = str(
            item
            or ""
        ).strip()

        if not text:
            continue

        items.append(text)

        if len(items) >= limit:
            break

    return items


def build_candidate_final_output(
    invitation,
    *,
    combined_questions=None,
) -> dict:
    """
    Assemble the candidate's existing saved AI content into one
    purpose-based final output.

    This function does not make any new AI request.
    """

    process = invitation.process

    overview_result = (
        invitation.ai_purpose_fit
        or {}
    )

    personality_result = (
        invitation.ai_personality_interpretation
        or {}
    )

    motivation_result = (
        invitation.ai_motivation_interpretation
        or {}
    )

    cognitive_result = (
        invitation.ai_cognitive_interpretation
        or {}
    )

    if combined_questions is None:
        combined_questions = (
            build_combined_candidate_questions(
                invitation
            )
        )

    # ---------------------------------------------------------
    # Purpose label
    # ---------------------------------------------------------

    if hasattr(
        process,
        "get_purpose_display",
    ):
        purpose_label = (
            process.get_purpose_display()
            or ""
        ).strip()
    else:
        purpose_label = ""

    if not purpose_label:
        purpose_label = (
            str(
                process.purpose
                or ""
            )
            .replace("_", " ")
            .strip()
            .title()
        )

    if not purpose_label:
        purpose_label = "General insights"

    # ---------------------------------------------------------
    # AI Overview
    # ---------------------------------------------------------

    overview_summary = str(
        overview_result.get("summary")
        or ""
    ).strip()

    overview_supporting = (
        _normalise_final_output_list(
            overview_result.get(
                "key_alignment"
            ),
            limit=3,
        )
    )

    overview_explore = (
        _normalise_final_output_list(
            overview_result.get(
                "areas_to_verify"
            ),
            limit=3,
        )
    )

    suggested_next_step = str(
        overview_result.get(
            "suggested_next_step"
        )
        or ""
    ).strip()

    overview_context_note = str(
        overview_result.get(
            "context_note"
        )
        or ""
    ).strip()

    has_overview = bool(
        overview_summary
        or overview_supporting
        or overview_explore
        or suggested_next_step
    )

    overview_status = (
        invitation.ai_purpose_fit_status
        or "not_started"
    )

    # ---------------------------------------------------------
    # Assessment-specific interpretations
    # ---------------------------------------------------------

    assessment_config = [
        {
            "key": "personality",
            "title": "Personality",
            "description": (
                "Likely behavioural preferences and "
                "how they may appear in practice."
            ),
            "result": personality_result,
            "status": (
                invitation
                .ai_personality_interpretation_status
                or "not_started"
            ),
            "summary_key": "interpretation",
            "support_key": (
                "supportive_patterns"
            ),
            "explore_key": (
                "areas_to_explore"
            ),
        },
        {
            "key": "motivation",
            "title": "Motivation",
            "description": (
                "Possible sources of engagement, energy "
                "and expectation setting."
            ),
            "result": motivation_result,
            "status": (
                invitation
                .ai_motivation_interpretation_status
                or "not_started"
            ),
            "summary_key": "interpretation",
            "support_key": (
                "engagement_conditions"
            ),
            "explore_key": (
                "areas_to_clarify"
            ),
        },
        {
            "key": "cognitive",
            "title": "Cognitive",
            "description": (
                "Indications from the available "
                "reasoning assessments."
            ),
            "result": cognitive_result,
            "status": (
                invitation
                .ai_cognitive_interpretation_status
                or "not_started"
            ),
            "summary_key": "interpretation",
            "support_key": None,
            "explore_key": "considerations",
        },
    ]

    assessment_sections = []

    for config in assessment_config:
        result = config["result"]

        summary = str(
            result.get(
                config["summary_key"]
            )
            or ""
        ).strip()

        support_items = []

        if config["support_key"]:
            support_items = (
                _normalise_final_output_list(
                    result.get(
                        config["support_key"]
                    ),
                    limit=3,
                )
            )

        explore_items = (
            _normalise_final_output_list(
                result.get(
                    config["explore_key"]
                ),
                limit=3,
            )
            if config["explore_key"]
            else []
        )

        if not (
            summary
            or support_items
            or explore_items
        ):
            continue

        status = (
            config["status"]
            or "not_started"
        )

        assessment_sections.append({
            "key": config["key"],
            "title": config["title"],
            "description": (
                config["description"]
            ),
            "summary": summary,
            "support_items": support_items,
            "explore_items": explore_items,
            "status": status,
            "is_outdated": (
                status == "outdated"
            ),
        })

    # ---------------------------------------------------------
    # Status and availability
    # ---------------------------------------------------------

    source_statuses = [
        section["status"]
        for section in assessment_sections
    ]

    if has_overview:
        source_statuses.append(
            overview_status
        )

    has_outdated_content = any(
        status == "outdated"
        for status in source_statuses
    )

    has_questions = bool(
        combined_questions.get(
            "has_questions"
        )
    )

    question_count = int(
        combined_questions.get(
            "total_count"
        )
        or 0
    )

    has_content = bool(
        has_overview
        or assessment_sections
        or has_questions
    )

    return {
        "purpose_label": purpose_label,

        "overview": {
            "summary": overview_summary,
            "supporting": overview_supporting,
            "explore": overview_explore,
            "suggested_next_step": (
                suggested_next_step
            ),
            "context_note": (
                overview_context_note
            ),
            "status": overview_status,
            "is_outdated": (
                overview_status == "outdated"
            ),
            "has_content": has_overview,
        },

        "assessment_sections": (
            assessment_sections
        ),

        "combined_questions": (
            combined_questions
        ),

        "question_count": question_count,
        "has_questions": has_questions,

        "source_count": (
            len(assessment_sections)
            + (1 if has_overview else 0)
        ),

        "has_outdated_content": (
            has_outdated_content
        ),

        "has_content": has_content,
    }


def build_candidate_detail_context(process, invitation):
    candidate = invitation.candidate
    payload = invitation.sova_payload or {}

    raw_sova_payload_json = json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
        default=str,
    )

    activities = invitation.sova_activities or payload.get("activities") or []

    if not activities:
        for phase in payload.get("phases") or []:
            activities.extend(phase.get("activities") or [])

    raw_sova_activities_json = json.dumps(
        activities,
        indent=2,
        ensure_ascii=False,
        default=str,
    )        

    def get_assessment_key(name):
        """
        Converts both ProjectMeta test names and Sova activity names
        into the same internal key, so we can avoid duplicates.
        """
        text = (name or "").strip().lower()

        if "personality" in text or text in {"pq", "personlighet"}:
            return "personality"

        if "motivation" in text or text in {"mq", "motivation questionnaire"}:
            return "motivation"

        if "numerical" in text or "numeric" in text or "numerisk" in text:
            return "numerical"

        if "logical" in text or "logisk" in text:
            return "logical"

        if "verbal" in text:
            return "verbal"

        if "one-question" in text or "one question" in text:
            return "one_question"

        return text


    def get_base_status_for_missing_activity(invitation):
        """
        Status for assessments that are part of the Sova project,
        but do not yet exist in invitation.sova_activities.
        """
        status = (invitation.status or "").strip().lower()

        if status == "completed":
            return "completed"

        if status == "started":
            return "not_started"

        if status == "sent":
            return "sent"

        if status == "created":
            return "created"

        return status or "created"


    def get_display_status(raw_status):
        status = (raw_status or "").strip().lower()

        if status in {
            "completed",
            "complete",
            "finished",
            "done",
            "result available",
            "result_available",
        }:
            return "completed"

        if status in {
            "started",
            "in progress",
            "in_progress",
        }:
            return "started"

        if status in {
            "sent",
            "invited",
        }:
            return "sent"

        if status in {
            "created",
            "not_sent",
            "not sent",
        }:
            return "created"

        if status in {
            "added",
            "not_started",
            "not started",
        }:
            return "not_started"

        # Sova can return pass/fail for small scored assessments.
        return status or "created"


    def build_sent_assessments(process, invitation, activities):
        """
        Shows the actual assessments included in the Sova project.

        Base source:
        - ProjectMeta.tests, based on process.account_code + process.project_code

        Status source:
        - invitation.sova_activities, when available

        Matching:
        - Uses internal assessment keys instead of exact display names.
        """

        meta = ProjectMeta.objects.filter(
            provider="sova",
            account_code=process.account_code,
            project_code=process.project_code,
        ).first()

        tests_raw = (getattr(meta, "tests", "") or "").strip() if meta else ""

        project_tests = [
            test_name.strip()
            for test_name in tests_raw.split(",")
            if test_name.strip()
        ]

        activity_by_key = {}

        for item in activities:
            activity_name = item.get("activity") or ""
            activity_key = get_assessment_key(activity_name)

            if activity_key:
                activity_by_key[activity_key] = item

        base_status = get_base_status_for_missing_activity(invitation)
        sent_assessments = []
        used_keys = set()

        # 1. Start with the actual tests in ProjectMeta.
        for test_name in project_tests:
            test_key = get_assessment_key(test_name)
            matching_activity = activity_by_key.get(test_key)

            if matching_activity:
                display_name = matching_activity.get("activity") or test_name
                status = get_display_status(matching_activity.get("status"))
                source = "sova_activity"
            else:
                display_name = test_name
                status = base_status
                source = "project_meta"

            sent_assessments.append({
                "activity": display_name,
                "status": status,
                "source": source,
                "key": test_key,
            })

            used_keys.add(test_key)

        # 2. Safety net: add Sova activities only if their key was not already shown.
        for item in activities:
            activity_name = item.get("activity") or ""
            activity_key = get_assessment_key(activity_name)

            if activity_key and activity_key not in used_keys:
                sent_assessments.append({
                    "activity": activity_name,
                    "status": get_display_status(item.get("status")),
                    "source": "sova_activity_extra",
                    "key": activity_key,
                })

                used_keys.add(activity_key)

        return sent_assessments


    sent_assessments = build_sent_assessments(
        process=process,
        invitation=invitation,
        activities=activities,
    )

    activity_events = (
        ActivityEvent.objects
        .filter(company=process.company, process=process, candidate=candidate)
        .select_related("actor", "candidate", "invitation")[:50]
    )

    from apps.emails.models import EmailLog

    email_log_ids = [
        (event.meta or {}).get("email_log_id")
        for event in activity_events
        if (event.meta or {}).get("email_log_id")
    ]

    email_logs_by_id = {
        log.id: log
        for log in EmailLog.objects.filter(id__in=email_log_ids)
    }

    for event in activity_events:
        email_log_id = (event.meta or {}).get("email_log_id")
        event.email_log = email_logs_by_id.get(email_log_id)

    def has_real_result(competencies):
        return any(
            comp.get("score") is not None
            or comp.get("stive") is not None
            or comp.get("stive_rounded") is not None
            or comp.get("sten") is not None
            or comp.get("sten_rounded") is not None
            or comp.get("percentile") is not None
            for comp in competencies
        )

    activity_count = len(sent_assessments)

    completed_statuses = {
        "completed",
        "complete",
        "finished",
        "done",
        "result available",
        "result_available",
    }

    tests_completed_count = sum(
        1
        for activity in activities
        if (activity.get("status") or "").strip().lower() in completed_statuses
    )

    has_any_completed_assessment = tests_completed_count > 0

    all_assessments_completed = (
        activity_count > 0
        and tests_completed_count >= activity_count
    )

    mq_competencies = []
    personality_competencies = []
    has_motivation_results = False
    has_personality_results = False

    for item in activities:
        activity_name = (item.get("activity") or "").strip().lower()
        competencies = item.get("competencies", []) or []

        is_motivation_activity = (
            activity_name == "motivation questionnaire"
            or activity_name == "sova motivation questionnaire"
            or "motivation" in activity_name
        )

        if is_motivation_activity:
            if has_real_result(competencies):
                has_motivation_results = True

            for comp in competencies:
                mq_competencies.append({
                    "competency": comp.get("competency"),
                    "score": comp.get("stive_rounded"),
                    "stive_rounded": comp.get("stive_rounded"),
                    "stive": comp.get("stive"),
                    "sten_rounded": comp.get("sten_rounded"),
                    "sten": comp.get("sten"),
                    "percentile": comp.get("percentile"),
                })

        is_personality_activity = (
            activity_name == "personality assessment"
            or activity_name == "sova personality questionnaire"
            or "personality" in activity_name
        )

        if is_personality_activity:
            if has_real_result(competencies):
                has_personality_results = True

            for comp in competencies:
                personality_competencies.append({
                    "competency": comp.get("competency"),

                    # Team styles use Sova's five-point STIVE scale.
                    "stive": comp.get("stive"),
                    "stive_rounded": comp.get("stive_rounded"),

                    # Ordinary personality traits and response styles use STEN.
                    "sten": comp.get("sten"),
                    "sten_rounded": comp.get("sten_rounded"),

                    "percentile": comp.get("percentile"),
                })

    personality_competencies = sorted(
        personality_competencies,
        key=lambda x: (x.get("competency") or "").lower()
    )

    response_styles = build_response_style_results(
        personality_competencies
    )   

    team_style_profile = build_team_style_profile(
        personality_competencies
    )

    motivation_scores = build_scores_by_competency(mq_competencies)

    motivation_insights = build_motivation_insight_section(
        mq_competencies,
        candidate_name=candidate.first_name,
    )

    practitioner_report = build_practitioner_report(
        competencies=mq_competencies,
    )

    manager_report = build_manager_report(
        competencies=mq_competencies,
    )

    candidate_report = build_candidate_report(
        competencies=mq_competencies,
    )

    coaching_report = build_motivation_coaching_report(
        competencies=mq_competencies,
    )

    personality_traits_for_selection = (
        extract_personality_results(
            invitation
        )
    )

    motivation_reports_for_ui = [
        practitioner_report,
        manager_report,
        coaching_report,
        candidate_report,
    ]

    def safe_motivation_score(item):
        return item.get("score") if item.get("score") is not None else -1

    def safe_personality_score(item):
        return item.get("sten_rounded") if item.get("sten_rounded") is not None else -1

    valid_mq_competencies = [
        comp for comp in mq_competencies
        if comp.get("score") is not None
    ]

    valid_personality_competencies = [
        comp for comp in personality_competencies
        if comp.get("sten_rounded") is not None
    ]

    sorted_mq_desc = sorted(
        valid_mq_competencies,
        key=safe_motivation_score,
        reverse=True,
    )

    sorted_personality_desc = sorted(
        valid_personality_competencies,
        key=safe_personality_score,
        reverse=True,
    )

    top_motivations = sorted_mq_desc[:3]
    top_personality_traits = sorted_personality_desc[:3]

    sorted_mq_asc = sorted(
        valid_mq_competencies,
        key=safe_motivation_score,
    )

    sorted_personality_asc = sorted(
        valid_personality_competencies,
        key=safe_personality_score,
    )

    motivation_development_areas = sorted_mq_asc[:2]
    personality_development_areas = sorted_personality_asc[:2]

    numerical_percentile = None
    logical_percentile = None
    verbal_percentile = None

    has_verbal_results = False
    has_logical_results = False
    has_numerical_results = False

    for item in activities:
        activity_name = item.get("activity", "")
        activity_key = get_assessment_key(activity_name)

        competencies = item.get("competencies", []) or []
        first_comp = competencies[0] if competencies else {}

        percentile = first_comp.get("percentile")

        if activity_key == "numerical":
            numerical_percentile = percentile
            has_numerical_results = percentile is not None

        elif activity_key == "logical":
            logical_percentile = percentile
            has_logical_results = percentile is not None

        elif activity_key == "verbal":
            verbal_percentile = percentile
            has_verbal_results = percentile is not None

    has_ability_results = (
        has_verbal_results
        or has_logical_results
        or has_numerical_results
    )

    general_insight_input = build_general_insight_input(
        personality_competencies=personality_competencies,
        motivation_competencies=mq_competencies,
        verbal_percentile=verbal_percentile,
        logical_percentile=logical_percentile,
        numerical_percentile=numerical_percentile,
    )

    print("=== GENERAL INSIGHT INPUT ===")
    print(json.dumps(
        general_insight_input,
        indent=2,
        ensure_ascii=False,
        default=str,
    ))
    print("=== /GENERAL INSIGHT INPUT ===")

    ability_reports_for_ui = {
        "overview": [],
        "verbal": build_cognitive_reports_for_test(
            test_key="verbal",
            percentile=verbal_percentile,
        ) if verbal_percentile is not None else None,

        "logical": build_cognitive_reports_for_test(
            test_key="logical",
            percentile=logical_percentile,
        ) if logical_percentile is not None else None,

        "numerical": build_cognitive_reports_for_test(
            test_key="numerical",
            percentile=numerical_percentile,
        ) if numerical_percentile is not None else None,
    }

    if ability_reports_for_ui["verbal"]:
        ability_reports_for_ui["overview"].append({
            "key": "verbal",
            "label": "Verbal",
            "percentile": verbal_percentile,
        })

    if ability_reports_for_ui["logical"]:
        ability_reports_for_ui["overview"].append({
            "key": "logical",
            "label": "Logical",
            "percentile": logical_percentile,
        })

    if ability_reports_for_ui["numerical"]:
        ability_reports_for_ui["overview"].append({
            "key": "numerical",
            "label": "Numerical",
            "percentile": numerical_percentile,
        })

    project_results = invitation.project_results or {}
    reports = invitation.sova_reports or payload.get("reports") or []

    sova_reports_for_ui = build_sova_reports_for_ui(
        reports
    )

    project_scores = (
        project_results.get("project_scores", [])
        if isinstance(project_results, dict)
        else []
    )

    competency_scores = (
        project_results.get("competency_scores", [])
        if isinstance(project_results, dict)
        else []
    )

    overall_score = (
        project_results.get("overall_score")
        if isinstance(project_results, dict)
        and project_results.get("overall_score") is not None
        else invitation.overall_score
    )

    combined_questions = (
        build_combined_candidate_questions(
            invitation
        )
    )

    final_output = (
        build_candidate_final_output(
            invitation,
            combined_questions=combined_questions,
        )
    )

    ability_results = []
    motivation_results = []
    all_competencies = []

    for item in activities:
        activity_name = item.get("activity", "") or ""
        item_status = item.get("status", "") or ""
        item_score = item.get("score")
        item_competencies = item.get("competencies", []) or []

        for comp in item_competencies:
            all_competencies.append({
                "activity": activity_name,
                "status": item_status,
                "competency": comp.get("competency"),
                "stive": comp.get("stive"),
                "stive_rounded": comp.get("stive_rounded"),
                "sten": comp.get("sten"),
                "sten_rounded": comp.get("sten_rounded"),
                "percentile": comp.get("percentile"),
                "assessment_centre": comp.get("assessment_centre"),
            })

        if activity_name in {
            "Sova Logical Reasoning Assessment",
            "Sova Numerical Reasoning Assessment",
            "Sova Verbal Reasoning Assessment",
        }:
            first_comp = item_competencies[0] if item_competencies else {}

            label_map = {
                "Sova Logical Reasoning Assessment": "Logical",
                "Sova Numerical Reasoning Assessment": "Numerical",
                "Sova Verbal Reasoning Assessment": "Verbal",
            }

            ability_results.append({
                "activity": activity_name,
                "label": label_map.get(activity_name, activity_name),
                "status": item_status,
                "score": item_score,
                "competency": first_comp.get("competency"),
                "stive": first_comp.get("stive"),
                "stive_rounded": first_comp.get("stive_rounded"),
                "sten": first_comp.get("sten"),
                "sten_rounded": first_comp.get("sten_rounded"),
                "percentile": first_comp.get("percentile"),
            })

        elif activity_name == "Motivation Questionnaire":
            for comp in item_competencies:
                motivation_results.append({
                    "activity": activity_name,
                    "competency": comp.get("competency"),
                    "stive": comp.get("stive"),
                    "stive_rounded": comp.get("stive_rounded"),
                    "sten": comp.get("sten"),
                    "sten_rounded": comp.get("sten_rounded"),
                    "percentile": comp.get("percentile"),
                    "assessment_centre": comp.get("assessment_centre"),
                })

    ability_order = {"Verbal": 1, "Logical": 2, "Numerical": 3}
    ability_results.sort(key=lambda x: ability_order.get(x["label"], 99))

    motivation_results.sort(
        key=lambda x: (x.get("competency") or "").lower()
    )

    library_status_lookup = {
        "cooperative": "not_started",
        "sensitivity": "not_started",
        "teamwork": "not_started",
        "agreeableness": "not_started",
        "empathy": "not_started",
        "tolerance": "not_started",
        "listening": "not_started",
        "warmth": "not_started",
        "supporting": "not_started",
        "developing_others": "not_started",
        "helpfulness": "not_started",
        "considerate": "not_started",
        "connecting": "not_started",
        "open_communication": "not_started",
        "building_networks": "not_started",
        "initiating_contact": "not_started",
        "dynamic": "not_started",
        "energetic": "not_started",
        "enthusiastic": "not_started",
        "risk_appetite": "not_started",
        "influential": "not_started",
        "persuading": "not_started",
        "desire_to_lead": "not_started",
        "assertive": "not_started",
        "goal_focused": "not_started",
        "competitive": "not_started",
        "challenge": "not_started",
        "self_discipline": "not_started",
        "structured": "not_started",
        "planning_and_organising": "not_started",
        "attention_to_detail": "not_started",
        "keeping_promises": "not_started",
        "analytical": "not_started",
        "data_focus": "not_started",
        "evaluating": "not_started",
        "analysing_problems": "not_started",
        "complex_thinking": "not_started",
        "strategic_thinking": "not_started",
        "conceptual": "not_started",
        "curiosity": "not_started",
        "creativity": "not_started",
        "innovating": "not_started",
        "generating_ideas": "not_started",
        "experimenting": "not_started",
        "adaptability": "not_started",
        "adapting_to_change": "not_started",
        "flexible": "not_started",
        "variety": "not_started",
        "straightforward": "not_started",
        "adhering_to_rules": "not_started",
        "candid": "not_started",
        "earnest": "not_started",
        "status_avoidance": "not_started",
        "egalitarian": "not_started",
        "collective": "not_started",
        "avoiding_status": "not_started",
        "modesty": "not_started",
        "humble": "not_started",
        "modest": "not_started",
        "avoiding_attention": "not_started",
        "resilience": "not_started",
        "tough_minded": "not_started",
        "recovering": "not_started",
        "optimistic": "not_started",
        "emotional_control": "not_started",
        "controlling_stress": "not_started",
        "calm": "not_started",
        "composed": "not_started",
        "independence": "not_started",
        "self_reliant": "not_started",
        "self_contained": "not_started",
        "thinking_independently": "not_started",
    }

    personality_reports = build_personality_reports_for_candidate(
        sova_activities=activities,
        library_status_lookup=library_status_lookup,
    )

    personality_reports = build_personality_reports_for_candidate(
        sova_activities=activities,
        library_status_lookup=library_status_lookup,
    )

    personality_profile_report = next(
        (
            report
            for report in personality_reports
            if report.get("report_id") == "trait_indicator_profile"
        ),
        None,
    )

    personality_profile = (
        build_profile_from_resolved_report(
            resolved_report=personality_profile_report,
            language="sv",
            include_missing_traits=False,
        )
        if personality_profile_report
        else None
    )

    available_reports_count = 0

    if has_verbal_results:
        available_reports_count += 2

    if has_numerical_results:
        available_reports_count += 2

    if has_logical_results:
        available_reports_count += 2

    if has_motivation_results:
        available_reports_count += 4

    if has_personality_results:
        available_reports_count += 11

    has_any_results = (
        has_ability_results
        or has_motivation_results
        or has_personality_results
    )

    purpose_report = get_report_mode_content(process.purpose)

    print("=== PURPOSE REPORT DEBUG ===")
    print("PROCESS PURPOSE:", repr(process.purpose))
    print("PURPOSE REPORT:", purpose_report)
    print("=== /PURPOSE REPORT DEBUG ===")

    # ------------------------------------------------------------
    # Purpose context / report mode
    # ------------------------------------------------------------
    # For now we still use the existing ProcessRoleContext model,
    # but expose it to templates as both role_context and purpose_context.
    # This lets us move towards a more general "purpose context" setup
    # without renaming models or breaking old templates.
    purpose_context_obj = getattr(process, "role_context", None)
    role_context_obj = purpose_context_obj

    has_purpose_context = (
        purpose_context_obj.has_content()
        if purpose_context_obj
        else False
    )

    context_title = ""

    if has_purpose_context:
        context_title = (
            purpose_context_obj.role_title
            or purpose_context_obj.job_advertisement[:80]
            or "this process context"
        )

    # Backwards-compatible name for existing templates
    has_role_context = has_purpose_context

    context_config = get_purpose_context_config(process.purpose)

    # New report mode:
    # - "general" = no added context, only test-based insights
    # - "context" = test data + purpose + added context
    candidate_insights_mode = (
        "context"
        if has_purpose_context
        else "general"
    )

    # Keep the old purpose/report key available separately.
    # Do not use this as the general/context mode.
    purpose_report_key = purpose_report.get("key")

    show_role_context_prompt = not has_purpose_context
    show_context_prompt = show_role_context_prompt

    show_context_prompt = show_role_context_prompt

    critical_competencies_active = has_purpose_context
    competency_overview_active = not has_purpose_context

    report_mode = "context" if has_purpose_context else "general"

    # ------------------------------------------------------------
    # Temporary dummy data for Candidate Insights
    # Later this can be replaced by structured AI JSON output.
    # ------------------------------------------------------------

    candidate_insights = build_candidate_insights(
        mode=candidate_insights_mode,
        general_insight_input=general_insight_input,
        process_purpose=process.purpose,
    )

    candidate_insights["cognitive_results"] = (
        build_cognitive_insight_results(
            verbal_percentile=verbal_percentile,
            logical_percentile=logical_percentile,
            numerical_percentile=numerical_percentile,
        )
    )

    print("=== FLEXIBLE AI CONDITION DEBUG ===")
    print("PROCESS PURPOSE:", repr(process.purpose))
    print("PURPOSE IS FLEXIBLE:", process.purpose == "flexible")
    print("HAS ANY RESULTS:", has_any_results)
    print("HAS PERSONALITY RESULTS:", has_personality_results)
    print("HAS MOTIVATION RESULTS:", has_motivation_results)
    print("HAS ABILITY RESULTS:", has_ability_results)
    print("=== /FLEXIBLE AI CONDITION DEBUG ===")

    return {
        "company": process.company,
        "process": process,
        "invitation": invitation,
        "inv": invitation,
        "candidate": candidate,
        "activity_events": activity_events,

        "activities": activities,
        "sent_assessments": sent_assessments,
        "project_results": project_results,
        "project_scores": project_scores,
        "competency_scores": competency_scores,
        "overall_score": overall_score,
        "reports": reports,

        "ability_results": ability_results,
        "motivation_results": motivation_results,
        "all_competencies": all_competencies,

        "numerical_percentile": numerical_percentile,
        "logical_percentile": logical_percentile,
        "verbal_percentile": verbal_percentile,
        "has_ability_results": has_ability_results,

        "mq_competencies": mq_competencies,
        "personality_competencies": personality_competencies,

        "tests_sent_count": activity_count,
        "tests_completed_count": tests_completed_count,
        "available_reports_count": len(sova_reports_for_ui),
        "email_logs_by_id": email_logs_by_id,
        "sova_reports_for_ui": sova_reports_for_ui,
        "available_reports_count": len(sova_reports_for_ui),

        "has_any_results": has_any_results,
        "has_any_completed_assessment": has_any_completed_assessment,
        "all_assessments_completed": all_assessments_completed,

        "top_motivations": top_motivations,
        "top_personality_traits": top_personality_traits,
        "motivation_development_areas": motivation_development_areas,
        "personality_development_areas": personality_development_areas,

        "motivation_scores": motivation_scores,
        "motivation_reports_for_ui": motivation_reports_for_ui,
        "ability_reports_for_ui": ability_reports_for_ui,
        "personality_reports": personality_reports,
        "personality_profile": personality_profile,
        "has_motivation_results": has_motivation_results,
        "has_personality_results": has_personality_results,

        # Existing report/purpose content
        "purpose_report": purpose_report,
        "purpose_report_key": purpose_report_key,

        # Candidate insights
        "candidate_insights": candidate_insights,
        "candidate_insights_mode": candidate_insights_mode,
        "report_mode": report_mode,
        "general_insight_input": general_insight_input,

        # Purpose context
        "purpose_context": purpose_context_obj,
        "has_purpose_context": has_purpose_context,
        "context_config": context_config,
        "show_context_prompt": show_context_prompt,

        # Backwards-compatible names
        "role_context": role_context_obj,
        "has_role_context": has_role_context,
        "show_role_context_prompt": show_role_context_prompt,

        "summary_owner": invitation,
        "raw_sova_payload_json": raw_sova_payload_json,
        "raw_sova_activities_json": raw_sova_activities_json,

        "response_styles": response_styles,
        "response_style_segments": range(1, 11),

        "response_style_guidance": (
            invitation.ai_response_style_guidance
            or {}
        ),

        "response_style_guidance_status": (
            invitation.ai_response_style_guidance_status
        ),
        "response_style_side_segments": range(1, 6),

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

        # Purpose-based final output
        "final_output": final_output,

        "has_final_output": (
            final_output["has_content"]
        ),

        "final_output_has_outdated_content": (
            final_output[
                "has_outdated_content"
            ]
        ),

        "final_output_refresh_url": reverse(
        (
            "processes:"
            "process_candidate_final_output"
        ),
        kwargs={
            "process_id": process.id,
            "candidate_id": candidate.id,
        },
    ),

        "motivation_insights": motivation_insights,

        "team_style_profile": team_style_profile,
        # Cognitive AI interpretation
        "cognitive_interpretation": (
            invitation.ai_cognitive_interpretation
            or {}
        ),

        "cognitive_interpretation_status": (
            invitation
            .ai_cognitive_interpretation_status
            or "not_started"
        ),

        "cognitive_interpretation_stream_url": reverse(
            (
                "processes:"
                "process_candidate_cognitive_"
                "interpretation_stream"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),

        "cognitive_interpretation_regenerate_url": reverse(
            (
                "processes:"
                "process_candidate_cognitive_"
                "interpretation_regenerate"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),
        # Motivation AI interpretation
        "motivation_interpretation": (
            invitation.ai_motivation_interpretation
            or {}
        ),

        "motivation_interpretation_status": (
            invitation
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

        # Personality AI interpretation
        "personality_interpretation": (
            invitation.ai_personality_interpretation
            or {}
        ),

        "personality_interpretation_status": (
            invitation.ai_personality_interpretation_status
            or "not_started"
        ),

        "personality_interpretation_stream_url": reverse(
            (
                "processes:"
                "process_candidate_personality_"
                "interpretation_stream"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),

        "personality_interpretation_regenerate_url": reverse(
            (
                "processes:"
                "process_candidate_personality_"
                "interpretation_regenerate"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),

        # Personality AI questions
        "personality_questions": (
            invitation.ai_personality_questions
            or {}
        ),

        # Combined assessment questions
        "combined_questions": combined_questions,

        "combined_question_sections": (
            combined_questions["sections"]
        ),

        "combined_questions_refresh_url": reverse(
            (
                "processes:"
                "process_candidate_combined_questions"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),

        "combined_question_count": (
            combined_questions["total_count"]
        ),

        "has_combined_questions": (
            combined_questions["has_questions"]
        ),

        "personality_questions_status": (
            invitation
            .ai_personality_questions_status
            or "not_started"
        ),

        "selected_personality_traits": (
            invitation.selected_personality_traits
            or []
        ),

        "personality_traits_for_selection": (
            personality_traits_for_selection
        ),

        "personality_questions_stream_url": reverse(
            (
                "processes:"
                "process_candidate_personality_"
                "questions_stream"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),

        "personality_questions_regenerate_url": reverse(
            (
                "processes:"
                "process_candidate_personality_"
                "questions_regenerate"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),

        "personality_traits_update_url": reverse(
            (
                "processes:"
                "process_candidate_personality_"
                "traits_update"
            ),
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate.id,
            },
        ),
    }

def get_dashboard_activity_for_user(user, limit=10):
    company = get_company_for_user(user)

    if not company:
        return ActivityEvent.objects.none()

    perms = get_effective_orgunit_permissions(user, company)

    own_ids = [uid for uid, p in perms.items() if p == "own"]
    visible_ids = [uid for uid, p in perms.items() if p in ("viewer", "editor")]

    process_q = Q(company=company, is_archived=False) & (
        Q(org_unit_id__in=visible_ids) |
        Q(org_unit_id__in=own_ids, created_by=user)
    )

    accessible_process_ids = (
        TestProcess.objects
        .filter(process_q)
        .values_list("id", flat=True)
    )

    return (
        ActivityEvent.objects
        .filter(
            company=company,
            process_id__in=accessible_process_ids,
        )
        .select_related(
            "actor",
            "candidate",
            "process",
            "invitation",
        )
        .order_by("-created_at")[:limit]
    )

def _get_active_company_for_user(user):
    # om du bara har 1 company per user just nu: ta första
    m = CompanyMember.objects.select_related("company").filter(user=user).first()
    return m.company if m else None


def user_can_access_process(user, process) -> bool:
    company_id = (
        CompanyMember.objects
        .filter(user=user)
        .values_list("company_id", flat=True)
        .first()
    )
    return bool(company_id and process.company_id == company_id)


@login_required
def process_candidate_final_output(
    request,
    process_id,
    candidate_id,
):
    """
    Return the latest saved candidate final output
    as rendered HTML.
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
            "You do not have access to this process."
        )

    if process.is_historical:
        return JsonResponse(
            {
                "error": (
                    "Historical final output "
                    "is not connected yet."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )

    combined_questions = (
        build_combined_candidate_questions(
            invitation
        )
    )

    final_output = (
        build_candidate_final_output(
            invitation,
            combined_questions=combined_questions,
        )
    )

    refresh_url = reverse(
        (
            "processes:"
            "process_candidate_final_output"
        ),
        kwargs={
            "process_id": process.id,
            "candidate_id": candidate_id,
        },
    )

    return render(
        request,
        (
            "customer/processes/partials/"
            "candidate_insights/tabs/"
            "_final_output.html"
        ),
        {
            "final_output": final_output,

            "has_final_output": (
                final_output["has_content"]
            ),

            "final_output_has_outdated_content": (
                final_output[
                    "has_outdated_content"
                ]
            ),

            "final_output_refresh_url": (
                refresh_url
            ),
        },
    )


@login_required
def process_candidate_combined_questions(
    request,
    process_id,
    candidate_id,
):
    """
    Return the latest saved Personality, Motivation and
    Cognitive questions as rendered HTML.
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
            "You do not have access to this process."
        )

    invitation = get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )

    combined_questions = (
        build_combined_candidate_questions(
            invitation
        )
    )

    refresh_url = reverse(
        (
            "processes:"
            "process_candidate_combined_questions"
        ),
        kwargs={
            "process_id": process.id,
            "candidate_id": candidate_id,
        },
    )

    return render(
        request,
        (
            "customer/processes/partials/"
            "candidate_insights/tabs/_questions.html"
        ),
        {
            "combined_questions": (
                combined_questions
            ),

            "combined_question_sections": (
                combined_questions["sections"]
            ),

            "combined_question_count": (
                combined_questions["total_count"]
            ),

            "has_combined_questions": (
                combined_questions["has_questions"]
            ),

            "combined_questions_refresh_url": (
                refresh_url
            ),
        },
    )


@login_required
def process_list(request):
    company_id = (
        CompanyMember.objects
        .filter(user=request.user)
        .values_list("company_id", flat=True)
        .first()
    )
    company = get_object_or_404(Company, pk=company_id)

    perms = get_effective_orgunit_permissions(request.user, company)

    own_ids = [uid for uid, p in perms.items() if p == "own"]
    other_ids = [uid for uid, p in perms.items() if p in ("viewer", "editor")]

    process_q = Q(company=company) & (
        Q(org_unit_id__in=other_ids) |
        Q(org_unit_id__in=own_ids, created_by=request.user)
    )

    # Tab: Active / Archived
    show_archived = request.GET.get("archived") == "1"

    historical_candidate_count_subquery = (
        HistoricalProcessCandidate.objects
        .filter(process=OuterRef("pk"))
        .values("process")
        .annotate(count=Count("id"))
        .values("count")
    )

    processes = (
        TestProcess.objects
        .filter(process_q)
        .filter(is_archived=show_archived)
        .annotate(
            live_candidates_count=Count("invitations", distinct=True),
            historical_candidates_count=Coalesce(
                Subquery(
                    historical_candidate_count_subquery,
                    output_field=IntegerField(),
                ),
                0,
            ),
        )
        .order_by("-created_at")
        .prefetch_related("labels")
    )

    # Build edit permissions after processes exists
    can_edit_by_process_id = {}
    for p in processes:
        perm = perms.get(p.org_unit_id)
        can_edit = (
            perm == "editor"
            or (perm == "own" and p.created_by_id == request.user.id)
        )
        can_edit_by_process_id[p.id] = can_edit

    # ProjectMeta lookup
    keys = {
        (p.account_code, p.project_code)
        for p in processes
        if p.account_code and p.project_code
    }

    meta_by_key = {}
    if keys:
        q = Q()
        for acc, proj in keys:
            q |= Q(account_code=acc, project_code=proj)

        metas = ProjectMeta.objects.filter(q)
        meta_by_key = {
            f"{m.account_code}::{m.project_code}": m
            for m in metas
        }

    return render(
        request,
        "customer/processes/process_list.html",
        {
            "company": company,
            "processes": processes,
            "meta_by_key": meta_by_key,
            "perms": perms,
            "show_archived": show_archived,
            "can_edit_by_process_id": can_edit_by_process_id,
        }
    )

def get_template_icon_class(tests, title=""):
    """
    Returns a FontAwesome icon class based on the test types/title.
    """
    text = " ".join(tests).lower()
    title = (title or "").lower()

    if "360" in text or "360" in title:
        return "fa-solid fa-arrows-rotate"

    if (
        "numerical" in text
        or "numerisk" in text
        or "färdighet" in text
        or "fardighet" in text
        or "ability" in text
        or "skills" in text
    ):
        return "fa-solid fa-chart-simple"

    if (
        "personality" in text
        or "personlighet" in text
        or "pq" in title
    ):
        return "fa-solid fa-user-check"

    if (
        "motivation" in text
        or "motivationstest" in text
    ):
        return "fa-solid fa-bullseye"

    if "leadership" in text or "ledarskap" in text:
        return "fa-solid fa-award"

    if "sales" in text or "sälj" in title or "salj" in title:
        return "fa-solid fa-handshake"

    if "admin" in text or "interim" in text or "interim" in title:
        return "fa-solid fa-briefcase"

    if "modern" in title:
        return "fa-solid fa-wand-magic-sparkles"

    if "linear" in title:
        return "fa-solid fa-wave-square"

    if "ihp" in title:
        return "fa-solid fa-layer-group"

    return "fa-solid fa-layer-group"


@login_required
def process_create(request):
    client = SovaClient()
    error = None

    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    choices = []
    template_cards = []
    project_id_map = {}

    for a in accounts:
        acc = (a.get("code") or "").strip()
        for p in (a.get("projects") or []):
            proj_code = (p.get("code") or "").strip()
            sova_name = (p.get("name") or proj_code).strip()

            value = f"{acc}|{proj_code}"
            project_id_map[value] = p.get("id")

            meta = meta_map.get((acc, proj_code))

            title = (getattr(meta, "intern_name", None) or sova_name)

            description = ""
            tests = []
            languages = []

            if meta:
                description = (getattr(meta, "notes", None) or "").strip()

                tests_raw = (getattr(meta, "tests", None) or "").strip()
                if tests_raw:
                    tests = [t.strip() for t in tests_raw.split(",") if t.strip()]

                languages_raw = (getattr(meta, "languages", None) or "").strip()
                if languages_raw:
                    languages = [l.strip() for l in languages_raw.split(",") if l.strip()]

            choices.append((value, title))
            template_cards.append({
                "value": value,
                "title": title,
                "description": description,
                "tests": tests,
                "languages": languages,
                "icon_class": get_template_icon_class(tests, title),
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
                "sova_project_id": p.get("id"),
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    if request.method == "POST":
        form = TestProcessCreateForm(request.POST)
        form.fields["sova_template"].choices = choices

        if form.is_valid():
            obj = form.save(commit=False)

            value = form.cleaned_data["sova_template"]
            acc, proj = value.split("|", 1)

            # ✅ sätt company (kundens “konto”)
            company_id = (
                CompanyMember.objects
                .filter(user=request.user)
                .values_list("company_id", flat=True)
                .first()
            )
            if not company_id:
                form.add_error(None, "You are not linked to a company.")
                return render(request, "customer/processes/process_create.html", {
                    "form": form,
                    "error": error,
                    "template_cards": template_cards,
                    "templates_count": len(template_cards),
                    "accounts_count": len(accounts),
                })

            obj.company_id = company_id

            
            # ✅ sätt org_unit från session (active org unit)
            active_unit_id = request.session.get("active_org_unit_id")

            company = Company.objects.get(pk=company_id)
            accessible_ids = get_accessible_orgunit_ids(request.user, company)

            if not active_unit_id or int(active_unit_id) not in accessible_ids:
                # fallback: välj en direkt/åtkomlig unit automatiskt
                fallback_id = next(iter(accessible_ids), None)
                if not fallback_id:
                    form.add_error(None, "You do not have an assigned org unit, so a process cannot be created.")
                    return render(request, "customer/processes/process_create.html", {
                        "form": form,
                        "error": error,
                        "template_cards": template_cards,
                        "templates_count": len(template_cards),
                        "accounts_count": len(accounts),
                    })
                active_unit_id = fallback_id
                request.session["active_org_unit_id"] = active_unit_id

            obj.org_unit_id = int(active_unit_id)

            # ✅ endast SOVA-referenser
            obj.provider = "sova"
            obj.account_code = acc
            obj.project_code = proj
            obj.sova_project_id = project_id_map.get(value)

            meta = meta_map.get((acc, proj))
            obj.project_name_snapshot = (getattr(meta, "intern_name", None) or "")
            if not obj.project_name_snapshot:
                match = next((t for t in template_cards if t["value"] == value), None)
                obj.project_name_snapshot = (match["sova_name"] if match else proj)

            obj.created_by = request.user

            membership = (
                CompanyMember.objects
                .filter(user=request.user, company_id=company_id)
                .select_related("primary_org_unit")
                .first()
            )

            if not membership or not membership.primary_org_unit_id:
                form.add_error(None, "You do not have a primary org unit. Please contact an administrator.")
                return render(request, "customer/processes/process_create.html", {
                    "form": form,
                    "error": error,
                    "template_cards": template_cards,
                    "templates_count": len(template_cards),
                    "accounts_count": len(accounts),
                })

            obj.org_unit_id = membership.primary_org_unit_id

            obj.save()

            log_event(
                company=company, 
                verb=ActivityEvent.Verb.PROCESS_CREATED,
                actor=request.user,
                process=obj,
                meta={"process_name": obj.name},
            )

            # ✅ LABELS: skapa/återanvänd labels per company och koppla
            label_names = form.cleaned_data.get("labels_text", [])
            if label_names:
                label_objs = []
                for name in label_names:
                    lab, _ = ProcessLabel.objects.get_or_create(
                        company_id=company_id,
                        name=name,
                    )
                    label_objs.append(lab)
                obj.labels.set(label_objs)
            else:
                obj.labels.clear()

            return redirect("processes:process_detail", pk=obj.pk)

        messages.error(request, "The process could not be created. Please check the fields.")
    else:
        form = TestProcessCreateForm()
        form.fields["sova_template"].choices = choices

    return render(request, "customer/processes/process_create.html", {
        "form": form,
        "error": error,
        "template_cards": template_cards,
        "templates_count": len(template_cards),
        "accounts_count": len(accounts),
    })

def mark_candidate_ai_content_outdated(process):
    """
    Keep existing AI content, but mark it as needing regeneration.

    Existing content remains saved until a replacement has been
    generated successfully.
    """

    invitations = TestInvitation.objects.filter(
        process=process,
    )

    summary_count = (
        invitations
        .exclude(ai_summary="")
        .update(ai_summary_status="outdated")
    )

    purpose_fit_count = (
        invitations
        .exclude(ai_purpose_fit={})
        .update(ai_purpose_fit_status="outdated")
    )

    cognitive_interpretation_count = (
        invitations
        .exclude(ai_cognitive_interpretation={})
        .update(
            ai_cognitive_interpretation_status="outdated"
        )
    )

    response_style_guidance_count = (
        invitations
        .exclude(ai_response_style_guidance={})
        .update(
            ai_response_style_guidance_status="outdated"
        )
    )

    motivation_interpretation_count = (
        invitations
        .exclude(ai_motivation_interpretation={})
        .update(
            ai_motivation_interpretation_status="outdated"
        )
    )

    personality_interpretation_count = (
        invitations
        .exclude(ai_personality_interpretation={})
        .update(
            ai_personality_interpretation_status="outdated"
        )
    )

    personality_questions_count = (
        invitations
        .exclude(ai_personality_questions={})
        .update(
            ai_personality_questions_status="outdated"
        )
    )

    return {
        "summaries": summary_count,
        "purpose_fits": purpose_fit_count,
        "cognitive_interpretations": (
            cognitive_interpretation_count
        ),
        "motivation_interpretations": (
            motivation_interpretation_count
        ),
        "personality_questions": (
            personality_questions_count
        ),
        "personality_interpretations": (
            personality_interpretation_count
        ),
        "response_style_guidance": (
            response_style_guidance_count
        ),
    }

def process_update(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk)

    if obj.is_historical:
        return HttpResponseForbidden("Historical processes are read-only.")

    company = get_company_for_user(request.user)
    if not company or obj.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, obj):
        return HttpResponseForbidden("You do not have permission to edit this process.")

    if not user_can_access_process(request.user, obj):
        return HttpResponseForbidden("You do not have access to this process.")

    old_acc = (obj.account_code or "").strip()
    old_proj = (obj.project_code or "").strip()
    locked = obj.is_template_locked()
    old_purpose = obj.purpose

    client = SovaClient()
    error = None

    # --------------------------------------------------
    # 1. Hämta Sova-projekt från API
    # --------------------------------------------------
    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    # --------------------------------------------------
    # 2. Hämta ProjectMeta så vi kan hitta namn, tester osv
    # --------------------------------------------------
    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    template_cards = []

    for account in accounts:
        acc = (account.get("code") or "").strip()

        for project in (account.get("projects") or []):
            proj_code = (project.get("code") or "").strip()
            sova_name = (project.get("name") or proj_code).strip()

            value = f"{acc}|{proj_code}"

            meta_item = meta_map.get((acc, proj_code))
            title = getattr(meta_item, "intern_name", None) or sova_name

            description = ""
            tests = []
            languages = []

            if meta_item:
                description = (getattr(meta_item, "notes", None) or "").strip()

                tests_raw = (getattr(meta_item, "tests", None) or "").strip()
                if tests_raw:
                    tests = [t.strip() for t in tests_raw.split(",") if t.strip()]

                languages_raw = (getattr(meta_item, "languages", None) or "").strip()
                if languages_raw:
                    languages = [l.strip() for l in languages_raw.split(",") if l.strip()]

            template_cards.append({
                "value": value,
                "title": title,
                "description": description,
                "tests": tests,
                "languages": languages,
                "icon_class": get_template_icon_class(tests, title),
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
                "sova_project_id": project.get("id"),
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    # --------------------------------------------------
    # 3. Hjälpvariabler till header/tabs
    # --------------------------------------------------
    purpose_lookup = {
        item["key"]: item
        for item in PROCESS_PURPOSES
    }

    process_purpose = purpose_lookup.get(obj.purpose)

    meta = ProjectMeta.objects.filter(
        account_code=obj.account_code,
        project_code=obj.project_code,
    ).first()

    can_edit = user_can_edit_process(request.user, company, obj)

    def render_edit(form):
        return render(request, "customer/processes/process_edit.html", {
            "form": form,
            "process": obj,
            "error": error,
            "template_locked": locked,

            # Header/base template stuff
            "active": "settings",
            "meta": meta,
            "can_edit": can_edit,
            "process_purpose": process_purpose,
            "context_config": get_purpose_context_config(obj.purpose),
            "self_reg_url": request.build_absolute_uri(obj.get_self_registration_url()),

            # Edit page stuff
            "process_purposes": PROCESS_PURPOSES,
            "available_tests": AVAILABLE_TESTS,
            "purpose_recommended_tests": PURPOSE_RECOMMENDED_TESTS,
            "template_cards": template_cards,
            "templates_count": len(template_cards),
            "accounts_count": len(accounts),
        })

    # --------------------------------------------------
    # 4. POST: uppdatera processen
    # --------------------------------------------------
    if request.method == "POST":
        form = TestProcessWizardCreateForm(request.POST)

        if form.is_valid():
            name = (form.cleaned_data.get("name") or "").strip()
            purpose = form.cleaned_data.get("purpose")
            selected_tests = form.cleaned_data.get("selected_tests") or []
            label_names = form.cleaned_data.get("labels_text") or []

            if isinstance(label_names, str):
                label_names = [
                    item.strip()
                    for item in label_names.split(",")
                    if item.strip()
                ]

            # Namn får alltid ändras
            obj.name = name or obj.name

            # Labels får alltid ändras
            label_objs = []
            for label_name in label_names:
                lab, _ = ProcessLabel.objects.get_or_create(
                    company=company,
                    name=label_name,
                )
                label_objs.append(lab)

            # Preserve the currently active context under the old purpose
            # before switching the process to a new purpose.
            if old_purpose != purpose:
                existing_context = getattr(obj, "role_context", None)

                if existing_context and existing_context.has_content():
                    existing_context.save_context_for_purpose(
                        old_purpose,
                        existing_context.get_current_context_data(),
                    )

                    existing_context.save(update_fields=[
                        "purpose_data",
                        "updated_at",
                    ])

            # --------------------------------------------------
            # Purpose får alltid ändras.
            # Tester och Sova-projekt låses efter första utskicket.
            # --------------------------------------------------
            obj.purpose = purpose

            if locked:
                # Behåll befintliga tester och befintlig Sova-koppling.
                # Ignorera manipulerade testvärden från POST.
                obj.provider = "sova"
                obj.account_code = old_acc
                obj.project_code = old_proj
                obj.selected_tests = obj.selected_tests or []

            else:
                # Innan tester har skickats får testpaketet fortfarande ändras.
                obj.selected_tests = selected_tests

                resolved_template = resolve_dev_sova_template(selected_tests)

                if not resolved_template:
                    form.add_error(
                        "selected_tests",
                        "Please select at least Personality or Motivation in the current development environment."
                    )
                    return render_edit(form)

                acc = (resolved_template["account_code"] or "").strip()
                proj = (resolved_template["project_code"] or "").strip()
                value = f"{acc}|{proj}"

                obj.provider = "sova"
                obj.account_code = acc
                obj.project_code = proj

                meta_match = meta_map.get((acc, proj))

                if meta_match and getattr(meta_match, "intern_name", None):
                    obj.project_name_snapshot = meta_match.intern_name
                else:
                    match = next(
                        (t for t in template_cards if t["value"] == value),
                        None
                    )

                    obj.project_name_snapshot = (
                        match["sova_name"] if match else proj
                    )

            # --------------------------------------------------
            # Spara ändringarna
            # --------------------------------------------------
            obj.save()
            obj.labels.set(label_objs)

            if old_purpose != obj.purpose:
                result = mark_candidate_ai_content_outdated(obj)

                print(
                    "AI CONTENT MARKED OUTDATED:",
                    result,
                )

            messages.success(
                request,
                "The process was updated."
            )

            return redirect(
                "processes:process_update",
                pk=obj.pk,
            )

    # --------------------------------------------------
    # 5. GET: fyll edit-formuläret med befintliga värden
    # --------------------------------------------------
    else:
        form = TestProcessWizardCreateForm(initial={
            "name": obj.name,
            "labels_text": ", ".join(obj.labels.values_list("name", flat=True)),
            "purpose": obj.purpose,
            "selected_tests": obj.selected_tests or [],
        })

    return render_edit(form)


@login_required
def process_delete(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk)

    # ✅ kräver POST (viktigt)
    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    company = get_company_for_user(request.user)
    if not company or obj.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, obj):
        return HttpResponseForbidden("Du har inte behörighet att radera denna process.")

    if not user_can_access_process(request.user, obj):
        return HttpResponseForbidden("You do not have access to this process.")

        # ✅ B + C: delete om möjligt, annars arkivera
    if obj.can_delete():
        log_event(
            company=company,
            verb=ActivityEvent.Verb.PROCESS_DELETED,
            actor=request.user,
            process=obj,
        )
        obj.delete()
    else:
        log_event(
            company=company,
            verb=ActivityEvent.Verb.PROCESS_ARCHIVED,
            actor=request.user,
            process=obj,
            meta={"reason": "could_not_delete"},
        )
        obj.archive()
        messages.info(request, "Processen kunde inte raderas eftersom tester har skickats. Den arkiverades istället.")

    return redirect("processes:process_list")



@login_required
def process_role_context(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    if process.is_historical:
        return HttpResponseForbidden(
            "Historical processes are read-only."
        )

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden(
            "You do not have access to this process."
        )

    context_config = get_purpose_context_config(process.purpose)
    purpose_key = normalize_purpose_key(process.purpose)

    role_context, created = ProcessRoleContext.objects.get_or_create(
        process=process
    )

    if request.method == "POST":
        # IMPORTANT:
        # Capture the saved database values before ModelForm validation,
        # because form.is_valid() may update the model instance in memory.
        previous_context_data = (
            role_context.get_current_context_data()
        )

        form = ProcessRoleContextForm(
            request.POST,
            instance=role_context,
            context_config=context_config,
        )

        if form.is_valid():
            submitted_data = {
                field_name: form.cleaned_data.get(field_name, "") or ""
                for field_name in ProcessRoleContext.CONTEXT_FIELDS
            }

            context_changed = previous_context_data != submitted_data

            role_context = form.save(commit=False)

            role_context.save_context_for_purpose(
                purpose=purpose_key,
                context_data=submitted_data,
            )

            role_context.apply_context_data(submitted_data)
            role_context.save()

            if context_changed:
                result = mark_candidate_ai_content_outdated(
                    process
                )

                print("=== CONTEXT CHANGED ===")
                print("PROCESS:", process.id)
                print("AI CONTENT MARKED OUTDATED:", result)

            messages.success(
                request,
                "The process context was saved."
            )

            return redirect(
                "processes:process_detail",
                pk=process.pk,
            )

    else:
        saved_purpose_context = role_context.get_context_for_purpose(
            purpose_key
        )

        if saved_purpose_context is not None:
            initial_data = saved_purpose_context
            using_previous_purpose_as_start = False
        else:
            # No saved version for this purpose yet.
            # Reuse the active context as a helpful starting point.
            initial_data = role_context.get_current_context_data()
            using_previous_purpose_as_start = role_context.has_content()

        form = ProcessRoleContextForm(
            instance=role_context,
            initial=initial_data,
            context_config=context_config,
        )

    meta = ProjectMeta.objects.filter(
        account_code=process.account_code,
        project_code=process.project_code,
    ).first()

    purpose_lookup = {
        item["key"]: item
        for item in PROCESS_PURPOSES
    }

    process_purpose = purpose_lookup.get(process.purpose)

    company = process.company
    can_edit = user_can_edit_process(
        request.user,
        company,
        process,
    )

    return render(
        request,
        "customer/processes/process_role_context.html",
        {
            "process": process,
            "form": form,
            "role_context": role_context,
            "purpose_context": role_context,
            "context_config": context_config,
            "purpose_key": purpose_key,

            "using_previous_purpose_as_start": (
                using_previous_purpose_as_start
                if request.method != "POST"
                else False
            ),

            # Header/base template
            "meta": meta,
            "process_purpose": process_purpose,
            "can_edit": can_edit,

            # Active tab
            "active": "context",
        },
    )


@login_required
def process_detail(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    context_config = get_purpose_context_config(process.purpose)

    company_id = (
        CompanyMember.objects
        .filter(user=request.user)
        .values_list("company_id", flat=True)
        .first()
    )
    company = get_object_or_404(Company, pk=company_id)

    # Must belong to the same company
    if process.company_id != company.id:
        return HttpResponseForbidden("No access.")

    # Access rule, including own-only logic
    if not user_can_view_process(request.user, company, process):
        return HttpResponseForbidden("You do not have access to this process.")

    meta = ProjectMeta.objects.filter(
        account_code=process.account_code,
        project_code=process.project_code,
    ).first()

    can_edit = user_can_edit_process(request.user, company, process)

    if process.is_historical:
        invitations = TestInvitation.objects.none()

        historical_candidates = (
            HistoricalProcessCandidate.objects
            .filter(process=process)
            .select_related("candidate", "created_by")
            .prefetch_related("reports")
            .order_by("-created_at")
        )

        status_counts = dict(
            historical_candidates.values("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )

        total_candidates = historical_candidates.count()
        invited_count = 0

        started_count = historical_candidates.filter(
            status__in=["started", "completed"]
        ).count()

        completed_count = historical_candidates.filter(
            status="completed"
        ).count()

        expired_count = 0
        not_invited_count = 0

        not_started_count = historical_candidates.exclude(
            status__in=["started", "completed"]
        ).count()

    else:
        historical_candidates = HistoricalProcessCandidate.objects.none()

        invitations = (
            process.invitations
            .select_related("candidate")
            .order_by("-created_at")
        )

        status_counts = dict(
            invitations.values("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )

        total_candidates = invitations.count()

        invited_qs = invitations.filter(
            Q(status__in=["sent", "started", "completed", "expired"]) |
            Q(source="self_registered")
        )

        invited_count = invited_qs.count()

        started_count = invitations.filter(
            status__in=["started", "completed"]
        ).count()

        completed_count = invitations.filter(
            status="completed"
        ).count()

        expired_count = invitations.filter(
            status="expired"
        ).count()

        # Candidates added but not yet given access to the assessment
        not_invited_count = total_candidates - invited_count

        # Candidates who have access but have not started or completed
        not_started_count = invited_qs.exclude(
            status__in=["started", "completed", "expired"]
        ).count()

    activity_events = (
        ActivityEvent.objects
        .filter(company=company, process=process)
        .select_related("actor", "candidate", "invitation")
        [:50]
    )

    purpose_lookup = {
        item["key"]: item
        for item in PROCESS_PURPOSES
    }

    process_purpose = purpose_lookup.get(process.purpose)

    context = {
        "process": process,
        "invitations": invitations,
        "historical_candidates": historical_candidates,
        "is_historical": process.is_historical,
        "meta": meta,
        "self_reg_url": request.build_absolute_uri(process.get_self_registration_url()),
        "status_counts": status_counts,
        "can_edit": can_edit,
        "activity_events": activity_events,
        "process_purpose": process_purpose,
        "active": "overview",
        "context_config": context_config,
        "kpis": {
            "total_candidates": total_candidates,
            "invited": invited_count,
            "started": started_count,
            "completed": completed_count,
            "expired": expired_count,
            "not_started": not_started_count,
            "not_invited": not_invited_count,
        },
    }

    return render(request, "customer/processes/process_detail.html", context)



@login_required
def process_add_candidate(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    if process.is_historical:
        return HttpResponseForbidden("Historical processes are read-only.")

    company = get_company_for_user(request.user)
    if not company or process.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, process):
        return HttpResponseForbidden("Du har inte behörighet att ändra i denna process.")

    # ✅ Säkerhetskontroll
    if not company or not user_can_edit_process(request.user, company, process):
        return HttpResponseForbidden("Du har inte behörighet att skicka tester i denna process.")

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if request.method == "POST":
        form = CandidateCreateForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()

            candidate, created = Candidate.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": form.cleaned_data["first_name"],
                    "last_name": form.cleaned_data["last_name"],
                }
            )

            invitation, inv_created = TestInvitation.objects.get_or_create(
                process=process,
                candidate=candidate,
                defaults={"source": "invited", "status": "created"},
            )

            if inv_created:
                log_event(
                    company=company,  # du har company i funktionen
                    verb=ActivityEvent.Verb.CANDIDATE_ADDED,
                    actor=request.user,
                    process=process,
                    candidate=candidate,
                    invitation=invitation,
                    meta={"source": "invited"},
                )

            if inv_created:
                msg = f"{candidate.email} har lagts till i processen."
                messages.success(request, msg)
            else:
                msg = f"{candidate.email} är redan i processen."
                messages.info(request, msg)

            # ✅ Modal/AJAX: return JSON istället för redirect
            if is_ajax:
                return JsonResponse({
                    "ok": True,
                    "message": msg,
                    "redirect_url": reverse("processes:process_detail", kwargs={"pk": process.pk})
                })

            return redirect("processes:process_detail", pk=process.pk)

        # ❌ Ogiltigt form
        if is_ajax:
            # returnera form-HTML med errors så modalen kan visa dem
            return render(
                request,
                "customer/processes/_add_candidate_form.html",
                {"process": process, "form": form},
                status=400
            )

    else:
        form = CandidateCreateForm()

    # ✅ GET: om AJAX -> partial, annars full page
    if is_ajax:
        return render(request, "customer/processes/_add_candidate_form.html", {
            "process": process,
            "form": form,
        })

    return render(request, "customer/processes/process_add_candidate.html", {
        "process": process,
        "form": form,
    })



@login_required
def invite_candidate(request, pk, candidate_id):
    process = get_object_or_404(TestProcess, pk=pk)

    # Säkerhetskontroll
    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("You do not have access to this process.")
    
    candidate = get_object_or_404(Candidate, pk=candidate_id)
    invitation = get_object_or_404(TestInvitation, process=process, candidate=candidate)

    # Här kopplar vi in SOVA i steg 3.
    # Tills vidare: fejka så att du ser flödet funka i UI:
    invitation.status = "sent"
    invitation.invited_at = invitation.invited_at or __import__("django.utils.timezone").utils.timezone.now()
    invitation.save(update_fields=["status", "invited_at"])

    messages.success(request, f"Invite triggered for {candidate.email} (stub).")
    return redirect("processes:process_detail", pk=process.pk)


@login_required
def sova_order_assessment_smoke_test(request, pk, candidate_id):
    process = get_object_or_404(TestProcess, pk=pk)

    # Säkerhetskontroll
    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("You do not have access to this process.")
    candidate = get_object_or_404(Candidate, pk=candidate_id)

    client = SovaClient()

    # ✅ From SOVA UI: account TQ_SWEDEN_ACCOUNT, project code tqs-simple-test
    project_code = "tqs-simple-test"

    request_id = f"talena-{process.id}-{candidate.id}-{uuid.uuid4().hex}"

    # ✅ Minimal valid payload (snake_case, matches docs)
    payload = {
        "request_id": request_id,
        "candidate_id": str(candidate.id),
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "language": "sv",  # test "sv" first; if needed change to "sv-SE"
        "job_title": "Smoke Test",
        "job_number": f"talena-{process.id}",
        "meta_data": {
            "talena_process_id": str(process.id),
            "talena_candidate_id": str(candidate.id),
            "talena_user_id": str(request.user.id),
        },
    }

    try:
        print("\n=== SOVA ORDER-ASSESSMENT SMOKE TEST ===")
        print("ACCOUNT:", "TQ_SWEDEN_ACCOUNT")
        print("PROJECT CODE:", project_code)
        print("BASE URL:", client.base_url)
        print("PAYLOAD:", payload)

        resp = client.order_assessment(project_code, payload)

        print("RESPONSE JSON:", resp)
        print("=== /SOVA ORDER-ASSESSMENT SMOKE TEST ===\n")

        assessment_url = resp.get("url")
        if assessment_url:
            return HttpResponse(
                f"✅ OK\nProject: {project_code}\nRequest: {request_id}\n\nTest URL:\n{assessment_url}",
                content_type="text/plain"
            )

        return HttpResponse(
            f"✅ OK but no 'url' returned\nProject: {project_code}\nRequest: {request_id}\n\nResponse:\n{resp}",
            content_type="text/plain"
        )

    except Exception as e:
        print("\n=== SOVA ORDER-ASSESSMENT SMOKE TEST FAILED ===")
        print("ERROR:", str(e))
        print("BASE URL:", client.base_url)
        print("PROJECT CODE:", project_code)
        print("PAYLOAD:", payload)
        print("=== /FAILED ===\n")

        return HttpResponse(f"❌ FAILED: {e}", content_type="text/plain", status=500)

def _is_safe_external_url(url: str) -> bool:
    try:
        p = urlparse(url or "")
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

def self_register(request, token):
    process = get_object_or_404(TestProcess, self_registration_token=token)

    if request.method != "POST":
        form = SelfRegisterForm()
        return render(request, "customer/processes/self_register_form.html", {
            "process": process,
            "form": form,
        })

    form = SelfRegisterForm(request.POST)
    if not form.is_valid():
        return render(request, "customer/processes/self_register_form.html", {
            "process": process,
            "form": form,
        })

    first_name = form.cleaned_data["first_name"].strip()
    last_name = form.cleaned_data["last_name"].strip()
    email = form.cleaned_data["email"].strip().lower()

    client = SovaClient()

    with transaction.atomic():
        candidate, _ = Candidate.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
            },
        )

        invitation, created = TestInvitation.objects.get_or_create(
            process=process,
            candidate=candidate,
            defaults={
                "status": "created",
                "source": "self_registered",
            },
        )

        if created:
            log_event(
                company=process.company,
                verb=ActivityEvent.Verb.CANDIDATE_ADDED,
                actor=None,
                actor_name="Self-registration",
                process=process,
                candidate=candidate,
                invitation=invitation,
                meta={"source": "self_registered"},
            )

        if not created and invitation.source != "self_registered":
            invitation.source = "self_registered"
            invitation.save(update_fields=["source"])

    existing_url = invitation.assessment_url
    if not existing_url:
        try:
            existing_url = (invitation.sova_payload or {}).get("url")
        except Exception:
            existing_url = None

    if (
        invitation.status in ("sent", "started", "completed")
        and existing_url
        and _is_safe_external_url(existing_url)
    ):
        return HttpResponseRedirect(existing_url)

    request_id = f"talena-selfreg-{process.id}-{candidate.id}-{uuid.uuid4().hex}"

    payload = {
        "request_id": request_id,
        "candidate_id": str(candidate.id),
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "language": "sv",
        "job_title": process.job_title or process.name,
        "job_number": f"talena-{process.id}",
        "meta_data": {
            "talena_process_id": str(process.id),
            "talena_candidate_id": str(candidate.id),
            "talena_request_id": request_id,
        },
    }

    try:
        resp = client.order_assessment(process.project_code, payload)
        test_url = (resp or {}).get("url")

        invitation.status = "sent"
        invitation.invited_at = timezone.now()
        invitation.sova_payload = resp
        invitation.request_id = request_id
        invitation.assessment_url = test_url
        invitation.save(update_fields=[
            "status",
            "invited_at",
            "sova_payload",
            "request_id",
            "assessment_url",
        ])

        # Hämta mall
        lang = "sv"
        template = (
            EmailTemplate.objects
            .filter(
                process=process,
                template_type="invitation",
                language=lang,
                is_active=True,
            )
            .first()
        )

        subject_tpl = template.subject if template else "{process_name}: Ditt test"
        body_tpl = template.body if template else (
            "Hej {first_name}!\n\n"
            "Klicka på länken för att starta testet:\n"
            "{assessment_url}\n\n"
            "Vänliga hälsningar,\n"
            "Talena"
        )

        ctx = {
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "process_name": process.name,
            "job_title": process.job_title,
            "job_location": process.job_location,
            "assessment_url": test_url,
        }

        subject = render_placeholders(subject_tpl, ctx)
        body = render_placeholders(body_tpl, ctx)

        email_log = EmailLog.objects.create(
            invitation=invitation,
            template_type="invitation",
            to_email=candidate.email,
            subject=subject,
            body_snapshot=body,
            status="queued",
        )

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None) or "no-reply@talena.se",
                to=[candidate.email],
            )
            msg.send()
            email_log.mark_sent()
        except Exception as e:
            email_log.mark_failed(str(e))
            # fallback-mejlet får faila utan att stoppa redirect till testet

        log_event(
            company=process.company,
            verb=ActivityEvent.Verb.INVITE_SENT,
            actor=None,
            actor_name="Self-registration",
            process=process,
            candidate=candidate,
            invitation=invitation,
            meta={
                "context": "self_register",
                "email_log_id": email_log.id,
            },
        )

        if test_url and _is_safe_external_url(test_url):
            return HttpResponseRedirect(test_url)

        return render(request, "customer/processes/self_register_success.html", {
            "process": process,
            "message": "Registrering klar. Vi skickar ett mejl när testlänken är redo.",
        })

    except Exception as e:
        print("❌ SELF REGISTER order_assessment failed:", str(e))
        return render(request, "customer/processes/self_register_success.html", {
            "process": process,
            "message": "Registrering klar, men vi kunde inte starta testet direkt. Du får ett mejl så snart det är redo.",
        })


@login_required
@require_POST
def remove_candidate_from_process(request, process_id, candidate_id):
    process = get_object_or_404(TestProcess, pk=process_id, created_by=request.user)

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate_id=candidate_id,
    )

    log_event(
        company=process.company,
        verb=ActivityEvent.Verb.CANDIDATE_REMOVED,
        actor=request.user,
        process=process,
        candidate=invitation.candidate,
        invitation=invitation,
    )


    invitation.delete()
    messages.success(request, "Candidate removed from process.")
    return redirect("processes:process_detail", pk=process.id)



@login_required
def process_send_tests(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    if process.is_historical or not process.sova_sync_enabled:
        messages.error(request, "This is a historical process and cannot send SOVA invitations.")
        return redirect("processes:process_detail", pk=process.pk)

    company = get_company_for_user(request.user)
    if not company or process.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, process):
        return HttpResponseForbidden("Du har inte behörighet att skicka tester i denna process.")

    if request.method != "POST":
        return redirect("processes:process_detail", pk=process.pk)

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("You do not have access to this process.")

    if request.method != "POST":
        return redirect("processes:process_detail", pk=process.pk)

    invitation_ids = request.POST.getlist("invitation_ids")
    if not invitation_ids:
        messages.warning(request, "Välj minst en kandidat.")
        return redirect("processes:process_detail", pk=process.pk)

    invitations = (
        TestInvitation.objects
        .filter(process=process, id__in=invitation_ids)
        .select_related("candidate")
    )

    result = send_assessments_and_emails(
        process=process,
        invitations=invitations,
        actor_user=request.user,
        context="customer",
    )

    if result["sent_count"]:
        messages.success(request, f"Skickade test till {result['sent_count']} kandidat(er).")

    if result["errors"]:
        for err in result["errors"]:
            messages.error(request, f"Kunde inte skicka till {err['email']}: {err['error']}")

    if result["sent_count"] == 0:
        if result["skipped_count"]:
            messages.info(request, "Inget skickades (alla markerade var redan skickade/igång/klara).")
        else:
            messages.warning(request, "Inget skickades. Kolla felmeddelanden ovan.")

    return redirect("processes:process_detail", pk=process.pk)

@login_required
def process_candidate_detail(request, process_id, candidate_id):
    process = get_object_or_404(TestProcess, pk=process_id)

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("You do not have access to this process.")

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if process.is_historical:
        historical_candidate = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
                "created_by",
            )
            .prefetch_related(
                "reports",
                "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process,
            candidate_id=candidate_id,
        )

        ctx = build_historical_candidate_detail_context(
            process=process,
            historical_candidate=historical_candidate,
        )

        return render(
            request,
            "customer/processes/_candidate_detail_sheet.html",
            ctx,
        )

        ctx = {
            "company": process.company,
            "process": process,
            "candidate": historical_candidate.candidate,
            "historical_candidate": historical_candidate,
            "historical_reports": historical_candidate.reports.all(),
            "is_historical": True,
            "assessment_results": assessment_results,
        }

    else:
        invitation = get_object_or_404(
            TestInvitation.objects.select_related("candidate"),
            process=process,
            candidate_id=candidate_id,
        )

        ctx = build_candidate_detail_context(
            process=process,
            invitation=invitation,
        )

        ctx["is_historical"] = False

    if is_ajax:
        return render(
            request,
            "customer/processes/_candidate_detail_sheet.html",
            ctx,
        )

    return render(
        request,
        "customer/processes/process_candidate_detail.html",
        ctx,
    )


@login_required
def process_invitation_statuses(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    # Säkerhetskontroll
    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("You do not have access to this process.")

    qs = (
        TestInvitation.objects
        .filter(process=process)
        .select_related("candidate")
        .order_by("created_at")
    )

    return JsonResponse({
        "invitations": [
            {
                "id": inv.id,
                "status": inv.status,
                "completed_at": inv.completed_at.isoformat() if inv.completed_at else None,
                "sova_overall_status": getattr(inv, "sova_overall_status", "") or "",
            }
            for inv in qs
        ]
    })


@login_required
def process_archive(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk)

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    company = get_company_for_user(request.user)
    if not company or obj.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, obj):
        return HttpResponseForbidden("Du har inte behörighet att arkivera denna process.")

    if not user_can_access_process(request.user, obj):
        return HttpResponseForbidden("You do not have access to this process.")

    obj.archive()

    log_event(
        company=company,
        verb=ActivityEvent.Verb.PROCESS_ARCHIVED,
        actor=request.user,
        process=obj,
    )

    messages.success(request, "Processen arkiverades.")
    return redirect("processes:process_list")


@login_required
def process_unarchive(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk)

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    company = get_company_for_user(request.user)
    if not company or obj.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, obj):
        return HttpResponseForbidden("Du har inte behörighet att återställa denna process.")

    if not user_can_access_process(request.user, obj):
        return HttpResponseForbidden("You do not have access to this process.")

    obj.unarchive()
    messages.success(request, "Processen återställdes.")
    return redirect("processes:process_list")


@login_required
def process_candidate_summary_stream(
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
            "You do not have access to this process."
        )

    # ---------------------------------------------------------
    # HISTORICAL CANDIDATE
    # ---------------------------------------------------------
    if process.is_historical:
        summary_owner = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related("candidate", "process")
            .prefetch_related(
                "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process,
            candidate_id=candidate_id,
        )

        is_historical = True

    # ---------------------------------------------------------
    # ACTIVE CANDIDATE
    # ---------------------------------------------------------
    else:
        summary_owner = get_object_or_404(
            TestInvitation.objects.select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

        is_historical = False

        # Active candidates must have completed all assessments.
        if summary_owner.status != "completed":
            return JsonResponse(
                {
                    "error": (
                        "Candidate has not completed "
                        "the assessments yet."
                    )
                },
                status=400,
            )

    # ---------------------------------------------------------
    # RETURN EXISTING SUMMARY
    # ---------------------------------------------------------
    if summary_owner.ai_summary:
        def existing_generator():
            yield summary_owner.ai_summary

        response = StreamingHttpResponse(
            existing_generator(),
            content_type="text/plain; charset=utf-8",
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    # ---------------------------------------------------------
    # PREVENT DUPLICATE GENERATION
    # ---------------------------------------------------------
    if summary_owner.ai_summary_status == "generating":
        return JsonResponse(
            {
                "error": (
                    "Summary is already being generated."
                )
            },
            status=409,
        )

    summary_owner.ai_summary_status = "generating"
    summary_owner.save(
        update_fields=["ai_summary_status"]
    )

    # ---------------------------------------------------------
    # STREAM GENERATION
    # ---------------------------------------------------------
    def generator():
        full_text = ""

        try:
            if is_historical:
                stream = stream_historical_candidate_summary(
                    process=process,
                    historical_candidate=summary_owner,
                )
            else:
                stream = stream_candidate_summary(
                    summary_owner
                )

            for chunk in stream:
                full_text += chunk
                yield chunk

            if is_historical:
                summary_owner.ai_summary = full_text
                summary_owner.ai_summary_status = "completed"
                summary_owner.ai_summary_generated_at = timezone.now()

                summary_owner.save(
                    update_fields=[
                        "ai_summary",
                        "ai_summary_status",
                        "ai_summary_generated_at",
                    ]
                )

            else:
                save_candidate_summary(
                    summary_owner,
                    full_text,
                )

        except Exception as error:
            summary_owner.ai_summary_status = "failed"

            summary_owner.save(
                update_fields=[
                    "ai_summary_status",
                ]
            )

            yield f"\n\n[Error: {str(error)}]"

    response = StreamingHttpResponse(
        generator(),
        content_type="text/plain; charset=utf-8",
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response


@login_required
def process_candidate_response_style_guidance_stream(
    request,
    process_id,
    candidate_id,
):
    """
    Stream and save AI-supported response-style guidance.

    Existing completed guidance is returned without making a new
    OpenAI request.

    Guidance is regenerated when its status is:
    - not_started
    - outdated
    - failed
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
            "You do not have access to this process."
        )

    # ---------------------------------------------------------
    # FIND THE CORRECT GUIDANCE OWNER
    # ---------------------------------------------------------
    if process.is_historical:
        guidance_owner = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    else:
        guidance_owner = get_object_or_404(
            TestInvitation.objects
            .select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

    # ---------------------------------------------------------
    # BUILD RESPONSE-STYLE RESULTS
    # ---------------------------------------------------------
    response_styles = (
        build_response_styles_for_guidance_owner(
            guidance_owner
        )
    )

    available_response_styles = [
        style
        for style in response_styles
        if style.get("available")
    ]

    if not available_response_styles:
        return JsonResponse(
            {
                "error": (
                    "No response-style results are "
                    "available for this candidate."
                )
            },
            status=400,
        )

    current_status = (
        guidance_owner
        .ai_response_style_guidance_status
        or "not_started"
    )

    saved_guidance = (
        guidance_owner.ai_response_style_guidance
        or {}
    )

    current_purpose = (
        process.purpose
        or ""
    ).strip().lower()

    saved_purpose = (
        guidance_owner
        .ai_response_style_guidance_purpose
        or ""
    ).strip().lower()

    # ---------------------------------------------------------
    # SAFETY CHECK FOR CHANGED PURPOSE
    # ---------------------------------------------------------
    if (
        saved_guidance
        and current_status == "completed"
        and saved_purpose != current_purpose
    ):
        current_status = "outdated"

        guidance_owner.ai_response_style_guidance_status = (
            "outdated"
        )

        guidance_owner.save(update_fields=[
            "ai_response_style_guidance_status",
        ])

    # ---------------------------------------------------------
    # RETURN SAVED GUIDANCE
    # ---------------------------------------------------------
    if (
        saved_guidance
        and current_status == "completed"
    ):
        def existing_generator():
            yield json.dumps(
                {
                    "type": "saved_result",
                    "data": saved_guidance,
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
                    "Response-style guidance is already "
                    "being generated."
                )
            },
            status=409,
        )

    guidance_owner.ai_response_style_guidance_status = (
        "generating"
    )

    guidance_owner.save(update_fields=[
        "ai_response_style_guidance_status",
    ])

    # ---------------------------------------------------------
    # STREAM GENERATION
    # ---------------------------------------------------------
    def generator():
        guidance = (
            create_empty_response_style_guidance(
                guidance_owner
            )
        )

        received_done_event = False

        try:
            for event in stream_response_style_guidance(
                guidance_owner=guidance_owner,
                response_styles=available_response_styles,
            ):
                guidance = (
                    apply_response_style_guidance_event(
                        guidance,
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
                guidance.get("summary")
                or ""
            ).strip():
                raise ValueError(
                    "The AI response did not contain "
                    "a guidance summary."
                )

            if not received_done_event:
                yield json.dumps({
                    "type": "done",
                }) + "\n"

            save_response_style_guidance(
                guidance_owner=guidance_owner,
                guidance=guidance,
            )

        except Exception as error:
            guidance_owner.ai_response_style_guidance_status = (
                "failed"
            )

            guidance_owner.save(update_fields=[
                "ai_response_style_guidance_status",
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
def process_candidate_purpose_fit_stream(
    request,
    process_id,
    candidate_id,
):
    print(
        f"[PURPOSE FIT] Stream requested "
        f"process={process_id}, candidate={candidate_id}",
        flush=True,
    )

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    print(
        f"[PURPOSE FIT] Process found: "
        f"{process.id}, purpose={process.purpose}",
        flush=True,
    )

    if not user_can_access_process(request.user, process):
        print(
            "[PURPOSE FIT] Access denied",
            flush=True,
        )

        return HttpResponseForbidden(
            "You do not have access to this process."
        )

    if not purpose_supports_fit(process):
        print(
            "[PURPOSE FIT] Purpose does not support fit",
            flush=True,
        )

        return JsonResponse(
            {
                "error": (
                    "Flexible processes do not support "
                    "purpose-fit analysis."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )

    print(
        f"[PURPOSE FIT] Invitation found: "
        f"id={invitation.id}, "
        f"status={invitation.status}, "
        f"fit_status={invitation.ai_purpose_fit_status}, "
        f"has_saved_fit={bool(invitation.ai_purpose_fit)}",
        flush=True,
    )

    if invitation.status != "completed":
        print(
            "[PURPOSE FIT] Candidate not completed",
            flush=True,
        )

        return JsonResponse(
            {
                "error": (
                    "Candidate assessments are not completed yet."
                )
            },
            status=400,
        )

    if invitation.ai_purpose_fit:
        print(
            "[PURPOSE FIT] Returning saved result",
            flush=True,
        )

        def existing_generator():
            yield json.dumps({
                "type": "saved_result",
                "data": invitation.ai_purpose_fit,
                "status": invitation.ai_purpose_fit_status,
            }) + "\n"

        response = StreamingHttpResponse(
            existing_generator(),
            content_type="application/x-ndjson; charset=utf-8",
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    if invitation.ai_purpose_fit_status == "generating":
        print(
            "[PURPOSE FIT] Already marked as generating",
            flush=True,
        )

        return JsonResponse(
            {
                "error": (
                    "Purpose-fit analysis is already being generated."
                )
            },
            status=409,
        )

    invitation.ai_purpose_fit_status = "generating"
    invitation.save(update_fields=[
        "ai_purpose_fit_status",
    ])

    print(
        "[PURPOSE FIT] Status changed to generating",
        flush=True,
    )

    def generator():
        purpose_fit = create_empty_purpose_fit(
            invitation
        )

        received_done_event = False

        try:
            print(
                "[PURPOSE FIT] Starting OpenAI stream",
                flush=True,
            )

            for event in stream_candidate_purpose_fit(
                invitation
            ):
                print(
                    "[PURPOSE FIT] Event received:",
                    event,
                    flush=True,
                )

                purpose_fit = apply_purpose_fit_event(
                    purpose_fit,
                    event,
                )

                if event.get("type") == "done":
                    received_done_event = True

                yield json.dumps(
                    event,
                    ensure_ascii=False,
                ) + "\n"

            print(
                "[PURPOSE FIT] OpenAI stream finished",
                flush=True,
            )

            if not received_done_event:
                print(
                    "[PURPOSE FIT] Adding missing done event",
                    flush=True,
                )

                yield json.dumps({
                    "type": "done",
                }) + "\n"

            save_candidate_purpose_fit(
                invitation,
                purpose_fit,
            )

            print(
                "[PURPOSE FIT] Result saved successfully",
                flush=True,
            )

        except Exception as exc:
            print(
                "[PURPOSE FIT] ERROR:",
                repr(exc),
                flush=True,
            )

            invitation.ai_purpose_fit_status = "failed"
            invitation.save(update_fields=[
                "ai_purpose_fit_status",
            ])

            yield json.dumps({
                "type": "error",
                "message": str(exc),
            }, ensure_ascii=False) + "\n"

    response = StreamingHttpResponse(
        generator(),
        content_type="application/x-ndjson; charset=utf-8",
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    print(
        "[PURPOSE FIT] Streaming response created",
        flush=True,
    )

    return response


@login_required
@require_POST
def process_candidate_purpose_fit_regenerate(
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
            "You do not have access to this process."
        )

    if not purpose_supports_fit(process):
        return JsonResponse(
            {
                "error": (
                    "Flexible processes do not support "
                    "purpose-fit analysis."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate_id=candidate_id,
    )

    invitation.ai_purpose_fit = {}
    invitation.ai_purpose_fit_status = "not_started"
    invitation.ai_purpose_fit_generated_at = None
    invitation.ai_purpose_fit_purpose = ""

    invitation.save(
        update_fields=[
            "ai_purpose_fit",
            "ai_purpose_fit_status",
            "ai_purpose_fit_generated_at",
            "ai_purpose_fit_purpose",
        ]
    )

    return JsonResponse(
        {
            "ok": True,
            "stream_url": reverse(
                "processes:process_candidate_purpose_fit_stream",
                kwargs={
                    "process_id": process.id,
                    "candidate_id": candidate_id,
                },
            ),
        }
    )

@login_required
def process_create_v2(request):
    client = SovaClient()
    error = None

    # --------------------------------------------------
    # 1. Hämta Sova-projekt från API
    # --------------------------------------------------
    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    # --------------------------------------------------
    # 2. Hämta ProjectMeta så vi kan hitta namn, tester osv
    # --------------------------------------------------
    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    project_id_map = {}
    template_cards = []

    for account in accounts:
        acc = (account.get("code") or "").strip()

        for project in (account.get("projects") or []):
            proj_code = (project.get("code") or "").strip()
            sova_name = (project.get("name") or proj_code).strip()

            value = f"{acc}|{proj_code}"
            project_id_map[value] = project.get("id")

            meta = meta_map.get((acc, proj_code))
            title = getattr(meta, "intern_name", None) or sova_name

            description = ""
            tests = []
            languages = []

            if meta:
                description = (getattr(meta, "notes", None) or "").strip()

                tests_raw = (getattr(meta, "tests", None) or "").strip()

                if tests_raw:
                    tests = [
                        test.strip().lower()
                        for test in tests_raw.split(",")
                        if test.strip()
                    ]

                languages_raw = (getattr(meta, "languages", None) or "").strip()

                if languages_raw:
                    languages = [
                        language.strip()
                        for language in languages_raw.split(",")
                        if language.strip()
                    ]

            # Fallback:
            # Om ProjectMeta saknar tester läser Talena kombinationen
            # direkt från Sova-projektets namn.
            if not tests:
                tests = extract_tests_from_project_name(sova_name)

            template_cards.append({
                "value": value,
                "title": title,
                "description": description,
                "tests": tests,
                "languages": languages,
                "icon_class": get_template_icon_class(tests, title),
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
                "sova_project_id": project.get("id"),
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    # --------------------------------------------------
    # 3. Hämta company
    # --------------------------------------------------
    company_id = (
        CompanyMember.objects
        .filter(user=request.user)
        .values_list("company_id", flat=True)
        .first()
    )

    if not company_id:
        messages.error(request, "You are not linked to a company.")
        return redirect("processes:process_list")

    company = get_object_or_404(Company, pk=company_id)

    # --------------------------------------------------
    # 4. POST: skapa processen
    # --------------------------------------------------
    if request.method == "POST":
        form = TestProcessWizardCreateForm(request.POST)

        if form.is_valid():
            purpose = form.cleaned_data.get("purpose")
            selected_tests = form.cleaned_data.get("selected_tests") or []
            name = (form.cleaned_data.get("name") or "").strip()

            # Om användaren inte skrev namn, skapa ett automatiskt
            if not name:
                name = build_default_process_name(
                    purpose=purpose,
                    selected_tests=selected_tests,
                )

            # --------------------------------------------------
            # 5. Matcha valda tester mot rätt Sova-projekt
            # --------------------------------------------------
            try:
                resolved_template = resolve_sova_template(
                    selected_tests=selected_tests,
                    template_cards=template_cards,
                )
            except ValueError as exc:
                form.add_error("selected_tests", str(exc))

                return render(request, "customer/processes/process_create_v2.html", {
                    "form": form,
                    "error": error,
                    "process_purposes": PROCESS_PURPOSES,
                    "available_tests": AVAILABLE_TESTS,
                    "purpose_recommended_tests": PURPOSE_RECOMMENDED_TESTS,
                    "template_cards": template_cards,
                    "templates_count": len(template_cards),
                    "accounts_count": len(accounts),
                })

            if not resolved_template:
                selected_labels = [
                    test["label"]
                    for test in AVAILABLE_TESTS
                    if test["key"] in selected_tests
                ]

                selected_label = " + ".join(selected_labels) or "the selected tests"

                form.add_error(
                    "selected_tests",
                    (
                        f"No matching Sova project was found for {selected_label}. "
                        "Please check that the project exists and that its ProjectMeta "
                        "record contains the correct tests."
                    ),
                )

                return render(request, "customer/processes/process_create_v2.html", {
                    "form": form,
                    "error": error,
                    "process_purposes": PROCESS_PURPOSES,
                    "available_tests": AVAILABLE_TESTS,
                    "purpose_recommended_tests": PURPOSE_RECOMMENDED_TESTS,
                    "template_cards": template_cards,
                    "templates_count": len(template_cards),
                    "accounts_count": len(accounts),
                })
            
            


            acc = resolved_template["account_code"]
            proj = resolved_template["project_code"]
            value = resolved_template["value"]

            # --------------------------------------------------
            # 6. Hämta org unit
            # --------------------------------------------------
            active_unit_id = request.session.get("active_org_unit_id")
            accessible_ids = get_accessible_orgunit_ids(request.user, company)

            if not active_unit_id or int(active_unit_id) not in accessible_ids:
                fallback_id = next(iter(accessible_ids), None)

                if not fallback_id:
                    form.add_error(
                        None,
                        "You do not have an assigned org unit, so a process cannot be created."
                    )

                    return render(request, "customer/processes/process_create_v2.html", {
                        "form": form,
                        "error": error,
                        "process_purposes": PROCESS_PURPOSES,
                        "available_tests": AVAILABLE_TESTS,
                        "purpose_recommended_tests": PURPOSE_RECOMMENDED_TESTS,
                        "template_cards": template_cards,
                        "templates_count": len(template_cards),
                        "accounts_count": len(accounts),
                    })

                active_unit_id = fallback_id
                request.session["active_org_unit_id"] = active_unit_id

            # --------------------------------------------------
            # 7. Skapa TestProcess
            # --------------------------------------------------
            obj = TestProcess(
                name=name,
                company=company,
                org_unit_id=int(active_unit_id),
                provider="sova",
                account_code=acc,
                project_code=proj,
                created_by=request.user,
                purpose=purpose,
                selected_tests=selected_tests,
            )

            # --------------------------------------------------
            # 8. Sätt project_name_snapshot
            # --------------------------------------------------
            meta = meta_map.get((acc, proj))

            if meta and getattr(meta, "intern_name", None):
                obj.project_name_snapshot = meta.intern_name
            else:
                obj.project_name_snapshot = (
                    resolved_template.get("sova_name")
                    or resolved_template.get("title")
                    or proj
                )

            obj.save()

            # --------------------------------------------------
            # 9. Spara labels
            # --------------------------------------------------
            label_names = form.cleaned_data.get("labels_text") or []

            # Om labels_text råkar komma in som string istället för lista
            if isinstance(label_names, str):
                label_names = [
                    item.strip()
                    for item in label_names.split(",")
                    if item.strip()
                ]

            if label_names:
                label_objs = []

                for label_name in label_names:
                    lab, _ = ProcessLabel.objects.get_or_create(
                        company=company,
                        name=label_name,
                    )
                    label_objs.append(lab)

                obj.labels.set(label_objs)
            else:
                obj.labels.clear()

            # --------------------------------------------------
            # 10. Logga activity
            # --------------------------------------------------
            log_event(
                company=company,
                verb=ActivityEvent.Verb.PROCESS_CREATED,
                actor=request.user,
                process=obj,
                meta={
                    "process_name": obj.name,
                    "purpose": obj.purpose,
                    "selected_tests": obj.selected_tests,
                    "resolved_sova_template": value,
                    "sova_project_id": project_id_map.get(value),
                },
            )

            messages.success(request, "Testprocessen skapades.")
            return redirect("processes:process_detail", pk=obj.pk)
        
        else:
            print("PROCESS CREATE FORM ERRORS:", form.errors.as_json())
            print("POST DATA:", request.POST)

        messages.error(request, "The process could not be created. Please check the fields.")

    # --------------------------------------------------
    # 11. GET: visa tom form
    # --------------------------------------------------
    else:
        form = TestProcessWizardCreateForm()

    return render(request, "customer/processes/process_create_v2.html", {
        "form": form,
        "error": error,
        "process_purposes": PROCESS_PURPOSES,
        "available_tests": AVAILABLE_TESTS,
        "purpose_recommended_tests": PURPOSE_RECOMMENDED_TESTS,
        "template_cards": template_cards,
        "templates_count": len(template_cards),
        "accounts_count": len(accounts),
    })


def build_historical_candidate_detail_context(
    process,
    historical_candidate,
):
    """
    Build candidate sheet context for a historical candidate.

    Historical assessment data is normalised through
    build_historical_candidate_profile() and then exposed using the same
    context keys as the regular candidate sheet.

    Historical candidates always use general insight mode because no
    original process purpose or context is available.
    """
    candidate = historical_candidate.candidate

    profile = build_historical_candidate_profile(
        historical_candidate
    )

    assessment_results = profile["assessment_results"]

    motivation_competencies = profile["motivation_competencies"]
    personality_competencies = profile["personality_competencies"]
    team_style_scores = profile["team_style_scores"]
    ability_results = profile["ability_results"]

    has_motivation_results = profile["has_motivation_results"]
    has_personality_results = profile["has_personality_results"]
    has_ability_results = profile["has_ability_results"]
    has_any_results = profile["has_any_results"]

    # Historical extracts contain completed result data.
    all_assessments_completed = has_any_results

    verbal_result = ability_results.get("verbal")
    logical_result = ability_results.get("logical")
    numerical_result = ability_results.get("numerical")

    verbal_percentile = (
        verbal_result.get("value")
        if verbal_result
        else None
    )

    logical_percentile = (
        logical_result.get("value")
        if logical_result
        else None
    )

    numerical_percentile = (
        numerical_result.get("value")
        if numerical_result
        else None
    )

    has_verbal_results = verbal_result is not None
    has_logical_results = logical_result is not None
    has_numerical_results = numerical_result is not None

    # -------------------------------------------------------------------------
    # Convert the common profile into structures already used by the template
    # -------------------------------------------------------------------------

    motivation_results = []
    mq_competencies = []

    for item in motivation_competencies:
        score_value = item.get("score")

        motivation_results.append({
            "activity": "Motivation Questionnaire",
            "competency": item.get("competency") or item.get("name"),
            "score": score_value,
            "stive": item.get("stive", score_value),
            "stive_rounded": item.get(
                "stive_rounded",
                round(score_value) if score_value is not None else None,
            ),
            "sten": item.get("sten"),
            "sten_rounded": item.get("sten_rounded"),
            "percentile": item.get("percentile"),
            "assessment_centre": None,
            "source": "historical_import",
        })

        mq_competencies.append({
            "competency": item.get("competency") or item.get("name"),
            "score": score_value,
            "stive": item.get("stive", score_value),
            "stive_rounded": item.get(
                "stive_rounded",
                round(score_value) if score_value is not None else None,
            ),
            "sten": item.get("sten"),
            "sten_rounded": item.get("sten_rounded"),
            "percentile": item.get("percentile"),
            "source": "historical_import",
        })

    normalised_personality_competencies = []

    for item in personality_competencies:
        normalised_personality_competencies.append({
            "competency": item.get("competency") or item.get("name"),
            "score": item.get("score"),
            "sten": item.get("sten"),
            "sten_rounded": item.get("sten_rounded"),
            "percentile": item.get("percentile"),
            "category": item.get("category"),
            "source": "historical_import",
        })

    normalised_team_style_scores = []

    for item in team_style_scores:
        score_value = item.get("score")

        normalised_team_style_scores.append({
            "competency": (
                item.get("competency")
                or item.get("name")
            ),

            "score": score_value,

            "stive": item.get(
                "stive",
                score_value,
            ),

            "stive_rounded": item.get(
                "stive_rounded",
                (
                    round(score_value)
                    if score_value is not None
                    else None
                ),
            ),

            "sten": item.get("sten"),
            "sten_rounded": item.get("sten_rounded"),
            "percentile": item.get("percentile"),

            "category": "team_style",
            "source": "historical_import",
        })

    motivation_results = sorted(
        motivation_results,
        key=lambda item: (
            item.get("competency") or ""
        ).lower(),
    )

    mq_competencies = sorted(
        mq_competencies,
        key=lambda item: (
            item.get("competency") or ""
        ).lower(),
    )

    normalised_personality_competencies = sorted(
        normalised_personality_competencies,
        key=lambda item: (
            item.get("competency") or ""
        ).lower(),
    )

    response_styles = build_response_style_results(
        normalised_personality_competencies
    )

    normalised_team_style_scores = sorted(
        normalised_team_style_scores,
        key=lambda item: (
            item.get("competency") or ""
        ).lower(),
    )

    # -------------------------------------------------------------------------
    # Shared score helpers
    # -------------------------------------------------------------------------

    def safe_score(item):
        """
        Return the first available numeric value.

        Explicit None checks are used so a legitimate value of 0 is not lost.
        """
        for key in (
            "score",
            "sten_rounded",
            "stive_rounded",
            "percentile",
        ):
            value = item.get(key)

            if value is not None:
                return value

        return -1

    top_motivations = sorted(
        mq_competencies,
        key=safe_score,
        reverse=True,
    )[:3]

    combined_personality_scores = (
        normalised_personality_competencies
        + normalised_team_style_scores
    )

    top_personality_traits = sorted(
        combined_personality_scores,
        key=safe_score,
        reverse=True,
    )[:3]

    motivation_development_areas = sorted(
        mq_competencies,
        key=safe_score,
    )[:2]

    personality_development_areas = sorted(
        combined_personality_scores,
        key=safe_score,
    )[:2]

    # -------------------------------------------------------------------------
    # Data supplied to the general insight engine
    # -------------------------------------------------------------------------

    general_insight_input = build_general_insight_input(
        personality_competencies=normalised_personality_competencies,
        motivation_competencies=mq_competencies,
        verbal_percentile=verbal_percentile,
        logical_percentile=logical_percentile,
        numerical_percentile=numerical_percentile,
    )

    # Temporary development logging.
    # Remove these prints once imported profiles have been verified.
    print("=== HISTORICAL GENERAL INSIGHT INPUT ===")
    print(json.dumps(
        general_insight_input,
        indent=2,
        ensure_ascii=False,
        default=str,
    ))
    print("=== /HISTORICAL GENERAL INSIGHT INPUT ===")

    # -------------------------------------------------------------------------
    # Ability reports
    # -------------------------------------------------------------------------

    ability_reports_for_ui = {
        "overview": [],
        "verbal": (
            build_cognitive_reports_for_test(
                test_key="verbal",
                percentile=verbal_percentile,
            )
            if verbal_percentile is not None
            else None
        ),
        "logical": (
            build_cognitive_reports_for_test(
                test_key="logical",
                percentile=logical_percentile,
            )
            if logical_percentile is not None
            else None
        ),
        "numerical": (
            build_cognitive_reports_for_test(
                test_key="numerical",
                percentile=numerical_percentile,
            )
            if numerical_percentile is not None
            else None
        ),
    }

    if ability_reports_for_ui["verbal"]:
        ability_reports_for_ui["overview"].append({
            "key": "verbal",
            "label": "Verbal",
            "percentile": verbal_percentile,
        })

    if ability_reports_for_ui["logical"]:
        ability_reports_for_ui["overview"].append({
            "key": "logical",
            "label": "Logical",
            "percentile": logical_percentile,
        })

    if ability_reports_for_ui["numerical"]:
        ability_reports_for_ui["overview"].append({
            "key": "numerical",
            "label": "Numerical",
            "percentile": numerical_percentile,
        })

    # -------------------------------------------------------------------------
    # Motivation reports
    # -------------------------------------------------------------------------

    motivation_scores = build_scores_by_competency(
        mq_competencies
    )

    motivation_insights = build_motivation_insight_section(
        mq_competencies,
        candidate_name=candidate.first_name,
    )

    motivation_reports_for_ui = []

    if has_motivation_results:
        motivation_reports_for_ui = [
            build_practitioner_report(
                competencies=mq_competencies,
            ),
            build_manager_report(
                competencies=mq_competencies,
            ),
            build_motivation_coaching_report(
                competencies=mq_competencies,
            ),
            build_candidate_report(
                competencies=mq_competencies,
            ),
        ]

        # -------------------------------------------------------------------------
        # Personality reports and profile
        # -------------------------------------------------------------------------

        personality_reports = []
        personality_profile = None

        if has_personality_results:
            historical_personality_competencies = (
                normalised_personality_competencies
                + normalised_team_style_scores
            )

            historical_personality_activities = [
                {
                    "activity": "Personality Assessment",
                    "status": "completed",
                    "competencies": historical_personality_competencies,
                }
            ]

            personality_reports = build_personality_reports_for_candidate(
                sova_activities=historical_personality_activities,
            )

            personality_profile_report = next(
                (
                    report
                    for report in personality_reports
                    if report.get("report_id") == "trait_indicator_profile"
                ),
                None,
            )

            if personality_profile_report:
                personality_profile = build_profile_from_resolved_report(
                    resolved_report=personality_profile_report,
                    language="sv",
                    include_missing_traits=False,
                )

    available_reports_count = 0

    if has_verbal_results:
        available_reports_count += 2

    if has_logical_results:
        available_reports_count += 2

    if has_numerical_results:
        available_reports_count += 2

    if has_motivation_results:
        available_reports_count += len(
            motivation_reports_for_ui
        )

    if has_personality_results:
        available_reports_count += len(
            personality_reports
        )

    # -------------------------------------------------------------------------
    # General candidate insights
    #
    # This is the temporary deterministic fallback. Later, replace this block
    # with the exact same insight generator used by active general-mode profiles.
    # -------------------------------------------------------------------------

    candidate_insights = {
        "summary": None,
        "key_strengths": [],
        "areas_to_explore": [],
        "questions": [],
        "fit": None,
        "cognitive_results": build_cognitive_insight_results(
            verbal_percentile=verbal_percentile,
            logical_percentile=logical_percentile,
            numerical_percentile=numerical_percentile,
        ),
    }

    if has_any_results:
        candidate_insights["summary"] = {
            "body": (
                "This candidate profile is based on structured historical "
                "SOVA assessment data. The insights are presented in general "
                "mode because no original process purpose or role context is "
                "available."
            )
        }

    for item in top_personality_traits[:2]:
        competency = item.get("competency")
        value = safe_score(item)

        candidate_insights["key_strengths"].append({
            "title": competency,
            "body": (
                "This is one of the candidate's higher imported personality "
                "or team style scores."
            ),
            "how_it_may_show": (
                "This may appear as a recurring behavioural preference in "
                "relevant work situations."
            ),
            "why_it_matters": (
                "This theme may be useful when considering the candidate's "
                "general work style and contribution."
            ),
            "evidence": [
                f"{competency}: {value}"
            ],
        })

    for item in top_motivations[:2]:
        competency = item.get("competency")
        value = safe_score(item)

        candidate_insights["key_strengths"].append({
            "title": competency,
            "body": (
                "This is one of the candidate's higher imported motivation "
                "scores."
            ),
            "how_it_may_show": (
                "This may indicate the conditions or activities that tend "
                "to energise and engage the candidate."
            ),
            "why_it_matters": (
                "Motivational drivers can affect engagement, satisfaction "
                "and longer-term retention."
            ),
            "evidence": [
                f"{competency}: {value}"
            ],
        })

    for item in personality_development_areas[:2]:
        competency = item.get("competency")
        value = safe_score(item)

        candidate_insights["areas_to_explore"].append({
            "title": competency,
            "body": (
                "This is one of the candidate's lower imported personality "
                "or team style scores."
            ),
            "explore_through": (
                "Ask for examples of situations where this behaviour is more "
                "or less natural for the candidate."
            ),
            "what_to_listen_for": (
                "Listen for context, self-awareness and strategies the "
                "candidate uses to adapt."
            ),
            "evidence": [
                f"{competency}: {value}"
            ],
        })

    for item in motivation_development_areas[:2]:
        competency = item.get("competency")
        value = safe_score(item)

        candidate_insights["areas_to_explore"].append({
            "title": competency,
            "body": (
                "This is one of the candidate's lower imported motivation "
                "scores."
            ),
            "explore_through": (
                "Ask which types of work situations tend to reduce energy, "
                "interest or engagement."
            ),
            "what_to_listen_for": (
                "Listen for what the candidate needs from the role, manager "
                "and working environment."
            ),
            "evidence": [
                f"{competency}: {value}"
            ],
        })

    if has_any_results:
        candidate_insights["questions"] = [
            {
                "category": "strengths",
                "category_label": "Strength",
                "question": (
                    "Which parts of your work tend to bring out your "
                    "strongest qualities?"
                ),
                "why": (
                    "This helps validate whether the imported assessment "
                    "profile matches the candidate's own experience."
                ),
                "listen_for": (
                    "Concrete examples and consistency with the strongest "
                    "assessment themes."
                ),
            },
            {
                "category": "explore",
                "category_label": "Explore",
                "question": (
                    "Are there situations where your usual working style "
                    "becomes less effective?"
                ),
                "why": (
                    "This helps add context to lower or less preferred scores "
                    "without treating them automatically as weaknesses."
                ),
                "listen_for": (
                    "Self-awareness, nuance and practical adaptation "
                    "strategies."
                ),
            },
            {
                "category": "motivation",
                "category_label": "Motivation",
                "question": (
                    "What type of working environment gives you the most "
                    "energy over time?"
                ),
                "why": (
                    "This helps connect imported motivation scores to actual "
                    "working conditions."
                ),
                "listen_for": (
                    "Drivers, demotivators and environmental preferences."
                ),
            },
        ]

    # -------------------------------------------------------------------------
    # Header assessment/activity information
    # -------------------------------------------------------------------------

    sent_assessments = []

    for result in assessment_results:
        sent_assessments.append({
            "activity": result.assessment_type.title(),
            "status": (
                (result.status or "completed")
                .strip()
                .lower()
            ),
        })

    all_competencies = (
        mq_competencies
        + normalised_personality_competencies
        + normalised_team_style_scores
    )

    return {
        "company": process.company,
        "process": process,
        "candidate": candidate,

        "historical_candidate": historical_candidate,
        "historical_reports": historical_candidate.reports.all(),
        "assessment_results": assessment_results,

        "is_historical": True,

        # Historical candidates have no live invitation.
        "invitation": None,
        "inv": None,
        "assessment_url": None,
        "activity_events": [],
        "email_logs_by_id": {},

        # Header information.
        "sent_assessments": sent_assessments,
        "tests_sent_count": assessment_results.count(),
        "tests_completed_count": assessment_results.count(),

        # Shared result flags.
        "has_motivation_results": has_motivation_results,
        "has_personality_results": has_personality_results,
        "has_ability_results": has_ability_results,
        "has_verbal_results": has_verbal_results,
        "has_logical_results": has_logical_results,
        "has_numerical_results": has_numerical_results,
        "has_any_results": has_any_results,
        "all_assessments_completed": all_assessments_completed,

        # Normalised assessment data.
        "motivation_results": motivation_results,
        "mq_competencies": mq_competencies,
        "personality_competencies": (
            normalised_personality_competencies
        ),
        "team_style_scores": normalised_team_style_scores,
        "all_competencies": all_competencies,
        "ability_results": ability_results,

        "verbal_percentile": verbal_percentile,
        "logical_percentile": logical_percentile,
        "numerical_percentile": numerical_percentile,

        # Existing report builders.
        "motivation_scores": motivation_scores,
        "motivation_insights": motivation_insights,
        "motivation_reports_for_ui": motivation_reports_for_ui,
        "ability_reports_for_ui": ability_reports_for_ui,
        "personality_reports": personality_reports,
        "personality_profile": personality_profile,
        "available_reports_count": available_reports_count,

        # General insight data.
        "candidate_insights": candidate_insights,
        "general_insight_input": general_insight_input,

        "top_motivations": top_motivations,
        "top_personality_traits": top_personality_traits,
        "motivation_development_areas": (
            motivation_development_areas
        ),
        "personality_development_areas": (
            personality_development_areas
        ),

        # Historical candidates always use general mode.
        "purpose_report": None,
        "report_mode": "general",
        "context_config": {},
        "show_context_prompt": False,
        "summary_owner": historical_candidate,

        # Compatibility keys expected elsewhere in the template.
        "activities": [],
        "project_results": {},
        "project_scores": [],
        "competency_scores": [],
        "overall_score": None,
        "reports": [],

        "response_styles": response_styles,
        "response_style_segments": range(1, 11),

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
            "You do not have access to this process."
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

    summary_owner.ai_summary = ""
    summary_owner.ai_summary_status = "not_started"
    summary_owner.ai_summary_generated_at = None

    summary_owner.save(
        update_fields=[
            "ai_summary",
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
            "You do not have access to this process."
        )

    if process.is_historical:
        return JsonResponse(
            {
                "error": (
                    "Historical cognitive interpretation "
                    "is not connected yet."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )

    if invitation.status != "completed":
        return JsonResponse(
            {
                "error": (
                    "The candidate has not completed "
                    "the assessments yet."
                )
            },
            status=400,
        )

    cognitive_results = extract_cognitive_results(
        invitation
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
        saved_interpretation
        and current_status == "completed"
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
                invitation
            )
        )

        received_done_event = False

        try:
            for event in stream_cognitive_interpretation(
                owner=invitation,
                cognitive_results=cognitive_results,
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
            "You do not have access to this process."
        )

    if process.is_historical:
        return JsonResponse(
            {
                "error": (
                    "Historical cognitive interpretation "
                    "is not connected yet."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate_id=candidate_id,
    )

    invitation.ai_cognitive_interpretation = {}
    invitation.ai_cognitive_interpretation_status = (
        "not_started"
    )
    invitation.ai_cognitive_interpretation_generated_at = (
        None
    )
    invitation.ai_cognitive_interpretation_purpose = ""

    invitation.save(
        update_fields=[
            "ai_cognitive_interpretation",
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
            "You do not have access to this process."
        )

    if process.is_historical:
        return JsonResponse(
            {
                "error": (
                    "Historical motivation interpretation "
                    "is not connected yet."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )

    if invitation.status != "completed":
        return JsonResponse(
            {
                "error": (
                    "The candidate has not completed "
                    "the assessments yet."
                )
            },
            status=400,
        )

    motivation_results = extract_motivation_results(
        invitation
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
        saved_interpretation
        and current_status == "completed"
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
                invitation
            )
        )

        received_done_event = False

        try:
            for event in stream_motivation_interpretation(
                owner=invitation,
                motivation_results=motivation_results,
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
            
            questions = (
                interpretation.get("questions")
                or []
            )

            if len(questions) != 3:
                raise ValueError(
                    "The AI response did not contain "
                    "three valid motivation questions."
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
            "You do not have access to this process."
        )

    if process.is_historical:
        return JsonResponse(
            {
                "error": (
                    "Historical motivation interpretation "
                    "is not connected yet."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate_id=candidate_id,
    )

    invitation.ai_motivation_interpretation = {}
    invitation.ai_motivation_interpretation_status = (
        "not_started"
    )
    invitation.ai_motivation_interpretation_generated_at = (
        None
    )
    invitation.ai_motivation_interpretation_purpose = ""

    invitation.save(update_fields=[
        "ai_motivation_interpretation",
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
def process_candidate_personality_interpretation_stream(
    request,
    process_id,
    candidate_id,
):
    """
    Stream and save an AI-supported interpretation of the
    candidate's personality trait profile.
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
            "You do not have access to this process."
        )

    if process.is_historical:
        return JsonResponse(
            {
                "error": (
                    "Historical personality interpretation "
                    "is not connected yet."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )

    if invitation.status != "completed":
        return JsonResponse(
            {
                "error": (
                    "The candidate has not completed "
                    "the assessments yet."
                )
            },
            status=400,
        )

    personality_results = extract_personality_results(
        invitation
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
        invitation.ai_personality_interpretation_status
        or "not_started"
    )

    saved_interpretation = (
        invitation.ai_personality_interpretation
        or {}
    )

    current_purpose = normalize_purpose_key(
        process.purpose
    )

    saved_purpose = normalize_purpose_key(
        invitation.ai_personality_interpretation_purpose
    )

    # Safety check in case the purpose changed without the normal
    # outdated-marking flow being triggered.
    if (
        saved_interpretation
        and current_status == "completed"
        and saved_purpose != current_purpose
    ):
        current_status = "outdated"

        invitation.ai_personality_interpretation_status = (
            "outdated"
        )

        invitation.save(update_fields=[
            "ai_personality_interpretation_status",
        ])

    # Return an existing completed interpretation.
    if (
        saved_interpretation
        and current_status == "completed"
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
                    "The personality interpretation is "
                    "already being generated."
                )
            },
            status=409,
        )

    invitation.ai_personality_interpretation_status = (
        "generating"
    )

    invitation.save(update_fields=[
        "ai_personality_interpretation_status",
    ])

    def generator():
        interpretation = (
            create_empty_personality_interpretation(
                invitation
            )
        )

        received_done_event = False

        try:
            for event in stream_personality_interpretation(
                owner=invitation,
                personality_results=personality_results,
            ):
                interpretation = (
                    apply_personality_interpretation_event(
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

            # Require the main interpretation, but do not throw away
            # a valid result merely because a secondary list was short.
            if not (
                interpretation.get("interpretation")
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
                owner=invitation,
                interpretation=interpretation,
            )

        except Exception as error:
            invitation.ai_personality_interpretation_status = (
                "failed"
            )

            invitation.save(update_fields=[
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
            "You do not have access to this process."
        )

    if process.is_historical:
        return JsonResponse(
            {
                "error": (
                    "Historical personality interpretation "
                    "is not connected yet."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate_id=candidate_id,
    )

    invitation.ai_personality_interpretation = {}
    invitation.ai_personality_interpretation_status = (
        "not_started"
    )
    invitation.ai_personality_interpretation_generated_at = (
        None
    )
    invitation.ai_personality_interpretation_purpose = ""

    invitation.save(update_fields=[
        "ai_personality_interpretation",
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
            "You do not have access to this process."
        )

    if process.is_historical:
        return JsonResponse(
            {
                "error": (
                    "Historical personality questions "
                    "are not connected yet."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )

    if invitation.status != "completed":
        return JsonResponse(
            {
                "error": (
                    "The candidate has not completed "
                    "the assessments yet."
                )
            },
            status=400,
        )

    personality_results = extract_personality_results(
        invitation
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
        saved_result
        and current_status == "completed"
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
            invitation
        )

        received_done_event = False

        try:
            for event in stream_personality_questions(
                owner=invitation,
                personality_results=personality_results,
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

            has_user_selected_traits = bool(
                invitation.selected_personality_traits
            )

            minimum_trait_count = (
                1
                if has_user_selected_traits
                else 4
            )

            if not minimum_trait_count <= len(selected_traits) <= 6:
                raise ValueError(
                    (
                        "The personality trait selection was invalid."
                        if has_user_selected_traits
                        else (
                            "The AI response did not contain "
                            "between four and six valid personality traits."
                        )
                    )
                )

            if len(questions) != 3:
                raise ValueError(
                    "The AI response did not contain "
                    "three valid personality questions."
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
            "You do not have access to this process."
        )

    if process.is_historical:
        return JsonResponse(
            {
                "error": (
                    "Historical personality questions "
                    "are not connected yet."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate_id=candidate_id,
    )

    invitation.ai_personality_questions = {}
    invitation.ai_personality_questions_status = (
        "not_started"
    )
    invitation.ai_personality_questions_generated_at = (
        None
    )
    invitation.ai_personality_questions_purpose = ""

    invitation.save(update_fields=[
        "ai_personality_questions",
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
    Save the user's selected personality traits and mark
    the generated questions as outdated.
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
            "You do not have access to this process."
        )

    if process.is_historical:
        return JsonResponse(
            {
                "error": (
                    "Historical personality trait selection "
                    "is not connected yet."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation,
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

    raw_traits = payload.get(
        "traits"
    )

    if not isinstance(raw_traits, list):
        return JsonResponse(
            {
                "error": (
                    "Traits must be supplied as a list."
                )
            },
            status=400,
        )

    personality_results = extract_personality_results(
        invitation
    )

    selected_traits = normalise_selected_traits(
        selected_traits=raw_traits,
        available_results=personality_results,
    )

    if not 1 <= len(selected_traits) <= 6:
        return JsonResponse(
            {
                "error": (
                    "Select between one and six "
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

    invitation.save(update_fields=[
        "selected_personality_traits",
        "ai_personality_questions_status",
    ])

    return JsonResponse(
        {
            "ok": True,
            "selected_traits": selected_traits,
            "questions_status": (
                invitation
                .ai_personality_questions_status
            ),
        }
    )