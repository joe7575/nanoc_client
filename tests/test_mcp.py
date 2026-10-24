import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest

from nanoc_client.mock_server import MockServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestMcpServer(unittest.TestCase):
    def setUp(self):
        self.port = free_port()
        self.srv = MockServer("127.0.0.1", self.port, "tok")
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        time.sleep(0.3)
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "nanoc_client.mcp",
             "--port", str(self.port), "--token", "tok"],
            cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
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

    def _send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def _read(self):
        line = self.proc.stdout.readline()
        self.assertTrue(line, "no MCP response")
        return json.loads(line)

    def _call(self, mid, method, params=None):
        self._send({"jsonrpc": "2.0", "id": mid, "method": method,
                    "params": params or {}})
        return self._read()

    def test_initialize_and_tools(self):
        r = self._call(1, "initialize", {"protocolVersion": "2024-11-05"})
        self.assertEqual(r["result"]["serverInfo"]["name"], "nanoc")
        r = self._call(2, "tools/list")
        names = [t["name"] for t in r["result"]["tools"]]
        self.assertIn("nanoc_scan", names)
        self.assertIn("nanoc_catalog", names)
        self.assertIn("nanoc_exec", names)

    def test_resources(self):
        r = self._call(1, "initialize", {"protocolVersion": "2024-11-05"})
        self.assertIn("resources", r["result"]["capabilities"])
        r = self._call(2, "resources/list")
        uris = [res["uri"] for res in r["result"]["resources"]]
        self.assertIn("nanoc://workflow", uris)
        self.assertIn("nanoc://language", uris)
        self.assertIn("nanoc://topics", uris)
        self.assertIn("nanoc://cookbook", uris)
        self.assertIn("nanoc://examples/factory_control", uris)
        r = self._call(3, "resources/read", {"uri": "nanoc://workflow"})
        text = r["result"]["contents"][0]["text"]
        self.assertIn("nanoc_scan", text)
        r = self._call(4, "resources/read", {"uri": "nanoc://nope"})
        self.assertIn("error", r)

    def test_catalog_tool(self):
        self._call(1, "initialize", {"protocolVersion": "2024-11-05"})
        r = self._call(2, "tools/call",
                       {"name": "nanoc_catalog", "arguments": {}})
        self.assertFalse(r["result"]["isError"])
        self.assertIn("chest state", r["result"]["content"][0]["text"])

    def test_scan_tool(self):
        self._call(1, "initialize", {"protocolVersion": "2024-11-05"})
        r = self._call(2, "tools/call",
                       {"name": "nanoc_scan", "arguments": {"radius": 8}})
        self.assertFalse(r["result"]["isError"])
        self.assertIn("techage:ta4_chest", r["result"]["content"][0]["text"])

    def test_check_and_exec(self):
        self._call(1, "initialize", {"protocolVersion": "2024-11-05"})
        r = self._call(2, "tools/call",
                       {"name": "nanoc_check", "arguments": {"text": "prinf(\"x\")\n"}})
        self.assertIn("unknown function", r["result"]["content"][0]["text"])
        r = self._call(3, "tools/call",
                       {"name": "nanoc_exec",
                        "arguments": {"text": "int32 a = 1\n", "seconds": 1.3}})
        self.assertIn("tick", r["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
