PURPOSE_TO_REPORT_MODE = {
    # General insights
    "flexible": "general",
    "unsure": "general",

    # Recruitment
    "recruitment": "recruitment",
    "hiring": "recruitment",
    "role_match": "recruitment",
    "internal_role_match": "recruitment",

    # Development, coaching and career
    "career_path": "development",
    "onboarding": "development",
    "new_hire": "development",
    "onboarding_new_hire": "development",
    "employee_development": "development",

    # Leadership
    "leadership_potential": "leadership",
    "leader_development": "leadership",

    # Team and organisation
    "team_development": "team",
    "reorganisation": "team",
}


REPORT_MODE_CONTENT = {
    "recruitment": {
        "key": "recruitment",
        "label": "Recruitment",
        "title": "Recruitment-focused result view",
        "intro": (
            "Use this view to support selection decisions, prepare follow-up questions "
            "and understand how the candidate may match the role."
        ),
        "summary_title": "Candidate fit overview",
        "summary_description": (
            "This section highlights strengths, possible concerns and areas to explore "
            "before making a hiring decision."
        ),
        "personality_title": "Personality signals for role fit",
        "personality_description": (
            "These traits can help you understand how the candidate may behave in the role, "
            "collaborate with others and respond to typical work demands."
        ),
        "motivation_title": "Motivation and work environment fit",
        "motivation_description": (
            "These motivators can help you understand what may drive the candidate and "
            "what type of environment is likely to support performance and retention."
        ),
        "ability_title": "Ability results for selection support",
        "ability_description": (
            "Use cognitive ability results as one part of the overall selection picture, "
            "especially when the role requires problem-solving, analysis or handling complex information."
        ),
        "followup_title": "Suggested follow-up focus",
        "followup_items": [
            "Explore how the candidate’s strongest traits connect to the requirements of the role.",
            "Use lower or more extreme scores as areas for structured interview follow-up.",
            "Compare motivation patterns with what the role and work environment can realistically offer.",
            "Avoid using one result in isolation. Combine test data with interview, experience and references.",
        ],
    },

    "development": {
        "key": "development",
        "label": "Development",
        "title": "Development-focused result view",
        "intro": (
            "Use this view to support onboarding, reflection, coaching and "
            "individual development. The focus is on strengths, growth areas "
            "and the conditions that may help the person perform and develop."
        ),

        "summary_title": "Development overview",
        "summary_description": (
            "This section highlights strengths to build on, areas to reflect on "
            "and practical themes for onboarding or development conversations."
        ),

        "personality_title": "Personality patterns for development",
        "personality_description": (
            "These traits may help explain the person’s natural working style, "
            "strengths and behaviours that could be developed or adapted."
        ),

        "motivation_title": "Motivation and energy drivers",
        "motivation_description": (
            "These results may help clarify what gives the person energy, "
            "what may reduce engagement and which conditions may support "
            "sustainable performance."
        ),

        "ability_title": "Ability results as learning context",
        "ability_description": (
            "Use cognitive ability results as context for learning, "
            "problem-solving style and potential development needs, "
            "not as a standalone judgement."
        ),

        "followup_title": "Suggested development focus",
        "followup_items": [
            "Discuss which strengths the person wants to use more intentionally.",
            "Explore which work conditions may increase energy, focus and motivation.",
            "Turn relevant development areas into practical experiments, support actions or coaching goals.",
            "Use the results as a conversation starter rather than a fixed description of the person.",
        ],
    },

    "leadership": {
        "key": "leadership",
        "label": "Leadership",
        "title": "Leadership-focused result view",
        "intro": (
            "Use this view to understand leadership-related strengths, development "
            "areas and the conditions that may support effective leadership."
        ),
        "summary_title": "Leadership overview",
        "summary_description": (
            "This section highlights leadership-related patterns, possible strengths "
            "and areas that may benefit from further exploration."
        ),
        "personality_title": "Personality patterns in leadership",
        "personality_description": (
            "These traits can help explain how the person may lead, communicate, "
            "influence others and respond to pressure or change."
        ),
        "motivation_title": "Leadership motivation and drivers",
        "motivation_description": (
            "These motivators can help clarify what may energise the person in a "
            "leadership role and which conditions may support sustained performance."
        ),
        "ability_title": "Ability results in leadership context",
        "ability_description": (
            "Use cognitive ability results as one part of understanding how the "
            "person may process complexity, solve problems and make decisions."
        ),
        "followup_title": "Suggested leadership focus",
        "followup_items": [
            "Explore how the person creates direction and gains commitment from others.",
            "Discuss how they respond to pressure, uncertainty and competing priorities.",
            "Identify leadership strengths that can be used more intentionally.",
            "Use the results as development support rather than a fixed judgement.",
        ],
    },

    "team": {
        "key": "team",
        "label": "Team / organisation",
        "title": "Team and organisation-focused result view",
        "intro": (
            "Use this view to understand how the person may contribute to team dynamics, collaboration "
            "and change. The focus is on interaction, working conditions and organisational fit."
        ),
        "summary_title": "Team contribution overview",
        "summary_description": (
            "This section highlights possible contributions, collaboration patterns and areas that may need support "
            "in a team or organisational context."
        ),
        "personality_title": "Personality patterns in collaboration",
        "personality_description": (
            "These traits can help you understand how the person may communicate, collaborate, take initiative "
            "and respond to change or pressure in a team setting."
        ),
        "motivation_title": "Motivation in the team environment",
        "motivation_description": (
            "These motivators can help clarify what the person needs from the team, manager and wider organisation "
            "to stay engaged and contribute well."
        ),
        "ability_title": "Ability results in team context",
        "ability_description": (
            "Use ability results to understand how the person may approach problem-solving, information processing "
            "and complexity within the team."
        ),
        "followup_title": "Suggested team focus",
        "followup_items": [
            "Explore how the person’s strengths can complement the rest of the team.",
            "Discuss what type of collaboration and communication supports their best contribution.",
            "Look for possible friction points between motivation, role expectations and team culture.",
            "Use the results to support better dialogue, not to label people.",
        ],
    },

    "general": {
        "key": "general",
        "label": "General",
        "title": "General result view",
        "intro": (
            "Use this view to understand the person’s results across personality, motivation and ability."
        ),
        "summary_title": "Result overview",
        "summary_description": (
            "This section summarises key result patterns and areas that may be useful to explore further."
        ),
        "personality_title": "Personality overview",
        "personality_description": (
            "These traits describe patterns in behaviour, preferences and working style."
        ),
        "motivation_title": "Motivation overview",
        "motivation_description": (
            "These results describe what may drive engagement, energy and satisfaction at work."
        ),
        "ability_title": "Ability overview",
        "ability_description": (
            "These results provide information about cognitive ability areas included in the assessment."
        ),
        "followup_title": "Suggested follow-up",
        "followup_items": [
            "Explore the most relevant result areas in conversation.",
            "Look at strengths, lower scores and possible patterns across the different tests.",
            "Use the results together with other information about the person and context.",
        ],
    },
}


def get_report_mode_for_purpose(purpose):
    return PURPOSE_TO_REPORT_MODE.get(purpose or "", "general")


def get_report_mode_content(purpose):
    mode = get_report_mode_for_purpose(purpose)
    return REPORT_MODE_CONTENT.get(mode, REPORT_MODE_CONTENT["general"])