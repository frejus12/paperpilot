"""Streamlit user interface (phase 9)."""

import requests
import streamlit as st

from paperpilot.config import settings

st.set_page_config(page_title="PaperPilot", layout="wide")


@st.cache_resource
def get_http_session() -> requests.Session:
    return requests.Session()


API_URL = settings.api_url.rstrip("/")
API_TIMEOUT = 180
st.session_state.setdefault("history", [])
st.session_state.setdefault("indexed", set())


def api_request(method: str, path: str, **kwargs):
    try:
        response = get_http_session().request(
            method,
            f"{API_URL}{path}",
            timeout=API_TIMEOUT,
            **kwargs,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        detail = error.response.text if error.response is not None else str(error)
        raise RuntimeError(f"API request failed: {detail}") from error
    return response.json()


def show_sources(hits, invalid=()):
    if invalid:
        st.warning(
            f"Model cited passage(s) {list(invalid)} that were not "
            "retrieved. Verify manually."
        )
    for i, hit in enumerate(hits, 1):
        metadata = hit["meta"]
        label = (
            f"[{i}] {metadata['title'][:48]} | {metadata['section']} | "
            f"p.{metadata['page']} | score {hit['score']:.2f}"
        )
        with st.expander(label):
            st.write(hit["text"])


# ------------------------------- sidebar: library -------------------------------
with st.sidebar:
    st.header("Library")
    uploaded_files = (
        st.file_uploader("Add PDFs", type="pdf", accept_multiple_files=True) or []
    )
    for uploaded_file in uploaded_files:
        if uploaded_file.name in st.session_state.indexed:
            continue
        with st.spinner(f"Indexing {uploaded_file.name}..."):
            try:
                api_request(
                    "POST",
                    "/papers",
                    files={
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type or "application/pdf",
                        )
                    },
                )
                st.session_state.indexed.add(uploaded_file.name)
                st.success(f"Indexed {uploaded_file.name}")
            except RuntimeError as error:
                st.error(f"{uploaded_file.name}: {error}")

    try:
        papers = api_request("GET", "/papers")
    except RuntimeError as error:
        st.error(
            f"Cannot connect to the PaperPilot API at {API_URL}. "
            f"Start the API and try again. Details: {error}"
        )
        st.stop()

    titles = {paper["paper_id"]: paper["title"] for paper in papers}
    st.caption("Search scope")
    selected = [
        paper["paper_id"]
        for paper in papers
        if st.checkbox(paper["title"][:55], value=True, key=paper["paper_id"])
    ]

st.title("PaperPilot")
tab_ask, tab_sum, tab_cmp = st.tabs(["Ask", "Summarize", "Compare"])

# ------------------------------------ Ask ---------------------------------------
with tab_ask:
    for role, text in st.session_state.history:
        with st.chat_message(role):
            st.markdown(text)
    if question := st.chat_input("Ask about the selected papers..."):
        prior = list(st.session_state.history)
        st.session_state.history.append(("user", question))
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"), st.spinner("Searching and reading..."):
            try:
                result = api_request(
                    "POST",
                    "/ask",
                    json={
                        "question": question,
                        "paper_ids": selected or None,
                        "history": prior,
                    },
                )
            except RuntimeError as error:
                st.error(str(error))
            else:
                st.markdown(result["answer"])
                show_sources(result["sources"], result["invalid_citations"])
                st.session_state.history.append(("assistant", result["answer"]))

# ---------------------------------- Summarize -----------------------------------
with tab_sum:
    if not papers:
        st.info("Upload a paper in the sidebar to begin.")
    else:
        paper_id = st.selectbox("Paper", list(titles), format_func=lambda x: titles[x])
        if st.button("Generate summary"):
            with st.spinner("Reading the paper..."):
                try:
                    output = api_request("GET", f"/papers/{paper_id}/summary")
                except RuntimeError as error:
                    st.error(str(error))
                else:
                    st.subheader("TL;DR")
                    st.write(output["tldr"])
                    for name, text, hits in output["sections"]:
                        st.markdown(f"**{name}**")
                        st.write(text)
                        show_sources(hits)

# ----------------------------------- Compare ------------------------------------
with tab_cmp:
    aspects = st.text_input(
        "Aspects (comma-separated)",
        "problem, method, datasets, results, limitations",
    )
    if len(selected) < 2:
        st.info("Select at least two papers in the sidebar.")
    elif len(selected) > 5:
        st.info("Select no more than five papers to compare.")
    elif st.button("Compare papers"):
        with st.spinner("Comparing..."):
            try:
                result = api_request(
                    "POST",
                    "/compare",
                    json={
                        "paper_ids": selected,
                        "aspects": [
                            aspect.strip()
                            for aspect in aspects.split(",")
                            if aspect.strip()
                        ],
                    },
                )
            except RuntimeError as error:
                st.error(str(error))
            else:
                st.markdown(result["answer"])
                show_sources(result["sources"], result["invalid_citations"])
