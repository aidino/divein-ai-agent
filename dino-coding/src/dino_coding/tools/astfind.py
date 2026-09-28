"""Engine tìm kiếm cấu trúc — port crates/pi-natives/src/ast.rs::ast_grep.

Điều chỉnh so với Rust (đã kiểm chứng trên ast-grep-py 0.45.3):
* Pattern rác không raise từ binding → tự validate (pattern_is_valid).
* BinaryHeap retain (skip+limit+1) → collect + sort + slice: cùng ngữ nghĩa.
* Pos.index là CODEPOINT (Rust là byte) → mọi slice chuỗi an toàn theo str.
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from ast_grep_py import SgRoot

from dino_coding.tools.astlang import is_supported_file, resolve_language

DEFAULT_FIND_LIMIT = 50  # ← ast.rs DEFAULT_FIND_LIMIT = ast-grep.ts DEFAULT_AST_LIMIT

# Thư mục bỏ qua khi walk. ← thay ignore-walk (gitignore) của Rust; defer §7
SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", "dist", "build",
    ".tox", ".eggs", ".idea", ".vscode",
}

# $$$NAME | $$NAME (bất hợp lệ, bắt để thay) | $NAME | $$$ | $_ | $
_METAVAR_TOKEN_RE = re.compile(
    r"\$\$\$[A-Z_][A-Z0-9_]*|\$\$[A-Z_][A-Z0-9_]*|\$[A-Z_][A-Z0-9_]*|\$\$\$|\$_|\$"
)


@dataclass
class AstMatch:
    """Một match có tọa độ 1-based. ← port ast.rs::AstFindMatch"""
    path: str              # display path posix tương đối workspace
    text: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    char_start: int        # codepoint offset (Rust: byte — binding đã chuẩn hóa)
    char_end: int
    meta: dict[str, str] = field(default_factory=dict)


@dataclass
class FindResult:
    """Thống kê một lượt tìm. ← port ast.rs::AstFindResult"""
    matches: list[AstMatch] = field(default_factory=list)
    total_matches: int = 0
    files_with_matches: int = 0
    files_searched: int = 0
    limit_reached: bool = False
    parse_errors: list[str] = field(default_factory=list)


def pattern_variables(pattern: str) -> list[str]:
    """Tên metavariable có tên, theo thứ tự xuất hiện, không trùng."""
    names: list[str] = []
    for token in _METAVAR_TOKEN_RE.findall(pattern):
        name = token.lstrip("$")
        if name and name != "_" and name not in names:
            names.append(name)
    return names


def pattern_is_valid(pattern: str, lang: str) -> bool:
    """Heuristic phát hiện pattern không parse được. ← bù lỗ hổng binding §3.3.

    Binding nuốt lỗi compile: pattern rác chỉ làm find_all trả []. Ở đây thay
    mọi metavar token bằng định danh trung tính `_MV` rồi dò node ERROR trong
    cây parse của chính pattern. Khảo sát 4/4: 'print($$$A)' và 'f($A, $B)'
    hợp lệ; 'def def def(' và 'class $_ {' rác với ngôn ngữ python.
    """
    prepared = _METAVAR_TOKEN_RE.sub("_MV", pattern)
    try:
        root = SgRoot(prepared, lang).root()
    except Exception:
        return False
    return not _tree_has_error(root)


def _tree_has_error(root) -> bool:
    """Cây có node ERROR nào không. ← thay node.has_error() (binding không có)."""
    stack = [root]
    while stack:
        node = stack.pop()
        if node.kind() == "ERROR":
            return True
        stack.extend(node.children())
    return False


def collect_files(root_abs: str, glob: Optional[str] = None) -> list[str]:
    """Danh sách file ứng viên (path posix tương đối root_abs, đã sort).

    File đơn → chính nó; thư mục → os.walk bỏ SKIP_DIRS + thư mục ẩn.
    ← port collect_candidates (phần walk; giữ nguyên ngữ nghĩa glob)
    """
    if os.path.isfile(root_abs):
        return [os.path.basename(root_abs)]
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root_abs):
        dirnames[:] = sorted(
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        )
        for name in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, name), root_abs)
            rel = rel.replace(os.sep, "/")
            if glob is None or fnmatch.fnmatch(rel, glob):
                found.append(rel)
    return found


def _match_sort_key(match: AstMatch) -> tuple:
    """Thứ tự hiển thị ổn định. ← port ast.rs::AstFindOrderKey"""
    return (
        match.path, match.start_line, match.start_column,
        match.end_line, match.end_column, match.char_start, match.char_end,
    )


def _meta_for(node, names: list[str]) -> dict[str, str]:
    """NAME → text. Single: text node; multi: join ', '. ← port meta_var.rs HashMap::from"""
    meta: dict[str, str] = {}
    for name in names:
        single = node.get_match(name)
        if single is not None:
            meta[name] = single.text()
            continue
        multi = node.get_multiple_matches(name)
        if multi:
            meta[name] = ", ".join(n.text() for n in multi)
    return meta


def find_matches(
    pattern: str,
    root_abs: str,
    glob: Optional[str] = None,
    lang: Optional[str] = None,
    skip: int = 0,
    limit: int = DEFAULT_FIND_LIMIT,
) -> FindResult:
    """Quét một scope bằng một pattern. ← port ast_grep (single-target).

    Vòng trong theo đúng ast.rs:684-777: file lỗi ngôn ngữ/đọc → parse_errors
    rồi tiếp tục file khác; cây có ERROR node → ghi parse error nhưng VẪN tìm
    (ast.rs:728 không continue — khớp error-recovery của tree-sitter).
    """
    result = FindResult()
    validated: dict[str, bool] = {}  # lang → pattern đã kiểm chưa
    names = pattern_variables(pattern)
    all_matches: list[AstMatch] = []
    is_single_file = os.path.isfile(root_abs)

    for rel in collect_files(root_abs, glob):
        if not is_supported_file(rel, lang):
            continue
        file_lang = resolve_language(lang, rel)
        if file_lang is None:
            continue
        result.files_searched += 1

        if file_lang not in validated:
            validated[file_lang] = pattern_is_valid(pattern, file_lang)
        if not validated[file_lang]:
            result.parse_errors.append(
                f"{pattern}: {rel}: Invalid pattern for {file_lang}"
            )
            continue

        absolute = root_abs if is_single_file else os.path.join(root_abs, rel)
        try:
            with open(absolute, "r", encoding="utf-8") as handle:
                source = handle.read()
        except (OSError, UnicodeDecodeError) as error:
            result.parse_errors.append(f"{pattern}: {rel}: {error}")
            continue

        root = SgRoot(source, file_lang).root()
        if _tree_has_error(root):
            result.parse_errors.append(
                f"{rel}: parse error (syntax tree contains error nodes)"
            )

        file_had_match = False
        for node in root.find_all(pattern=pattern):
            result.total_matches += 1
            if not file_had_match:
                result.files_with_matches += 1
                file_had_match = True
            rng = node.range()
            all_matches.append(AstMatch(
                path=rel,
                text=node.text(),
                start_line=rng.start.line + 1,
                start_column=rng.start.column + 1,
                end_line=rng.end.line + 1,
                end_column=rng.end.column + 1,
                char_start=rng.start.index,
                char_end=rng.end.index,
                meta=_meta_for(node, names),
            ))

    all_matches.sort(key=_match_sort_key)
    visible = all_matches[skip:]
    result.matches = visible[:limit]
    result.limit_reached = len(all_matches) > skip + limit  # ← page_retained_matches
    return result
