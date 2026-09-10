import math

from django.utils.translation import gettext as _, gettext_noop

# Talena team styles language batch 1

_TEAM_STYLE_TRANSLATION_STRINGS = (
    gettext_noop('Catalyst'),
    gettext_noop('Director'),
    gettext_noop('Energiser'),
    gettext_noop('Architect'),
    gettext_noop('Harmoniser'),
    gettext_noop('Analyst'),
    gettext_noop('Auditor'),
    gettext_noop('Connector'),
    gettext_noop('Explore'),
    gettext_noop('Lead'),
    gettext_noop('Deliver'),
    gettext_noop('Critically review'),
    gettext_noop('Looks for creative and innovative solutions and ideas. Brings new insight and new approaches to the team.'),
    gettext_noop('May dismiss established approaches too quickly, overcomplicate issues or develop solutions that are more complex than necessary.'),
    gettext_noop('May communicate spontaneously and move quickly between ideas.'),
    gettext_noop('Show genuine interest, allow room for creativity and ask questions that help develop the idea.'),
    gettext_noop('Rejecting ideas before exploring them, or moving immediately into detailed facts and restrictions.'),
    gettext_noop('Coordinates the group, clarifies needs and goals, and delegates accordingly. Brings clarity and decisiveness to the team.'),
    gettext_noop('May become overly directive, move ahead too quickly or pursue their own agenda without giving enough space to other views.'),
    gettext_noop('May focus on tasks, direction and strategy and can sometimes appear relatively businesslike or distant.'),
    gettext_noop('Be clear, rational and businesslike. Focus on the task, expected outcomes and areas of responsibility.'),
    gettext_noop('Losing focus on the task, becoming overly personal or failing to deliver what has been agreed.'),
    gettext_noop('Gets things done and drives the team forward. Brings energy and a sense of motivation to the team.'),
    gettext_noop('May weaken focus by pursuing too many things at once or changing direction quickly. Can appear forceful or impatient with people who work at a slower pace.'),
    gettext_noop('May communicate quickly, directly and with a strong sense of pace.'),
    gettext_noop('Maintain momentum, focus on the most important details, show confidence and involve them in decisions.'),
    gettext_noop('Responding too slowly, being excessively cautious or spending too much time on minor details.'),
    gettext_noop('Turns ideas into practical actions and plans. Brings efficiency, planning and organisation to the team.'),
    gettext_noop('May delay delivery through too much planning and preparation, and may find it difficult to adapt plans when requirements or priorities change.'),
    gettext_noop('May prefer concrete discussions about how ideas will be turned into actions.'),
    gettext_noop('Be specific, present a clear plan and describe the actions, responsibilities and practical next steps.'),
    gettext_noop('Discussing strategy without a practical plan, changing direction after work has started or setting unrealistic timelines.'),
    gettext_noop("Considers other people's needs and feelings. Brings cohesion and a sense of belonging to the team."),
    gettext_noop('May try too hard to please others, find it difficult to say no or set realistic boundaries, and may be less comfortable working independently.'),
    gettext_noop('May pay close attention to relationships, inclusion and how other people are feeling.'),
    gettext_noop('Show consideration, recognise individual needs and offer sincere appreciation and support.'),
    gettext_noop('Ignoring relationship concerns, communicating impersonally or placing excessive demands on people who are already under strain.'),
    gettext_noop('Considers alternatives and takes a critical view of ideas and plans. Brings objectivity and critical analysis to the team.'),
    gettext_noop('May spend so much time analysing and evaluating that decisions are delayed or opportunities pass. May appear overly negative or reluctant to accept other perspectives.'),
    gettext_noop('May focus on facts, evidence, sources and the reliability of available information.'),
    gettext_noop('Be factual and well prepared, provide sufficient detail and allow time to examine or verify important information.'),
    gettext_noop('Making unsupported claims, appearing careless or disorganised, withholding relevant information or setting unrealistic deadlines.'),
    gettext_noop('Looks for inaccuracies and shortcomings and focuses on delivering what was promised. Brings quality awareness and attention to detail to the team.'),
    gettext_noop('May devote too much time to minor details, overwork to maintain standards or follow rules and procedures so closely that delivery becomes less flexible.'),
    gettext_noop('May communicate carefully and methodically and prefer time to consider information before responding.'),
    gettext_noop('Be calm and systematic, explain the reasons for changes and be clear about deadlines, safety and follow-up.'),
    gettext_noop('Leaving deadlines unclear, demanding immediate answers or using a forceful approach without explaining why.'),
    gettext_noop('Builds, develops and uses networks and other useful resources. Brings new contacts and connections to the team.'),
    gettext_noop('May spend too much time interacting and networking at the expense of other goals, or involve others before the process is sufficiently clear.'),
    gettext_noop('May communicate in a friendly and relationship-focused way and place value on personal connection.'),
    gettext_noop('Explain what you want clearly, allow time for conversation, show appreciation and ask about their perspective.'),
    gettext_noop('Taking over the conversation, withholding information, showing little engagement or using a cold or dismissive tone.'),
)


