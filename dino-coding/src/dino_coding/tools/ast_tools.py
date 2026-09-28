"""Tool ast_grep + ast_edit — port packages/coding-agent/src/tools/ast-grep.ts
và ast-edit.ts (phần execute, bỏ internal-URL filesystem + delegation bias).

Điều chỉnh lớn nhất: omp finalize codemod bằng write tới thiết bị xd://resolve;
dino-coding chưa có lớp dispatch đó → hợp đồng 2 pha tường minh: gọi đầu
preview (apply=False, mặc định), gọi lại apply=True để ghi.
"""

from __future__ import annotations

import os
import posixpath
from typing import Optional

from langchain_core.tools import tool
from rich.console import Console
from rich.markup import escape

from dino_coding.tools.astfind import DEFAULT_FIND_LIMIT, find_matches
from dino_coding.tools.astrewrite import RewriteConflict, rewrite_target
from dino_coding.tools.hashline.text import (
    file_hash, normalize_to_lf, seen_lines_from_body, strip_bom,
)
from dino_coding.tools.workspace import get_store, get_workspace

console = Console()

MAX_AST_FILES = 1000   # ← ast-edit.ts $envpos("PI_MAX_AST_FILES", 1000)
PARSE_ERROR_CAP = 3    # ← capParseErrors: in 3 lỗi đầu, đếm phần còn lại
_LAST_PREVIEW: dict[tuple, tuple[dict[str, int], int, dict[str, str]]] = {}
# Preview gần nhất theo (rules, paths): (counts, tổng thay đổi, {rel → content tag}).
# Pha apply so với CHÍNH preview mà model đã xem — thay closure queueResolveHandler
# của omp (resolve.ts). Chiều thứ 3 (content tag) bắt file đổi ngoài vùng match.

AST_GREP_DESCRIPTION = """Structural code search via ast-grep. Use when syntax shape matters more than text (calls, declarations, language constructs).

- `pat` is ONE AST pattern per call; separate calls for unrelated patterns.
- Set `lang` when extension inference is ambiguous (for example `cpp` for `.h`).
- `$NAME` captures one node; `$_` matches without binding; `$$$NAME` zero-or-more; `$$$` zero-or-more unbound.
  - Use `$$$NAME`, NOT `$$NAME` (invalid). Names UPPERCASE, whole node — `prefix$VAR` fails.
- Same metavariable twice MUST match identical code (`$A == $A` matches `x == x`, not `x == y`).
- Patterns MUST parse as a single AST node. Non-standalone fragments: wrap them, e.g. `class $_ { ... }`.
- Declaration forms are distinct — `function foo`, method `foo()`, `const foo = () => {}`; search the right form before concluding absence.
- Loosest existence check: `pat: "executeBash"` with a narrow `path`.
- Match rows render as `N:TEXT` under a `[path#TAG]` header — those lines are valid edit anchors; copy the header into your next edit.
- Parse issues mean the query may be mis-scoped: fix the pattern or narrow `path` BEFORE concluding "no matches"."""

AST_EDIT_DESCRIPTION = """Structural AST-aware rewrites via ast-grep. Use for codemods where text replace is unsafe. Mixed-language paths are fine: each file is parsed in its own language, and a pattern only rewrites files it parses in.

- Metavariables in `pat` (`$A`, `$$$ARGS`) substitute into `out`.
- Patterns match AST structure, not text. `$NAME` = one node; `$_` = unbound; `$$$NAME` = zero-or-more.
  - Use `$$$NAME`, NOT `$$NAME` (invalid). Names UPPERCASE, whole node — partial like `prefix$VAR` fails.
- Same metavariable twice MUST match identical code.
- Rewrite patterns MUST parse as a single AST node; wrap non-standalone fragments.
- 1:1 substitution — no splitting or merging captures. Delete with empty `out`.
- Calls run as a DRY-RUN first: the diff comes back staged, files NOT modified. Re-issue the same call with `apply=true` to write, or adjust `ops`/`paths`.
- After `apply=true`, fresh `[path#TAG]` headers are returned for follow-up line edits.
- Parse issues mean a malformed rewrite, not a clean no-op. For one-off text edits, prefer the edit tool."""


