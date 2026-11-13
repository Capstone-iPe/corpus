"""Split a corpus document into the chunks the index stores."""

from __future__ import annotations

import math
import os
import re
from pathlib import Path

# Defaults match Assignment 05 / Track B pack sizing. Override for local experiments.
CHUNK = int(os.environ.get("ONB_CHUNK", "800"))
OVERLAP = int(os.environ.get("ONB_OVERLAP", "120"))
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
TOKEN = re.compile(r"[a-z0-9§]+(?:-[a-z0-9§]+)*")
HEADER_ROW = re.compile(
    r"^\|\s*(?:|Document ID|Version|Status|Classification|Owner|Effective|Review|"
    r"Applies to|Related|Audience|From|Date|To)\s*\|.*$",
    re.M,
)
TABLE_RULE = re.compile(r"^\|[\s|:-]+\|\s*$", re.M)
BOILERPLATE = re.compile(
    r"^iPe \(India Pay\) is (?:a )?fictional.*$|^---\s*$|The issue is: .*?$",
    re.M,
)
NOT_IN_FORCE_STATUS = re.compile(r"^\|\s*Status\s*\|[^|\n]*not in force", re.I | re.M)


def chunk_text(text: str) -> list[str]:
    if len(text) <= CHUNK:
        return [text]
    step = CHUNK - OVERLAP
    pieces = []
    start = 0
    while start < len(text):
        pieces.append(text[start : start + CHUNK])
        if start + CHUNK >= len(text):
            break
        start += step
    return pieces


def expected_chunks(text: str) -> int:
    if len(text) <= CHUNK:
        return 1
    return 1 + math.ceil((len(text) - CHUNK) / (CHUNK - OVERLAP))


def document_id(text: str, path: Path) -> str:
    for line in text.splitlines():
        if "Document ID" not in line or "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == "Document ID" and cells[1]:
            return cells[1]
    return path.stem


def title(text: str) -> str:
    headings = [line[2:].strip() for line in text.splitlines()[:4] if line.startswith("# ")]
    if len(headings) >= 2:
        return headings[1]
    return headings[0] if headings else ""


def clean(text: str) -> str:
    """Drop the metadata table and the sentences every memo repeats."""
    text = HEADER_ROW.sub("", text)
    text = TABLE_RULE.sub("", text)
    text = BOILERPLATE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def in_force(text: str, path: Path) -> bool:
    return "not-in-force" not in path.parts and not NOT_IN_FORCE_STATUS.search(text)


def load_chunks(corpus: Path) -> list[dict]:
    documents = corpus / "corpus"
    files = sorted(path for path in documents.rglob("*.md") if path.is_file())
    rows = []
    for path in files:
        rows.extend(_rows(path, corpus, documents))
    return rows


def _rows(path: Path, corpus: Path, documents: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(corpus).as_posix()
    pieces = chunk_text(text)
    if len(pieces) != expected_chunks(text):
        raise RuntimeError(f"chunk count drifted for {relative}")
    doc_id = document_id(text, path)
    heading = title(text)
    folder = path.relative_to(documents).parts[0]
    force = in_force(text, path)
    return [_row(doc_id, relative, folder, piece, heading, force) for piece in pieces]


def _row(doc_id: str, relative: str, folder: str, piece: str, heading: str, force: bool) -> dict:
    return {
        "document_id": doc_id,
        "path": relative,
        "folder": folder,
        "text": piece,
        "search_text": f"{doc_id}\n{heading}\n{clean(piece)}",
        "in_force": force,
    }


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def search_text(row: dict) -> str:
    return row.get("search_text") or row["text"]