CHART_CENTER = 200

CHART_OUTER_RADIUS = 148
CHART_OUTER_RING_INNER_RADIUS = 128

CHART_SLICE_OUTER_RADIUS = 128
CHART_SLICE_INNER_RADIUS = 70

CHART_RESULT_MAX_RADIUS = 54

TEAM_STYLE_CONFIG = [
    {
        "key": "catalyst",
        "source_names": ("catalyst", "katalysator"),
        "title": "Catalyst",
        "quadrant_key": "explore",
        "quadrant_label": "Explore",
        "angle": -112.5,
        "label_x": 100,
        "label_y": 34,
        "label_anchor": "middle",
        "contribution": (
            "Looks for creative and innovative solutions and ideas. "
            "Brings new insight and new approaches to the team."
        ),
        "possible_overuse": (
            "May dismiss established approaches too quickly, overcomplicate "
            "issues or develop solutions that are more complex than necessary."
        ),
        "communication_tendency": (
            "May communicate spontaneously and move quickly between ideas."
        ),
        "build_trust": (
            "Show genuine interest, allow room for creativity and ask "
            "questions that help develop the idea."
        ),
        "avoid": (
            "Rejecting ideas before exploring them, or moving immediately "
            "into detailed facts and restrictions."
        ),
    },
    {
        "key": "director",
        "source_names": ("director", "leader", "ledare"),
        "title": "Director",
        "quadrant_key": "lead",
        "quadrant_label": "Lead",
        "angle": -67.5,
        "label_x": 260,
        "label_y": 34,
        "label_anchor": "middle",
        "contribution": (
            "Coordinates the group, clarifies needs and goals, and delegates "
            "accordingly. Brings clarity and decisiveness to the team."
        ),
        "possible_overuse": (
            "May become overly directive, move ahead too quickly or pursue "
            "their own agenda without giving enough space to other views."
        ),
        "communication_tendency": (
            "May focus on tasks, direction and strategy and can sometimes "
            "appear relatively businesslike or distant."
        ),
        "build_trust": (
            "Be clear, rational and businesslike. Focus on the task, expected "
            "outcomes and areas of responsibility."
        ),
        "avoid": (
            "Losing focus on the task, becoming overly personal or failing "
            "to deliver what has been agreed."
        ),
    },
    {
        "key": "energiser",
        "source_names": ("energiser", "energizer", "motivator"),
        "title": "Energiser",
        "quadrant_key": "lead",
        "quadrant_label": "Lead",
        "angle": -22.5,
        "label_x": 332,
        "label_y": 122,
        "label_anchor": "end",
        "contribution": (
            "Gets things done and drives the team forward. Brings energy and "
            "a sense of motivation to the team."
        ),
        "possible_overuse": (
            "May weaken focus by pursuing too many things at once or changing "
            "direction quickly. Can appear forceful or impatient with people "
            "who work at a slower pace."
        ),
        "communication_tendency": (
            "May communicate quickly, directly and with a strong sense of pace."
        ),
        "build_trust": (
            "Maintain momentum, focus on the most important details, show "
            "confidence and involve them in decisions."
        ),
        "avoid": (
            "Responding too slowly, being excessively cautious or spending "
            "too much time on minor details."
        ),
    },
    {
        "key": "architect",
        "source_names": ("architect", "arkitekt"),
        "title": "Architect",
        "quadrant_key": "deliver",
        "quadrant_label": "Deliver",
        "angle": 22.5,
        "label_x": 332,
        "label_y": 248,
        "label_anchor": "end",
        "contribution": (
            "Turns ideas into practical actions and plans. Brings efficiency, "
            "planning and organisation to the team."
        ),
        "possible_overuse": (
            "May delay delivery through too much planning and preparation, "
            "and may find it difficult to adapt plans when requirements or "
            "priorities change."
        ),
        "communication_tendency": (
            "May prefer concrete discussions about how ideas will be turned "
            "into actions."
        ),
        "build_trust": (
            "Be specific, present a clear plan and describe the actions, "
            "responsibilities and practical next steps."
        ),
        "avoid": (
            "Discussing strategy without a practical plan, changing direction "
            "after work has started or setting unrealistic timelines."
        ),
    },
    {
        "key": "harmoniser",
        "source_names": ("harmoniser", "harmonizer", "harmoniserare"),
        "title": "Harmoniser",
        "quadrant_key": "deliver",
        "quadrant_label": "Deliver",
        "angle": 67.5,
        "label_x": 260,
        "label_y": 336,
        "label_anchor": "middle",
        "contribution": (
            "Considers other people's needs and feelings. Brings cohesion and "
            "a sense of belonging to the team."
        ),
        "possible_overuse": (
            "May try too hard to please others, find it difficult to say no "
            "or set realistic boundaries, and may be less comfortable working "
            "independently."
        ),
        "communication_tendency": (
            "May pay close attention to relationships, inclusion and how "
            "other people are feeling."
        ),
        "build_trust": (
            "Show consideration, recognise individual needs and offer sincere "
            "appreciation and support."
        ),
        "avoid": (
            "Ignoring relationship concerns, communicating impersonally or "
            "placing excessive demands on people who are already under strain."
        ),
    },
    {
        "key": "analyst",
        "source_names": ("analyst", "analytiker"),
        "title": "Analyst",
        "quadrant_key": "review",
        "quadrant_label": "Critically review",
        "angle": 112.5,
        "label_x": 100,
        "label_y": 336,
        "label_anchor": "middle",
        "contribution": (
            "Considers alternatives and takes a critical view of ideas and "
            "plans. Brings objectivity and critical analysis to the team."
        ),
        "possible_overuse": (
            "May spend so much time analysing and evaluating that decisions "
            "are delayed or opportunities pass. May appear overly negative or "
            "reluctant to accept other perspectives."
        ),
        "communication_tendency": (
            "May focus on facts, evidence, sources and the reliability of "
            "available information."
        ),
        "build_trust": (
            "Be factual and well prepared, provide sufficient detail and "
            "allow time to examine or verify important information."
        ),
        "avoid": (
            "Making unsupported claims, appearing careless or disorganised, "
            "withholding relevant information or setting unrealistic deadlines."
        ),
    },
    {
        "key": "auditor",
        "source_names": ("auditor", "reviewer", "granskare"),
        "title": "Auditor",
        "quadrant_key": "review",
        "quadrant_label": "Critically review",
        "angle": 157.5,
        "label_x": 28,
        "label_y": 248,
        "label_anchor": "start",
        "contribution": (
            "Looks for inaccuracies and shortcomings and focuses on delivering "
            "what was promised. Brings quality awareness and attention to "
            "detail to the team."
        ),
        "possible_overuse": (
            "May devote too much time to minor details, overwork to maintain "
            "standards or follow rules and procedures so closely that delivery "
            "becomes less flexible."
        ),
        "communication_tendency": (
            "May communicate carefully and methodically and prefer time to "
            "consider information before responding."
        ),
        "build_trust": (
            "Be calm and systematic, explain the reasons for changes and be "
            "clear about deadlines, safety and follow-up."
        ),
        "avoid": (
            "Leaving deadlines unclear, demanding immediate answers or using "
            "a forceful approach without explaining why."
        ),
    },
    {
        "key": "connector",
        "source_names": ("connector", "sammanhållare", "sammanhallare"),
        "title": "Connector",
        "quadrant_key": "explore",
        "quadrant_label": "Explore",
        "angle": 202.5,
        "label_x": 28,
        "label_y": 122,
        "label_anchor": "start",
        "contribution": (
            "Builds, develops and uses networks and other useful resources. "
            "Brings new contacts and connections to the team."
        ),
        "possible_overuse": (
            "May spend too much time interacting and networking at the expense "
            "of other goals, or involve others before the process is "
            "sufficiently clear."
        ),
        "communication_tendency": (
            "May communicate in a friendly and relationship-focused way and "
            "place value on personal connection."
        ),
        "build_trust": (
            "Explain what you want clearly, allow time for conversation, show "
            "appreciation and ask about their perspective."
        ),
        "avoid": (
            "Taking over the conversation, withholding information, showing "
            "little engagement or using a cold or dismissive tone."
        ),
    },
]


