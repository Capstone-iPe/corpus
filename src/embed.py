"""Hosted embeddings: OpenAI-compatible POST /embeddings."""

from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.error
import urllib.request

import numpy as np

from config import (
    embedding_model,
    embeddings_api_key,
    embeddings_base_url,
    embeddings_ca_cert,
)

log = logging.getLogger("corpus_svc")
BATCH = 16


def embed_texts(texts: list[str]) -> np.ndarray:
    """Return L2-normalized vectors, one row per text, in the same order."""
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    key = embeddings_api_key()
    if not key:
        raise RuntimeError("Set EMBEDDINGS_API_KEY in .env")
    rows: list[list[float]] = []
    for start in range(0, len(texts), BATCH):
        batch = texts[start : start + BATCH]
        payload = _post(batch, key)
        ordered = sorted(payload, key=lambda item: int(item["index"]))
        rows.extend(item["embedding"] for item in ordered)
    vectors = np.asarray(rows, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return vectors / norms


def _post(texts: list[str], key: str) -> list[dict]:
    body = {"model": embedding_model(), "input": texts}
    url = f"{embeddings_base_url().rstrip('/')}/embeddings"
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    context = ssl.create_default_context(cafile=str(embeddings_ca_cert()))
    for delay in (0, 2, 4, 8):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(request, context=context, timeout=120) as response:
                payload = json.load(response)
            data = payload.get("data")
            if not isinstance(data, list) or len(data) != len(texts):
                raise RuntimeError("embeddings response size did not match the batch")
            return data
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 503}:
                log.info("embeddings failed with HTTP %s", exc.code)
                raise
            log.info("embeddings busy (HTTP %s), retrying", exc.code)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
            log.info("embeddings failed (%s)", type(exc).__name__)
            if delay == 8:
                raise
    raise RuntimeError("embeddings still busy after retries")
