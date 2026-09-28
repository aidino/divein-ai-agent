"""Stage một patch: verify snapshot tag → seen-lines guard → apply in-memory.

Port rút gọn của crates/pi-edit/src/modes/hashline/patcher.rs
(bỏ fuzzy recovery và path-recovery-by-suffix).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from dino_coding.tools.hashline import messages
from dino_coding.tools.hashline.apply import apply_edits
from dino_coding.tools.hashline.block import BlockUnresolved, resolve_block_edits
from dino_coding.tools.hashline.diffpreview import compact_preview
from dino_coding.tools.hashline.input import Patch, PatchSection
from dino_coding.tools.hashline.store import Clipboard, EditStore
from dino_coding.tools.hashline.text import (
    LineEnding, file_hash, normalize_to_lf, payload_hash, strip_bom,
)
from dino_coding.tools.hashline.types import EditBlock

if TYPE_CHECKING:
    from dino_coding.tools.workspace import WorkspacePolicy

SEEN_LINE_REVEAL_CAP = 40        # ← port patcher.rs
SEEN_LINE_REVEAL_MAX_COLUMNS = 512


class EditRejected(ValueError):
    """Lỗi model-facing — message sẽ được trả nguyên văn cho model."""


@dataclass
class FileRead:
    """Kết quả đọc một file mục tiêu qua path policy."""
    display_path: str
    absolute_path: str
    raw: str            # bytes gốc (đã decode, còn BOM/CRLF)
    text: str           # LF-normalized, BOM-stripped
    ending: str


@dataclass
class StagedFile:
    """Trạng thái sau-edit của một file, chưa ghi đĩa. ← port engine::StagedFile (rút gọn)"""
    display_path: str
    absolute_path: str
    op: str = "update"          # update | create | delete | noop | move
    before: str = ""
    after: str = ""
    ending: str = "lf"
    move_to: Optional[str] = None
    diff_preview: str = ""
    first_changed_line: Optional[int] = None
    warnings: list[str] = field(default_factory=list)
    new_tag: Optional[str] = None
    read: Optional[FileRead] = None


def _reject(message: str) -> EditRejected:
    return EditRejected(message)


def read_target(display_path: str, absolute_path: str) -> FileRead:

    # newline="" tắt universal newlines: giữ nguyên \r\n để detect() đo đúng kiểu dòng
    with open(absolute_path, "r", encoding="utf-8", errors="strict", newline="") as handle:
        raw = handle.read()
    ending = LineEnding.detect(raw)
    text = normalize_to_lf(strip_bom(raw))
    return FileRead(display_path, absolute_path, raw, text, ending)


def _assert_seen_lines(
    section: PatchSection,
    expected: str,
    store: EditStore,
    canonical: str,
    text: str,
) -> None:
    """Guard seen-lines. ← port patcher::assert_seen_lines"""
    snapshot = store.by_content(canonical, text)
    if snapshot is None or not snapshot.seen_lines:
        return
    unseen = [line for line in section.collect_anchor_lines() if line not in snapshot.seen_lines]
    if not unseen:
        return
    source = snapshot.text.split("\n")
    revealed: list[tuple[int, str]] = []
    column_truncated = False
    for line in unseen[:SEEN_LINE_REVEAL_CAP]:
        if not (1 <= line <= len(source)):
            continue
        value = source[line - 1]
        if len(value) > SEEN_LINE_REVEAL_MAX_COLUMNS:
            revealed.append((line, value[:SEEN_LINE_REVEAL_MAX_COLUMNS] + "…"))
            column_truncated = True
        else:
            revealed.append((line, value))
    truncated = len(unseen) > len(revealed) or column_truncated
    if not truncated:
        store.record_seen_lines(canonical, expected, [n for n, _ in revealed])
    raise _reject(
        messages.unseen_lines_message(section.path, unseen, expected, revealed, truncated)
    )


def _mismatch(
    section: PatchSection,
    canonical: str,
    normalized: str,
    expected: str,
    store: EditStore,
) -> EditRejected:
    actual = file_hash(normalized)
    store.record(canonical, normalized, None)
    raise _reject(
        messages.format_mismatch_message(
            path=section.path,
            expected=expected,
            actual=actual,
            file_lines=normalized.split("\n"),
            anchor_lines=section.collect_anchor_lines(),
            hash_recognized=store.by_hash(canonical, expected) is not None,
        )
    )


def _has_anchor_scoped_edit(section: PatchSection) -> bool:
    return section.has_anchor_scoped_edit()


def stage_patch(
    patch: Patch,
    raw_input: str,
    store: EditStore,
    workspace: "WorkspacePolicy",
    enforce_seen_lines: bool = True,
) -> list[StagedFile]:
    """Stage mọi section — atomic: lỗi bất kỳ section nào → không ghi gì.
    ← port patcher::stage_patch
    """
    clipboard = store.start_clipboard_batch()
    staged: list[StagedFile] = []
    for section in patch.sections:
        staged.append(
            _stage_section(section, raw_input, store, workspace, clipboard, enforce_seen_lines)
        )
    store.commit_clipboard(clipboard)
    return staged


def _stage_section(
    section: PatchSection,
    raw_input: str,
    store: EditStore,
    workspace: "WorkspacePolicy",
    clipboard: Clipboard,
    enforce_seen_lines: bool,
) -> StagedFile:
    parsed = section.parse()
    if section.file_hash is None:
        raise _reject(messages.missing_snapshot_tag_message(section.path))

    absolute = workspace.resolve(section.path)
    if not os.path.isfile(absolute):
        raise _reject(messages.file_not_found_message(section.path))
    read = read_target(section.path, absolute)
    canonical = workspace.canonical_key(absolute)

    if any(isinstance(edit, EditBlock) for edit in parsed.edits):
        try:
            lowered, block_warnings = resolve_block_edits(
                parsed.edits, read.text, section.path
            )
        except BlockUnresolved as error:
            raise _reject(f"{section.path}: {error}")
        parsed.edits = lowered
        parsed.warnings = parsed.warnings + block_warnings

    expected = section.file_hash
    live_matches = file_hash(read.text).upper() == expected.upper()

    if parsed.file_op and parsed.file_op.kind == "move":
        dest_abs = workspace.resolve(parsed.file_op.dest or "")
        if workspace.canonical_key(dest_abs) == canonical:
            raise _reject(f"MV destination is the same as {section.path}.")

    if parsed.file_op and parsed.file_op.kind == "rem":
        staged = StagedFile(section.path, absolute, op="delete", before=read.text,
                            ending=read.ending, read=read)
        staged.warnings = list(parsed.warnings)
        return staged

    if live_matches:
        if enforce_seen_lines:
            _assert_seen_lines(section, expected, store, canonical, read.text)
        new_text, first_changed, apply_warnings = apply_edits(read.text, parsed.edits, clipboard)
    elif not _has_anchor_scoped_edit(section):
        # head/tail inserts không có mỏ neo — áp lên nội dung hiện tại + cảnh báo
        new_text, first_changed, apply_warnings = apply_edits(read.text, parsed.edits, clipboard)
        apply_warnings = [messages.HEADTAIL_DRIFT_WARNING] + apply_warnings
    else:
        raise _mismatch(section, canonical, read.text, expected, store)

    staged = StagedFile(
        display_path=section.path,
        absolute_path=absolute,
        before=read.text,
        after=new_text,
        ending=read.ending,
        first_changed_line=first_changed,
        read=read,
    )
    staged.warnings = list(parsed.warnings) + apply_warnings

    if parsed.file_op and parsed.file_op.kind == "move":
        staged.op = "move"
        staged.move_to = workspace.resolve(parsed.file_op.dest or "")

    if new_text == read.text and staged.op == "update":
        staged.op = "noop"
        count, escalate = store.record_noop(canonical, payload_hash(raw_input))
        if escalate:
            raise _reject(messages.no_change_loop_diagnostic(section.path, count))
        # no_change_diagnostic sẽ được render ở editor.py

    staged.diff_preview = compact_preview(read.text.split("\n"), new_text.split("\n"))
    return staged
