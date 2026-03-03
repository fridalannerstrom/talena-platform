import hashlib
from typing import List
from .rag import embed_text
from .pinecone_client import get_pinecone_index
import re
import unicodedata

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

def make_ascii_id(value: str) -> str:
    value = value or ""
    # ÅÄÖ -> A A O (och andra accenttecken -> “nära” ascii)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    # bara tillåt säkra tecken
    value = re.sub(r"[^a-zA-Z0-9\-_\.]", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "doc"


def upsert_document(
    title: str,
    text: str,
    source: str,
    tags: str = "",
    namespace: str = "",
    doc_id: str = "",
    max_chars: int = 1200,
    kind: str = "base",  # "base" eller "tq"
) -> List[str]:
    # ✅ Välj rätt index baserat på kind
    index = get_pinecone_index(kind)
    index = get_pinecone_index("tq")
    index.fetch(ids=["din-id-här"])

    chunks = chunk_text(text, max_chars=max_chars)

    ids = []
    vectors = []

    for idx, chunk in enumerate(chunks):
        chunk_hash = hashlib.md5(chunk.encode("utf-8")).hexdigest()[:10]
        safe_doc_id = make_ascii_id(doc_id) if doc_id else ""
        vector_id = f"{safe_doc_id}-{idx}-{chunk_hash}" if safe_doc_id else f"{idx}-{chunk_hash}"

        values = embed_text(chunk)

        # ✅ Skydd: om dimension inte matchar så vill vi faila direkt
        if not isinstance(values, list) or len(values) != 3072:
            raise ValueError(f"Embedding dimension {len(values)} does not match expected 3072")

        ids.append(vector_id)
        vectors.append({
            "id": vector_id,
            "values": values,
            "metadata": {
                "text": chunk,
                "title": title,
                "source": source,
                "tags": tags,
                "doc_id": doc_id,
                "chunk_index": idx,
            }
        })

    if not vectors:
        return []

    # ✅ Debug: så du ser i terminalen var den upsertar
    print(f"[PINECONE] Upserting {len(vectors)} vectors -> kind={kind}, namespace='{namespace or ''}', first_id={vectors[0]['id']}")

    # ✅ Upsert och logga svar
    if namespace:
        resp = index.upsert(vectors=vectors, namespace=namespace or "")
        print("PINECONE UPSERT RESPONSE:", resp)
    else:
        resp = index.upsert(vectors=vectors)

    print("[PINECONE] Upsert response:", resp)

    return ids