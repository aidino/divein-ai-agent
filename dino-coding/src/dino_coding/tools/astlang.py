"""Bản đồ ngôn ngữ cho ast-grep — port rút gọn pi-ast/src/language/mod.rs
(extensions + aliases) và ops.rs::resolve_language / is_supported_file.

ast-grep-py bundle sẵn parser; module này trả lời hai câu hỏi:
file này dùng ngôn ngữ gì, và có đáng quét không.
"""

from __future__ import annotations

import os
from typing import Optional

# ext → ngôn ngữ. ← port language/mod.rs::from_extension (subset 25 ngôn ngữ)
EXTENSION_LANGS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".html": "html", ".htm": "html",
    ".css": "css",
    ".json": "json",
    ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".kt": "kotlin", ".kts": "kotlin",
    ".swift": "swift",
    ".php": "php",
    ".lua": "lua",
    ".scala": "scala",
    ".sh": "bash", ".bash": "bash",
    ".sql": "sql",
}

# alias → ngôn ngữ (canonical name là alias của chính nó). ← port LANG_ALIASES
_CANONICAL = ("python", "javascript", "typescript", "tsx", "rust", "go",
              "java", "c", "cpp", "csharp", "ruby", "html", "css", "json",
              "yaml", "toml", "markdown", "kotlin", "swift", "php", "lua",
              "scala", "bash", "sql")
LANG_ALIASES: dict[str, str] = {name: name for name in _CANONICAL} | {
    "py": "python", "python3": "python",
    "js": "javascript", "node": "javascript",
    "rs": "rust",
    "golang": "go",
    "c++": "cpp", "cxx": "cpp",
    "c#": "csharp",
    "rb": "ruby",
    "yml": "yaml",
    "md": "markdown",
    "kt": "kotlin",
    "sh": "bash", "shell": "bash",
}


def resolve_lang_alias(name: str) -> Optional[str]:
    """Alias → tên ngôn ngữ core, None nếu không biết. ← port resolve_supported_lang"""
    return LANG_ALIASES.get(name.strip().lower())


def lang_from_path(path: str) -> Optional[str]:
    """Suy ngôn ngữ từ đuôi file. ← port language::from_extension"""
    _, ext = os.path.splitext(path.lower())
    return EXTENSION_LANGS.get(ext)


def resolve_language(lang: Optional[str], path: str) -> Optional[str]:
    """Lang override thắng path-inference. ← port ops.rs::resolve_language.

    Chuỗi rỗng/toàn khoảng trắng coi như không ghi (ast.rs:666 trim + filter).
    """
    if lang and lang.strip():
        return resolve_lang_alias(lang)
    return lang_from_path(path)


def is_supported_file(path: str, explicit_lang: Optional[str]) -> bool:
    """Có explicit lang → mọi file là ứng viên (người gọi đã chọn). ← port ops.rs:417"""
    if explicit_lang and explicit_lang.strip():
        return True
    return lang_from_path(path) is not None
