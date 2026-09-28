"""Tokenizer dòng cho hashline patch.

Port của crates/pi-edit/src/modes/hashline/tokenizer.rs (bỏ streaming buffer).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Union

from dino_coding.tools.hashline.types import Anchor, ParsedRange

HASH_LENGTH = 4  # HL_FILE_HASH_LENGTH
HASH_RE = re.compile(r"[0-9A-Fa-f]{4}")

# Locator + register tùy chọn của một op header. ← port tokenizer::BlockTarget
@dataclass
class ReplaceTarget:
    range: ParsedRange
    register: Optional[str] = None

@dataclass
class BlockTarget:
    anchor: Anchor
    register: Optional[str] = None

@dataclass
class InsertBeforeTarget:
    anchor: Anchor
    register: Optional[str] = None

@dataclass
class InsertAfterTarget:
    anchor: Anchor
    register: Optional[str] = None

@dataclass
class InsertAfterBlockTarget:
    anchor: Anchor
    register: Optional[str] = None

@dataclass
class CutTarget:
    range: ParsedRange
    register: Optional[str] = None

@dataclass
class CutBlockTarget:
    anchor: Anchor
    register: Optional[str] = None

@dataclass
class BofTarget:
    register: Optional[str] = None

@dataclass
class EofTarget:
    register: Optional[str] = None

@dataclass
class RemTarget:
    pass

@dataclass
class MoveTarget:
    dest: str

AnyTarget = Union[
    ReplaceTarget, BlockTarget, InsertBeforeTarget, InsertAfterTarget,
    InsertAfterBlockTarget, CutTarget, CutBlockTarget, BofTarget, EofTarget,
    RemTarget, MoveTarget,
]


def target_register(target: AnyTarget) -> Optional[str]:
    return getattr(target, "register", None)


# ---- token của một dòng ----
@dataclass
class HeaderToken:
    line_num: int
    path: str
    file_hash: Optional[str]

@dataclass
class OpToken:
    line_num: int
    target: AnyTarget
    had_colon: bool

@dataclass
class PayloadToken:
    line_num: int
    text: str

@dataclass
class RawToken:
    line_num: int
    text: str

@dataclass
class BlankToken:
    line_num: int

Token = Union[HeaderToken, OpToken, PayloadToken, RawToken, BlankToken]


def _number_prefix(raw: str) -> Optional[tuple[int, int]]:
    """Số dương không bắt đầu bằng 0. ← port tokenizer::parse_number_prefix"""
    if not raw or not raw[0].isascii() or not raw[0].isdigit() or raw[0] == "0":
        return None
    end = 1
    while end < len(raw) and raw[end].isdigit():
        end += 1
    return int(raw[:end]), end


def parse_range(raw: str, allow_single: bool = True) -> Optional[tuple[ParsedRange, int, bool]]:
    """`N`, `N.=M`, `N-M`, `N…M`, `N M`. ← port tokenizer::parse_range

    Trả về (range, số ký tự đã dùng, có_separator?). Separator hợp lệ:
    whitespace, `-`, `.`, `=`, `…` (chuỗi `.=` là 2 ký tự của cùng bộ này).
    """
    start = len(raw) - len(raw.lstrip())
    head = _number_prefix(raw[start:])
    if head is None:
        return None
    first, used = head
    cursor = start + used
    saw_non_ws = False
    while cursor < len(raw):
        ch = raw[cursor]
        if ch.isspace() or ch in "-.=…":
            saw_non_ws = saw_non_ws or not ch.isspace()
            cursor += 1
        else:
            break
    second = _number_prefix(raw[cursor:])
    if second is not None:
        end, count = second
        cursor += count
        while cursor < len(raw) and raw[cursor].isspace():
            cursor += 1
        rng = ParsedRange(Anchor(first), Anchor(end))
        return rng, cursor, True
    if not allow_single:
        return None
    rng = ParsedRange(Anchor(first), Anchor(first))
    if saw_non_ws and (cursor == len(raw) or raw[cursor] in ":@"):
        return rng, cursor, True
    return rng, cursor, False


def _register_and_colon(raw: str, target: AnyTarget) -> Optional[tuple[AnyTarget, bool]]:
    """`@name` tùy chọn + `:` tùy chọn; còn rác → None. ← port parse_register_and_colon"""
    rest = raw.lstrip()
    if rest.startswith("@"):
        tail = rest[1:]
        length = 0
        while length < len(tail) and (tail[length].isalnum() or tail[length] in "_-"):
            length += 1
        if length == 0 or length > 64:
            return None
        register, rest = tail[:length], tail[length:].lstrip()
        if hasattr(target, "register"):
            target.register = register
    had_colon = rest.startswith(":")
    if had_colon:
        rest = rest[1:].lstrip()
    if rest:
        return None
    return target, had_colon


def parse_put_target(raw: str) -> Optional[tuple[AnyTarget, bool]]:
    """Locator sau `PUT `. ← port tokenizer::parse_put_target"""
    rest = raw.lstrip()
    if rest.startswith(">"):
        after = rest[1:].lstrip()
        if after.startswith("$"):
            return _register_and_colon(after[1:], EofTarget())
        head = _number_prefix(after)
        if head is None:
            return None
        line, used = head
        tail = after[used:]
        block = tail.startswith("*")
        if block:
            tail = tail[1:]
        target: AnyTarget = (
            InsertAfterBlockTarget(Anchor(line)) if block else InsertAfterTarget(Anchor(line))
        )
        return _register_and_colon(tail, target)
    if rest.startswith("<"):
        after = rest[1:].lstrip()
        head = _number_prefix(after)
        if head is None:
            return None
        line, used = head
        tail = after[used:]
        if tail.startswith("*"):
            tail = tail[1:]
        target = BofTarget() if line == 1 else InsertBeforeTarget(Anchor(line))
        return _register_and_colon(tail, target)
    parsed = parse_range(rest)
    if parsed is None:
        return None
    rng, used, had_sep = parsed
    tail = rest[used:]
    if tail.startswith("*"):
        if had_sep:
            return None
        return _register_and_colon(tail[1:], BlockTarget(rng.start))
    return _register_and_colon(tail, ReplaceTarget(rng))


def parse_cut_target(raw: str) -> Optional[tuple[AnyTarget, bool]]:
    """Locator sau `CUT `. ← port tokenizer::parse_cut_target"""
    rest = raw.lstrip()
    parsed = parse_range(rest)
    if parsed is None:
        return None
    rng, used, had_sep = parsed
    tail = rest[used:]
    if tail.startswith("*"):
        if had_sep:
            return None
        return _register_and_colon(tail[1:], CutBlockTarget(rng.start))
    return _register_and_colon(tail, CutTarget(rng))


def _unquote_path(raw: str) -> Optional[str]:
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    if raw.startswith(("\"", "'")):
        return None
    return raw


def _keyword_tail(line: str, keyword: str) -> Optional[str]:
    """Phần sau keyword, chỉ hợp lệ khi trống/bắt đầu `:` hoặc whitespace. ← port keyword_tail"""
    if not line.startswith(keyword):
        return None
    rest = line[len(keyword):]
    if not rest or rest.startswith(":") or (rest and rest[0].isspace()):
        return rest
    return None


def parse_hunk_header(line: str) -> Optional[tuple[AnyTarget, bool]]:
    """PUT/CUT/REM/MV trên một dòng. ← port tokenizer::parse_hunk_header"""
    stripped = line.strip()
    rest = _keyword_tail(stripped, "REM")
    if rest is not None:
        return (RemTarget(), False) if not rest.strip() else None
    rest = _keyword_tail(stripped, "MV")
    if rest is not None:
        dest = _unquote_path(rest.strip())
        if dest:
            return MoveTarget(dest), False
        return None
    rest = _keyword_tail(stripped, "PUT")
    if rest is not None:
        return parse_put_target(rest)
    rest = _keyword_tail(stripped, "CUT")
    if rest is not None:
        return parse_cut_target(rest)
    return None


def _path_has_orphan_bracket(path: str) -> bool:
    """] không mở bằng [ → dòng chứa 2 nhóm bracket (noise). ← port header_path_has_orphan_bracket"""
    depth = 0
    for ch in path:
        if ch == "[":
            depth += 1
        elif ch == "]":
            if depth == 0:
                return True
            depth -= 1
    return False


def parse_header(line: str) -> Optional[tuple[str, Optional[str]]]:
    """`[path]` hoặc `[path#TAG]`. ← port tokenizer::parse_header

    TAG: đúng 4 hex (chấp nhận thường, chuẩn hóa HOA). path chứa `#` nữa → None
    (để rơi vào nhánh phục hồi của input.py).
    """
    stripped = line.rstrip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return None
    body = stripped[1:-1]
    if not body:
        return None
    if "#" in body:
        path, _, tag = body.rpartition("#")
        if (
            not path
            or "#" in path
            or _path_has_orphan_bracket(path)
            or len(tag) != HASH_LENGTH
            or not HASH_RE.fullmatch(tag)
        ):
            return None
        return path, tag.upper()
    if _path_has_orphan_bracket(body):
        return None
    return body, None


def classify_line(line: str, line_num: int) -> Token:
    """Phân loại một dòng patch. ← port tokenizer::classify_line"""
    if not line:
        return BlankToken(line_num)
    header = parse_header(line)
    if header is not None:
        return HeaderToken(line_num, header[0], header[1])
    op = parse_hunk_header(line)
    if op is not None:
        return OpToken(line_num, op[0], op[1])
    if line.startswith("+"):
        return PayloadToken(line_num, line[1:])
    return RawToken(line_num, line)


def is_op_line(line: str) -> bool:
    """Dòng có phải op header trọn vẹn? ← port Tokenizer::is_op"""
    return parse_hunk_header(line) is not None
