"""Compact diff preview `-N|old` / `+N|new` — mô phỏng streaming_diff của omp."""

from __future__ import annotations

import difflib


def compact_preview(before: list[str], after: list[str], max_rows: int = 64) -> str:
    rows: list[str] = []
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        for i in range(i1, i2):
            rows.append(f"-{i + 1}|{before[i]}")
        for j in range(j1, j2):
            rows.append(f"+{j + 1}|{after[j]}")
    if len(rows) > max_rows:
        head = rows[: max_rows // 2]
        tail = rows[-(max_rows - len(head)) :]
        return "\n".join(head + [f"… ({len(rows) - max_rows} more rows)"] + tail)
    return "\n".join(rows)
