"""Demo toàn bộ engine hashline — vòng đời edit của agent THẬT, không cần LLM.

Chạy:  uv run python scripts/demo_engine.py

Gọi trực tiếp các tool read/write/edit (giống hệt những gì model sẽ gọi)
trên một workspace tạm — diễn theo dòng thời gian một phiên sửa code:
viết file mới → đọc lấy tag → sửa đúng → tag chaining → các tình huống
từ chối (stale tag, unseen lines, path lậu) → CUT/PASTE → REM.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

# Workspace tạm — phải set TRƯỚC khi dùng tool (singleton lazy)
_DEMO_ROOT = Path(tempfile.mkdtemp(prefix="dino-demo-"))
os.environ["DINO_WORKSPACE"] = str(_DEMO_ROOT)

from dino_coding.tools.editor import edit  # noqa: E402
from dino_coding.tools.fs import read, write  # noqa: E402

console = Console()


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


def tag_of(tool_output: str) -> str:
    return tool_output.splitlines()[0].split("#")[1].rstrip("]")


def call_read(path: str, **kwargs: int) -> str:
    return read.invoke({"path": path, **kwargs})


def call_write(path: str, content: str) -> str:
    return write.invoke({"path": path, "content": content})


def call_edit(patch: str) -> str:
    return edit.invoke({"input": patch})


# ===========================================================================
console.print(
    Panel(
        f"workspace demo: [magenta]{_DEMO_ROOT}[/magenta]\n"
        "mỗi lượt gọi tool y hệt output model sẽ nhận",
        title="Hashline Engine — vòng đời một phiên sửa code", style="green"),
)

# --- 1. write: tạo file mới ------------------------------------------------
title(1, "write tạo file mới → snapshot header")
out = call_write(
    "calc.py",
    '"""Tiny calc."""\n\n\ndef calc(a, b):\n    return a + b\n',
)
show(out, "green")
explain("write là cách tạo file mới; edit chỉ nhận file đã có snapshot")

# --- 2. read: lấy tag + số dòng anchor -------------------------------------
title(2, "read → header [path#TAG] + số dòng anchor")
out = call_read("calc.py")
tag = tag_of(out)
show(out)
explain(f"tag [yellow]{tag}[/yellow] chính là 'vé' model phải mang theo khi edit")

# --- 3. edit đúng: PUT theo anchor ----------------------------------------
title(3, "edit PUT 4.=4 → thành công, trả TAG MỚI")
out = call_edit(f"[calc.py#{tag}]\nPUT 4.=4:\n+    return a * b")
show(out, "green")
new_tag = tag_of(out)
explain(f"tag chaining: [yellow]{tag}[/yellow] → [yellow]{new_tag}[/yellow]; "
        f"dùng tag mới cho lần sửa kế tiếp trên cùng file")

# --- 4. dùng lại tag cũ (stale) → bị chặn ---------------------------------
title(4, "dùng tag cũ sau khi file đã đổi → STALE, bị chặn")
out = call_edit(f"[calc.py#{tag}]\nPUT 4.=4:\n+    return a - b")
show(out, "red")
explain("engine so hash hiện tại của file với tag — lệch là từ chối, không bao giờ mù edit")

# --- 5. unseen lines guard --------------------------------------------------
title(5, "read phân trang rồi sửa dòng chưa từng thấy → bị chặn + reveal")
big = "".join(f"row {i}\n" for i in range(1, 21))
call_write("data.txt", big)
page = call_read("data.txt", offset=1, limit=5)  # model chỉ thấy dòng 1-5
page_tag = tag_of(page)
out = call_edit(f"[data.txt#{page_tag}]\nPUT 12.=12:\n+hacked")
show(out, "red")
explain("guard seen-lines: chỉ dòng đã hiển thị mới đủ điều kiện làm anchor; "
        "thông báo reveal đúng vùng model cần đọc lại")

# --- 6. CUT + PASTE qua register giữa 2 file --------------------------------
title(6, "CUT sang register @fn rồi PASTE sang file khác")
call_write("src.py", "keep\nMOVE ME\nkeep2\n")
call_write("dst.py", "header\n")
t_src = tag_of(call_read("src.py"))
t_dst = tag_of(call_read("dst.py"))
out = call_edit(
    f"[src.py#{t_src}]\nCUT 2.=2 @fn\n"
    f"[dst.py#{t_dst}]\nPUT >1 @fn"
)
show(out, "green")
moved = (_DEMO_ROOT / "dst.py").read_text(encoding="utf-8")
console.print(f"  dst.py trên đĩa: [green]{moved!r}[/green]")
explain("register @fn sống qua ranh giới file trong CÙNG một lượt edit")

# --- 7. file lớn → outline --------------------------------------------------
title(7, "file 160 dòng → read gấp thành outline")
body = "".join(f"def fn_{i}(x):\n    y = {i}\n    return y + x\n\n" for i in range(40))
call_write("big.py", body)
out = call_read("big.py")
lines_out = out.splitlines()
console.print(f"  [{lines_out[0]}]")
for line in lines_out[1:8]:
    console.print(f"  {line}")
console.print(f"  [dim]… tổng {len(lines_out)} dòng thay vì 160[/dim]")
explain("chỉ xương (def/class/import) được đánh số — dòng gấp KHÔNG phải anchor, "
        "phải re-read offset/limit trước khi sửa")

# --- 8. path lậu → từ chối --------------------------------------------------
title(8, "model gõ path lọt ra ngoài workspace → từ chối")
out = call_read("../../etc/passwd")
show(out, "red")
explain("WorkspacePolicy cô lập mọi truy cập vào root — model không đọc được gì ngoài dự án")

# --- 9. REM -----------------------------------------------------------------
title(9, "REM xóa file + dọn snapshot")
t_src = tag_of(call_read("src.py"))
out = call_edit(f"[src.py#{t_src}]\nREM")
show(out, "green")
console.print(f"  src.py còn tồn tại? [red]{(_DEMO_ROOT / 'src.py').exists()}[/red]")
explain("snapshot cũng bị invalidate — model không thể hallucinate nội dung file đã xóa")

# ===========================================================================
table = Table(title="Tổng kết — engine phản ứng gì với từng hành vi của model")
table.add_column("Hành vi model", style="bold")
table.add_column("Engine", style="magenta")
table.add_row("Edit đúng tag, dòng đã thấy", "Áp dụng + trả tag mới (tag chaining)")
table.add_row("Dùng tag cũ (file đã đổi)", "Từ chối + chẩn đoán stale")
table.add_row("Sửa dòng chưa từng hiển thị", "Từ chối + reveal vùng cần đọc")
table.add_row("Path trốn ra ngoài workspace", "Từ chối (path policy)")
table.add_row("Xóa file", "Xóa + invalidate snapshot")
console.print()
console.print(table)
console.print()
console.print("[bold green]✓ Demo hoàn tất — mọi edit đều qua mỏ neo tag: không đoán mò, không mù sửa.[/bold green]")