def _parse_error_lines(errors: list[str]) -> list[str]:
    """In tối đa 3 lỗi + dòng đếm. ← port capParseErrors/formatParseErrors"""
    shown = errors[:PARSE_ERROR_CAP]
    lines = [f"Parse issue: {error}" for error in shown]
    if len(errors) > PARSE_ERROR_CAP:
        lines.append(f"(+{len(errors) - PARSE_ERROR_CAP} more parse issues)")
    return lines

def _ws_rel(target: str, rel: str, scope_is_file: bool) -> str:
    """Engine trả path tương đối SCOPE; omp hiển thị tương đối WORKSPACE
    (ast-grep.ts:301). Chuẩn hóa khi merge để mint tag mở đúng file với
    directory-target ở mọi chiều sâu — không chỉ file ngay dưới root."""
    norm = posixpath.normpath((target or ".").replace(os.sep, "/"))
    if norm in ("", "."):
        return rel
    return norm if scope_is_file else f"{norm}/{rel}"



def _read_normalized(absolute: str) -> Optional[str]:
    """Đọc file về dạng chuẩn snapshot (LF, không BOM). None nếu không đọc được."""
    try:
        with open(absolute, "r", encoding="utf-8", newline="") as handle:
            return normalize_to_lf(strip_bom(handle.read()))
    except (OSError, UnicodeDecodeError):
        return None


def _split_targets(path_param: str) -> list[str]:
    """`src;tests` → ['src', 'tests']; rỗng → ['.']. ← port toPathList"""
    parts = [p.strip() for p in path_param.split(";") if p.strip()]
    return parts or ["."]


@tool(description=AST_GREP_DESCRIPTION)
def ast_grep(
    pat: str,
    path: str = ".",
    lang: Optional[str] = None,
    skip: int = 0,
) -> str:
    """Structural code search via ast-grep."""
    workspace = get_workspace()
    store = get_store()

    pattern = pat.strip()
    if not pattern:
        return "Error: `pat` must be a non-empty pattern."
    try:
        skip = int(skip)
        assert skip >= 0
    except (ValueError, AssertionError):
        return "Error: `skip` must be a non-negative number."

    # Multi-target: chạy từng scope rồi merge-sort toàn cục. ← runMultiTargetAstGrep
    merged: list = []
    total = files_with = searched = 0
    limit_reached = False
    parse_errors: list[str] = []
    for target in _split_targets(path):
        try:
            absolute = workspace.resolve(target)
        except ValueError as error:
            return f"Error: {error}"
        result = find_matches(pattern, absolute, lang=lang, skip=0,
                              limit=skip + DEFAULT_FIND_LIMIT + 1)
        total += result.total_matches
        files_with += result.files_with_matches
        searched += result.files_searched
        limit_reached = limit_reached or result.limit_reached
        parse_errors.extend(result.parse_errors)
        for match in result.matches:
            match.path = _ws_rel(target, match.path, os.path.isfile(absolute))
        merged.extend(result.matches)

    merged.sort(key=lambda m: (m.path, m.start_line, m.start_column,
                               m.end_line, m.end_column))
    visible = merged[skip:]
    paged = visible[:DEFAULT_FIND_LIMIT]
    limit_reached = limit_reached or len(visible) > DEFAULT_FIND_LIMIT

    if not paged:
        message = "No matches found"
        if parse_errors:
            message = ("No matches found. Parse issues mean the query may be "
                       "mis-scoped; narrow `path` before concluding absence.")
            message += "\n" + "\n".join(_parse_error_lines(parse_errors))
        console.print(f"[dim]ast_grep → {escape(pattern)}: no matches[/dim]")
        return message

    # Render theo file, mint tag + seen-lines. ← ast-grep.ts:287-339
    by_file: dict[str, list] = {}
    for match in paged:
        by_file.setdefault(match.path, []).append(match)

    output: list[str] = []
    for rel in sorted(by_file):
        absolute = os.path.join(workspace.root, rel)
        text = _read_normalized(absolute)
        rows: list[str] = []
        if text is not None:
            tag = store.record(workspace.canonical_key(absolute), text)
            output.append(f"[{rel}#{tag}]")
            for match in by_file[rel]:
                for index, line in enumerate(match.text.split("\n")):
                    marker = "*" if index == 0 else " "
                    rows.append(f"{marker}{match.start_line + index}:{line}")
                if match.meta:
                    serialized = ", ".join(
                        f"{name}={value}" for name, value in sorted(match.meta.items())
                    )
                    rows.append(f"  meta: {serialized}")
            store.record_seen_lines(
                workspace.canonical_key(absolute), tag,
                seen_lines_from_body("\n".join(rows)),
            )
            output.extend(rows)
        else:
            output.append(f"[{rel}]")
            output.append("  (file unreadable)")

    if limit_reached:
        output.append("")
        output.append("Result limit reached; narrow `path` or page with `skip`.")
    if parse_errors:
        output.append("")
        output.extend(_parse_error_lines(parse_errors))

    console.print(f"[dim]ast_grep → {escape(pattern)}: {total} matches "
                  f"in {files_with} file(s)[/dim]")
    return "\n".join(output)


