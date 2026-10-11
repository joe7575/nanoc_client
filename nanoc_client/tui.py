"""Portable curses TUI for the NanoC terminal.

Shows the emulated termlib screen and lets you type/function-key input back to
the controller.

Portability: ``curses`` is in the Python standard library on Linux, macOS and
Android/Termux. On Windows it is not; install the ``windows-curses`` package
(``pip install windows-curses``). The same :class:`~nanoc_client.screen.Screen`
intermediate representation is used as by the CLI and DAP clients, so all
front ends stay consistent.
"""

from __future__ import annotations

import argparse
import locale
import os
import queue
import socket
import sys
import threading

from . import protocol as p
from .client import NanocClient, NanocError
from .screen import DEFAULT_COLOR, Screen

try:  # stdlib on Linux/macOS/Android; pip "windows-curses" on Windows
    import curses
except ImportError:  # pragma: no cover - platform dependent
    curses = None

FUNCTION_KEY_BASE = 128  # termlib F1..F8 -> 128..135


def function_key_bytes(n: int) -> bytes:
    """Bytes sent to the VM when termlib function key Fn (1..8) is pressed."""
    return bytes([FUNCTION_KEY_BASE + n - 1]) + b"\n"


class ColorMap:
    """Map termlib color indices (0..15, 255=default) to curses attributes."""

    def __init__(self, stdscr):
        self.enabled = bool(curses and curses.has_colors())
        self._pairs = {}
        self._next = 1
        if self.enabled:
            curses.start_color()
            try:
                curses.use_default_colors()
            except curses.error:
                pass

    def attr(self, fg: int, bg: int) -> int:
        if not self.enabled:
            return curses.A_NORMAL
        bright = curses.A_NORMAL
        if 0 <= fg <= 15:
            if fg >= 8:
                bright = curses.A_BOLD
                fg -= 8
        else:
            fg = -1
        bg = bg if 0 <= bg <= 15 else -1
        key = (fg, bg)
        if key not in self._pairs:
            if self._next >= curses.COLOR_PAIRS:
                return curses.A_NORMAL
            try:
                curses.init_pair(self._next,
                                 (curses.COLOR_BLACK + fg) if fg >= 0 else -1,
                                 (curses.COLOR_BLACK + bg) if bg >= 0 else -1)
            except curses.error:
                return curses.A_NORMAL
            self._pairs[key] = curses.color_pair(self._next)
            self._next += 1
        return self._pairs[key] | bright


