"""Debug Adapter Protocol (DAP) server for NanoC.

Speaks DAP over stdio (as launched by VS Code / vim) and translates requests
into the NanoC wire protocol on the remote bridge (see
nanoc_lib/doc/protocol.md). This lets any DAP-capable editor debug a NanoC
controller with full syntax highlighting and the editor's own UI.

Run:  nanoc-dap        (the editor talks to it via stdio)
"""

from __future__ import annotations

import json
import sys
import threading

from . import protocol as p
from .client import NanocClient, NanocError


class DapError(Exception):
    pass


class DapServer:
    def __init__(self):
        self.client = None
        self._seq = 1
        self._out_lock = threading.Lock()
        self._resp_lock = threading.Lock()
        self._resp_cond = threading.Condition(self._resp_lock)
        self._responses = {}
        self._source_path = None
        self._breakpoints = []
        self._last_line = 1
        self._attached_state = None
        self._upload_on_start = False
        self._running = True
        self._reader = None

    # -- DAP framing (stdio) ------------------------------------------------
    def send(self, msg):
        body = json.dumps(msg).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        with self._out_lock:
            sys.stdout.buffer.write(header + body)
            sys.stdout.buffer.flush()

    def send_response(self, request, body=None, success=True, message=None):
        msg = {
            "type": "response",
            "seq": self._next_seq(),
            "request_seq": request.get("seq", 0),
            "success": success,
            "command": request.get("command", ""),
        }
        if body:
            msg["body"] = body
        if message:
            msg["message"] = message
        self.send(msg)

    def send_event(self, event, body=None):
        msg = {"type": "event", "seq": self._next_seq(), "event": event}
        if body is not None:
            msg["body"] = body
        self.send(msg)

    def _next_seq(self):
        with self._out_lock:
            s = self._seq
            self._seq += 1
            return s

    def _read_message(self):
        headers = {}
        while True:
            line = sys.stdin.buffer.readline()
            if line in (b"", b"\r\n", b"\n"):
                break
            try:
                key, value = line.decode("ascii").split(":", 1)
            except ValueError:
                continue
            headers[key.strip().lower()] = value.strip()
        if "content-length" not in headers:
            return None
        length = int(headers["content-length"])
        body = sys.stdin.buffer.read(length)
        if not body:
            return None
        return json.loads(body.decode("utf-8"))

    # -- remote (NanoC bridge) ---------------------------------------------
    def _remote_request(self, cmd, *data, timeout=5.0):
        with self._resp_cond:
            self._responses.pop(int(cmd), None)
        self.client.send_debug(cmd, *data)
        with self._resp_cond:
            ok = self._resp_cond.wait_for(lambda: int(cmd) in self._responses, timeout)
            if not ok:
                raise DapError(f"timeout waiting for {cmd.name}")
            return self._responses.pop(int(cmd))

    def _reader_loop(self):
        try:
            while self._running:
                channel, payload = self.client.recv_frame()
                if channel is p.Channel.TERMINAL:
                    self.send_event("output", {
                        "category": "stdout",
                        "output": payload.decode("utf-8", "replace"),
                    })
                elif channel is p.Channel.DEBUG:
                    cmd, data = p.decode_debug(payload)
                    if cmd == p.Event.HALTED:
                        reason = data[0] if data else 0
                        line = data[1] if len(data) > 1 else 0
                        self._last_line = line
                        desc = {1: "breakpoint", 2: "step", 3: "pause",
                                5: "error"}.get(reason, "stopped")
                        self.send_event("stopped", {
                            "reason": desc, "threadId": 1, "allThreadsStopped": True,
                        })
                    elif cmd == p.Event.ENDED:
                        self.send_event("terminated")
                    elif cmd == p.Event.DETACHED:
                        self.send_event("terminated")
                    else:
                        with self._resp_cond:
                            self._responses[int(cmd)] = (int(cmd), data)
                            self._resp_cond.notify_all()
        except (NanocError, OSError):
            self.send_event("terminated")

    def _connect(self, args):
        self.client = NanocClient(
            host=args.get("host", "127.0.0.1"),
            port=int(args.get("port", 41100)),
            token=args.get("token", ""),
            tls=bool(args.get("tls", False)),
        )
        self.client.connect()
        self._source_path = args.get("source") or args.get("program")
        self._upload_on_start = bool(args.get("upload", False))
        self._reader = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader.start()

    # -- request handling ---------------------------------------------------
    def handle(self, req):
        cmd = req.get("command")
        args = req.get("arguments") or {}
        custom = {
            "nanoc/upload": self._do_upload,
            "nanoc/download": self._do_download,
        }
        if cmd in custom:
            try:
                custom[cmd](req, args)
            except (DapError, NanocError, OSError) as err:
                self.send_response(req, success=False, message=str(err))
            return
        handler = getattr(self, "_do_" + cmd, None)
        if handler is None:
            self.send_response(req, success=False, message=f"unsupported: {cmd}")
            return
        try:
            handler(req, args)
        except (DapError, NanocError, OSError) as err:
            self.send_response(req, success=False, message=str(err))

    def _do_upload(self, req, args):
        data = args.get("text", "").encode("utf-8")
        words = [int(b) for b in data]
        cmd, resp = self._remote_request(p.Command.PROG_SET, len(words), *words)
        status = resp[0] if resp else 1
        msg = ""
        if len(resp) >= 2:
            n = resp[1]
            msg = bytes(b & 0xFF for b in resp[2:2 + n]).decode("utf-8", "replace")
        if msg:
            self.send_event("output", {
                "category": "stderr" if status != 0 else "stdout",
                "output": msg if msg.endswith("\n") else msg + "\n",
            })
        if status != 0:
            self._remote_request(p.Command.ATTACH, 1, 0)
            self.send_response(req, success=False,
                                message="compile failed: " + (msg.strip() or "unknown error"))
            return
        # compiling cleared the breakpoints; re-apply them
        self._remote_request(p.Command.BP_CLR_ALL)
        for line in self._breakpoints:
            self._remote_request(p.Command.BP_SET, line)
        cmd, state = self._remote_request(p.Command.ATTACH, 1, 0)
        self.send_response(req, body={"message": msg})
        if state and len(state) >= 4 and state[1] == 1:
            self._emit_stopped("entry", state[3])

    def _do_download(self, req, args):
        cmd, data = self._remote_request(p.Command.PROG_GET)
        text = ""
        if data and data[0] == 0 and len(data) >= 2:
            n = data[1]
            text = bytes(b & 0xFF for b in data[2:2 + n]).decode("utf-8", "replace")
        self.send_response(req, body={"text": text})

    def _do_initialize(self, req, args):
        self.send_response(req, body={
            "supportsConfigurationDoneRequest": True,
            "supportsFunctionBreakpoints": False,
            "supportsConditionalBreakpoints": False,
            "supportsSetVariable": False,
            "supportsTerminateRequest": False,
        })
        self.send_event("initialized")

    def _do_attach(self, req, args):
        self._connect(args)
        cmd, state = self._remote_request(p.Command.ATTACH, 1, 0)
        if state and state[0] == p.Status.DENIED:
            self.send_response(
                req, success=False,
                message="controller is already being debugged by another client")
            self._running = False
            try:
                self.client.close()
            except OSError:
                pass
            return
        self._attached_state = state
        self.send_response(req)

    _do_launch = _do_attach

    def _do_configurationDone(self, req, args):
        # optional: upload the active file before attaching (F5 runs it)
        if self._upload_on_start and self._source_path:
            try:
                with open(self._source_path, "rb") as f:
                    data = f.read()
                cmd2, resp = self._remote_request(
                    p.Command.PROG_SET, len(data), *list(data), timeout=15)
                msg = _compiler_message(resp)
                if msg:
                    self.send_event("output", {"category": "stdout", "output": msg})
                # re-apply breakpoints (compiling rebuilt the line table)
                self._remote_request(p.Command.BP_CLR_ALL)
                for line in self._breakpoints:
                    self._remote_request(p.Command.BP_SET, line)
            except OSError as err:
                self.send_event("output", {
                    "category": "stderr",
                    "output": f"upload failed: {err}\n"})

        cmd, data = self._remote_request(p.Command.ATTACH, 1, 0)
        self.send_response(req)
        # notify the editor that the target is now stopped (attach pauses it)
        if data and len(data) >= 4 and data[1] == 1:
            self._emit_stopped("entry", data[3])

    def _emit_stopped(self, reason, line):
        if line:
            self._last_line = line
        self.send_event("stopped", {
            "reason": reason, "threadId": 1, "allThreadsStopped": True,
        })

    def _do_setBreakpoints(self, req, args):
        src = args.get("source") or {}
        if src.get("path"):
            self._source_path = src["path"]
        self._remote_request(p.Command.BP_CLR_ALL)
        result = []
        self._breakpoints = []
        for bp in args.get("breakpoints", []):
            line = int(bp.get("line", 0))
            cmd, data = self._remote_request(p.Command.BP_SET, line)
            actual = data[1] if len(data) > 1 else 0
            actual = actual - 0x100000000 if actual >= 0x80000000 else actual
            ok = (data[0] == 0 and actual >= 0)
            result.append({"verified": ok, "line": actual if ok else line})
            if ok:
                self._breakpoints.append(actual)
        self.send_response(req, body={"breakpoints": result})

    def _do_threads(self, req, args):
        self.send_response(req, body={"threads": [{"id": 1, "name": "NanoC VM"}]})

    def _do_stackTrace(self, req, args):
        cmd, data = self._remote_request(p.Command.BACKTRACE)
        frames = []
        if data and data[0] == 0:
            count = data[1] if len(data) > 1 else 0
            raw = data[2:2 + 2 * count]
            for i in range(0, len(raw) - 1, 2):
                line, pc = raw[i], raw[i + 1]
                frames.append({
                    "id": (i // 2) + 1,
                    "name": f"pc {pc}",
                    "line": line if line > 0 else 1,
                    "column": 1,
                    "source": {"name": "NanoC", "path": self._source_path} if self._source_path else None,
                })
        if not frames:
            frames = [{"id": 1, "name": "NanoC VM", "line": self._last_line or 1,
                       "column": 1,
                       "source": {"name": "NanoC", "path": self._source_path} if self._source_path else None}]
        self.send_response(req, body={"stackFrames": frames, "totalFrames": len(frames)})

    def _do_scopes(self, req, args):
        self.send_response(req, body={"scopes": [
            {"name": "Globals", "variablesReference": 1, "expensive": False},
            {"name": "Locals", "variablesReference": 2, "expensive": False},
        ]})

    def _do_variables(self, req, args):
        scope = 1 if int(args.get("variablesReference", 1)) == 2 else 0
        variables = []
        for index in range(256):
            cmd, data = self._remote_request(p.Command.VAR_INFO, scope, index)
            if not data or data[0] != 0:
                break
            kind = data[1] if len(data) > 1 else 0
            nlen = data[2] if len(data) > 2 else 0
            name = _chars(data[3:3 + nlen])
            off = 3 + nlen
            vlen = data[off] if len(data) > off else 0
            value = _chars(data[off + 1:off + 1 + vlen])
            variables.append({"name": name, "value": value,
                              "variablesReference": 0, "type": p.VarKind(kind).name if kind in p.VarKind._value2member_map_ else ""})
        self.send_response(req, body={"variables": variables})

    def _do_continue(self, req, args):
        self._remote_request(p.Command.CONTINUE)
        self.send_response(req, body={"allThreadsContinued": True})

    def _do_next(self, req, args):
        cmd, data = self._remote_request(p.Command.STEP_OVER)
        self.send_response(req)
        self._step_stopped(data)

    def _do_stepIn(self, req, args):
        cmd, data = self._remote_request(p.Command.STEP)
        self.send_response(req)
        self._step_stopped(data)

    def _do_stepOut(self, req, args):
        cmd, data = self._remote_request(p.Command.STEP_OUT)
        self.send_response(req)
        self._step_stopped(data)

    def _step_stopped(self, data):
        # step response: [status, mode, reason, line, pc]
        if data and len(data) >= 4:
            self._emit_stopped("step", data[3])

    def _do_pause(self, req, args):
        self._remote_request(p.Command.HALT)
        self.send_response(req)

    def _do_disconnect(self, req, args):
        try:
            if self.client:
                self.client.send_debug(p.Command.DETACH)
        except (OSError, NanocError):
            pass
        self._running = False
        self.send_response(req)

    # -- main loop ----------------------------------------------------------
    def run(self):
        while self._running:
            msg = self._read_message()
            if msg is None:
                break
            if msg.get("type") == "request":
                self.handle(msg)
        if self.client:
            self.client.close()


def _chars(words):
    return "".join(chr(w & 0xFF) for w in words)


def _compiler_message(resp):
    if not resp or len(resp) < 2:
        return ""
    n = resp[1]
    return bytes(b & 0xFF for b in resp[2:2 + n]).decode("utf-8", "replace")


def main():
    DapServer().run()


if __name__ == "__main__":
    main()
