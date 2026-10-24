import hashlib
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest

from nanoc_client.client import NanocClient, NanocError
from nanoc_client.mock_server import MockServer


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@unittest.skipUnless(shutil.which("openssl"), "openssl command not available")
class TestTlsClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="nanoc-tls-")
        cls.cert = os.path.join(cls.dir, "cert.pem")
        cls.key = os.path.join(cls.dir, "key.pem")
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
             "-keyout", cls.key, "-out", cls.cert, "-days", "1",
             "-subj", "/CN=localhost",
             "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"],
            check=True, capture_output=True)
        der = ssl.PEM_cert_to_DER_cert(open(cls.cert).read())
        cls.fingerprint = hashlib.sha256(der).hexdigest()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def setUp(self):
        self.port = free_port()
        self.srv = MockServer("127.0.0.1", self.port, "tok", tls=True,
                              certfile=self.cert, keyfile=self.key)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        time.sleep(0.3)

    def tearDown(self):
        self.srv.stop()

    def _connect(self, **kwargs):
        client = NanocClient("127.0.0.1", self.port, "tok", tls=True,
                             timeout=5.0, **kwargs)
        client.connect()
        return client

    def test_cafile(self):
        c = self._connect(cafile=self.cert, server_hostname="localhost")
        c.close()

    def test_insecure(self):
        c = self._connect(tls_insecure=True)
        c.close()

    def test_fingerprint(self):
        c = self._connect(tls_fingerprint=self.fingerprint)
        c.close()

    def test_fingerprint_colons(self):
        fp = ":".join(self.fingerprint[i:i + 2]
                      for i in range(0, len(self.fingerprint), 2))
        c = self._connect(tls_fingerprint=fp)
        c.close()

    def test_fingerprint_mismatch(self):
        with self.assertRaises(NanocError):
            self._connect(tls_fingerprint="00" * 32)

    def test_plain_client_fails(self):
        with self.assertRaises((OSError, NanocError)):
            NanocClient("127.0.0.1", self.port, "tok",
                        timeout=2.0).connect()


if __name__ == "__main__":
    unittest.main()
