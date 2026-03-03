from typing import Iterable
from .openai_client import get_openai_client, get_chat_model
from .rag import retrieve_context


def stream_ai(message: str, scope: str = "base", top_k: int = 5) -> Iterable[str]:
    client = get_openai_client()

    # 1) Hämta context (RAG) först
    if scope == "both":
        ctx_base = retrieve_context(message, top_k=top_k, kind="base")
        ctx_tq = retrieve_context(message, top_k=top_k, kind="tq")
        context = "\n\n".join([c for c in [ctx_base, ctx_tq] if c])
    else:
        context = retrieve_context(message, top_k=top_k, kind=scope)

    prompt = f"""
You are a helpful assistant inside Talena.

Use the provided context if relevant. If context is empty or irrelevant, answer normally.

Context:
{context}

User message:
{message}
""".strip()

    # 2) Streama svaret från OpenAI
    stream = client.chat.completions.create(
        model=get_chat_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        stream=True,
    )

    for event in stream:
        delta = event.choices[0].delta
        if delta and delta.content:
            yield delta.content