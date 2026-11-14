"""FastAPI search service over the policy corpus.

  GET  /health              open (does not wait on the index)
  GET  /v1/document-ids     Bearer CORPUS_API_KEY
  POST /v1/search           Bearer CORPUS_API_KEY
"""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from auth import require_api_key
from config import index_path
from index import Index

log = logging.getLogger("corpus_svc")

_index: Index | None = None
_index_error: str | None = None
_lock = threading.Lock()


def _load_index() -> None:
    global _index, _index_error
    path = index_path()
    try:
        if not (path / "chunks.jsonl").is_file() or not (path / "vectors.npy").is_file():
            raise RuntimeError(
                f"index missing at {path}; run: PYTHONPATH=src python -m index build"
            )
        loaded = Index(path, rerank=False)
        with _lock:
            _index = loaded
            _index_error = None
        log.info("loaded index from %s (%s in-force ids)", path, len(loaded.document_ids))
    except Exception as exc:
        with _lock:
            _index = None
            _index_error = str(exc)
        log.exception("index load failed")


def get_index() -> Index:
    with _lock:
        if _index is not None:
            return _index
        err = _index_error
    if err:
        raise HTTPException(status_code=503, detail=f"index unavailable: {err}")
    raise HTTPException(status_code=503, detail="index still loading")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Bind the port first so Render health checks pass, then load the pack.
    threading.Thread(target=_load_index, name="load-index", daemon=True).start()
    yield


app = FastAPI(title="iPe onb-corpus", version="0.1.0", lifespan=lifespan)


class SearchBody(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=4, ge=1, le=20)


@app.get("/health")
def health() -> dict[str, str]:
    with _lock:
        if _index is not None:
            state = "ready"
        elif _index_error:
            state = "error"
        else:
            state = "loading"
    return {"status": "ok", "index": state}


@app.get("/v1/document-ids", dependencies=[Depends(require_api_key)])
def document_ids() -> dict[str, list[str]]:
    return {"document_ids": sorted(get_index().document_ids)}


@app.post("/v1/search", dependencies=[Depends(require_api_key)])
def search(body: SearchBody) -> dict[str, list[dict[str, Any]]]:
    hits = get_index().search(body.query, body.k)
    return {
        "hits": [
            {
                "document_id": row["document_id"],
                "path": row["path"],
                "folder": row["folder"],
                "text": row["text"],
                "search_text": row.get("search_text") or row["text"],
                "in_force": bool(row["in_force"]),
            }
            for row in hits
        ]
    }
