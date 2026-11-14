"""Issue #355: focused, versioned post-interview Overall picture generation.

The legacy content_blocks.overall_picture is deliberately retained for older reports.
One persisted item = one assessment area, factor, or selected personality theme.
No candidate identifiers, cross-tenant lookup, or unrelated assessment sources leave
this module. All model output is structured data, never trusted HTML.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy

from django.db import transaction
from django.utils import timezone

from .candidate_name_privacy import redact_candidate_name
from .language import normalize_ai_language
from .shared_context import build_shared_ai_context

SCHEMA_VERSION = 1
CATEGORIES = ("skills", "motivation", "personality", "synthesis")
PROMPT_KEYS = {
    "skills": "post_interview_overall_skills",
    "motivation": "post_interview_overall_motivation",
    "personality": "post_interview_overall_personality",
    "synthesis": "post_interview_overall_synthesis",
}
SKILL_TITLES = {
    "sv": {"numerical": "Numerisk", "logical": "Logisk", "verbal": "Verbal"},
    "en": {"numerical": "Numerical", "logical": "Logical", "verbal": "Verbal"},
}
MISSING_INTERVIEW = {
    "sv": "Området har inte utvecklats i det tillgängliga intervjuunderlaget.",
    "en": "This area was not addressed in the available interview evidence.",
}
COMMON_SV = """Skriv naturlig, varm, saklig och utförlig rapportprosa i sammanhängande
stycken, inte punktlistor. Utgå enbart från faktiska, angivna källor.
Testbild ska ENBART förklara testindikationer. Intervjun ska ENBART återge
vad som faktiskt framkommer i intervjuanteckningar och sparade svar.
Håll perspektiven strikt åtskilda. Intervjufrågor och anteckningar ska
tolkas tillsammans med den EXAKTA frågetexten; en intervjuaranteckning
är inte automatiskt ett ordagrant kandidatcitat. Vid avsaknad av
relevant intervjuunderlag, ange det kort, och hitta aldrig på exempel.
Undvik råpoäng, nivåetiketter, högt/lågt, prognoser, säkra egenskapspåståenden,
diagnoser, rollpassningsbedömningar och anställningsrekommendationer.
Skriv utvecklat när stöd finns, annars kortare. Upprepa inte rubriker i
fälttexten: Talena visar rubrikerna Testbild och Intervjun automatiskt."""
COMMON_EN = """Write natural, warm, precise and substantial prose in connected
paragraphs, not lists. Use only the supplied evidence.
Testbild must ONLY explain assessment indications; Intervjun must ONLY
describe actual interview accounts, notes and saved answers.
Never merge the two perspectives inside the fields. Keep each saved note
attached to the EXACT question. Interviewer notes are not automatically
verbatim candidate quotes. If topic-specific evidence is missing, state so
briefly; never invent stories. Avoid raw scores, high/low labels, predictions,
categorical personality claims, diagnoses, suitability and hiring verdicts.
Preserve detail where supported. Do not reproduce headings inside the fields:
Talena displays Testbild and Intervjun itself."""
PERSONALITY_THEME_VERSION = 2
GENERATION_RULES_VERSION = 6
PERSONALITY_THEMES = (
    {"sv": "Samarbete och relationer", "en": "Collaboration and relationships",
     "traits": ("Cooperative", "Connecting"),
     "scope": "samarbete kring en gemensam uppgift, arbetsrelationer och nya kontakter"},
    {"sv": "Hjälpsamhet och finnas där för andra", "en": "Helping and supporting others",
     "traits": ("Empathy", "Supporting"),
     "scope": "hur personen uppmärksammar andras behov och väljer om och hur stöd ges"},
    {"sv": "Påverka andra och komma framåt", "en": "Influencing others and moving work forward",
     "traits": ("Dynamic", "Influential"),
     "scope": "initiativ, ta ledning, leda eller koordinera arbete, driva en fråga vidare, skapa samsyn kring nästa steg och få med sig andra"},
    {"sv": "Planering och målfokus", "en": "Planning and goal focus",
     "traits": ("Goal-focused", "Structured"),
     "scope": "prioritering, planering, uppföljning och omplanering av arbete"},
    {"sv": "Analys och strategi", "en": "Analysis and strategy",
     "traits": ("Analytical", "Complex Thinking"),
     "scope": "hur personen sätter sig in i en komplex fråga och väger information eller alternativ"},
    {"sv": "Förändring och nytänkande", "en": "Change and new ideas",
     "traits": ("Creativity", "Adaptability"),
     "scope": "att pröva nya lösningar och ställa om när förutsättningar ändras"},
    {"sv": "Kommunikationsstil och principfasthet", "en": "Communication style and principles",
     "traits": ("Straightforward",),
     "scope": "att uttrycka en ståndpunkt, hantera olika förväntningar eller resonera om regler"},
    {"sv": "Att synas eller smälta in", "en": "Taking the spotlight or blending in",
     "traits": ("Status Avoidance", "Modesty"),
     "scope": "att ta plats, synliggöra egen insats och ge andra erkännande"},
    {"sv": "Stress och press", "en": "Stress and pressure",
     "traits": ("Resilience", "Emotional Control"),
     "scope": "reaktioner vid hög belastning, motgångar eller oväntade problem"},
    {"sv": "Självständigt arbete och förankring", "en": "Independent work and alignment",
     "traits": ("Independence",),
     "scope": "vad personen driver eller beslutar själv och när hen stämmer av eller söker stöd"},
)

PROMPT_DEFAULTS = {
    "skills": {
        "sv": """För det angivna ENDA färdighetsområdet, skriv ett utvecklat
