"""Shared Bearer API key for /v1 routes."""

from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from onb_corpus.config import corpus_api_key

_bearer = HTTPBearer(auto_error=False)


def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    expected = corpus_api_key()
    if not expected:
        raise HTTPException(status_code=503, detail="CORPUS_API_KEY is not configured")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = credentials.credentials
    if len(token) != len(expected) or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="invalid bearer token")
