"""NanoC MCP server (Model Context Protocol) over stdio.

Exposes the NanoC bridge to AI clients (Claude Desktop, OpenCode, ...) as MCP
tools: scan the TA4 techage network, upload/run/stop programs, read terminal
output. Connection defaults come from the args or the environment
(NANOC_HOST, NANOC_PORT, NANOC_TOKEN, NANOC_TLS).

Run:  nanoc-mcp [--host H] [--port P] [--token T] [--tls]
"""

from __future__ import annotations

import json
import os
import sys
import types

from . import protocol as p
from .checker import check
from .nanoc import (
    _claim, _cmd, _compiler_message, _connect, _read_seconds, _upload_bytes,
)

PROTOCOL_VERSION = "2024-11-05"
_STR = {"type": "string"}
_INT = {"type": "integer"}
_NUM = {"type": "number"}
_CONN = {
    "host": _STR, "port": _INT, "token": _STR, "tls": {"type": "boolean"},
}

TOOLS = [
    {
        "name": "nanoc_scan",
        "description": "Dump the TA4 techage network around the controller as "
                       "JSON (nodes with number/state/inventory/caps and edges).",
        "inputSchema": {"type": "object", "properties": {
            "radius": _INT, **_CONN}},
    },
    {
        "name": "nanoc_catalog",
        "description": "Dump the Beduino/techage topic catalog as JSON "
                       "(topic -> kind/name/payload/response) plus the node "
                       "name-pattern rules.",
        "inputSchema": {"type": "object", "properties": {**_CONN}},
    },
    {
        "name": "nanoc_check",
        "description": "Lint NanoC source (brackets, unknown functions, "
                       "undeclared variables). Returns file:line: error lines.",
        "inputSchema": {"type": "object", "properties": {
            "text": _STR, "file": _STR}, "required": []},
    },
    {
        "name": "nanoc_push",
        "description": "Upload and compile a NanoC program to the controller. "
                       "Returns the compiler output (empty on success).",
        "inputSchema": {"type": "object", "properties": {
            "text": _STR, "file": _STR, **_CONN}},
    },
    {
        "name": "nanoc_program_get",
        "description": "Read the program currently stored on the controller.",
        "inputSchema": {"type": "object", "properties": {**_CONN}},
    },
    {
        "name": "nanoc_run",
        "description": "Resume/run the controller.",
        "inputSchema": {"type": "object", "properties": {**_CONN}},
    },
    {
        "name": "nanoc_stop",
        "description": "Halt (pause) the controller.",
        "inputSchema": {"type": "object", "properties": {**_CONN}},
    },
    {
        "name": "nanoc_read",
        "description": "Read the controller's terminal output for a while.",
        "inputSchema": {"type": "object", "properties": {
            "seconds": _NUM, **_CONN}},
    },
    {
        "name": "nanoc_exec",
        "description": "Upload, run and read in one call (write -> run -> read).",
        "inputSchema": {"type": "object", "properties": {
            "text": _STR, "file": _STR, "seconds": _NUM, **_CONN}},
    },
]


_DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")

