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
from .prompt_templates import get_global_ai_guidance

CATEGORIES = {"motivation": "motivation", "skills": "cognitive"}
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
    if category not in CATEGORIES:
        raise ValueError("Unknown manager report comment category.")
    language = normalize_ai_language(language_code)
    area_name = ("motivation" if category == "motivation" else "cognitive skills")
    return "\n\n".join([
        "TASK: Write the manager report's 'Kandidatens kommentarer' / "
        "'Candidate comments' for the " + area_name + " area only.",
        "OUTPUT: JSON object with exactly one string field 'text'. "
        "Use Swedish for sv, English for en. Language: " + language,
        "Write one coherent, concise, professional paragraph that paraphrases "
        "and polishes the actual interview notes and saved answers. "
        "Never copy/paste the raw notes or print the questions and answers as a list. "
        "Do not add facts, motivation, skills, causes, experience, intentions, "
        "outcomes, feelings or behaviour absent from the supplied answers. "
        "Do not speculate, evaluate the candidate's fit, or interpret test results.",
        "Preserve the distinction between the person's self-reported account "
        "and interviewer's observation. Do not present an interviewer inference "
        "as a verbatim candidate statement. Respect negations and uncertainty. "
        "A question alone is not evidence of an answer. "
        "If nothing relevant was actually described, return an empty string.",
        "Only interview material from THIS area is supplied below. Other "
        "categories' interview material and assessment scores are unavailable. "
        "Do not infer them.",
        "GLOBAL STYLE GUIDANCE:\n" + get_global_ai_guidance(language=language),
        "SOURCE INTERVIEW NOTES AND QUESTION/ANSWER PAIRS:\n" +
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
    response = get_openai_client().chat.completions.create(
        model=get_chat_model(),
        messages=[
            {"role": "system", "content":
             "You write a source-faithful manager report from interview material only. "
             "Reply with a JSON object containing only the text string."},
            {"role": "user", "content": prompt},
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
    from .structured_overall_picture import _validated_prose
    polished = _validated_prose(parsed["text"], field="Kandidatens kommentarer", allow_empty=True)
    return polished, fingerprint


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
