"""Offline-first Streamlit review surface for the read-only Threads demo."""

import json
import os
from pathlib import Path
from urllib.parse import urlencode

from rdsa import config
from rdsa.classifier import classify
from rdsa.extractor import extract
from rdsa.matcher import load_inventory, match
from rdsa.notifier import format_card
from rdsa.scorer import score
from rdsa.threads_client import ThreadsClient

MAX_RESULTS = 10
SCOPES = "threads_basic,threads_keyword_search"
ROOT = Path(__file__).resolve().parent


def _truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def live_enabled():
    return _truthy(os.getenv("THREADS_LIVE_ENABLED", config.THREADS_LIVE_ENABLED))


def validate_config(limit=None):
    """Return clear configuration errors; never returns or prints secrets."""
    errors = []
    if limit is not None and int(limit) > MAX_RESULTS:
        errors.append("Live searches are capped at 10 results.")
    if live_enabled():
        for name in ("THREADS_APP_ID", "THREADS_APP_SECRET", "THREADS_REDIRECT_URI"):
            if not os.getenv(name, getattr(config, name, "")):
                errors.append(f"{name} is required when live mode is enabled.")
    return errors


def redact_token(value):
    """Safe display helper; intentionally never returns the supplied token."""
    if not value:
        return ""
    return "[redacted]"


def _synthetic_posts():
    with (ROOT / "data" / "synthetic_posts.json").open(encoding="utf-8") as fh:
        return [item["post"] for item in json.load(fh)["posts"]]


def process_posts(posts, now=None, inventory_path=None):
    inventory = load_inventory(inventory_path or config.INVENTORY_CSV)
    results = []
    for post in posts:
        lead = extract(post, now=now)
        score(lead, now=now)
        classify(lead)
        if lead.lead_class in ("hot_lead", "qualified_lead"):
            lead.matched_inventory = match(lead, inventory, limit=3)
        results.append({"post": post, "lead": lead, "card": format_card(lead)})
    return results


def _synthetic_filter(posts, keyword="", location=""):
    terms = [term.strip().lower() for term in (keyword, location) if term and term.strip()]
    return [post for post in posts if not terms or all(term in post.get("text", "").lower() for term in terms)]


def run_search(keyword="", location="", mode="Synthetic", limit=10, token=None, now=None):
    """Run the same processing flow used by the UI; safe and network-free in Synthetic mode."""
    mode = str(mode).strip().lower()
    limit = min(int(limit), MAX_RESULTS)
    if mode == "synthetic":
        posts = _synthetic_filter(_synthetic_posts(), keyword, location)
        return {"status": "ok", "message": "Synthetic mode — no credentials or network used.", "results": process_posts(posts[:limit], now=now)}
    if not live_enabled():
        return {"status": "disabled", "message": "Live mode disabled. Set THREADS_LIVE_ENABLED=true to enable it.", "results": []}
    errors = validate_config(limit)
    token = token or os.getenv("THREADS_USER_TOKEN", config.THREADS_USER_TOKEN)
    if not token:
        return {"status": "needs_connection", "message": "Connect Threads first to run a live search.", "results": []}
    if errors:
        return {"status": "invalid_config", "message": " ".join(errors), "results": []}
    posts = ThreadsClient(token).search(keyword, location=location or None, limit=limit)
    return {"status": "ok", "message": "Live search complete.", "results": process_posts(posts[:MAX_RESULTS], now=now)}


def authorization_url():
    params = {"client_id": os.getenv("THREADS_APP_ID", config.THREADS_APP_ID), "redirect_uri": os.getenv("THREADS_REDIRECT_URI", config.THREADS_REDIRECT_URI), "scope": SCOPES, "response_type": "code"}
    return "https://threads.net/oauth/authorize?" + urlencode(params)