def _normalise_name(value):
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .replace("_", " ")
        .split()
    )


def _coerce_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _coerce_int(value):
    try:
        return int(round(float(value))) if value is not None else None
    except (TypeError, ValueError):
        return None


def _get_team_style_values(item):
    """
    Read Sova's five-point STIVE result for a team style.

    Live payloads contain both stive and stive_rounded. Historical imports may
    expose the same five-point value as score. STEN is deliberately not used
    as a fallback because Talena should not convert between the scales.
    """
    if not item:
        return {
            "raw_value": None,
            "display_value": None,
        }

    raw_value = _coerce_float(item.get("stive"))
    display_value = _coerce_int(item.get("stive_rounded"))

    is_historical_team_style = (
        item.get("category") == "team_style"
        or item.get("source") == "historical_import"
    )

    if raw_value is None and is_historical_team_style:
        raw_value = _coerce_float(item.get("score"))

    if display_value is None and raw_value is not None:
        display_value = int(round(raw_value))

    if raw_value is None and display_value is not None:
        raw_value = float(display_value)

    if raw_value is not None:
        raw_value = max(1.0, min(5.0, raw_value))

    if display_value is not None:
        display_value = max(1, min(5, display_value))

    return {
        "raw_value": raw_value,
        "display_value": display_value,
    }


