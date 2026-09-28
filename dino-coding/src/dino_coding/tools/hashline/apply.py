"""Áp edits đã parse lên text (LF-normalized).

Port phần lõi của crates/pi-edit/src/modes/hashline/apply.rs:
- resolve_clipboard_edits (hạ mức CUT/PASTE @register)
- validate_bounds + phantom-line guard
- materialize (bucket theo dòng, splice ngược dòng)

KHÔNG port trong phase này (cần tree-sitter): repair_indentation,
repair_landings, normalize_echoes, repair_boundaries. Engine sẽ apply đúng
như model viết — sai indent là trách nhiệm của model (đúng tinh thần omp
trước khi các lớp repair được thêm vào).
"""

from __future__ import annotations

from typing import Callable, Optional

from dino_coding.tools.hashline import messages
from dino_coding.tools.hashline.store import Clipboard
from dino_coding.tools.hashline.types import (
    Anchor, Cursor, Edit, EditCut, EditDelete, EditInsert, EditPaste,
)


def resolve_clipboard_edits(
    edits: list[Edit],
    file_lines: list[str],
    clipboard: Clipboard,
    on_warning: Callable[[str], None],
) -> list[Edit]:
    """Hạ mức CUT/PASTE thành Insert/Delete. ← port clipboard.rs (rút gọn)

    Quy tắc ẩn danh: một CUT ẩn danh pendings ngay trước PUT ẩn danh.
    Nhiều CUT ẩn danh → ambiguous; không có → EMPTY_PASTE.
    """
    out: list[Edit] = []
    for edit in edits:
        if isinstance(edit, EditCut):
            captured = file_lines[edit.range.start.line - 1 : edit.range.end.line]
            if edit.register:
                clipboard.named[edit.register] = captured
            else:
                clipboard.anon.append(captured)
            continue  # các Delete tương ứng đã có từ parser
        if isinstance(edit, EditPaste):
            register = edit.register
            if register is not None:
                if register not in clipboard.named:
                    known = ", ".join(f"`@{name}`" for name in sorted(clipboard.named))
                    raise ValueError(
                        f"`@{register}` was empty — no `CUT ... @{register}` precedes this op in "
                        "this call and no persisted register has that name — so nothing was "
                        f"pasted.{f' Available registers: {known}.' if known else ''}"
                    )
                lines = clipboard.named[register]
            else:
                if not clipboard.anon:
                    raise ValueError(messages.EMPTY_PASTE)
                if len(clipboard.anon) > 1:
                    raise ValueError(
                        f"{len(clipboard.anon)} unlabeled `CUT`s are pending — an unlabeled "
                        "paste cannot tell which one you meant. Label the moves "
                        "(`CUT ... @name` -> `PUT ... @name`), or keep at most one unlabeled "
                        "`CUT` before each unlabeled paste."
                    )
                lines = clipboard.anon.pop()
            cursor = edit.at.cursor
            rng = edit.at.range
            if rng is not None:
                # paste đè span: insert trước dòng đầu + delete cả span
                for text in lines:
                    out.append(
                        EditInsert(Cursor("before", rng.start), text, edit.line_num, edit.index)
                    )
                for line in range(rng.start.line, rng.end.line + 1):
                    out.append(EditDelete(Anchor(line), edit.line_num, edit.index))
            elif cursor is not None:
                for text in lines:
                    out.append(EditInsert(cursor, text, edit.line_num, edit.index))
            continue
        out.append(edit)
    return out


def validate_bounds(edits: list[Edit], lines: list[str]) -> None:
    """Mọi mỏ neo phải tồn tại trong file. ← port apply::validate_bounds"""
    for edit in edits:
        anchors: list[Anchor] = []
        if isinstance(edit, EditDelete):
            anchors.append(edit.anchor)
        elif isinstance(edit, EditInsert) and edit.cursor.anchor is not None:
            anchors.append(edit.cursor.anchor)
        for anchor in anchors:
            if not (1 <= anchor.line <= len(lines)):
                raise ValueError(messages.format_out_of_range(anchor.line, len(lines)))


