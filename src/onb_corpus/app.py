"""FastAPI search service over the policy corpus.

  GET  /health              open
  GET  /v1/document-ids     Bearer CORPUS_API_KEY
  POST /v1/search           Bearer CORPUS_API_KEY
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from onb_corpus.auth import require_api_key
from onb_corpus.config import index_path
from onb_corpus.index import Index

log = logging.getLogger("onb_corpus")

_index: Index | None = None


def get_index() -> Index:
    if _index is None:
        raise RuntimeError("index is not loaded")
    return _index


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _index
    path = index_path()
    if not (path / "chunks.jsonl").is_file() or not (path / "vectors.npy").is_file():
        raise RuntimeError(
            f"index missing at {path}; run: PYTHONPATH=src python -m onb_corpus build"
        )
    _index = Index(path)
    log.info("loaded index from %s (%s in-force ids)", path, len(_index.document_ids))
    yield
    _index = None


app = FastAPI(title="iPe onb-corpus", version="0.1.0", lifespan=lifespan)


class SearchBody(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=4, ge=1, le=20)


class Hit(BaseModel):
    document_id: str
    path: str
    folder: str
    text: str
    search_text: str
    in_force: bool


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
