"""Addresses and keys the corpus search service uses."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DEFAULT_INDEX = ROOT / "index"
DEFAULT_DOCS_ROOT = ROOT  # corpus/ lives under the repo root


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
    """Path to the Capstone embeddings CA file.

    Local default: repo-root vm02-ca.crt (gitignored).
    On Render: Secret File at /etc/secrets/vm02-ca.crt
    (set EMBEDDINGS_CA_CERT=/etc/secrets/vm02-ca.crt).
    """
    raw = os.environ.get("EMBEDDINGS_CA_CERT", "").strip()
    if raw:
        path = Path(raw).expanduser()
        return path if path.is_absolute() else ROOT / path
    render_secret = Path("/etc/secrets/vm02-ca.crt")
    if render_secret.is_file():
        return render_secret
    return ROOT / "vm02-ca.crt"


def embedding_model() -> str:
    return os.environ.get("EMBEDDING_MODEL", "bge-small-en-v1.5").strip()


def corpus_api_key() -> str:
    return os.environ.get("CORPUS_API_KEY", "").strip()


def index_path() -> Path:
    return _path("INDEX_PATH", DEFAULT_INDEX)


def docs_root() -> Path:
    return _path("CORPUS_DOCS_ROOT", DEFAULT_DOCS_ROOT)
