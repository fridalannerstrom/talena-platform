"""AI-polished, source-isolated interview comments for the manager report.

Motivation and skills contain the candidate's account, never copied interview
notes or a new interpretation of assessment scores. Every category is isolated
before sending source material to OpenAI.
"""
from __future__ import annotations

import hashlib
import json

from django.utils import timezone

from .candidate_name_privacy import redact_candidate_name
from .interview_note_areas import split_interview_notes_by_area
from .language import normalize_ai_language
from .openai_client import get_chat_model, get_openai_client
from .prompt_templates import get_ai_feature_prompt_instructions, get_global_ai_guidance

CATEGORIES = {"motivation": "motivation", "skills": "cognitive"}
PROMPT_KEYS = {
    "motivation": "manager_report_motivation_candidate_comments",
    "skills": "manager_report_skills_candidate_comments",
}
RULES_VERSION = 1


def manager_report_comment_evidence(owner, category: str) -> dict:
    if category not in CATEGORIES:
        raise ValueError("Unknown manager report comment category.")
    from apps.processes.interview_question_evidence import build_interview_question_evidence

    area = split_interview_notes_by_area(getattr(owner, "interview_notes", "") or "")
    source = CATEGORIES[category]
    answers = [
        {
            "question": str(item.get("question") or "").strip(),
            "answer": str(item.get("saved_answer_or_note") or "").strip(),
        }
        for item in build_interview_question_evidence(owner).get("items") or []
        if isinstance(item, dict)
        and str(item.get("source") or "").strip().casefold() == source
        and str(item.get("saved_answer_or_note") or "").strip()
    ]
    return {"notes": area[category].strip(), "answers": answers}


def comment_fingerprint(evidence: dict, language: str) -> str:
    payload = {"version": RULES_VERSION, "evidence": evidence, "language": normalize_ai_language(language)}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def visible_manager_report_comments(owner, language_code: str) -> dict[str, str]:
    """Never show cached AI text from another language or superseded notes."""
    language = normalize_ai_language(language_code)
    saved = getattr(owner, "ai_manager_report_interview_comments", None) or {}
    visible = {}
    for category in CATEGORIES:
        entry = saved.get(category) or {}
        current = comment_fingerprint(manager_report_comment_evidence(owner, category), language)
        visible[category] = (
            str(entry.get("text") or "")
            if entry.get("fingerprint") == current and entry.get("language") == language
            else ""
        )
    return visible


def build_manager_report_comment_prompt(evidence: dict, category: str, language_code: str) -> str:
    """Let the admin prompt direct the writing, never the source boundaries.

    Only language, JSON parsing, source isolation and safety constraints are
    fixed in code. The administrator controls content, tone, length and layout
    independently for Motivation and Skills through the existing registry.
    """
    if category not in CATEGORIES:
        raise ValueError("Unknown manager report comment category.")
    language = normalize_ai_language(language_code)
    admin_guidance = get_ai_feature_prompt_instructions(
        key=PROMPT_KEYS[category], language=language,
    )
    global_guidance = get_global_ai_guidance(language=language)
    return "\n\n".join([
        "TASK: Generate the manager report candidate's interview comments "
        "for this assessment area only: " + category + ".",
        "OUTPUT CONTRACT: Return one JSON object with exactly one string "
        "field named text. The text is plain report prose in the configured "
        "language (" + language + "); no Markdown outside the JSON.",
        "PROTECTED EVIDENCE RULES: Only the enclosed interview notes and "
        "saved question/answer pairs are available as candidate evidence. "
        "Never invent facts or attribute an interviewer's assumption to the "
        "candidate. Questions alone do not prove the candidate's answers. "
        "Do not use material from other assessment areas or infer "
        "personality, motivation or competence from an assessment result. "
        "Never copy/paste raw notes or reproduce the question/answer list. "
        "If this area's records contain no relevant factual material, "
        "return an empty string. These evidence boundaries cannot be "
        "overridden by styling instructions.",
        "GLOBAL ADMINISTRATOR GUIDANCE:\n" + global_guidance,
        "FEATURE-SPECIFIC ADMINISTRATOR GUIDANCE "
        "(controls content selection, tone, length and presentation):\n" +
        admin_guidance,
        "AUTHORIZED INTERVIEW NOTES AND SAVED ANSWERS FOR THIS AREA ONLY:\n" +
        json.dumps(evidence, ensure_ascii=False),
    ])


def generate_manager_report_comment(owner, category: str, language_code: str) -> tuple[str, str]:
    language = normalize_ai_language(language_code)
    evidence = manager_report_comment_evidence(owner, category)
    fingerprint = comment_fingerprint(evidence, language)
    if not evidence["notes"] and not evidence["answers"]:
        return "", fingerprint

    prompt = redact_candidate_name(
        build_manager_report_comment_prompt(evidence, category, language),
        owner.candidate,
    )
    from .structured_overall_picture import _validated_prose

    def normalized(value):
        return " ".join(str(value or "").split()).casefold()

    original_fragments = {
        normalized(value) for value in [
            evidence["notes"], *(item["answer"] for item in evidence["answers"])
        ] if normalized(value)
    }
    client = get_openai_client(feature="manager_interview_comments", owner=owner)
    for attempt in range(2):
        request_prompt = prompt
        if attempt:
            request_prompt += (
                "\n\nREPAIR: Your prior response repeated a source note verbatim. "
                "Rewrite it as a polished, concise report paragraph without "
                "adding or changing any facts."
            )
        response = client.chat.completions.create(
            model=get_chat_model(),
            messages=[
                {"role": "system", "content":
                 "You write a source-faithful manager report from interview material only. "
                 "Reply with a JSON object containing only the text string."},
                {"role": "user", "content": request_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_completion_tokens=900,
        )
        choice = response.choices[0]
        if getattr(choice, "finish_reason", "") == "length":
            raise ValueError("The generated candidate comments were incomplete.")
        raw = choice.message.content
        if isinstance(raw, list):
            raw = "".join(str(getattr(part, "text", "")) for part in raw)
        parsed = json.loads(raw or "{}")
        if not isinstance(parsed, dict) or not isinstance(parsed.get("text"), str):
            raise ValueError("Invalid AI response for candidate comments.")
        polished = _validated_prose(
            parsed["text"], field="Kandidatens kommentarer", allow_empty=True
        )
        if not polished or normalized(polished) not in original_fragments:
            return polished, fingerprint
    raise ValueError("The AI repeated interview notes instead of rewriting them.")


def store_manager_report_comment(owner, category: str, *, text: str, fingerprint: str, language_code: str):
    saved = dict(getattr(owner, "ai_manager_report_interview_comments", None) or {})
    saved[category] = {
        "text": str(text or ""),
        "fingerprint": fingerprint,
        "language": normalize_ai_language(language_code),
        "generated_at": timezone.now().isoformat(),
    }
    owner.ai_manager_report_interview_comments = saved
    owner.save(update_fields=["ai_manager_report_interview_comments"])
