"""Toàn bộ text model-facing của engine (lỗi, cảnh báo, định dạng dòng).

Port của crates/pi-edit/src/modes/hashline/messages.rs và mismatch.rs.
Giữ nguyên tiếng Anh gốc: models được train trên các chuỗi này.
"""

from __future__ import annotations

import json
from typing import Optional

MISMATCH_CONTEXT = 2  # dòng ngữ cảnh quanh anchor trong thông báo lỗi

# ---- warnings phổ biến (const, rút từ messages.rs) ----
BARE_BODY_AUTO_PIPED_WARNING = (
    "Auto-prefixed bare body row(s) with `+`. Body rows must be `+TEXT` literal lines."
)
MINUS_ROW_REJECTED = (
    "`-` rows are not valid; the range already names the lines being changed. "
    "For Markdown bullets or other literal `-` lines, prefix the literal row with `+`: `+- item`."
)
MINUS_BULLET_AUTO_PIPED_WARNING = (
    "Auto-prefixed bare `-` Markdown bullet row(s) with `+` as literal content."
)
DIFF_OLD_ROWS_IGNORED_WARNING = (
    "Ignored `-` context row(s) copied from a diff; body rows are final content only."
)
EMPTY_INSERT = (
    "`PUT <N:` / `PUT >N:` promises body rows and got none. Write `+TEXT` rows, or drop "
    "the `:` to paste a register (`PUT >N` = anonymous, `PUT >N @name` = named)."
)
EMPTY_PUT_AUTO_CUT_WARNING = (
    "`PUT N.=M:` with an empty body was treated as `CUT N.=M` (delete the range)."
)
CUT_COLON_IGNORED_WARNING = "CUT takes no body; the trailing `:` was ignored."
CUT_TAKES_NO_BODY = "CUT takes no body rows. Name the range on the CUT line itself."
REM_TAKES_NO_BODY = "`REM` deletes the whole file and takes no body rows."
MOVE_TAKES_NO_BODY = "`MV` takes no body rows. Put line ops in a separate section."
REGISTER_PUT_TAKES_NO_BODY = (
    "Register pastes have no body: the payload comes from the named `CUT ... @name`."
)
COLON_ON_REGISTER_PUT = (
    "Register pastes take no `:` and no body: the payload comes from the named `CUT ... @name`."
)
COLONLESS_PUT_TAKES_NO_BODY = "Body rows require a trailing `:` on the hunk header."
COLONLESS_SPAN_PUT = "`PUT N.=M` without `:` and without a body is ambiguous; write `CUT N.=M` to delete."
SNAPSHOT_ROWS_AUTO_PUT_WARNING = (
    "Recovered pasted read-output row(s) `N:TEXT` as single-line `PUT N.=N:` replacements."
)
BARE_RANGE_AUTO_PUT_WARNING = "Recovered a bare `N-M:` row as `PUT N.=M:`."
READ_METADATA_IGNORED_WARNING = "Ignored read metadata/truncation notice row(s) in the patch body."
REPLACE_PAIR_COALESCED_WARNING = (
    "Coalesced a duplicated before/after replacement pair into one hunk; body is final content only."
)
BLOCK_RESOLVER_UNAVAILABLE = (
    "Block locators (`N*` in `PUT N*:`, `PUT >N*`, `CUT N*`) are not available here "
    "(no block resolver configured). Use a concrete line range."
)
EMPTY_PASTE = (
    "Nothing to paste: no unlabeled `CUT` precedes this `PUT` in this call, and the anonymous "
    "register never carries across calls. Put `CUT N.=M` above it, or use named registers "
    "(`CUT ... @name` -> `PUT ... @name`)."
)
CLIPBOARD_INTERLEAVED_SECTIONS = (
    "The same file appears in non-adjacent sections while clipboard edits are in play. "
    "Keep each file's ops under ONE `[path#TAG]` header."
)
HEADTAIL_DRIFT_WARNING = (
    "File changed since the tagged read; these ops are head/tail inserts with no line anchors, "
    "so they were applied to the current content. Verify the placement."
)


def json_quote(value: str) -> str:
    """JSON.stringify tương thích JS — dùng trong thông báo lỗi. ← port messages::json_quote"""
    return json.dumps(value, ensure_ascii=False)


def format_numbered_line(number: int, line: str) -> str:
    """`N:TEXT` — định dạng dòng của read output và context lỗi. ← port messages"""
    return f"{number}:{line}"


