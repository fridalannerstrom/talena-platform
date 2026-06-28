"""Shared candidate insight content for active and historical candidates."""

from __future__ import annotations

from typing import Any, Literal
import re

InsightMode = Literal["general", "context"]

# Indicators that may be highly significant, but where a high score
# should not automatically be presented as a strength.
DOUBLE_EDGED_INDICATORS = {
    "stubborn",
    "rigid",
    "casual",
    "dramatic",
    "unpredictable",
    "dependent",
    "dependence",
    "vulnerability",
    "over sensitive",
    "over-sensitive",
    "volatility",
    "impulsiveness",
    "hesitant",
    "detached",
}

EXPLORE_COMBINATION_RULES = {
    "flexibility_when_challenged": {
        "title": "Flexibility when challenged",
        "high_any": {
            "stubborn",
            "rigid",
        },
        "low_any": {
            "flexibility",
            "flexible",
            "adaptability",
            "adapting to change",
            "openness to change",
            "change oriented",
            "dealing with the changes",
        },
        "high_threshold": 8,
        "low_threshold": 4,
        "body": (
            "The candidate may show strong persistence and conviction, "
            "but could find it difficult to reconsider an established "
            "position or adapt quickly when circumstances change."
        ),
        "explore_through": (
            "Ask about a situation where the candidate needed to abandon "
            "an original plan, accept another person’s approach or adjust "
            "quickly to unexpected change."
        ),
        "what_to_listen_for": (
            "Listen for self-awareness, openness to new information and "
            "practical strategies for adapting without losing determination."
        ),
    },

    "structure_and_follow_through": {
        "title": "Structure and follow-through",
        "high_any": {
            "casual",
        },
        "low_any": {
            "self discipline",
            "keeping promises",
            "attention to detail",
            "meticulous",
            "order",
            "structured",
            "planning and organising",
            "planning and organizing",
        },
        "high_threshold": 8,
        "low_threshold": 4,
        "body": (
            "The candidate may prefer an informal or flexible approach, "
            "which could make consistent structure and detailed follow-through "
            "more demanding in some situations."
        ),
        "explore_through": (
            "Ask for an example involving detailed planning, recurring "
            "deadlines or responsibility for completing precise work."
        ),
        "what_to_listen_for": (
            "Listen for practical systems, checking routines and examples "
            "of maintaining reliability over time."
        ),
    },

    "independence_and_reassurance": {
        "title": "Independent decision-making",
        "high_any": {
            "dependent",
            "dependence",
        },
        "low_any": {
            "independence",
            "self reliant",
            "thinking independently",
        },
        "high_threshold": 7,
        "low_threshold": 4,
        "body": (
            "The candidate may value guidance, reassurance or close alignment "
            "with others when making decisions."
        ),
        "explore_through": (
            "Ask about a situation where the candidate needed to make an "
            "important decision without immediate support or detailed guidance."
        ),
        "what_to_listen_for": (
            "Listen for confidence in personal judgement, appropriate use "
            "of support and the ability to act independently when required."
        ),
    },

    "emotional_response_under_pressure": {
        "title": "Emotional response under pressure",
        "high_any": {
            "vulnerability",
            "over sensitive",
            "over-sensitive",
            "volatility",
        },
        "low_any": {
            "emotional control",
            "controlling stress",
            "calm",
            "composed",
            "recovering",
            "resilience",
        },
        "high_threshold": 7,
        "low_threshold": 4,
        "body": (
            "The candidate may experience demanding or uncertain situations "
            "more intensely and may need effective strategies for maintaining "
            "balance under pressure."
        ),
        "explore_through": (
            "Ask about a demanding period involving criticism, uncertainty "
            "or sustained pressure and how the candidate managed it."
        ),
        "what_to_listen_for": (
            "Listen for emotional self-awareness, recovery strategies and "
            "the ability to continue functioning effectively under pressure."
        ),
    },
}


