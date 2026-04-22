MOTIVATION_FACTORS = [
    {"key": "affiliation", "label": "Affiliation", "aliases": ["Affiliation"]},
    {"key": "customer_service", "label": "Customer Service", "aliases": ["Customer Service", "Service Focus"]},
    {"key": "work_life_balance", "label": "Work-life Balance", "aliases": ["Work-life Balance", "Finding the right balance"]},
    {"key": "people_development", "label": "People Development", "aliases": ["People Development", "Developing Others", "Coaching & Developing"]},
    {"key": "stability", "label": "Stability", "aliases": ["Stability"]},
    {"key": "authority", "label": "Authority", "aliases": ["Authority"]},
    {"key": "acquisition", "label": "Acquisition", "aliases": ["Acquisition"]},
    {"key": "autonomy", "label": "Autonomy", "aliases": ["Autonomy"]},
    {"key": "recognition", "label": "Recognition", "aliases": ["Recognition"]},
    {"key": "making_a_difference", "label": "Making a Difference", "aliases": ["Making a Difference"]},
    {"key": "achievement", "label": "Achievement", "aliases": ["Achievement"]},
    {"key": "quality", "label": "Quality", "aliases": ["Quality"]},
    {"key": "learning", "label": "Learning", "aliases": ["Learning"]},
    {"key": "ethics", "label": "Ethics", "aliases": ["Ethics"]},
    {"key": "commercial_value", "label": "Commercial Value", "aliases": ["Commercial Value"]},
    {"key": "curiosity", "label": "Curiosity", "aliases": ["Curiosity"]},
    {"key": "creativity", "label": "Creativity", "aliases": ["Creativity"]},
    {"key": "enjoyment", "label": "Enjoyment", "aliases": ["Enjoyment"]},
    {"key": "variety", "label": "Variety", "aliases": ["Variety"]},
    {"key": "risk", "label": "Risk", "aliases": ["Risk"]},
]

MOTIVATION_REPORTS = {
    "practitioner_report": {
        "title": "Practitioner Report",
        "intro": (
            "This report is based on the individual's responses to the Sova Motivation Questionnaire. "
            "It provides information about how their responses suggest they are motivated by all factors "
            "in the Sova Motivation Model, as well as what the implications may be of their highest and "
            "lowest motivators. The report also touches on the ideal environment for this individual to "
            "thrive in the workplace based on their motivation profile."
        ),
        "domain": "motivation",
        "sections": [
            "motivation_summary",
            "all_motivators",
            "implications",
            "ideal_environment",
        ],
        "items": MOTIVATION_FACTORS,
        "top_n": 3,
        "bottom_n": 3,
    },
    "manager_report": {
        "title": "Manager Report",
        "intro": (
            "This report is based on the individual's responses to the Sova Motivation Questionnaire. "
            "Based on their top three motivators at work, it offers practical guidance for line managers "
            "in order to motivate the individual most effectively. It offers tips on how to manage the "
            "individual to play to their core motivations and offers some indications of how these "
            "motivators could affect their relationships at work."
        ),
        "domain": "motivation",
        "sections": [
            "management_tips",
            "relationships_at_work",
        ],
        "items": MOTIVATION_FACTORS,
        "top_n": 3,
    },
    "candidate_report": {
        "title": "Candidate Report",
        "intro": (
            "This report shows which motivational factors are most likely to "
            "energise and engage this individual."
        ),
        "domain": "motivation",
        "items": [
            {
                "key": "affiliation",
                "label": "Affiliation",
                "aliases": ["Affiliation"],
            },
            {
                "key": "customer_service",
                "label": "Customer Service",
                "aliases": ["Customer Service", "Service Focus"],
            },
            {
                "key": "work_life_balance",
                "label": "Work-life Balance",
                "aliases": ["Work-life Balance", "Finding the right balance"],
            },
            {
                "key": "people_development",
                "label": "People Development",
                "aliases": ["People Development", "Developing Others", "Coaching & Developing"],
            },
        ],
    },
    "coaching_report": {
        "title": "Coaching Report",
        "intro": "...",
        "domain": "motivation",
        "sections": [
            "motivation_summary",
            "coaching_facilitation",
        ],
        "items": MOTIVATION_FACTORS,
        "top_n": 3,
    },
}

