from __future__ import annotations

import json
from typing import Any, Iterable

from django.utils import timezone

from .candidate_name_privacy import redact_candidate_name
from .language import (
    get_ai_language_instruction,
    get_ai_system_language_instruction,
    normalize_ai_language,
    set_ai_content_language,
)
from .openai_client import get_chat_model, get_openai_client
from .personality_interpretation import (
    PERSONALITY_MANAGER_REPORT_THEMES,
    build_personality_indicator_interpretations,
)
from .prompt_templates import get_ai_feature_prompt_instructions
from .shared_context import build_shared_ai_context, get_process_purpose_key


PARTS = ("testbild", "candidate_describes")

MANAGER_INTERVIEW_THEME_CUES = {
    "leading_and_working_with_others": (
        "leda", "ledde", "ledarskap", "driva arbetet", "driva en fråga",
        "ta initiativ", "samordna", "koordinera", "användartest",
        "användartester", "samarbeta", "samarbete", "stötta", "stödja",
        "hjälpa kolleg", "påverka", "nätverk", "involver", "kolleg",
        "team", "arbetsgrupp", "annons", "inspel", "synpunkt",
        "gemensam", "tillsammans", "sammanställ", "förankra",
        "rekryterande chef",
    ),
    "organising_and_thinking_patterns": (
        "planera", "planering", "prioritera", "prioritering", "struktur",
        "organisera", "organisering", "mål", "målsättning", "lösa problem",
        "problemlösning", "analysera", "analys", "kreativ", "idé",
        "förändring", "anpassa arbetssätt",
    ),
    "interaction_and_emotion_management": (
        "regel", "överenskommelse", "uppriktig", "ärlig", "rak",
        "uttrycka sin åsikt", "uttrycka sina åsikter", "kommunikation",
        "misstag", "kritik", "press", "stress", "motgång",
        "självständigt", "självständighet", "vägledning", "avstämning",
        "stöd från andra",
    ),
}


def _route_manager_interview_evidence(
    general_notes: str,
    question_items: list[dict[str, Any]],
) -> dict[str, list[dict[str, str]]]:
    """Route interview evidence to one clearly relevant manager-report theme."""
    routed = {theme["key"]: [] for theme in PERSONALITY_MANAGER_REPORT_THEMES}

    def best_theme(text: str) -> str | None:
        normalized = " ".join(str(text or "").lower().split())
        # In this report, user-test coordination examples belong to the
        # leadership/collaboration theme even when the question also mentions
        # planning or organization.
        if "användartest" in normalized or "användartester" in normalized:
            return "leading_and_working_with_others"
        scores = {
            theme: sum(cue in normalized for cue in cues)
            for theme, cues in MANAGER_INTERVIEW_THEME_CUES.items()
        }
        top = max(scores.values(), default=0)
        winners = [theme for theme, score in scores.items() if score == top and score > 0]
        return winners[0] if len(winners) == 1 else None

    for paragraph in (part.strip() for part in str(general_notes or "").splitlines() if part.strip()):
        theme = best_theme(paragraph)
        if theme:
            routed[theme].append({"source": "general_interview_note", "evidence": paragraph})

    for item in question_items:
        question = str(item.get("question") or "")
        answer = str(item.get("saved_answer_or_note") or "")
        theme = best_theme(question)
        if theme:
            routed[theme].append({
                "source": str(item.get("source_label") or item.get("source") or "interview"),
                "question": question,
                "evidence": answer,
            })

    return routed



def _get_manager_report_interview_material(owner):
    """Keep all saved interview material, even when cue-based routing is unsure.

    Keyword routing is only a hint for the model, never a completeness gate.
    A multi-theme example, paraphrase or English question must not disappear
    merely because it lacks one of the Swedish keyword cues.
    """
    from apps.processes.interview_question_evidence import (
        build_interview_question_evidence,
    )

    question_evidence = build_interview_question_evidence(owner)
    notes = str(getattr(owner, "interview_notes", "") or "").strip()
    items = question_evidence.get("items") or []
    routed = _route_manager_interview_evidence(notes, items)
    return routed, notes, items


