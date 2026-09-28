"""Block resolver cho ops `N*` — port pi-ast/src/block.rs::block_range_at và
pi-edit/src/modes/hashline/block.rs::resolve_block_edits.

Thay cho BLOCK_RESOLVER_UNAVAILABLE của Phase 2: `PUT N*:` / `CUT N*` /
`PUT >N*` giờ phân giải thành các edit dòng cụ thể qua cây cú pháp.
"""

from __future__ import annotations

import re
from typing import Optional

from ast_grep_py import SgRoot

from dino_coding.tools.astlang import resolve_language
from dino_coding.tools.hashline import messages
from dino_coding.tools.hashline.types import (
    Anchor,
    Cursor,
    Edit,
    EditBlock,
    EditCut,
    EditDelete,
    EditInsert,
    EditPaste,
    ParsedRange,
    PasteTarget,
)

BLOCK_SUGGESTION_SCAN_LIMIT = 64  # ← pi-edit/block.rs:27

# ← port STRUCTURAL_CLOSER_RE (pi-edit apply.rs:26)
STRUCTURAL_CLOSER_RE = re.compile(r"^\s*[)\]}]+[;,]?\s*$")

# Container "chuỗi statement": bắt đầu đúng chỗ con đầu tiên → nếu nhận khi leo
# lên sẽ nuốt các anh em kế tiếp. ← port pi-ast/block.rs::is_statement_sequence
_STATEMENT_SEQUENCE_KINDS = {
    "statement_list", "block", "body_statement", "statements", "body",
    "indented_block", "block_mapping", "block_sequence", "import_list",
    "hash_literal_body",
}

BlockSpan = tuple[int, int]  # (start_line, end_line) 1-based inclusive


class BlockUnresolved(ValueError):
    """Không phân giải được block — message model-facing kèm theo."""


def _first_content_column(code: str, row: int) -> Optional[int]:
    """Cột (0-based) của ký tự nội dung đầu tiên của dòng `row`; None nếu trống."""
    lines = code.split("\n")
    if row >= len(lines):
        return None
    for col, char in enumerate(lines[row]):
        if char not in (" ", "\t"):
            return col
    return None


def _subtree_has_error(node) -> bool:
    stack = [node]
    while stack:
        current = stack.pop()
        if current.kind() == "ERROR":
            return True
        stack.extend(current.children())
    return False


def block_range_at(code: str, path: str, line: int) -> Optional[BlockSpan]:
    """Block bắt đầu ĐÚNG dòng `line` (1-based), hoặc None.

    ← port pi-ast/block.rs::block_range_at. Binding không có
    named_descendant_for_point_range nên mô phỏng "point range (row,col)..(row,col+1)"
    bằng điều kiện chứa-điểm-mở: node ẩn zero-width (end == start) tự bị loại.
    """
    if line <= 0 or not code:
        return None
    lang = resolve_language(None, path)
    if lang is None:
        return None
    row, col = line - 1, _first_content_column(code, line - 1)
    if col is None:
        return None

    root = SgRoot(code, lang).root()
    node = root
    while True:
        nxt = None
        for child in node.children():
            rng = child.range()
            if (rng.start.line, rng.start.column) <= (row, col) < (rng.end.line, rng.end.column):
                nxt = child
                break
        if nxt is None:
            break
        node = nxt

    if node is root or node.range().start.line != row:
        return None  # dòng tiếp diễn / dòng đóng của block trước đó

    while True:
        parent = node.parent()
        if parent is None or parent.parent() is None:  # parent là root → dừng
            break
        if parent.range().start.line != row:
            break
        if (
            parent.kind() in _STATEMENT_SEQUENCE_KINDS
            and (parent.range().start.line, parent.range().start.column)
            == (node.range().start.line, node.range().start.column)
        ):
            break
        node = parent

    if _subtree_has_error(node):
        return None
    rng = node.range()
    return (rng.start.line + 1, rng.end.line + 1)


def find_next_block(anchor_line: int, code: str, path: str) -> Optional[BlockSpan]:
    """Block đa dòng ĐẦU TIÊN bắt đầu sau `anchor_line`, trong phạm vi quét 64 dòng.
    ← port find_next_block (block.rs:57-79): skip dòng trống trước khi parse."""
    lines = code.split("\n")
    last = min(len(lines), anchor_line + BLOCK_SUGGESTION_SCAN_LIMIT)
    for candidate in range(anchor_line + 1, last + 1):
        if not lines[candidate - 1].strip():
            continue  # dòng trống không thể mở block — khỏi parse (block.rs:65)
        span = block_range_at(code, path, candidate)
        if span and span[0] == candidate and span[0] != span[1]:
            return span
    return None


def find_enclosing_block(anchor_line: int, code: str, path: str) -> Optional[BlockSpan]:
    """Block đa dòng GẦN NHẤT bao chứa `anchor_line`, quét tối đa 64 dòng lên trên.
    ← port find_enclosing_block (block.rs:81-106): đi TỪ GẦN ĐẾN XA (rev),
    chỉ nhận block bắt đầu TRƯỚC anchor (start < anchor) và chạm tới anchor."""
    lines = code.split("\n")
    first = max(1, anchor_line - BLOCK_SUGGESTION_SCAN_LIMIT)
    for start in range(anchor_line - 1, first - 1, -1):
        if not lines[start - 1].strip():
            continue
        span = block_range_at(code, path, start)
        if span and span[0] == start and span[1] >= anchor_line and span[1] > start:
            return span
    return None