# Documentation served to AI clients as MCP resources. Files are vendored into
# the package (see docs/README.md and tools/sync_docs.py).
RESOURCES = [
    {
        "uri": "nanoc://workflow",
        "name": "NanoC workflow",
        "description": "How to drive a NanoC controller over these tools: "
                       "scan, catalog, write, check, exec.",
        "mimeType": "text/markdown",
        "file": "workflow.md",
    },
    {
        "uri": "nanoc://cookbook",
        "name": "Techage cookbook",
        "description": "Verified TA4 behaviour: pusher filter/limit, autocrafter "
                       "recipe reference, chest/recipe-block topics, signal "
                       "tower, NanoC pitfalls.",
        "mimeType": "text/markdown",
        "file": "techage_cookbook.md",
    },
    {
        "uri": "nanoc://language",
        "name": "NanoC language primer",
        "description": "Syntax rules and examples for writing NanoC programs.",
        "mimeType": "text/markdown",
        "file": "language.md",
    },
    {
        "uri": "nanoc://reference",
        "name": "NanoC language reference",
        "description": "Full language reference (types, operators, control "
                       "flow, arrays, builtins).",
        "mimeType": "text/markdown",
        "file": "reference.md",
    },
    {
        "uri": "nanoc://manual",
        "name": "NanoC manual",
        "description": "Player manual: components, language examples, timing, "
                       "Techage integration, persistence.",
        "mimeType": "text/markdown",
        "file": "manual.md",
    },
    {
        "uri": "nanoc://topics",
        "name": "Techage topic reference",
        "description": "BEP 005: techage command topics, payloads and node "
                       "name patterns.",
        "mimeType": "text/markdown",
        "file": "techage_topics.md",
    },
    {
        "uri": "nanoc://examples/techage_monitor",
        "name": "Example: techage monitor",
        "description": "Monitor input chests, output chest and autocrafter "
                       "state, with terminal alarms.",
        "mimeType": "text/plain",
        "file": "examples/techage_monitor.nanoc",
    },
    {
        "uri": "nanoc://examples/termlib_demo",
        "name": "Example: termlib demo",
        "description": "Terminal output, colours and keyboard input.",
        "mimeType": "text/plain",
        "file": "examples/termlib_demo.nanoc",
    },
    {
        "uri": "nanoc://examples/factory_control",
        "name": "Example: factory control",
        "description": "Menu-driven TA4 production: recipe block, ingredient "
                       "checks, pushers, autocrafter, intermediates and a "
                       "status tower.",
        "mimeType": "text/plain",
        "file": "examples/factory_control.nanoc",
    },
    {
        "uri": "nanoc://examples/fab_control",
        "name": "Example: electronic fab control",
        "description": "Menu-driven electronic fab production via a recipe "
                       "adapter: ingredient checks, sub-crafts, output and "
                       "return pushers.",
        "mimeType": "text/plain",
        "file": "examples/fab_control.nanoc",
    },
    {
        "uri": "nanoc://examples/oven_control",
        "name": "Example: furnace control",
        "description": "Menu-driven furnace production via a recipe adapter: "
                       "ingredient checks, intermediate products, output, "
                       "return and eject pushers.",
        "mimeType": "text/plain",
        "file": "examples/oven_control.nanoc",
    },
]


def _resource_available(res):
    return os.path.isfile(os.path.join(_DOCS, res["file"]))


def _resource_entry(res):
    return {key: res[key] for key in ("uri", "name", "description", "mimeType")}


def _read_resource(uri):
    for res in RESOURCES:
        if res["uri"] != uri:
            continue
        path = os.path.join(_DOCS, res["file"])
        if not os.path.isfile(path):
            raise McpError(-32603, "resource file missing: " + res["file"])
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return {"contents": [{"uri": uri, "mimeType": res["mimeType"],
                              "text": text}]}
    raise McpError(-32602, "unknown resource: " + str(uri))


