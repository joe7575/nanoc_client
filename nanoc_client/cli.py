"""Interactive CLI for the NanoC client (protocol version 1).

A reader thread prints terminal output and debugger events as they arrive;
the main loop reads commands from stdin and sends requests. A curses TUI can
be built on top of the same core later.

Run:  nanoc-client --host 127.0.0.1 --port 40000 --token secret
"""

from __future__ import annotations

import argparse
import sys
import threading

from . import protocol as p
from .client import NanocClient, NanocError

HELP = """\
commands:
  state                     query the VM state
  attach [user_lines]       attach the debugger (allow variable write)
  detach                    detach the debugger
  bp <line>                 set a breakpoint
  bpc <line>                clear a breakpoint
  bpa                       clear all breakpoints
  c | cont                  continue
  halt                      halt at the next line
  s | step                  step into
  over                      step over
  out                       step out
  vars [scope]              list variables (scope 0=global, 1=local)
  bt                        backtrace
  key <text>                send key input to the terminal
  clear                     clear the local screen
  help                      this help
  quit | exit               disconnect
"""

COMMANDS = {
    "state": (p.Command.STATE,),
    "attach": (p.Command.ATTACH,),
    "detach": (p.Command.DETACH,),
    "halt": (p.Command.HALT,),
    "c": (p.Command.CONTINUE,),
    "cont": (p.Command.CONTINUE,),
    "continue": (p.Command.CONTINUE,),
    "s": (p.Command.STEP,),
    "step": (p.Command.STEP,),
    "over": (p.Command.STEP_OVER,),
    "out": (p.Command.STEP_OUT,),
    "bt": (p.Command.BACKTRACE,),
}


class Cli:
    def __init__(self, client: NanocClient, show_terminal=True):
        self.client = client
        self.show_terminal = show_terminal
        self._stop = threading.Event()

    # -- output -------------------------------------------------------------
    def _reader(self):
        while not self._stop.is_set():
            try:
                channel, payload = self.client.recv_frame()
            except (NanocError, OSError):
                if not self._stop.is_set():
                    print("\n[client] connection closed")
                self._stop.set()
                return
            if channel is p.Channel.TERMINAL:
                if self.show_terminal:
                    sys.stdout.write(payload.decode("utf-8", "replace"))
                    sys.stdout.flush()
            elif channel is p.Channel.DEBUG:
                try:
                    cmd, data = p.decode_debug(payload)
                except ValueError:
                    continue
                print("\n[debug] " + self._format(cmd, data))

    @staticmethod
    def _format(cmd, data):
        try:
            if cmd == p.Event.HALTED:
                return f"HALTED reason={data[0]} line={data[1]} pc={data[2]}"
            if cmd == p.Event.ENDED:
                return "ENDED"
            if cmd == p.Event.DETACHED:
                return "DETACHED"
            name = p.Command(cmd).name
        except ValueError:
            name = f"0x{cmd:02x}"
        return f"{name} {data}"

    # -- run ----------------------------------------------------------------
    def run(self):
        threading.Thread(target=self._reader, daemon=True).start()
        print("NanoC client connected. Type 'help' for commands.")
        while not self._stop.is_set():
            try:
                line = input("nanoc> ")
            except (EOFError, KeyboardInterrupt):
                break
            if not self._dispatch(line.strip()):
                break
        self._stop.set()
        self.client.close()

    def _dispatch(self, line):
        if not line:
            return True
        parts = line.split()
        cmd, args = parts[0], parts[1:]

        if cmd in ("quit", "exit"):
            return False
        if cmd == "help":
            print(HELP)
            return True
        if cmd == "clear":
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
            return True
        if cmd == "key":
            self.client.send_terminal((" ".join(args) + "\n").encode())
            return True
        if cmd in ("bp", "bpc"):
            if not args:
                print("usage: bp <line>")
                return True
            c = p.Command.BP_SET if cmd == "bp" else p.Command.BP_CLR
            self.client.send_debug(c, int(args[0], 0))
            return True
        if cmd == "bpa":
            self.client.send_debug(p.Command.BP_CLR_ALL)
            return True
        if cmd == "attach":
            user_lines = int(args[0], 0) if args else 0
            self.client.send_debug(p.Command.ATTACH, 1, user_lines)
            return True
        if cmd == "vars":
            scope = int(args[0], 0) if args else 0
            for index in range(16):
                self.client.send_debug(p.Command.VAR_INFO, scope, index)
            return True
        if cmd == "var":
            if len(args) < 2:
                print("usage: var <scope> <index>")
                return True
            self.client.send_debug(p.Command.VAR_INFO, int(args[0], 0), int(args[1], 0))
            return True
        if cmd in COMMANDS:
            self.client.send_debug(*COMMANDS[cmd])
            return True
        print(f"unknown command: {cmd} (try 'help')")
        return True


def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="nanoc-client",
                                 description="NanoC external terminal/debugger client")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=40000)
    ap.add_argument("--token", default="")
    ap.add_argument("--tls", action="store_true", help="use TLS")
    ap.add_argument("--server-hostname", default=None, help="SNI/hostname for TLS")
    ap.add_argument("--no-terminal", action="store_true", help="do not print terminal output")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        client = NanocClient(
            host=args.host, port=args.port, token=args.token, tls=args.tls,
            server_hostname=args.server_hostname,
        )
        client.connect()
    except (NanocError, OSError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    Cli(client, show_terminal=not args.no_terminal).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
