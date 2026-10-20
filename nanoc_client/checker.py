"""Lightweight NanoC linter.

Adapted from the HMS ConfigTool "nc_check.py": a best-effort static check that
catches the most common mistakes without a full compile:

  - unbalanced parentheses / braces / brackets
  - calls to unknown functions
  - use of undeclared variables (typos)

Findings are (line, message); the CLI prints them GCC-style so editors jump to
the line.

Run:  nanoc-check <file.nc>   ->  <file>:<line>: error: <message>
"""

from __future__ import annotations

import re
import sys

# NanoC keywords
KEYWORDS = {
    "int32", "uint32", "str8", "u8", "u16", "u32", "void",
    "func", "return", "reti", "for", "to", "step", "next",
    "if", "then", "else", "elseif", "endif", "end",
    "while", "loop", "and", "or", "not", "mod", "break",
    "const", "local", "dim", "dispatch", "goto", "gosub",
    "print", "printf", "read", "restore", "ref", "erase", "data",
    "on", "tron", "troff", "inc", "dec", "shl", "shr", "copy",
    "param", "params", "NULL", "true", "false",
}

TYPES = {"int32", "uint32", "str8", "void"}

# Built-in / API functions available in NanoC
BUILTINS = {
    "printf", "sleep", "millis", "key", "log", "breakpoint",
    "ta_send_cmd", "ta_send_cmd_s", "ta_signal",
    "ta_req_data", "ta_req_data_s", "ta_req_data_str",
    "ta_recv", "ta_port", "ta_topic", "ta_payload",
    "ta_recv_sig", "ta_sig_port", "ta_sig_val",
    "rnd", "abs", "len", "val", "instr", "string$", "string", "free",
    "left$", "left", "right$", "right", "mid$", "mid",
    "str$", "str", "hex$", "hex",
    "u8", "u16", "u32", "copy",
    "str2arr", "arr2str$", "arr2str",
}

PREDEFINED: set = set()

_TOKEN_RE = re.compile(
    r'"(?:[^"\\]|\\.)*"'            # string literal
    r"|//[^\n]*"                    # line comment
    r"|/\*.*?\*/"                   # block comment (single line)
    r"|0[xX][0-9A-Fa-f]+"           # hex number
    r"|\d+"                         # decimal number
    r"|[A-Za-z_][A-Za-z0-9_]*\$?"   # identifier (optional trailing $)
    r"|."                           # any other single char
)


def _tokenize(code):
    tokens = []
    for lineno, line in enumerate(code.splitlines(), start=1):
        for m in _TOKEN_RE.finditer(line):
            tok = m.group(0)
            if tok.startswith("//") or tok.startswith("/*") or tok.startswith('"') or tok.isspace():
                continue
            tokens.append((tok, lineno))
    return tokens


def _is_ident(tok):
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*\$?$", tok))


def _check_balance(code):
    errors = []
    pairs = {")": "(", "}": "{", "]": "["}
    openers = set(pairs.values())
    stack = []
    in_block_comment = False
    for lineno, line in enumerate(code.splitlines(), start=1):
        in_str = False
        i = 0
        while i < len(line):
            c = line[i]
            if in_block_comment:
                if c == "*" and i + 1 < len(line) and line[i + 1] == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            if in_str:
                if c == "\\":
                    i += 2
                    continue
                if c == '"':
                    in_str = False
                i += 1
                continue
            if c == '"':
                in_str = True
            elif c == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            elif c == "/" and i + 1 < len(line) and line[i + 1] == "*":
                in_block_comment = True
                i += 2
                continue
            elif c in openers:
                stack.append((c, lineno))
            elif c in pairs:
                if not stack:
                    errors.append((lineno, "unexpected '%s'" % c))
                elif stack[-1][0] != pairs[c]:
                    op, opln = stack.pop()
                    errors.append((lineno, "'%s' does not match '%s' from line %d" % (c, op, opln)))
                else:
                    stack.pop()
            i += 1
    for op, opln in stack:
        errors.append((opln, "unclosed '%s'" % op))
    return errors


def check(code):
    """Return a sorted, de-duplicated list of (line, message)."""
    errors = list(_check_balance(code))
    tokens = _tokenize(code)
    n = len(tokens)

    declared = set(PREDEFINED)
    user_funcs = set()
    i = 0
    while i < n:
        tok = tokens[i][0]
        nxt = tokens[i + 1][0] if i + 1 < n else ""
        if tok in TYPES:
            if _is_ident(nxt):
                declared.add(nxt)
        elif tok in ("const", "for"):
            j = i + 1
            # skip a type before a for/const name
            if tok == "for" and nxt in TYPES and i + 2 < n:
                j = i + 2
            if j < n and _is_ident(tokens[j][0]):
                declared.add(tokens[j][0])
        elif tok == "func":
            j = i + 1
            if j < n and tokens[j][0] in TYPES:
                j += 1
            if j < n and _is_ident(tokens[j][0]):
                user_funcs.add(tokens[j][0])
                j += 1
            if j < n and tokens[j][0] == "(":
                depth = 0
                while j < n:
                    t = tokens[j][0]
                    if t == "(":
                        depth += 1
                    elif t == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    elif _is_ident(t) and t not in TYPES:
                        declared.add(t)
                    j += 1
        elif _is_ident(tok) and nxt == "=":
            declared.add(tok)
        i += 1

    known_calls = BUILTINS | user_funcs | KEYWORDS
    i = 0
    while i < n:
        tok, lineno = tokens[i]
        prev = tokens[i - 1][0] if i > 0 else ""
        nxt = tokens[i + 1][0] if i + 1 < n else ""
        if not _is_ident(tok) or tok in KEYWORDS:
            i += 1
            continue
        if prev in TYPES or prev in ("func", "const", "for"):
            i += 1
            continue
        if nxt == "(":
            if tok not in known_calls:
                errors.append((lineno, "call to unknown function '%s'" % tok))
        else:
            if tok not in declared and tok not in BUILTINS and tok not in user_funcs:
                errors.append((lineno, "undeclared variable '%s'" % tok))
        i += 1

    seen = set()
    result = []
    for ln, msg in sorted(errors, key=lambda e: e[0]):
        if (ln, msg) not in seen:
            seen.add((ln, msg))
            result.append((ln, msg))
    return result


def check_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return check(f.read())


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 1:
        print("usage: nanoc-check <file.nc>", file=sys.stderr)
        return 2
    path = argv[0]
    try:
        errors = check_file(path)
    except OSError as err:
        print("%s: error: %s" % (path, err), file=sys.stderr)
        return 2
    for line, msg in errors:
        # GCC-style so editors can jump to the line
        print("%s:%d: error: %s" % (path, line, msg))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