INSIGHT_THEMES = {
    "structured_delivery": {
        "title": "Structured and reliable delivery",
        "indicator_keys": {
            "planning",
            "planning and organising",
            "planning and organizing",
            "quality focus",
            "reliability",
            "self discipline",
            "attention to detail",
            "task focus",
            "keeping promises",
            "meticulous",
            "structured",
            "order",
            "perfectionism",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may bring structure, accuracy and dependable "
            "follow-through to their work."
        ),
        "strength_show": (
            "May organise work clearly, maintain quality and follow agreed "
            "tasks through to completion."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where accuracy, planning and "
                "dependable follow-through are important."
            ),
            "hiring": (
                "This may support roles that require reliable delivery, clear "
                "planning, accuracy and consistent follow-through."
            ),
            "leadership": (
                "This may help the candidate create clarity, maintain standards "
                "and follow through on agreed priorities."
            ),
            "development": (
                "This strength may provide a useful foundation for taking on "
                "greater responsibility, coordinating work and improving consistency."
            ),
            "team": (
                "This may help the team maintain structure, coordinate responsibilities "
                "and deliver work consistently."
            ),
            "internal_role_match": (
                "This may support an internal role that requires planning, accuracy, "
                "dependable execution or responsibility for recurring delivery."
            ),
        },
        "explore_body": (
            "It may be useful to explore how the candidate maintains "
            "structure, accuracy and follow-through in demanding situations."
        ),
        "explore_through": (
            "Ask for an example involving competing deadlines, detailed work "
            "or responsibility for recurring delivery."
        ),
    },

    "analytical_problem_solving": {
        "title": "Analytical problem solving",
        "indicator_keys": {
            "analytical thinking",
            "analytical",
            "analysing problems",
            "analyzing problems",
            "analytical orientation",
            "analytical approach",
            "analyst",
            "evaluating",
            "using the facts",
            "data focus",
            "logical reasoning",
            "numerical reasoning",
            "verbal reasoning",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may be comfortable examining information, "
            "identifying patterns and reaching evidence-based conclusions."
        ),
        "strength_show": (
            "May compare alternatives, question assumptions and use relevant "
            "information to support decisions."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where information needs to be examined, "
                "compared and translated into well-supported conclusions."
            ),
            "hiring": (
                "This may support roles that require problem-solving, evidence-based "
                "decisions or the ability to work with complex information."
            ),
            "leadership": (
                "This may help the candidate assess situations carefully, challenge "
                "assumptions and make decisions based on relevant evidence."
            ),
            "development": (
                "This strength may provide a useful foundation for developing sound "
                "judgement, problem-solving and confidence in complex decisions."
            ),
            "team": (
                "This may help the team examine problems carefully, compare options "
                "and avoid conclusions that are not supported by evidence."
            ),
            "internal_role_match": (
                "This may support an internal role involving analysis, problem-solving, "
                "evaluation or responsibility for evidence-based decisions."
            ),
        },
        "explore_body": (
            "It may be useful to explore how confidently the candidate works "
            "with information and reaches sound conclusions."
        ),
        "explore_through": (
            "Ask for an example of analysing a difficult problem and explain "
            "how the conclusion was reached."
        ),
    },

    "strategic_complex_thinking": {
        "title": "Strategic and complex thinking",
        "indicator_keys": {
            "strategic thinking",
            "strategic insight",
            "strategic focus",
            "complex thinking",
            "conceptual",
            "architect",
            "creates the vision",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may be comfortable considering broader patterns, "
            "longer-term implications and complex information."
        ),
        "strength_show": (
            "May connect different pieces of information, consider several "
            "perspectives and think beyond immediate operational details."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where broader patterns, complexity and "
                "longer-term implications need to be considered."
            ),
            "hiring": (
                "This may support roles that require the candidate to understand complex "
                "information, consider long-term consequences and make thoughtful decisions."
            ),
            "leadership": (
                "This may help the candidate connect operational decisions to broader goals "
                "and consider the longer-term impact of leadership choices."
            ),
            "development": (
                "This strength may provide a useful foundation for developing strategic "
                "judgement and handling increasingly complex responsibilities."
            ),
            "team": (
                "This may help the team connect detailed information to broader priorities "
                "and consider several perspectives before deciding."
            ),
            "internal_role_match": (
                "This may support an internal role involving strategic planning, complex "
                "decisions or responsibility beyond immediate operational tasks."
            ),
        },
        "explore_body": (
            "It may be useful to explore how the candidate translates "
            "strategic thinking into practical action."
        ),
        "explore_through": (
            "Ask for an example of turning a complex issue into a clear "
            "decision or course of action."
        ),
    },

    "innovation_originality": {
        "title": "Innovation and original thinking",
        "indicator_keys": {
            "innovating",
            "innovation",
            "thinking innovatively",
            "creativity",
            "generating ideas",
            "generates solutions",
            "unconventional",
            "curiosity",
            "experimenting",
            "catalyst",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may contribute original perspectives and be open "
            "to alternative ways of approaching challenges."
        ),
        "strength_show": (
            "May question established approaches, explore possibilities and "
            "suggest new ways forward."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where new perspectives and alternative "
                "approaches are valued."
            ),
            "hiring": (
                "This may support roles where the candidate needs to challenge "
                "established approaches, solve unfamiliar problems or contribute new ideas."
            ),
            "leadership": (
                "This may help the candidate encourage new thinking, challenge established "
                "assumptions and create space for improvement."
            ),
            "development": (
                "This strength may provide a useful foundation for developing greater "
                "innovation, experimentation and confidence in proposing new approaches."
            ),
            "team": (
                "This may help the team consider alternative perspectives and avoid "
                "becoming overly dependent on familiar solutions."
            ),
            "internal_role_match": (
                "This may be relevant for an internal role involving change, improvement, "
                "innovation or unfamiliar challenges."
            ),
        },
        "explore_body": (
            "It may be useful to explore how the candidate balances original "
            "thinking with practical requirements."
        ),
        "explore_through": (
            "Ask for an example where the candidate introduced a new approach "
            "and evaluated whether it would work."
        ),
    },

    "learning_orientation": {
        "title": "Learning orientation",
        "indicator_keys": {
            "learning mindset",
            "curiosity",
            "inquisitiveness",
            "openness to experience",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may show an active interest in learning, developing "
            "their knowledge and understanding unfamiliar topics."
        ),
        "strength_show": (
            "May seek information, ask questions and engage actively with "
            "new knowledge or experiences."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where continuous learning, curiosity "
                "and the ability to engage with unfamiliar topics are important."
            ),
            "hiring": (
                "This may support roles where the candidate needs to learn quickly, "
                "build new knowledge or adapt to unfamiliar subject areas."
            ),
            "leadership": (
                "This may help the candidate remain curious, learn from experience "
                "and encourage development within the wider team."
            ),
            "development": (
                "This may provide a strong foundation for learning new skills, "
                "seeking feedback and applying new knowledge in practice."
            ),
            "team": (
                "This may help the team stay curious, share learning and remain "
                "open to new information or approaches."
            ),
            "internal_role_match": (
                "This may support an internal move into a role that requires rapid "
                "learning, new subject knowledge or broader responsibilities."
            ),
        },
        "explore_body": (
            "It may be useful to explore how the candidate develops and "
            "applies new knowledge."
        ),
        "explore_through": (
            "Ask about something the candidate recently needed to learn and "
            "how they approached it."
        ),
    },

    "network_building": {
        "title": "Network building",

        "indicator_keys": {
            "building networks",
            "building strong networks",
            "connecting",
            "connector",
            "builds alliances",
            "keeping in touch",
            "initiating contact",
            "sociability",
        },

        "minimum_strong": 2,
        "allow_single_from": 8,

        "strength_body": (
            "The candidate may be comfortable establishing and maintaining "
            "useful professional relationships."
        ),

        # General fallback
        "strength_show": (
            "May establish contact with relevant people, maintain professional "
            "relationships and create useful connections over time."
        ),

        # Purpose-adapted expression
        "strength_show_by_purpose": {
            "default": (
                "May establish contact with relevant people, maintain professional "
                "relationships and create useful connections over time."
            ),

            "hiring": (
                "In a recruitment context, this may show as readily establishing "
                "contact with colleagues, stakeholders or external partners and "
                "maintaining useful working relationships."
            ),

            "leadership": (
                "In a leadership context, this may show as building trust across "
                "teams, maintaining key stakeholder relationships and connecting "
                "people who may benefit from working more closely together."
            ),

            "development": (
                "In a development context, this may show as using professional "
                "relationships to exchange knowledge, seek perspectives and broaden "
                "collaboration."
            ),

            "team": (
                "In a team context, this may show as connecting colleagues, "
                "maintaining dialogue and strengthening cooperation across group "
                "or functional boundaries."
            ),

            "internal_role_match": (
                "In an internal role context, this may show as building relationships "
                "outside the immediate team and establishing the contacts needed to "
                "work effectively across the organisation."
            ),
        },

        "explore_body": (
            "It may be useful to explore how the candidate establishes and "
            "maintains professional relationships."
        ),

        "explore_through": (
            "Ask for an example of building a relationship that supported "
            "a work-related outcome."
        ),
    },

    "supporting_others": {
        "title": "Supporting and developing others",
        "indicator_keys": {
            "developing others",
            "nurtures talent",
            "coaching and developing",
            "coaching developing",
            "supporting",
            "helpfulness",
            "compassion",
            "altruism",
            "looking out for others",
            "considerate",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may be motivated to support others and contribute "
            "to their development or wellbeing."
        ),
        "strength_show": (
            "May offer support, share knowledge and take an interest in the "
            "needs or development of colleagues."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where supporting, guiding or developing "
                "other people is important."
            ),
            "hiring": (
                "This may support roles that involve collaboration, service, coaching "
                "or responsibility for helping others succeed."
            ),
            "leadership": (
                "This may help the candidate build trust, support employee development "
                "and create conditions in which others can perform well."
            ),
            "development": (
                "This strength may provide a useful foundation for taking greater "
                "responsibility for coaching, feedback or employee development."
            ),
            "team": (
                "This may contribute to a supportive team climate where colleagues share "
                "knowledge and help one another develop."
            ),
            "internal_role_match": (
                "This may be relevant for an internal role involving mentoring, onboarding, "
                "people support or development responsibility."
            ),
        },
        "explore_body": (
            "It may be useful to explore how the candidate supports and "
            "develops others in practice."
        ),
        "explore_through": (
            "Ask for an example of helping another person improve, learn or "
            "manage a difficult situation."
        ),
    },

    "adaptability_pressure": {
        "title": "Adaptability under pressure",
        "indicator_keys": {
            "adaptability",
            "adapting to change",
            "openness to change",
            "change oriented",
            "dealing with the changes",
            "flexible",
            "flexibility",
            "variety",
            "resilience",
            "recovering",
            "staying strong",
            "emotional control",
            "controlling stress",
            "calm",
            "composed",
            "optimistic",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may remain adaptable and composed when demands "
            "or circumstances change."
        ),
        "strength_show": (
            "May adjust priorities, recover from setbacks and continue "
            "working effectively under pressure."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where priorities change, pressure rises "
                "or the individual needs to adjust to new circumstances."
            ),
            "hiring": (
                "This may support roles that involve changing demands, uncertainty, "
                "tight deadlines or the need to recover quickly from setbacks."
            ),
            "leadership": (
                "This may help the candidate remain composed, adjust direction and "
                "provide stability when circumstances or priorities change."
            ),
            "development": (
                "This strength may provide a useful foundation for taking on more "
                "complex, uncertain or demanding responsibilities."
            ),
            "team": (
                "This may help the team maintain momentum, adapt to changing demands "
                "and respond constructively under pressure."
            ),
            "internal_role_match": (
                "This may support an internal role involving change, uncertainty, "
                "competing priorities or increased pressure."
            ),
        },
        "explore_body": (
            "It may be useful to explore how the candidate responds when "
            "priorities shift or pressure increases."
        ),
        "explore_through": (
            "Ask for an example involving uncertainty, stress or several "
            "changing demands at once."
        ),
    },

    "drive_ownership": {
        "title": "Drive and ownership",
        "indicator_keys": {
            "achievement",
            "achievement striving",
            "drive to achieve",
            "drive and motivation",
            "goal focused",
            "competitive",
            "challenge",
            "independence",
            "self reliant",
            "thinking independently",
            "entrepreneurial",
            "drives momentum",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may show personal drive, initiative and a "
            "willingness to take responsibility for outcomes."
        ),
        "strength_show": (
            "May pursue objectives, act independently and maintain ownership "
            "of agreed responsibilities."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where initiative, personal responsibility "
                "and sustained effort are important."
            ),
            "hiring": (
                "This may support roles where the candidate needs to take ownership, "
                "work independently and maintain progress toward clear objectives."
            ),
            "leadership": (
                "This may help the candidate take responsibility, create momentum "
                "and follow through on decisions or commitments."
            ),
            "development": (
                "This strength may provide a useful foundation for taking on greater "
                "ownership, broader responsibility and more demanding goals."
            ),
            "team": (
                "This may help the team maintain momentum and benefit from a colleague "
                "who takes responsibility for agreed outcomes."
            ),
            "internal_role_match": (
                "This may support an internal role that requires initiative, autonomy, "
                "ownership or responsibility for driving work forward."
            ),
        },
        "explore_body": (
            "It may be useful to explore how the candidate takes ownership "
            "and maintains momentum."
        ),
        "explore_through": (
            "Ask about a situation where they needed to take initiative "
            "without detailed guidance."
        ),
    },

    "leadership_influence": {
        "title": "Leadership and influence",
        "indicator_keys": {
            "desire to lead",
            "taking the lead",
            "leading and influencing",
            "leads by example",
            "director",
            "assertive",
            "assertiveness",
            "persuading",
            "influential",
            "influencing",
            "inspiring others",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may be comfortable influencing direction, "
            "expressing a position and taking a visible role."
        ),
        "strength_show": (
            "May communicate a clear point of view, influence others and "
            "step forward when direction is needed."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where direction, influence and the ability "
                "to gain support from others are important."
            ),
            "hiring": (
                "This may support roles where the candidate needs to influence others, "
                "communicate a clear position or take responsibility for direction."
            ),
            "leadership": (
                "This may help the candidate provide direction, gain commitment and "
                "influence how people approach shared goals."
            ),
            "development": (
                "This strength may provide a useful foundation for developing greater "
                "leadership responsibility, influence and confidence in visible roles."
            ),
            "team": (
                "This may help the team create direction, move discussions forward "
                "and build support for decisions or priorities."
            ),
            "internal_role_match": (
                "This may support an internal role involving leadership, stakeholder "
                "influence, visible responsibility or ownership of direction."
            ),
        },
        "explore_body": (
            "It may be useful to explore how the candidate influences others "
            "and adapts their leadership approach."
        ),
        "explore_through": (
            "Ask for an example of gaining support for an idea or providing "
            "direction to others."
        ),
    },

    "communication_engagement": {
        "title": "Communication and engagement",
        "indicator_keys": {
            "effective communication",
            "open communication",
            "candid",
            "straightforward",
            "enthusiastic",
            "warmth",
            "initiating contact",
            "sociability",
            "connecting",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may communicate with energy and engage readily "
            "with other people."
        ),
        "strength_show": (
            "May express ideas openly, create engagement and establish contact "
            "with others."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where ideas need to be communicated "
                "clearly and other people need to be engaged."
            ),
            "hiring": (
                "This may support roles that require regular communication, stakeholder "
                "engagement or the ability to make messages understandable."
            ),
            "leadership": (
                "This may help the candidate communicate direction, create engagement "
                "and maintain open dialogue with others."
            ),
            "development": (
                "This strength may provide a useful foundation for developing broader "
                "influence, presentation skills and communication across audiences."
            ),
            "team": (
                "This may help the team share information openly, maintain dialogue "
                "and create engagement around shared work."
            ),
            "internal_role_match": (
                "This may support an internal role requiring stakeholder communication, "
                "presentation, coordination or regular interaction with others."
            ),
        },
        "explore_body": (
            "It may be useful to explore how the candidate adjusts their "
            "communication to different audiences."
        ),
        "explore_through": (
            "Ask for an example of communicating a difficult message or "
            "engaging an initially unreceptive audience."
        ),
    },

    "integrity_sincerity": {
        "title": "Integrity and sincerity",
        "indicator_keys": {
            "honesty",
            "earnest",
            "straightforward",
            "candid",
            "modest",
            "modesty",
            "humility",
            "humble",
            "being open and modest",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may value honesty, sincerity and an open approach "
            "in their interactions."
        ),
        "strength_show": (
            "May communicate sincerely, avoid unnecessary self-promotion and "
            "seek to behave consistently with stated values."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where trust, honesty and consistency "
                "between words and actions are important."
            ),
            "hiring": (
                "This may support roles where credibility, responsible judgement "
                "and open communication are particularly important."
            ),
            "leadership": (
                "This may help the candidate build trust, communicate honestly and "
                "create consistency between stated expectations and personal behaviour."
            ),
            "development": (
                "This strength may provide a useful foundation for developing trusted "
                "relationships and handling increasingly sensitive responsibilities."
            ),
            "team": (
                "This may contribute to trust, openness and a working environment "
                "where colleagues can communicate honestly with one another."
            ),
            "internal_role_match": (
                "This may support an internal role involving trust, confidentiality, "
                "responsible judgement or sensitive stakeholder relationships."
            ),
        },
        "explore_body": (
            "It may be useful to explore how the candidate handles situations "
            "where openness and diplomacy need to be balanced."
        ),
        "explore_through": (
            "Ask about a situation where the candidate needed to communicate "
            "an uncomfortable truth constructively."
        ),
    },

    "energy_momentum": {
        "title": "Energy and momentum",
        "indicator_keys": {
            "energetic",
            "dynamic",
            "enthusiastic",
            "energiser",
            "drives momentum",
            "intense",
            "catalyst",
        },
        "minimum_strong": 2,
        "allow_single_from": 8,
        "strength_body": (
            "The candidate may bring energy and momentum to tasks, discussions "
            "or collaborative activity."
        ),
        "strength_show": (
            "May create pace, communicate enthusiasm and encourage progress."
        ),
        "why_it_matters_by_purpose": {
            "default": (
                "This strength may be useful where energy, pace and the ability to "
                "encourage progress are important."
            ),
            "hiring": (
                "This may support roles that require visible energy, sustained activity "
                "or the ability to help move work forward."
            ),
            "leadership": (
                "This may help the candidate create momentum, communicate enthusiasm "
                "and encourage others to maintain progress."
            ),
            "development": (
                "This strength may provide a useful foundation for taking on work "
                "that requires greater visibility, pace or responsibility for momentum."
            ),
            "team": (
                "This may contribute energy to the team and help maintain pace, "
                "engagement and forward movement."
            ),
            "internal_role_match": (
                "This may support an internal role that requires pace, visible energy, "
                "initiative or responsibility for driving activity forward."
            ),
        },
        "explore_body": (
            "It may be useful to explore how the candidate maintains energy "
            "over longer or less stimulating assignments."
        ),
        "explore_through": (
            "Ask about a lengthy assignment where motivation or momentum was "
            "difficult to sustain."
        ),
    },
}