def format_anchored_context(anchor_lines: list[int], file_lines: list[str]) -> list[str]:
    """Ngữ cảnh ±MISMATCH_CONTEXT dòng quanh mỗi anchor. ← port messages::format_anchored_context

    Dòng anchor đánh dấu `*N:TEXT`, dòng ngữ cảnh ` N:TEXT` (leading space),
    chèn `...` giữa các vùng không liền kề.
    """
    rows: list[str] = []
    last_emitted: Optional[int] = None
    for anchor in sorted(anchor_lines):
        if not (1 <= anchor <= len(file_lines)):
            continue
        start = max(1, anchor - MISMATCH_CONTEXT)
        end = min(len(file_lines), anchor + MISMATCH_CONTEXT)
        if last_emitted is not None and start > last_emitted + 1:
            rows.append("...")
        for n in range(start, end + 1):
            marker = "*" if n == anchor else " "
            rows.append(f"{marker}{n}:{file_lines[n - 1]}")
        last_emitted = end
    return rows


def missing_snapshot_tag_message(path: str) -> str:
    return (
        f"Missing hashline snapshot tag for {path}; use `[{path}#tag]` from your latest "
        f"read/search output. To create a new file, use the write tool."
    )


def file_not_found_message(path: str) -> str:
    return f"File not found: {path}. Use the write tool to create new files."


def invalid_header_message(preview: str) -> str:
    return (
        'input must begin with "[PATH#HASH]" on the first non-blank line for anchored edits; '
        f"got: {json_quote(preview)}. Example: \"[src/foo.ts#1A2B]\" then edit ops."
    )


def conflicting_tags_message(path: str, first: str, second: str) -> str:
    return (
        f"Conflicting hashline snapshot tags for {path}: #{first} and #{second}. "
        "Re-read the file and retry with one current header."
    )


def no_change_diagnostic(path: str) -> str:
    return (
        f"Edits to {path} parsed and applied cleanly, but produced no change: your body row(s) "
        "are byte-identical to the file at the targeted lines. The bug is somewhere else — "
        "re-read the file before issuing another edit. Do NOT widen the payload or add lines; "
        "verify the anchor first."
    )


def no_change_loop_diagnostic(path: str, count: int) -> str:
    return (
        f"STOP. Edits to {path} have been a byte-identical no-op {count} times in a row — the "
        "patch body matches the file at the targeted lines and the soft hint did not break the "
        "cycle. Cease re-issuing this payload. Either the intended change is already on disk "
        "(move on), or your anchor is wrong (re-read the file with `read` to observe the current "
        "line numbers and tag, then author a different edit). This exact payload will keep being "
        "rejected until it changes."
    )


def unseen_lines_message(
    path: str,
    unseen: list[int],
    tag: str,
    revealed: list[tuple[int, str]],
    truncated: bool,
) -> str:
    """Guard seen-lines: liệt kê dòng chưa từng hiển thị + lộ nội dung thật.
    ← port messages::unseen_lines_message
    """
    selector = ",".join(str(line) for line in unseen)
    header = (
        f"This edit anchors to lines {selector} of {path} that [{path}#{tag}] never displayed "
        "(it showed a partial range, a search hit, or a folded summary)."
    )
    if not revealed:
        return (
            f"{header} Re-read them in full first with a ranged read (pass explicit "
            f"`offset`/`limit` covering {selector}) — it skips summarization and mints a fresh "
            "tag — then re-issue the edit."
        )
    preview = "\n".join(f"  {n}:{text}" for n, text in revealed)
    if truncated:
        return (
            f"{header} Preview of the actual file content at the first {len(revealed)} unseen "
            f"line(s):\n{preview}\nThe range exceeds the inline preview cap — re-read the "
            f"remainder (offset/limit covering {selector}) before re-issuing the edit."
        )
    return (
        f"{header} Actual file content at those lines:\n{preview}\nVerify the content matches "
        "what you intend to touch, then re-issue the edit with the same [path#tag] header — a "
        "straight retry now succeeds without a re-read. If the content does NOT match, fix your "
        "line numbers."
    )


def format_mismatch_message(
    path: str,
    expected: str,
    actual: str,
    file_lines: list[str],
    anchor_lines: list[int],
    hash_recognized: bool,
) -> str:
    """Chẩn đoán tag lệch. ← port mismatch::format_mismatch_message (nguyên văn)"""
    where = f" for {path}" if path else ""
    if hash_recognized:
        lines = [
            f"Edit rejected{where}: file changed between read and edit.",
            f"Section is bound to #{expected}, but the current file hashes to #{actual}. If a "
            "prior edit in this session modified this file, copy the [path#newhash] header from "
            "that edit's response; otherwise re-read the file with `read` to refresh the tag "
            "before retrying.",
        ]
    else:
        lines = [
            f"Edit rejected{where}: hash #{expected} is not from this session.",
            f"The current file hashes to #{actual}. Re-read the file with `read` to copy a "
            "current [path#tag] header — never invent the tag and never reuse one from a prior "
            "session.",
        ]
    context = format_anchored_context(anchor_lines, file_lines)
    if context:
        lines.append("")
        lines.extend(context)
    return "\n".join(lines)


def format_out_of_range(line: int, total: int) -> str:
    return f"Line {line} does not exist (file has {total} lines)"
