#!/usr/bin/env python3
"""Sync the NanoC documentation into this package.

The client is installed from its own git repository, so the docs of the
sibling repositories must be vendored here. Run this after changing any of
them:

    python tools/sync_docs.py            # copy + write docs/SOURCES.json
    python tools/sync_docs.py --check    # fail if a copy is out of date

Source locations default to the layout of the author's workspace and can be
overridden with the options below or the matching environment variables.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "nanoc_client", "docs")

# (destination, source directory option, source file name)
COPIES = [
    ("language.md", "nanoc_docs", "nanoc_llm_prompt.md"),
    ("reference.md", "nanoc_docs", "nanoc_reference.md"),
    ("manual.md", "nanoc_mod", "doc/manual.md"),
    ("techage_topics.md", "beduino", "BEPs/bep-005_ta_cmnd.md"),
    ("examples/techage_monitor.nanoc", "nanoc_mod",
     "examples/techage_monitor.nanoc"),
    ("examples/termlib_demo.nanoc", "nanoc_mod",
     "examples/termlib_demo.nanoc"),
    ("examples/factory_control.nanoc", "nanoc_mod",
     "examples/factory_control.nanoc"),
    ("examples/fab_control.nanoc", "nanoc_mod",
     "examples/fab_control.nanoc"),
    ("examples/oven_control.nanoc", "nanoc_mod",
     "examples/oven_control.nanoc"),
    ("examples/blinds_demo.nanoc", "nanoc_mod",
     "examples/blinds_demo.nanoc"),
]


def git_head(path):
    """Return (commit, dirty) for the repository containing *path*."""
    try:
        commit = subprocess.check_output(
            ["git", "-C", path, "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(
            ["git", "-C", path, "status", "--porcelain"],
            stderr=subprocess.DEVNULL, text=True).strip())
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nanoc-docs", default=os.environ.get(
        "NANOC_DOCS", os.path.join(REPO, "..", "C", "_compiler", "nanoc", "docs")))
    ap.add_argument("--nanoc-mod", default=os.environ.get(
        "NANOC_MOD", os.path.join(REPO, "..", "nanoc_mod")))
    ap.add_argument("--beduino", default=os.environ.get(
        "BEDUINO", os.path.join(REPO, "..", "..", "luanti-5.11.0", "mods", "beduino")))
    ap.add_argument("--check", action="store_true",
                    help="only verify that the copies match the sources")
    args = ap.parse_args(argv)

    roots = {
        "nanoc_docs": os.path.abspath(args.nanoc_docs),
        "nanoc_mod": os.path.abspath(args.nanoc_mod),
        "beduino": os.path.abspath(args.beduino),
    }

    sources = {}
    stale = []
    for dest, root_key, name in COPIES:
        src = os.path.join(roots[root_key], name)
        dst = os.path.join(DOCS, dest)
        if not os.path.isfile(src):
            print(f"missing source: {src}", file=sys.stderr)
            return 1
        sources[dest] = {"root": root_key, "file": name}
        if args.check:
            if not os.path.isfile(dst):
                stale.append(dest)
                continue
            with open(src, "rb") as a, open(dst, "rb") as b:
                if a.read() != b.read():
                    stale.append(dest)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            print(f"copied {name} -> docs/{dest}")

    if args.check:
        if stale:
            print("out of date: " + ", ".join(stale), file=sys.stderr)
            print("run: python tools/sync_docs.py", file=sys.stderr)
            return 1
        print("docs are up to date")
        return 0

    # Record provenance so drift is visible in review. Paths are left out on
    # purpose: this file is committed and the checkouts are machine-specific.
    meta = {}
    for root_key, root in roots.items():
        commit, dirty = git_head(root)
        meta[root_key] = {"commit": commit, "dirty": dirty}
    meta["files"] = sources
    with open(os.path.join(DOCS, "SOURCES.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
        f.write("\n")
    print("wrote docs/SOURCES.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
