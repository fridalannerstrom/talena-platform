"""Read the three Interview notes areas from the existing persisted text.

The customer UI serializes them into TestInvitation.interview_notes with exact
headers. Mirror that contract on the server so AI prompts never receive text
from a different interview-note field. Do not infer topics from free-form text.
"""
from __future__ import annotations

import re

AREAS = ("personality", "motivation", "skills")
AREA_HEADINGS = {
    "Personlighet": "personality",
    "Motivation": "motivation",
    "Färdighet": "skills",
}
# Keep in sync with static/js/talena/interview-note-areas.js.
_SECTION_HEADER = re.compile(
    r"^### Intervjuunderlag: (Personlighet|Motivation|Färdighet)[ \t]*$",
    re.MULTILINE,
)


def split_interview_notes_by_area(value: str) -> dict[str, str]:
    """Return only the visible contents of each of the three UI text fields.

    Legacy, unclassified notes remain in the Personality field, matching the
    existing editor. Other sections never inherit them. Mixed historical notes
    must be categorised by the user, not heuristically reassigned by Talena.
    """
    text = str(value or "")
    sections = {area: "" for area in AREAS}
    if not text.strip():
        return sections

    headers = list(_SECTION_HEADER.finditer(text))
    if not headers:
        sections["personality"] = text
        return sections

    legacy_prefix = text[: headers[0].start()].strip()
    if legacy_prefix:
        sections["personality"] = legacy_prefix

    for index, match in enumerate(headers):
        start = match.end()
        stop = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        body = text[start:stop].strip()
        if not body:
            continue
        area = AREA_HEADINGS[match.group(1)]
        sections[area] = "\n\n".join(filter(None, (sections[area], body)))
    return sections
