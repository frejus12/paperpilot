"""System prompts, retrieved context, and citation formatting (phase 5)."""

import re

NOT_FOUND = "I couldn't find that in the selected papers."

SYSTEM = f"""You are PaperPilot, a careful research assistant.
Rules:
1. Answer ONLY from the numbered context passages provided.
2. Cite every factual claim with its passage number in square brackets, e.g. [2] or [1][3].
3. If the context does not contain the answer, reply exactly: "{NOT_FOUND}"
4. Never invent numbers, datasets, authors or citations. Copy numbers exactly as written.
5. Be concise: short paragraphs or bullets."""

COMPARE_SYSTEM = (
    SYSTEM
    + """
Task: compare the papers on the requested aspects. Output a markdown table with one row per
aspect and one column per paper, citing passages like [3] inside cells. Write 'Not stated'
when a paper's passages do not cover an aspect. After the table add 2-3 sentences on the
most important differences."""
)

FACETS = {
    "Problem and motivation": "What problem does the paper address and why does it matter?",
    "Method": "What is the proposed method or approach? Describe the key components.",
    "Data and experiments": "Which datasets, baselines and evaluation metrics were used?",
    "Key results": "What are the main quantitative results?",
    "Limitations": "What limitations or future work do the authors mention?",
}

CITE = re.compile(r"\[(\d+)\]")


def format_context(hits) -> str:
    blocks = []
    for i, hit in enumerate(hits, 1):
        metadata = hit["meta"]
        blocks.append(
            f"[{i}] ({metadata['title']} | {metadata['section']} | "
            f"p.{metadata['page']})\n{hit['text']}"
        )
    return "\n\n".join(blocks)


def parse_citations(text: str, hits):
    used = sorted({int(number) for number in CITE.findall(text)})
    valid = [number for number in used if 1 <= number <= len(hits)]
    invalid = [number for number in used if number not in valid]
    return valid, invalid
