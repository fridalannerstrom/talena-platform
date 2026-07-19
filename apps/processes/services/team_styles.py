import math


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


# Source: Sova TQ Personality - Team Report (Team Style Implications and
# communication guidance). The wording is intentionally kept source-led.
SOVA_TEAM_STYLE_GUIDANCE = {
    "connector": {
        "expected_behavior": (
            "Friendly and talkative; initiates new contacts, builds relationships "
            "and maintains good awareness of the outside world."
        ),
        "potential_limitations": (
            "Can spend too long interacting with others at the expense of achieving "
            "other goals and objectives. May be too quick to involve others, thereby "
            "compromising time or process-related efficiency within the team."
        ),
        "build_trust": (
            "Clearly show what you want, be flexible and allow time to talk. Show "
            "that you enjoy their company, ask how they feel and let them express "
            "their feelings."
        ),
        "create_irritation": (
            "Controlling or taking over the conversation, not disclosing information, "
            "not showing eagerness, or using a cold or dismissive tone."
        ),
    },
    "catalyst": {
        "expected_behavior": (
            "Talkative, impulsive and expressive. May use their hands when talking, "
            "become emotional easily and be less careful with time."
        ),
        "potential_limitations": (
            "Can be too quick to dismiss what is working well and may pursue change "
            "for the sake of change. May overcomplicate issues or design solutions "
            "that are unnecessarily complex."
        ),
        "build_trust": (
            "Show positive commitment, be flexible and allow time for creativity. "
            "Ask for their opinions or comments and show appreciation for their ideas."
        ),
        "create_irritation": (
            "Criticising ideas without being constructive, focusing on excessive "
            "detail, facts or figures, or showing little eagerness to listen to ideas."
        ),
    },
    "director": {
        "expected_behavior": (
            "Talks about the task and is happy to discuss strategy. May be perceived "
            "as distant or unaffected when discussing relationships."
        ),
        "potential_limitations": (
            "Tends to be quite directive and may be seen as too quick to tell others "
            "what to do. May push their own agenda rather than listen to others or "
            "consult to identify mutually agreeable outcomes."
        ),
        "build_trust": (
            "Do not discuss personal matters unless invited. Be clear, businesslike "
            "and rational."
        ),
        "create_irritation": (
            "Not focusing on the task, talking too much about personal matters or "
            "failing to deliver what has been requested."
        ),
    },
    "energiser": {
        "expected_behavior": (
            "Talks fast, makes a strong first impression and communicates directly. "
            "May appear impatient or try to control the situation."
        ),
        "potential_limitations": (
            "Can undermine the team's focus and motivation by pursuing too many "
            "things at once or changing direction too rapidly. May be seen as overly "
            "aggressive or intolerant of those who are less driven."
        ),
        "build_trust": (
            "Keep a high pace and focus on the most important details. Show confidence, "
            "involve them in decisions, avoid wasting time and focus on efficiency."
        ),
        "create_irritation": (
            "Not reacting quickly enough, speaking or acting too cautiously, focusing "
            "on insignificant matters or appearing muddled."
        ),
    },
    "architect": {
        "expected_behavior": (
            "Concrete and action-oriented. Asks how to proceed, breaks down broad "
            "strategies into actions and can work independently without needing to lead."
        ),
        "potential_limitations": (
            "May delay execution and delivery through excessive planning and preparation. "
            "May struggle to modify plans in response to changing requirements, "
            "conditions or priorities."
        ),
        "build_trust": (
            "Be specific and show how. Have a clear plan, discuss matters affecting the "
            "group, let them take over the baton and establish clear action and "
            "development plans."
        ),
        "create_irritation": (
            "Discussing strategy without a plan, changing course after work has started, "
            "changing conditions too quickly or setting unrealistic time frames."
        ),
    },
    "harmoniser": {
        "expected_behavior": (
            "Patient and attentive to how colleagues feel. Communicates inclusively and "
            "focuses on cohesion and making the group feel good."
        ),
        "potential_limitations": (
            "Can be too eager to please others and may struggle to say no or set realistic "
            "boundaries. May rely too heavily on a team-based approach and find "
            "independent work difficult."
        ),
        "build_trust": (
            "Show that you care, consider individuals within the group, express sincere "
            "appreciation, focus on loyalty and communicate clearly when something is urgent."
        ),
        "create_irritation": (
            "Focusing only on the task when relationships are strained, not engaging "
            "personally, being harsh or dismissive, or demanding too much from people "
            "already under strain."
        ),
    },
    "analyst": {
        "expected_behavior": (
            "Refers to and asks questions about facts and statistics. Acts carefully "
            "without reliable data, gestures sparingly, reviews critically and is "
            "suspicious of superlatives."
        ),
        "potential_limitations": (
            "May spend so long analysing and evaluating that action is delayed and "
            "opportunities are lost. Can be seen as overly critical or too quick to "
            "find fault with new ideas and proposed approaches."
        ),
        "build_trust": (
            "Be concrete and fact-oriented, avoid intrusive personal questions, support "
            "creative ideas with evidence, be prepared and careful, and provide proven "
            "assurances for important decisions."
        ),
        "create_irritation": (
            "Being spontaneous without referring to facts for important decisions, "
            "appearing careless or disorganised, overselling ideas, or setting "
            "unrealistic time frames."
        ),
    },
    "auditor": {
        "expected_behavior": (
            "Patient, easy-going, reserved and methodical. Tends to finish what they "
            "start and may be perceived as careful."
        ),
        "potential_limitations": (
            "Can labour over small details and miss the bigger picture. May adhere too "
            "rigidly to rules and procedures or struggle to recognise when commitments "
            "should change with circumstances."
        ),
        "build_trust": (
            "Create a friendly atmosphere, be calm and careful, present information "
            "systematically, explain reasons and benefits when change is required, show "
            "appreciation and focus on safety and follow-up."
        ),
        "create_irritation": (
            "Being vague about deadlines, not engaging personally, being dominant or "
            "demanding without explanation, or requiring quick answers."
        ),
    },
}


