"""Demo engine Phase 2.5 — các module ast-grep KHÔNG cần LLM, không cần workspace.

Chạy:  uv run python scripts/demo_ast.py

Diễn theo dòng thời gian một lần "codebase intelligence" của agent:
1. astlang    — cổng vào: file nào parse được, ngôn ngữ gì (ext + alias)
2. astfind    — structural search: metavar $NAME/$$$NAME, parse-error vẫn quét,
               pattern rác bị heuristic chặn TRƯỚC khi tìm
3. astrewrite — expand_template (phần bù lỗ hổng replace() của binding),
               rewrite_text đa rule một parse, rewrite_target staged writes
4. block      — block_range_at: dòng neo → span block syntax; suggestion ±64
5. resolve_block_edits — hạ `PUT N*` về line-edit thường (cầu nối về Phase 2)

Khác với scripts/acceptance_phase25.py (gọi TOOL trên workspace thật, E2E),
demo này gọi thẳng engine để thấy từng cấu trúc dữ liệu trung gian.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ast_grep_py import SgRoot
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from dino_coding.tools.astfind import find_matches, pattern_is_valid
from dino_coding.tools.astlang import is_supported_file, resolve_language
from dino_coding.tools.astrewrite import expand_template, rewrite_target, rewrite_text
from dino_coding.tools.hashline.block import (
    block_range_at,
    find_enclosing_block,
    find_next_block,
    resolve_block_edits,
)
from dino_coding.tools.hashline.types import Anchor, EditBlock

console = Console()

_ROOT = Path(tempfile.mkdtemp(prefix="dino-ast-demo-"))

SAMPLE = (
    "import os\n"
    "\n"
    "\n"
    "def slow(a, b):\n"
    "    total = a + b\n"
    "    return total\n"
    "\n"
    "class Calc:\n"
    "    def run(self, x):\n"
    "        print(x)\n"
    "        return slow(x, 1)\n"
    "\n"
    "print('done')\n"
)


def title(no: int, name: str) -> None:
    console.print()
    console.rule(f"[bold cyan]Bước {no}: {name}[/bold cyan]", style="cyan")


def explain(text: str) -> None:
    console.print(f"  [dim]→ {text}[/dim]")


def show(text: str, color: str = "white") -> None:
    for line in text.splitlines()[:14]:
        console.print(f"  [{color}]{escape(line)}[/{color}]")
    if len(text.splitlines()) > 14:
        console.print(f"  [dim]… ({len(text.splitlines()) - 14} dòng nữa)[/dim]")


def main() -> None:
    console.print(Panel.fit(
        "[bold]dino-coding · Phase 2.5 engine demo[/bold]\n"
        "astlang → astfind → astrewrite → hashline/block",
        border_style="green",
    ))
    src = _ROOT / "app.py"
    src.write_text(SAMPLE, encoding="utf-8", newline="")
    explain(f"file mẫu: {src} ({len(SAMPLE.splitlines())} dòng)")

    # ---- 1. astlang -------------------------------------------------------
    title(1, "astlang — cổng vào: file nào parse được, ngôn ngữ gì?")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Path")
    table.add_column("supported")
    table.add_column("lang")
    for rel in ("app.py", "lib.ts", "ui.vue", "data.bin", "Makefile"):
        table.add_row(rel, str(is_supported_file(rel, None)), str(resolve_language(None, rel)))
    console.print(table)
    explain("`.vue` alias → typescript; `.bin`/`Makefile` bị loại khỏi mọi scan.")

    # ---- 2. astfind --------------------------------------------------------
    title(2, "astfind — structural search với metavariable")
    result = find_matches("def $NAME($$$ARGS):\n    $$$BODY", str(src))
    explain(
        'pattern "def $NAME($$$ARGS):\n    $$$BODY" (def PHẢI gồm body '
        f"để thành node hoàn chỉnh) → {result.total_matches} matches, "
        f"{result.files_searched} file quét"
    )
    for m in result.matches:
        console.print(
            f"  dòng {m.start_line}–{m.end_line}  "
            f"[green]$NAME[/green]={escape(m.meta.get('NAME', '?'))}  "
            f"$$$ARGS={escape(m.meta.get('ARGS', '?'))}"
        )

    explain("pattern rác bị heuristic chặn trước khi tìm (binding im lặng trả []):")
    for pat in ("def $NAME($$$ARGS):", "def def def(", "pri nt("):
        ok = pattern_is_valid(pat, "python")
        mark = "[green]True[/green]" if ok else "[red]False[/red]"
        console.print(f"  pattern_is_valid({pat!r:<22}) → {mark}")

    # ---- 3. astrewrite ------------------------------------------------------
    title(3, "astrewrite — expand_template + rewrite_text (codemod 1 file)")
    explain("lỗ hổng binding: node.replace() trả template THÔ — ta tự thay metavar.")
    root = SgRoot(SAMPLE, "python").root().find_all(pattern="print($$$ARGS)")[0]
    console.print(
        "  expand_template(\"log($$$ARGS, src='m')\") →\n"
        f"    [yellow]{escape(expand_template('log($$$ARGS, src=\'m\')', root, SAMPLE))}[/yellow]"
    )

    changes, out = rewrite_text(
        SAMPLE, "python", [("print($$$ARGS)", "log($$$ARGS, level='debug')")]
    )
    explain(f"rewrite_text 1 rule → {len(changes)} thay đổi:")
    show(out, "yellow")

    staged = rewrite_target(
        [("print($$$ARGS)", "log($$$ARGS, level='debug')")], str(src)
    )
    explain(
        f"rewrite_target dry-run → {staged.total_replacements} thay đổi trên "
        f"{staged.files_touched} file, applied={staged.applied}"
    )
    for change in staged.changes:
        console.print(
            f"  {change.path}: dòng {change.start_line}  "
            f"[red]{escape(change.before)}[/red] → [green]{escape(change.after)}[/green]"
        )

    # ---- 4. block -----------------------------------------------------------
    title(4, "hashline/block — dòng neo → span block syntax")
    for line_no, note in ((1, "import"), (4, "def slow"), (8, "class"),
                          (9, "def run"), (12, "thân hàm"), (7, "dòng trống")):
        span = block_range_at(SAMPLE, "app.py", line_no)
        mark = str(span) if span else "[red]None[/red]"
        console.print(f"  block_range_at(dòng {line_no:<2} {note:<11}) → {mark}")
    console.print(f"  find_next_block(7)        → {find_next_block(7, SAMPLE, 'app.py')}")
    console.print(
        f"  find_enclosing_block(10)  → {find_enclosing_block(10, SAMPLE, 'app.py')}"
    )

    # ---- 5. resolve_block_edits ---------------------------------------------
    title(5, "resolve_block_edits — hạ PUT N* về line-edit thường")
    edits = [EditBlock(Anchor(4), ["def slow(a, b):", "    return a * b"],
                       None, None, 1, 0)]
    lowered, warnings = resolve_block_edits(edits, SAMPLE, "app.py")
    explain(
        f"PUT 4* (2 dòng body) → {len(lowered)} line-edit "
        f"({', '.join(type(e).__name__ for e in lowered)}), "
        f"{len(warnings)} cảnh báo"
    )
    for edit in lowered:
        console.print(f"  [cyan]{edit}[/cyan]")

    console.print()
    console.rule("[bold green]Kết: engine Phase 2.5 hoạt động đúng hợp đồng[/bold green]")
    console.print(
        "[dim]Muốn thấy tầng TOOL E2E (tag mint, preview/apply, stale, CUT N*): "
        "uv run python scripts/acceptance_phase25.py[/dim]"
    )


if __name__ == "__main__":
    main()