class Tui:
    def __init__(self, args):
        self.args = args
        self.screen = Screen()
        self.events = queue.Queue()
        self._stop = threading.Event()
        self.client = None
        self.input = ""
        self.status = "connecting..."
        self._last_debug = ""
        self._last_log = ""

    # -- connection --------------------------------------------------------
    def connect(self) -> None:
        self.client = NanocClient(
            host=self.args.host, port=self.args.port, token=self.args.token,
            tls=self.args.tls, server_hostname=self.args.server_hostname,
            blocking=False, timeout=0.2,
        )
        self.client.connect()
        self.status = f"connected {self.args.host}:{self.args.port}"

    # -- reader thread -----------------------------------------------------
    def _reader(self) -> None:
        while not self._stop.is_set():
            try:
                channel, payload = self.client.recv_frame()
            except socket.timeout:
                continue
            except (NanocError, OSError):
                if not self._stop.is_set():
                    self.events.put(("closed", None))
                return
            if channel is p.Channel.TERMINAL:
                self.events.put(("term", payload))
            elif channel is p.Channel.LOG:
                self.events.put(("log", payload))
            elif channel is p.Channel.DEBUG:
                self.events.put(("dbg", payload))

    def _on_debug(self, payload) -> None:
        try:
            cmd, data = p.decode_debug(payload)
        except ValueError:
            return
        if cmd == p.Event.HALTED:
            self._last_debug = f"HALTED line {data[1] if len(data) > 1 else '?'}"
        elif cmd == p.Event.ENDED:
            self._last_debug = "ENDED"
        elif cmd == p.Event.DETACHED:
            self._last_debug = "DETACHED"

    # -- events ------------------------------------------------------------
    def _drain(self) -> None:
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "term":
                    self.screen.feed(data)
                    if self.screen.take_bell():
                        curses.beep()
                elif kind == "log":
                    self._last_log = data.decode("utf-8", "replace").strip()
                elif kind == "dbg":
                    self._on_debug(data)
                elif kind == "closed":
                    self.status = "connection closed"
                    self._stop.set()
        except queue.Empty:
            pass

    # -- input -------------------------------------------------------------
    def _handle_key(self, ch) -> None:
        if isinstance(ch, int):
            if ch == curses.KEY_RESIZE:
                return
            for n in range(1, 9):
                if ch == getattr(curses, f"KEY_F{n}", -1):
                    self.client.send_terminal(function_key_bytes(n))
                    return
            if ch in (curses.KEY_BACKSPACE, 8, 127):
                self.input = self.input[:-1]
            elif ch == curses.KEY_ENTER:
                self._send_line()
            return
        # str from get_wch()
        if ch in ("\x03", "\x11", "\x18"):   # Ctrl-C / Ctrl-Q / Ctrl-X: quit
            self._stop.set()
        elif ch in ("\n", "\r"):
            self._send_line()
        elif ch in ("\x7f", "\b"):
            self.input = self.input[:-1]
        elif ch == "\x0c":               # Ctrl-L: redraw
            pass
        elif ch.isprintable():
            self.input += ch

    def _send_line(self) -> None:
        if self.client is None:
            return
        # termlib trims the line before sending (string.trim), so do the same
        # to keep in-game and TUI input identical for the program.
        text = self.input.strip()
        try:
            self.client.send_terminal((text + "\n").encode("utf-8"))
        except (NanocError, OSError):
            self._stop.set()
        self.input = ""

    # -- drawing -----------------------------------------------------------
    def _draw(self, stdscr, cmap: "ColorMap") -> None:
        height, width = stdscr.getmaxyx()
        stdscr.erase()
        if height < self.screen.size_y + 2 or width < 20:
            self._center(stdscr, "terminal too small")
            stdscr.refresh()
            return
        for y in range(self.screen.size_y):
            x = 0
            for text, fg, bg in self.screen.runs(y):
                if x >= width:
                    break
                text = text[:width - x]
                try:
                    stdscr.addstr(y, x, text, cmap.attr(fg, bg))
                except curses.error:
                    pass
                x += len(text)
        self._hline(stdscr, self.screen.size_y, width)
        status = self.status
        if self._last_debug:
            status += "   |   " + self._last_debug
        if self._last_log:
            status += "   |   log: " + self._last_log
        stdscr.addstr(self.screen.size_y, 0, status[:width - 1],
                      curses.A_REVERSE)
        prompt = "> " + self.input
        try:
            stdscr.addstr(self.screen.size_y + 1, 0, prompt[:width - 1])
            stdscr.move(self.screen.size_y + 1, min(len(prompt), width - 2))
        except curses.error:
            pass
        stdscr.refresh()

    @staticmethod
    def _hline(stdscr, y, width) -> None:
        try:
            stdscr.addstr(y, 0, " " * (width - 1), curses.A_REVERSE)
        except curses.error:
            pass

    @staticmethod
    def _center(stdscr, text) -> None:
        height, width = stdscr.getmaxyx()
        try:
            stdscr.addstr(height // 2, max(0, (width - len(text)) // 2), text)
        except curses.error:
            pass

    # -- main --------------------------------------------------------------
    def run(self, stdscr) -> None:
        curses.raw()          # no line buffering / echo / flow control
        curses.noecho()
        curses.curs_set(1)
        stdscr.keypad(True)
        cmap = ColorMap(stdscr)
        try:
            curses.mousemask(0)
        except curses.error:
            pass
        stdscr.timeout(100)
        threading.Thread(target=self._reader, daemon=True).start()
        while not self._stop.is_set():
            try:
                self._drain()
                self._draw(stdscr, cmap)
                try:
                    ch = stdscr.get_wch()
                except curses.error:
                    continue      # timeout: loop to poll events
                self._handle_key(ch)
            except KeyboardInterrupt:
                self._stop.set()
        if self.client is not None:
            self.client.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="nanoc-tui", description="NanoC terminal TUI (curses)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=41100)
    ap.add_argument("--token", default="")
    ap.add_argument("--tls", action="store_true")
    ap.add_argument("--server-hostname", default=None)
    args = ap.parse_args(argv)

    if curses is None:
        print("error: the 'curses' module is unavailable.\n"
              "  Windows: pip install windows-curses\n"
              "  Linux/macOS/Android: usually built in", file=sys.stderr)
        return 2

    # get_wch() needs a UTF-8 aware locale for umlauts etc.
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass

    tui = Tui(args)
    try:
        tui.connect()
    except (NanocError, OSError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    try:
        curses.wrapper(tui.run)
    finally:
        if tui.client is not None:
            try:
                tui.client.close()
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
