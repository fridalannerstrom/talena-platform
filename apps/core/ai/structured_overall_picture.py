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


def _theme_selection(owner, shared, rows, notes, language):
    if not rows:
        return []
    identity = [r["key"] for r in rows]
    global_rules, _narrative_guidance = _guidance("personality", language)
    prompt = (
        "Select up to seven (usually five to seven when supported) genuinely distinct "
        "ROLE-RELEVANT work themes from the supplied candidate personality evidence "
        "and existing process context. Theme headings must describe meaningful work "
        "domains rather than trait names. Never invent role requirements or new traits. "
        "Return JSON object with key themes: a list of objects {title: string, traits: "
        "list of exact trait keys from the evidence}. Use at most three relevant traits "
        "per theme; each selected trait must exist in the supplied list. "
        "If evidence or role context is sparse, return fewer distinct themes.\n"
        "Language: " + language + "\nRole context: " + str(shared.get("context_text") or "") +
        "\nPersonality results: " + json.dumps(
            [{"key": x["key"], "title": x["title"], "summary": x["evidence"]["summary"]} for x in rows],
            ensure_ascii=False
        ) + "\nProtected constraints: " + global_rules
        # The editable personality-writing instructions are used in the
        # per-theme text calls, not this typed theme-selection step.
    )
    parsed = _completion(prompt, owner, output_tokens=1200)
    results = []
    for item in (parsed.get("themes") or [])[:7]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:150]
        traits = [key for key in (item.get("traits") or []) if isinstance(key, str) and key in identity][:3]
        if not title or not traits or title.casefold() in [x["title"].casefold() for x in results]:
            continue
        results.append({"key": "theme_" + str(len(results) + 1), "title": title, "traits": traits})
    return results


def _item_prompt(owner, category, item, shared, notes, language):
    global_rules, guidance = _guidance(category, language)
    return "\n\n".join([
        "OUTPUT: JSON object with keys testbild and intervjun, each containing one or more "
        "natural paragraphs. No Markdown headings. Write in language: " + language,
        "CANDIDATE: CANDIDATE_A",
        "AREA: " + str(item["title"]),
        "PURPOSE: " + str(shared.get("purpose_label") or ""),
        "ROLE CONTEXT (for relevance, not proof): " + str(shared.get("context_text") or ""),
        "ASSESSMENT FOR THIS AREA ONLY:\n" + json.dumps(item["evidence"], ensure_ascii=False),
        "INTERVIEW NOTES (only cite material explicitly relevant to this area):\n" +
        json.dumps(notes, ensure_ascii=False),
        "PROTECTED EVIDENCE RULES: Testbild must use ONLY assessment data; "
        "Intervjun must use ONLY actual interview evidence, and missing topic-specific "
        "evidence must be acknowledged briefly. Never infer interview stories from scores. "
        "No other assessment sources, raw scores in prose, or suitability decisions. "
        "Keep exact question/answer provenance; an interviewer note is not a verbatim quote. "
        "Do not emit personal identifiers.",
        "GLOBAL AI GUIDANCE:\n" + global_rules,
        "SCOPED ADMIN PROMPT:\n" + guidance,
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
        "ROLE CONTEXT: " + str(shared.get("context_text") or ""),
        "PREVIOUSLY GENERATED, SOURCE-BOUNDED SECTIONS: " + json.dumps(available, ensure_ascii=False),
        "Protected: do not introduce new information, interview anecdotes, suitability "
        "judgments or hiring verdicts; keep test indications and candidate accounts distinct.",
        "GLOBAL GUIDANCE: " + global_rules,
        "SCOPED ADMIN GUIDANCE: " + guidance,
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
                "sources": sources, "language": language, "guidance": _guidance(part, language),
            })
            if not force and old.get("status") == "completed" and old.get("fingerprint") == fingerprint:
                yield {"type": "structured_section_skipped", "section": part}
                continue
            try:
                response = _completion(_synthesis_prompt(owner, sections, shared, language), owner, output_tokens=1600)
                text = str(response.get("text") or "").strip()
                if not text:
                    raise ValueError("The final synthesis was empty.")
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
        if part == "personality":
            # Persist the controlled selection so retries do not silently
            # change theme identities or discard a previous successful item.
            previous_themes = old.get("themes") or []
            if previous_themes and not force:
                themes = previous_themes
            else:
                try:
                    themes = _theme_selection(owner, shared, rows, notes, language)
                except Exception:
                    sections[part] = {**old, "status": "failed"}
                    _save(owner, state)
                    yield {"type": "structured_section_error", "section": part, "message": "Could not select grounded personality themes."}
                    continue
            by_trait = {row["key"]: row for row in rows}
            units = [{
                "key": theme["key"], "title": theme["title"],
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
            fingerprint = _hash({
                "subject": item, "notes": scoped_notes,
                "guidance": _guidance(part, language), "context": shared.get("context_text"),
                "language": language,
            })
            if not force and existing.get("status") == "completed" and existing.get("fingerprint") == fingerprint:
                saved_items.append(existing)
                continue
            yield {"type": "structured_item_started", "section": part, "item": item["key"]}
            try:
                result = _completion(_item_prompt(owner, part, item, shared, scoped_notes, language), owner)
                testbild = str(result.get("testbild") or "").strip()
                intervjun = str(result.get("intervjun") or "").strip()
                if not testbild:
                    raise ValueError("The model did not return Testbild.")
                if not intervjun:
                    # General notes may exist without covering this particular area.
                    # A blank interview field is never permission to invent examples.
                    intervjun = MISSING_INTERVIEW[language]
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
            }
            _save(owner, state)
        sections[part] = {
            "status": "failed" if section_error else "completed",
            "items": saved_items, "themes": themes,
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
