"""Select concrete job duties already stated in a process context.

This is deterministic input structuring, not a new AI interpretation.
It preserves the original context text and never infers an unmentioned task.
"""
from __future__ import annotations

import re


_ACTIONS = (
    "designa", "utforma", "utveckla", "ta fram", "koordinera", "samordna",
    "leda", "utföra", "analysera", "sammanställa", "presentera",
    "planera", "skapa", "kommunicera", "hantera", "prioritera",
    "följa upp", "genomföra", "testa", "kvalitetssäkra", "delta",
    "samarbeta", "utvärdera", "kvalificera", "intervjua", "rekrytera",
    "publicera", "kontakta", "identifiera", "aktivt söka",
    "söka upp", "bygga", "stötta", "säkerställa", "ansvara",
    "manage", "coordinate", "analyse", "analyze", "design", "develop",
    "create", "plan", "conduct", "present", "communicate", "test",
    "deliver", "support", "evaluate", "build", "follow up", "prioritize",
)
_ACTION_START = re.compile(
    r"^(?:" + "|".join(re.escape(x) for x in sorted(_ACTIONS, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)
# Separators between role activities, not between words in one verb phrase.
_CLAUSE_STARTS = (
    "designa", "utforma", "utveckla", "ta fram", "koordinera",
    "samordna", "analysera", "sammanställa", "presentera",
    "skapa", "kommunicera", "hantera", "prioritera",
    "följa upp", "genomföra", "kvalitetssäkra", "utvärdera",
    "bygga", "säkerställa",
)
_SPLIT_AT_ACTIVITY = re.compile(
    r",\s*(?=(?:" + "|".join(re.escape(x) for x in _CLAUSE_STARTS) + r")\b)"
    r"|\s+och\s+(?=(?:hantera|sammanställa|presentera|säkerställa)\b)",
    re.IGNORECASE,
)
_ROLE_LEAD_IN = re.compile(
    r"^.*?\b(?:arbetet innebär att|rollen innebär att|"
    r"arbetsuppgifterna innebär att|ansvarar för att|"
    r"tasks include|responsibilities include)\s+",
    re.IGNORECASE,
)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")


def extract_role_task_anchors(context: str, *, limit: int = 8) -> list[str]:
    """Return distinct concise source phrases about real duties.

    Never produces a phrase absent from the supplied text. This is deliberately
    conservative: an incomplete list is safer than invented responsibilities.
    """
    text = str(context or "").strip()
    if not text or limit <= 0:
        return []

    candidates: list[str] = []
    for line in text.splitlines():
        line = _BULLET.sub("", line).strip()
        if not line:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            sentence = sentence.strip().rstrip(".;")
            if not sentence:
                continue
            explicit_duty = _ROLE_LEAD_IN.search(sentence)
            if explicit_duty:
                sentence = sentence[explicit_duty.end():]
            elif not _ACTION_START.search(sentence):
                # Avoid employer background, qualifications and legal disclaimers.
                continue

            for clause in _SPLIT_AT_ACTIVITY.split(sentence):
                clause = clause.strip(" \t.,;:")
                if _ACTION_START.search(clause) and 10 <= len(clause) <= 240:
                    candidates.append(clause)

    # Preserve first occurrence but avoid verbatim duplicates.
    anchors: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = re.sub(r"\s+", " ", item).casefold()
        if key in seen:
            continue
        seen.add(key)
        anchors.append(item)
        if len(anchors) >= limit:
            break
    return anchors