stycke Testbild: beskriv begripligt och vardagsnära hur kandidaten kan
ta sig an den här sortens information eller problem, vad som kan komma
naturligt och vad som kan behöva tid, energi eller strategi. Reducera
inte resultatet till en nivåetikett. Intervjun: beskriv konkret vilka
uppgifter/situationer kandidaten faktiskt berättat om, hur hen började,
resonerade, agerade och vad som hände, om detta finns i underlaget.
Kort inte ned rika exempel till en enda egenskap och skriv inte bort
testresultatet med kandidatens strategier. Behåll djup och nyanser.""",
        "en": """For this ONE available skill, explain in Testbild how the
result may relate to handling this type of information, in accessible
day-to-day language, including what may be natural or need strategies.
In Intervjun describe the candidate's actual tasks, situations,
approach, reasoning and examples with detail if supported. Do not turn
a rich example into a generic trait or explain away the test result.""",
    },
    "motivation": {
        "sv": """För EN av kandidatens faktiska tre högst rankade
motivationsfaktorer: beskriv i Testbild på ett naturligt och nyanserat
sätt vad den godkända drivkraften betyder och hur den kan ge energi,
utan att förutsätta samma innebörd för alla. I Intervjun: vad
kandidaten faktiskt säger om engagemang, situationer, värderingar
och när drivkraften får eller inte får utrymme. Ge egna exempel
och resonemang plats; skriv inte en tolkning i kandidatens ställe.
Dra ingen rollslutsats och blanda inte in andra faktorer.""",
        "en": """For ONE of the candidate's actual top-three motivators,
describe its approved meaning and possible energy sources in Testbild
without universal assumptions. In Intervjun, detail what the candidate
actually describes about engagement, values, examples or constraints
when grounded in the notes. Do not substitute a personal explanation
for a missing candidate account, mix factors or give role verdicts.""",
    },
    "personality": {
        "sv": """Skriv utförlig text för EN beskrivande, rollrelevant
temarubrik (inte ett ensamt testdrag). I Testbild: väv ihop de
ANGIVNA och relevanta kandidatunika indikatortolkningarna; samspelet
kan nyansera vad som kommer naturligt respektive är situationsbundet.
Rada inte upp drag, slå inte fast egenskaper eller kompetenser och
dra inte slutsatser om vad personen bidrar med i rollen.
I Intervjun: återge kandidatens faktiska situationer, uppgifter,
människor, avvägningar, agerande och resultat när dessa har
beskrivits. Ge berättelsen ordentligt utrymme, inklusive möjliga
spänningar, utan att jämföra med testresultatet i denna del.
Finns inget relevant intervjusvar: ange det kort.""",
        "en": """Write substantial prose for ONE descriptive, role-relevant
theme, not a mere trait name. In Testbild, combine only the supplied
candidate-specific trait and indicator interpretations with nuance,
without concluding competence or suitability. In Intervjun, recount
actual situations, people, choices, reasoning and outcomes when given;
preserve the account's depth and tensions, without comparing it to
the test in this field. Briefly state missing topic-specific evidence.""",
    },
    "synthesis": {
        "sv": """Skriv en avslutande, sammanhängande Helhetsbild i ett eller
två utvecklade stycken utifrån de lyckade, separata delarna.
Väg samman testindikationer, kandidatens egna uppgifter, drivkrafter
och kontext. Synliggör osäkerheter och spänningar med tydlig
källskillnad. Ha en röd tråd, repetera inte varje avsnitt och
tillför ALDRIG nya fakta, intervjuexempel, lämplighets- eller
anställningsbedömningar. Avsluta utan intervjufrågor eller
rekommendationer om ytterligare intervju.""",
        "en": """Write one or two substantial final synthesis paragraphs