class McpError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class McpServer:
    def __init__(self, host, port, token, tls):
        self.host = host
        self.port = port
        self.token = token
        self.tls = tls

    # -- io ----------------------------------------------------------------
    def reply(self, mid, result):
        self._write({"jsonrpc": "2.0", "id": mid, "result": result})

    def error(self, mid, code, message):
        self._write({"jsonrpc": "2.0", "id": mid,
                     "error": {"code": code, "message": message}})

    def _write(self, obj):
        sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
        sys.stdout.flush()

    def run(self):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            self._handle(msg)

    # -- dispatch ----------------------------------------------------------
    def _handle(self, msg):
        method = msg.get("method")
        mid = msg.get("id")
        if method is None:
            return                       # a response, ignore
        if method.startswith("notifications/"):
            return                       # no reply
        try:
            if method == "initialize":
                params = msg.get("params") or {}
                self.reply(mid, {
                    "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                    "capabilities": {"tools": {}, "resources": {}},
                    "serverInfo": {"name": "nanoc", "version": "0.1.0"},
                })
            elif method == "ping":
                self.reply(mid, {})
            elif method == "tools/list":
                self.reply(mid, {"tools": TOOLS})
            elif method == "tools/call":
                self.reply(mid, self._call_tool(msg.get("params") or {}))
            elif method == "resources/list":
                self.reply(mid, {"resources": [
                    _resource_entry(res) for res in RESOURCES
                    if _resource_available(res)]})
            elif method == "resources/templates/list":
                self.reply(mid, {"resourceTemplates": []})
            elif method == "resources/read":
                params = msg.get("params") or {}
                self.reply(mid, _read_resource(params.get("uri")))
            elif method == "prompts/list":
                self.reply(mid, {"prompts": []})
            else:
                raise McpError(-32601, f"method not found: {method}")
        except McpError as err:
            self.error(mid, err.code, err.message)
        except Exception as err:         # noqa: BLE001
            self.error(mid, -32603, str(err))

    def _call_tool(self, params):
        name = params.get("name")
        args = params.get("arguments") or {}
        handler = getattr(self, "_tool_" + name, None)
        if handler is None:
            return {"content": [{"type": "text", "text": f"unknown tool: {name}"}],
                    "isError": True}
        try:
            text = handler(args)
            return {"content": [{"type": "text", "text": text}], "isError": False}
        except Exception as err:         # noqa: BLE001
            return {"content": [{"type": "text", "text": f"error: {err}"}],
                    "isError": True}

    # -- helpers -----------------------------------------------------------
    def _conn(self, args):
        return types.SimpleNamespace(
            host=args.get("host", self.host),
            port=int(args.get("port", self.port)),
            token=args.get("token", self.token),
            tls=bool(args.get("tls", self.tls)),
            server_hostname=None,
        )

    @staticmethod
    def _text(args):
        if "text" in args and args["text"] is not None:
            return str(args["text"])
        if args.get("file"):
            with open(args["file"], "r", encoding="utf-8") as f:
                return f.read()
        raise McpError(-32602, "either 'text' or 'file' is required")

    @staticmethod
    def _format_output(collect, logs):
        text = b"".join(collect).decode("utf-8", "replace")
        if logs and text and not text.endswith("\n"):
            text += "\n"
        for line in logs:
            msg = line.decode("utf-8", "replace").rstrip("\n")
            text += "[log] " + msg + "\n"
        return text

    # -- tools -------------------------------------------------------------
    def _tool_nanoc_scan(self, args):
        client = _connect(self._conn(args))
        try:
            resp = _cmd(client, p.Command.SCAN, int(args.get("radius", 8)), timeout=20)
            status = resp[0] if resp else 1
            text = _compiler_message(resp)
            if status != 0 or not text:
                raise McpError(-32603, "scan failed")
            return text
        finally:
            client.close()

    def _tool_nanoc_catalog(self, args):
        client = _connect(self._conn(args))
        try:
            resp = _cmd(client, p.Command.CATALOG, timeout=15)
            status = resp[0] if resp else 1
            text = _compiler_message(resp)
            if status != 0 or not text:
                raise McpError(-32603, "catalog failed")
            return text
        finally:
            client.close()

    def _tool_nanoc_check(self, args):
        errors = check(self._text(args))
        return "\n".join(f"line {ln}: {msg}" for ln, msg in errors) or "OK"

    def _tool_nanoc_push(self, args):
        data = self._text(args).encode("utf-8")
        client = _connect(self._conn(args))
        try:
            if not _claim(client):
                raise McpError(-32603, "controller is busy (another debugger)")
            ok, msg = _upload_bytes(client, data)
            if ok:
                _cmd(client, p.Command.CONTINUE)    # resume
            return msg.strip() or ("uploaded" if ok else "upload failed")
        finally:
            client.close()

    def _tool_nanoc_program_get(self, args):
        client = _connect(self._conn(args))
        try:
            resp = _cmd(client, p.Command.PROG_GET)
            return _compiler_message(resp)
        finally:
            client.close()

    def _tool_nanoc_run(self, args):
        client = _connect(self._conn(args))
        try:
            if not _claim(client):
                raise McpError(-32603, "controller is busy")
            _cmd(client, p.Command.CONTINUE)
            return "running"
        finally:
            client.close()

    def _tool_nanoc_stop(self, args):
        client = _connect(self._conn(args))
        try:
            if not _claim(client):
                raise McpError(-32603, "controller is busy")
            _cmd(client, p.Command.HALT)
            return "stopped"
        finally:
            client.close()

    def _tool_nanoc_read(self, args):
        client = _connect(self._conn(args))
        collect = []
        logs = []
        try:
            _read_seconds(client, float(args.get("seconds", 3.0)), collect, logs)
            return self._format_output(collect, logs)
        finally:
            client.close()

    def _tool_nanoc_exec(self, args):
        data = self._text(args).encode("utf-8")
        client = _connect(self._conn(args))
        collect = []
        logs = []
        try:
            if not _claim(client):
                raise McpError(-32603, "controller is busy")
            ok, msg = _upload_bytes(client, data)
            if not ok:
                return "compile failed:\n" + msg
            _cmd(client, p.Command.CONTINUE)
            _read_seconds(client, float(args.get("seconds", 3.0)), collect, logs)
            return self._format_output(collect, logs)
        finally:
            client.close()


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="nanoc-mcp", description="NanoC MCP server")
    ap.add_argument("--host", default=os.environ.get("NANOC_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("NANOC_PORT", "41100")))
    ap.add_argument("--token", default=os.environ.get("NANOC_TOKEN", ""))
    ap.add_argument("--tls", action="store_true",
                    default=os.environ.get("NANOC_TLS", "") not in ("", "0", "false"))
    args = ap.parse_args(argv)
    McpServer(args.host, args.port, args.token, args.tls).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
