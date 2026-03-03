import os
from pinecone import Pinecone


def get_pinecone_index():
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")

    if not api_key:
        raise ValueError("Missing PINECONE_API_KEY environment variable")
    if not index_name:
        raise ValueError("Missing PINECONE_INDEX_NAME environment variable")

    pc = Pinecone(api_key=api_key)
    return pc.Index(index_name)