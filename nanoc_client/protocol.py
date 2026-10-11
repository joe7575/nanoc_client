"""NanoC TCP wire protocol (protocol version 1).

See nanoc_lib/doc/protocol.md. All multi-byte integers are little-endian.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum

PROTOCOL = 1

MAGIC0 = 0x4E  # 'N'
MAGIC1 = 0x43  # 'C'

HEADER = struct.Struct("<4B I 2H")  # magic0, magic1, version, channel, session, length, reserved
HEADER_SIZE = HEADER.size  # 12

TERMINAL_WIDTH = 80
TERMINAL_HEIGHT = 24


class Channel(IntEnum):
    DEBUG = 1
    TERMINAL = 2
    CONTROL = 3
    LOG = 4


class Command(IntEnum):
    ATTACH = 0x01
    DETACH = 0x02
    STATE = 0x03
    BP_SET = 0x04
    BP_CLR = 0x05
    BP_CLR_ALL = 0x06
    HALT = 0x07
    CONTINUE = 0x08
    STEP = 0x09
    STEP_OVER = 0x0A
    STEP_OUT = 0x0B
    VAR_INFO = 0x0C
    VAR_WRITE = 0x0D
    ARR_READ = 0x0E
    BACKTRACE = 0x0F
    PROG_GET = 0x20
    PROG_SET = 0x21
    SCAN = 0x22
    CATALOG = 0x23


class Event(IntEnum):
    HALTED = 0x80
    ENDED = 0x81
    DETACHED = 0x82


class Status(IntEnum):
    OK = 0
    END = 1
    NOT_ATTACHED = 2
    NO_SCRIPT = 3
    PARAM = 4
    NOT_HALTED = 5
    FULL = 6
    NO_CODE = 7
    DENIED = 8
    UNKNOWN_CMD = 9


class Mode(IntEnum):
    RUN = 0
    HALTED = 1
    STEP = 2
    STEP_OVER = 3
    STEP_OUT = 4


class HaltReason(IntEnum):
    NONE = 0
    BREAKPOINT = 1
    STEP = 2
    HALT = 3
    BREAK_STMT = 4
    ERROR = 5
    RESET = 6


class VarKind(IntEnum):
    INT = 1
    STR = 2
    ARR = 3
    CONST = 4


class HelloStatus(IntEnum):
    OK = 0
    BAD_PROTOCOL = 1
    BAD_TOKEN = 2
    BUSY = 3


@dataclass
class Frame:
    channel: Channel
    payload: bytes
    session: int = 0
    version: int = PROTOCOL

    def pack(self) -> bytes:
        return HEADER.pack(
            MAGIC0,
            MAGIC1,
            self.version,
            int(self.channel),
            self.session,
            len(self.payload),
            0,
        ) + self.payload

    @classmethod
    def parse_header(cls, header: bytes) -> "FrameHeader":
        if len(header) != HEADER_SIZE:
            raise ValueError("short frame header")
        magic0, magic1, version, channel, session, length, reserved = HEADER.unpack(header)
        if magic0 != MAGIC0 or magic1 != MAGIC1:
            raise ValueError("bad magic")
        if version != PROTOCOL:
            raise ValueError(f"unsupported protocol version {version}")
        return FrameHeader(
            version=version,
            channel=Channel(channel),
            session=session,
            length=length,
        )


@dataclass
class FrameHeader:
    version: int
    channel: Channel
    session: int
    length: int


def encode_words(words) -> bytes:
    return struct.pack("<%dI" % len(words), *[int(w) & 0xFFFFFFFF for w in words])


def decode_words(payload: bytes):
    n = len(payload) // 4
    return list(struct.unpack("<%dI" % n, payload[: n * 4]))


def encode_debug(cmd: Command, *data: int) -> bytes:
    return encode_words([int(cmd), *data])


def decode_debug(payload: bytes):
    words = decode_words(payload)
    if not words:
        raise ValueError("empty debug payload")
    return words[0], words[1:]


def encode_hello(client_protocol: int, token: str) -> bytes:
    raw = token.encode("utf-8")
    return struct.pack("<IB", client_protocol, len(raw)) + raw


def decode_hello(payload: bytes):
    if len(payload) < 5:
        raise ValueError("short HELLO")
    client_protocol, token_len = struct.unpack_from("<IB", payload, 0)
    token = payload[5 : 5 + token_len].decode("utf-8", "replace")
    return client_protocol, token


def encode_hello_ack(status: HelloStatus, server_protocol: int = PROTOCOL) -> bytes:
    return struct.pack("<BI", int(status), server_protocol)


def decode_hello_ack(payload: bytes):
    if len(payload) < 5:
        raise ValueError("short HELLO_ACK")
    status, server_protocol = struct.unpack_from("<BI", payload, 0)
    return HelloStatus(status), server_protocol
