"""Hashline edit tool — port của packages/coding-agent/src/edit/index.ts.

Một tham số duy nhất `input`: nội dung patch hashline nhiều file.
"""

from __future__ import annotations

import os
import shutil

from langchain_core.tools import tool
from rich.console import Console

from dino_coding.tools.hashline import messages
from dino_coding.tools.hashline.input import split_patch
from dino_coding.tools.hashline.patcher import StagedFile, stage_patch
from dino_coding.tools.hashline.text import LineEnding, normalize_to_lf
from dino_coding.tools.workspace import get_store, get_workspace

console = Console()

# ← rút từ crates/pi-edit/prompts/hashline.md (chỉ ops engine này hỗ trợ)
HASHLINE_DESCRIPTION = """Edit existing files using line-anchored hunks. New files: use `write`.

Each file section: `[PATH#TAG]` where TAG is the required 4-hex snapshot tag copied
verbatim from the latest `read`/`write` output header. Numbers are original line
numbers from that output, never shifted.

<ops>
`PUT N.=M:` replace inclusive lines N-M with the `+` body (`N.=N` for one line).
`PUT <N:` insert body before line N; `PUT >N:` insert after line N.
`PUT >$:` append at end of file.
`CUT N.=M` delete lines N-M, optionally capturing as `CUT N.=M @name`.
`PUT <N @name` / `PUT >N @name` / `PUT N.=M @name` paste a register (anonymous
paste: `PUT <N` after an unlabeled `CUT`).
`REM` delete the whole file. `MV DEST` rename/move the file after edits.
</ops>

<rules>
- Body rows are `+TEXT` verbatim including indentation; a lone `+` is a blank line.
  Never send removed lines back; the body is the FINAL content of the range only.
- Body length is independent of the range length. To delete, use `CUT`, not an empty PUT.
- Only touch lines you actually saw in the latest read; re-read after edits change
  line numbers or the tag. If the tool reports a mismatch or unseen lines, re-read
  and retry — never invent a tag.
- Split non-adjacent changes into multiple hunks; one hunk per contiguous range.
- After every successful edit the response carries a NEW `[path#TAG]` header; use it
  for the next edit to the same file.
</rules>

<example>
```
[greet.py#A1B2]
PUT 3.=4:
+def greet(name):
+    print(name)
```
Cross-file move: `CUT 2.=5 @fn` in the source section, then `PUT <1 @fn` in the
destination section (same input, different `[PATH#TAG]` headers).
</example>"""


@tool(description=HASHLINE_DESCRIPTION)
def edit(input: str) -> str:
    """Edit existing files using line-anchored hunks. New files: use `write`."""
    workspace = get_workspace()
    store = get_store()

    try:
        patch = split_patch(input)
        staged = stage_patch(patch, input, store, workspace)
    except ValueError as error:
        # Lỗi model-facing: trả nguyên văn để model tự sửa (byte-faithful theo omp)
        console.print(f"[red]edit rejected:[/red] {str(error).splitlines()[0][:160]}")
        return f"Edit rejected:\n{error}"

    outcomes: list[str] = []
    for item in staged:
        outcomes.append(_commit(item, store, workspace))

    result = "\n\n".join(outcomes)
    console.print(f"[green]edit applied:[/green] {', '.join(f.display_path for f in staged)}")
    return result


def _commit(item: StagedFile, store, workspace) -> str:
    """Ghi một StagedFile xuống đĩa + mint tag mới + carry seen-lines."""

    canonical = workspace.canonical_key(item.absolute_path)

    if item.op == "delete":
        os.remove(item.absolute_path)
        store.invalidate(canonical)
        return f"Deleted {item.display_path}"

    # Ghi theo kiểu dòng gốc của file
    on_disk = LineEnding.restore(item.after, item.ending)
    os.makedirs(os.path.dirname(item.absolute_path) or ".", exist_ok=True)
    with open(item.absolute_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(on_disk)

    if item.op == "move" and item.move_to:
        shutil.move(item.absolute_path, item.move_to)
        store.relocate(canonical, workspace.canonical_key(item.move_to))
        canonical = workspace.canonical_key(item.move_to)
        item.display_path = workspace.display(item.move_to)

    # Snapshot phiên bản mới → tag mới cho lần edit kế tiếp
    written = normalize_to_lf(on_disk)
    tag = store.record(canonical, written)
    store.reset_noop(canonical)

    # Carry seen-lines: giữ các dòng đã seen từ snapshot cũ trong vùng đầu gióng nhau
    _carry_seen_lines(store, canonical, tag, item)

    header = f"[{item.display_path}#{tag}]"
    lines = [header]
    if item.op == "noop":

        lines.append(messages.no_change_diagnostic(item.display_path))
    if item.diff_preview:
        lines.append(item.diff_preview)
    if item.op == "move":
        lines.append(f"Moved to {workspace.display(item.move_to or '')}")
    text = "\n".join(line for line in lines if line)
    if item.warnings:
        text += "\n\nWarnings:\n" + "\n".join(f"- {w}" for w in item.warnings)
    return text


def _carry_seen_lines(store, canonical: str, tag: str, item: StagedFile) -> None:
    """← port session::carried_seen_lines (rút gọn: prefix chung đầu file)."""
    prior = store.by_content(canonical, item.before)
    if prior is None or not prior.seen_lines:
        return
    before_lines = item.before.split("\n")
    after_lines = item.after.split("\n")
    prefix = 0
    for a, b in zip(before_lines, after_lines):
        if a != b:
            break
        prefix += 1
    carried = [line for line in prior.seen_lines if line <= prefix]
    if carried:
        store.record_seen_lines(canonical, tag, carried)
