"""Scriptable NanoC command line: check, push, run, stop, read, exec.

Non-interactive, so it can be driven by scripts and AI agents:

    nanoc check app.nanoc            # local lint (Problems-style output)
    nanoc push  app.nanoc            # upload + compile (errors on stderr)
    nanoc run                        # continue/resume the controller
    nanoc stop                       # halt (pause) the controller
    nanoc read --seconds 3           # print terminal output for N seconds
    nanoc exec  app.nanoc --seconds 3   # push + run + read in one call

Connection: --host/--port/--token (+ --tls). Token from the controller form.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time

from . import protocol as p
from .checker import check_file
from .client import NanocClient, NanocError
from .screen import Screen


def _add_conn(ap):
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=41100)
    ap.add_argument("--token", default="")
    ap.add_argument("--tls", action="store_true")
    ap.add_argument("--server-hostname", default=None)


def _connect(args):
    client = NanocClient(
        host=args.host, port=args.port, token=args.token,
        tls=args.tls, server_hostname=args.server_hostname, blocking=False,
    )
    client.connect()
    return client


def _recv_debug(client, cmd, collect=None, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            channel, payload = client.recv_frame()
        except socket.timeout:
            continue
        except (NanocError, OSError) as err:
            raise NanocError(str(err))
        if channel is p.Channel.TERMINAL:
            if collect is not None:
                collect.append(payload)
        elif channel is p.Channel.DEBUG:
            got, data = p.decode_debug(payload)
            if got == int(cmd):
                return data
    raise NanocError(f"timeout waiting for {p.Command(cmd).name}")


def _cmd(client, cmd, *data, timeout=5.0, collect=None):
    client.send_debug(cmd, *data)
    return _recv_debug(client, cmd, collect, timeout)


def _compiler_message(resp):
    if not resp or len(resp) < 2:
        return ""
    n = resp[1]
    return bytes(b & 0xFF for b in resp[2:2 + n]).decode("utf-8", "replace")


def _claim(client):
    """Attach and check that we got debug focus."""
    state = _cmd(client, p.Command.ATTACH, 1, 0)
    if state and state[0] == p.Status.DENIED:
        print("error: controller is busy (debugged by another client)",
              file=sys.stderr)
        return False
    return True


def _read_seconds(client, seconds, collect):
    end = time.time() + seconds
    while time.time() < end:
        try:
            channel, payload = client.recv_frame()
        except socket.timeout:
            continue
        except (NanocError, OSError):
            break
        if channel is p.Channel.TERMINAL:
            collect.append(payload)


def _upload_bytes(client, data, timeout=10.0):
    resp = _cmd(client, p.Command.PROG_SET, len(data), *list(data), timeout=timeout)
    status = resp[0] if resp else 1
    return status == 0, _compiler_message(resp)


def _upload(client, path, timeout=10.0):
    with open(path, "rb") as f:
        data = f.read()
    return _upload_bytes(client, data, timeout)


# -- subcommands -----------------------------------------------------------

def cmd_check(args):
    errors = check_file(args.file)
    for line, msg in errors:
        print(f"{args.file}:{line}: error: {msg}")
    return 1 if errors else 0


def cmd_push(args):
    client = _connect(args)
    try:
        if not _claim(client):
            return 2
        ok, msg = _upload(client, args.file)
        if msg:
            sys.stderr.write(msg if msg.endswith("\n") else msg + "\n")
        if not ok:
            return 1
        _cmd(client, p.Command.CONTINUE)      # resume the VM
        print(f"uploaded {args.file}")
        return 0
    finally:
        client.close()


def cmd_run(args):
    client = _connect(args)
    try:
        if not _claim(client):
            return 2
        _cmd(client, p.Command.CONTINUE)
        print("running")
        return 0
    finally:
        client.close()


def cmd_stop(args):
    client = _connect(args)
    try:
        if not _claim(client):
            return 2
        _cmd(client, p.Command.HALT)
        print("stopped")
        return 0
    finally:
        client.close()


def cmd_read(args):
    client = _connect(args)
    collect = []
    try:
        _read_seconds(client, args.seconds, collect)
        _print_screen(collect)
        return 0
    finally:
        client.close()


def _print_screen(chunks):
    """Render the collected terminal chunks through the termlib screen model."""
    screen = Screen()
    for chunk in chunks:
        screen.feed(chunk)
    color = sys.stdout.isatty()
    sys.stdout.write(screen.render_ansi(color=color).rstrip("\n") + "\n")


def cmd_exec(args):
    client = _connect(args)
    collect = []
    try:
        if not _claim(client):
            return 2
        ok, msg = _upload(client, args.file)
        if not ok:
            sys.stderr.write(msg if msg.endswith("\n") else msg + "\n")
            return 1
        _cmd(client, p.Command.CONTINUE)
        _read_seconds(client, args.seconds, collect)
        _print_screen(collect)
        return 0
    finally:
        client.close()


def cmd_scan(args):
    client = _connect(args)
    try:
        resp = _cmd(client, p.Command.SCAN, args.radius, timeout=20)
        status = resp[0] if resp else 1
        text = _compiler_message(resp)
        if status != 0 or not text:
            print("error: scan failed", file=sys.stderr)
            return 1
        try:
            print(json.dumps(json.loads(text), indent=2))
        except ValueError:
            print(text)
        return 0
    finally:
        client.close()


def cmd_catalog(args):
    client = _connect(args)
    try:
        resp = _cmd(client, p.Command.CATALOG, timeout=15)
        status = resp[0] if resp else 1
        text = _compiler_message(resp)
        if status != 0 or not text:
            print("error: catalog failed", file=sys.stderr)
            return 1
        try:
            print(json.dumps(json.loads(text), indent=2))
        except ValueError:
            print(text)
        return 0
    finally:
        client.close()


def cmd_tui(args):
    from .tui import main as tui_main
    argv = ["--host", args.host, "--port", str(args.port), "--token", args.token]
    if args.tls:
        argv.append("--tls")
    if args.server_hostname:
        argv += ["--server-hostname", args.server_hostname]
    return tui_main(argv)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="nanoc", description="Scriptable NanoC client")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("check", help="lint a file locally")
    pc.add_argument("file")
    pc.set_defaults(func=cmd_check)

    pp = sub.add_parser("push", help="upload + compile a file")
    pp.add_argument("file")
    _add_conn(pp)
    pp.set_defaults(func=cmd_push)

    pr = sub.add_parser("run", help="resume the controller")
    _add_conn(pr)
    pr.set_defaults(func=cmd_run)

    ps = sub.add_parser("stop", help="halt (pause) the controller")
    _add_conn(ps)
    ps.set_defaults(func=cmd_stop)

    prd = sub.add_parser("read", help="print terminal output for a while")
    _add_conn(prd)
    prd.add_argument("--seconds", type=float, default=3.0)
    prd.set_defaults(func=cmd_read)

    pe = sub.add_parser("exec", help="push + run + read in one call")
    pe.add_argument("file")
    _add_conn(pe)
    pe.add_argument("--seconds", type=float, default=3.0)
    pe.set_defaults(func=cmd_exec)

    psc = sub.add_parser("scan", help="dump the TA4 techage topology as JSON")
    _add_conn(psc)
    psc.add_argument("--radius", type=int, default=8)
    psc.set_defaults(func=cmd_scan)

    pcat = sub.add_parser("catalog", help="dump the Beduino topic catalog as JSON")
    _add_conn(pcat)
    pcat.set_defaults(func=cmd_catalog)

    pt = sub.add_parser("tui", help="open the curses terminal view (TUI)")
    _add_conn(pt)
    pt.set_defaults(func=cmd_tui)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except (NanocError, OSError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