THEME_ICON_MAP = {
    "structured_delivery": "structure",
    "analytical_problem_solving": "analysis",
    "strategic_complex_thinking": "analysis",
    "innovation_originality": "idea",
    "learning_orientation": "idea",
    "network_building": "network",
    "collaboration": "network",
    "supporting_others": "support",
    "adaptability_pressure": "resilience",
    "drive_ownership": "leadership",
    "leadership_influence": "leadership",
    "communication_engagement": "communication",
    "integrity_sincerity": "support",
    "energy_momentum": "spark",
}


STRENGTH_EXPRESSIONS_BY_THEME = {
    "structured_delivery": {
        "default": (
            "May organise work clearly, maintain quality and follow agreed "
            "tasks through to completion."
        ),
        "hiring": (
            "May be well suited to responsibilities that require careful planning, "
            "consistent quality and reliable follow-through."
        ),
        "leadership": (
            "May bring clarity to leadership responsibilities by translating goals "
            "into plans, setting expectations and maintaining consistent standards."
        ),
        "development": (
            "May apply feedback systematically, build effective routines and gradually "
            "take responsibility for more complex delivery."
        ),
        "team": (
            "May help the team clarify responsibilities, coordinate shared work and "
            "maintain dependable delivery."
        ),
        "internal_role_match": (
            "May bring structure to new responsibilities and establish reliable "
            "working routines when moving into a different role."
        ),
    },

    "analytical_problem_solving": {
        "default": (
            "May examine information carefully, compare alternatives and use "
            "relevant evidence to support conclusions."
        ),
        "hiring": (
            "May be particularly effective in roles that require complex problems "
            "to be broken down, alternatives compared and conclusions clearly explained."
        ),
        "leadership": (
            "May support sound leadership decisions by examining situations carefully, "
            "testing assumptions and drawing on relevant evidence."
        ),
        "development": (
            "May identify patterns in experience, reflect carefully on outcomes and "
            "translate lessons into practical improvements."
        ),
        "team": (
            "May help the team clarify complex problems, introduce relevant evidence "
            "and challenge conclusions that are not well supported."
        ),
        "internal_role_match": (
            "May quickly understand complex issues in a new area and contribute "
            "well-reasoned conclusions."
        ),
    },

    "strategic_complex_thinking": {
        "default": (
            "May connect different pieces of information, consider several "
            "perspectives and think beyond immediate operational details."
        ),
        "hiring": (
            "May suit roles where the individual needs to look beyond immediate tasks "
            "and consider broader implications, dependencies and longer-term consequences."
        ),
        "leadership": (
            "May connect day-to-day decisions with broader direction and anticipate "
            "how current choices could affect future priorities."
        ),
        "development": (
            "May increasingly move beyond detailed task considerations to recognise "
            "broader systems, patterns and longer-term implications."
        ),
        "team": (
            "May help colleagues connect daily activity with wider priorities and "
            "consider several perspectives before reaching a decision."
        ),
        "internal_role_match": (
            "May recognise how a new area connects with wider organisational priorities "
            "and longer-term objectives."
        ),
    },

    "innovation_originality": {
        "default": (
            "May question established approaches, explore possibilities and "
            "suggest alternative ways forward."
        ),
        "hiring": (
            "May add value in roles that involve unfamiliar challenges, continuous "
            "improvement or the need to generate alternative solutions."
        ),
        "leadership": (
            "May encourage new ideas, challenge familiar assumptions and create space "
            "for practical experimentation and improvement."
        ),
        "development": (
            "May be willing to test new approaches, learn from the outcome and build "
            "confidence in proposing alternatives."
        ),
        "team": (
            "May introduce fresh perspectives, encourage experimentation and help the "
            "group avoid relying only on familiar solutions."
        ),
        "internal_role_match": (
            "May spot opportunities for improvement in a new area and suggest "
            "alternative approaches to established ways of working."
        ),
    },

    "learning_orientation": {
        "default": (
            "May seek information, ask questions and engage actively with "
            "new knowledge or experiences."
        ),
        "hiring": (
            "May adapt well to roles that require rapid learning, unfamiliar subject "
            "matter and an active willingness to ask relevant questions."
        ),
        "leadership": (
            "May remain open to new information, learn from feedback and encourage "
            "curiosity and continuous learning in others."
        ),
        "development": (
            "May engage actively with feedback, practise new skills and seek "
            "opportunities that extend current capability."
        ),
        "team": (
            "May share knowledge, ask useful questions and encourage colleagues to "
            "remain open to new information and perspectives."
        ),
        "internal_role_match": (
            "May actively build knowledge in a new function while applying relevant "
            "learning from previous experience."
        ),
    },

    "network_building": {
        "default": (
            "May establish contact with relevant people, maintain professional "
            "relationships and create useful connections over time."
        ),
        "hiring": (
            "May suit roles that depend on establishing contact readily and maintaining "
            "productive relationships with colleagues, stakeholders or external partners."
        ),
        "leadership": (
            "May build trust across teams, maintain important stakeholder relationships "
            "and connect people who would benefit from working more closely together."
        ),
        "development": (
            "May use professional relationships to exchange knowledge, seek new "
            "perspectives and broaden opportunities for collaboration."
        ),
        "team": (
            "May connect colleagues, maintain dialogue and strengthen cooperation "
            "across group or functional boundaries."
        ),
        "internal_role_match": (
            "May build relationships beyond the immediate team and establish the "
            "contacts needed to work effectively in a new part of the organisation."
        ),
    },

    "collaboration": {
        "default": (
            "May listen to others, share relevant information and contribute "
            "constructively toward shared objectives."
        ),
        "hiring": (
            "May be well suited to roles that depend on close cooperation, shared "
            "delivery and effective coordination with different people."
        ),
        "leadership": (
            "May involve others in decisions, build shared ownership and encourage "
            "cooperation around common goals."
        ),
        "development": (
            "May actively seek input, work across different interpersonal styles and "
            "strengthen the way they collaborate with others."
        ),
        "team": (
            "May support open dialogue, shared responsibility and constructive ways "
            "of working through differences."
        ),
        "internal_role_match": (
            "May establish effective working relationships with unfamiliar colleagues "
            "and stakeholder groups when moving into a new role."
        ),
    },

    "supporting_others": {
        "default": (
            "May offer support, share knowledge and take an interest in the "
            "needs or development of other people."
        ),
        "hiring": (
            "May contribute strongly in roles that involve helping colleagues, "
            "supporting customers or enabling other people to succeed."
        ),
        "leadership": (
            "May provide guidance, offer constructive feedback and create conditions "
            "in which other people can develop and perform effectively."
        ),
        "development": (
            "May be ready to take greater responsibility for mentoring, coaching or "
            "supporting the learning of others."
        ),
        "team": (
            "May notice when colleagues need support, share expertise and help others "
            "manage challenges."
        ),
        "internal_role_match": (
            "May support onboarding, knowledge transfer and colleague development "
            "within a new area of responsibility."
        ),
    },

    "adaptability_pressure": {
        "default": (
            "May adjust priorities, recover from setbacks and continue working "
            "effectively when circumstances change."
        ),
        "hiring": (
            "May be well suited to roles involving changing demands, shifting "
            "deadlines or regular exposure to unfamiliar situations."
        ),
        "leadership": (
            "May remain composed when circumstances change, adjust direction when "
            "necessary and provide stability to others."
        ),
        "development": (
            "May stretch into unfamiliar situations, learn from setbacks and adapt "
            "their approach in response to experience."
        ),
        "team": (
            "May help the group remain flexible, maintain perspective and continue "
            "making progress when priorities change."
        ),
        "internal_role_match": (
            "May adapt constructively to new routines, stakeholders and expectations "
            "while maintaining effective delivery."
        ),
    },

    "drive_ownership": {
        "default": (
            "May pursue objectives, act independently and maintain ownership "
            "of agreed responsibilities."
        ),
        "hiring": (
            "May suit roles that require initiative, personal responsibility and "
            "the ability to maintain progress without extensive guidance."
        ),
        "leadership": (
            "May create momentum, take responsibility for decisions and follow "
            "through consistently on commitments."
        ),
        "development": (
            "May pursue stretching goals, seek greater responsibility and sustain "
            "effort when challenges arise."
        ),
        "team": (
            "May take clear ownership of agreed actions and help maintain momentum "
            "toward shared goals."
        ),
        "internal_role_match": (
            "May step proactively into new responsibilities and take ownership while "
            "building knowledge of the role."
        ),
    },

    "leadership_influence": {
        "default": (
            "May communicate a clear position, influence others and step forward "
            "when direction is needed."
        ),
        "hiring": (
            "May be effective in roles that require visible responsibility, persuasive "
            "communication and the ability to gain support for a course of action."
        ),
        "leadership": (
            "May provide clear direction, build commitment and adapt their approach "
            "when influencing different people."
        ),
        "development": (
            "May be ready to practise more visible leadership, strengthen persuasive "
            "communication and build confidence when guiding others."
        ),
        "team": (
            "May move discussions forward, help the group reach decisions and build "
            "support around shared priorities."
        ),
        "internal_role_match": (
            "May establish credibility, communicate a clear position and influence "
            "stakeholders within a new area of responsibility."
        ),
    },

    "communication_engagement": {
        "default": (
            "May express ideas openly, create engagement and establish constructive "
            "dialogue with other people."
        ),
        "hiring": (
            "May suit roles that require ideas to be explained clearly, relevant "
            "questions to be asked and different stakeholders to be engaged."
        ),
        "leadership": (
            "May communicate direction clearly, invite dialogue and help others "
            "understand priorities and decisions."
        ),
        "development": (
            "May refine their communication for different audiences, seek feedback "
            "and build confidence in more visible situations."
        ),
        "team": (
            "May keep information flowing, encourage open exchange and help colleagues "
            "remain engaged in shared work."
        ),
        "internal_role_match": (
            "May build understanding with new stakeholders and adapt their communication "
            "to unfamiliar audiences."
        ),
    },

    "integrity_sincerity": {
        "default": (
            "May communicate sincerely, avoid unnecessary self-promotion and "
            "seek consistency between stated values and behaviour."
        ),
        "hiring": (
            "May be well suited to responsibilities where credibility, responsible "
            "judgement and candid communication are particularly important."
        ),
        "leadership": (
            "May communicate transparently, demonstrate personal credibility and "
            "maintain consistency between words and actions."
        ),
        "development": (
            "May receive feedback openly, acknowledge limitations and take personal "
            "responsibility for improvement."
        ),
        "team": (
            "May keep commitments, communicate openly and contribute to working "
            "relationships built on trust."
        ),
        "internal_role_match": (
            "May handle sensitive information responsibly and build trust with new "
            "colleagues or stakeholders."
        ),
    },

    "energy_momentum": {
        "default": (
            "May create pace, communicate enthusiasm and encourage continued progress."
        ),
        "hiring": (
            "May bring visible energy to roles that require sustained activity, "
            "initiative and a strong focus on forward movement."
        ),
        "leadership": (
            "May mobilise others, communicate enthusiasm and help maintain momentum "
            "through demanding periods."
        ),
        "development": (
            "May approach stretching assignments with initiative and remain actively "
            "engaged while building new capability."
        ),
        "team": (
            "May raise energy, encourage action and help the group regain momentum "
            "when progress slows."
        ),
        "internal_role_match": (
            "May bring visible drive to new responsibilities while actively building "
            "knowledge and confidence in the area."
        ),
    },

    # Cognitive strengths

    "cognitive_verbal_reasoning": {
        "default": (
            "May quickly understand written information, identify relevant points "
            "and communicate well-supported conclusions."
        ),
        "hiring": (
            "May be well suited to roles involving complex written information, "
            "detailed instructions, reports or evidence-based communication."
        ),
        "leadership": (
            "May absorb complex written material, compare different viewpoints and "
            "communicate a clear, well-supported rationale."
        ),
        "development": (
            "May learn effectively from written resources and articulate newly "
            "developed understanding with clarity."
        ),
        "team": (
            "May summarise written information and make complex material easier for "
            "colleagues to understand."
        ),
        "internal_role_match": (
            "May quickly navigate new documentation, policies and written subject "
            "matter when moving into a different role."
        ),
    },

    "cognitive_logical_reasoning": {
        "default": (
            "May quickly identify patterns, apply logical rules and reason "
            "through unfamiliar or abstract problems."
        ),
        "hiring": (
            "May be particularly effective in roles involving unfamiliar problems, "
            "complex systems or the need to identify patterns and test solutions."
        ),
        "leadership": (
            "May bring structure to ambiguous situations, test assumptions and "
            "compare possible courses of action."
        ),
        "development": (
            "May learn from complex challenges and refine the approach used to solve "
            "unfamiliar problems."
        ),
        "team": (
            "May clarify complex issues and help colleagues identify structured routes "
            "toward a solution."
        ),
        "internal_role_match": (
            "May quickly understand unfamiliar systems, processes and relationships "
            "within a new area."
        ),
    },

    "cognitive_numerical_reasoning": {
        "default": (
            "May quickly interpret numerical information, identify relevant "
            "relationships and reach accurate quantitative conclusions."
        ),
        "hiring": (
            "May be well suited to roles involving figures, metrics, financial "
            "information or decisions based on quantitative evidence."
        ),
        "leadership": (
            "May use numerical evidence to monitor performance, compare outcomes "
            "and support well-informed decisions."
        ),
        "development": (
            "May draw useful insight from metrics and use quantitative feedback "
            "to guide improvement."
        ),
        "team": (
            "May interpret figures accurately and translate numerical information "
            "into clear shared understanding."
        ),
        "internal_role_match": (
            "May quickly understand role-specific metrics, financial information "
            "and quantitative reporting in a new area."
        ),
    },
}

