from .openai_client import (
    get_openai_client,
    get_chat_model,
)

from .rag import retrieve_context

from .language import (
    get_ai_system_language_instruction,
    normalize_ai_language,
)


def ask_ai(
    message: str,
    scope: str = "base",
    top_k: int = 5,
    *,
    language_code: str = "en",
) -> str:
    language_code = normalize_ai_language(
        language_code
    )

    client = get_openai_client()

    if scope == "both":
        ctx_base = retrieve_context(
            message,
            top_k=top_k,
            kind="base",
        )

        ctx_tq = retrieve_context(
            message,
            top_k=top_k,
            kind="tq",
        )

        context = "\n\n".join(
            context_part
            for context_part in (
                ctx_base,
                ctx_tq,
            )
            if context_part
        )

    else:
        context = retrieve_context(
            message,
            top_k=top_k,
            kind=scope,
        )

    system_prompt = (
        "You are an AI component inside Talena. "
        "Answer the user's question using the available "
        "Talena context where relevant. "
        f"{get_ai_system_language_instruction(language_code)}"
    )

    user_prompt = f"""
TALENA CONTEXT

{context or "No additional context available."}


USER MESSAGE

{message}
""".strip()

    response = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.2,
    )

    return (
        response.choices[0].message.content
        or ""
    )