def _get_manager_report_interview_evidence(owner) -> dict[str, list[dict[str, str]]]:
    # Compatibility for callers that need the suggested primary theme only.
    routed, _notes, _items = _get_manager_report_interview_material(owner)
    return routed


def _enforce_manager_interview_availability(
    event: dict[str, Any], *, has_interview_evidence: bool
) -> dict[str, Any]:
    """Only blank a candidate account when there is no interview input at all.

    With interview evidence, relevance is judged against the full source notes
    and the specific question/answer pairs by the report generator.
    """
    if (
        event.get("type") == "manager_report_personality_text"
        and event.get("part") == "candidate_describes"
        and not has_interview_evidence
    ):
        return {**event, "text": ""}
    return event



def empty_manager_report_personality() -> dict[str, dict[str, str]]:
    return {
        theme["key"]: {part: "" for part in PARTS}
        for theme in PERSONALITY_MANAGER_REPORT_THEMES
    }


def build_manager_report_personality_prompt(owner, *, language_code: str = "en") -> str:
    language_code = normalize_ai_language(language_code)
    shared_context = build_shared_ai_context(owner)
    indicator_interpretations = build_personality_indicator_interpretations(
        owner,
        language_code=language_code,
    )

    interview_evidence_by_theme, general_interview_notes, question_items = (
        _get_manager_report_interview_material(owner)
    )

    guidance = {}
    for theme in PERSONALITY_MANAGER_REPORT_THEMES:
        guidance[theme["key"]] = {
            part: get_ai_feature_prompt_instructions(
                key=f"manager_personality_{theme['prompt_stem']}_{part}",
                language=language_code,
            )
            for part in PARTS
        }

    examples = {
        "leading_and_working_with_others": {
            "testbild": "",
            "candidate_describes": "",
        },
        "organising_and_thinking_patterns": {
            "testbild": "",
            "candidate_describes": "",
        },
        "interaction_and_emotion_management": {
            "testbild": "",
            "candidate_describes": "",
        },
    }

    event_lines = []
    for theme in PERSONALITY_MANAGER_REPORT_THEMES:
        for part in PARTS:
            event_lines.append(json.dumps({
                "type": "manager_report_personality_text",
                "theme": theme["key"],
                "part": part,
                "text": examples[theme["key"]][part],
            }, ensure_ascii=False))
    event_lines.append(json.dumps({"type": "done"}))

    return f"""
TASK
Generate the six separate personality texts for the manager report. This is an independent report task; do not generate or rewrite the candidate's overall personality interpretation.

PURPOSE AND CONTEXT
Purpose: {shared_context["purpose_label"]}
Process context: {shared_context["context_text"] or "No additional process context supplied."}

PERSONALITY INDICATOR INTERPRETATIONS BY THEME
{json.dumps(indicator_interpretations, ensure_ascii=False, indent=2)}

INTERVIEW EVIDENCE SUGGESTED BY THEME
The keyword-based routing below is only a helpful first suggestion. It can miss
paraphrases, English questions and examples involving multiple themes. An empty
theme list does NOT prove that relevant interview evidence is missing.
{json.dumps(interview_evidence_by_theme, ensure_ascii=False, indent=2)}

COMPLETE GENERAL INTERVIEW NOTES
{general_interview_notes or "No general interview notes were provided."}

COMPLETE SAVED QUESTION-SPECIFIC INTERVIEW EVIDENCE
These records preserve each answer together with the exact question it answered.
{json.dumps(question_items, ensure_ascii=False, indent=2)}

EVIDENCE RULES
- For each testbild field, use only the personality indicator interpretations for its theme. Do not use interview evidence.
- For each candidate_describes field, review BOTH the suggested theme entries and the complete interview notes and question/answer records. Select specific, factual details that actually concern this theme, even when the keyword router failed to classify them. An example may be relevant to more than one theme, but do not repeat the same description unnecessarily.
- Do not turn an item routed under another theme into a claim about this theme unless its actual words clearly support that connection. Never borrow personality test results as interview evidence.
- Preserve provenance: interview notes may be a paraphrased candidate account or an interviewer observation. Do not present an interviewer's inference as the candidate's own statement or as proof of skill, competence, behaviour, or performance.
- For testbild text, describe possible preferences or tendencies; never call them natural ability, competence, or proven performance.
- Do not infer feelings, reactions, support needs, motivation, experience, or ability from an event unless the interview notes explicitly describe them.
- A factual example of an error (such as giving incorrect change) does not by itself show how the person handles pressure, takes responsibility, or needs support.
- Do not turn theoretical knowledge or preparation into practical experience, leadership ability, or an expressed willingness unless stated.
- Context may clarify relevance but is not evidence about the candidate.
- Do not recommend that the recruiter explore a trait, and do not describe a trait as valuable, suitable, or beneficial for the role.
- Describe role relevance only as a cautious possible expression of the stated tendency, not as a claim about contribution or fit.
- Prioritise a brief, grounded account of what was actually described over a generic statement about missing interview evidence. A limited example may be summarised narrowly, with its uncertainty clear; it need not prove a stable personality pattern.
- If the complete interview material has no factual information relevant to a theme, return an empty string for that field rather than asserting that all interview notes are missing.
- Do not invent candidate facts, behaviours, experience, or role requirements.

FIELD GUIDANCE
{json.dumps(guidance, ensure_ascii=False, indent=2)}

OUTPUT CONTRACT
Return newline-delimited JSON (NDJSON), one JSON object per line, no Markdown and no text outside JSON.
Return exactly one manager_report_personality_text event for each theme/part pair in this order, using the exact keys and part names shown in the examples. Finish with the done event.
{chr(10).join(event_lines)}

OUTPUT LANGUAGE
{get_ai_language_instruction(language_code)}
""".strip()