COGNITIVE_STRENGTH_PERCENTILE = 90
COGNITIVE_EXPLORE_PERCENTILE = 10


COGNITIVE_INSIGHT_CONFIG = {
    "verbal reasoning": {
        "theme_key": "cognitive_verbal_reasoning",
        "title": "Verbal reasoning",
        "strength_body": (
            "The candidate shows a particularly strong ability to understand, "
            "evaluate and draw conclusions from written information."
        ),
        "strength_show": (
            "May quickly identify relevant information, understand complex written "
            "material and reach well-supported verbal conclusions."
        ),
        "why_it_matters": (
            "This may be useful in work involving written information, instructions, "
            "reports, communication or evidence-based conclusions."
        ),
        "explore_body": (
            "The candidate’s result suggests that tasks involving complex written "
            "information may require more time, structure or support."
        ),
        "explore_through": (
            "Explore how the candidate approaches lengthy instructions, unfamiliar "
            "written material and situations requiring conclusions from text."
        ),
        "what_to_listen_for": (
            "Listen for practical strategies such as summarising information, asking "
            "clarifying questions, checking understanding and allowing sufficient time."
        ),
    },

    "logical reasoning": {
        "theme_key": "cognitive_logical_reasoning",
        "title": "Logical reasoning",
        "strength_body": (
            "The candidate shows a particularly strong ability to identify patterns, "
            "apply logical rules and solve unfamiliar problems."
        ),
        "strength_show": (
            "May quickly recognise relationships, test possible solutions and reason "
            "through new or abstract information."
        ),
        "why_it_matters": (
            "This may be useful in work involving unfamiliar problems, systems, "
            "patterns, diagnosis or complex decision-making."
        ),
        "explore_body": (
            "The candidate’s result suggests that unfamiliar logical or abstract "
            "problems may require more time, structure or support."
        ),
        "explore_through": (
            "Explore how the candidate approaches unfamiliar problems where the rules "
            "or solution are not immediately clear."
        ),
        "what_to_listen_for": (
            "Listen for structured problem-solving, willingness to test alternatives, "
            "use of available information and strategies for checking conclusions."
        ),
    },

    "numerical reasoning": {
        "theme_key": "cognitive_numerical_reasoning",
        "title": "Numerical reasoning",
        "strength_body": (
            "The candidate shows a particularly strong ability to understand, "
            "evaluate and draw conclusions from numerical information."
        ),
        "strength_show": (
            "May quickly interpret numerical data, identify relevant relationships "
            "and reach accurate conclusions from figures."
        ),
        "why_it_matters": (
            "This may be useful in work involving numerical data, calculations, "
            "financial information, metrics or quantitative decisions."
        ),
        "explore_body": (
            "The candidate’s result suggests that tasks involving numerical "
            "information may require more time, structure or support."
        ),
        "explore_through": (
            "Explore how the candidate handles calculations, numerical reports, "
            "percentages and decisions based on quantitative information."
        ),
        "what_to_listen_for": (
            "Listen for checking routines, use of tools, attention to accuracy and "
            "strategies for working carefully with numerical information."
        ),
    },
}

STRENGTH_ANCHOR_SOURCES = {
    "personality",
    "cognitive",
}

EXPLORE_ANCHOR_SOURCES = {
    "personality",
    "cognitive",
}

EVIDENCE_SOURCES = {
    "personality",
    "motivation",
    "cognitive",
}


def indicator_can_support_strength(
    indicator: dict[str, Any],
) -> bool:
    """
    Personality, motivation and cognitive indicators may support
    a strength.

    Double-edged personality indicators should not automatically
    be presented as strengths.
    """
    is_double_edged_personality = (
        indicator.get("source") == "personality"
        and indicator.get("key") in DOUBLE_EDGED_INDICATORS
    )

    return not is_double_edged_personality


def select_diverse_supporting_indicators(
    indicators: list[dict[str, Any]],
    limit: int = 4,
) -> list[dict[str, Any]]:
    """
    Select supporting indicators while trying to represent
    different assessment sources.

    This prevents four personality indicators from always pushing
    motivation and cognitive evidence out of the result.
    """
    ordered = sorted(
        indicators,
        key=lambda item: item.get("normalized_score", 0),
        reverse=True,
    )

    selected: list[dict[str, Any]] = []

    # First include the strongest result from each available source.
    for source in (
        "personality",
        "cognitive",
        "motivation",
    ):
        source_match = next(
            (
                item
                for item in ordered
                if item.get("source") == source
            ),
            None,
        )

        if source_match is not None:
            selected.append(source_match)

    # Then fill the remaining spaces with the strongest results overall.
    for item in ordered:
        if len(selected) >= limit:
            break

        if item not in selected:
            selected.append(item)

    return selected[:limit]


