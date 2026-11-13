"""Chunk, embed, and search the policy corpus."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from onb_corpus.chunks import RERANK_MODEL, load_chunks, search_text, tokens
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


def prefer_held(hits: list[dict], rows: list[dict]) -> list[dict]:
    """Use the chunk that carries the held line when the same document has one."""
    held: dict[str, dict] = {}
    for row in rows:
        document_id = str(row.get("document_id") or "")
        if document_id and document_id not in held and "## Held" in str(row.get("text") or ""):
            held[document_id] = row
    return [held.get(str(row.get("document_id") or ""), row) for row in hits]


def build(corpus: Path, out: Path) -> None:
    import numpy as np

    rows = load_chunks(corpus)
    print(f"embedding {len(rows)} chunks with {embedding_model()}")
    vectors = embed_texts([search_text(row) for row in rows])
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
    vectors = np.load(index / "vectors.npy")
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


class Index:
    """In-process hybrid search over a built index."""

    def __init__(self, index: Path | None = None, rerank: bool = True) -> None:
        from rank_bm25 import BM25Okapi
        import numpy as np

        path = index or index_path()
        self.rows, self.vectors = load_index(path)
        self.keyword = BM25Okapi([tokens(search_text(row)) for row in self.rows])
        self.bonus = tier_bonus(self.rows)
        self.document_ids = {row["document_id"] for row in self.rows if row["in_force"]}
        self.reranker = _reranker() if rerank else None
        self.np = np

    def search(self, query: str, k: int = 4) -> list[dict]:
        query_vector = embed_texts([query])[0]
        vector_order = self.np.argsort(-(self.vectors @ query_vector)).tolist()
        keyword_order = self.np.argsort(-self.keyword.get_scores(tokens(query))).tolist()
        pool = []
        for row_id in merge(vector_order, keyword_order, self.bonus):
            row = self.rows[row_id]
            if row["in_force"]:
                pool.append(row)
            if len(pool) == POOL:
                break
        if self.reranker is not None:
            scores = self.reranker.predict([(query, search_text(row)) for row in pool])
            order = sorted(range(len(pool)), key=lambda i: float(scores[i]), reverse=True)
            pool = [pool[i] for i in order]
        found = one_per_document(pool, k)
        found = prefer_held(found, self.rows)
        log.info("search %s", [row["document_id"] for row in found])
        return found


def _reranker():
    try:
        from sentence_transformers import CrossEncoder

        return CrossEncoder(RERANK_MODEL, local_files_only=True)
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

    args = parser.parse_args()
    if args.command == "build":
        build(args.corpus, args.out)
        return
    for row in Index(args.index).search(args.query, args.k):
        print(f"{row['document_id']}  {row['path']}")


if __name__ == "__main__":
    main()
