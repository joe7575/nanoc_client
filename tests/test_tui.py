import unittest

from nanoc_client import tui
from nanoc_client.screen import Screen


class FakeClient:
    def __init__(self):
        self.sent = []

    def send_terminal(self, data):
        self.sent.append(data)


def make_tui():
    args = type("Args", (), {
        "host": "127.0.0.1", "port": 1, "token": "",
        "tls": False, "server_hostname": None,
    })()
    t = tui.Tui(args)
    t.client = FakeClient()
    return t


@unittest.skipIf(tui.curses is None, "curses not available")
class TestKeyHandling(unittest.TestCase):
    def test_function_key_bytes(self):
        self.assertEqual(tui.function_key_bytes(1), b"\x80\n")
        self.assertEqual(tui.function_key_bytes(8), b"\x87\n")

    def test_type_and_backspace(self):
        t = make_tui()
        t._handle_key("a")
        t._handle_key("b")
        self.assertEqual(t.input, "ab")
        t._handle_key("\x7f")
        self.assertEqual(t.input, "a")

    def test_utf8_input(self):
        t = make_tui()
        t._handle_key("ö")
        t._handle_key("ä")
        self.assertEqual(t.input, "öä")

    def test_enter_sends_line(self):
        t = make_tui()
        for ch in "hi":
            t._handle_key(ch)
        t._handle_key("\n")
        self.assertEqual(t.client.sent, [b"hi\n"])
        self.assertEqual(t.input, "")

    def test_line_is_trimmed(self):
        t = make_tui()
        for ch in "  hi there  ":
            t._handle_key(ch)
        t._handle_key("\n")
        self.assertEqual(t.client.sent, [b"hi there\n"])

    def test_function_key_sends(self):
        t = make_tui()
        t._handle_key(tui.curses.KEY_F3)
        self.assertEqual(t.client.sent, [tui.function_key_bytes(3)])

    def test_ctrl_q_quits(self):
        t = make_tui()
        self.assertFalse(t._stop.is_set())
        t._handle_key("\x11")
        self.assertTrue(t._stop.is_set())


class TestScreenRuns(unittest.TestCase):
    def test_runs_default(self):
        s = Screen(size_x=10, size_y=2)
        s.feed("öä".encode("utf-8"))
        self.assertEqual(s.runs(0), [("öä", 255, 255)])

    def test_runs_with_color(self):
        s = Screen(size_x=10, size_y=2)
        s.feed(b"ab" + bytes([27, 8, 1]) + b"cd")
        self.assertEqual(s.runs(0), [("ab", 255, 255), ("cd", 1, 255)])


if __name__ == "__main__":
    unittest.main()