@tool(description=AST_EDIT_DESCRIPTION)
def ast_edit(ops: list[dict], paths: list[str], apply: bool = False) -> str:
    """Structural AST-aware rewrites via ast-grep."""
    workspace = get_workspace()
    store = get_store()

    if not ops:
        return "Error: `ops` must include at least one op entry."
    rules: list[tuple[str, str]] = []
    seen_patterns: set[str] = set()
    for index, entry in enumerate(ops):
        pat = (entry.get("pat") or "").strip()
        if not pat:
            return f"Error: `ops[{index}].pat` must be a non-empty pattern."
        if pat in seen_patterns:
            return f"Error: Duplicate rewrite pattern: {pat}"
        seen_patterns.add(pat)
        rules.append((pat, entry.get("out") or ""))
    if not paths:
        return "Error: `paths` must include at least one path."
    targets: list[tuple[str, str]] = []  # (display, absolute)
    for target in paths:
        try:
            targets.append((target, workspace.resolve(target)))
        except ValueError as error:
            return f"Error: {error}"

    def run(dry_run: bool):
        """Một pass qua mọi target. ← port runAstEditOnce/runAstEditTargets."""
        changes: list = []
        counts: dict[str, int] = {}
        searched = 0
        errors: list[str] = []
        limit_reached = False
        for display, absolute in targets:
            res = rewrite_target(rules, absolute, apply=not dry_run,
                                 max_files=MAX_AST_FILES)
            searched += res.files_searched
            limit_reached = limit_reached or res.limit_reached
            errors.extend(res.parse_errors)
            # path engine = tương đối scope → đổi về tương đối workspace
            # (mint tag phải mở đúng file với directory-target sâu).
            scope_is_file = os.path.isfile(absolute)
            for change in res.changes:
                change.path = _ws_rel(display, change.path, scope_is_file)
            changes.extend(res.changes)
            for path_, count in res.file_counts.items():
                key = _ws_rel(display, path_, scope_is_file)
                counts[key] = counts.get(key, 0) + count
        return changes, counts, searched, errors, limit_reached

    # ---- Pha 1: dry-run preview (LUÔN) ← ast-edit.ts:285-292 ----
    try:
        changes, counts, searched, parse_errors, limit_reached = run(dry_run=True)
    except RewriteConflict as conflict:
        return f"Error: {conflict}"
    if not changes:
        message = "No replacements made"
        if parse_errors:
            message += "\n" + "\n".join(_parse_error_lines(parse_errors))
        console.print("[dim]ast_edit → no replacements[/dim]")
        return message

    # ---- Render diff preview (tag mint từ nội dung TRƯỚC apply) ----
    by_file: dict[str, list] = {}
    for change in changes:
        by_file.setdefault(change.path, []).append(change)

    output: list[str] = []
    preview_tags: dict[str, str] = {}  # rel → content tag lúc render (stale check)
    for rel in sorted(by_file):
        absolute = os.path.join(workspace.root, rel)
        text = _read_normalized(absolute)
        if text is not None:
            tag = store.record(workspace.canonical_key(absolute), text)
            preview_tags[rel] = tag
            output.append(f"[{rel}#{tag}]")
        else:
            output.append(f"[{rel}]")
        for change in by_file[rel]:
            before = change.before.split("\n", 1)[0][:120]
            after = change.after.split("\n", 1)[0][:120]
            output.append(f"-{change.start_line}:{before}")
            output.append(f"+{change.start_line}:{after}")

    if limit_reached:
        output.append("")
        output.append("Limit reached; narrow paths.")
    if parse_errors:
        output.append("")
        output.extend(_parse_error_lines(parse_errors))

    if not apply:
        _LAST_PREVIEW[(tuple(rules), tuple(targets))] = (counts, len(changes), preview_tags)
        output.insert(0, "Staged as a proposal — files NOT modified yet. "
                         "Re-issue the same call with apply=true to apply these changes.")
        output.insert(1, "")
        console.print(f"[dim]ast_edit → staged {len(changes)} replacement(s) "
                      f"in {len(counts)} file(s)[/dim]")
        return "\n".join(output)

    # ---- Stale check GIỮA HAI LẦN GỌI: so với preview model đã xem ----
    # ← thay closure queueResolveHandler của omp: nếu file đổi sau preview,
    # từ chối ghi và bắt preview lại, thay vì áp một diff người ta chưa duyệt.
    # So TWO chiều: (a) số match, (b) content tag từng file — thay đổi ngoài
    # vùng match (comment appends, formatter...) cũng bị bắt, không chỉ đổi count.
    staged = _LAST_PREVIEW.get((tuple(rules), tuple(targets)))
    if staged is not None:
        counts_changed = counts != staged[0] or len(changes) != staged[1]
        tags_changed = False
        for rel, expected_tag in staged[2].items():
            live = _read_normalized(os.path.join(workspace.root, rel))
            live_tag = file_hash(live).upper() if live is not None else None
            if live_tag != expected_tag.upper():
                tags_changed = True
                break
        if counts_changed or tags_changed:
            reason = ("match counts changed" if counts_changed
                      else "file contents changed since the preview")
            return (f"Error: Preview is stale / no longer matches ({reason}); "
                    "nothing was written. Re-run the preview first, then "
                    "apply.")
    _LAST_PREVIEW.pop((tuple(rules), tuple(targets)), None)

    # ---- Pha 2: apply thật + stale check giữa 2 pha + fresh tags ----
    try:
        applied_changes, applied_counts, _, _, _ = run(dry_run=False)
    except RewriteConflict as conflict:
        return f"Error: apply failed; no files were modified: {conflict}"
    applied_total = len(applied_changes)

    if applied_counts != counts or applied_total != len(changes):
        if applied_total == 0:
            return ("Error: Preview is stale / no longer matches; no replacements "
                    f"were applied. Preview expected {len(changes)} replacement(s) "
                    f"in {len(counts)} file(s).")
        return ("Error: Preview is stale / no longer matches; "
                f"{applied_total} of {len(changes)} replacements were applied "
                f"in {len(applied_counts)} of {len(counts)} files.")

    fresh_headers: list[str] = []
    for rel in sorted(applied_counts):
        absolute = os.path.join(workspace.root, rel)
        text = _read_normalized(absolute)
        if text is not None:
            tag = store.record(workspace.canonical_key(absolute), text)
            fresh_headers.append(f"[{rel}#{tag}]")

    message = f"Applied {applied_total} replacement(s) in {len(applied_counts)} file(s)."
    if fresh_headers:
        message += "\n" + "\n".join(fresh_headers)
    console.print(f"[dim]ast_edit → applied {applied_total} replacement(s)[/dim]")
    return message


ast_tools = [ast_grep, ast_edit]