def normalize_indicator_key(value: Any) -> str:
    text = str(value or "").strip().lower()

    text = text.replace("&", " and ")
    text = text.replace("_", " ")
    text = text.replace("-", " ")

    return re.sub(r"\s+", " ", text).strip()


def ordinal_percentile(value: float) -> str:
    rounded = int(round(value))

    if 10 <= rounded % 100 <= 20:
        suffix = "th"
    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd",
        }.get(rounded % 10, "th")

    return f"{rounded}{suffix} percentile"


def safe_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_assessment_indicators(
    general_insight_input: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    source = general_insight_input or {}
    indicators: list[dict[str, Any]] = []

    personality_data = source.get("personality") or {}
    motivation_data = source.get("motivation") or {}
    ability_data = source.get("ability") or {}
    ability_results = ability_data.get("results") or {}

    personality_items = (
        personality_data.get("all_scores")
        or []
    )

    motivation_items = (
        motivation_data.get("all_scores")
        or []
    )

    # --------------------------------------------------
    # Personality
    #
    # Supports both Talena's current normalised format:
    # {"name": "Adaptability", "score": 7}
    #
    # and the original Sova format:
    # {
    #     "competency": "Thinking Independently",
    #     "sten": 5.23,
    #     "sten_rounded": 5,
    # }
    # --------------------------------------------------
    seen_personality = set()

    for item in personality_items:
        name = (
            item.get("name")
            or item.get("competency")
        )

        # Prefer the original STEN value when it is available.
        score = safe_float(item.get("sten"))

        if score is None:
            score = safe_float(item.get("score"))

        # Prefer Sova's own rounded STEN result.
        sten_rounded = safe_float(
            item.get("sten_rounded")
        )

        # Optional compatibility with other prepared data.
        if sten_rounded is None:
            sten_rounded = safe_float(
                item.get("score_rounded")
            )

        # Some prepared data may contain only the rounded score.
        if score is None and sten_rounded is not None:
            score = sten_rounded

        if not name or score is None:
            continue

        key = normalize_indicator_key(name)

        # Avoid duplicate personality traits.
        if key in seen_personality:
            continue

        seen_personality.add(key)

        # Keep the underlying result for identifying and
        # prioritising themes.
        normalized_score = max(
            1.0,
            min(10.0, score),
        )

        # Use Sova's rounded result for presentation.
        if sten_rounded is not None:
            sten_value = int(sten_rounded)
        else:
            # STEN values are always positive, so this gives
            # conventional rounding rather than Python's
            # round-to-even behaviour.
            sten_value = int(normalized_score + 0.5)

        sten_value = max(
            1,
            min(10, sten_value),
        )

        # Position on a scale where STEN 1 is the left endpoint
        # and STEN 10 is the right endpoint.
        sten_position = round(
            ((sten_value - 1) / 9) * 100,
            2,
        )

        indicators.append({
            "key": key,
            "name": str(name),
            "source": "personality",
            "source_label": "Personality assessment",

            "raw_score": score,
            "scale": "sten",
            "normalized_score": normalized_score,

            # Used by the visual STEN graph.
            "sten_value": sten_value,
            "sten_position": sten_position,

            "display_score": f"STEN {sten_value}",
            "tooltip": (
                f"Personality assessment · "
                f"STEN {sten_value} on a scale from 1 to 10."
            ),
        })

    # --------------------------------------------------
    # Motivation
    # Input format is expected to be:
    # {"name": "...", "score": ...}
    #
    # Your example currently contains no motivation
    # results, so this part will simply add nothing.
    # --------------------------------------------------
    seen_motivation = set()

    for item in motivation_items:
        name = item.get("name")
        score = safe_float(item.get("score"))

        if not name or score is None:
            continue

        key = normalize_indicator_key(name)

        if key in seen_motivation:
            continue

        seen_motivation.add(key)

        # Adjust this if the input later proves to use
        # another motivation scale.
        normalized_score = max(
            1.0,
            min(10.0, score * 2),
        )

        indicators.append({
            "key": key,
            "name": str(name),
            "source": "motivation",
            "source_label": "Motivation questionnaire",
            "raw_score": score,
            "scale": "five_point",
            "normalized_score": normalized_score,
            "display_score": f"{score:g}/5",
            "tooltip": (
                f"Motivation questionnaire · "
                f"score {score:g} of 5."
            ),
        })

    # --------------------------------------------------
    # Cognitive abilities
    # Input format:
    # ability.results.numerical_percentile
    # ability.results.logical_percentile
    # ability.results.verbal_percentile
    # --------------------------------------------------
    cognitive_results = [
        {
            "name": "Verbal reasoning",
            "value": ability_results.get(
                "verbal_percentile"
            ),
        },
        {
            "name": "Logical reasoning",
            "value": ability_results.get(
                "logical_percentile"
            ),
        },
        {
            "name": "Numerical reasoning",
            "value": ability_results.get(
                "numerical_percentile"
            ),
        },
    ]

    for cognitive_result in cognitive_results:
        name = cognitive_result["name"]
        percentile = safe_float(
            cognitive_result["value"]
        )

        if percentile is None:
            continue

        normalized_score = max(
            1.0,
            min(10.0, percentile / 10),
        )

        indicators.append({
            "key": normalize_indicator_key(name),
            "name": name,
            "source": "cognitive",
            "source_label": "Cognitive assessment",
            "raw_score": percentile,
            "scale": "percentile",
            "normalized_score": normalized_score,
            "display_score": ordinal_percentile(
                percentile
            ),
            "tooltip": (
                f"Cognitive assessment · "
                f"{ordinal_percentile(percentile)}."
            ),
        })

    return indicators

def build_cognitive_insights(
    indicators: list[dict[str, Any]],
    process_purpose: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    strengths: list[dict[str, Any]] = []
    explore_areas: list[dict[str, Any]] = []

    cognitive_indicators = [
        indicator
        for indicator in indicators
        if indicator.get("source") == "cognitive"
    ]

    for indicator in cognitive_indicators:
        key = indicator.get("key")
        config = COGNITIVE_INSIGHT_CONFIG.get(key)

        if not config:
            continue

        percentile = safe_float(
            indicator.get("raw_score")
        )

        if percentile is None:
            continue

        # --------------------------------------------
        # Very high cognitive result
        # --------------------------------------------
        if percentile >= COGNITIVE_STRENGTH_PERCENTILE:
            level = round(
                max(
                    1,
                    min(
                        10,
                        percentile / 10,
                    ),
                ),
                1,
            )

            strengths.append({
                "theme_key": config["theme_key"],
                "icon_key": "analysis",
                "title": config["title"],
                "body": config["strength_body"],
                "how_it_may_show": get_theme_strength_expression(
                    config["theme_key"],
                    config,
                    process_purpose,
                ),
                "purpose_label": get_process_purpose_label(
                    process_purpose
                ),
                "level": level,
                "level_rounded": round(level),
                "level_label": "Very high cognitive result",
                "explanation": (
                    f"This strength was identified from a result at the "
                    f"{ordinal_percentile(percentile)} in the cognitive assessment."
                ),
                "supporting_indicators": [indicator],
                "evidence": [
                    indicator["name"],
                ],
                "insight_type": "cognitive",
            })

        # --------------------------------------------
        # Very low cognitive result
        # --------------------------------------------
        elif percentile <= COGNITIVE_EXPLORE_PERCENTILE:
            normalized_score = max(
                1,
                min(
                    10,
                    percentile / 10,
                ),
            )

            level = round(
                11 - normalized_score,
                1,
            )

            explore_areas.append({
                "theme_key": config["theme_key"],
                "icon_key": "analysis",
                "title": config["title"],
                "body": config["explore_body"],
                "explore_through": config["explore_through"],
                "what_to_listen_for": config[
                    "what_to_listen_for"
                ],
                "level": level,
                "level_rounded": round(level),
                "level_label": "High priority to explore",
                "explanation": (
                    f"This area was identified from a result at the "
                    f"{ordinal_percentile(percentile)} in the cognitive assessment. "
                    f"It should be considered in relation to the requirements of the "
                    f"role and verified alongside other evidence."
                ),
                "supporting_indicators": [indicator],
                "evidence": [
                    indicator["name"],
                ],
                "area_type": "cognitive",
            })

    strengths.sort(
        key=lambda item: item["level"],
        reverse=True,
    )

    explore_areas.sort(
        key=lambda item: item["level"],
        reverse=True,
    )

    return strengths, explore_areas

PURPOSE_PERSPECTIVE_LABELS = {
    "default": "How this strength may show",
    "hiring": "Recruitment perspective",
    "leadership": "Leadership perspective",
    "development": "Development perspective",
    "team": "Team perspective",
    "internal_role_match": "Internal role perspective",
}


def get_process_purpose_label(
    process_purpose: str | None,
) -> str:
    purpose_key = normalize_process_purpose_key(
        process_purpose
    )

    return PURPOSE_PERSPECTIVE_LABELS.get(
        purpose_key,
        PURPOSE_PERSPECTIVE_LABELS["default"],
    )


def build_combination_explore_areas(
    indicators: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    explore_areas: list[dict[str, Any]] = []

    personality_indicators = [
        item
        for item in indicators
        if item.get("source") == "personality"
    ]

    for rule_key, rule in EXPLORE_COMBINATION_RULES.items():
        high_matches = [
            item
            for item in personality_indicators
            if (
                item.get("key") in rule["high_any"]
                and item["normalized_score"]
                >= rule.get("high_threshold", 8)
            )
        ]

        low_matches = [
            item
            for item in personality_indicators
            if (
                item.get("key") in rule["low_any"]
                and item["normalized_score"]
                <= rule.get("low_threshold", 4)
            )
        ]

        if not high_matches or not low_matches:
            continue

        high_matches.sort(
            key=lambda item: item["normalized_score"],
            reverse=True,
        )

        low_matches.sort(
            key=lambda item: item["normalized_score"],
        )

        selected = (
            high_matches[:2]
            + low_matches[:3]
        )

        high_strength = max(
            item["normalized_score"]
            for item in high_matches
        )

        low_strength = max(
            1,
            11 - min(
                item["normalized_score"]
                for item in low_matches
            ),
        )

        level = round(
            (high_strength + low_strength) / 2,
            1,
        )

        explanation = (
            "This area was identified from a combination of one or more "
            "elevated double-edged indicators and related lower assessment "
            "results. It is intended as a topic to verify, not a confirmed "
            "weakness."
        )

        explore_areas.append({
            "theme_key": rule_key,
            "title": rule["title"],
            "body": rule["body"],
            "explore_through": rule["explore_through"],
            "what_to_listen_for": rule["what_to_listen_for"],
            "level": level,
            "level_rounded": round(level),
            "level_label": "Priority to explore",
            "explanation": explanation,
            "supporting_indicators": selected,
            "evidence": [
                item["name"]
                for item in selected
            ],
            "area_type": "combination",
        })

    return explore_areas

def build_low_score_explore_areas(
    indicators: list[dict[str, Any]],
    excluded_theme_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    explore_areas: list[dict[str, Any]] = []
    excluded_theme_keys = excluded_theme_keys or set()

    for theme_key, theme in INSIGHT_THEMES.items():
        if theme_key in excluded_theme_keys:
            continue

        matched = [
            indicator
            for indicator in indicators
            if (
                indicator.get("source") in EVIDENCE_SOURCES
                and indicator.get("key")
                in theme["indicator_keys"]
            )
        ]

        if not matched:
            continue

        # Personality and cognitive results may anchor an area
        # to explore.
        lower_anchor_indicators = [
            item
            for item in matched
            if (
                item.get("source") in EXPLORE_ANCHOR_SOURCES
                and item["normalized_score"] <= 4
            )
        ]

        lower_anchor_indicators.sort(
            key=lambda item: item["normalized_score"],
        )

        # Lower motivation may add useful context, but should not
        # independently be described as a weakness.
        related_lower_motivation = [
            item
            for item in matched
            if (
                item.get("source") == "motivation"
                and item["normalized_score"] <= 4
            )
        ]

        related_lower_motivation.sort(
            key=lambda item: item["normalized_score"],
        )

        has_multiple_lower_anchors = (
            len(lower_anchor_indicators) >= 2
        )

        has_one_extremely_low_anchor = (
            len(lower_anchor_indicators) == 1
            and lower_anchor_indicators[0][
                "normalized_score"
            ] <= 2
        )

        # One clearly lower cognitive result may be relevant enough
        # to explore, even when only one cognitive test was completed.
        has_one_clearly_low_cognitive_result = (
            len(lower_anchor_indicators) == 1
            and lower_anchor_indicators[0].get(
                "source"
            ) == "cognitive"
            and lower_anchor_indicators[0][
                "normalized_score"
            ] <= 3
        )

        is_supported_explore_area = (
            has_multiple_lower_anchors
            or has_one_extremely_low_anchor
            or has_one_clearly_low_cognitive_result
        )

        if not is_supported_explore_area:
            continue

        supporting_pool = (
            lower_anchor_indicators
            + related_lower_motivation
        )

        selected = select_diverse_supporting_indicators(
            supporting_pool,
            limit=4,
        )

        # Exploration priority should be based on capability or
        # behavioural evidence, not on motivation alone.
        average_anchor_score = (
            sum(
                item["normalized_score"]
                for item in lower_anchor_indicators
            )
            / len(lower_anchor_indicators)
        )

        level = round(
            max(
                1,
                min(
                    10,
                    11 - average_anchor_score,
                ),
            ),
            1,
        )

        if level >= 8.5:
            level_label = "High priority to explore"
        elif level >= 7:
            level_label = "Explore further"
        else:
            level_label = "Consider exploring"

        source_labels = list(
            dict.fromkeys(
                item["source_label"]
                for item in selected
            )
        )

        source_text = ", ".join(source_labels)

        if len(lower_anchor_indicators) == 1:
            explanation = (
                "This area was identified from one clearly lower "
                "assessment result. It should be explored and verified, "
                "not treated as a confirmed weakness."
            )
        else:
            explanation = (
                f"This area was identified from "
                f"{len(lower_anchor_indicators)} related lower "
                f"assessment results. It should be explored and "
                f"verified, not treated as a confirmed weakness."
            )

        if related_lower_motivation:
            explanation += (
                " Related motivation results are included as contextual "
                "evidence about where the candidate may experience less "
                "energy or engagement."
            )

        explanation += (
            f" Supporting evidence is drawn from: {source_text}."
        )

        explore_areas.append({
            "theme_key": theme_key,
            "icon_key": THEME_ICON_MAP.get(
                theme_key,
                "spark",
            ),
            "title": theme["title"],
            "body": theme["explore_body"],
            "explore_through": theme["explore_through"],
            "what_to_listen_for": (
                "Listen for relevant context, self-awareness and practical "
                "strategies the candidate uses to manage this area."
            ),
            "level": level,
            "level_rounded": round(level),
            "level_label": level_label,
            "explanation": explanation,
            "supporting_indicators": selected,
            "evidence": [
                item["name"]
                for item in selected
            ],
            "area_type": "low_scores",
        })

    return explore_areas


def get_theme_why_it_matters(
    theme: dict[str, Any],
    process_purpose: str | None,
) -> str:
    purpose_texts = (
        theme.get("why_it_matters_by_purpose")
        or {}
    )

    normalized_purpose = str(
        process_purpose or "default"
    ).strip().lower()

    return (
        purpose_texts.get(normalized_purpose)
        or purpose_texts.get("default")
        or (
            "This theme may be relevant where the process requires "
            "these behaviours or capabilities."
        )
    )

PURPOSE_KEY_ALIASES = {
    # Recruitment
    "hiring": "hiring",
    "recruitment": "hiring",

    # Leadership
    "leadership": "leadership",
    "leadership potential": "leadership",
    "leadership development": "leadership",

    # Development
    "development": "development",
    "employee development": "development",

    # Team
    "team": "team",
    "team development": "team",

    # Internal role match
    "internal role match": "internal_role_match",
    "role match": "internal_role_match",
}


def normalize_process_purpose_key(
    process_purpose: Any,
) -> str:
    normalized = normalize_indicator_key(
        process_purpose or "default"
    )

    return PURPOSE_KEY_ALIASES.get(
        normalized,
        normalized.replace(" ", "_"),
    )


def get_theme_strength_expression(
    theme_key: str,
    theme: dict[str, Any],
    process_purpose: str | None,
) -> str:
    purpose_key = normalize_process_purpose_key(
        process_purpose
    )

    purpose_texts = (
        STRENGTH_EXPRESSIONS_BY_THEME.get(
            theme_key,
            {},
        )
    )

    return (
        purpose_texts.get(purpose_key)
        or purpose_texts.get("default")
        or theme.get("strength_show")
        or (
            "This strength may influence how the candidate approaches "
            "relevant tasks and working relationships."
        )
    )


def build_evidence_themes(
    indicators: list[dict[str, Any]],
    process_purpose: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    strengths: list[dict[str, Any]] = []

    for theme_key, theme in INSIGHT_THEMES.items():
        matched = [
            indicator
            for indicator in indicators
            if (
                indicator.get("source") in EVIDENCE_SOURCES
                and indicator.get("key")
                in theme["indicator_keys"]
            )
        ]

        if not matched:
            continue

        matched.sort(
            key=lambda item: item["normalized_score"],
            reverse=True,
        )

        # All clearly elevated assessment results that may support
        # this particular theme.
        strong_indicators = [
            item
            for item in matched
            if (
                item["normalized_score"] >= 7
                and indicator_can_support_strength(item)
            )
        ]

        if not strong_indicators:
            continue

        # A strength should have at least one capability or behavioural
        # anchor. Motivation may reinforce a strength, but should not
        # independently prove that the person is skilled in the area.
        anchor_indicators = [
            item
            for item in strong_indicators
            if item.get("source") in STRENGTH_ANCHOR_SOURCES
        ]

        minimum_strong = theme.get(
            "minimum_strong",
            2,
        )

        allow_single_from = theme.get(
            "allow_single_from",
            8,
        )

        has_multiple_strong_indicators = (
            len(strong_indicators) >= minimum_strong
            and bool(anchor_indicators)
        )

        has_one_very_strong_anchor = any(
            item["normalized_score"] >= allow_single_from
            for item in anchor_indicators
        )

        is_supported_strength = (
            has_multiple_strong_indicators
            or has_one_very_strong_anchor
        )

        if not is_supported_strength:
            continue

        selected = select_diverse_supporting_indicators(
            strong_indicators,
            limit=4,
        )

        level = round(
            sum(
                item["normalized_score"]
                for item in selected
            ) / len(selected),
            1,
        )

        if level >= 8.5:
            level_label = "Very strong evidence"
        elif level >= 7:
            level_label = "Strong evidence"
        else:
            level_label = "Moderate evidence"

        source_labels = list(
            dict.fromkeys(
                item["source_label"]
                for item in selected
            )
        )

        source_text = ", ".join(source_labels)

        if len(selected) == 1:
            explanation = (
                "This theme was identified from one particularly "
                "elevated assessment result. The individual result "
                "is shown below as supporting assessment evidence."
            )
        else:
            explanation = (
                f"This theme was identified from {len(selected)} "
                f"elevated assessment indicators across: "
                f"{source_text}. The individual results are shown "
                f"below as supporting assessment evidence."
            )

        strengths.append({
            "theme_key": theme_key,
            "icon_key": THEME_ICON_MAP.get(
                theme_key,
                "spark",
            ),
            "title": theme["title"],
            "body": theme["strength_body"],
            "how_it_may_show": get_theme_strength_expression(
                theme_key,
                theme,
                process_purpose,
            ),
            "purpose_label": get_process_purpose_label(
                process_purpose
            ),
            "level": level,
            "level_rounded": round(level),
            "level_label": level_label,
            "explanation": explanation,
            "supporting_indicators": selected,
            "evidence": [
                item["name"]
                for item in selected
            ],
        })

    strengths.sort(
        key=lambda item: (
            item["level"],
            len(item["supporting_indicators"]),
        ),
        reverse=True,
    )

    strength_theme_keys = {
        item["theme_key"]
        for item in strengths
    }

    # These rules deliberately remain personality-based because
    # they describe specific combinations of personality traits.
    combination_explore_areas = (
        build_combination_explore_areas(indicators)
    )

    combination_theme_keys = {
        item["theme_key"]
        for item in combination_explore_areas
    }

    low_score_explore_areas = (
        build_low_score_explore_areas(
            indicators,
            excluded_theme_keys=(
                strength_theme_keys
                | combination_theme_keys
            ),
        )
    )

    explore_areas = (
        combination_explore_areas
        + low_score_explore_areas
    )

    explore_areas.sort(
        key=lambda item: (
            item["level"],
            len(item["supporting_indicators"]),
        ),
        reverse=True,
    )

    return strengths[:4], explore_areas[:4]

def build_candidate_insights(
    *,
    mode: InsightMode = "general",
    general_insight_input: dict[str, Any] | None = None,
    process_purpose: str | None = None,
) -> dict[str, Any]:
    """Return the candidate insight structure used by the candidate sheet.

    ``general_insight_input`` is accepted now so both active and historical
    candidate flows use the same API. The current implementation still returns
    the deterministic content that previously lived in views.py.
    """

    candidate_insights_mode: InsightMode = (
        "context" if mode == "context" else "general"
    )

    assessment_indicators = normalize_assessment_indicators(
        general_insight_input
    )

    print(
        "PROCESS PURPOSE:",
        {
            "raw": process_purpose,
            "normalized": normalize_process_purpose_key(
                process_purpose
            ),
        },
        flush=True,
    )

    evidence_strengths, evidence_explore_areas = (
        build_evidence_themes(
            assessment_indicators,
            process_purpose=process_purpose,
        )
    )

    cognitive_strengths, cognitive_explore_areas = (
        build_cognitive_insights(
            assessment_indicators,
            process_purpose=process_purpose,
        )
    )

    evidence_strengths = (
        cognitive_strengths
        + evidence_strengths
    )

    evidence_explore_areas = (
        cognitive_explore_areas
        + evidence_explore_areas
    )

    evidence_strengths.sort(
        key=lambda item: (
            item.get("level", 0),
            len(item.get("supporting_indicators", [])),
        ),
        reverse=True,
    )

    evidence_explore_areas.sort(
        key=lambda item: (
            item.get("level", 0),
            len(item.get("supporting_indicators", [])),
        ),
        reverse=True,
    )

    evidence_strengths = evidence_strengths[:4]
    evidence_explore_areas = evidence_explore_areas[:4]


    if candidate_insights_mode == "context":
        candidate_insights = {
            "summary": {
                "headline": "Potential fit for a structured Business Controller role",
                "body": (
                    "The candidate shows a profile that may support structured analysis, reliable delivery and careful business follow-up. "
                    "For this Business Controller context, the strongest signal is the combination of analytical thinking, planning and quality focus. "
                    "The main areas to validate are stakeholder communication, pace when priorities change and the ability to turn analysis into practical recommendations."
                ),
                "bullets": [
                    {
                        "label": "Most important interpretation",
                        "text": "The candidate appears well aligned with work that requires structure, accuracy and thoughtful analysis, but the interview should validate how this translates into stakeholder-facing business support.",
                    },
                    {
                        "label": "Confidence / context level",
                        "text": "Medium confidence. The interpretation uses completed assessment data and the added Business Controller role context, but should be combined with interview evidence.",
                    },
                    {
                        "label": "What this report is based on",
                        "text": "Assessment results, personality and motivation indicators, cognitive reasoning data, and the added role context covering requirements, priorities and interview focus.",
                    },
                ],
            },
            "fit": {
                "title": "Role match verdict",
                "label": "Potential match",
                "confidence": "Medium",
                "summary": (
                    "Talena sees a promising match for the Business Controller role, mainly because the candidate shows strong "
                    "indicators for structure, analytical thinking and reliable delivery."
                ),
                "body": (
                    "Talena sees a promising match for the Business Controller role, mainly because the candidate shows strong "
                    "indicators for structure, analytical thinking and reliable delivery."
                ),
                "reasoning": [
                    "The role requires structured analysis and careful follow-up, which appears aligned with the candidate’s strengths in planning, quality focus and analytical thinking.",
                    "The candidate may be well suited to work that requires accuracy, ownership and thoughtful decision support.",
                    "The match is not yet strong enough to confirm without interview validation, especially around stakeholder-facing business support.",
                ],
                "watch_points": [
                    "Stakeholder communication",
                    "Pace under ambiguity",
                    "Commercial judgement",
                ],
                "suggested_next_step": "Proceed with a structured interview focused on stakeholder communication, changing priorities and business impact.",
                "decision_note": (
                    "This is a decision-support recommendation, not a final hiring decision. Combine it with interview evidence, experience and role requirements."
                ),
            },
            "key_strengths": evidence_strengths,
            "areas_to_explore": evidence_explore_areas,
            "questions": [
                {
                    "category": "strengths",
                    "category_label": "Strengths",
                    "question": "Tell me about a time when you used financial or business analysis to support an important decision.",
                    "why": "Helps validate analytical problem-solving and ability to turn data into practical recommendations.",
                    "listen_for": "Look for clear reasoning, business understanding, accuracy and impact on the decision.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Can you describe a situation where you had to explain complex financial information to someone without a finance background?",
                    "why": "Explores stakeholder communication and ability to make analysis understandable.",
                    "listen_for": "Look for clarity, adaptation to the audience and ability to connect numbers to business reality.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Tell me about a time when priorities changed close to a deadline. How did you handle it?",
                    "why": "Helps understand pace, flexibility and prioritisation under pressure.",
                    "listen_for": "Look for structure, calmness, communication and practical decision-making.",
                },
                {
                    "category": "motivation",
                    "category_label": "Motivation",
                    "question": "What type of financial or analytical work gives you the most energy?",
                    "why": "Explores motivation fit with the role’s recurring tasks and stakeholder support.",
                    "listen_for": "Look for alignment with analysis, quality, ownership and business impact.",
                },
                {
                    "category": "work_style",
                    "category_label": "Work style",
                    "question": "How do you prefer to work with managers who need support but may not know exactly what analysis they need?",
                    "why": "Explores consulting style, communication and ability to clarify needs.",
                    "listen_for": "Look for curiosity, structure, patience and ability to guide stakeholders.",
                },
            ],
            "motivation_environment": {
                "summary": (
                    "In this Business Controller context, the candidate’s likely motivation for quality, autonomy and meaningful contribution "
                    "may support independent delivery and careful analysis. Engagement may be strongest when expectations are clear and the work "
                    "has visible business value."
                ),
                "top_motivators": [
                    {
                        "title": "Quality",
                        "body": "May be motivated by accurate, reliable work and high standards.",
                    },
                    {
                        "title": "Autonomy",
                        "body": "May value ownership over tasks and freedom to decide how to approach analysis.",
                    },
                    {
                        "title": "Making a difference",
                        "body": "May gain energy from seeing that their work improves decisions or creates business value.",
                    },
                ],
                "possible_demotivators": [
                    {
                        "title": "Unclear priorities",
                        "body": "May lose energy if goals, responsibilities or decision-making authority remain vague.",
                    },
                    {
                        "title": "Low-quality shortcuts",
                        "body": "May become frustrated if speed is repeatedly prioritised over accuracy.",
                    },
                    {
                        "title": "Limited ownership",
                        "body": "May find it less engaging if there is little room to influence how work is done.",
                    },
                ],
                "best_environment": [
                    {
                        "title": "Clear expectations",
                        "body": "Clear priorities and success criteria may help the candidate focus effectively.",
                    },
                    {
                        "title": "Trust and responsibility",
                        "body": "The candidate may perform well when trusted to own analysis and follow through.",
                    },
                    {
                        "title": "Business-oriented dialogue",
                        "body": "Regular dialogue with managers can help connect analysis to practical decisions.",
                    },
                    {
                        "title": "Constructive feedback",
                        "body": "Feedback on usefulness and business impact may help maintain motivation.",
                    },
                ],
                "manager_tips": [
                    {
                        "title": "Clarify the business question",
                        "body": "Explain what decision the analysis should support before asking for numbers or reports.",
                    },
                    {
                        "title": "Agree on priorities",
                        "body": "Be clear about what is urgent, what can wait and what level of detail is needed.",
                    },
                    {
                        "title": "Give ownership",
                        "body": "Let the candidate own recurring analysis while agreeing on checkpoints and deadlines.",
                    },
                    {
                        "title": "Connect work to impact",
                        "body": "Show how their analysis contributes to decisions, improvements or financial control.",
                    },
                ],
                "context_implications": (
                    "For this role, the motivation profile may support careful and independent delivery. "
                    "The main thing to watch is whether the role provides enough clarity, ownership and connection to business impact."
                ),
            },
            "work_style": {
                "summary": (
                    "The candidate appears likely to work best with clarity, structure and enough space to think things through. "
                    "In this role context, that may support reliable analysis, careful financial follow-up and considered business recommendations."
                ),
                "items": [
                    {
                        "title": "How they work",
                        "subtitle": "Structure, pace and task approach",
                        "body": "May prefer clear expectations, organised work and time to understand the task before moving into action.",
                        "practical_tip": "Provide clear priorities and agree on what good delivery looks like early in the process.",
                        "evidence": ["Planning", "Reliability", "Quality Focus"],
                        "icon": "work",
                        "icon_class": "",
                    },
                    {
                        "title": "How they communicate",
                        "subtitle": "Information sharing and stakeholder dialogue",
                        "body": "May communicate most effectively when there is a clear purpose and enough context to form a considered view.",
                        "practical_tip": "Invite them to explain their reasoning and connect analysis to practical business consequences.",
                        "evidence": ["Communication", "Analytical Thinking"],
                        "icon": "communicate",
                        "icon_class": "is-blue",
                    },
                    {
                        "title": "How they handle change",
                        "subtitle": "Changing priorities and business needs",
                        "body": "May adapt well when changes are explained clearly, but may need clarity around priorities if several things change at once.",
                        "practical_tip": "When priorities shift, clarify what changed, what stays the same and what should be handled first.",
                        "evidence": ["Adaptability", "Decision-making"],
                        "icon": "change",
                        "icon_class": "is-green",
                    },
                    {
                        "title": "How they handle pressure",
                        "subtitle": "Deadlines and workload",
                        "body": "May perform best when pressure is paired with structure, realistic priorities and clear expectations.",
                        "practical_tip": "Use short check-ins during intense reporting periods to remove blockers and keep priorities visible.",
                        "evidence": ["Resilience", "Emotional Control"],
                        "icon": "pressure",
                        "icon_class": "is-orange",
                    },
                    {
                        "title": "How they prefer to be managed",
                        "subtitle": "Support, autonomy and feedback",
                        "body": "May respond well to a management style that combines trust and autonomy with clear goals and constructive feedback.",
                        "practical_tip": "Give ownership, but agree on checkpoints and make expectations explicit.",
                        "evidence": ["Autonomy", "Quality", "Achievement"],
                        "icon": "managed",
                        "icon_class": "is-pink",
                    },
                ],
                "footer_note": (
                    "This section translates personality and motivation indicators into practical behaviours for the current role context. "
                    "Full trait-level results can be reviewed further down as evidence."
                ),
            },
            "next_steps": [
                {
                    "label": "Recommended action",
                    "title": "Proceed with a structured interview",
                    "body": "Use the report to guide a focused interview rather than as a standalone decision.",
                    "focus": "Validate stakeholder communication, commercial judgement and pace under ambiguity.",
                },
                {
                    "label": "Interview focus",
                    "title": "Ask evidence-based follow-up questions",
                    "body": "Use behavioural questions to understand how the candidate applies analysis and structure in real work situations.",
                    "focus": "Ask for examples involving financial analysis, deadlines, prioritisation and influencing decisions.",
                },
                {
                    "label": "Decision support",
                    "title": "Combine assessment insights with interview evidence",
                    "body": "Use the assessment results together with interview notes, experience and role requirements.",
                    "focus": "Avoid making a decision from assessment data alone.",
                },
            ],
        }

    else:
        candidate_insights = {
            "summary": {
                "headline": (
                    "General assessment summary"
                    if candidate_insights_mode == "general"
                    else "Contextual candidate insight summary"
                ),
                "body": (
                    "The candidate’s assessment profile suggests a structured and analytical work style, with strong indicators around planning, quality focus and working with complex information. "
                    "This may support roles or situations where careful follow-up, accuracy and thoughtful problem-solving are important. "
                    "At the same time, the results should be explored further through conversation, especially around stakeholder influence, decision-making pace and how the candidate handles changing priorities. "
                    "Add role or process context to make this interpretation more specific."
                ),
            },
            "fit": {
                "label": (
                    "Insufficient context"
                    if candidate_insights_mode == "general"
                    else "Potential fit"
                ),
                "confidence": (
                    "Low"
                    if candidate_insights_mode == "general"
                    else "Medium"
                ),
                "suggested_next_step": (
                    "Add context"
                    if candidate_insights_mode == "general"
                    else "Structured follow-up"
                ),
                "body": (
                    "No process context has been added yet, so this section does not assess "
                    "fit for a specific role, team, leadership situation or development goal."
                    if candidate_insights_mode == "general"
                    else
                    "Based on the added context, the candidate appears to show several relevant "
                    "indicators. Some areas should be explored further before making a decision."
                ),
            },
                "key_strengths": evidence_strengths,
            "areas_to_explore": evidence_explore_areas,
            "questions": [
                {
                    "question": "Tell me about a time when you used analysis to influence a decision.",
                    "why": "Validates analytical thinking and communication in a practical situation.",
                },
                {
                    "question": "How do you handle situations where priorities change quickly?",
                    "why": "Explores adaptability, structure and decision-making under pressure.",
                },
                {
                    "question": "What type of work environment helps you perform at your best?",
                    "why": "Connects motivation and work style to the candidate’s preferred conditions.",
                },
            ],
            "motivation_environment": {
                "summary": (
                    "The candidate appears likely to be energised by quality, autonomy and meaningful contribution. "
                    "They may perform best in an environment with clear expectations, room for ownership and opportunities to do work properly."
                ),
                "top_motivators": [
                    {
                        "title": "Quality",
                        "body": "May be motivated by doing work to a high standard and feeling that the result is accurate and reliable.",
                    },
                    {
                        "title": "Autonomy",
                        "body": "May value having ownership over tasks and enough freedom to decide how work should be approached.",
                    },
                    {
                        "title": "Making a difference",
                        "body": "May gain energy from seeing that their work contributes to something meaningful or useful.",
                    },
                ],
                "possible_demotivators": [
                    {
                        "title": "Unclear expectations",
                        "body": "May lose energy if goals, responsibilities or decision-making authority are vague for too long.",
                    },
                    {
                        "title": "Low-quality shortcuts",
                        "body": "May become frustrated if speed is consistently prioritised over accuracy or thoughtful delivery.",
                    },
                    {
                        "title": "Limited ownership",
                        "body": "May find it less engaging if there is little room to take responsibility or influence how work is done.",
                    },
                ],
                "best_environment": [
                    {
                        "title": "Clear goals",
                        "body": "An environment with clear priorities and expectations may help the candidate focus their energy effectively.",
                    },
                    {
                        "title": "Trust and ownership",
                        "body": "They may perform well when trusted to take responsibility and manage tasks with a degree of independence.",
                    },
                    {
                        "title": "Quality-focused culture",
                        "body": "A culture that values accuracy, improvement and thoughtful work may support engagement.",
                    },
                    {
                        "title": "Constructive feedback",
                        "body": "Regular feedback and clear dialogue may help maintain motivation and alignment.",
                    },
                ],
                "manager_tips": [
                    {
                        "title": "Clarify expectations early",
                        "body": "Be clear about what success looks like and which priorities matter most.",
                    },
                    {
                        "title": "Give ownership with boundaries",
                        "body": "Allow independence while agreeing on checkpoints, timelines and decision areas.",
                    },
                    {
                        "title": "Connect work to purpose",
                        "body": "Explain why tasks matter and how they contribute to wider goals or customer value.",
                    },
                    {
                        "title": "Avoid unnecessary ambiguity",
                        "body": "When things are changing, communicate what is known, what is uncertain and when decisions will be made.",
                    },
                ],
                "context_implications": (
                    "Without added process context, these insights should be read as general motivation themes. "
                    "If this report is used for a specific role, onboarding plan or development purpose, the motivation profile should be interpreted against that situation."
                ),
            },
            "work_style": {
                "summary": (
                    "The candidate appears likely to work best with clarity, structure and enough space to think things through. "
                    "Their profile may suggest a thoughtful and reliable working style, with a preference for quality and considered decisions."
                ),
                "items": [
                    {
                        "title": "How they work",
                        "subtitle": "Structure, pace and task approach",
                        "body": "The candidate may prefer clear expectations, organised work and time to understand the task before moving into action.",
                        "practical_tip": "Provide clear priorities and agree on what good delivery looks like early in the process.",
                        "evidence": ["Planning", "Reliability", "Quality Focus"],
                        "icon": "work",
                        "icon_class": "",
                    },
                    {
                        "title": "How they communicate",
                        "subtitle": "Information sharing and collaboration",
                        "body": "They may communicate most effectively when there is a clear purpose and enough context to form a considered view.",
                        "practical_tip": "Invite them to explain their reasoning and give space for questions, especially in complex discussions.",
                        "evidence": ["Communication", "Analytical Thinking"],
                        "icon": "communicate",
                        "icon_class": "is-blue",
                    },
                    {
                        "title": "How they handle change",
                        "subtitle": "Adaptability and shifting priorities",
                        "body": "They may adapt well when changes are explained clearly, but may need clarity around priorities if several things change at once.",
                        "practical_tip": "When priorities shift, clarify what has changed, what stays the same and what should be handled first.",
                        "evidence": ["Adaptability", "Decision-making"],
                        "icon": "change",
                        "icon_class": "is-green",
                    },
                    {
                        "title": "How they handle pressure",
                        "subtitle": "Pressure response and workload",
                        "body": "The candidate may perform best when pressure is paired with structure, realistic priorities and clear expectations.",
                        "practical_tip": "Use regular check-ins during intense periods to remove blockers and keep priorities visible.",
                        "evidence": ["Resilience", "Emotional Control"],
                        "icon": "pressure",
                        "icon_class": "is-orange",
                    },
                    {
                        "title": "How they prefer to be managed",
                        "subtitle": "Support, autonomy and feedback",
                        "body": "They may respond well to a management style that combines trust and autonomy with clear goals and constructive feedback.",
                        "practical_tip": "Give ownership, but agree on checkpoints and make expectations explicit.",
                        "evidence": ["Autonomy", "Quality", "Achievement"],
                        "icon": "managed",
                        "icon_class": "is-pink",
                    },
                ],
                "footer_note": (
                    "This section translates personality and work style indicators into practical behaviours. "
                    "Full trait-level results can be reviewed further down as evidence."
                ),
            },
            "next_steps": [
                {
                    "label": "Recommended action",
                    "title": "Use a structured follow-up conversation",
                    "body": "Use the insights as a starting point for a structured conversation rather than as a final conclusion.",
                    "focus": "Focus on examples from real work situations, especially where the candidate had to apply their strengths in practice.",
                },
                {
                    "label": "Validate through examples",
                    "title": "Explore the most relevant follow-up themes",
                    "body": "Ask targeted questions around the areas that would benefit from more context before making decisions or recommendations.",
                    "focus": "Prioritise stakeholder influence, pace under ambiguity and collaboration style.",
                },
                {
                    "label": "Connect insights to context",
                    "title": "Add process context for sharper recommendations",
                    "body": "If this report will be used for a specific role, team, onboarding plan or development purpose, add context to make the next steps more precise.",
                    "focus": "Add role, team, leadership or onboarding context to tailor the interpretation.",
                },
            ],

            "questions": [
                {
                    "category": "strengths",
                    "category_label": "Strengths",
                    "question": "Tell me about a situation where you used structure or analysis to solve a work-related problem.",
                    "why": "Helps validate how the candidate applies analytical and structured strengths in real situations.",
                    "listen_for": "Look for clear reasoning, practical action, follow-through and ability to explain the outcome.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Can you describe a time when you needed to influence someone who had a different opinion from you?",
                    "why": "Explores how the candidate gains buy-in and handles different perspectives.",
                    "listen_for": "Look for listening, clarity, adaptability, confidence and respect for other viewpoints.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Tell me about a situation where you had to make progress without having all the information you wanted.",
                    "why": "Helps understand how the candidate handles ambiguity and changing priorities.",
                    "listen_for": "Look for balance between careful thinking and practical action.",
                },
                {
                    "category": "motivation",
                    "category_label": "Motivation",
                    "question": "What type of work tends to give you the most energy, and what tends to drain your energy over time?",
                    "why": "Explores motivation fit and the conditions that may support sustained performance.",
                    "listen_for": "Look for alignment between the candidate’s drivers and the realities of the role or context.",
                },
                {
                    "category": "work_style",
                    "category_label": "Work style",
                    "question": "How do you prefer to receive goals, feedback and follow-up from a manager?",
                    "why": "Helps understand what management style may support the candidate’s performance.",
                    "listen_for": "Look for self-awareness, clarity around support needs and ability to work with expectations.",
                },
            ],

        }

    print(
        "AREAS TO EXPLORE:",
        candidate_insights.get("areas_to_explore"),
        flush=True,
    )


    return candidate_insights


