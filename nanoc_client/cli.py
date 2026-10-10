"""Minimal CLI entry point for the NanoC client."""

from __future__ import annotations

import argparse
import sys

from .client import NanocClient, NanocError


def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="nanoc-client", description="NanoC external terminal/debugger client")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=40000)
    ap.add_argument("--token", default="")
    ap.add_argument("--tls", action="store_true", help="use TLS")
    ap.add_argument("--server-hostname", default=None, help="SNI/hostname for TLS")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        with NanocClient(
            host=args.host,
            port=args.port,
            token=args.token,
            tls=args.tls,
            server_hostname=args.server_hostname,
        ) as client:
            print(f"connected to {args.host}:{args.port} (session {client.session})")
            # Interactive debugger/terminal UI follows.
    except (NanocError, OSError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