based ONLY on the successful, version-consistent prior sections.
Bring together assessment indications and the candidate's accounts
while identifying meaningful tensions and uncertainty. Keep provenance
clear, avoid repeating every section, and add NO new facts, examples,
suitability verdicts, hiring decisions or interview questions.""",
    },
}
PROMPT_REGISTRY_ADDITIONS = {
    PROMPT_KEYS[category]: {
        "name": {
            "skills": "Helhetsbild – Färdighet",
            "motivation": "Helhetsbild – Motivation",
            "personality": "Helhetsbild – Personlighet",
            "synthesis": "Helhetsbild – Sammanfattande helhetsbild",
        }[category],
        "category": "Efter intervju · Helhetsbild",
        "description": "Ticket #355: individually configurable, focused structured report section",
        "defaults": {
            language: (COMMON_SV if language == "sv" else COMMON_EN)
            + "\n\n" + text
            for language, text in languages.items()
        },
    }
    for category, languages in PROMPT_DEFAULTS.items()
}


def _guidance(category, language):
    from .prompt_templates import get_ai_feature_prompt_instructions, get_global_ai_guidance
    return (
        get_global_ai_guidance(language=language),
        get_ai_feature_prompt_instructions(key=PROMPT_KEYS[category], language=language),
    )


def _personality_theme_guidance(guidance, title):
    """Pass only the selected theme's editable guidance to its generation call."""
    text = str(guidance or "")
    feature_marker = "FEATURE-SPECIFIC ADMINISTRATOR AI GUIDANCE"
    marker_index = text.find(feature_marker)
    if marker_index >= 0:
        text = text[marker_index + len(feature_marker):]
    headings = list(re.finditer(r"(?m)^(#{1,5})[ \t]+(.+?)\s*$", text))
    target = str(title or "").strip().casefold()
    for index, match in enumerate(headings):
        if len(match.group(1)) != 4 or match.group(2).strip().casefold() != target:
            continue
        end = len(text)
        for following in headings[index + 1:]:
            if len(following.group(1)) <= 4:
                end = following.start()
                break
        return text[match.start():end].strip()
    # Fail closed: never expose another theme's examples when a custom heading
    # cannot be matched. The fixed theme scope and protected rules still apply.
    return ""


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _state(owner):
    stored = (owner.ai_post_interview_decision_support or {}).get("overall_picture_structured")
    if not isinstance(stored, dict) or stored.get("schema") != SCHEMA_VERSION:
        return {"schema": SCHEMA_VERSION, "sections": {}, "language": ""}
    return deepcopy(stored)


def _save(owner, result):
    """Never overwrite another After interview content block."""
    with transaction.atomic():
        locked = type(owner).objects.select_for_update().get(pk=owner.pk)
        document = dict(locked.ai_post_interview_decision_support or {})
        document["overall_picture_structured"] = result
        locked.ai_post_interview_decision_support = document
        locked.save(update_fields=["ai_post_interview_decision_support"])


def _subject_evidence(owner, category, language, shared, notes):
    # Lazy imports prevent the admin prompt registry from importing AI generators
    # while the registry itself is still being initialized.
    from .cognitive_interpretation import extract_cognitive_results
    from apps.reports.libraries.cognitive.builder import build_cognitive_report
    from .motivation_interpretation import (
        extract_motivation_results, get_motivation_factor_display_name,
    )
    from .personality_ai_evidence import build_owner_personality_ai_evidence
    if category == "skills":
        found = {row["key"]: row for row in extract_cognitive_results(owner)}
        order = ("numerical", "logical", "verbal")
        units = []
        for key in order:
            if key not in found:
                continue
            percentile = found[key]["percentile"]
            approved = build_cognitive_report(
                test_key=key, audience="practitioner", percentile=percentile,
            )
            units.append({
                "key": key, "title": SKILL_TITLES[language][key],
                "evidence": {
                    # Percentile is used locally to select approved copy,
                    # not sent as raw numeric evidence to OpenAI (#358).
                    "test": key,
                    "approved_test_description": approved.get("test_description") or "",
                    "approved_result_interpretation": approved.get("result_text") or "",
                },
            })
        return units
    if category == "motivation":
        scores = sorted(
            extract_motivation_results(owner),
            key=lambda row: (-row["score"], row["name"].casefold()),
        )
        entries = []
        for index, row in enumerate(scores[:3]):
            label = get_motivation_factor_display_name(row["name"], language_code=language)
            # Never show provider identifiers as a visible heading.
            if re.search(r"\d{4}_MQ_|Sova_Motivation_", label, re.I):
                label = re.sub(r"^.*?Motivation_", "", label, flags=re.I).replace("_", " ").strip() or "Motivation"
            entries.append({
                "key": "factor_" + str(index + 1),
                "title": label,
                # Precise score only determines the top-three ordering locally.
                "evidence": {"definition": row.get("definition") or "", "name": label},
            })
        return entries
    if category == "personality":
        rows = build_owner_personality_ai_evidence(owner, language_code=language)
        return [{
            "key": str(row.get("name") or "").strip(),
            "title": str(row.get("label") or row.get("name") or "").strip(),
            "evidence": {"summary": row.get("summary") or "", "indicators": [
                {"name": x.get("label") or x.get("name"), "text": x.get("text")}
                for x in (row.get("indicators") or [])
            ]},
        } for row in rows if row.get("name")]
    return []


