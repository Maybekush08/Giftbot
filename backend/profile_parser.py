# backend/profile_parser.py

import json
from typing import Any, Dict

from .llm import llm_json

SYSTEM_PROFILE_EXTRACTOR = """
You are a strict JSON extractor. Convert the user's gifting request into a compact profile JSON.

Return ONLY valid JSON with these keys:
- relationship: string or ""
- age: number or null
- personality: string or ""
- interests: string or ""
- occasion: string or ""
- budget_usd: number or null
- exclude_ideas: array of strings (can be empty)
- extra: string or ""

Rules:
- If a field is missing, return "" or null (as specified).
- Parse "no-go" and "avoid" into exclude_ideas (e.g., "clothes are a no-go" -> ["clothes"]).
- budget_usd must be a number (e.g., "$50 max" -> 50).
"""

def profile_from_prompt(prompt: str) -> Dict[str, Any]:
    raw = llm_json(SYSTEM_PROFILE_EXTRACTOR, prompt)

    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    profile = {
        "relationship": data.get("relationship", "") or "",
        "age": data.get("age", None),
        "personality": data.get("personality", "") or "",
        "interests": data.get("interests", "") or "",
        "occasion": data.get("occasion", "") or "",
        "budget_usd": data.get("budget_usd", None),
        "exclude_ideas": data.get("exclude_ideas", []) or [],
        "extra": data.get("extra", "") or "",
    }

    # Normalizing exclude ideas to clean strings
    cleaned = []
    for x in profile["exclude_ideas"]:
        if isinstance(x, str):
            s = x.strip()
            if s:
                cleaned.append(s)
    profile["exclude_ideas"] = cleaned

    return profile
