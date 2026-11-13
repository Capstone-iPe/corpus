"""Local recall@k over a fixed question set (Week 2 retrieval eval).

  PYTHONPATH=src python -m onb_corpus recall
  PYTHONPATH=src python -m onb_corpus recall --modes dense,keyword,hybrid --k 4,8
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from onb_corpus.config import ROOT, index_path
from onb_corpus.index import MODES, Index

DEFAULT_QUESTIONS = ROOT / "eval" / "questions.json"
DEFAULT_OUT = ROOT / "eval" / "results" / "recall.json"


def load_questions(path: Path) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"empty question set: {path}")
    for row in rows:
        if not row.get("id") or not row.get("query") or not row.get("relevant"):
            raise RuntimeError(f"bad question row: {row!r}")
    return rows


def hit_at_k(retrieved: list[str], relevant: set[str], k: int) -> bool:
    return any(doc_id in relevant for doc_id in retrieved[:k])


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    found = set(retrieved[:k]) & relevant
    return len(found) / len(relevant)


def score_mode(
    index: Index,
    questions: list[dict],
    mode: str,
    ks: list[int],
) -> dict:
    max_k = max(ks)
    per_q: list[dict] = []
    hits = {k: 0 for k in ks}
    recalls = {k: 0.0 for k in ks}
    t0 = time.perf_counter()
    for row in questions:
        relevant = set(row["relevant"])
        found = index.search(row["query"], k=max_k, mode=mode)
        ids = [item["document_id"] for item in found]
        entry = {
            "id": row["id"],
            "query": row["query"],
            "relevant": sorted(relevant),
            "retrieved": ids,
            "hit": {},
            "recall": {},
        }
        for k in ks:
            hit = hit_at_k(ids, relevant, k)
            rec = recall_at_k(ids, relevant, k)
            entry["hit"][str(k)] = hit
            entry["recall"][str(k)] = round(rec, 4)
            if hit:
                hits[k] += 1
            recalls[k] += rec
        per_q.append(entry)
    n = len(questions)
    return {
        "mode": mode,
        "n": n,
        "seconds": round(time.perf_counter() - t0, 2),
        "hit_rate": {str(k): round(hits[k] / n, 4) for k in ks},
        "mean_recall": {str(k): round(recalls[k] / n, 4) for k in ks},
        "questions": per_q,
    }


def run(
    questions_path: Path,
    index: Path,
    modes: list[str],
    ks: list[int],
    out: Path,
) -> dict:
    questions = load_questions(questions_path)
    want_rerank = "hybrid_rerank" in modes
    loaded = Index(index, rerank=want_rerank)
    unknown = sorted(set(modes) - set(MODES))
    if unknown:
        raise SystemExit(f"unknown modes: {unknown}")
    if "hybrid_rerank" in modes and loaded._ensure_reranker() is None:
        print("warning: hybrid_rerank requested but CrossEncoder unavailable; skipping")
        modes = [m for m in modes if m != "hybrid_rerank"]
    results = {
        "index": str(index),
        "questions": str(questions_path),
        "ks": ks,
        "modes": [],
    }
    for mode in modes:
        print(f"scoring mode={mode} …")
        block = score_mode(loaded, questions, mode, ks)
        summary = {
            "mode": mode,
            "hit_rate": block["hit_rate"],
            "mean_recall": block["mean_recall"],
            "seconds": block["seconds"],
        }
        print(
            f"  hit@4={block['hit_rate'].get('4')} hit@8={block['hit_rate'].get('8')} "
            f"recall@4={block['mean_recall'].get('4')} recall@8={block['mean_recall'].get('8')} "
            f"({block['seconds']}s)"
        )
        results["modes"].append(block)
        _ = summary
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Score recall@k on the fixed question set.")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--index", type=Path, default=index_path())
    parser.add_argument(
        "--modes",
        default="dense,keyword,hybrid",
        help="Comma-separated: dense,keyword,hybrid,hybrid_rerank",
    )
    parser.add_argument("--k", default="4,8", help="Comma-separated cutoffs")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    ks = sorted({int(x) for x in args.k.split(",") if x.strip()})
    run(args.questions, args.index, modes, ks, args.out)


if __name__ == "__main__":
    main()