def _notes_for_category(notes, category):
    source = {"skills": "cognitive", "motivation": "motivation", "personality": "personality"}[category]
    items = [
        {"question": item.get("question") or "", "saved_answer_or_note": item.get("saved_answer_or_note") or ""}
        for item in notes["question_evidence"].get("items") or []
        if item.get("source") == source
    ]
    # General interview notes can be relevant to multiple areas; preserve them
    # with explicit relevance filtering in the protected prompt.
    return {"general_notes": notes["general_notes"], "question_evidence": items}


def _completion(prompt, owner, *, output_tokens=1800):
    """One non-streaming, schema-constrained call for exactly one unit."""
    from .openai_client import get_chat_model, get_openai_client
    safe = redact_candidate_name(prompt, owner.candidate)
    client = get_openai_client()
    response = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {"role": "system", "content": "You are Talena's evidence-grounded assessment writer. Return ONLY valid JSON. Protected evidence rules take precedence over editable guidance."},
            {"role": "user", "content": safe},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_completion_tokens=output_tokens,
    )
    choice = response.choices[0]
    if getattr(choice, "finish_reason", "") == "length":
        raise ValueError("AI content exceeded the response limit.")
    content = choice.message.content
    if isinstance(content, list):
        content = "".join(str(getattr(part, "text", "")) for part in content)
    parsed = json.loads(content or "{}")
    if not isinstance(parsed, dict):
        raise ValueError("AI returned invalid section data.")
    return parsed



# A JSON-mode completion only guarantees the *outer* response is JSON.
# The model may still put an entire source dictionary inside "testbild" or
# "intervjun". Never turn such values into publishable prose with str(dict).
_RAW_SOURCE_KEYS = (
    "definition", "name", "summary", "traits", "indicators", "general_notes",
    "question_evidence", "saved_answer_or_note", "testbild", "intervjun",
)
_RAW_SOURCE_KEY_PATTERN = re.compile(
    r"""['"](?:definition|general_notes|question_evidence|saved_answer_or_note|traits|indicators|summary)['"]\s*:""",
    flags=re.I,
)


def is_raw_source_dump(value):
    """Recognise model echoes of JSON/Python evidence mappings, not prose."""
    if not isinstance(value, str):
        return isinstance(value, (dict, list, tuple))
    stripped = value.strip()
    if not stripped:
        return False
    # Python repr ({'definition': ...}), JSON ({"traits": ...}), arrays,
    # including input containing escaped newline sequences.
    if re.match(r"""^[\[{]\s*['"]""", stripped):
        return True
    if re.match(r"^[\[{]\s*[a-zA-Z_][\w]*\s*:", stripped):
        return True
    return bool(_RAW_SOURCE_KEY_PATTERN.search(stripped[:400]))


def _validated_prose(value, *, field, allow_empty=False):
    """Only genuine plain text can become a completed report item."""
    if value is None or value == "":
        if allow_empty:
            return ""
        raise ValueError(f"Model returned empty {field}.")
    if not isinstance(value, str):
        raise ValueError(f"Model returned a non-text {field}.")
    prose = value.strip()
    if not prose:
        if allow_empty:
            return ""
        raise ValueError(f"Model returned empty {field}.")
    if is_raw_source_dump(prose):
        raise ValueError(f"Model echoed raw source data in {field}.")
    return prose


_REPAIR_INSTRUCTION = (
    "\n\nIMPORTANT REPAIR: The earlier attempt returned structured source data, "
    "a nested dictionary, or an empty field rather than report prose. Write "
    "fresh, natural prose grounded in the sources ABOVE. JSON keys such as "
    "definition, general_notes, traits, indicators, question_evidence, or "
    "saved_answer_or_note must NEVER appear as values in the output. "
    "Use a JSON object with STRING values only; do not nest dictionaries, "
    "echo input JSON, or simply reproduce the source notes. Keep Testbild "
    "and Intervjun separate and preserve their evidential boundaries."
)


def _generate_validated_item(owner, prompt, *, language):
    """Repair a malformed answer once, then report failure without storing it."""
    for attempt in range(2):
        output = _completion(prompt + (_REPAIR_INSTRUCTION if attempt else ""), owner)
        try:
            testbild = _validated_prose(output.get("testbild"), field="Testbild")
            intervjun = _validated_prose(
                output.get("intervjun"), field="Intervjun", allow_empty=True,
            )
            return testbild, intervjun or MISSING_INTERVIEW[language]
        except ValueError:
            if attempt:
                raise


def _strip_synthesis_headings(value):
    """Remove report headings already rendered by the Talena interface."""
    lines = str(value or "").splitlines()
    kept = [
        line for line in lines
        if not re.match(r"^\\s*#{1,6}\\s*(?:Helhetsbild|Overall picture)\\s*#*\\s*$", line, re.I)
    ]
    return "\\n".join(kept).strip()


