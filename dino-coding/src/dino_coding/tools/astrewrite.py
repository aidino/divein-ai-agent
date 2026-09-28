"""Engine tái cấu trúc — port ast.rs::ast_edit_blocking + ops.rs::apply_edits,
kèm expand_template tự viết theo core/replacer.rs (binding không thay metavar).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from ast_grep_py import SgRoot

from dino_coding.tools.astfind import _tree_has_error, collect_files, pattern_is_valid
from dino_coding.tools.astlang import is_supported_file, resolve_language

# Biến có tên trong template kết quả. $$$NAME | $NAME — anonymous ($, $_, $$$)
# KHÔNG match → giữ nguyên là chữ thường (đúng replacer.rs::split_first_meta_var
# trả None cho biến không tên).
_TEMPLATE_VAR_RE = re.compile(r"\$\$\$[A-Z_][A-Z0-9_]*|\$[A-Z_][A-Z0-9_]*")


class RewriteConflict(ValueError):
    """Hai edit đè lên cùng một vùng chữ. ← port ops.rs overlap error."""


@dataclass
class RewriteChange:
    """Một thay đổi sắp xảy ra trên file. ← port ast.rs::AstReplaceChange"""
    path: str
    before: str
    after: str
    start_line: int
    start_column: int
    char_start: int
    char_end: int


@dataclass
class RewriteResult:
    """Kết quả một lượt rewrite (có thể dry-run). ← port ast.rs::AstReplaceResult"""
    changes: list[RewriteChange] = field(default_factory=list)
    file_counts: dict[str, int] = field(default_factory=dict)
    total_replacements: int = 0
    files_touched: int = 0
    files_searched: int = 0
    applied: bool = False
    limit_reached: bool = False
    parse_errors: list[str] = field(default_factory=list)


def expand_template(template: str, node, source: str) -> str:
    """Thay metavar trong template. ← port replacer.rs::maybe_get_var.

    Thứ tự tra: single trước (get_match), multi sau (get_multiple_matches) —
    vì một tên chỉ được bắt ở đúng một trong hai dạng.
    """
    parts: list[str] = []
    pos = 0
    for hit in _TEMPLATE_VAR_RE.finditer(template):
        parts.append(template[pos : hit.start()])
        name = hit.group(0).lstrip("$")
        single = node.get_match(name)
        if single is not None:
            parts.append(single.text())
        else:
            multi = node.get_multiple_matches(name)
            if multi:
                first, last = multi[0], multi[-1]
                parts.append(source[first.range().start.index : last.range().end.index])
        # cả hai đều rỗng → biến chưa từng được bắt: bỏ trống (core omit bytes)
        pos = hit.end()
    parts.append(template[pos:])
    return "".join(parts)


def apply_edits(source: str, edits: list[tuple[int, int, str]]) -> str:
    """Áp danh sách (char_pos, deleted_len, inserted) lên source.

    ← port ops.rs::apply_edits: sort → dedupe identical → overlap check →
    áp từ cuối lên. Edit trùng byte-identical giữa hai rule là MỘT edit
    deterministic; chỉ overlap *khác nhau* mới là mâu thuẫn.
    """
    ordered = sorted(edits, key=lambda e: (e[0], e[1], e[2]))
    unique: list[tuple[int, int, str]] = []
    for edit in ordered:
        if not unique or unique[-1] != edit:
            unique.append(edit)
    prev_end = 0
    for position, deleted_length, _ in unique:
        if position < prev_end:
            raise RewriteConflict(
                "Overlapping replacements detected; refine pattern to avoid ambiguous edits"
            )
        prev_end = position + deleted_length
    output = source
    for position, deleted_length, inserted in reversed(unique):
        output = output[:position] + inserted + output[position + deleted_length :]
    return output


def rewrite_text(
    source: str,
    lang: str,
    rules: list[tuple[str, str]],
    max_replacements: Optional[int] = None,
) -> tuple[list[RewriteChange], str]:
    """Chạy mọi rule trên MỘT parse của source. ← port ast_edit_blocking:1107-1154.

    Trả (changes, new_source). Ném RewriteConflict nếu hai rule đè vùng chữ
    khác nhau — caller quyết định bỏ cả lượt (đúng ngữ nghĩa atomic của omp).
    """
    root = SgRoot(source, lang).root()
    staged: list[tuple[int, int, str]] = []
    changes: list[RewriteChange] = []

    for pattern, template in rules:
        if not pattern_is_valid(pattern, lang):
            continue  # đã được báo ở parse_errors của rewrite_target
        for node in root.find_all(pattern=pattern):
            rng = node.range()
            position = rng.start.index
            deleted_length = rng.end.index - rng.start.index
            inserted = expand_template(template, node, source)
            edit = (position, deleted_length, inserted)
            # Hai rule cho cùng node cùng kết quả = một edit. ← ast.rs:1116
            if any(
                e[0] == edit[0] and e[1] == edit[1] and e[2] == edit[2]
                for e in staged
            ):
                continue
            if max_replacements is not None and len(staged) >= max_replacements:
                raise RewriteConflict("max_replacements exceeded")  # không dùng — xem ghi chú
            staged.append(edit)
            changes.append(RewriteChange(
                path="",
                before=node.text(),
                after=inserted,
                start_line=rng.start.line + 1,
                start_column=rng.start.column + 1,
                char_start=rng.start.index,
                char_end=rng.end.index,
            ))

    return changes, apply_edits(source, staged)


def rewrite_target(
    rules: list[tuple[str, str]],
    root_abs: str,
    lang: Optional[str] = None,
    glob: Optional[str] = None,
    apply: bool = False,
    max_files: int = 1000,  # ← ast-edit.ts $envpos("PI_MAX_AST_FILES", 1000)
    max_replacements: Optional[int] = None,
    writer=None,  # callable(absolute_path, new_text) — test chèn vào đây; mặc định ghi đĩa
) -> RewriteResult:
    """Rewrite cả scope (file hoặc thư mục). ← port ast_edit_blocking toàn phần.

    staged writes: mọi file được tính xong TRƯỚC khi file đầu tiên được ghi
    (ast.rs:1050 'Stage writes in memory … flush only after the whole pass
    succeeds'). Apply bị lỗi giữa chừng → không file nào đổi.
    """
    result = RewriteResult(applied=apply)
    validated: dict[str, bool] = {}
    pending_writes: list[tuple[str, str]] = []
    is_single_file = os.path.isfile(root_abs)

    def _write(path: str, text: str) -> None:
        if writer is not None:
            writer(path, text)
        else:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)

    for rel in collect_files(root_abs, glob):
        if not is_supported_file(rel, lang):
            continue
        file_lang = resolve_language(lang, rel)
        if file_lang is None:
            continue
        result.files_searched += 1

        if file_lang not in validated:
            validated[file_lang] = all(
                pattern_is_valid(pat, file_lang) for pat, _ in rules
            )
        if not validated[file_lang]:
            result.parse_errors.append(
                f"{rel}: Invalid pattern for {file_lang}"
            )
            continue

        absolute = root_abs if is_single_file else os.path.join(root_abs, rel)
        try:
            with open(absolute, "r", encoding="utf-8") as handle:
                source = handle.read()
        except (OSError, UnicodeDecodeError) as error:
            result.parse_errors.append(f"{rel}: {error}")
            continue

        parse_root = SgRoot(source, file_lang).root()
        if _tree_has_error(parse_root):
            result.parse_errors.append(
                f"{rel}: parse error (syntax tree contains error nodes)"
            )
            continue

        changes, new_source = rewrite_text(source, file_lang, rules, max_replacements)
        if not changes:
            continue
        if result.files_touched >= max_files:
            result.limit_reached = True
            break

        result.files_touched += 1
        result.file_counts[rel] = len(changes)
        for change in changes:
            change.path = rel
        result.changes.extend(changes)
        if apply and new_source != source:
            pending_writes.append((absolute, new_source))

    result.total_replacements = len(result.changes)
    if apply:
        for absolute, new_source in pending_writes:  # flush sau khi pass sạch lỗi
            _write(absolute, new_source)
    return result