def _op_phrase(mode: Optional[str], register: Optional[str], line: int) -> tuple[str, str]:
    """(dạng block, dạng dòng cụ thể) cho thông báo — PUT/CUT với @register."""
    reg = f" @{register}" if register else ""
    if mode == "cut":
        return f"CUT {line}*{reg}", f"CUT {line}.=M{reg}"
    colon = ":" if not register else ""
    return f"PUT {line}*{reg}{colon}", f"PUT {line}.=M{reg}{colon}"


def resolve_block_edits(
    edits: list[Edit], text: str, path: str
) -> tuple[list[Edit], list[str]]:
    """Hạ mọi EditBlock thành edit dòng cụ thể. ← port resolve_block_edits.

    Trả (edits_mới, warnings). Ném BlockUnresolved(message) khi một op
    replace/cut không phân giải được — caller (patcher) biến thành reject.

    Hạ mức (đúng block.rs:215-298):
    - mode "paste_after"  → EditPaste vào gap sau span.end
    - mode "cut"          → EditCut(range) + EditDelete từng dòng span
    - mode "insert_after" → EditInsert sau span.end (KHÔNG replacement)
    - mode None + register→ EditPaste đè span
    - mode None           → EditInsert trước span.start (replacement) + Delete span

    mode "insert_after"/"paste_after" KHÔNG phân giải được thì hạ tiếp thành
    op dòng thường + warning (block.rs:130-167) — chèn sau dòng N vẫn hợp lệ.
    """
    lowered: list[Edit] = []
    warnings: list[str] = []
    synth = 0  # index tổng hợp cho các edit sinh ra — giữ thứ tự ổn định

    for edit in edits:
        if not isinstance(edit, EditBlock):
            lowered.append(edit)
            continue
        anchor_line = edit.anchor.line
        span = block_range_at(text, path, anchor_line)

        if span is None:
            if edit.mode in ("insert_after", "paste_after"):
                is_closer = bool(
                    STRUCTURAL_CLOSER_RE.match(
                        text.split("\n")[anchor_line - 1]
                        if anchor_line <= len(text.split("\n")) else ""
                    )
                )
                plain = f"PUT >{anchor_line}" + (":" if edit.payloads else "")
                if is_closer:
                    warning = messages.block_closer_lowered_warning(
                        f"PUT >{anchor_line}*", plain
                    )
                else:
                    warning = messages.block_unresolved_lowered_warning(
                        f"PUT >{anchor_line}*", anchor_line, plain
                    )
                warnings.append(warning)
                if edit.mode == "paste_after":
                    lowered.append(EditPaste(
                        at=PasteTarget(cursor=Cursor("after", Anchor(anchor_line))),
                        register=edit.register,
                        line_num=edit.line_num,
                        index=synth,
                    ))
                else:
                    for payload in edit.payloads:
                        lowered.append(EditInsert(
                            cursor=Cursor("after", Anchor(anchor_line)),
                            text=payload,
                            line_num=edit.line_num,
                            index=synth,
                        ))
                synth += 1
                continue

            next_block = find_next_block(anchor_line, text, path)
            enclosing = find_enclosing_block(anchor_line, text, path)
            block_form, fallback = _op_phrase(edit.mode, edit.register, anchor_line)
            raise BlockUnresolved(messages.block_unresolved_message(
                anchor_line, block_form, fallback,
                next_block, enclosing,
            ))

        if span[0] == span[1]:
            enclosing = find_enclosing_block(anchor_line, text, path)
            block_form, _ = _op_phrase(edit.mode, edit.register, anchor_line)
            raise BlockUnresolved(messages.block_single_line_message(
                anchor_line, block_form, enclosing
            ))

        rng = ParsedRange(Anchor(span[0]), Anchor(span[1]))
        if edit.mode == "paste_after":
            lowered.append(EditPaste(
                at=PasteTarget(cursor=Cursor("after", Anchor(span[1]))),
                register=edit.register, line_num=edit.line_num, index=synth,
            ))
        elif edit.mode == "cut":
            lowered.append(EditCut(
                range=rng, register=edit.register,
                line_num=edit.line_num, index=synth,
            ))
            for line in range(span[0], span[1] + 1):
                lowered.append(EditDelete(Anchor(line), edit.line_num, synth))
        elif edit.mode == "insert_after":
            for payload in edit.payloads:
                lowered.append(EditInsert(
                    cursor=Cursor("after", Anchor(span[1])), text=payload,
                    line_num=edit.line_num, index=synth, replacement=False,
                ))
        elif edit.register is not None:
            lowered.append(EditPaste(
                at=PasteTarget(range=rng), register=edit.register,
                line_num=edit.line_num, index=synth,
            ))
        else:
            for payload in edit.payloads:
                lowered.append(EditInsert(
                    cursor=Cursor("before", Anchor(span[0])), text=payload,
                    line_num=edit.line_num, index=synth, replacement=True,
                ))
            for line in range(span[0], span[1] + 1):
                lowered.append(EditDelete(Anchor(line), edit.line_num, synth))
        synth += 1

    return lowered, warnings