def build_manager_report_personality_part_prompt(
    owner, *, part: str, language_code: str = "en"
) -> str:
    """Isolate assessment and interview sources in separate model requests.

    Testbild is generated without receiving *any* interview notes or
    question-specific answers. Kandidaten beskriver is generated without
    receiving assessment interpretations. This prevents cross-source leakage
    even if a model or edited admin prompt disregards prose-only boundaries.
    """
    if part not in PARTS:
        raise ValueError("Unknown manager-report personality part.")
    language_code = normalize_ai_language(language_code)
    shared_context = build_shared_ai_context(owner)
    guidance = {
        theme["key"]: get_ai_feature_prompt_instructions(
            key=f"manager_personality_{theme['prompt_stem']}_{part}",
            language=language_code,
        )
        for theme in PERSONALITY_MANAGER_REPORT_THEMES
    }
    examples = [
        json.dumps({
            "type": "manager_report_personality_text",
            "theme": theme["key"], "part": part, "text": "",
        }, ensure_ascii=False)
        for theme in PERSONALITY_MANAGER_REPORT_THEMES
    ]

    if part == "testbild":
        source = json.dumps(
            build_personality_indicator_interpretations(
                owner, language_code=language_code,
            ), ensure_ascii=False, indent=2,
        )
        source_label = "PERSONALITY INDICATOR INTERPRETATIONS ONLY"
        rules = (
            "Use ONLY the supplied personality-test indicator interpretations "
            "for each named theme. No interview notes, saved answers or "
            "candidate interview material are present in this request. "
            "Do not describe or infer what the candidate said in an interview. "
            "Describe cautious tendencies and preferences, not proven "
            "abilities, experience, competence or performance. "
            "Write a coherent 2–4 sentence synthesis for each theme, "
            "without lists or individual indicator labels."
        )
    else:
        suggested, general_notes, question_items = (
            _get_manager_report_interview_material(owner)
        )
        source = json.dumps({
            "general_interview_notes": general_notes,
            "saved_interview_question_answers": question_items,
            "suggested_theme_routes_only": suggested,
        }, ensure_ascii=False, indent=2)
        source_label = "COMPLETE INTERVIEW MATERIAL ONLY"
        rules = (
            "Only use actual interview notes, saved answers and observations. "
            "The suggested theme routes are optional keyword hints, not gates. "
            "Read the FULL source when choosing facts for each theme: one "
            "example may be relevant to multiple themes, but do not repeat it "
            "unnecessarily. Interpret each answer with its exact question. "
            "Do not treat interviewer notes as verbatim candidate quotations. "
            "Never invent actions, intentions, outcomes, experience or "
            "competence. Do not infer a demonstrated skill from theoretical "
            "knowledge or use of software. No personality-test results are "
            "present or permitted in this request. "
            "Prefer a concise, grounded account to a generic claim that notes "
            "are missing. Return an empty string ONLY when the complete "
            "interview material contains no relevant factual information "
            "for that theme. When there is no interview material whatsoever, "
            "return empty strings for all three themes."
        )

    return "\n\n".join([
        "TASK: Generate three independent manager-report personality texts. "
        "Generate ONLY part " + part + ".",
        "PURPOSE: " + str(shared_context["purpose_label"]),
        "PROCESS CONTEXT (not candidate evidence): " +
        str(shared_context["context_text"] or "No further context."),
        source_label + ":\n" + source,
        "EVIDENCE RULES: " + rules,
        "SCOPED ADMIN INSTRUCTIONS:\n" +
        json.dumps(guidance, ensure_ascii=False, indent=2),
        "OUTPUT: Exactly one JSON text event for EACH of the three theme keys, "
        "with the same part name. Use NDJSON, one object per line, and a final "
        'JSON object {"type":"done"}. No Markdown.',
        "\n".join(examples),
        '{"type":"done"}',
        "OUTPUT LANGUAGE: " + get_ai_language_instruction(language_code),
    ])


