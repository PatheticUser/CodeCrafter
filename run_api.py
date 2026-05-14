#!/usr/bin/env python3
"""Entry point to run the CodeCrafter Inference API server.

Usage:
    python run_api.py [--host HOST] [--port PORT] [--reload]
"""

import argparse

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="CodeCrafter Inference API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")
    args = parser.parse_args()

    print(f"  🚀  CodeCrafter API starting on http://{args.host}:{args.port}")
    print(f"  📖  Docs: http://{args.host}:{args.port}/docs")
    print()

    uvicorn.run(
        "api.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