def _validate_synthesis_provenance(value):
    """Reject a few explicit synthesis overreaches seen in generated reports."""
    text = str(value or "")
    prohibited = (
        r"\\b(?:bekräftar|bekräftade|confirms?|corroborates?)\\b.{0,100}\\b(?:testresultat(?:et)?|testresultaten|test result|assessment result)\\b",
        r"\\b(?:behöver|bör|kan behöva|need(?:s)? to|should)\\b.{0,70}\\b(?:utforskas vidare|utforska vidare|explore further|be explored further)\\b",
        r"\\b(?:potential(?:en)? att bidra|potential to contribute|kan bidra positivt|could contribute positively|god grund att bidra)\\b",
    )
    if any(re.search(pattern, text, re.I | re.S) for pattern in prohibited):
        raise ValueError("Synthesis contains an unsupported cross-source or role inference.")


_SYNTHESIS_REPAIR_INSTRUCTION = (
    "\\n\\nREPAIR THE SYNTHESIS: The previous text added an unsupported conclusion. "
    "Use only statements already present in the supplied sections. Never say the interview "
    "confirms a test result, recommend exploring an area further, or describe the candidate's "
    "potential contribution or value to a role. Do not add a Markdown heading; the interface "
    "renders the heading. Return only the requested JSON text field."
)


def _generate_validated_synthesis(owner, prompt):
    last_error = None
    for attempt in range(2):
        repair = _SYNTHESIS_REPAIR_INSTRUCTION if attempt else ""
        output = _completion(prompt + repair, owner, output_tokens=1600)
        try:
            prose = _strip_synthesis_headings(output.get("text"))
            prose = _validated_prose(prose, field="final synthesis")
            _validate_synthesis_provenance(prose)
            return prose
        except ValueError as exc:
            last_error = exc
            if attempt:
                raise
    if last_error:
        raise last_error


def _theme_selection(owner, shared, rows, notes, language):
    """Use the ten approved themes; never ask a model to redefine report structure."""
    return [
        {
            "key": "theme_" + str(index),
            "title": definition.get(language, definition["sv"]),
            "traits": list(definition["traits"]),
            "scope": definition["scope"],
        }
        for index, definition in enumerate(PERSONALITY_THEMES, start=1)
    ]


def _assign_personality_interview_evidence(owner, themes, notes, language):
    """Assign each interview record only to a clearly relevant personality theme."""
    question_items = list(notes.get("question_evidence", {}).get("items") or [])
    records = []
    if notes.get("general_notes"):
        records.append({"source": "general", "index": 0, "text": str(notes["general_notes"])})
    for index, item in enumerate(question_items):
        if item.get("source") == "personality":
            records.append({
                "source": "question",
                "index": index,
                "question": str(item.get("question") or ""),
                "text": str(item.get("saved_answer_or_note") or ""),
            })
    assigned = {
        theme["key"]: {"general_notes": "", "question_evidence": []}
        for theme in themes
    }
    if not records or not themes:
        return assigned

    theme_scope = [
        {"key": theme["key"], "title": theme["title"], "scope": theme["scope"]}
        for theme in themes
    ]
    prompt = "\n\n".join([
        "Classify interview records for the ten fixed personality themes.",
        "Return JSON only: {\"assignments\":[{\"source\":\"general|question\",\"index\":integer,\"theme\":theme_key}]}",
        "Assign a record to the single best-matching theme based first on the exact interview question, even if the answer says the person has no practical experience. A question about leading, coordinating, or ensuring all parts of a task are completed is relevant to the matching theme even when the answer describes only theoretical knowledge or tracking software. Use the answer only for facts it explicitly states; never treat the question or its examples as the person's actions. Be conservative; leave unrelated records unassigned. For personality, general notes must explicitly describe work behaviour, choices, preferences, collaboration or reactions. Exclude self-reported skill levels, test performance, qualifications and task errors from personality evidence, including numerical-data difficulties. Do not infer relevance from the role or assessment. Assign each record to at most one theme. Do not create, rewrite, or summarize evidence.",
        "Language: " + language,
        "Themes: " + json.dumps(theme_scope, ensure_ascii=False),
        "Interview records: " + json.dumps(records, ensure_ascii=False),
    ])
    try:
        parsed = _completion(prompt, owner, output_tokens=900)
    except Exception:
        return assigned
    theme_aliases = {}
    for theme in themes:
        theme_aliases[theme["key"]] = theme["key"]
        theme_aliases[str(theme["title"]).casefold()] = theme["key"]
    used = set()
    for item in parsed.get("assignments") or []:
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        if source in ("question-specific", "question_evidence"):
            source = "question"
        index = item.get("index")
        if isinstance(index, str) and index.isdigit():
            index = int(index)
        theme_value = item.get("theme") or item.get("theme_key") or item.get("theme_title")
        theme_key = theme_aliases.get(str(theme_value).strip().casefold())
        if source not in ("general", "question") or not isinstance(index, int):
            continue
        identity = (source, index)
        if identity in used or theme_key not in assigned:
            continue
        record = next((row for row in records if row["source"] == source and row["index"] == index), None)
        if not record:
            continue
        used.add(identity)
        if source == "general":
            assigned[theme_key]["general_notes"] = record["text"]
        else:
            original = question_items[index]
            assigned[theme_key]["question_evidence"].append({
                "question": original.get("question") or "",
                "saved_answer_or_note": original.get("saved_answer_or_note") or "",
            })
    return assigned


