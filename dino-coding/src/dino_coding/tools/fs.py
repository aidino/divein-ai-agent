"""Smart Read & Write tools — mặt tiền hashline của Agent.

Định dạng read output (hợp đồng với edit engine):
    [relative/path.py#A1B2]
    1:...
    2:...
    [Showing lines 1-40 of 120. Use offset=41 to continue]

← port tinh thần packages/coding-agent/src/tools/read.ts + read-summary.ts
   (schema điều chỉnh: offset/limit là JSON args thay vì selector inline)
"""

from __future__ import annotations

import os
import re
from typing import Optional

from langchain_core.tools import tool
from rich.console import Console
from rich.markup import escape

from dino_coding.tools.hashline.text import normalize_to_lf, seen_lines_from_body, strip_bom
from dino_coding.tools.workspace import get_store, get_workspace

console = Console()

DEFAULT_LIMIT = 300        # ← read.defaultLimit của omp
MAX_LINES = 3000           # DEFAULT_MAX_LINES
SUMMARY_MIN_LINES = 100    # ← cfgReadSummarizeMinTotalLines (default 100)

# Heuristic outline thay tree-sitter summarizeCode — mỗi ngôn ngữ một bộ regex "xương"
OUTLINE_RULES: dict[str, list[re.Pattern[str]]] = {
    ".py": [
        re.compile(r"^\s*(?:async\s+)?def\s+\w+"),
        re.compile(r"^\s*class\s+\w+"),
        re.compile(r"^\s*@\w+"),                      # decorator
        re.compile(r"^\s*(?:from\s+[\w.]+\s+)?import\s+"),
    ],
    ".js": [
        re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+\w+"),
        re.compile(r"^\s*(?:export\s+)?class\s+\w+"),
        re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?(?:\(|function)"),
    ],
    ".ts": [
        re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+\w+"),
        re.compile(r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+\w+"),
        re.compile(r"^\s*(?:export\s+)?(?:interface|type|enum)\s+\w+"),
        re.compile(r"^\s*(?:export\s+)?(?:const|let)\s+\w+\s*=\s*(?:async\s*)?(?:\(|function)"),
    ],
    ".md": [re.compile(r"^#{1,6}\s")],
    ".rs": [
        re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+\w+"),
        re.compile(r"^\s*(?:pub\s+)?(?:struct|enum|trait|impl|mod)\s*\w*"),
    ],
}
OUTLINE_RULES[".tsx"] = OUTLINE_RULES[".ts"]
OUTLINE_RULES[".jsx"] = OUTLINE_RULES[".js"]


def _outline_rules(path: str) -> list[re.Pattern[str]] | None:
    _, ext = os.path.splitext(path.lower())
    return OUTLINE_RULES.get(ext)


def _build_summary(lines: list[str], rules: list[re.Pattern[str]]) -> tuple[str, int]:
    """Gấp file lớn thành outline. Trả về (text, số dòng bị gấp).

    Dòng giữ nguyên đánh số `N:TEXT`; vùng gấp chỉ một dòng `…` (KHÔNG đánh số —
    những dòng đó là unseen với seen-lines guard).
    """
    keep = [bool(any(rule.match(line) for rule in rules)) for line in lines]
    rows: list[str] = []
    elided = 0
    run_start: int | None = None

    def close_run(end: int) -> None:
        nonlocal run_start, elided
        if run_start is not None:
            elided += end - run_start
            rows.append("…")
            run_start = None

    for index, line in enumerate(lines, start=1):
        if keep[index - 1]:
            close_run(index - 1)
            rows.append(f"{index}:{line}")
        else:
            if run_start is None:
                run_start = index
    close_run(len(lines))
    return "\n".join(rows), elided



@tool
def read(path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> str:
    """Read a file with a snapshot tag and stable line numbers.

    Output starts with `[path#TAG]` — copy it verbatim as the `edit` section
    header. Every displayed line is `N:TEXT` where N is the anchor `edit` uses.
    Pass explicit offset/limit to page through large files; a whole-file read of
    a large file may return a folded outline (elided lines are NOT anchors:
    re-read the exact range before editing it).
    """
    workspace = get_workspace()
    store = get_store()
    try:
        absolute = workspace.resolve(path)
    except ValueError as error:
        return f"Error: {error}"
    display = workspace.display(absolute)

    try:
        with open(absolute, "r", encoding="utf-8", newline="") as handle:
            raw = handle.read()
    except FileNotFoundError:
        return f"Error: File not found: {display}. Use the write tool to create new files."
    except UnicodeDecodeError:
        return f"Error: Cannot decode {display} as UTF-8 text."

    text = normalize_to_lf(strip_bom(raw))
    lines = text.split("\n")
    # Bỏ sentinel trống cuối nếu file kết thúc bằng newline (không phải dòng thật)
    trailing_newline = len(lines) > 1 and lines[-1] == ""
    if trailing_newline:
        lines = lines[:-1]
    total = len(lines)

    rules = _outline_rules(display)
    summarize = (
        offset is None and limit is None
        and rules is not None
        and total >= SUMMARY_MIN_LINES
    )

    if summarize:
        assert rules is not None
        body, elided = _build_summary(lines, rules)
        shown = body.split("\n")
        shown += [
            "",
            f"[…{elided}ln elided; re-read needed ranges with explicit offset/limit, "
            f"e.g. path={display} offset=<start> limit=<span>]",
        ]
    else:
        start = max(1, offset or 1)
        count = min(limit or DEFAULT_LIMIT, MAX_LINES)
        page = lines[start - 1 : start - 1 + count]
        shown = [f"{start + i}:{line}" for i, line in enumerate(page)]
        shown_end = start + len(page) - 1
        if shown_end < total:
            shown.append(
                f"[Showing lines {start}-{shown_end} of {total}. "
                f"Use offset={shown_end + 1} to continue]"
            )
        elided = 0

    tag = store.record(workspace.canonical_key(absolute), text)
    store.record_seen_lines(workspace.canonical_key(absolute), tag, seen_lines_from_body("\n".join(shown)))
    header = f"[{display}#{tag}]"
    # escape() bắt rich hiểu `[path#TAG]` là markup tag — không thì header biến mất trên CLI
    console.print(f"[dim]read → {escape(header)} ({total} lines)[/dim]")
    return "\n".join([header, *shown])


@tool
def write(path: str, content: str) -> str:
    """Create or overwrite a file with full content.

    For editing existing files prefer `edit` (anchored, refuses stale writes).
    Use `write` for new files or full rewrites. Returns the `[path#TAG]` header
    that `edit` accepts afterwards.
    """
    workspace = get_workspace()
    store = get_store()
    try:
        absolute = workspace.resolve(path)
    except ValueError as error:
        return f"Error: {error}"
    display = workspace.display(absolute)

    existed = os.path.isfile(absolute)
    os.makedirs(os.path.dirname(absolute) or ".", exist_ok=True)
    normalized = normalize_to_lf(content)
    if not normalized.endswith("\n"):
        normalized += "\n"
    with open(absolute, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(normalized)

    tag = store.record(workspace.canonical_key(absolute), normalized)
    store.reset_noop(workspace.canonical_key(absolute))
    header = f"[{display}#{tag}]"
    verb = "Overwrote" if existed else "Created"
    lines = normalized.split("\n")
    return f"{verb} {display} ({max(0, len(lines) - 1)} lines). Snapshot header for edits:\n{header}"


file_tools = [read, write]
