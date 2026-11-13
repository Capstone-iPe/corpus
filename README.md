# onb-corpus

Policy pack and search API for the iPe onboarding copilot. ONB still decides fields, files, and the verdict; this service only returns passages for citation and explanation.

**500 documents** under `documents/` (Track B range 500–2,000). Generators live in `corpus-build/`. The indexer only reads `documents/**/*.md`.

| Folder | What |
|---|---|
| `documents/policy/` | ONB-POL-001–005 |
| `documents/annex/` | Evidence, volume, type aliases |
| `documents/circulars/` | Activation and untrusted text |
| `documents/briefings/` | Background statutes (not extra pack items) |
| `documents/opinions/` | IRAC memos |
| `documents/faq/` | Merchant-facing answers |
| `documents/territorial/` | Non-exceptions |
| `documents/handbook/` | Reviewer handbook |
| `documents/not-in-force/` | Rejected drafts — discard if retrieved |

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
PYTHONPATH=src .venv/bin/python -m onb_corpus build
PYTHONPATH=src .venv/bin/python -m onb_corpus search "why is bank proof required"
```

## Run the search API

```bash
PYTHONPATH=src .venv/bin/python -m onb_corpus serve
```

Binds `0.0.0.0:$PORT` (default 8081).

```bash
curl -s http://127.0.0.1:8081/health

curl -s http://127.0.0.1:8081/v1/search \
  -H "Authorization: Bearer $CORPUS_API_KEY" \
  -H "content-type: application/json" \
  -d '{"query":"why is bank proof required","k":4}'
```

| Route | Auth |
|---|---|
| `GET /health` | open |
| `GET /v1/document-ids` | Bearer |
| `POST /v1/search` | Bearer |

## Render

Web service on the **iPe** workspace (free plan is fine for Capstone):

- **Build:** `pip install -r requirements.txt && PYTHONPATH=src python -m onb_corpus build`
- **Start:** `PYTHONPATH=src python -m onb_corpus serve`
- **Health check:** `/health`
- **Env:** `EMBEDDINGS_API_KEY`, `EMBEDDINGS_BASE_URL`, `EMBEDDINGS_CA_PEM` (full PEM text), `EMBEDDING_MODEL`, `CORPUS_API_KEY`

Point `copilot-svc` at the public URL with the same `CORPUS_API_KEY`:

```bash
CORPUS_SEARCH_URL=https://onb-corpus-xxxx.onrender.com
CORPUS_API_KEY=…
```

## Regenerate memos

```bash
python3 corpus-build/expand.py
python3 corpus-build/stats.py
```

Then rebuild the index and redeploy/restart the API.
