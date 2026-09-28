"""Tách patch thô thành các section theo header [PATH#TAG].

Port rút gọn của crates/pi-edit/src/modes/hashline/input.rs
(bỏ envelope `*** Begin/End Patch` và streaming recovery).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from dino_coding.tools.hashline import messages
from dino_coding.tools.hashline.parser import parse_patch
from dino_coding.tools.hashline.text import BOM
from dino_coding.tools.hashline.tokenizer import parse_header
from dino_coding.tools.hashline.types import (
    EditCut, EditDelete, EditInsert, EditPaste, FileOp, Parsed,
)

# Noise kiểu apply_patch: `*** Update File:`, `*** Move to:`... ← port APPLY_PATCH_PATH_NOISE_RE
PATH_NOISE_RE = re.compile(
    r"(?i)^\*{0,3}\s*(?:(?:update|add|delete|move)[^A-Za-z0-9]*(?:file|to)?[^A-Za-z0-9]*:)?\s*\*{0,3}\s*"
)

# ← port input.rs RECOVERY_TAG_RE (static LazyLock<Regex> của omp)
RECOVERY_TAG_RE = re.compile(r"#([0-9A-Fa-f]{4})\s*$")


@dataclass
class PatchSection:
    """Một section = header (path + tag) + thân ops. ← port input::PatchSection"""
    path: str
    file_hash: Optional[str]
    diff: str
    _parsed: Optional[Parsed] = field(default=None, repr=False)
    _parse_error: Optional[str] = field(default=None, repr=False)

    def parse(self) -> Parsed:
        """Parse (memoized) thân section."""
        if self._parsed is None and self._parse_error is None:
            try:
                self._parsed = parse_patch(self.diff)
                if self._parsed.file_op and self._parsed.file_op.kind == "move":
                    self._parsed.file_op.dest = _normalize_path(
                        self._parsed.file_op.dest, cwd=None
                    )
            except ValueError as error:
                self._parse_error = str(error)
        if self._parse_error is not None:
            raise ValueError(self._parse_error)
        assert self._parsed is not None
        return self._parsed

    def edits(self):
        return self.parse().edits

    def file_op(self) -> Optional[FileOp]:
        return self.parse().file_op

    def has_anchor_scoped_edit(self) -> bool:
        """Có edit nào neo vào nội dung cụ thể không? ← port PatchSection::has_anchor_scoped_edit

        Không có (chỉ head/tail insert) → tag lệch vẫn cho phép apply (vì
        không có mỏ neo nào có thể sai).
        """
        for edit in self.edits():
            if isinstance(edit, (EditDelete, EditCut)):
                return True
            if isinstance(edit, EditPaste) and edit.at.range is not None:
                return True
            if isinstance(edit, EditInsert) and edit.cursor.anchor is not None:
                return True
        return False

    def collect_anchor_lines(self) -> list[int]:
        """Mọi dòng mỏ neo, tăng dần, không trùng. ← port PatchSection::collect_anchor_lines"""
        lines: list[int] = []
        for edit in self.edits():
            if isinstance(edit, EditDelete):
                lines.append(edit.anchor.line)
            elif isinstance(edit, EditCut):
                lines.extend(range(edit.range.start.line, edit.range.end.line + 1))
            elif isinstance(edit, EditPaste):
                if edit.at.range is not None:
                    lines.extend(range(edit.at.range.start.line, edit.at.range.end.line + 1))
                elif edit.at.cursor is not None and edit.at.cursor.anchor is not None:
                    lines.append(edit.at.cursor.anchor.line)
            elif isinstance(edit, EditInsert) and edit.cursor.anchor is not None:
                lines.append(edit.cursor.anchor.line)
        return sorted(set(lines))


@dataclass
class Patch:
    """Patch đa file đã tách section. ← port input::Patch"""
    sections: list[PatchSection]


def _unquote(path: str) -> str:
    if len(path) >= 2 and path[0] == path[-1] and path[0] in "\"'":
        return path[1:-1]
    return path


def _normalize_path(raw: str, cwd: Optional[str]) -> str:
    """Bỏ quote, bỏ noise apply_patch. ← port input::normalize_hashline_path (rút gọn)"""
    cleaned = PATH_NOISE_RE.sub("", _unquote(raw.strip())).strip()
    return cleaned


def _parse_header_line(line: str) -> Optional[PatchSection]:
    stripped = line.strip()
    if not stripped.startswith("["):
        return None
    header = parse_header(stripped)
    if header is not None:
        path, tag = header
        if not path:
            raise ValueError('Input header "[]" is empty; provide a file path.')
        return PatchSection(path=_normalize_path(path, None), file_hash=tag, diff="")
    # Phục hồi nhẹ: `[src/a.py #ABCD]` (space trước #) hoặc path có noise
    if stripped.startswith("[") and stripped.endswith("]"):
        body = PATH_NOISE_RE.sub("", stripped[1:-1].strip()).strip()
        tag_match = RECOVERY_TAG_RE.search(body)
        if tag_match:
            path_text = body[: tag_match.start()].strip()
            if path_text and "#" not in path_text:
                return PatchSection(
                    path=_normalize_path(path_text, None),
                    file_hash=tag_match.group(1).upper(),
                    diff="",
                )
    return None  # dòng `[...]` không parse được sẽ bị từ chối ở split


def split_patch(input_text: str) -> Patch:
    """Tách sections. ← port input::Patch::parse + split_raw_sections"""
    text = input_text.lstrip(BOM).rstrip("\n")
    lines = [ln.rstrip("\r") for ln in text.split("\n")]
    while lines and (not lines[0].strip() or lines[0].strip() == "*** Begin Patch"):
        lines.pop(0)
    if not lines:
        raise ValueError(messages.invalid_header_message(""))

    first = _parse_header_line(lines[0])
    if first is None:
        preview = lines[0][:120]
        raise ValueError(messages.invalid_header_message(preview))

    sections: list[PatchSection] = []
    current: Optional[PatchSection] = None
    body: list[str] = []
    aborted = False

    for line in lines:
        if line.strip() in ("*** End Patch", "*** Abort"):
            aborted = True
            break
        if line.strip() == "*** Begin Patch":
            continue
        if line.lstrip().startswith("["):
            header = _parse_header_line(line)
            if header is not None:
                _flush(sections, current, body)
                current = header
                continue
        body.append(line)
    if not aborted:
        _flush(sections, current, body)

    if not sections:
        raise ValueError("No hashline sections found in input.")

    _merge_same_path(sections)
    return Patch(sections=sections)


def _flush(sections: list[PatchSection], current: Optional[PatchSection], body: list[str]) -> None:
    if current is None:
        body.clear()
        return
    if any(line.strip() for line in body):
        current.diff = "\n".join(body)
        sections.append(current)
    body.clear()


def _merge_same_path(sections: list[PatchSection]) -> None:
    """Gộp section cùng path; tag xung đột → lỗi. ← port input::merge_same_path_sections"""
    positions: dict[str, int] = {}
    result: list[PatchSection] = []
    for section in sections:
        if section.path in positions:
            existing = result[positions[section.path]]
            if existing.file_hash and section.file_hash and existing.file_hash != section.file_hash:
                raise ValueError(
                    messages.conflicting_tags_message(
                        section.path, existing.file_hash, section.file_hash
                    )
                )
            if existing.file_hash is None:
                existing.file_hash = section.file_hash
            existing.diff = existing.diff + "\n" + section.diff
            continue
        positions[section.path] = len(result)
        result.append(section)
    sections[:] = result
