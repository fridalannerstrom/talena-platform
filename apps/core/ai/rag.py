from typing import List
from .openai_client import get_openai_client, get_embed_model
from .pinecone_client import get_pinecone_index


def embed_text(text: str) -> List[float]:
    client = get_openai_client()
    res = client.embeddings.create(
        model=get_embed_model(),
        input=text,
    )
    return res.data[0].embedding


def retrieve_context(query: str, top_k: int = 5, kind: str = "base") -> str:
    index = get_pinecone_index(kind=kind)
    vector = embed_text(query)

    res = index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
    )

    # Pinecone SDK kan ge objekt/dict-liknande struktur
    matches = getattr(res, "matches", None) or res.get("matches", [])
    chunks = []

    for m in matches:
        md = getattr(m, "metadata", None) or m.get("metadata", {}) or {}
        text = md.get("text") or md.get("content") or ""
        if text:
            chunks.append(text.strip())

    return "\n\n".join(chunks)