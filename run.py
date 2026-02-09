#!/usr/bin/env python
"""
run.py — Start the docparse server.

Usage:
    python run.py                          # defaults: port 12330, 1 worker, info logging
    python run.py --port 8000              # custom port
    python run.py --workers 4              # multiple workers
    python run.py --log-level debug        # verbose logging
    python run.py --reload                 # auto-reload on code changes (dev)
"""

import argparse
import os
import sys

import uvicorn


def main():
    parser = argparse.ArgumentParser(
        description="Start the docparse PDF extraction server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=int(os.getenv("PORT", "12330")),
        help="Port to listen on (default: 12330, env: PORT)",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=int(os.getenv("WORKERS", "1")),
        help="Number of uvicorn worker processes (default: 1, env: WORKERS)",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "info").lower(),
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level (default: info, env: LOG_LEVEL)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload on code changes (development only)",
    )

    args = parser.parse_args()

    # Expose values as env vars so the lifespan / banner can read them
    os.environ["PORT"] = str(args.port)
    os.environ["WORKERS"] = str(args.workers)
    os.environ["LOG_LEVEL"] = args.log_level

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers if not args.reload else 1,
        log_level=args.log_level,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
