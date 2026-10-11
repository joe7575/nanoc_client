import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from nanoc_client import dap, protocol as p
from nanoc_client.mock_server import MockServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestDapAdapter(unittest.TestCase):
    def setUp(self):
        self.port = free_port()
        self.srv = MockServer("127.0.0.1", self.port, "tok")
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        time.sleep(0.3)
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "nanoc_client.dap"], cwd=REPO,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        )

    def tearDown(self):
        try:
            self.proc.stdin.close()
            self.proc.stdout.close()
        except OSError:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.srv.stop()

    def _send(self, msg):
        body = json.dumps(msg).encode()
        self.proc.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
        self.proc.stdin.flush()

    def _read(self):
        headers = {}
        while True:
            line = self.proc.stdout.readline()
            if line in (b"", b"\r\n", b"\n"):
                break
            key, value = line.decode().split(":", 1)
            headers[key.strip().lower()] = value.strip()
        length = int(headers["content-length"])
        return json.loads(self.proc.stdout.read(length))

    def _request(self, seq, command, arguments=None):
        self._send({"seq": seq, "type": "request", "command": command,
                    "arguments": arguments or {}})
        while True:
            msg = self._read()
            if msg.get("type") == "response" and msg.get("request_seq") == seq:
                return msg

    def test_end_to_end(self):
        r = self._request(1, "initialize")
        self.assertTrue(r["success"])
        self._request(2, "attach", {
            "host": "127.0.0.1", "port": self.port, "token": "tok",
            "source": "prog.nanoc"})
        r = self._request(3, "setBreakpoints", {
            "source": {"path": "prog.nanoc"}, "breakpoints": [{"line": 3}]})
        self.assertTrue(r["body"]["breakpoints"][0]["verified"])
        self._request(4, "configurationDone")
        r = self._request(5, "threads")
        self.assertEqual(r["body"]["threads"][0]["id"], 1)
        r = self._request(6, "stackTrace", {"threadId": 1})
        self.assertGreaterEqual(len(r["body"]["stackFrames"]), 1)
        r = self._request(7, "scopes", {"frameId": 1})
        self.assertEqual(r["body"]["scopes"][0]["name"], "Globals")
        r = self._request(8, "variables", {"variablesReference": 1})
        names = [v["name"] for v in r["body"]["variables"]]
        self.assertIn("count", names)
        r = self._request(9, "continue", {"threadId": 1})
        self.assertTrue(r["success"])
        r = self._request(10, "nanoc/download")
        self.assertIn("int32", r["body"]["text"])
        r = self._request(11, "nanoc/upload", {"text": "int32 x = 5\n"})
        self.assertTrue(r["success"])
        r = self._request(12, "nanoc/download")
        self.assertEqual(r["body"]["text"], "int32 x = 5\n")
        r = self._request(13, "nanoc/upload", {"text": "SYNTAX_ERROR\n"})
        self.assertFalse(r["success"])
        self.assertTrue(self._request(14, "disconnect")["success"])


    def test_upload_on_start(self):
        fd, path = tempfile.mkstemp(suffix=".nanoc", text=True)
        with os.fdopen(fd, "w") as f:
            f.write("int32 x = 7\n")
        try:
            self._request(1, "initialize")
            self._request(2, "attach", {
                "host": "127.0.0.1", "port": self.port, "token": "tok",
                "program": path, "source": path, "upload": True})
            self._request(3, "configurationDone")
            time.sleep(0.2)
            self.assertIn("int32 x = 7", self.srv.program)
        finally:
            os.unlink(path)


class _FakeClient:
    def __init__(self, frames):
        self._frames = list(frames)

    def recv_frame(self):
        if self._frames:
            return self._frames.pop(0)
        raise OSError("done")


class _CaptureDap(dap.DapServer):
    def __init__(self):
        super().__init__()
        self.outputs = []

    def send_event(self, event, body=None):
        if event == "output" and body:
            self.outputs.append(body.get("output", ""))


class TestTerminalInConsole(unittest.TestCase):
    def _run(self, terminal_in_console):
        srv = _CaptureDap()
        srv._terminal_in_console = terminal_in_console
        srv.client = _FakeClient([(p.Channel.TERMINAL, b"hello world\n")])
        srv._running = True
        srv._reader_loop()          # stops on the OSError after the frame
        return "".join(srv.outputs)

    def test_default_off(self):
        self.assertFalse(dap.DapServer()._terminal_in_console)

    def test_off_keeps_console_clean(self):
        self.assertNotIn("hello world", self._run(False))

    def test_on_mirrors_output(self):
        self.assertIn("hello world", self._run(True))

    def test_log_channel_goes_to_console(self):
        srv = _CaptureDap()
        srv.client = _FakeClient([(p.Channel.LOG, b"a log line\n")])
        srv._running = True
        srv._reader_loop()
        self.assertIn("a log line", "".join(srv.outputs))


if __name__ == "__main__":
    unittest.main()
