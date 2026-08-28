from __future__ import annotations

from typing import Any


COMPETENCY_TOKEN_PREFIX = "competency::"


COMPETENCY_DOMAINS = {
    "interpersonal": {
        "label_en": "Interpersonal",
        "label_sv": "Interpersonellt",
    },
    "task": {
        "label_en": "Task",
        "label_sv": "Uppgift",
    },
    "mindset": {
        "label_en": "Mindset",
        "label_sv": "Mindset",
    },
}


# Canonical source: Sova Competency Model (38 competencies), as documented in
# the Competency Profile / Interview Guide supplied to Talena.
#
# `evidence_names` are deliberately NOT a scoring formula. They identify
# personality outputs that may provide useful supporting context when Talena
# creates behavioural interview questions about a competency. They must never
# be presented as a direct competency rating.
COMPETENCIES = [
    {
        "key": "teamwork",
        "domain": "interpersonal",
        "name": "Teamwork",
        "label_sv": "Teamarbete",
        "definition": (
            "Works collaboratively with team members to meet shared objectives, "
            "resolve potential challenges and promote a cooperative approach."
        ),
        "evidence_names": ["Teamwork", "Cooperative", "Agreeableness"],
    },
    {
        "key": "networking",
        "domain": "interpersonal",
        "name": "Networking",
        "label_sv": "Nätverkande",
        "definition": (
            "Develops a wide range of useful networks both inside and outside "
            "of the organisation."
        ),
        "evidence_names": [
            "Building Networks",
            "Building Strong Networks",
            "Connecting",
            "Initiating Contact",
        ],
    },
    {
        "key": "developing_relationships",
        "domain": "interpersonal",
        "name": "Developing Relationships",
        "label_sv": "Utveckla relationer",
        "definition": (
            "Develops and maintains positive relationships; relates well to a "
            "diverse range of people."
        ),
        "evidence_names": ["Connecting", "Warmth", "Open Communication"],
    },
    {
        "key": "developing_others",
        "domain": "interpersonal",
        "name": "Developing Others",
        "label_sv": "Utveckla andra",
        "definition": (
            "Motivates and supports others to develop themselves both personally "
            "and professionally."
        ),
        "evidence_names": ["Developing Others", "Coaching & Developing", "Supporting"],
    },
    {
        "key": "supporting_others",
        "domain": "interpersonal",
        "name": "Supporting Others",
        "label_sv": "Stödja andra",
        "definition": (
            "Supports others when faced with challenges and difficult situations. "
            "Helps those who are less able to help themselves."
        ),
        "evidence_names": ["Supporting", "Helpfulness", "Considerate", "Empathy"],
    },
    {
        "key": "influencing",
        "domain": "interpersonal",
        "name": "Influencing",
        "label_sv": "Påverkan",
        "definition": (
            "Influences others' actions and opinions, using convincing and "
            "persuasive arguments and strategies."
        ),
        "evidence_names": ["Influencing", "Influential", "Persuading", "Assertive"],
    },
    {
        "key": "directing_others",
        "domain": "interpersonal",
        "name": "Directing Others",
        "label_sv": "Leda andra",
        "definition": (
            "Provides clear direction and strong encouragement to ensure others "
            "are successful in achieving their goals and objectives."
        ),
        "evidence_names": ["Leading and Influencing", "Desire to Lead", "Influential"],
    },
    {
        "key": "delegating",
        "domain": "interpersonal",
        "name": "Delegating",
        "label_sv": "Delegera",
        "definition": (
            "Delegates work appropriately, taking account of skills, experience "
            "and availability; assigns others the right level of autonomy and authority."
        ),
        "evidence_names": ["Clarifies Expectations"],
    },
    {
        "key": "engaging_others",
        "domain": "interpersonal",
        "name": "Engaging Others",
        "label_sv": "Engagera andra",
        "definition": (
            "Displays enthusiasm and passion to inspire others are engaged with "
            "their work and the wider organisation."
        ),
        "evidence_names": ["Inspiring Others", "Enthusiastic", "Energetic"],
    },
    {
        "key": "managing_conflict",
        "domain": "interpersonal",
        "name": "Managing Conflict",
        "label_sv": "Hantera konflikter",
        "definition": (
            "Manages and resolves conflict and disagreement amongst others "
            "tactfully, yet openly."
        ),
        "evidence_names": ["Tolerance", "Agreeableness", "Calm"],
    },
    {
        "key": "interpersonal_communication",
        "domain": "interpersonal",
        "name": "Interpersonal Communication",
        "label_sv": "Mellanmänsklig kommunikation",
        "definition": (
            "Communicates effectively, engaging with others in a warm and "
            "professional manner."
        ),
        "evidence_names": ["Open Communication", "Effective Communication", "Listening"],
    },
    {
        "key": "written_communication",
        "domain": "interpersonal",
        "name": "Written Communication",
        "label_sv": "Skriftlig kommunikation",
        "definition": (
            "Writes clearly and concisely, in a manner which ensures the needs "
            "of each audience is met."
        ),
        "evidence_names": ["Effective Communication"],
    },
    {
        "key": "negotiating",
        "domain": "interpersonal",
        "name": "Negotiating",
        "label_sv": "Förhandla",
        "definition": (
            "Arrives at solutions which meet the needs of multiple parties "
            "through compromise and mutual understanding."
        ),
        "evidence_names": ["Persuading", "Influencing", "Tolerance"],
    },
    {
        "key": "customer_focus",
        "domain": "interpersonal",
        "name": "Customer Focus",
        "label_sv": "Kundfokus",
        "definition": (
            "Seeks to understand what customers need and works hard to ensure "
            "these needs are met."
        ),
        "evidence_names": ["Service Focus", "Listening"],
    },
    {
        "key": "planning",
        "domain": "task",
        "name": "Planning",
        "label_sv": "Planering",
        "definition": (
            "Plans work effectively to meet objectives; takes account of workload, "
            "resources and deadlines, and builds in appropriate contingency."
        ),
        "evidence_names": ["Planning and Organising", "Planning & Organising"],
    },
    {
        "key": "organising_and_prioritising",
        "domain": "task",
        "name": "Organising and Prioritising",
        "label_sv": "Organisera och prioritera",
        "definition": (
            "Organises resources and people to ensure delivery to quality and "
            "timescales. Prioritises work and tasks for optimum results."
        ),
        "evidence_names": ["Planning and Organising", "Attention to Detail", "Self-Discipline"],
    },
    {
        "key": "optimising_processes",
        "domain": "task",
        "name": "Optimising Processes",
        "label_sv": "Processoptimering",
        "definition": (
            "Uses the most efficient and effective processes to achieve objectives; "
            "looks for improvements that can be made in this regard."
        ),
        "evidence_names": ["Evaluating", "Analysing Problems"],
    },
    {
        "key": "quality_focus",
        "domain": "task",
        "name": "Quality Focus",
        "label_sv": "Kvalitetsfokus",
        "definition": (
            "Sets and maintains high quality standards; evaluates work at a detailed "
            "level and strives to get things right first time."
        ),
        "evidence_names": ["Attention to Detail", "Keeping Promises", "Meticulous"],
    },
    {
        "key": "analytical_thinking",
        "domain": "task",
        "name": "Analytical Thinking",
        "label_sv": "Analytiskt tänkande",
        "definition": (
            "Breaks down and understands complex information and data to draw "
            "appropriate insights; analyses and uses a wide range of data."
        ),
        "evidence_names": [
            "Analytical Thinking",
            "Analytical",
            "Analysing Problems",
            "Data Focus",
            "Evaluating",
        ],
    },
    {
        "key": "problem_solving",
        "domain": "task",
        "name": "Problem Solving",
        "label_sv": "Problemlösning",
        "definition": (
            "Identifies the root cause of problems; looks for effective and pragmatic "
            "solutions to address them."
        ),
        "evidence_names": ["Generates Solutions", "Analysing Problems", "Analytical"],
    },
    {
        "key": "strategic_focus",
        "domain": "task",
        "name": "Strategic Focus",
        "label_sv": "Strategiskt fokus",
        "definition": (
            "Demonstrates a strategic approach to their work; considers how different "
            "aspects of the organisation interact, the broader picture and the longer-term "
            "future of the business."
        ),
        "evidence_names": ["Strategic Focus", "Strategic Thinking", "Strategic Insight", "Complex Thinking"],
    },
    {
        "key": "driving_vision_and_purpose",
        "domain": "task",
        "name": "Driving Vision and Purpose",
        "label_sv": "Driva vision och syfte",
        "definition": (
            "Defines a clear vision for the future of the business or team; takes account "
            "of all relevant information and communicates a compelling vision."
        ),
        "evidence_names": ["Creates the Vision", "Strategic Insight", "Influential"],
    },
    {
        "key": "organisational_awareness",
        "domain": "task",
        "name": "Organisational Awareness",
        "label_sv": "Organisatorisk medvetenhet",
        "definition": (
            "Utilises a good understanding of how the business operates in terms of "
            "structure, people and politics to assess the impact on themselves, their "
            "team and the business."
        ),
        "evidence_names": ["Strategic Insight"],
    },
    {
        "key": "commercial_thinking",
        "domain": "task",
        "name": "Commercial Thinking",
        "label_sv": "Kommersiellt tänkande",
        "definition": (
            "Demonstrates commercial awareness including an understanding of key markets "
            "and competitors; looks for new opportunities for the business."
        ),
        "evidence_names": [],
    },
    {
        "key": "innovating",
        "domain": "task",
        "name": "Innovating",
        "label_sv": "Nyskapande",
        "definition": (
            "Puts forward new and innovative ideas, solutions and approaches; looks for "
            "ways to go beyond the conventional and traditional."
        ),
        "evidence_names": ["Innovating", "Innovation", "Creativity", "Generating Ideas", "Experimenting"],
    },
    {
        "key": "adaptability",
        "domain": "task",
        "name": "Adaptability",
        "label_sv": "Anpassningsförmåga",
        "definition": (
            "Adapts approach and responds effectively to different situations, people "
            "and new opportunities."
        ),
        "evidence_names": ["Adaptability", "Adapting to Change", "Flexible", "Flexibility", "Change Oriented"],
    },
    {
        "key": "embracing_diversity",
        "domain": "task",
        "name": "Embracing Diversity",
        "label_sv": "Omfamna mångfald",
        "definition": (
            "Demonstrates interest in understanding different perspectives and cultures; "
            "draws on the diversity of others to enhance the organisation."
        ),
        "evidence_names": ["Embraces Diversity", "Tolerance", "Flexibility"],
    },
    {
        "key": "decisiveness",
        "domain": "task",
        "name": "Decisiveness",
        "label_sv": "Beslutsamhet",
        "definition": (
            "Makes good decisions in a timely manner based on sound logic and reasoning; "
            "acts with conviction when a decision needs to be made, even with limited information."
        ),
        "evidence_names": ["Assertive", "Dynamic"],
    },
    {
        "key": "technical_knowledge_and_skill",
        "domain": "task",
        "name": "Technical Knowledge and Skill",
        "label_sv": "Teknisk kunskap och färdighet",
        "definition": (
            "Demonstrates strong technical knowledge and skills and applies them in their "
            "role; looks for opportunities to extend this knowledge where possible."
        ),
        "evidence_names": [],
    },
    {
        "key": "resilience",
        "domain": "mindset",
        "name": "Resilience",
        "label_sv": "Motståndskraft",
        "definition": (
            "Works well under pressure; bounces back quickly from setbacks in a positive "
            "and constructive manner."
        ),
        "evidence_names": ["Resilience", "Recovering", "Tough Minded", "Optimistic"],
    },
    {
        "key": "drive",
        "domain": "mindset",
        "name": "Drive",
        "label_sv": "Drivkraft",
        "definition": (
            "Highly motivated and driven; tackles challenging goals and situations with "
            "energy and enthusiasm."
        ),
        "evidence_names": ["Drive and Motivation", "Drive to Achieve", "Dynamic", "Energetic"],
    },
    {
        "key": "results_orientation",
        "domain": "mindset",
        "name": "Results Orientation",
        "label_sv": "Resultatorientering",
        "definition": (
            "Consistently strives to achieve results whatever the circumstances; attempts "
            "to exceed expectations with tenacity and determination."
        ),
        "evidence_names": ["Goal-focused", "Achievement-striving", "Drive to Achieve", "Competitive", "Challenge"],
    },
    {
        "key": "reliability",
        "domain": "mindset",
        "name": "Reliability",
        "label_sv": "Pålitlighet",
        "definition": (
            "Demonstrates a focus on delivering what is asked of them. Delivers on "
            "commitments and promises made to others."
        ),
        "evidence_names": ["Keeping Promises", "Self-Discipline", "Structured", "Conscientiousness"],
    },
    {
        "key": "integrity",
        "domain": "mindset",
        "name": "Integrity",
        "label_sv": "Integritet",
        "definition": (
            "Demonstrates high ethical standards and works in an authentic and honest "
            "manner. Responds to ethical conflicts with integrity."
        ),
        "evidence_names": ["Honesty", "Earnest", "Straightforward", "Adhering to Rules"],
    },
    {
        "key": "initiative",
        "domain": "mindset",
        "name": "Initiative",
        "label_sv": "Initiativtagande",
        "definition": (
            "Identifies and acts upon opportunities without needing direction or support "
            "from others. Takes a proactive approach."
        ),
        "evidence_names": ["Dynamic", "Initiating Contact", "Self-Reliant", "Independence"],
    },
    {
        "key": "self_awareness",
        "domain": "mindset",
        "name": "Self-Awareness",
        "label_sv": "Självmedvetenhet",
        "definition": (
            "Is sensitive to the feelings and reactions of others; is modest in their "
            "approach and aware of their impact on others."
        ),
        "evidence_names": ["Empathy", "Modesty", "Considerate", "Sensitivity"],
    },
    {
        "key": "dealing_with_ambiguity",
        "domain": "mindset",
        "name": "Dealing with Ambiguity",
        "label_sv": "Hantera otydlighet",
        "definition": (
            "Responds well to ambiguous situations; continues to be effective when faced "
            "with uncertainty or a lack of clarity."
        ),
        "evidence_names": ["Adaptability", "Flexibility", "Variety", "Coping with the chaos"],
    },
    {
        "key": "learning_focus",
        "domain": "mindset",
        "name": "Learning Focus",
        "label_sv": "Inlärningsfokus",
        "definition": (
            "Demonstrates a desire to grow and develop as a person and a professional. "
            "Actively seeks opportunities to extend their skills and capabilities."
        ),
        "evidence_names": ["Learning Mindset", "Curiosity", "Inquisitiveness"],
    },
]


