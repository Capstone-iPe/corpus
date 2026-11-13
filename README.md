# onb-corpus

Policy pack and search API for the iPe onboarding copilot. ONB still decides fields, files, and the verdict; this service only returns passages for citation and explanation.

**500 documents** under `corpus/` (Track B range 500–2,000). Generators live in `corpus-build/`. The indexer only reads `corpus/**/*.md`.

| Folder | What |
|---|---|
| `corpus/policy/` | ONB-POL-001–005 |
| `corpus/annex/` | Evidence, volume, type aliases |
| `corpus/circulars/` | Activation and untrusted text |
| `corpus/briefings/` | Background statutes (not extra pack items) |
| `corpus/opinions/` | IRAC memos |
| `corpus/faq/` | Merchant-facing answers |
| `corpus/territorial/` | Non-exceptions |
| `corpus/handbook/` | Reviewer handbook |
| `corpus/not-in-force/` | Rejected drafts — discard if retrieved |

`copilot-svc` calls this service over HTTP (`CORPUS_SEARCH_URL` + Bearer `CORPUS_API_KEY`). It does not vendor the pack.

## Clone

```bash
git clone https://github.com/Capstone-iPe/onb-corpus.git
cd onb-corpus
```

## Config

```bash
cp .env.example .env
# fill EMBEDDINGS_API_KEY and CORPUS_API_KEY
# place vm02-ca.crt next to the repo (or set EMBEDDINGS_CA_CERT)
```

| Variable | Purpose |
|---|---|
| `EMBEDDINGS_*` / `EMBEDDING_MODEL` | Hosted embeddings for build + query |
| `CORPUS_API_KEY` | Bearer secret for `/v1/*` (same value in copilot-svc) |
| `INDEX_PATH` | Optional (default `index`) |
| `PORT` | HTTP port (default `8081`; Render sets `PORT`) |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Build the index

```bash
.venv/bin/python -m onb_corpus build
.venv/bin/python -m onb_corpus search "why is bank proof required"
```

## Run the search API

```bash
.venv/bin/python -m onb_corpus serve
```

Binds `0.0.0.0:$PORT` (default 8081).

| Route | Auth |
|---|---|
| `GET /health` | open |
| `GET /v1/document-ids` | Bearer |
| `POST /v1/search` | Bearer |

### Local curl

```bash
curl -sS http://127.0.0.1:8081/health

curl -sS http://127.0.0.1:8081/v1/document-ids \
  -H "Authorization: Bearer $CORPUS_API_KEY"

curl -sS http://127.0.0.1:8081/v1/search \
  -H "Authorization: Bearer $CORPUS_API_KEY" \
  -H "content-type: application/json" \
  -d '{"query":"why is bank proof required","k":4}'
```

### Production curl (Render)

```bash
export CORPUS_API_KEY='…'   # same secret as the onb-corpus service

curl -sS https://onb-corpus.onrender.com/health

curl -sS https://onb-corpus.onrender.com/v1/document-ids \
  -H "Authorization: Bearer $CORPUS_API_KEY"

curl -sS https://onb-corpus.onrender.com/v1/search \
  -H "Authorization: Bearer $CORPUS_API_KEY" \
  -H "content-type: application/json" \
  -d '{"query":"why is bank proof required","k":4}'
```

Free-tier cold start can take a minute; `/health` may return before the index is ready (`"status":"ok"` with loading still in progress — retry `/v1/search` if you get 503).

## Render

Live URL: **https://onb-corpus.onrender.com** (iPe workspace, free plan).

| When | What runs |
|---|---|
| **Deploy / push to `main`** | Build: `pip install -r requirements.txt && PYTHONPATH=src python -m onb_corpus build` (re-embeds the pack via the Capstone embeddings API, writes `index/`). Then start: `PYTHONPATH=src python -m onb_corpus serve`. |
| **Cold start** (free spin-up after idle) | **Start only** — loads the index already built into the deploy slug. Does **not** re-run build or call embeddings for the whole corpus. |

So: rebuild happens on **deploy**, not every wake-up. Changing documents or chunking needs a new deploy (or a manual rebuild + restart locally).

- **Health check:** `/health`
- **Env:** `EMBEDDINGS_API_KEY`, `EMBEDDINGS_BASE_URL`, `EMBEDDINGS_CA_PEM` (full PEM text), `EMBEDDING_MODEL=bge-small-en-v1.5`, `CORPUS_API_KEY`
- Free plan is 512Mi: no torch / sentence-transformers; mmap vectors; compact keyword index; `/health` answers before the index finishes loading.

Point `copilot-svc` at the public URL with the same `CORPUS_API_KEY`:

```bash
CORPUS_SEARCH_URL=https://onb-corpus.onrender.com
CORPUS_API_KEY=…
```

## Week 2 — local recall (not required for E2E)

Chunking / hybrid / rerank experiments and **hit@4 / hit@8** on a fixed question set are **local only**. Render keeps hybrid without a CrossEncoder. Write-up: [eval/week2-retrieval.md](eval/week2-retrieval.md).

```bash
.venv/bin/python -m onb_corpus build
.venv/bin/python -m onb_corpus recall --modes dense,keyword,hybrid --k 4,8
# optional: pip install '.[rerank]' then --modes hybrid_rerank
```

Latest summary: [eval/results/summary.json](eval/results/summary.json) — **hybrid @ 800/120: hit@4 = 0.958, hit@8 = 1.0**. Rerank did not help hit@4.

## Regenerate memos

```bash
python3 corpus-build/expand.py
python3 corpus-build/stats.py
```

Then rebuild the index and redeploy/restart the API.
