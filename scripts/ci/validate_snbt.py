#!/usr/bin/env python3
"""Fast-tier CI check + reusable parser: syntax-check every *.snbt file under
pack/ (recursively - this covers FTB Quests' pack/config/ftbquests/quests/**
tree and standalone files like pack/config/ftbchunks-world.snbt).

SNBT ("stringified NBT") is Minecraft/FTB's human-editable NBT text format:
compounds `{ key: value, ... }`, lists `[ value, ... ]`, typed arrays
`[I; 1, 2, 3]` / `[B; ...]` / `[L; ...]`, quoted (`"..."`/`'...'`, with
backslash escapes) and unquoted/bare strings, numbers with optional type
suffixes (b/s/l/f/d), and the bare words `true`/`false`.

This module implements a small hand-written recursive-descent parser (no
external deps) rather than assuming JSON compatibility, because real SNBT
differs from JSON in ways this repo's own files exercise:

  - `pack/config/ftbchunks-world.snbt` uses `#`-to-end-of-line comments and
    UNQUOTED keys, and separates compound members with newlines rather than
    commas (commas are optional wherever a newline/further whitespace
    already separates two members) - none of which plain `json.loads` can
    parse. This is the ground truth for why a real SNBT parser is needed;
    without it this specific file cannot be validated at all.
  - FTB Quests' own generated chapter/lang/data files in
    pack/config/ftbquests/quests/** happen, in this repo, to already be
    valid single-line JSON (produced by scripts/gen_quests.py) - but the
    format FTB Quests itself accepts (and what hand-edited quest files in
    the wild look like) is the same comma-optional, unquoted-key, bare
    top-level compound style as ftbchunks-world.snbt, so the parser
    supports that shape unconditionally rather than special-casing "the
    files happen to be JSON today".
  - A bare top-level compound (the file's content IS a compound's member
    list, with no wrapping `{`/`}`) is also accepted, since FTB's own SNBT
    tooling allows omitting the outermost braces.

check_quests.py (#5) imports parse_snbt() from this module directly to walk
FTB Quests data without a second parser implementation.

Usage: python3 scripts/ci/validate_snbt.py [root]
Exit code: 0 if every *.snbt file under pack/ parses, 1 otherwise.
"""
import sys
from collections import namedtuple
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PACK_DIR = REPO_ROOT / "pack"

# See validate_json.py's identical note: nothing under pack/ currently needs
# excluding from *.snbt discovery either.
EXCLUDED_DIRS: set[str] = set()


class SNBTError(Exception):
    """Raised on any syntax error. line/col are 1-indexed."""

    def __init__(self, message, line, col):
        super().__init__(f"line {line} column {col}: {message}")
        self.message = message
        self.line = line
        self.col = col


class NbtArray(list):
    """A typed NBT array ([I; ...], [B; ...], [L; ...]). Behaves as a plain
    list (equality, iteration, len) but remembers its element-type letter."""

    def __new__(cls, array_type, values):
        obj = super().__new__(cls)
        return obj

    def __init__(self, array_type, values):
        super().__init__(values)
        self.array_type = array_type

    def __eq__(self, other):
        if isinstance(other, NbtArray):
            return self.array_type == other.array_type and list(self) == list(other)
        return list(self) == other

    __hash__ = None  # explicit: like list, NbtArray is unhashable


Token = namedtuple("Token", ["type", "value", "line", "col"])

_STRUCTURAL = {"{": "LBRACE", "}": "RBRACE", "[": "LBRACKET", "]": "RBRACKET",
               ":": "COLON", ",": "COMMA", ";": "SEMI"}
_BARE_STOP_CHARS = set(" \t\r\n#{}[]:,;\"'")
_SIMPLE_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "'": "'",
                   "\\": "\\", "b": "\b", "f": "\f"}
_NUMBER_SUFFIXES = set("bBsSlLfFdD")


