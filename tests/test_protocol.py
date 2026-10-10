import unittest

from nanoc_client import protocol as p


class TestFraming(unittest.TestCase):
    def test_frame_roundtrip(self):
        f = p.Frame(channel=p.Channel.DEBUG, payload=b"abc", session=7)
        raw = f.pack()
        self.assertEqual(len(raw), p.HEADER_SIZE + 3)
        header = p.Frame.parse_header(raw[:p.HEADER_SIZE])
        self.assertEqual(header.channel, p.Channel.DEBUG)
        self.assertEqual(header.session, 7)
        self.assertEqual(header.length, 3)

    def test_bad_magic(self):
        raw = bytearray(p.Frame(p.Channel.TERMINAL, b"").pack())
        raw[0] = 0
        with self.assertRaises(ValueError):
            p.Frame.parse_header(bytes(raw[:p.HEADER_SIZE]))


class TestDebug(unittest.TestCase):
    def test_debug_roundtrip(self):
        payload = p.encode_debug(p.Command.BP_SET, 42)
        cmd, data = p.decode_debug(payload)
        self.assertEqual(cmd, p.Command.BP_SET)
        self.assertEqual(data, [42])

    def test_empty_debug(self):
        with self.assertRaises(ValueError):
            p.decode_debug(b"")


class TestHandshake(unittest.TestCase):
    def test_hello_roundtrip(self):
        payload = p.encode_hello(p.PROTOCOL, "tok3n")
        proto, token = p.decode_hello(payload)
        self.assertEqual(proto, p.PROTOCOL)
        self.assertEqual(token, "tok3n")

    def test_ack_roundtrip(self):
        payload = p.encode_hello_ack(p.HelloStatus.OK, p.PROTOCOL)
        status, proto = p.decode_hello_ack(payload)
        self.assertEqual(status, p.HelloStatus.OK)
        self.assertEqual(proto, p.PROTOCOL)


if __name__ == "__main__":
    unittest.main()
