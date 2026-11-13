"""Addresses and keys the corpus search service uses."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DEFAULT_INDEX = ROOT / "index"
DEFAULT_DOCS_ROOT = ROOT  # documents/ lives under the repo root


def _path(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    path = Path(raw).expanduser()
    return path if path.is_absolute() else ROOT / path


def embeddings_api_key() -> str:
    return os.environ.get("EMBEDDINGS_API_KEY", "").strip()


def embeddings_base_url() -> str:
    return os.environ.get("EMBEDDINGS_BASE_URL", "https://103.42.50.41:1035/v1").strip()


def embeddings_ca_cert() -> Path:
    return _path("EMBEDDINGS_CA_CERT", ROOT / "vm02-ca.crt")


def embedding_model() -> str:
    return os.environ.get("EMBEDDING_MODEL", "bge-small-en-v1.5").strip()


def corpus_api_key() -> str:
    return os.environ.get("CORPUS_API_KEY", "").strip()


def index_path() -> Path:
    return _path("INDEX_PATH", DEFAULT_INDEX)


def docs_root() -> Path:
    return _path("CORPUS_DOCS_ROOT", DEFAULT_DOCS_ROOT)
