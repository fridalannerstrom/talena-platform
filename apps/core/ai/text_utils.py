# apps/core/ai/text_utils.py
from typing import List

def chunk_text(text: str, max_chars: int = 1200) -> List[str]:
    """
    Very simple chunker: splits by paragraphs first, then falls back to hard splits.
    """
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for p in paragraphs:
        if len(current) + len(p) + 2 <= max_chars:
            current = f"{current}\n\n{p}".strip() if current else p
        else:
            if current:
                chunks.append(current)
            # If a single paragraph is too large, hard-split it
            while len(p) > max_chars:
                chunks.append(p[:max_chars])
                p = p[max_chars:]
            current = p

    if current:
        chunks.append(current)

    return chunks