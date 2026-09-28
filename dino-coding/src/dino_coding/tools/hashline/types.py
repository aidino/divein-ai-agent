"""Kiểu dữ liệu thuần dùng chung bởi tokenizer/parser/apply/patcher.

Port của crates/pi-edit/src/modes/hashline/types.rs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass(frozen=True)
class Anchor:
    """Mỏ neo dòng 1-indexed. ← port types::Anchor"""
    line: int


@dataclass(frozen=True)
class Cursor:
    """Vị trí chèn tương đối nội dung hiện có. ← port types::Cursor

    kind: "bof" | "eof" | "before" | "after"; anchor chỉ dùng cho before/after.
    """
    kind: str
    anchor: Optional[Anchor] = None


@dataclass(frozen=True)
class ParsedRange:
    """Khoảng dòng đóng [start, end] 1-indexed. ← port types::ParsedRange"""
    start: Anchor
    end: Anchor


@dataclass(frozen=True)
class PasteTarget:
    """Điểm hạ của paste: một gap (cursor) hoặc một span bị thay thế. ← port types::PasteTarget"""
    cursor: Optional[Cursor] = None
    range: Optional[ParsedRange] = None


# Block op bị hoãn (cần tree-sitter) — xem BLOCK_RESOLVER_UNAVAILABLE trong messages.py
BlockMode = str  # "insert_after" | "cut" | "paste_after" | "" (thay thế block)


@dataclass
class EditInsert:
    """Một dòng chèn vào cursor. ← port types::Edit::Insert

    replacement=True khi dòng đến từ body của `PUT N.=M:` (chèn trước dòng đầu
    range, kèm Delete các dòng cũ) — phân biệt với chèn thuần `PUT <N:`.
    line_num/index: vị trí trong patch (để cảnh báo chẩn đoán).
    """
    cursor: Cursor
    text: str
    line_num: int
    index: int
    replacement: bool = False


@dataclass
class EditDelete:
    """Xóa đúng một dòng theo mỏ neo. ← port types::Edit::Delete"""
    anchor: Anchor
    line_num: int
    index: int


@dataclass
class EditCut:
    """CUT range (tùy chọn @register) — hạ mức thành các EditDelete. ← port types::Edit::Cut"""
    range: ParsedRange
    register: Optional[str]
    line_num: int
    index: int


@dataclass
class EditPaste:
    """Paste register vào gap hoặc đè lên span. ← port types::Edit::Paste"""
    at: PasteTarget
    register: Optional[str]
    line_num: int
    index: int


@dataclass
class EditBlock:
    """Op khối hoãn giải (`PUT N*:`...) — engine này luôn từ chối. ← port types::Edit::Block"""
    anchor: Anchor
    payloads: list[str]
    mode: Optional[BlockMode]
    register: Optional[str]
    line_num: int
    index: int


Edit = Union[EditInsert, EditDelete, EditCut, EditPaste, EditBlock]


@dataclass
class FileOp:
    """Op toàn file từ thân section. ← port types::FileOp (Rem | Move)"""
    kind: str  # "rem" | "move"
    dest: Optional[str] = None


@dataclass
class Parsed:
    """Kết quả parse một thân section. ← port input::Parsed"""
    edits: list[Edit] = field(default_factory=list)
    file_op: Optional[FileOp] = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class ApplyResult:
    """Kết quả áp edits lên text. ← port types::ApplyResult"""
    text: str = ""
    first_changed_line: Optional[int] = None
    warnings: list[str] = field(default_factory=list)
