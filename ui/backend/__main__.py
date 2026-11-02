"""``python -m ui.backend [--host H] [--port P] [--reload]``: serve the API (and the built
frontend, when ``ui/frontend/dist`` exists) with uvicorn."""

from __future__ import annotations

import argparse

import uvicorn


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m ui.backend", description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--reload",
        action="store_true",
        help="restart on code changes (development; a run in flight is lost on reload)",
    )
    args = parser.parse_args(argv)
    uvicorn.run(
        "ui.backend.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