def _parse_event(raw_line: str) -> dict[str, Any] | None:
    try:
        event = json.loads(raw_line.strip())
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(event, dict) or not event.get("type"):
        return None
    return event


def _recover_manager_report_events(raw_text: str) -> list[dict[str, Any]]:
    text = str(raw_text or "").strip()
    if not text:
        return []

    unfenced = "\n".join(
        line for line in text.splitlines()
        if not line.strip().startswith("```")
    )
    events: list[dict[str, Any]] = []

    def collect(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                collect(item)
            return
        if not isinstance(value, dict):
            return
        if value.get("type") == "manager_report_personality_text":
            events.append(value)
            return
        if value.get("type") == "done":
            events.append(value)
            return
        if value.get("theme") and value.get("part") and "text" in value:
            events.append({
                "type": "manager_report_personality_text",
                "theme": value["theme"],
                "part": value["part"],
                "text": value["text"],
            })
            return

        # Recover the common nested shape {theme: {part: text}} too.
        for theme in PERSONALITY_MANAGER_REPORT_THEMES:
            theme_key = theme["key"]
            parts = value.get(theme_key)
            if isinstance(parts, dict):
                for part in PARTS:
                    if part in parts:
                        collect({
                            "theme": theme_key,
                            "part": part,
                            "text": parts[part],
                        })
        for key, nested in value.items():
            if key not in {theme["key"] for theme in PERSONALITY_MANAGER_REPORT_THEMES}:
                collect(nested)

    # Parse individual NDJSON lines and complete JSON containers.
    for line in unfenced.splitlines():
        try:
            collect(json.loads(line.strip()))
        except (json.JSONDecodeError, TypeError):
            pass

    decoder = json.JSONDecoder()
    index = 0
    while index < len(unfenced):
        start = unfenced.find("{", index)
        if start < 0:
            break
        try:
            value, end = decoder.raw_decode(unfenced, start)
        except json.JSONDecodeError:
            index = start + 1
            continue
        collect(value)
        index = max(end, start + 1)

    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in events:
        key = json.dumps(event, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(event)
    return unique


def stream_manager_report_personality(
    *, owner, language_code: str = "en"
) -> Iterable[dict[str, Any]]:
    """Stream two source-isolated requests, publishing a single done event."""
    language_code = normalize_ai_language(language_code)
    _suggested, general_notes, question_items = (
        _get_manager_report_interview_material(owner)
    )
    has_interview_evidence = bool(general_notes or question_items)
    system_language_instruction = get_ai_system_language_instruction(
        language_code, owner=owner,
    )
    client = get_openai_client()

    for part in PARTS:
        prompt = redact_candidate_name(
            build_manager_report_personality_part_prompt(
                owner, part=part, language_code=language_code,
            ),
            owner.candidate,
        )
        source_boundary = (
            "This request contains assessment evidence ONLY. No interview "
            "notes or answers may be used or inferred."
            if part == "testbild"
            else "This request contains interview evidence ONLY. No "
            "personality-test results may be used or inferred."
        )
        stream = client.chat.completions.create(
            model=get_chat_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate only the requested independent manager-"
                        "report personality fields for Talena. Follow the "
                        "evidence rules and NDJSON output contract exactly. "
                        "Never treat process context or examples in admin "
                        "guidance as facts about the candidate. "
                        + source_boundary + " " + system_language_instruction
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            stream=True,
        )

        buffer = ""
        complete_response = ""
        emitted_fields: set[tuple[str, str]] = set()

        def validated(event: dict[str, Any]) -> dict[str, Any] | None:
            if (
                event.get("type") != "manager_report_personality_text"
                or event.get("part") != part
                or event.get("theme")
                not in {item["key"] for item in PERSONALITY_MANAGER_REPORT_THEMES}
            ):
                return None
            if part == "candidate_describes":
                return _enforce_manager_interview_availability(
                    event, has_interview_evidence=has_interview_evidence
                )
            return event

        for response_event in stream:
            delta = response_event.choices[0].delta
            if not delta or not delta.content:
                continue
            buffer += delta.content
            complete_response += delta.content
            while "\n" in buffer:
                raw_line, buffer = buffer.split("\n", 1)
                parsed = _parse_event(raw_line)
                if parsed:
                    checked = validated(parsed)
                    if checked:
                        field = (str(checked["theme"]), part)
                        if field not in emitted_fields:
                            emitted_fields.add(field)
                            yield checked

        # Recover complete JSON containers and NDJSON trailing fragments.
        for parsed in _recover_manager_report_events(complete_response):
            checked = validated(parsed)
            if checked:
                field = (str(checked["theme"]), part)
                if field not in emitted_fields:
                    emitted_fields.add(field)
                    yield checked

    yield {"type": "done"}


def apply_manager_report_personality_event(
    result: dict[str, Any], event: dict[str, Any]
) -> dict[str, Any]:
    if event.get("type") != "manager_report_personality_text":
        return result
    theme = str(event.get("theme") or "")
    part = str(event.get("part") or "")
    valid_themes = {item["key"] for item in PERSONALITY_MANAGER_REPORT_THEMES}
    if theme in valid_themes and part in PARTS:
        result.setdefault(theme, {})[part] = str(event.get("text") or "").strip()
    return result


def save_manager_report_personality(
    *, owner, result: dict[str, Any], language_code: str = "en"
) -> None:
    language_code = normalize_ai_language(language_code)
    normalized = empty_manager_report_personality()
    for theme, parts in normalized.items():
        source = result.get(theme) or {}
        for part in PARTS:
            parts[part] = str(source.get(part) or "").strip()

    owner.ai_manager_report_personality = normalized
    owner.ai_manager_report_personality_status = "completed"
    owner.ai_manager_report_personality_generated_at = timezone.now()
    owner.ai_manager_report_personality_purpose = get_process_purpose_key(
        owner.process
    )
    set_ai_content_language(owner, "manager_report_personality", language_code)
    owner.save(update_fields=[
        "ai_manager_report_personality",
        "ai_manager_report_personality_status",
        "ai_manager_report_personality_generated_at",
        "ai_manager_report_personality_purpose",
        "ai_content_languages",
    ])

    # Manager personality is regenerated independently of Overall picture and
    # manager advice. Snapshot only this part, never clear the other digests.
    from django.db import transaction
    from apps.processes.post_interview_evidence import stamp_report_evidence

    with transaction.atomic():
        stored_owner = type(owner).objects.select_for_update().get(pk=owner.pk)
        if stored_owner.ai_post_interview_decision_support:
            stored_owner.ai_post_interview_decision_support = stamp_report_evidence(
                stored_owner.ai_post_interview_decision_support,
                stored_owner,
                "manager_personality",
            )
            stored_owner.save(update_fields=["ai_post_interview_decision_support"])
