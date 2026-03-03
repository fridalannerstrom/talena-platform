import os
from openai import OpenAI


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY environment variable")
    return OpenAI(api_key=api_key)


def get_chat_model() -> str:
    return os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def get_embed_model() -> str:
    return os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")