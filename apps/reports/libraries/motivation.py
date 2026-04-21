MOTIVATION_REPORTS = {
    "motivation_summary": {
        "title": "Motivation Summary",
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
    "practitioner_report": {
        "title": "Practitioner Report",
        "intro": (
            "This report provides a broader interpretation of the individual's "
            "motivation profile and likely workplace implications."
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
        "title": "TQ Motivation - Coaching Report",
        "intro": (
            "This report is based on the individual's responses to the Sova Motivation Questionnaire. "
            "It provides information about how their responses suggest they are motivated by all factors "
            "in the Sova Motivation Model, as well as guidance about how to run a coaching session with them."
        ),
        "domain": "motivation",
        "selection_mode": "top_n",
        "top_n": 3,
    },
}


MOTIVATION_COACHING_CONTENT = {
    "curiosity": {
        "label": "Curiosity",
        "aliases": ["Curiosity"],
        "bands": {
            "1_2": {
                "summary": "Less motivated by finding out new information and solving novel problems.",
                "upsides": [
                    "May prefer familiar tasks and established approaches.",
                    "Can stay grounded in practical realities rather than constantly exploring new ideas.",
                ],
                "downsides": [
                    "May be less energised by novelty, experimentation and open-ended discovery.",
                    "Could miss opportunities that require exploration and curiosity-driven thinking.",
                ],
                "questions": [
                    "What helps you engage with new ideas or unfamiliar topics?",
                    "How do you respond when a task requires exploration rather than clarity from the start?",
                ],
            },
            "7_8": {
                "summary": "Motivated by finding out new information and solving novel problems.",
                "upsides": [
                    "Highly inquisitive and will find genuine interest in a wide range of topics, activities and experiences.",
                    "Will likely enjoy being exposed to a wide range of people and perspectives.",
                ],
                "downsides": [
                    "May allow their curiosity and desire to explore the new to get in the way of getting things done.",
                    "May ask so many questions of others that their workplace relationships are undermined to some degree.",
                ],
                "questions": [
                    "What is it about new information and experiences that gives you so much enjoyment and satisfaction?",
                    "How do you ensure that you get meaningful, or the right, information and not just a large mass of meaningless or unimportant facts and figures?",
                    "How do you typically cope with limited exposure to new information and experiences?",
                ],
            },
        },
    },

    "quality": {
        "label": "Quality",
        "aliases": ["Quality"],
        "bands": {
            "7_8": {
                "summary": "Motivated by producing accurate, quality and timely work output.",
                "upsides": [
                    "Will consistently strive to do their best and deliver work that represents the highest standards possible.",
                    "Likely to derive considerable pride and satisfaction from producing work that looks professional.",
                ],
                "downsides": [
                    "May become disillusioned if they feel that they are part of an organisation that is not synonymous with high quality products and services.",
                    "May sometimes become so focused on quality and perfection that they lose sight of other priorities.",
                ],
                "questions": [
                    "Is it possible to spend too much time and effort on making sure that things are high quality and professional?",
                    "How can the drive for quality best be balanced with other priorities such as timelines, cost efficiency, productivity, etc?",
                    "How do you typically feel or react when not given sufficient opportunity to deliver the level of quality you'd like to?",
                ],
            },
        },
    },

    "stability": {
        "label": "Stability",
        "aliases": ["Stability"],
        "bands": {
            "7_8": {
                "summary": "Motivated by job security, organisational stability and consistency.",
                "upsides": [
                    "Will likely give their long-term loyalty and commitment in exchange for continued job security.",
                    "Will be highly motivated by discussions relating to their longer-term career aspirations and future job prospects within the organisation.",
                ],
                "downsides": [
                    "May be too dependent on having a high degree of clarity over what the future will hold.",
                    "May become quite anxious if they do not feel that their future in the organisation is secure.",
                ],
                "questions": [
                    "What does job security mean to you?",
                    "How realistic is it to expect the level of job-related certainty or consistency you would ideally like to have?",
                    "How do you typically react to situations where you feel you don't have the level of security you would like?",
                ],
            },
        },
    },

    "customer_service": {
        "label": "Customer Service",
        "aliases": ["Customer Service", "Service Focus"],
        "bands": {
            "1_2": {
                "summary": "Less motivated by customer facing environments, understanding needs and providing a good service.",
                "upsides": [
                    "May stay more detached and objective in situations where emotional customer expectations are high.",
                    "May prefer roles where value is created more indirectly rather than through direct service interaction.",
                ],
                "downsides": [
                    "May feel drained by highly customer-facing environments.",
                    "May be less naturally energised by spending time understanding individual customer needs in depth.",
                ],
                "questions": [
                    "How do you feel about roles that involve a lot of direct customer contact?",
                    "What kind of work gives you more energy than service-oriented tasks?",
                ],
            },
            "7_8": {
                "summary": "Motivated by customer facing environments, understanding needs and providing a good service.",
                "upsides": [
                    "Likely to enjoy understanding the needs of others and creating a positive customer experience.",
                    "May thrive in environments where service and responsiveness are important.",
                ],
                "downsides": [
                    "May become frustrated in environments where customer focus is low.",
                    "May overinvest time and energy in trying to satisfy others.",
                ],
                "questions": [
                    "What does excellent service mean to you?",
                    "How do you balance customer needs with business constraints?",
                ],
            },
        },
    },

    "affiliation": {
        "label": "Affiliation",
        "aliases": ["Affiliation"],
        "bands": {
            "7_8": {
                "summary": "Motivated by social interaction with others, having support and working in teams.",
                "upsides": [
                    "Likely to value connection, support and team belonging.",
                    "May thrive in environments with strong collaboration and social energy.",
                ],
                "downsides": [
                    "May feel less motivated in isolated or highly independent environments.",
                    "Could sometimes prioritise harmony or belonging over difficult but necessary conversations.",
                ],
                "questions": [
                    "What kinds of team environments bring out the best in you?",
                    "How important is day-to-day connection with others in your work?",
                ],
            },
        },
    },
}

MOTIVATION_TEXTS = {
    "motivation_summary": {
        "affiliation": {
            "1_2": "Less motivated by social interaction and teamwork.",
            "3_4": "Can appreciate collaboration, but it is not a strong driver.",
            "5_6": "Shows a moderate interest in collaboration and connection.",
            "7_8": "Motivated by social interaction, support and teamwork.",
            "9_10": "Highly energised by social interaction, support and collaborative environments.",
        },
        "customer_service": {
            "1_2": "Less motivated by customer-facing environments.",
            "3_4": "Can engage with customer needs, but it is not a strong source of energy.",
            "5_6": "Shows a moderate interest in customer-oriented work.",
            "7_8": "Motivated by understanding customer needs and providing good service.",
            "9_10": "Highly energised by customer-facing environments and delivering excellent service.",
        },
        "work_life_balance": {
            "1_2": "Less motivated by work-life balance as a key driver.",
            "3_4": "Can value balance, but it is not a primary source of motivation.",
            "5_6": "Shows a moderate preference for maintaining balance.",
            "7_8": "Motivated by being able to maintain a healthy work-life balance.",
            "9_10": "Highly motivated by environments that support sustainable balance and wellbeing.",
        },
        "people_development": {
            "1_2": "Less motivated by supporting or developing others.",
            "3_4": "Can contribute to development, but it is not a key source of energy.",
            "5_6": "Shows a moderate interest in helping others grow.",
            "7_8": "Motivated by helping, coaching and supporting the growth of others.",
            "9_10": "Highly energised by developing others and contributing to their success.",
        },
    },
    "practitioner_report": {
        "affiliation": {
            "1_2": "This individual may place less emphasis on close collaboration and group belonging.",
            "3_4": "This individual can work with others effectively, though social interaction may not be a major source of energy.",
            "5_6": "This individual is likely to show a balanced level of interest in collaboration and connection.",
            "7_8": "This individual is likely to value collaboration, support and regular interaction with others.",
            "9_10": "This individual is likely to be strongly energised by teamwork, belonging and frequent social connection.",
        },
        "customer_service": {
            "1_2": "This individual may be less energised by customer-facing work and service-oriented environments.",
            "3_4": "This individual can operate in service contexts, though they may not be especially driven by them.",
            "5_6": "This individual is likely to show a moderate level of interest in customer-oriented work.",
            "7_8": "This individual is likely to be motivated by understanding customer needs and delivering a strong service experience.",
            "9_10": "This individual is likely to thrive in environments where customer focus and service quality are central.",
        },
        "work_life_balance": {
            "1_2": "This individual may place less emphasis on work-life balance as a motivational factor.",
            "3_4": "This individual may value balance, though it is unlikely to be a strong driver of engagement.",
            "5_6": "This individual is likely to have a moderate preference for maintaining balance across work and life demands.",
            "7_8": "This individual is likely to value roles that allow for a healthy and sustainable work-life balance.",
            "9_10": "This individual is likely to be strongly motivated by balance, sustainability and overall wellbeing.",
        },
        "people_development": {
            "1_2": "This individual may be less motivated by coaching, mentoring or developing others.",
            "3_4": "This individual can support others when needed, though it may not be a major source of motivation.",
            "5_6": "This individual is likely to show a moderate interest in helping others grow and succeed.",
            "7_8": "This individual is likely to value opportunities to coach, support and develop others.",
            "9_10": "This individual is likely to be strongly energised by helping others grow and realise their potential.",
        },
    },
}