def exchange_code(code):
    """Exchange OAuth code server-side; the token is returned only to session state."""
    import requests
    response = requests.request("POST", "https://graph.threads.net/oauth/access_token", data={"client_id": os.getenv("THREADS_APP_ID", config.THREADS_APP_ID), "client_secret": os.getenv("THREADS_APP_SECRET", config.THREADS_APP_SECRET), "grant_type": "authorization_code", "redirect_uri": os.getenv("THREADS_REDIRECT_URI", config.THREADS_REDIRECT_URI), "code": code}, timeout=30)
    response.raise_for_status()
    short_lived = response.json().get("access_token", "")
    if not short_lived:
        return ""
    long_lived = requests.request("GET", "https://graph.threads.net/access_token", params={"grant_type": "th_exchange_token", "client_secret": os.getenv("THREADS_APP_SECRET", config.THREADS_APP_SECRET), "access_token": short_lived}, timeout=30)
    long_lived.raise_for_status()
    return long_lived.json().get("access_token", "")


def _render():
    import streamlit as st

    st.set_page_config(page_title="Rental Demand Signal — App Review", layout="wide")
    st.title("Rental Demand Signal — App Review Demo")
    st.caption("A human-triggered review surface for public Threads content only.")
    with st.expander("App Overview", expanded=True):
        st.write("This demo extracts rental requirements, scores and classifies public posts, then matches qualified demand to sample inventory.")
        st.info("Public content only. No automatic contact: a human reviews any result before taking action.")
        st.markdown("[Privacy Policy Draft](docs/review/PRIVACY_POLICY_DRAFT.md) · [Data Deletion Instructions](docs/review/DATA_DELETION_INSTRUCTIONS.md)")
    with st.expander("Threads Connection", expanded=True):
        connected = bool(st.session_state.get("threads_user_token"))
        st.write("Authentication status: **connected**" if connected else "Authentication status: **not connected**")
        st.write(f"Granted scopes: {SCOPES} (token hidden)")
        if st.button("Connect Threads"):
            if not validate_config(): st.link_button("Open Threads Authorization Window", authorization_url())
            else: st.error(" ".join(validate_config()))
        if connected and st.button("Disconnect / clear local session"):
            st.session_state.pop("threads_user_token", None); st.rerun()
        code = st.query_params.get("code")
        if code and not connected:
            if token := exchange_code(code): st.session_state["threads_user_token"] = token; st.rerun()
    with st.expander("Search Form", expanded=True):
        keyword = st.text_input("Keyword", placeholder="Leave blank for all synthetic posts")
        keyword = st.selectbox("Keyword suggestions", [""] + config.KEYWORDS, index=0) if not keyword else keyword
        location = st.text_input("Location", placeholder="Leave blank for all synthetic posts")
        location = st.selectbox("Location suggestions", [""] + config.LOCATIONS, index=0) if not location else location
        limit = st.slider("Maximum results", 1, MAX_RESULTS, 10)
        mode = st.radio("Source mode", ["Synthetic", "Live"], horizontal=True)
        if mode == "Live" and not live_enabled(): st.warning("Live mode disabled. No network/API call will be made.")
        if st.button("Run Search"):
            outcome = run_search(keyword, location, mode, limit, st.session_state.get("threads_user_token"))
            st.session_state["last_search"] = outcome
    outcome = st.session_state.get("last_search")
    if outcome:
        st.subheader("Search Results"); st.write(outcome["message"])
        for item in outcome["results"]:
            lead = item["lead"]
            with st.expander(f"{lead.lead_class} · {lead.lead_score}/100 · @{lead.author_username}"):
                st.write(lead.raw_text); st.markdown(f"Source: [{lead.source_url}]({lead.source_url})")
                st.write({"timestamp": lead.post_timestamp, "location": lead.desired_location, "type": lead.property_type, "bedrooms": lead.bedrooms, "budget": [lead.budget_min, lead.budget_max], "dates": lead.move_in_date, "duration": lead.rental_duration, "requirements": lead.special_requirements})
                st.write("Score explanation:", lead.score_breakdown); st.write("Inventory matches:", lead.matched_inventory); st.code(item["card"])
    with st.expander("Safety & Data Handling", expanded=True):
        st.info("This app never replies, comments, follows, publishes, sends DMs, or contacts anyone. It temporarily processes public post fields only: text, permalink, username, timestamp, and id.")
        if st.button("Delete session data"):
            st.session_state.clear(); st.rerun()


if __name__ == "__main__":
    _render()