def tokenize(text):
    """Turn SNBT source text into a flat list of Tokens, ending in an EOF
    token. Raises SNBTError on unterminated strings or stray characters."""
    tokens = []
    i = 0
    n = len(text)
    line = 1
    col = 1

    def bump(ch):
        nonlocal line, col
        if ch == "\n":
            line += 1
            col = 1
        else:
            col += 1

    while i < n:
        ch = text[i]

        if ch in " \t\r\n":
            bump(ch)
            i += 1
            continue

        if ch == "#":
            while i < n and text[i] != "\n":
                bump(text[i])
                i += 1
            continue

        if ch in _STRUCTURAL:
            tokens.append(Token(_STRUCTURAL[ch], ch, line, col))
            bump(ch)
            i += 1
            continue

        if ch == '"' or ch == "'":
            quote = ch
            start_line, start_col = line, col
            buf = []
            bump(ch)
            i += 1
            closed = False
            while i < n:
                c = text[i]
                if c == "\\" and i + 1 < n:
                    nxt = text[i + 1]
                    if nxt in _SIMPLE_ESCAPES:
                        buf.append(_SIMPLE_ESCAPES[nxt])
                        bump(c)
                        bump(nxt)
                        i += 2
                        continue
                    if nxt == "u" and i + 5 < n:
                        hex_digits = text[i + 2:i + 6]
                        try:
                            buf.append(chr(int(hex_digits, 16)))
                        except ValueError:
                            raise SNBTError(
                                f"invalid unicode escape \\u{hex_digits}", line, col)
                        for k in range(6):
                            bump(text[i + k])
                        i += 6
                        continue
                    raise SNBTError(f"invalid escape sequence '\\{nxt}'", line, col)
                if c == quote:
                    bump(c)
                    i += 1
                    closed = True
                    break
                buf.append(c)
                bump(c)
                i += 1
            if not closed:
                raise SNBTError(
                    f"unterminated quoted string (started with {quote!r})",
                    start_line, start_col)
            tokens.append(Token("STRING", "".join(buf), start_line, start_col))
            continue

        # bare token: identifier, number literal, or unquoted string
        start_line, start_col = line, col
        start_i = i
        while i < n and text[i] not in _BARE_STOP_CHARS:
            bump(text[i])
            i += 1
        if i == start_i:
            raise SNBTError(f"unexpected character {ch!r}", line, col)
        tokens.append(Token("BARE", text[start_i:i], start_line, start_col))

    tokens.append(Token("EOF", "", line, col))
    return tokens


def _parse_number_literal(raw, line, col):
    core = raw
    if core and core[-1] in _NUMBER_SUFFIXES:
        core = core[:-1]
    if not core:
        raise SNBTError(f"invalid number literal {raw!r}", line, col)
    try:
        if "." in core or "e" in core.lower():
            return float(core)
        return int(core)
    except ValueError:
        raise SNBTError(f"invalid number literal {raw!r}", line, col)