def _item_prompt(owner, category, item, shared, notes, language):
    global_rules, guidance = _guidance(category, language)
    if category == "personality":
        guidance = _personality_theme_guidance(guidance, item["title"])
    final_boundary = (
        "FINAL EVIDENCE FIREWALL: The assessment and interview blocks are the only facts about this person. "
        "Exact question text and examples in any guidance are prompts about possible topics, never evidence "
        "that the person did or said those things. Never convert them into candidate facts. Do not invent or "
        "infer actions, frequency, outcomes, intentions, abilities, competence, motivation or interests. "
        "If the saved answer says the person has not done an activity, state that directly; do not replace it "
        "with hypothetical positive behaviour. Do not infer willingness, leadership or motivation from "
        "theoretical knowledge or software use. Use 'personen' rather than gendered pronouns."
    )
    if category == "skills":
        final_boundary += (
            " Testbild: maximum three sentences, based only on the result for this test and what that result "
            "may indicate about handling this type of task in the test situation. Do not say the person "
            "'has difficulty', infer time, effort or strategy, or make a general ability or job-performance "
            "claim based only on a score. Intervjun: attribute self-reported difficulty to the interview; "
            "do not infer lack of ability from one event."
        )
    elif category == "personality":
        trait_names = [
            str(trait.get("name") or trait.get("title") or "").strip()
            for trait in (item.get("evidence") or {}).get("traits") or []
            if isinstance(trait, dict)
        ]
        final_boundary += (
            " Testbild: maximum three sentences, based only on this theme's supplied trait evidence. "
            "This theme contains these available traits: " + ", ".join(trait_names) + ". "
            "When two traits are available, include a distinct supported nuance from each; do not let "
            "one trait replace the other. Do not describe a test result as competence or predict work "
            "performance; situational results must remain situational. Intervjun: use only the interview "
            "records selected for this theme, and do not infer willingness or leadership from theoretical "
            "knowledge or use of software."
        )
    elif category == "motivation":
        final_boundary += (
            " Testbild: maximum three sentences and only the current factor. Intervjun: describe only "
            "explicitly stated motives, values or sources of energy, not inferred behavior."
        )
    return "\n\n".join([
        "OUTPUT: JSON object with EXACTLY two string fields, testbild and intervjun. "
        "Each field must contain natural, newly written Swedish or English report prose, "
        "NEVER a dictionary, array, JSON literal, Python object representation, "
        "source note dump, or unedited assessment definition. Use the input only as evidence; "
        "do not quote its technical field names (definition, general_notes, traits, "
        "question_evidence, indicators). No Markdown headings. Write in language: " + language,
        "CANDIDATE: CANDIDATE_A",
        "AREA: " + str(item["title"]),
        "PURPOSE: " + str(shared.get("purpose_label") or ""),
        "ASSESSMENT FOR THIS AREA ONLY:\n" + json.dumps(item["evidence"], ensure_ascii=False),
        "INTERVIEW NOTES (only cite material explicitly relevant to this area):\n" +
        json.dumps(notes, ensure_ascii=False),
        "THEME SCOPE: " + str(item.get("scope") or ""),
        "PROTECTED EVIDENCE RULES: Testbild must use ONLY the assessment evidence for this item; "
        "Intervjun must use ONLY the interview records supplied for this exact theme. "
        "Do not use one field's evidence in the other field. Never turn a question into an answer, "
        "add actions, intentions, frequency, outcomes, skills or examples absent from the saved text, "
        "or infer a stable pattern from one account. If selected interview evidence is empty or "
        "does not address this theme, say so briefly. If test evidence is empty, say so briefly. "
        "No other assessment sources, raw scores in prose, predictions, or suitability decisions. "
        "Keep exact question/answer provenance; an interviewer note is not a verbatim quote. "
        "Do not emit personal identifiers.",
        "GLOBAL AI GUIDANCE:\n" + global_rules,
        "SCOPED ADMIN PROMPT:\n" + guidance,
        final_boundary,
    ])

