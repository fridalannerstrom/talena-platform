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
        "hjälpa kolleg", "påverka", "nätverk",
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
        "misstag", "fel", "kritik", "press", "stress", "motgång",
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

    from apps.processes.interview_question_evidence import (
        build_interview_question_evidence,
    )

    question_evidence = build_interview_question_evidence(owner)
    notes = str(getattr(owner, "interview_notes", "") or "").strip()
    interview_evidence_by_theme = _route_manager_interview_evidence(
        notes,
        question_evidence.get("items") or [],
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

INTERVIEW EVIDENCE ROUTED BY THEME
Each interview item below is assigned to at most one theme because its question or note clearly concerns that theme. An empty list means there is no clearly relevant interview evidence for that theme.
{json.dumps(interview_evidence_by_theme, ensure_ascii=False, indent=2)}

EVIDENCE RULES
- For each testbild field, use only the personality indicator interpretations for its theme. Do not use interview evidence.
- For each candidate_describes field, use only interview evidence listed under that exact theme. Do not use evidence listed under another theme or personality test results.
- Treat the interview evidence as the candidate's account, not as proof of skill, competence, behaviour, or performance.
- Do not infer feelings, reactions, support needs, motivation, experience, or ability from an event unless the interview notes explicitly describe them.
- A factual example of an error (such as giving incorrect change) does not by itself show how the person handles pressure, takes responsibility, or needs support.
- Do not turn theoretical knowledge or preparation into practical experience, leadership ability, or an expressed willingness unless stated.
- Context may clarify relevance but is not evidence about the candidate.
- If the routed evidence does not directly address the field, return an empty string for that field.
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


def _parse_event(raw_line: str) -> dict[str, Any] | None:
    try:
        event = json.loads(raw_line.strip())
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(event, dict) or not event.get("type"):
        return None
    return event


def stream_manager_report_personality(
    *, owner, language_code: str = "en"
) -> Iterable[dict[str, Any]]:
    language_code = normalize_ai_language(language_code)
    prompt = redact_candidate_name(
        build_manager_report_personality_prompt(
            owner,
            language_code=language_code,
        ),
        owner.candidate,
    )
    system_language_instruction = get_ai_system_language_instruction(
        language_code,
        owner=owner,
    )
    stream = get_openai_client().chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate only the independent manager-report "
                    "personality fields requested by Talena. Follow the "
                    "evidence boundaries and NDJSON contract exactly. For "
                    "every testbild field, write a concise, coherent "
                    "synthesis in natural prose, usually two to four "
                    "sentences. Do not list indicator names, repeat "
                    "indicator labels, use bullet points or dash-separated "
                    "entries, or copy the source interpretations one by one. "
                    "Describe possible preferences and tendencies, not "
                    "ability or proven performance. These testbild format "
                    "rules apply even if field guidance requests another "
                    "format. Leave candidate_describes fields unchanged in "
                    "style and follow their field guidance. "
                    f"{system_language_instruction}"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        stream=True,
    )

    buffer = ""
    for response_event in stream:
        delta = response_event.choices[0].delta
        if not delta or not delta.content:
            continue
        buffer += delta.content
        while "\n" in buffer:
            raw_line, buffer = buffer.split("\n", 1)
            parsed = _parse_event(raw_line)
            if parsed:
                yield parsed
    parsed = _parse_event(buffer)
    if parsed:
        yield parsed


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
