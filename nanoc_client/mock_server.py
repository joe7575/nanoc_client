"""Mock NanoC server for testing the client (protocol version 1).

Speaks the same TCP wire protocol as the Luanti-side bridge will
(see nanoc_lib/doc/protocol.md), but simulates a tiny VM: a counter that
prints once per second, a few variables, and single-step/breakpoint support.

Run:  python -m nanoc_client.mock_server --port 40000 --token secret
"""

from __future__ import annotations

import argparse
import socket
import threading
import time

from . import protocol as p


def _words_to_ascii(words):
    return "".join(chr(w & 0xFF) for w in words)


def _ascii_to_words(s):
    return [ord(c) for c in s]


class MockServer:
    def __init__(self, host="127.0.0.1", port=40000, token="secret"):
        self.host = host
        self.port = port
        self.token = token
        self._sock = None
        self._conn = None
        self._running = False
        self._sendlock = threading.Lock()
        self._session = 0

        # simulated VM state
        self.pc = 100
        self.line = 1
        self.mode = p.Mode.RUN
        self.reason = p.HaltReason.NONE
        self.halted = False
        self.counter = 0
        self.breakpoints = set()
        self.variables = [("count", p.VarKind.INT, 0), ("name", p.VarKind.STR, 0)]

    # -- lifecycle ----------------------------------------------------------
    def serve_forever(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(1)
        print(f"[mock] listening on {self.host}:{self.port} (token={self.token!r})")
        self._running = True
        while self._running:
            conn, addr = self._sock.accept()
            print(f"[mock] client {addr}")
            self._conn = conn
            try:
                self._handle(conn)
            except (OSError, ConnectionError):
                pass
            finally:
                conn.close()
                self._conn = None
                print("[mock] client gone")

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    # -- framing ------------------------------------------------------------
    def _send(self, channel, payload, session=None):
        if not self._conn:
            return
        frame = p.Frame(channel=channel, payload=payload,
                        session=self._session if session is None else session).pack()
        with self._sendlock:
            self._conn.sendall(frame)

    def _recv_exact(self, conn, n):
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("closed")
            buf += chunk
        return buf

    def _recv(self, conn):
        header = p.Frame.parse_header(self._recv_exact(conn, p.HEADER_SIZE))
        payload = self._recv_exact(conn, header.length) if header.length else b""
        return header.channel, payload

    # -- handling -----------------------------------------------------------
    def _handle(self, conn):
        channel, payload = self._recv(conn)
        if channel is not p.Channel.CONTROL:
            return
        client_protocol, token = p.decode_hello(payload)
        if client_protocol != p.PROTOCOL:
            self._send(p.Channel.CONTROL, p.encode_hello_ack(p.HelloStatus.BAD_PROTOCOL, p.PROTOCOL))
            return
        if token != self.token:
            self._send(p.Channel.CONTROL, p.encode_hello_ack(p.HelloStatus.BAD_TOKEN, p.PROTOCOL))
            return
        self._send(p.Channel.CONTROL, p.encode_hello_ack(p.HelloStatus.OK, p.PROTOCOL))

        sender = threading.Thread(target=self._terminal_loop, args=(conn,), daemon=True)
        sender.start()

        while self._running:
            channel, payload = self._recv(conn)
            if channel is p.Channel.DEBUG:
                cmd, data = p.decode_debug(payload)
                self._debug(conn, cmd, data)
            elif channel is p.Channel.TERMINAL:
                # key input: echo it back as output
                self._send(p.Channel.TERMINAL, b"> " + payload)

    def _debug(self, conn, cmd, data):
        resp = [int(cmd), int(p.Status.OK)]

        if cmd == p.Command.ATTACH:
            self.halted = False
            self.mode = p.Mode.RUN
            resp += [int(self.mode), int(self.reason), self.line, self.pc]
        elif cmd == p.Command.DETACH:
            pass
        elif cmd == p.Command.STATE:
            resp += [int(self.mode), int(self.reason), self.line, self.pc]
        elif cmd == p.Command.BP_SET:
            line = data[0]
            self.breakpoints.add(line)
            resp += [line]
        elif cmd == p.Command.BP_CLR:
            self.breakpoints.discard(data[0])
        elif cmd == p.Command.BP_CLR_ALL:
            self.breakpoints.clear()
        elif cmd == p.Command.HALT:
            self.halted = True
            self.mode = p.Mode.HALTED
            self.reason = p.HaltReason.HALT
            resp += []
        elif cmd == p.Command.CONTINUE:
            self.halted = False
            self.mode = p.Mode.RUN
        elif cmd in (p.Command.STEP, p.Command.STEP_OVER, p.Command.STEP_OUT):
            self._step(cmd)
            resp = [int(cmd), int(p.Status.OK), int(self.mode), int(self.reason), self.line, self.pc]
        elif cmd == p.Command.VAR_INFO:
            scope = data[0] if data else 0
            index = data[1] if len(data) > 1 else 0
            if scope == 0 and index < len(self.variables):
                name, kind, value = self.variables[index]
                val = str(value)
                resp = ([int(cmd), int(p.Status.OK), int(kind), len(name)]
                        + _ascii_to_words(name) + [len(val)] + _ascii_to_words(val))
            else:
                resp = [int(cmd), int(p.Status.END)]
        elif cmd == p.Command.VAR_WRITE:
            pass
        elif cmd == p.Command.BACKTRACE:
            resp = [int(cmd), int(p.Status.OK), 2, 2, 10, 1, 0]
        else:
            resp = [int(cmd), int(p.Status.UNKNOWN_CMD)]

        self._send(p.Channel.DEBUG, p.encode_words(resp), session=self._session)

        # after a step/continue that hit a breakpoint, emit a HALTED event
        if cmd in (p.Command.STEP, p.Command.STEP_OVER, p.Command.STEP_OUT,
                   p.Command.CONTINUE, p.Command.HALT):
            if self.halted and cmd != p.Command.HALT:
                self._send(p.Channel.DEBUG, p.encode_words(
                    [int(p.Event.HALTED), int(self.reason), self.line, self.pc]),
                    session=self._session)

    def _step(self, cmd):
        self.pc += 1
        self.line += 1
        self.halted = True
        if self.line in self.breakpoints:
            self.reason = p.HaltReason.BREAKPOINT
        elif cmd == p.Command.STEP_OVER:
            self.reason = p.HaltReason.STEP
        else:
            self.reason = p.HaltReason.STEP
        self.mode = p.Mode.STEP

    def _terminal_loop(self, conn):
        while self._running and self._conn is conn:
            time.sleep(1.0)
            if not self.halted:
                self.counter += 1
                if self.variables:
                    name, kind, _ = self.variables[0]
                    self.variables[0] = (name, kind, self.counter)
            text = f"tick {self.counter} (line {self.line}, pc {self.pc})\r\n"
            try:
                self._send(p.Channel.TERMINAL, text.encode(), session=self._session)
            except OSError:
                return


def main(argv=None):
    ap = argparse.ArgumentParser(prog="nanoc-mock-server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=40000)
    ap.add_argument("--token", default="secret")
    args = ap.parse_args(argv)
    srv = MockServer(args.host, args.port, args.token)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.stop()


if __name__ == "__main__":
    main()
