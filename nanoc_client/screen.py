"""Termlib screen emulator (shared intermediate representation).

The NanoC controller writes its terminal output as a byte stream. When a
termlib terminal is connected, that stream follows termlib's own syntax:
control characters, ``ESC`` sequences (1..7) and internal ``@`` commands
(see the termlib mod's ``api.lua``/``commands.lua``).

This module is the *single parser* for that syntax. It maintains a 20x120
cell grid and offers renderers for the different front ends:

* :meth:`Screen.render_text`  - plain text
* :meth:`Screen.render_ansi`  - ANSI/SGR (colours), for terminals / Tk
* :meth:`Screen.changed_rows` - only the rows that changed since the last
  frame, for log-style consumers (VS Code Debug Console, CLI)

The in-game Luanti renderer lives in the termlib mod (Lua) and consumes the
same byte syntax directly, so no Python is involved there.

Colour extension (client only, reserved)
----------------------------------------
termlib has no colour commands. We reserve two extra escapes that termlib
currently ignores (it would print them literally in-game):

* ``ESC 8 <fg>`` - set foreground colour (0..15, 255 = default)
* ``ESC 9 <bg>`` - set background colour (0..15, 255 = default)

Programs that do not use them stay 100%% compatible with the in-game
terminal; front ends that support colour (ANSI/Tk) render them.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

DEFAULT_SIZE_X = 120
DEFAULT_SIZE_Y = 20

DEFAULT_COLOR = 255
Color = Tuple[int, int]  # (fg, bg)

# termlib's help text (shown by the internal @help command). The backslash
# sequences are literal text here, exactly as in termlib/commands.lua.
HELP_TEXT = (
    "Escape Sequences:\n"
    "\n"
    " Chars            | Description\n"
    "------------------+-------------------------------------\n"
    " \\27\\1            | Clear screen\n"
    " \\27\\2\\<row>      | Set cursor to row <row> (1 - 20)\n"
    " \\27\\3\\<font>     | 0 = normal, 1 = mono\n"
    " \\27\\4\\<cmnd>\\n   | Execute the command\n"
    " \\27\\5\\1          | suppress further terminal output\n"
    " \\27\\5\\2          | force the terminal output\n"
    " \\n               | New line + Carriage Return\n"
    " \\t               | Tab (8 chars)\n"
    " \\r               | Carriage Return (rewrite line)\n"
    " \\a               | bell (sound)\n"
    " \\b               | Clear screen\n"
)


def _ansi_color(idx: int) -> int:
    """Map a small colour index to an ANSI colour number (30..37/90..97)."""
    if 0 <= idx <= 7:
        return 30 + idx
    if 8 <= idx <= 15:
        return 90 + (idx - 8)
    return 39  # default foreground


class Screen:
    """20x120 (default) termlib screen buffer."""

    def __init__(self, size_x: int = DEFAULT_SIZE_X, size_y: int = DEFAULT_SIZE_Y):
        self.size_x = size_x
        self.size_y = size_y
        self.bell = False
        self.clear_screen()

    # -- state -------------------------------------------------------------
    def clear_screen(self) -> None:
        self.lines: List[bytearray] = [bytearray() for _ in range(self.size_y)]
        self.attrs: List[List[Color]] = [[] for _ in range(self.size_y)]
        self.temp = bytearray()          # line 0: command / insert buffer
        self.temp_attr: List[Color] = []
        self.cursor_row = 1
        self.escaped = False
        self.esc_cmnd: Optional[int] = None
        self.insert_pos: Optional[int] = None
        self.insert_row: Optional[int] = None
        self.font = "mono"               # termlib default
        self.suppressed = False
        self.pen: Color = (DEFAULT_COLOR, DEFAULT_COLOR)
        self._dirty = True

    # -- helpers -----------------------------------------------------------
    def _current(self):
        if self.cursor_row == 0:
            return self.temp, self.temp_attr
        i = self.cursor_row - 1
        return self.lines[i], self.attrs[i]

    def _mark(self, force: bool = False) -> None:
        if force or not self.suppressed:
            self._dirty = True

    def _put(self, byte: int) -> None:
        line, attr = self._current()
        if len(line) < self.size_x:
            line.append(byte)
            attr.append(self.pen)
            self._mark()

    def _clear_row(self, row: int) -> None:
        if row == 0:
            self.temp = bytearray()
            self.temp_attr = []
        else:
            i = min(row, self.size_y) - 1
            self.lines[i] = bytearray()
            self.attrs[i] = []
        self._mark(force=True)

    def _clear_all(self) -> None:
        for i in range(self.size_y):
            self.lines[i] = bytearray()
            self.attrs[i] = []
        self.cursor_row = 1
        self._mark(force=True)

    # -- termlib operations ------------------------------------------------
    def _new_line(self) -> Optional[bool]:
        # Lua's `or` treats 0 as truthy; keep row 0 (command/insert buffer).
        if self.cursor_row is None:
            self.cursor_row = 1
        if self.insert_pos is not None:
            row = min(self.insert_row or 1, self.size_y)
            i = row - 1
            base, base_attr = self.lines[i], self.attrs[i]
            pos = min(self.insert_pos, self.size_x) - 1
            ins = bytes(self.temp)
            ins_attr = self.temp_attr
            self.lines[i] = base[:pos] + ins + base[pos + len(ins):]
            self.attrs[i] = base_attr[:pos] + ins_attr + base_attr[pos + len(ins):]
            self.temp = bytearray()
            self.temp_attr = []
            self.insert_pos = None
            self.insert_row = None
            self.cursor_row = row
            self._mark(force=True)
            return None
        if self.cursor_row == 0:
            cmd = self.temp.decode("latin-1")
            self.temp = bytearray()
            self.temp_attr = []
            self.cursor_row = 1
            self._command(cmd)
            return None
        if self.cursor_row < self.size_y:
            self.cursor_row += 1
            return True
        # scroll up: drop first visible line, append an empty one
        self.lines.pop(0)
        self.attrs.pop(0)
        self.lines.append(bytearray())
        self.attrs.append([])
        return True

    def _command(self, cmd: str) -> None:
        cmd = cmd.strip()
        name = cmd.split(" ", 1)[0] if cmd else ""
        if name == "@cls":
            self._clear_all()
        elif name == "@help":
            self._clear_all()
            for b in HELP_TEXT.encode("latin-1"):
                self._feed_byte(b)

    def _ctrl(self, byte: int) -> bool:
        if byte == 0:
            return False
        if byte == 7:                      # bell
            self.bell = True
            return False
        if byte == 8:                      # clear screen
            self._clear_all()
            return True
        if byte == 9:                      # tab to next multiple of 8
            line, attr = self._current()
            n = 8 - (len(line) % 8)
            for _ in range(n):
                line.append(0x20)
                attr.append(self.pen)
            self._mark()
            return False
        if byte == 10:                     # new line
            if self._new_line():
                self._clear_row(self.cursor_row)
            return not self.suppressed
        if byte == 13:                     # carriage return (rewrite line)
            self._clear_row(self.cursor_row)
            return False
        if byte == 27:                     # escape
            self.escaped = True
            return False
        return False

    def _escape(self, byte: int) -> bool:
        if self.esc_cmnd is None:
            if byte == 1:                  # clear screen
                self._clear_all()
                self.escaped = False
                return True
            if byte == 4:                  # command line mode
                self.cursor_row = 0
                self.temp = bytearray()
                self.temp_attr = []
                self.escaped = False
                return False
            if byte == 7:                  # clear line, cursor up
                self.cursor_row = max(self.cursor_row - 1, 1)
                self._clear_row(self.cursor_row)
                self.escaped = False
                return False
            self.esc_cmnd = byte
            return False
        if self.insert_pos is not None:    # ESC 6 <pos> <row>: the <row> byte
            self.insert_row = min(byte, self.size_y)
            self.cursor_row = 0
            self.temp = bytearray()
            self.temp_attr = []
            self.esc_cmnd = None
            self.escaped = False
            return False
        cmd = self.esc_cmnd
        if cmd == 2:                       # set cursor row
            self.cursor_row = min(byte, self.size_y)
            self._clear_row(self.cursor_row)
        elif cmd == 3:                     # font
            self.font = "normal" if byte == 0 else "mono"
        elif cmd == 5:                     # suppress / force
            self.suppressed = byte == 1
            self._mark(force=True)
            self.esc_cmnd = None
            self.escaped = False
            return byte == 2
        elif cmd == 6:                     # insert position (keep escape)
            self.insert_pos = min(byte, self.size_x)
            return False
        elif cmd == 8:                     # colour extension: foreground
            self.pen = (byte, self.pen[1])
        elif cmd == 9:                     # colour extension: background
            self.pen = (self.pen[0], byte)
        else:                              # unknown: print it literally
            self._put(27)
            self._put(cmd)
            self._put(byte)
        self.esc_cmnd = None
        self.escaped = False
        return False

    def _feed_byte(self, byte: int) -> None:
        if self.escaped:
            if self._escape(byte):
                self._dirty = True
        elif byte < 32:
            if self._ctrl(byte):
                self._dirty = True
        else:
            self._put(byte)

    # -- public ------------------------------------------------------------
    def feed(self, data: bytes) -> bool:
        """Process a chunk; returns True if the visible screen changed."""
        self._dirty = False
        for byte in data:
            self._feed_byte(byte)
        return self._dirty

    def take_bell(self) -> bool:
        b = self.bell
        self.bell = False
        return b

    def row_text(self, row: int) -> str:
        return self.lines[row].decode("utf-8", "replace")

    def render_text(self) -> str:
        return "\n".join(self.row_text(i) for i in range(self.size_y))

    def runs(self, row: int):
        """Return character-level ``(text, fg, bg)`` runs for a row.

        UTF-8 bytes are grouped per pen, so a multi-byte character is never
        split (the pen can only change between characters).
        """
        line = self.lines[row]
        attrs = self.attrs[row]
        default = (DEFAULT_COLOR, DEFAULT_COLOR)
        result = []
        start = 0
        cur = attrs[0] if attrs else default
        for i in range(1, len(line) + 1):
            nxt = attrs[i] if i < len(attrs) else default
            if i == len(line) or nxt != cur:
                text = bytes(line[start:i]).decode("utf-8", "replace")
                result.append((text, cur[0], cur[1]))
                start = i
                cur = nxt
        return result

    def _render_row(self, row: int, color: bool) -> str:
        line = self.lines[row]
        if not color or not any(
                a != (DEFAULT_COLOR, DEFAULT_COLOR) for a in self.attrs[row]):
            return line.decode("utf-8", "replace")
        parts = []
        for text, fg, bg in self.runs(row):
            if fg == DEFAULT_COLOR and bg == DEFAULT_COLOR:
                parts.append(text)
            else:
                parts.append(self._sgr((fg, bg)) + text + "\x1b[0m")
        return "".join(parts)

    @staticmethod
    def _sgr(color: Optional[Color]) -> str:
        if not color:
            return ""
        fg, bg = color
        codes = []
        if fg != DEFAULT_COLOR:
            codes.append(str(_ansi_color(fg)))
        if bg != DEFAULT_COLOR:
            codes.append(str(_ansi_color(bg) + 10))
        return "\x1b[" + ";".join(codes) + "m" if codes else ""

    def render_ansi(self, color: bool = True, home: bool = False) -> str:
        body = "\n".join(self._render_row(i, color) for i in range(self.size_y))
        return ("\x1b[H" + body) if home else body

    def changed_rows(self, last: Optional[Sequence[bytes]], color: bool = True):
        """Return (row, text) for rows changed since ``last`` (a list of bytes)."""
        result = []
        for i in range(self.size_y):
            cur = bytes(self.lines[i])
            if last is None or last[i] != cur:
                result.append((i, self._render_row(i, color)))
        return result

    def snapshot(self) -> List[bytes]:
        return [bytes(line) for line in self.lines]
