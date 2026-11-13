"""Chunk, embed, and search the policy corpus."""

from __future__ import annotations

import argparse
import json
import logging
import os
from collections import defaultdict
from pathlib import Path

from onb_corpus.chunks import load_chunks, search_text, tokens
from onb_corpus.config import docs_root, embedding_model, index_path
from onb_corpus.embed import embed_texts

RRF_K = 60
POOL = 20

TIER_BONUS = {
    "policy": 0.4,
    "annex": 0.4,
    "circulars": 0.4,
    "faq": 0.3,
    "handbook": 0.1,
}

log = logging.getLogger("onb_corpus")


def prefer_held(hits: list[dict], held_by_id: dict[str, dict]) -> list[dict]:
    """Use the chunk that carries the held line when the same document has one."""
    return [held_by_id.get(str(row.get("document_id") or ""), row) for row in hits]


def build(corpus: Path, out: Path) -> None:
    import numpy as np

    rows = load_chunks(corpus)
    print(f"embedding {len(rows)} chunks with {embedding_model()}")
    # Stream texts so we do not hold two full copies while embedding.
    texts = [search_text(row) for row in rows]
    vectors = embed_texts(texts)
    del texts
    out.mkdir(parents=True, exist_ok=True)
    with (out / "chunks.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    np.save(out / "vectors.npy", vectors)
    documents = len({row["path"] for row in rows})
    held_back = sum(1 for row in rows if not row["in_force"])
    print(f"documents {documents}")
    print(f"chunks {len(rows)}")
    print(f"not-in-force chunks {held_back}")
    print(f"wrote {out}")


def load_index(index: Path) -> tuple[list[dict], object]:
    import numpy as np

    rows = [
        json.loads(line)
        for line in (index / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    # mmap avoids a second full copy of the matrix in RAM.
    vectors = np.load(index / "vectors.npy", mmap_mode="r")
    if len(rows) != len(vectors):
        raise RuntimeError("chunks.jsonl and vectors.npy are different lengths")
    return rows, vectors


def merge(
    vector_order: list[int],
    keyword_order: list[int],
    bonus: list[float] | None = None,
) -> list[int]:
    scores: dict[int, float] = {}
    for order in (vector_order, keyword_order):
        for rank, row_id in enumerate(order):
            scores[row_id] = scores.get(row_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    if bonus:
        for row_id in scores:
            scores[row_id] += bonus[row_id] / (RRF_K + 1)
    return sorted(scores, key=lambda row_id: scores[row_id], reverse=True)


def tier_bonus(rows: list[dict]) -> list[float]:
    return [TIER_BONUS.get(str(row.get("folder") or ""), 0.0) for row in rows]


def one_per_document(rows: list[dict], k: int) -> list[dict]:
    seen: set[str] = set()
    found = []
    for row in rows:
        if row["document_id"] in seen:
            continue
        seen.add(row["document_id"])
        found.append(row)
        if len(found) == k:
            break
    return found


def _inverted(rows: list[dict]) -> dict[str, list[int]]:
    """Compact term → row-id posting lists (lighter than BM25Okapi on 512Mi)."""
    postings: dict[str, list[int]] = defaultdict(list)
    for row_id, row in enumerate(rows):
        seen: set[str] = set()
        for term in tokens(search_text(row)):
            if term in seen:
                continue
            seen.add(term)
            postings[term].append(row_id)
    return dict(postings)


def _keyword_order(query: str, postings: dict[str, list[int]], n_rows: int) -> list[int]:
    scores = [0.0] * n_rows
    for term in tokens(query):
        for row_id in postings.get(term, ()):
            scores[row_id] += 1.0
    return sorted(range(n_rows), key=lambda i: scores[i], reverse=True)


MODES = ("dense", "keyword", "hybrid", "hybrid_rerank")


class Index:
    """In-process hybrid search over a built index."""

    def __init__(self, index: Path | None = None, rerank: bool = False) -> None:
        import numpy as np

        path = index or index_path()
        self.rows, self.vectors = load_index(path)
        self.postings = _inverted(self.rows)
        self.bonus = tier_bonus(self.rows)
        self.document_ids = {row["document_id"] for row in self.rows if row["in_force"]}
        held: dict[str, dict] = {}
        for row in self.rows:
            doc_id = str(row.get("document_id") or "")
            if doc_id and doc_id not in held and "## Held" in str(row.get("text") or ""):
                held[doc_id] = row
        self.held_by_id = held
        self._want_rerank = rerank
        self.reranker = None
        self.np = np

    def _ensure_reranker(self):
        if self.reranker is None and self._want_rerank:
            self.reranker = _reranker()
            if self.reranker is None:
                self._want_rerank = False
        return self.reranker

    def search(self, query: str, k: int = 4, mode: str = "hybrid") -> list[dict]:
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")
        n = len(self.rows)
        if mode == "keyword":
            order = _keyword_order(query, self.postings, n)
        elif mode == "dense":
            query_vector = embed_texts([query])[0]
            order = self.np.argsort(-(self.vectors @ query_vector)).tolist()
        else:
            query_vector = embed_texts([query])[0]
            vector_order = self.np.argsort(-(self.vectors @ query_vector)).tolist()
            keyword_order = _keyword_order(query, self.postings, n)
            order = merge(vector_order, keyword_order, self.bonus)
        pool = []
        for row_id in order:
            row = self.rows[row_id]
            if row["in_force"]:
                pool.append(row)
            if len(pool) == POOL:
                break
        if mode == "hybrid_rerank":
            reranker = self._ensure_reranker()
            if reranker is not None:
                scores = reranker.predict([(query, search_text(row)) for row in pool])
                ranked = sorted(range(len(pool)), key=lambda i: float(scores[i]), reverse=True)
                pool = [pool[i] for i in ranked]
        found = one_per_document(pool, k)
        found = prefer_held(found, self.held_by_id)
        log.info("search[%s] %s", mode, [row["document_id"] for row in found])
        return found


def _reranker():
    try:
        from sentence_transformers import CrossEncoder
        from onb_corpus.chunks import RERANK_MODEL

        # Local eval may download once; Render never installs this extra.
        local_only = os.environ.get("RERANK_LOCAL_ONLY", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        return CrossEncoder(RERANK_MODEL, local_files_only=local_only)
    except Exception as exc:
        log.info("no reranker (%s)", exc)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Index the policy corpus and search it.")
    commands = parser.add_subparsers(dest="command", required=True)

    build_command = commands.add_parser("build")
    build_command.add_argument("--corpus", type=Path, default=docs_root())
    build_command.add_argument("--out", type=Path, default=index_path())

    search_command = commands.add_parser("search")
    search_command.add_argument("query")
    search_command.add_argument("--index", type=Path, default=index_path())
    search_command.add_argument("--k", type=int, default=5)
    search_command.add_argument("--mode", choices=MODES, default="hybrid")

    args = parser.parse_args()
    if args.command == "build":
        build(args.corpus, args.out)
        return
    want_rerank = args.mode == "hybrid_rerank"
    for row in Index(args.index, rerank=want_rerank).search(args.query, args.k, mode=args.mode):
        print(f"{row['document_id']}  {row['path']}")


if __name__ == "__main__":
    main()
