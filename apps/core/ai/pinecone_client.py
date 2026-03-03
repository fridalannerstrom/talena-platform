import os
from pinecone import Pinecone


def _get_pc():
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("Missing PINECONE_API_KEY environment variable")
    return Pinecone(api_key=api_key)


def get_pinecone_index(kind: str = "base"):
    pc = _get_pc()

    if kind == "tq":
        index_name = os.getenv("PINECONE_INDEX_TQ")
        if not index_name:
            raise ValueError("Missing PINECONE_INDEX_TQ environment variable")
        return pc.Index(index_name)

    index_name = os.getenv("PINECONE_INDEX_BASE")
    if not index_name:
        raise ValueError("Missing PINECONE_INDEX_BASE environment variable")
    return pc.Index(index_name)