_BY_NAME = {
    item["name"].casefold(): item
    for item in COMPETENCIES
}

_BY_KEY = {
    item["key"]: item
    for item in COMPETENCIES
}


def competency_token(name: str) -> str:
    item = get_competency(name)
    canonical_name = item["name"] if item else str(name or "").strip()
    return f"{COMPETENCY_TOKEN_PREFIX}{canonical_name}"


def parse_competency_token(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text.casefold().startswith(COMPETENCY_TOKEN_PREFIX):
        return None

    raw_name = text[len(COMPETENCY_TOKEN_PREFIX):].strip()
    item = get_competency(raw_name)
    return item["name"] if item else None


def get_competency(value: Any) -> dict[str, Any] | None:
    text = str(value or "").strip()
    if text.casefold().startswith(COMPETENCY_TOKEN_PREFIX):
        text = text[len(COMPETENCY_TOKEN_PREFIX):].strip()

    return _BY_NAME.get(text.casefold()) or _BY_KEY.get(text.casefold())


def normalise_competency_tokens(values: list[Any] | None, *, limit: int = 6) -> list[str]:
    result = []
    seen = set()

    for raw_value in values or []:
        name = parse_competency_token(raw_value)
        if not name:
            continue

        token = competency_token(name)
        token_key = token.casefold()
        if token_key in seen:
            continue

        seen.add(token_key)
        result.append(token)

        if len(result) >= limit:
            break

    return result


def competency_label(value: Any, language_code: str = "en") -> str:
    item = get_competency(value)
    if not item:
        return str(value or "").strip()

    if str(language_code or "").lower().startswith("sv"):
        return item["label_sv"]

    return item["name"]


def competency_groups(language_code: str = "en") -> list[dict[str, Any]]:
    use_sv = str(language_code or "").lower().startswith("sv")
    groups = []

    for domain_key in ("interpersonal", "task", "mindset"):
        domain = COMPETENCY_DOMAINS[domain_key]
        items = []

        for competency in COMPETENCIES:
            if competency["domain"] != domain_key:
                continue

            items.append({
                **competency,
                "token": competency_token(competency["name"]),
                "label": competency["label_sv"] if use_sv else competency["name"],
            })

        groups.append({
            "key": domain_key,
            "label": domain["label_sv"] if use_sv else domain["label_en"],
            "items": items,
        })

    return groups


def _normalise_evidence_name(value: Any) -> str:
    text = str(value or "").strip().casefold()
    for character in ("_", "-", "–", "—", "/"):
        text = text.replace(character, " ")
    return " ".join(text.split())


def build_supporting_personality_evidence(
    owner,
    selected_tokens: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """
    Return supporting personality signals for selected competencies.

    The rows remain evidence only. They are intentionally not aggregated into
    competency scores because Sova's flat personality activity can contain
    several report outputs with duplicate display names and no row-level report
    provenance.
    """

    activities = getattr(owner, "sova_activities", None) or []
    raw_rows = []

    for activity in activities:
        activity_name = str(activity.get("activity") or "").casefold()
        if "personality" not in activity_name and "personlighet" not in activity_name:
            continue

        for row in activity.get("competencies") or []:
            name = str(row.get("competency") or row.get("name") or "").strip()
            if not name:
                continue

            sten = row.get("sten_rounded")
            if sten is None:
                sten = row.get("sten")

            percentile = row.get("percentile")

            raw_rows.append({
                "name": name,
                "name_key": _normalise_evidence_name(name),
                "sten": sten,
                "percentile": percentile,
            })

    evidence_by_token: dict[str, list[dict[str, Any]]] = {}

    for token in normalise_competency_tokens(selected_tokens):
        competency = get_competency(token)
        if not competency:
            continue

        wanted_names = {
            _normalise_evidence_name(name)
            for name in competency.get("evidence_names") or []
        }

        matches = []
        seen = set()

        for row in raw_rows:
            if row["name_key"] not in wanted_names:
                continue

            identity = (
                row["name_key"],
                str(row.get("sten")),
                str(row.get("percentile")),
            )
            if identity in seen:
                continue

            seen.add(identity)
            matches.append({
                "name": row["name"],
                "sten": row.get("sten"),
                "percentile": row.get("percentile"),
            })

        evidence_by_token[token] = matches

    return evidence_by_token
