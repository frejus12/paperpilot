"""PDF extraction and text chunking utilities (phases 1-2)."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from .config import settings


HEADING = re.compile(
    r"^\s*(\d+(\.\d+)*\.?\s+)?"
    r"(abstract|introduction|related work|background|"
    r"methods?|methodology|approach|experiments?|results|discussion|limitations|"
    r"conclusions?|references)\s*$",
    re.IGNORECASE,
)


@dataclass
class Chunk:
    chunk_id: str
    paper_id: str
    title: str
    section: str
    page: int
    text: str


def file_id(path: str) -> str:
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:12]


def clean(text: str) -> str:
    text = text.replace("-\n", "")  # de-hyphenate line breaks
    text = re.sub(r"\s*\n\s*", " ", text)  # newlines -> spaces
    return re.sub(r"\s{2,}", " ", text).strip()


def guess_title(doc, path: str) -> str:
    metadata_title = ((doc.metadata or {}).get("title") or "").strip()
    if len(metadata_title) > 8:
        return metadata_title

    for blk in doc[0].get_text("blocks", sort=True):
        text = clean(blk[4])
        if blk[6] == 0 and 15 < len(text) < 200:
            return text
    return Path(path).stem


def parse_pdf(path: str):
    """Return (paper_id, title, [(paragraph_text, section, page_number), ...])."""
    doc = fitz.open(path)
    pid, title = file_id(path), guess_title(doc, path)
    paragraphs, section, done = [], "Front Matter", False

    for pno, page in enumerate(doc, start=1):
        for blk in page.get_text("blocks", sort=True):
            txt, kind = blk[4], blk[6]
            if kind != 0:  # 0 = text block, 1 = image block
                continue

            txt = clean(txt)
            match = HEADING.match(txt)
            if match:
                section = match.group(3).title()
                if section == "References":
                    done = True
                    break
                continue

            if len(txt) >= 25:  # drop page numbers, stray labels
                paragraphs.append((txt, section, pno))
        if done:
            break

    return pid, title, paragraphs


def chunk(paragraphs, pid, title, target=None, overlap=None):
    target = target or settings.chunk_words
    overlap = overlap or settings.chunk_overlap
    chunks, buf, new, page, section = [], [], 0, None, None

    def flush(keep_tail=True):
        nonlocal buf, new, page
        if new > 0 and len(buf) >= 30:  # 'new' avoids emitting a pure-overlap chunk
            n = len(chunks)
            chunks.append(Chunk(f"{pid}-{n}", pid, title, section, page, " ".join(buf)))
        buf = buf[-overlap:] if keep_tail else []
        new, page = 0, None

    for txt, sec, pno in paragraphs:
        if sec != section:  # new section: close the current chunk
            flush(keep_tail=False)
            section = sec
        words = txt.split()
        for i in range(0, len(words), target):
            piece = words[i : i + target]
            if buf and len(buf) + len(piece) > target:
                flush()
            if page is None:
                page = pno
            buf.extend(piece)
            new += len(piece)
    flush(keep_tail=False)
    return chunks


def ingest_pdf(path: str) -> list[Chunk]:
    pid, title, paragraphs = parse_pdf(path)
    return chunk(paragraphs, pid, title)
