"""CLI and HTTP entrypoints.

  PYTHONPATH=src python -m onb_corpus build
  PYTHONPATH=src python -m onb_corpus search "why is bank proof required"
  PYTHONPATH=src python -m onb_corpus serve
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import uvicorn

from onb_corpus.index import main as index_main


def serve() -> None:
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8081"))
    uvicorn.run("onb_corpus.app:app", host=host, port=port, log_level="info")


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m onb_corpus {build,search,serve} ...", file=sys.stderr)
        raise SystemExit(2)
    if argv[0] == "serve":
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        serve()
        return
    sys.argv = [sys.argv[0], *argv]
    index_main()


if __name__ == "__main__":
    main()
