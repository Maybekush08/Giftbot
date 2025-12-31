# backend/llm.py

import os
from typing import List, Any

from openai import OpenAI


# Pulling API key from env first, then Streamlit secrets if running under Streamlit
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

try:
    import streamlit as st
    OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY") or OPENAI_API_KEY
except Exception:
    pass

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY not set. Add it to .streamlit/secrets.toml "
        "or set it as an environment variable."
    )

# Model can be overridden via env var
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_client = OpenAI(api_key=OPENAI_API_KEY)


def llm_json(system: str, user: str) -> str:
    """Gets a JSON object response as a string."""
    resp = _client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        text={"format": {"type": "json_object"}},
    )
    return resp.output_text


def llm_text(system: str, user: str) -> str:
    """Gets a normal text response as a string."""
    resp = _client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.output_text


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embeds a list of strings and returns vectors."""
    # Using a dedicated embedding model env var if provided
    embed_model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    resp = _client.embeddings.create(
        model=embed_model,
        input=texts,
    )

    return [item.embedding for item in resp.data]