def _team_style_relevance(display_value):
    if display_value is None:
        return None
    if display_value >= 4:
        return {
            "key": "prominent",
            "label": "Prominent style",
            "guidance_intro": (
                "This is a prominent preference in the candidate's profile. The "
                "guidance below is therefore likely to be particularly relevant."
            ),
            "show_guidance": True,
        }
    if display_value == 3:
        return {
            "key": "situational",
            "label": "Situational style",
            "guidance_intro": (
                "This preference is around the middle of the scale. The guidance "
                "may be relevant depending on the situation and team context."
            ),
            "show_guidance": True,
        }
    return {
        "key": "less_likely",
        "label": "Less likely style",
        "guidance_intro": (
            "This is a less likely style for the candidate. Behavioural guidance "
            "is not shown as candidate-typical for this result."
        ),
        "show_guidance": False,
    }


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

        guidance = SOVA_TEAM_STYLE_GUIDANCE.get(config["key"], {})
        relevance = _team_style_relevance(display_value)

        chart_styles.append({
            **config,
            **guidance,
            "relevance": relevance,
            "config_index": config_index,
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

        quadrant_colors = {
            "explore": {
                "bg": "rgba(184, 17, 120, 0.30)",
                "border": "rgba(184, 17, 120, 0.85)",
            },
            "lead": {
                "bg": "rgba(62, 142, 230, 0.30)",
                "border": "rgba(62, 142, 230, 0.85)",
            },
            "deliver": {
                "bg": "rgba(35, 43, 180, 0.30)",
                "border": "rgba(35, 43, 180, 0.85)",
            },
            "review": {
                "bg": "rgba(111, 60, 183, 0.30)",
                "border": "rgba(111, 60, 183, 0.85)",
            },
        }

        for style in chart_styles:
            if not style["available"]:
                continue

            colors = quadrant_colors.get(style["quadrant_key"], {
                "bg": "rgba(104, 82, 214, 0.30)",
                "border": "rgba(104, 82, 214, 0.85)",
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
