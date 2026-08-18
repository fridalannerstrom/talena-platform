from __future__ import annotations


INTERVIEW_SECTION_DEFAULTS = {
    "cognitive": {
        "order": 1,
        "question_count": 3,
        "estimated_minutes": 10,
    },
    "motivation": {
        "order": 2,
        "question_count": 3,
        "estimated_minutes": 10,
    },
    "personality": {
        "order": 3,
        "question_count": 8,
        "estimated_minutes": 20,
    },
}


def get_interview_section_config(key: str) -> dict:
    normalised_key = str(key or "").strip().lower()

    config = INTERVIEW_SECTION_DEFAULTS.get(
        normalised_key,
        {},
    )

    return {
        "key": normalised_key,
        "order": int(config.get("order", 99)),
        "question_count": int(
            config.get("question_count", 0)
        ),
        "estimated_minutes": int(
            config.get("estimated_minutes", 0)
        ),
    }
