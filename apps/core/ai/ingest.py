import hashlib
from typing import List
from .rag import embed_text
from .pinecone_client import get_pinecone_index

def chunk_text(text: str, max_chars: int = 1200) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+max_chars])
        i += max_chars
    return chunks


def upsert_document(
    title: str,
    text: str,
    source: str,
    tags: str = "",
    namespace: str = "",
    doc_id: str = "",
    max_chars: int = 1200,
    kind: str = "base",   # <- NY
) -> List[str]:
    index = get_pinecone_index()
    chunks = chunk_text(text, max_chars=max_chars)

    ids = []
    vectors = []
    for idx, chunk in enumerate(chunks):
        chunk_hash = hashlib.md5(chunk.encode("utf-8")).hexdigest()[:10]
        vector_id = f"{doc_id}-{idx}-{chunk_hash}" if doc_id else f"{idx}-{chunk_hash}"

        ids.append(vector_id)
        vectors.append({
            "id": vector_id,
            "values": embed_text(chunk),
            "metadata": {
                "text": chunk,
                "title": title,
                "source": source,
                "tags": tags,
                "doc_id": doc_id,
                "chunk_index": idx,
            }
        })

    if vectors:
        if namespace:
            index.upsert(vectors=vectors, namespace=namespace)
        else:
            index.upsert(vectors=vectors)

    return ids