def _synthesis_prompt(owner, sections, shared, language):
    global_rules, guidance = _guidance("synthesis", language)
    available = {
        key: [{"title": item["title"], "testbild": item["testbild"], "intervjun": item["intervjun"]}
              for item in (sections.get(key) or {}).get("items") or [] if item.get("status") == "completed"]
        for key in ("skills", "motivation", "personality")
    }
    return "\n\n".join([
        "Write ONLY the final cross-section synthesis in language " + language,
        "Respond as JSON object with a single key text (one or two substantial paragraphs).",
        "CANDIDATE: CANDIDATE_A",
        "PREVIOUSLY GENERATED, SOURCE-BOUNDED SECTIONS: " + json.dumps(available, ensure_ascii=False),
        "Protected: do not introduce new information, interview anecdotes, suitability "
        "judgments or hiring verdicts; keep test indications and candidate accounts distinct.",
        "GLOBAL GUIDANCE: " + global_rules,
        "SCOPED ADMIN GUIDANCE: " + guidance,
        "FINAL SYNTHESIS EVIDENCE FIREWALL: Treat each Testbild and Intervjun field as a separate source; "
        "a field saying no interview evidence is available must never be transformed into an interview claim. "
        "Compress only facts explicitly present in these fields. Do not state that interview evidence confirms "
        "or proves a test result; describe each source separately, even when they point in a similar direction. "
        "Do not label traits as strengths or development areas unless a supplied source explicitly does so. "
        "Do not add personal interest, motivation, skill, behavior or experience from the role description or "
        "application. Do not describe potential contribution, value or suitability for a role. Do not turn a test "
        "indication into a claim about work performance. Do not suggest support, management actions, further "
        "exploration, next steps or recommendations. Preserve uncertainty and distinguish assessment indications "
        "from interview accounts. Output prose only, without a Markdown heading; the interface renders the heading.",
    ])


def _legacy_markdown(state):
    titles = {"sv": ("Färdighet", "Motivation", "Personlighet", "Helhetsbild"),
              "en": ("Skills", "Motivation", "Personality", "Overall picture")}
    lang = state.get("language") if state.get("language") in ("sv", "en") else "sv"
    result = []
    for category, title in zip(CATEGORIES, titles[lang]):
        section = (state.get("sections") or {}).get(category) or {}
        if category == "synthesis":
            if section.get("status") == "completed" and section.get("text"):
                result.append("## " + title + "\n\n" + section["text"])
            continue
        items = section.get("items") or []
        if not items:
            continue
        result.append("## " + title)
        for item in items:
            if item.get("status") == "completed":
                result.append("### " + item["title"] + "\n\n#### Testbild\n\n" +
                              item["testbild"] + "\n\n#### Intervjun\n\n" + item["intervjun"])
    return "\n\n".join(result)


