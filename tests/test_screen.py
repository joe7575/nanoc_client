import unittest

from nanoc_client.screen import DEFAULT_COLOR, Screen

ESC = 27


def e(*values):
    return bytes([ESC, *values])


class TestText(unittest.TestCase):
    def test_simple_lines(self):
        s = Screen(size_x=10, size_y=3)
        s.feed(b"hello\nworld\n")
        self.assertEqual(s.row_text(0), "hello")
        self.assertEqual(s.row_text(1), "world")
        self.assertEqual(s.row_text(2), "")

    def test_utf8(self):
        s = Screen(size_x=10, size_y=2)
        s.feed("öäü".encode("utf-8"))
        self.assertEqual(s.row_text(0), "öäü")

    def test_tab(self):
        s = Screen(size_x=20, size_y=2)
        s.feed(b"A\tB")
        self.assertEqual(s.row_text(0), "A" + 7 * " " + "B")

    def test_carriage_return(self):
        s = Screen(size_x=20, size_y=2)
        s.feed(b"progress: 0%\rprogress: 100%")
        self.assertEqual(s.row_text(0), "progress: 100%")

    def test_bell(self):
        s = Screen(size_x=10, size_y=2)
        s.feed(b"\a")
        self.assertTrue(s.take_bell())
        self.assertFalse(s.take_bell())


class TestControlEscapes(unittest.TestCase):
    def test_backspace_clears_screen(self):
        s = Screen(size_x=10, size_y=2)
        s.feed(b"abc\n")
        s.feed(b"\b")                      # 8 = clear screen
        self.assertEqual(s.row_text(0), "")

    def test_esc_clear(self):
        s = Screen(size_x=10, size_y=2)
        s.feed(b"abc\n")
        s.feed(e(1))
        self.assertEqual(s.row_text(0), "")

    def test_esc_set_row(self):
        s = Screen(size_x=10, size_y=5)
        s.feed(e(2, 3) + b"row3")
        self.assertEqual(s.row_text(2), "row3")

    def test_esc_font(self):
        s = Screen(size_x=10, size_y=2)
        self.assertEqual(s.font, "mono")
        s.feed(e(3, 0))
        self.assertEqual(s.font, "normal")
        s.feed(e(3, 1))
        self.assertEqual(s.font, "mono")

    def test_esc_clear_line_up(self):
        s = Screen(size_x=10, size_y=5)
        s.feed(b"lineA\nlineB\n")
        s.feed(e(7) + b"X\n")
        self.assertEqual(s.row_text(0), "lineA")
        self.assertEqual(s.row_text(1), "X")

    def test_suppress_then_force(self):
        s = Screen(size_x=20, size_y=3)
        s.feed(e(5, 1) + b"hidden\n")
        self.assertEqual(s.row_text(0), "hidden")   # stored ...
        s.feed(e(5, 2))                              # ... forced visible
        self.assertIn("hidden", s.render_text())
        self.assertFalse(s.suppressed)


class TestInsert(unittest.TestCase):
    def test_esc_insert(self):
        s = Screen(size_x=20, size_y=6)
        s.feed(e(2, 5) + b"ABCDEFGHIJ\n")   # base line in row 5
        s.feed(e(6, 5, 5) + b"xyz\n")       # insert at pos 5, row 5
        self.assertEqual(s.row_text(4), "ABCDxyzHIJ")


class TestColor(unittest.TestCase):
    def test_default_renders_plain(self):
        s = Screen(size_x=10, size_y=2)
        s.feed(b"Hi")
        self.assertEqual(s.render_ansi().split("\n")[0], "Hi")

    def test_foreground(self):
        s = Screen(size_x=10, size_y=2)
        s.feed(b"Hi")
        s.feed(e(8, 1) + b"X")             # fg = 1 (red)
        row = s.render_ansi().split("\n")[0]
        self.assertEqual(row, "Hi\x1b[31mX\x1b[0m")

    def test_background(self):
        s = Screen(size_x=10, size_y=2)
        s.feed(e(9, 2) + b"X")             # bg = 2 (green)
        row = s.render_ansi().split("\n")[0]
        self.assertEqual(row, "\x1b[42mX\x1b[0m")


class TestDiff(unittest.TestCase):
    def test_changed_rows(self):
        s = Screen(size_x=10, size_y=3)
        last = s.snapshot()
        s.feed(b"a\nb\n")
        changed = s.changed_rows(last)
        rows = {i: text for i, text in changed}
        self.assertEqual(rows.get(0), "a")
        self.assertEqual(rows.get(1), "b")
        last = s.snapshot()
        s.feed(b"c")                        # only row 3 (index 2) changes
        rows = {i: text for i, text in s.changed_rows(last)}
        self.assertEqual(rows, {2: "c"})

    def test_command_cls(self):
        s = Screen(size_x=10, size_y=3)
        s.feed(b"abc\n")
        s.feed(e(4) + b"@cls\n")           # ESC 4 = run terminal command
        self.assertEqual(s.render_text().strip(), "")


if __name__ == "__main__":
    unittest.main()
