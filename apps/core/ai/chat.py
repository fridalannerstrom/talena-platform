from .openai_client import get_openai_client, get_chat_model
from .rag import retrieve_context


def ask_ai(message: str, scope: str = "base", top_k: int = 5) -> str:
    client = get_openai_client()

    if scope == "both":
        ctx_base = retrieve_context(message, top_k=top_k, kind="base")
        ctx_tq = retrieve_context(message, top_k=top_k, kind="tq")
        context = "\n\n".join([c for c in [ctx_base, ctx_tq] if c])
    else:
        context = retrieve_context(message, top_k=top_k, kind=scope)

    user_prompt = f"""
You are a helpful assistant inside Talena.

Use the provided context if relevant. If context is empty or irrelevant, answer normally.

Context:
{context}

User message:
{message}
""".strip()

    resp = client.chat.completions.create(
        model=get_chat_model(),
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""