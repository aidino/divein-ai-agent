"""Executor: dịch op headers + body thành edits cấp thấp.

Port rút gọn của crates/pi-edit/src/modes/hashline/parser.rs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from dino_coding.tools.hashline import messages
from dino_coding.tools.hashline.tokenizer import (
    AnyTarget, BofTarget, BlockTarget, CutBlockTarget, CutTarget, EofTarget,
    InsertAfterBlockTarget, InsertAfterTarget, InsertBeforeTarget, MoveTarget,
    RemTarget, ReplaceTarget, classify_line, is_op_line,
    BlankToken, HeaderToken, OpToken, PayloadToken, RawToken, target_register,
)
from dino_coding.tools.hashline.types import (
    Anchor, Cursor, EditBlock, EditCut, EditDelete, EditInsert, EditPaste,
    FileOp, Parsed, ParsedRange, PasteTarget,
)

MAX_EXPANDED_RANGE_LINES = 100_000  # ← port parser::MAX_EXPANDED_RANGE_LINES

# Dòng metadata của read (truncation notice) — bỏ qua với warning. ← port prefixes.rs
READ_METADATA_RE = re.compile(r"^\s*[\[（(]")

# ← port parser.rs::UNIFIED_HUNK_RE
UNIFIED_HUNK_RE = re.compile(r"^@@\s+[-+]?\d+,\d+\s+[-+]?\d+,\d+\s+@@")

# ← port parser.rs: apply_patch sentinels bị dán nhầm vào hashline input
_APPLY_PATCH_PREFIXES = (
    "*** Update File:",
    "*** Add File:",
    "*** Delete File:",
    "*** Move to:",
)


@dataclass
class _PayloadRow:
    text: str
    line_num: int
    bare: bool = False
    minus: bool = False


@dataclass
class _Pending:
    target: AnyTarget
    line_num: int
    payloads: list[_PayloadRow] = field(default_factory=list)
    had_colon: bool = False
    deferred_blanks: list[_PayloadRow] = field(default_factory=list)


class Executor:
    """Bộ thực thi token→edit tăng dần. ← port parser::Executor"""

    def __init__(self) -> None:
        self.edits: list = []
        self.warnings: list[str] = []
        self._edit_index = 0
        self._pending: Optional[_Pending] = None
        self._file_op: Optional[FileOp] = None
        self._recovered_lines: set[int] = set()

    # ---------- API ----------

    def feed_line(self, line: str, line_num: int) -> None:
        token = classify_line(line, line_num)
        self.feed(token)

    def feed(self, token) -> None:

        if isinstance(token, HeaderToken):
            self._flush_pending()
        elif isinstance(token, BlankToken):
            self._handle_blank("", token.line_num)
        elif isinstance(token, PayloadToken):
            self._handle_literal(token.text, token.line_num)
        elif isinstance(token, OpToken):
            self._handle_op(token)
        elif isinstance(token, RawToken):
            self._handle_raw(token.text, token.line_num)

    def finish(self) -> Parsed:
        self._flush_pending()
        if self._file_op and self._file_op.kind == "rem" and self.edits:
            raise ValueError(
                "`REM` deletes the whole file and cannot be combined with line ops."
            )
        self._normalize_overlaps()
        return Parsed(edits=self.edits, file_op=self._file_op, warnings=self.warnings)

    # ---------- contamination guard ← port parser.rs::contamination_message ----------

    def _contamination_check(self, text: str, line_num: int) -> None:
        """Phát hiện dòng bị lẫn từ các định dạng diff/patch khác (apply_patch, unified diff).

        ← port parser.rs::contamination_message — giữ nguyên English cho model-facing.
        """
        trimmed = text.lstrip()
        # apply_patch sentinels (`*** Update File:`, `*** Add File:`, ...)
        for prefix in _APPLY_PATCH_PREFIXES:
            if trimmed.startswith(prefix):
                preview = trimmed[:48] + "…" if len(trimmed) > 48 else trimmed
                raise ValueError(
                    f"line {line_num}: apply_patch sentinel {messages.json_quote(preview)} "
                    "is not valid in hashline. File sections start with `[path#HASH]` "
                    "(no `Update File:` / `Add File:` keyword). Use `PUT N.=M:`, "
                    "`CUT N.=M`, or `PUT <N:`/`PUT >N:` ops."
                )
        # unified-diff hunk header (`@@ -N,M +N,M @@`)
        if trimmed.startswith("@@"):
            if UNIFIED_HUNK_RE.match(trimmed):
                raise ValueError(
                    f"line {line_num}: unified-diff hunk header (`@@ -N,M +N,M @@`) "
                    "is not valid in hashline. Use `PUT N.=M:`, `CUT N.=M`, "
                    "or `PUT <N:`/`PUT >N:` ops."
                )
            preview = trimmed[:48] + "…" if len(trimmed) > 48 else trimmed
            raise ValueError(
                f"line {line_num}: `@@`-bracketed hunk header "
                f"{messages.json_quote(preview)} is not valid in hashline. "
                "Drop the `@@ ... @@` brackets and write a header such as `PUT N.=M:`."
            )
        # Lone number (e.g. model pastes just "42")
        stripped = trimmed.strip()
        if stripped and all(ch.isdigit() or ch.isspace() for ch in stripped):
            parts = stripped.split()
            if len(parts) == 1:
                raise ValueError(
                    f"line {line_num}: hunk headers need a verb and both endpoints. "
                    f"Use `PUT {stripped}.={stripped}:` to replace, or "
                    f"`CUT {stripped}.={stripped}` to delete."
                )
        # Bare two-number range without verb ("3 5" or "3 5:")
        pieces = trimmed.rstrip(":").split()
        if len(pieces) == 2 and all(p.isdigit() for p in pieces):
            raise ValueError(
                f"line {line_num}: bare range hunk header "
                f"{messages.json_quote(trimmed)} is not valid. "
                "Hunk headers need a verb: use `PUT N.=M:` or `CUT N.=M`."
            )

    # ---------- ops ----------

    def _handle_op(self, token) -> None:
        target, line_num, had_colon = token.target, token.line_num, token.had_colon
        if isinstance(target, (ReplaceTarget, CutTarget)):
            self._validate_range(target.range, line_num)
        if had_colon and isinstance(target, (CutTarget, CutBlockTarget)):
            self._warn_once(messages.CUT_COLON_IGNORED_WARNING)
        if had_colon and not isinstance(target, (RemTarget, MoveTarget)) and target_register(target):
            raise ValueError(
                f"line {line_num}: {messages.COLON_ON_REGISTER_PUT}"
            )
        if isinstance(target, (RemTarget, MoveTarget)):
            self._flush_pending()
            self._set_file_op(target, line_num)
            return
        self._flush_pending()
        self._pending = _Pending(target=target, line_num=line_num, had_colon=had_colon)

    def _set_file_op(self, target: AnyTarget, line_num: int) -> None:
        if self._file_op is not None:
            raise ValueError(
                f"line {line_num}: only one file-level op (`REM` or `MV`) per section. "
                "Merge them under one header."
            )
        if isinstance(target, RemTarget):
            if self.edits:
                raise ValueError(f"line {line_num}: {messages.REM_TAKES_NO_BODY}")
            self._file_op = FileOp(kind="rem")
        elif isinstance(target, MoveTarget):
            self._file_op = FileOp(kind="move", dest=target.dest)

    # ---------- body rows ----------

    def _handle_literal(self, text: str, line_num: int) -> None:
        if self._pending is None:
            if self._file_op is not None:
                raise ValueError(f"line {line_num}: {messages.MOVE_TAKES_NO_BODY}")
            raise ValueError(
                f"line {line_num}: payload line has no preceding hunk header. "
                f"Got {messages.json_quote('+' + text)}."
            )
        self._reject_bodyless(line_num)
        self._pending.payloads.extend(self._pending.deferred_blanks)
        self._pending.deferred_blanks.clear()
        if is_op_line(text):
            self.warnings.append(
                f"line {line_num}: body row `{text}` is itself a valid hunk header, so it was "
                "inserted as literal text rather than executed. Drop the `+` to run it."
            )
        self._pending.payloads.append(_PayloadRow(text, line_num))

    def _handle_raw(self, text: str, line_num: int) -> None:
        if self._pending is None:
            if READ_METADATA_RE.match(text):
                self._warn_once(messages.READ_METADATA_IGNORED_WARNING)
                return
            self._contamination_check(text, line_num)
            if self._file_op is not None:
                raise ValueError(f"line {line_num}: {messages.MOVE_TAKES_NO_BODY}")
            if not text.strip():
                return
            bare_range = _parse_bare_range(text)
            if bare_range is not None:
                self._validate_range(bare_range, line_num)
                self._pending = _Pending(
                    target=ReplaceTarget(bare_range), line_num=line_num, had_colon=True
                )
                self._warn_once(messages.BARE_RANGE_AUTO_PUT_WARNING)
                return
            snapshot_row = _parse_snapshot_row(text)
            if snapshot_row is not None:
                line, value = snapshot_row
                if line in self._recovered_lines:
                    raise ValueError(
                        f"line {line_num}: two or more pasted `{line}:TEXT` rows name line "
                        f"{line}. Write one `PUT {line}.=M:` header covering the changing lines, "
                        "followed by `+TEXT` body rows with their final content."
                    )
                self._recovered_lines.add(line)
                rng = ParsedRange(Anchor(line), Anchor(line))
                self._push_insert(Cursor("before", Anchor(line)), value, line_num, replacement=True)
                self._push_delete_range(rng, line_num)
                self._warn_once(messages.SNAPSHOT_ROWS_AUTO_PUT_WARNING)
                return
            raise ValueError(
                f"line {line_num}: payload line has no preceding hunk header. Use `PUT N.=M:`, "
                f"`CUT N.=M`, or `PUT <N:`/`PUT >N:` above the body. Got {messages.json_quote(text)}."
            )
        if not text.strip():
            self._handle_blank(text, line_num)
            return
        self._reject_bodyless(line_num)
        minus = text.lstrip().startswith("-")
        if not minus:
            self._warn_once(messages.BARE_BODY_AUTO_PIPED_WARNING)
        self._pending.payloads.extend(self._pending.deferred_blanks)
        self._pending.deferred_blanks.clear()
        self._pending.payloads.append(_PayloadRow(text, line_num, bare=True, minus=minus))

    def _handle_blank(self, text: str, line_num: int) -> None:
        if self._pending is None:
            return
        if self._bodyless_message() or not self._pending.payloads:
            return
        # Blank trong thân payload: hoãn lại — chỉ giữ nếu có nội dung theo sau.
        self._pending.deferred_blanks.append(_PayloadRow(text, line_num, bare=True))

    def _reject_bodyless(self, line_num: int) -> None:
        message = self._bodyless_message()
        if message:
            raise ValueError(f"line {line_num}: {message}")

    def _bodyless_message(self) -> Optional[str]:
        target = self._pending.target if self._pending else None
        if target is None:
            return None
        if isinstance(target, (CutTarget, CutBlockTarget)):
            return messages.CUT_TAKES_NO_BODY
        if isinstance(target, (RemTarget, MoveTarget)):
            return None
        if target_register(target):
            return messages.REGISTER_PUT_TAKES_NO_BODY
        if not self._pending.had_colon:
            return messages.COLONLESS_PUT_TAKES_NO_BODY
        return None

    # ---------- flush: hạ mức pending thành edits ----------

    def _flush_pending(self) -> None:
        pending = self._pending
        if pending is None:
            return
        self._pending = None
        self._resolve_minus_rows(pending.payloads)
        _strip_uniform_bare_prefixes(pending.payloads)
        target, line = pending.target, pending.line_num

        if isinstance(target, (RemTarget, MoveTarget)):
            return
        if isinstance(target, CutTarget):
            self._push_cut(target.range, target.register, line)
        elif isinstance(target, CutBlockTarget):
            self.edits.append(
                EditBlock(target.anchor, [], "cut", target.register, line, self._next_index())
            )
        elif isinstance(target, ReplaceTarget):
            if target.register is not None:
                self._push_paste(PasteTarget(range=target.range), target.register, line)
            elif not pending.payloads:
                if not pending.had_colon:
                    raise ValueError(f"line {line}: {messages.COLONLESS_SPAN_PUT}")
                self._push_delete_range(target.range, line)
                self._warn_once(messages.EMPTY_PUT_AUTO_CUT_WARNING)
            else:
                for row in pending.payloads:
                    self._push_insert(
                        Cursor("before", target.range.start), row.text, line, replacement=True
                    )
                self._push_delete_range(target.range, line)
        elif isinstance(target, BlockTarget):
            self.edits.append(
                EditBlock(
                    target.anchor,
                    [row.text for row in pending.payloads],
                    None,
                    target.register,
                    line,
                    self._next_index(),
                )
            )
        elif isinstance(target, InsertAfterBlockTarget):
            if target.register is not None or (
                not pending.had_colon and not pending.payloads
            ):
                self._push_paste(
                    PasteTarget(cursor=Cursor("after", target.anchor)), target.register, line
                )
            elif not pending.payloads:
                raise ValueError(f"line {line}: {messages.EMPTY_INSERT}")
            else:
                self.edits.append(
                    EditBlock(
                        target.anchor,
                        [row.text for row in pending.payloads],
                        "insert_after",
                        None,
                        line,
                        self._next_index(),
                    )
                )
        else:
            # InsertBefore / InsertAfter / Bof / Eof
            if isinstance(target, InsertBeforeTarget):
                cursor = Cursor("before", target.anchor)
            elif isinstance(target, InsertAfterTarget):
                cursor = Cursor("after", target.anchor)
            elif isinstance(target, BofTarget):
                cursor = Cursor("bof")
            elif isinstance(target, EofTarget):
                cursor = Cursor("eof")
            else:  # pragma: no cover
                raise ValueError(f"line {line}: unsupported target")
            if target_register(target) is not None or (
                not pending.had_colon and not pending.payloads
            ):
                self._push_paste(PasteTarget(cursor=cursor), target_register(target), line)
            elif not pending.payloads:
                raise ValueError(f"line {line}: {messages.EMPTY_INSERT}")
            else:
                for row in pending.payloads:
                    self._push_insert(cursor, row.text, line, replacement=False)

    def _resolve_minus_rows(self, rows: list[_PayloadRow]) -> None:
        """`-` rows: bullet MD → giữ như literal; diff context → bỏ; còn lại → lỗi.
        ← port parser::resolve_minus_rows
        """
        minus_rows = [row for row in rows if row.minus]
        if not minus_rows:
            return
        all_bullets = all(_markdown_bullet(row.text) for row in minus_rows)
        explicit = [row for row in rows if not row.bare]
        if all_bullets and (not explicit or any(_markdown_bullet(r.text) for r in explicit)):
            self._warn_once(messages.MINUS_BULLET_AUTO_PIPED_WARNING)
            return
        if explicit and not all_bullets:
            rows[:] = [row for row in rows if not row.minus]
            self._warn_once(messages.DIFF_OLD_ROWS_IGNORED_WARNING)
            return
        raise ValueError(f"line {minus_rows[0].line_num}: {messages.MINUS_ROW_REJECTED}")

    def _normalize_overlaps(self) -> None:
        """Một dòng chỉ được một hunk sở hữu; trùng hoàn toàn → gộp. ← port normalize_overlaps"""
        hunks: dict[int, tuple[set[int], bool]] = {}
        for edit in self.edits:
            if isinstance(edit, EditCut):
                lines, is_clip = hunks.setdefault(edit.line_num, (set(), False))
                hunks[edit.line_num] = (lines, True)
            elif isinstance(edit, EditPaste) and edit.at.range is not None:
                lines, _ = hunks.setdefault(edit.line_num, (set(), False))
                lines.update(range(edit.at.range.start.line, edit.at.range.end.line + 1))
                hunks[edit.line_num] = (lines, True)
            elif isinstance(edit, EditDelete):
                lines, is_clip = hunks.setdefault(edit.line_num, (set(), False))
                lines.add(edit.anchor.line)
                hunks[edit.line_num] = (lines, is_clip)
        if not hunks:
            return
        owner: dict[int, int] = {}
        dropped: set[int] = set()
        for line_num in sorted(hunks):
            hunk_lines, is_clip = hunks[line_num]
            if not hunk_lines:
                continue
            overlaps = {owner[line] for line in hunk_lines if line in owner}
            if not overlaps:
                for line in hunk_lines:
                    owner[line] = line_num
                continue
            if len(overlaps) == 1:
                prev = next(iter(overlaps))
                prev_lines, prev_clip = hunks[prev]
                if not prev_clip and prev_lines == hunk_lines:
                    dropped.add(prev)
                    for line in hunk_lines:
                        owner[line] = line_num
                    self._warn_once(messages.REPLACE_PAIR_COALESCED_WARNING)
                    continue
            first = next(line for line in sorted(hunk_lines) if line in owner)
            prior = next(iter(overlaps)) if len(overlaps) == 1 else "an earlier line"
            raise ValueError(
                f"line {line_num}: anchor line {first} is already targeted by another hunk on "
                f"line {prior}. Issue ONE hunk per range; payload is only the final desired "
                "content, never a before/after pair."
            )
        if dropped:
            self.edits[:] = [e for e in self.edits if e.line_num not in dropped]

    # ---------- helpers ----------

    def _validate_range(self, rng: ParsedRange, line_num: int) -> None:
        if rng.end.line < rng.start.line:
            raise ValueError(
                f"line {line_num}: Invalid absolute range: start {rng.start.line}, end "
                f"{rng.end.line}. The value after `.=` is an absolute source line, not a line "
                f"count or replacement length. For one line use `PUT {rng.start.line}:`."
            )
        span = rng.end.line - rng.start.line + 1
        if span > MAX_EXPANDED_RANGE_LINES:
            raise ValueError(
                f"line {line_num}: range spans {span} lines; the maximum is "
                f"{MAX_EXPANDED_RANGE_LINES}. Split it into smaller hunks."
            )

    def _warn_once(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def _next_index(self) -> int:
        index = self._edit_index
        self._edit_index += 1
        return index

    def _push_insert(self, cursor: Cursor, text: str, line_num: int, replacement: bool) -> None:
        self.edits.append(
            EditInsert(cursor, text, line_num, self._next_index(), replacement)
        )

    def _push_delete(self, anchor: Anchor, line_num: int) -> None:
        self.edits.append(EditDelete(anchor, line_num, self._next_index()))

    def _push_delete_range(self, rng: ParsedRange, line_num: int) -> None:
        for line in range(rng.start.line, rng.end.line + 1):
            self._push_delete(Anchor(line), line_num)

    def _push_cut(self, rng: ParsedRange, register: Optional[str], line_num: int) -> None:
        self.edits.append(EditCut(rng, register, line_num, self._next_index()))
        self._push_delete_range(rng, line_num)

    def _push_paste(self, at: PasteTarget, register: Optional[str], line_num: int) -> None:
        self.edits.append(EditPaste(at, register, line_num, self._next_index()))


def _markdown_bullet(text: str) -> bool:
    trimmed = text.lstrip()
    return (
        trimmed.startswith("- ")
        and len(trimmed) > 2
        and not trimmed[2].isspace()
    )


def _parse_snapshot_row(text: str) -> Optional[tuple[int, str]]:
    """`123:text` copy nguyên từ read output → phục hồi thành PUT 1 dòng."""
    trimmed = text.lstrip()
    split = next((i for i, ch in enumerate(trimmed) if ch in ":|"), None)
    if split is None or split == 0:
        return None
    number = trimmed[:split]
    if number.startswith("0") or not number.isdigit():
        return None
    return int(number), trimmed[split + 1:]


def _parse_bare_range(text: str) -> Optional[ParsedRange]:
    """`3.=5:` không có verb → phục hồi thành PUT. ← port parser::parse_bare_range"""
    trimmed = text.strip()
    if not trimmed.endswith(":"):
        return None
    before = trimmed[:-1].strip()
    parts = [p for p in re.split(r"[\s\-.=…]+", before) if p]
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return None
    start, end = int(parts[0]), int(parts[1])
    if start == 0 or end == 0:
        return None
    return ParsedRange(Anchor(start), Anchor(end))


_PREFIX_RE = re.compile(r"^\s*(?:(?:>>>|>>)\s*)?(?:[+*-]\s*)?\d+[:|]")


def _strip_uniform_bare_prefixes(rows: list[_PayloadRow]) -> None:
    """Bare rows đều mang số dòng prefix → lột một lớp. ← port strip_uniform_bare_prefixes"""
    bare = [row for row in rows if row.bare and row.text.strip()]
    if not bare:
        return
    stripped = [_PREFIX_RE.sub("", row.text, count=1) for row in bare]
    if any(s == row.text for s, row in zip(stripped, bare)):
        return
    if all(_literal_value(s) for s in stripped):
        return  # giá trị literal như "12:30" — không phải prefix
    mapping = {id(row): s for row, s in zip(bare, stripped)}
    for row in rows:
        if id(row) in mapping:
            row.text = mapping[id(row)]


def _literal_value(text: str) -> bool:
    value = text.strip().rstrip(",").strip()
    return (
        len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'"
    ) or _is_number(value)


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def parse_patch(diff: str) -> Parsed:
    """Parse trọn một thân section. ← port parser::parse_patch"""
    executor = Executor()
    for index, line in enumerate(diff.split("\n"), start=1):
        executor.feed_line(line, index)
    return executor.finish()