def materialize(original: list[str], edits: list[Edit]) -> tuple[str, Optional[int]]:
    """Dựng văn bản mới từ edits. ← port apply::materialize (nguyên thuật toán)

    1. BOF-inserts gom về đầu; EOF-inserts gom về cuối (trước sentinel trống).
    2. Các edit còn lại bỏ vào bucket theo dòng mỏ neo.
    3. Xử lý bucket THEO DÒNG GIẢM DẦN → chỉ số dòng thấp không bị trôi.
    4. Trong một bucket: [insert-before] + [replacement] + [dòng cũ nếu không
       delete] + [insert-after], đúng thứ tự index.
    """
    lines = list(original)
    first_changed: Optional[int] = None
    bof: list[str] = []
    eof: list[str] = []
    buckets: dict[int, list[tuple[int, Edit]]] = {}
    for index, edit in enumerate(edits):
        if isinstance(edit, EditInsert):
            if edit.cursor.kind == "bof":
                bof.append(edit.text)
            elif edit.cursor.kind == "eof":
                eof.append(edit.text)
            elif edit.cursor.anchor is not None:
                buckets.setdefault(edit.cursor.anchor.line, []).append((index, edit))
        elif isinstance(edit, EditDelete):
            buckets.setdefault(edit.anchor.line, []).append((index, edit))

    for line in sorted(buckets, reverse=True):
        bucket = sorted(buckets[line], key=lambda pair: pair[0])
        idx = line - 1
        current = lines[idx] if idx < len(lines) else ""
        before: list[str] = []
        replacements: list[str] = []
        after: list[str] = []
        delete = False
        for _, edit in bucket:
            if isinstance(edit, EditInsert):
                if edit.cursor.kind == "after":
                    after.append(edit.text)
                elif edit.replacement:
                    replacements.append(edit.text)
                else:
                    before.append(edit.text)
            elif isinstance(edit, EditDelete):
                delete = True
        if not (before or replacements or after or delete):
            continue
        spliced = before + replacements + ([current] if not delete else []) + after
        lines[idx : idx + 1] = spliced
        first_changed = line if first_changed is None else min(first_changed, line)

    if bof:
        if len(lines) == 1 and lines[0] == "":
            lines = bof
        else:
            lines[0:0] = bof
        first_changed = 1
    if eof:
        if len(lines) == 1 and lines[0] == "":
            lines = eof
            first_changed = 1
        else:
            insert_at = len(lines) - 1 if lines and lines[-1] == "" else len(lines)
            lines[insert_at:insert_at] = eof
            first_changed = (
                insert_at + 1 if first_changed is None else min(first_changed, insert_at + 1)
            )
    return "\n".join(lines), first_changed


def phantom_line(lines: list[str]) -> Optional[int]:
    """File kết thúc bằng newline → sentinel trống cuối; không cho delete nó.
    ← port apply::phantom_line
    """
    if len(lines) > 1 and lines[-1] == "":
        return len(lines)
    return None


def apply_edits(
    text: str,
    edits: list[Edit],
    clipboard: Optional[Clipboard] = None,
) -> tuple[str, Optional[int], list[str]]:
    """Điểm vào áp edits. ← port apply::apply_edits (không phần repair).

    Trả về (text mới, dòng đổi đầu tiên, warnings).
    """
    if not edits:
        return text, None, []
    lines = text.split("\n")
    local_clipboard = clipboard if clipboard is not None else Clipboard()
    warnings: list[str] = []

    concrete = resolve_clipboard_edits(edits, lines, local_clipboard, warnings.append)
    for edit in concrete:
        if isinstance(edit, EditPaste):
            raise ValueError("UNRESOLVED_CLIPBOARD_INTERNAL")  # pragma: no cover

    phantom = phantom_line(lines)
    if phantom is not None:
        concrete = [
            e
            for e in concrete
            if not (isinstance(e, EditDelete) and e.anchor.line == phantom)
        ]

    validate_bounds(concrete, lines)
    new_text, first_changed = materialize(lines, concrete)
    return new_text, first_changed, warnings