def _chart_point(angle, radius):
    radians = math.radians(angle)

    return {
        "x": round(
            CHART_CENTER + math.cos(radians) * radius,
            1,
        ),
        "y": round(
            CHART_CENTER + math.sin(radians) * radius,
            1,
        ),
    }


def _polar_to_cartesian(angle_degrees, radius):
    radians = math.radians(angle_degrees)

    return {
        "x": round(
            CHART_CENTER + math.cos(radians) * radius,
            1,
        ),
        "y": round(
            CHART_CENTER + math.sin(radians) * radius,
            1,
        ),
    }


def _describe_sector(start_angle, end_angle, outer_radius, inner_radius=0):
    outer_start = _polar_to_cartesian(start_angle, outer_radius)
    outer_end = _polar_to_cartesian(end_angle, outer_radius)

    large_arc_flag = 1 if abs(end_angle - start_angle) > 180 else 0

    if inner_radius <= 0:
        return (
            f"M {CHART_CENTER} {CHART_CENTER} "
            f"L {outer_start['x']} {outer_start['y']} "
            f"A {outer_radius} {outer_radius} 0 {large_arc_flag} 1 "
            f"{outer_end['x']} {outer_end['y']} Z"
        )

    inner_end = _polar_to_cartesian(end_angle, inner_radius)
    inner_start = _polar_to_cartesian(start_angle, inner_radius)

    return (
        f"M {outer_start['x']} {outer_start['y']} "
        f"A {outer_radius} {outer_radius} 0 {large_arc_flag} 1 "
        f"{outer_end['x']} {outer_end['y']} "
        f"L {inner_end['x']} {inner_end['y']} "
        f"A {inner_radius} {inner_radius} 0 {large_arc_flag} 0 "
        f"{inner_start['x']} {inner_start['y']} Z"
    )

def _build_team_style_relevance(display_value):
    """
    Determine how strongly the practical guidance should be applied.

    Sova provides fixed guidance for each team style, rather than separate
    low-, middle- and high-score interpretations. The STIVE result therefore
    controls how the source guidance is presented, not its content.
    """
    if display_value is None:
        return {
            "key": "unavailable",
            "label": None,
            "show_guidance": False,
            "guidance_intro": None,
        }

    if display_value >= 4:
        return {
            "key": "prominent",
            "label": _("Prominent style"),
            "show_guidance": True,
            "guidance_intro": _(
                "This is a prominent preference in the candidate's profile. "
                "The guidance below is therefore likely to be particularly "
                "relevant."
            ),
        }

    if display_value == 3:
        return {
            "key": "situational",
            "label": _("Situational style"),
            "show_guidance": True,
            "guidance_intro": _(
                "This preference is around the middle of the scale. "
                "The guidance may be relevant depending on the situation "
                "and team context."
            ),
        }

    return {
        "key": "less_likely",
        "label": _("Less likely style"),
        "show_guidance": True,
        "guidance_intro": _(
            "This is a less prominent preference in the candidate's profile. "
            "The guidance below may therefore be less characteristic of their "
            "usual approach, but can still be relevant in certain situations."
        ),
    }