def _interpret_bare_value(tok):
    s = tok.value
    if s == "true":
        return True
    if s == "false":
        return False
    # Numeric? (optional leading sign, digits, optional fraction/exponent,
    # optional single-letter type suffix)
    core = s[:-1] if s and s[-1] in _NUMBER_SUFFIXES else s
    is_numeric = False
    if core:
        body = core[1:] if core[0] in "+-" else core
        if body and all(c.isdigit() or c in ".eE+-" for c in body):
            # cheap pre-filter; let float()/int() in _parse_number_literal
            # do the real validation
            digits_only = body.replace(".", "").replace("e", "").replace(
                "E", "").replace("+", "").replace("-", "")
            is_numeric = digits_only.isdigit() and digits_only != ""
    if is_numeric:
        return _parse_number_literal(s, tok.line, tok.col)
    return s  # unquoted/bare string, kept verbatim


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset=0):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF

    def advance(self):
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def parse_document(self):
        first = self.peek()
        if first.type == "EOF":
            return {}
        if first.type == "LBRACE":
            value = self.parse_compound()
            trailing = self.peek()
            if trailing.type != "EOF":
                raise SNBTError(
                    f"unexpected trailing token {trailing.value!r} after top-level compound",
                    trailing.line, trailing.col)
            return value
        return self.parse_members_until_eof()

    def parse_key(self):
        tok = self.peek()
        if tok.type == "STRING":
            self.advance()
            return tok.value
        if tok.type == "BARE":
            self.advance()
            return tok.value
        raise SNBTError(f"expected a key (quoted or bare), got {tok.type}", tok.line, tok.col)

    def _maybe_consume_separator(self):
        tok = self.peek()
        if tok.type == "COMMA":
            self.advance()

    def parse_members_until_eof(self):
        result = {}
        while True:
            tok = self.peek()
            if tok.type == "EOF":
                return result
            key = self.parse_key()
            colon = self.peek()
            if colon.type != "COLON":
                raise SNBTError(f"expected ':' after key {key!r}, got {colon.type}",
                                 colon.line, colon.col)
            self.advance()
            value = self.parse_value()
            result[key] = value
            self._maybe_consume_separator()

    def parse_compound(self):
        open_tok = self.advance()  # consumes '{'
        result = {}
        while True:
            tok = self.peek()
            if tok.type == "RBRACE":
                self.advance()
                return result
            if tok.type == "EOF":
                raise SNBTError("unterminated compound - missing '}'",
                                 open_tok.line, open_tok.col)
            key = self.parse_key()
            colon = self.peek()
            if colon.type != "COLON":
                raise SNBTError(f"expected ':' after key {key!r}, got {colon.type}",
                                 colon.line, colon.col)
            self.advance()
            value = self.parse_value()
            result[key] = value
            self._maybe_consume_separator()

    def parse_value(self):
        tok = self.peek()
        if tok.type == "LBRACE":
            return self.parse_compound()
        if tok.type == "LBRACKET":
            return self.parse_list_or_array()
        if tok.type == "STRING":
            self.advance()
            return tok.value
        if tok.type == "BARE":
            self.advance()
            return _interpret_bare_value(tok)
        raise SNBTError(f"expected a value, got {tok.type}", tok.line, tok.col)

    def parse_list_or_array(self):
        open_tok = self.advance()  # consumes '['
        first = self.peek()
        if first.type == "BARE" and first.value in ("I", "B", "L") and \
                self.peek(1).type == "SEMI":
            array_type = first.value
            self.advance()  # letter
            self.advance()  # ';'
            values = []
            while True:
                tok = self.peek()
                if tok.type == "RBRACKET":
                    self.advance()
                    return NbtArray(array_type, values)
                if tok.type == "EOF":
                    raise SNBTError("unterminated typed array - missing ']'",
                                     open_tok.line, open_tok.col)
                if tok.type != "BARE":
                    raise SNBTError(
                        f"typed array element must be a number literal, got {tok.type}",
                        tok.line, tok.col)
                values.append(_parse_number_literal(tok.value, tok.line, tok.col))
                self.advance()
                self._maybe_consume_separator()

        values = []
        while True:
            tok = self.peek()
            if tok.type == "RBRACKET":
                self.advance()
                return values
            if tok.type == "EOF":
                raise SNBTError("unterminated list - missing ']'",
                                 open_tok.line, open_tok.col)
            values.append(self.parse_value())
            self._maybe_consume_separator()


def parse_snbt(text):
    """Parse SNBT source text into native Python values (dict/list/str/int/
    float/bool). Raises SNBTError on malformed input."""
    tokens = tokenize(text)
    parser = _Parser(tokens)
    return parser.parse_document()


def parse_snbt_file(path):
    text = Path(path).read_text(encoding="utf-8")
    return parse_snbt(text)


def _is_excluded(path):
    try:
        rel = path.relative_to(PACK_DIR)
    except ValueError:
        return False
    return any(part in EXCLUDED_DIRS for part in rel.parts[:-1])


def find_files(pack_dir):
    return sorted(p for p in pack_dir.rglob("*.snbt") if p.is_file() and not _is_excluded(p))


def check_file(path):
    """Return None on success, or a human-readable error string on failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return f"could not decode as UTF-8: {e}"
    except OSError as e:
        return f"could not read file: {e}"
    try:
        parse_snbt(text)
    except SNBTError as e:
        return str(e)
    return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    pack_dir = Path(argv[0]) / "pack" if argv else PACK_DIR

    if not pack_dir.is_dir():
        print(f"validate_snbt: FAIL - pack directory not found at {pack_dir}", file=sys.stderr)
        return 1

    files = find_files(pack_dir)
    failures = []
    for path in files:
        err = check_file(path)
        if err is not None:
            failures.append((path, err))

    if failures:
        print(f"validate_snbt: FAIL - {len(failures)}/{len(files)} file(s) failed to parse:")
        for path, err in failures:
            try:
                rel = path.relative_to(REPO_ROOT)
            except ValueError:
                rel = path
            print(f"  {rel}: {err}")
        return 1

    print(f"validate_snbt: PASS - {len(files)} file(s) parsed cleanly ({pack_dir})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
