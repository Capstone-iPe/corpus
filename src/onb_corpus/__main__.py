"""Compat entry for: PYTHONPATH=src python -m onb_corpus …

Render Dashboard still uses this form; flat modules live next to this package under src/.
"""

from __future__ import annotations

import logging
import os
import sys

import uvicorn


def serve() -> None:
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8081"))
    uvicorn.run("app:app", host=host, port=port, log_level="info")


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(
            "usage: python -m onb_corpus {build,search,serve} ...",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if argv[0] == "serve":
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        serve()
        return
    if argv[0] == "recall":
        print(
            "recall moved to eval/: PYTHONPATH=src python eval/recall.py …",
            file=sys.stderr,
        )
        raise SystemExit(2)
    from index import main as index_main

    sys.argv = [sys.argv[0], *argv]
    index_main()


if __name__ == "__main__":
    main()
