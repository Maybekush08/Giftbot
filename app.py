# app.py
# Centered profile form (no sidebar, no prompt box).
# Always shows gift ideas and message draft.
# Link behavior:
#   - Uses real per-item url fields if present
#   - Otherwise generates safe search links (Etsy / Pinterest / Web) from the idea title

from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import streamlit as st

from backend.recommender import generate_batch, generate_cards


st.set_page_config(page_title="GiftBot", page_icon="🎁", layout="wide")


def _init_state() -> None:
    defaults = {
        "recipient": "",
        "relationship": "",
        "age": None,
        "personality": "",
        "interests": "",
        "occasion": "",
        "budget": 50.0,
        "exclude_ideas_text": "",
        "exclude_ideas": [],
        "last_batch": None,
        "last_selected_ideas": None,
        "last_cards": None,
        "last_draft": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _parse_excludes(text: str) -> List[str]:
    if not text:
        return []
    parts = [p.strip() for p in text.split(",")]
    return [p for p in parts if p]


def _extract_selected_ideas(batch: Any) -> Any:
    if isinstance(batch, dict):
        return (
            batch.get("selected_ideas")
            or batch.get("ideas")
            or batch.get("results")
            or batch.get("selected")
            or []
        )
    return (
        getattr(batch, "selected_ideas", None)
        or getattr(batch, "ideas", None)
        or getattr(batch, "results", None)
        or getattr(batch, "selected", None)
        or []
    )


def _card_to_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}

    if isinstance(obj, dict):
        return obj

    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return obj.model_dump()
        except Exception:
            pass

    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return obj.dict()
        except Exception:
            pass

    if hasattr(obj, "__dict__"):
        try:
            return dict(obj.__dict__)
        except Exception:
            pass

    if isinstance(obj, str):
        return {"title": obj}

    return {"title": str(obj)}


