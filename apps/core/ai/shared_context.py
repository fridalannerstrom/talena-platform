from __future__ import annotations

from typing import Any

from apps.processes.purpose_utils import (
    normalize_purpose_key,
)


PURPOSE_LABELS = {
    "hiring": "Recruitment",
    "recruitment": "Recruitment",

    "role_match": "Role matching",
    "internal_role_match": "Role matching",

    "leadership_potential": "Leadership potential",
    "leader_development": "Leadership development",

    "employee_development": "Employee development",
    "career_path": "Career development",

    "onboarding": "Onboarding",
    "team_development": "Team development",

    "reorganisation": "Reorganisation",
    "reorganization": "Reorganisation",

    "flexible": "General insights",
    "unsure": "General insights",
    "general": "General insights",
}


NO_CONTEXT_TEXT = (
    "No additional process context has been added."
)


def get_process_purpose_key(process) -> str:
    """
    Return Talena's normalised purpose key.
    """

    return normalize_purpose_key(
        getattr(process, "purpose", "") or ""
    )


def get_process_purpose_label(process) -> str:
    """
    Return one shared human-readable purpose label for all AI modules.
    """

    purpose_key = get_process_purpose_key(process)

    if purpose_key in PURPOSE_LABELS:
        return PURPOSE_LABELS[purpose_key]

    if hasattr(process, "get_purpose_display"):
        display_value = process.get_purpose_display()

        if display_value:
            return display_value

    return purpose_key or "General insights"


def get_process_context(
    process,
) -> tuple[str, dict[str, Any]]:
    """
    Return the context saved for the process's current purpose.

    Important:
    Context saved for another purpose must not silently be supplied
    to the AI after the process purpose changes.
    """

    if getattr(process, "is_historical", False):
        return (
            (
                "This is a historical profile. "
                "No original process context is available."
            ),
            {},
        )

    context_object = getattr(
        process,
        "role_context",
        None,
    )

    if not context_object:
        return NO_CONTEXT_TEXT, {}

    purpose_key = get_process_purpose_key(process)
    context_text = ""

    # Prefer the version explicitly saved for the active purpose.
    if hasattr(
        context_object,
        "get_context_for_purpose",
    ):
        saved_context = (
            context_object.get_context_for_purpose(
                purpose_key
            )
        )

        if saved_context is not None:
            context_text = (
                saved_context.get("context_text")
                or ""
            ).strip()

        elif context_object.purpose_data:
            # Context versions exist, but none has been saved for
            # the active purpose. Do not leak another purpose's context.
            context_text = ""

        elif hasattr(
            context_object,
            "get_current_context_text",
        ):
            # Backwards compatibility for old processes that have not
            # yet stored purpose-specific context.
            context_text = (
                context_object.get_current_context_text()
                or ""
            ).strip()

    elif hasattr(
        context_object,
        "get_current_context_text",
    ):
        context_text = (
            context_object.get_current_context_text()
            or ""
        ).strip()

    else:
        context_text = (
            getattr(
                context_object,
                "context_text",
                "",
            )
            or ""
        ).strip()

    if not context_text:
        return NO_CONTEXT_TEXT, {}

    return (
        context_text,
        {
            "context_text": context_text,
        },
    )


def build_shared_ai_context(
    owner,
) -> dict[str, Any]:
    """
    Build the common contextual foundation used by Talena's
    candidate AI functions.

    Owner may be a TestInvitation or another candidate result owner
    with candidate and process attributes.
    """

    candidate = owner.candidate
    process = owner.process

    context_text, context_data = (
        get_process_context(process)
    )

    candidate_name = " ".join(
        part.strip()
        for part in (
            candidate.first_name or "",
            candidate.last_name or "",
        )
        if part and part.strip()
    )

    return {
        "candidate": candidate,
        "candidate_name": (
            candidate_name
            or candidate.email
        ),
        "candidate_first_name": (
            candidate.first_name
            or "The candidate"
        ),

        "process": process,
        "purpose_key": (
            get_process_purpose_key(process)
        ),
        "purpose_label": (
            get_process_purpose_label(process)
        ),

        "context_text": context_text,
        "context_data": context_data,
        "has_context": bool(context_data),

        "is_historical": bool(
            getattr(
                process,
                "is_historical",
                False,
            )
        ),
    }