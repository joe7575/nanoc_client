import contextlib
import io
import os
import socket
import tempfile
import threading
import time
import unittest

from nanoc_client import nanoc
from nanoc_client.mock_server import MockServer


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = nanoc.main(argv)
    return code, out.getvalue(), err.getvalue()


class TestNanocCli(unittest.TestCase):
    def setUp(self):
        self.port = free_port()
        self.srv = MockServer("127.0.0.1", self.port, "tok")
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        time.sleep(0.3)
        fd, self.path = tempfile.mkstemp(suffix=".nanoc", text=True)
        with os.fdopen(fd, "w") as f:
            f.write("int32 a = 1\nprintf(\"%d\\n\", a)\n")

    def tearDown(self):
        self.srv.stop()
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_check(self):
        code, out, _ = run_main(["check", self.path])
        self.assertEqual(code, 0)

    def test_push(self):
        code, out, err = run_main(
            ["push", self.path, "--port", str(self.port), "--token", "tok"])
        self.assertEqual(code, 0, err)
        self.assertIn("uploaded", out)

    def test_exec_reads_output(self):
        code, out, err = run_main(
            ["exec", self.path, "--port", str(self.port), "--token", "tok",
             "--seconds", "1.3"])
        self.assertEqual(code, 0, err)
        self.assertIn("tick", out)

    def test_scan(self):
        code, out, err = run_main(
            ["scan", "--port", str(self.port), "--token", "tok"])
        self.assertEqual(code, 0, err)
        self.assertIn("techage:ta4_chest", out)
        self.assertIn("edges", out)

    def test_catalog(self):
        code, out, err = run_main(
            ["catalog", "--port", str(self.port), "--token", "tok"])
        self.assertEqual(code, 0, err)
        self.assertIn("chest state", out)

    def test_run_denied_when_busy(self):
        self.srv.stop()
        port = free_port()
        srv = MockServer("127.0.0.1", port, "tok", deny_attach=True)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        time.sleep(0.3)
        try:
            code, out, err = run_main(
                ["run", "--port", str(port), "--token", "tok"])
            self.assertEqual(code, 2)
            self.assertIn("busy", err)
        finally:
            srv.stop()


if __name__ == "__main__":
    unittest.main()
