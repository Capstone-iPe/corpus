"""CLI and HTTP entrypoints.

  PYTHONPATH=src python src/__main__.py build
  PYTHONPATH=src python src/__main__.py search "why is bank proof required"
  PYTHONPATH=src python src/__main__.py recall
  PYTHONPATH=src python src/__main__.py serve
"""

from __future__ import annotations

import logging
import os
import sys

import uvicorn

from index import main as index_main


def serve() -> None:
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8081"))
    uvicorn.run("app:app", host=host, port=port, log_level="info")


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(
            "usage: python src/__main__.py {build,search,recall,serve} ...",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if argv[0] == "serve":
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        serve()
        return
    if argv[0] == "recall":
        from recall import main as recall_main

        recall_main(argv[1:])
        return
    sys.argv = [sys.argv[0], *argv]
    index_main()


if __name__ == "__main__":
    main()
