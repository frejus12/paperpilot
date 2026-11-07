from .config import settings
from .ingest import ingest_pdf
from .llm import complete
from .prompts import (
    COMPARE_SYSTEM,
    FACETS,
    NOT_FOUND,
    SYSTEM,
    format_context,
    parse_citations,
)
from .store import PaperStore

MIN_SCORE = 0.30


REWRITE_SYSTEM = (
    "Rewrite the user's last question as a standalone search query, resolving "
    "pronouns using the conversation. Output only the query, nothing else."
)


def standalone(history, question: str) -> str:
    if not history:
        return question

    convo = "\n".join(f"{role}: {text}" for role, text in history[-6:])
    return complete(REWRITE_SYSTEM, f"{convo}\nuser: {question}", max_tokens=80).strip()


class PaperPilot:
    def __init__(self):
        self.store = PaperStore()

    # ---- indexing -------------------------------------------------------------
    def add_pdf(self, path: str) -> dict:
        chunks = ingest_pdf(path)

        if not chunks:
            raise ValueError("No extractable text found. Is this a scanned PDF?")
        pid = chunks[0].paper_id
        if not self.store.has_paper(pid):
            self.store.add_chunks(chunks)
        return {"paper_id": pid, "title": chunks[0].title, "chunks": len(chunks)}

    # ---- question answering ---------------------------------------------------
    def ask(self, question: str, paper_ids=None, history=None) -> dict:
        query = standalone(history, question)
        hits = self.store.search(query, k=settings.top_k, paper_ids=paper_ids)
        hits = [h for h in hits if h["score"] >= MIN_SCORE]
        if not hits:
            return {
                "answer": NOT_FOUND,
                "sources": [],
                "invalid_citations": [],
                "query": query,
            }
        user = f"CONTEXT:\n{format_context(hits)}\n\nQUESTION: {question}"
        answer = complete(SYSTEM, user)
        _, invalid = parse_citations(answer, hits)
        return {
            "answer": answer,
            "sources": hits,
            "invalid_citations": invalid,
            "query": query,
        }

    # ---- summarization --------------------------------------------------------
    def summarize(self, paper_id: str) -> dict:
        sections = []
        for name, question in FACETS.items():
            hits = self.store.search(question, k=4, paper_ids=[paper_id])
            user = (
                f"CONTEXT:\n{format_context(hits)}\n\nQUESTION: {question}\n"
                "Answer in 2-4 sentences."
            )
            sections.append((name, complete(SYSTEM, user, max_tokens=500), hits))
        digest = "\n\n".join(f"{n}: {t}" for n, t, _ in sections)
        tldr = complete(
            "Write a 3-sentence TL;DR of a research paper from these notes. "
            "Do not include citation numbers.",
            digest,
            max_tokens=300,
        )
        return {"tldr": tldr, "sections": sections}

    # ---- comparison -----------------------------------------------------------
    def compare(self, paper_ids, aspects) -> dict:
        found = {}
        for aspect in aspects:
            for pid in paper_ids:  # per-paper retrieval = fair comparison
                for h in self.store.search(aspect, k=3, paper_ids=[pid]):
                    found[h["id"]] = h  # dict de-duplicates overlapping hits
        hits = list(found.values())
        titles = sorted({h["meta"]["title"] for h in hits})
        user = (
            f"CONTEXT:\n{format_context(hits)}\n\nPAPERS: {'; '.join(titles)}\n"
            f"ASPECTS: {', '.join(aspects)}\nProduce the comparison."
        )
        answer = complete(COMPARE_SYSTEM, user, max_tokens=1800)
        _, invalid = parse_citations(answer, hits)
        return {"answer": answer, "sources": hits, "invalid_citations": invalid}
