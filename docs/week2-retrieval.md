# Week 2 — retrieval experiments (local)

Scored apart from shop E2E / replay. Product search on Render stays **hybrid without torch**. These runs use the Capstone hosted embeddings API (`bge-small-en-v1.5`) against a local index.

## Fixed question set

[`eval/questions.json`](../eval/questions.json) — **24** why/cite queries with gold `document_id` lists (policy, annex, circular, FAQ). Shop gold in analysis `eval/` is not used here and is not indexed.

## Metrics

| Metric | Definition |
|---|---|
| **hit@k** | Share of questions where ≥1 gold id appears in the top-k unique documents |
| **mean recall@k** | Mean of \|retrieved ∩ gold\| / \|gold\| at cutoff k |

Primary Capstone numbers: **hit@4** and **hit@8** (reported as recall@k in the checklist sense of “did the right doc land in k”).

## How to reproduce (local only)

```bash
cp .env.example .env   # EMBEDDINGS_* required
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m onb_corpus build
PYTHONPATH=src .venv/bin/python -m onb_corpus recall --modes dense,keyword,hybrid --k 4,8

# optional chunking variants
ONB_CHUNK=400 ONB_OVERLAP=60 PYTHONPATH=src .venv/bin/python -m onb_corpus build --out index-c400
ONB_CHUNK=1200 ONB_OVERLAP=180 PYTHONPATH=src .venv/bin/python -m onb_corpus build --out index-c1200
PYTHONPATH=src .venv/bin/python -m onb_corpus recall --index index-c400 --modes hybrid --out eval/results/recall-c400.json
PYTHONPATH=src .venv/bin/python -m onb_corpus recall --index index-c1200 --modes hybrid --out eval/results/recall-c1200.json

# optional rerank (pip install '.[rerank]' — not used on free Render)
PYTHONPATH=src .venv/bin/python -m onb_corpus recall --modes hybrid_rerank --out eval/results/recall-rerank.json
```

## Chunking

| Setting | Chunks | hybrid hit@4 | hybrid hit@8 | mean recall@4 | mean recall@8 |
|---|---:|---:|---:|---:|---:|
| 400 / 60 | 2667 | 0.875 | 0.958 | 0.597 | 0.729 |
| **800 / 120** | **1446** | **0.958** | **1.000** | **0.694** | **0.840** |
| 1200 / 180 | 1063 | 0.958 | 1.000 | 0.701 | 0.840 |

**Keep 800/120.** Smaller chunks diluted hit@4; larger chunks matched hit rates but did not beat 800/120 enough to justify a rebuild of the deploy index. Same size family as Assignment 05.

## Dense vs keyword vs hybrid (800/120)

| Mode | hit@4 | hit@8 | mean recall@4 | mean recall@8 |
|---|---:|---:|---:|---:|
| dense | 0.792 | 0.833 | 0.458 | 0.625 |
| keyword | 0.583 | 0.750 | 0.333 | 0.479 |
| **hybrid** | **0.958** | **1.000** | **0.694** | **0.840** |
| hybrid + MiniLM cross-encoder | 0.833 | 1.000 | 0.500 | 0.722 |

**Keep hybrid** (dense cosine + keyword postings, RRF, folder tier bonus, one chunk per document). Hybrid lifts hit@4 by ~17 points over dense and ~37 over keyword.

**Do not keep the CrossEncoder on the product path.** Local `cross-encoder/ms-marco-MiniLM-L-6-v2` over the hybrid pool **hurt hit@4** (0.83 vs 0.96) while hit@8 stayed 1.0. Free Render also cannot host torch. Optional `pip install '.[rerank]'` remains for local probes only.

## What ships

| Surface | Setting |
|---|---|
| Render `onb-corpus` | 800/120 index from deploy build; hybrid; no rerank |
| Local Week 2 eval | this doc + `eval/results/*.json` |
| Copilot | unchanged — `POST /v1/search` only |

Raw runs: [`eval/results/`](../eval/results/).