def _pick_first(d: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for k in keys:
        if k in d and d[k] not in (None, "", [], {}):
            return d[k]
    return None


def _safe_external_url(url: Any) -> Optional[str]:
    if not isinstance(url, str):
        return None
    u = url.strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return None


def _extract_url_strict(d: Dict[str, Any]) -> Optional[str]:
    url_keys = [
        "url",
        "link",
        "href",
        "product_url",
        "page_url",
        "source_url",
        "canonical_url",
        "productLink",
        "sourceLink",
    ]
    for k in url_keys:
        safe = _safe_external_url(d.get(k))
        if safe:
            return safe
    return None


def _make_search_links(title: str, budget: Optional[float]) -> Dict[str, str]:
    # Keeping queries simple and reliable.
    q = title.strip()
    if budget not in (None, "", 0, 0.0):
        q = f"{q} under {int(float(budget))} dollars"
    enc = quote_plus(q)

    return {
        "Search Etsy": f"https://www.etsy.com/search?q={enc}",
        "Search Pinterest": f"https://www.pinterest.com/search/pins/?q={enc}",
        "Search Web": f"https://www.google.com/search?q={enc}",
    }


def _render_ideas(items: Any, budget: Optional[float], title_fallback: str = "Gift idea") -> None:
    if not items:
        st.info("No ideas to show yet.")
        return

    if not isinstance(items, list):
        items = [items]

    for idx, raw in enumerate(items, start=1):
        d = _card_to_dict(raw)

        title = _pick_first(d, ["title", "name", "idea", "headline", "gift"]) or title_fallback
        desc = _pick_first(d, ["description", "desc", "why", "summary", "details", "reason"])
        price = _pick_first(d, ["price", "price_usd", "cost"])
        source = _pick_first(d, ["source", "site", "provider"])

        url = _extract_url_strict(d)

        with st.container(border=True):
            st.subheader(f"{idx}. {title}")

            if desc:
                st.write(desc)

            meta_bits = []
            if price:
                meta_bits.append(f"**Price:** {price}")
            if source:
                meta_bits.append(f"**Source:** {source}")
            if meta_bits:
                st.write(" • ".join(meta_bits))

            if url:
                st.link_button("Open link", url)
            else:
                # Fallback: generated search links (Etsy/Pinterest/Web)
                links = _make_search_links(title, budget)
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.link_button("Search Etsy", links["Search Etsy"], use_container_width=True)
                with c2:
                    st.link_button("Search Pinterest", links["Search Pinterest"], use_container_width=True)
                with c3:
                    st.link_button("Search Web", links["Search Web"], use_container_width=True)


def _split_cards_and_draft(output: Any) -> Tuple[List[Any], str]:
    if output is None:
        return [], ""

    if isinstance(output, (tuple, list)) and len(output) == 2 and not isinstance(output[0], (str, bytes)):
        cards_part, draft_part = output
        cards_list = cards_part if isinstance(cards_part, list) else ([cards_part] if cards_part else [])
        draft_text = draft_part if isinstance(draft_part, str) else ""
        return cards_list, draft_text

    if isinstance(output, dict):
        cards = (
            output.get("cards")
            or output.get("gift_cards")
            or output.get("ideas")
            or output.get("results")
            or []
        )
        draft = (
            output.get("message_draft")
            or output.get("draft")
            or output.get("email")
            or output.get("message")
            or ""
        )
        cards_list = cards if isinstance(cards, list) else ([cards] if cards else [])
        draft_text = draft if isinstance(draft, str) else ""
        return cards_list, draft_text

    if isinstance(output, str):
        return [], output

    if isinstance(output, list):
        return output, ""

    return [output], ""


_init_state()

st.title("🎁 GiftBot")
st.caption("Profile-based gift recommendations (centered form).")

left, center, right = st.columns([1, 2, 1])

with center:
    st.subheader("Recipient Profile")

    with st.form("profile_form", clear_on_submit=False):
        st.text_input("Recipient name (optional)", key="recipient", placeholder="e.g., Priya")
        st.text_input("Relationship", key="relationship", placeholder="Sister, friend, partner...")
        st.number_input("Age", min_value=0, max_value=120, step=1, key="age")
        st.text_input("Personality", key="personality", placeholder="Playful, minimalist, sentimental...")
        st.text_input("Interests", key="interests", placeholder="Books, cooking, fitness...")
        st.text_input("Occasion", key="occasion", placeholder="Anniversary, birthday...")
        st.number_input("Budget (USD)", min_value=0.0, step=5.0, key="budget")
        st.text_input("No-go ideas (comma-separated)", key="exclude_ideas_text", placeholder="clothes, perfume, mugs")

        col_a, col_b = st.columns(2)
        with col_a:
            generate_clicked = st.form_submit_button("Generate ideas", use_container_width=True)
        with col_b:
            clear_clicked = st.form_submit_button("Clear results", use_container_width=True)

    if clear_clicked:
        st.session_state["last_batch"] = None
        st.session_state["last_selected_ideas"] = None
        st.session_state["last_cards"] = None
        st.session_state["last_draft"] = ""
        st.rerun()

    st.session_state["exclude_ideas"] = _parse_excludes(st.session_state.get("exclude_ideas_text", ""))

    if generate_clicked:
        budget_val = float(st.session_state.get("budget", 50.0) or 50.0)
        no_go_list = st.session_state.get("exclude_ideas", []) or []
        no_go_text = ", ".join(no_go_list)

        profile = SimpleNamespace(
            recipient=st.session_state.get("recipient", "") or "",
            relationship=st.session_state.get("relationship", "") or "",
            age=st.session_state.get("age", None),
            personality=st.session_state.get("personality", "") or "",
            interests=st.session_state.get("interests", "") or "",
            occasion=st.session_state.get("occasion", "") or "",
            budget=budget_val,
            budget_usd=budget_val,
            no_go=no_go_text,
            exclude_ideas=no_go_list,
            extra="",
            extra_notes="",
            prompt="",
        )

        with st.status("Generating ideas...", expanded=False):
            batch = generate_batch(profile, exclude_names=no_go_list, k=5)
            selected_ideas = _extract_selected_ideas(batch)
            output = generate_cards(profile, selected_ideas)
            cards, draft = _split_cards_and_draft(output)

        st.session_state["last_batch"] = batch
        st.session_state["last_selected_ideas"] = selected_ideas
        st.session_state["last_cards"] = cards
        st.session_state["last_draft"] = draft


st.subheader("Gift ideas")

budget_val = float(st.session_state.get("budget", 50.0) or 50.0)
cards = st.session_state.get("last_cards")
selected = st.session_state.get("last_selected_ideas")

if cards:
    _render_ideas(cards, budget=budget_val, title_fallback="Gift idea")
else:
    _render_ideas(selected, budget=budget_val, title_fallback="Gift idea")

draft = st.session_state.get("last_draft", "")
if isinstance(draft, str) and draft.strip():
    st.subheader("Message draft")
    st.text_area("Draft", value=draft, height=220)