def generate_structured_overall_picture(owner, *, language_code="sv", category=None, force=False):
    """Yield progress events; save each successful item atomically.

    A failed unit never erases previous successful content. Regenerating any
    source invalidates the synthesis until it is rebuilt from the new versions.
    """
    language = normalize_ai_language(language_code)
    if category is not None and category not in CATEGORIES:
        raise ValueError("Unknown Overall picture section.")
    from .post_interview_question_evidence_policy import get_post_interview_note_evidence
    shared = build_shared_ai_context(owner)
    notes = get_post_interview_note_evidence(owner)
    if not notes["has_evidence"]:
        raise ValueError("Interview notes or saved answers are required.")

    state = _state(owner)
    if state.get("language") and state["language"] != language:
        for section in state["sections"].values():
            if section.get("status") == "completed":
                section["status"] = "outdated"
    state["language"] = language
    targets = [category] if category else list(CATEGORIES)
    for part in targets:
        state = _state(owner) if not state["sections"] else state
        sections = state["sections"]
        old = sections.get(part) or {}
        if part == "synthesis":
            sources = [sections.get(k) or {} for k in CATEGORIES[:3]]
            if not any(sec.get("items") for sec in sources):
                yield {"type": "structured_section_skipped", "section": part}
                continue
            if any(sec.get("status") not in ("completed", "not_applicable") for sec in sources):
                yield {"type": "structured_section_error", "section": part, "message": "Regenerate outdated/failed source sections before final synthesis."}
                continue
            fingerprint = _hash({
                "generation_rules_version": GENERATION_RULES_VERSION,
                "sources": sources, "language": language, "guidance": _guidance(part, language),
            })
            if not force and old.get("status") == "completed" and old.get("fingerprint") == fingerprint:
                yield {"type": "structured_section_skipped", "section": part}
                continue
            try:
                text = _generate_validated_synthesis(
                    owner, _synthesis_prompt(owner, sections, shared, language),
                )
                sections[part] = {"status": "completed", "text": text, "fingerprint": fingerprint,
                                  "generated_at": timezone.now().isoformat()}
                _save(owner, state)
                yield {"type": "structured_section_complete", "section": part}
            except Exception:
                sections[part] = {**old, "status": "failed"}
                _save(owner, state)
                yield {"type": "structured_section_error", "section": part, "message": "Could not generate final synthesis."}
            continue

        rows = _subject_evidence(owner, part, language, shared, notes)
        if not rows:
            sections[part] = {"status": "not_applicable", "items": []}
            _save(owner, state)
            yield {"type": "structured_section_skipped", "section": part}
            continue
        personality_notes_by_theme = {}
        if part == "personality":
            # The ten approved themes are fixed. Older model-selected headings
            # are replaced so a forced or ordinary regeneration uses this schema.
            previous_themes = old.get("themes") or []
            if previous_themes and old.get("theme_version") == PERSONALITY_THEME_VERSION and not force:
                themes = previous_themes
            else:
                themes = _theme_selection(owner, shared, rows, notes, language)
            personality_notes_by_theme = _assign_personality_interview_evidence(
                owner, themes, notes, language,
            )
            by_trait = {row["key"]: row for row in rows}
            units = [{
                "key": theme["key"], "title": theme["title"], "scope": theme["scope"],
                "evidence": {
                    "traits": [by_trait[t]["evidence"] | {"name": by_trait[t]["title"]}
                               for t in theme["traits"] if t in by_trait]
                }
            } for theme in themes]
        else:
            themes = []
            units = rows
        old_items = {x.get("key"): x for x in old.get("items") or []}
        saved_items = []
        section_error = False
        scoped_notes = _notes_for_category(notes, part)
        for item in units:
            existing = old_items.get(item["key"]) or {}
            item_notes = (
                personality_notes_by_theme.get(
                    item["key"], {"general_notes": "", "question_evidence": []},
                ) if part == "personality" else scoped_notes
            )
            fingerprint = _hash({
                "generation_rules_version": GENERATION_RULES_VERSION,
                "subject": item, "notes": item_notes,
                "guidance": _guidance(part, language), "language": language,
            })
            if not force and existing.get("status") == "completed" and existing.get("fingerprint") == fingerprint:
                saved_items.append(existing)
                continue
            yield {"type": "structured_item_started", "section": part, "item": item["key"]}
            try:
                testbild, intervjun = _generate_validated_item(
                    owner,
                    _item_prompt(owner, part, item, shared, item_notes, language),
                    language=language,
                )
                saved_items.append({
                    "key": item["key"], "title": item["title"], "testbild": testbild,
                    "intervjun": intervjun, "status": "completed",
                    "fingerprint": fingerprint, "generated_at": timezone.now().isoformat(),
                })
                yield {"type": "structured_item_complete", "section": part, "item": item["key"]}
            except Exception:
                section_error = True
                saved_items.append({**existing, "key": item["key"], "title": item["title"], "status": "failed"})
                yield {"type": "structured_item_error", "section": part, "item": item["key"],
                       "message": "This report item could not be generated."}
            sections[part] = {
                "status": "failed" if section_error else "generating",
                "items": saved_items + [old_items[x["key"]] for x in units[len(saved_items):]
                                         if x["key"] in old_items],
                "themes": themes,
                **({"theme_version": PERSONALITY_THEME_VERSION} if part == "personality" else {}),
            }
            _save(owner, state)
        sections[part] = {
            "status": "failed" if section_error else "completed",
            "items": saved_items, "themes": themes,
            **({"theme_version": PERSONALITY_THEME_VERSION} if part == "personality" else {}),
            "generated_at": timezone.now().isoformat(),
        }
        if part != "synthesis":
            prev_synthesis = sections.get("synthesis")
            if prev_synthesis and prev_synthesis.get("status") == "completed":
                prev_synthesis["status"] = "outdated"
        _save(owner, state)
        yield {"type": "structured_section_complete" if not section_error else "structured_section_error",
               "section": part, **({"message": "Some report items failed."} if section_error else {})}
    yield {"type": "structured_result", "data": state, "markdown": _legacy_markdown(state)}

def guarded_structured_overall_picture(owner, **kwargs):
    """Best-effort duplicate-submit guard; cache should be shared between workers."""
    from django.core.cache import cache

    lock = "talena:overall_picture:" + str(owner.pk)
    if not cache.add(lock, "generating", timeout=900):
        raise ValueError("Overall picture generation is already in progress.")
    try:
        yield from generate_structured_overall_picture(owner, **kwargs)
    finally:
        cache.delete(lock)

def mark_structured_sections_outdated(document):
    """Flag previous structured successes stale when source notes/context change."""
    typed = document.get("overall_picture_structured")
    if not isinstance(typed, dict):
        return False
    changed = False
    typed = deepcopy(typed)
    for section in (typed.get("sections") or {}).values():
        if section.get("status") == "completed":
            section["status"] = "outdated"
            changed = True
        for item in section.get("items") or []:
            if item.get("status") == "completed":
                item["status"] = "outdated"
                changed = True
    if changed:
        document["overall_picture_structured"] = typed
    return changed
