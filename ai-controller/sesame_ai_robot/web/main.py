from __future__ import annotations

import argparse
import os

from .app import create_app
from .security import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_WORKERS, assert_local_host
from .service import create_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Sesame localhost-only Web Simulator API")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        host = assert_local_host(args.host)
    except ValueError as exc:
        print(str(exc))
        return 2
    os.environ.setdefault("SESAME_AI_PROVIDER", "mock")
    print("LOCAL SIMULATOR ONLY")
    print("REAL HARDWARE DISABLED")
    print(f"Listening on http://{host}:{args.port}")
    try:
        import uvicorn
    except ImportError:
        print("Missing web dependencies. Install with: python -m pip install -e '.[web]'")
        return 2
    service = create_service(provider_name=os.environ.get("SESAME_AI_PROVIDER", "mock"))
    app = create_app(service=service)
    uvicorn.run(app, host=host, port=args.port, workers=DEFAULT_WORKERS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