def build_team_style_profile(personality_competencies):
    """
    Build Talena's team-style presentation from Sova personality results.

    Psychometric handling:
    - Raw STIVE (1-5) shapes the radar chart and determines display order.
    - Rounded STIVE (1-5) is the value shown in the interface.
    - No conversion from STEN is performed.
    """
    competency_lookup = {}

    for item in personality_competencies or []:
        name = _normalise_name(
            item.get("competency") or item.get("name")
        )

        if name:
            competency_lookup[name] = item

    chart_styles = []

    for config_index, config in enumerate(TEAM_STYLE_CONFIG):
        config = {
            **config,
            "title": _(config["title"]),
            "quadrant_label": _(config["quadrant_label"]),
            "contribution": _(config["contribution"]),
            "possible_overuse": _(config["possible_overuse"]),
            "communication_tendency": _(
                config["communication_tendency"]
            ),
            "build_trust": _(config["build_trust"]),
            "avoid": _(config["avoid"]),
        }
        source = None

        for source_name in config["source_names"]:
            source = competency_lookup.get(
                _normalise_name(source_name)
            )

            if source:
                break

        values = _get_team_style_values(source)
        raw_value = values["raw_value"]
        display_value = values["display_value"]
        available = raw_value is not None and display_value is not None

        relevance = _build_team_style_relevance(
            display_value
        )

        score_radius = (
            CHART_RESULT_MAX_RADIUS * raw_value / 5
            if available
            else 0
        )

        score_point = _chart_point(
            config["angle"],
            score_radius,
        )

        axis_point = _chart_point(
            config["angle"],
            CHART_OUTER_RADIUS,
        )

        start_angle = config["angle"] - 22.5
        end_angle = config["angle"] + 22.5

        outer_ring_path = _describe_sector(
            start_angle=start_angle,
            end_angle=end_angle,
            outer_radius=CHART_OUTER_RADIUS,
            inner_radius=CHART_OUTER_RING_INNER_RADIUS,
        )

        slice_path = _describe_sector(
            start_angle=start_angle,
            end_angle=end_angle,
            outer_radius=CHART_SLICE_OUTER_RADIUS,
            inner_radius=CHART_SLICE_INNER_RADIUS,
        )

        label_point = _polar_to_cartesian(
            config["angle"],
            92,
        )

        chart_styles.append({
            **config,
            "config_index": config_index,
            "relevance": relevance,
            "available": available,
            "raw_value": raw_value,
            "display_value": display_value,
            "chart_x": score_point["x"],
            "chart_y": score_point["y"],
            "axis_x": axis_point["x"],
            "axis_y": axis_point["y"],
            "scale_segments": range(1, 6),
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
            "outer_ring_path": outer_ring_path,
            "slice_path": slice_path,
            "label_center_x": label_point["x"],
            "label_center_y": label_point["y"],
        })

    available_styles = [
        style
        for style in chart_styles
        if style["available"]
    ]

    ranked_styles = sorted(
        available_styles,
        key=lambda style: (
            -style["raw_value"],
            style["config_index"],
        ),
    )

    polygon_points = " ".join(
        f'{style["chart_x"]},{style["chart_y"]}'
        for style in chart_styles
    )

    rings = []

    for value in range(1, 6):
        radius = round(
            CHART_RESULT_MAX_RADIUS * value / 5,
            1,
        )

        rings.append({
            "value": value,
            "radius": radius,
        })

        chart_labels = [style["title"] for style in chart_styles if style["available"]]
        chart_values = [
            style["display_value"]
            for style in chart_styles
            if style["available"]
        ]
        chart_backgrounds = []
        chart_border_colors = []

        # Talena brand palette, also used by the client-side chart theme.
        # Keep the server-rendered fallback branded so the chart is correct
        # even before the enhancement script has run.
        quadrant_colors = {
            "explore": {
                "bg": "rgba(239, 94, 82, 0.30)",
                "border": "rgba(239, 94, 82, 0.85)",
            },
            "lead": {
                "bg": "rgba(207, 137, 127, 0.30)",
                "border": "rgba(207, 137, 127, 0.85)",
            },
            "deliver": {
                "bg": "rgba(126, 162, 143, 0.30)",
                "border": "rgba(126, 162, 143, 0.85)",
            },
            "review": {
                "bg": "rgba(197, 151, 79, 0.30)",
                "border": "rgba(197, 151, 79, 0.85)",
            },
        }

        for style in chart_styles:
            if not style["available"]:
                continue

            colors = quadrant_colors.get(style["quadrant_key"], {
                "bg": "rgba(239, 94, 82, 0.30)",
                "border": "rgba(239, 94, 82, 0.85)",
            })

            chart_backgrounds.append(colors["bg"])
            chart_border_colors.append(colors["border"])

    return {
        "available": bool(available_styles),
        "complete": len(available_styles) == len(TEAM_STYLE_CONFIG),
        "styles": ranked_styles,
        "chart_styles": chart_styles,
        "polygon_points": polygon_points,
        "rings": rings,
        "chart": {
            "labels": chart_labels,
            "values": chart_values,
            "backgrounds": chart_backgrounds,
            "border_colors": chart_border_colors,
        },
    }
