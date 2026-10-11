"""TCP/TLS client for the NanoC computer."""

from __future__ import annotations

import socket
import ssl
from typing import Optional

from . import protocol as p


class NanocError(Exception):
    pass


class NanocClient:
    """Blocking client. Connects, performs the handshake, then exchanges
    control/debug/terminal frames."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 40000,
        token: str = "",
        tls: bool = False,
        server_hostname: Optional[str] = None,
        timeout: float = 10.0,
        blocking: bool = True,
    ):
        self.host = host
        self.port = port
        self.token = token
        self.tls = tls
        self.server_hostname = server_hostname or host
        self.timeout = timeout
        self.blocking = blocking
        self.session = 0
        self._sock: Optional[socket.socket] = None
        self._buf = b""

    # -- connection ---------------------------------------------------------
    def connect(self) -> None:
        raw = socket.create_connection((self.host, self.port), self.timeout)
        if self.tls:
            ctx = ssl.create_default_context()
            raw = ctx.wrap_socket(raw, server_hostname=self.server_hostname)
        raw.settimeout(self.timeout)
        self._sock = raw
        self._handshake()
        # After the handshake: blocking for interactive readers (default), or
        # keep the timeout for scripted request/response use.
        if self.blocking:
            raw.settimeout(None)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    def _handshake(self) -> None:
        self.send_frame(p.Channel.CONTROL, p.encode_hello(p.PROTOCOL, self.token))
        channel, payload = self.recv_frame()
        if channel is not p.Channel.CONTROL:
            raise NanocError(f"expected CONTROL during handshake, got {channel}")
        status, server_protocol = p.decode_hello_ack(payload)
        if status is not p.HelloStatus.OK:
            raise NanocError(f"handshake failed: {status.name}")
        if server_protocol != p.PROTOCOL:
            raise NanocError(
                f"protocol mismatch: server={server_protocol} client={p.PROTOCOL}"
            )

    # -- framing ------------------------------------------------------------
    def _send_all(self, data: bytes) -> None:
        assert self._sock is not None
        self._sock.sendall(data)

    def send_frame(self, channel: p.Channel, payload: bytes) -> None:
        self._send_all(p.Frame(channel=channel, payload=payload, session=self.session).pack())

    def _recv_exact(self, n: int) -> bytes:
        assert self._sock is not None
        while len(self._buf) < n:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise NanocError("connection closed")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def recv_frame(self):
        header = p.Frame.parse_header(self._recv_exact(p.HEADER_SIZE))
        self.session = header.session
        payload = self._recv_exact(header.length) if header.length else b""
        return header.channel, payload

    # -- debug --------------------------------------------------------------
    def send_debug(self, cmd: p.Command, *data: int) -> None:
        self.send_frame(p.Channel.DEBUG, p.encode_debug(cmd, *data))

    def recv_debug(self):
        channel, payload = self.recv_frame()
        if channel is not p.Channel.DEBUG:
            raise NanocError(f"expected DEBUG, got {channel}")
        return p.decode_debug(payload)

    def attach(self, allow_write: bool = True, user_lines: int = 0):
        self.send_debug(p.Command.ATTACH, 1 if allow_write else 0, user_lines)
        return self.recv_debug()

    def set_breakpoint(self, line: int):
        self.send_debug(p.Command.BP_SET, line)
        return self.recv_debug()

    def clear_breakpoint(self, line: int):
        self.send_debug(p.Command.BP_CLR, line)
        return self.recv_debug()

    def cont(self):
        self.send_debug(p.Command.CONTINUE)
        return self.recv_debug()

    def halt(self):
        self.send_debug(p.Command.HALT)
        return self.recv_debug()

    def step(self):
        self.send_debug(p.Command.STEP)
        return self.recv_debug()

    def step_over(self):
        self.send_debug(p.Command.STEP_OVER)
        return self.recv_debug()

    def step_out(self):
        self.send_debug(p.Command.STEP_OUT)
        return self.recv_debug()

    def variables(self, scope: int = 0):
        self.send_debug(p.Command.VAR_INFO, scope, 0)
        return self.recv_debug()

    def backtrace(self):
        self.send_debug(p.Command.BACKTRACE)
        return self.recv_debug()

    # -- terminal -----------------------------------------------------------
    def send_terminal(self, data: bytes) -> None:
        self.send_frame(p.Channel.TERMINAL, data)
