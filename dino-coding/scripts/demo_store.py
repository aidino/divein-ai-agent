"""Demo EditStore — 9 use case thường gặp của một coding agent thật.

Chạy:  uv run python scripts/demo_store.py

Mỗi section là một tình huống agent gặp trong session, cho thấy EditStore
(bộ nhớ chia sẻ vòng đời session của engine hashline) phản ứng thế nào và
VÌ SAO omp thiết kế như vậy. Tag là xxh32 → tất cả output deterministic.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dino_coding.tools.hashline.store import (
    MAX_PATHS,
    MAX_VERSIONS_PER_PATH,
    NOOP_HARD_LIMIT,
    EditStore,
)

console = Console()


def title(no: int, name: str) -> None:
    console.print()
    console.rule(f"[bold cyan]UC{no}: {name}[/bold cyan]", style="cyan")


def explain(text: str) -> None:
    console.print(f"  [dim]→ {text}[/dim]")


def history_len(store: EditStore, path: str) -> int:
    """Chỉ để minh họa — code thật không cần nhìn vào nội bộ store."""
    return len(store._histories.get(path, []))


# ============================================================================
store = EditStore()
APP = "src/app.py"
console.print(
    Panel(
        "[bold]EditStore[/bold] — snapshot phiên bản file + clipboard + no-op guard\n"
        f"giới hạn: {MAX_PATHS} path × {MAX_VERSIONS_PER_PATH} phiên bản, "
        f"no-op leo thang ở lần thứ {NOOP_HARD_LIMIT}",
        title="phiên làm việc của agent", style="green"),
)

# ---------------------------------------------------------------------------
# UC1: Read file → mint tag + ghi provenance "đã thấy dòng nào"
# ---------------------------------------------------------------------------
title(1, "Read file → mint tag + seen_lines")

app_v1 = '"""App module."""\n\n\ndef greet(name: str) -> str:\n    return f"Hello {name}"\n'
tag1 = store.record(APP, app_v1, seen_lines=[1, 2, 3, 4, 5])
console.print(f"  agent đọc [magenta]{APP}[/magenta] (trang 1: dòng 1-5)")
console.print(f"  store.record(...) → tag [bold yellow]{tag1}[/bold yellow]")

# Read tiếp trang 2 (dòng 6-10) — cùng phiên bản, seen_lines được GỘP
store.record(APP, app_v1, seen_lines=[6, 7, 8])
snap = store.by_hash(APP, tag1)
console.print(f"  read tiếp trang 2 → seen_lines gộp thành [green]{sorted(snap.seen_lines)}[/green]")
explain("tag là 'tàu kéo' provenance: model chỉ cần nhớ 1 tag, store nhớ dòng nào model đã thấy")

# ---------------------------------------------------------------------------
# UC2: Edit thành công → phiên bản mới, tag mới, lịch sử giữ bản cũ
# ---------------------------------------------------------------------------
title(2, "Edit thành công → lịch sử 2 phiên bản")

app_v2 = app_v1.replace('return f"Hello {name}"', 'return f"Xin chào {name}"')
tag2 = store.record(APP, app_v2, seen_lines=[1, 2, 3, 4, 5])
console.print(f"  edit áp dụng → tag mới [bold yellow]{tag2}[/bold yellow]")
console.print(f"  lịch sử {APP}: [green]{history_len(store, APP)}[/green] phiên bản (mới nhất đứng đầu)")
old = store.by_hash(APP, tag1)
console.print(f"  tra tag cũ {tag1} vẫn ra: [green]'{old.text.splitlines()[3]}'[/green]")
explain("giữ 4 bản gần nhất = 'undo hạn chế': chẩn đoán stale tag, so diff hai phiên bản")

# ---------------------------------------------------------------------------
# UC3: Tag stale — file đổi ngoài ý muốn (formatter, editor của user)
# ---------------------------------------------------------------------------
title(3, "Tag stale — file bị thay đổi từ bên ngoài")

console.print(f"  user chạy formatter → đĩa khác với lúc mint tag [yellow]{tag1}[/yellow]")
on_disk_now = app_v1.replace('"""App module."""', '"""App module (formatted)."""')
live = store.by_content(APP, on_disk_now)
console.print(f"  store.by_content(text_trên_đĩa) → [red]{live}[/red] (không phiên bản nào khớp)")
explain("by_content là cổng của seen-lines guard: text không khớp không được công nhận seen_lines")

# ---------------------------------------------------------------------------
# UC4: Model gõ tag thường — normalize hoa/thường cứu vãn
# ---------------------------------------------------------------------------
title(4, "Model gõ tag thường vẫn khớp (ví dụ 'ab12')")

found = store.by_hash(APP, tag2.lower())
console.print(f"  by_hash('{tag2.lower()}') → [green]tìm thấy[/green] phiên bản {found.hash}")
explain("omp uppercase tag ngay lúc parse (tokenizer.rs:576) + so sánh eq_ignore_ascii_case")

# ---------------------------------------------------------------------------
# UC5: No-op guard — model gửi cùng một edit lần thứ 3
# ---------------------------------------------------------------------------
title(5, "No-op guard — model gửi edit GIỐNG HỆT liên tiếp")

payload = hash(('# model sửa dòng 4 lần 1', app_v2))
for attempt in range(1, NOOP_HARD_LIMIT + 1):
    count, escalate = store.record_noop(APP, payload)
    console.print(
        f"  lần {attempt}: record_noop → (count=[yellow]{count}[/yellow], "
        f"escalate=[red]{escalate}[/red])"
        + ("  [bold red]→ agent chặn: 'STOP — cùng edit đã gửi 3 lần'[/bold red]" if escalate else "")
    )
count, _ = store.record_noop(APP, hash(("# model sửa khác", app_v2)))
console.print(f"  model đổi edit khác → count reset [yellow]{count}[/yellow]")
explain("phát hiện model chạy vòng lặp vô hạn — lỗi kinh điển của LLM agent")

# ---------------------------------------------------------------------------
# UC6: git mv — đổi tên file nhưng giữ nguyên provenance
# ---------------------------------------------------------------------------
title(6, "git mv src/app.py → src/core/app.py")

store.relocate(APP, "src/core/app.py")
moved = store.by_hash("src/core/app.py", tag1)
console.print(f"  relocate → snapshot.path = [magenta]{moved.path}[/magenta], seen_lines còn nguyên")
console.print(f"  tra path cũ: [red]{store.by_hash(APP, tag1)}[/red] (đã chuyển hết)")
explain("đổi tên file không làm agent 'mù' provenance của các dòng đã đọc")

# ---------------------------------------------------------------------------
# UC7: Clipboard — CUT vào register có tên, chỉ sống nếu batch thành công
# ---------------------------------------------------------------------------
title(7, "Clipboard: CUT vào register, batch lỗi thì biến mất")

# Batch 1: THẤT BẠI (giả sử patch sau đó lỗi cú pháp → không commit)
batch1 = store.start_clipboard_batch()
batch1.named["helper_fn"] = ["def helper():", "    return 42"]
console.print("  batch 1 (thất bại): CUT 2 dòng vào @helper_fn → [red]không commit[/red]")
console.print(f"    batch sau thấy @helper_fn? [red]{store.start_clipboard_batch().named.get('helper_fn', 'KHÔNG')}[/red]")

# Batch 2: THÀNH CÔNG
batch2 = store.start_clipboard_batch()
batch2.named["helper_fn"] = ["def helper():", "    return 42"]
store.commit_clipboard(batch2)
console.print("  batch 2 (thành công): CUT lại → commit")
console.print(f"    batch sau thấy @helper_fn? [green]{store.start_clipboard_batch().named['helper_fn']}[/green]")
explain("register có tên xuyên các lần edit; register ẩn danh chết ngay sau một apply")

# ---------------------------------------------------------------------------
# UC8: REM file — invalidate dọn sạch
# ---------------------------------------------------------------------------
title(8, "Xóa file → invalidate dọn lịch sử")

store.invalidate("src/core/app.py")
console.print(f"  invalidate('src/core/app.py') → by_hash bây giờ: [red]{store.by_hash('src/core/app.py', tag1)}[/red]")
explain("file đã xóa mà còn snapshot = mồi để model hallucinate nội dung cũ")

# ---------------------------------------------------------------------------
# UC9: Session dài — LRU eviction giới hạn bộ nhớ
# ---------------------------------------------------------------------------
title(9, f"Session dài: vượt {MAX_PATHS} path → LRU quên path cũ nhất")

tags = {}
for i in range(MAX_PATHS + 1):  # monorepo lớn: agent đọc 257 file
    path = f"src/gen/module_{i:03d}.py"
    tags[path] = store.record(path, f"# module {i}\n", seen_lines=[1])
first, last = "src/gen/module_000.py", f"src/gen/module_{MAX_PATHS:03d}.py"
console.print(f"  ghi {MAX_PATHS + 1} path...")
console.print(f"  path đầu tiên: by_hash → [red]{store.by_hash(first, tags[first])}[/red] (bị quên)")
console.print(f"  path cuối:     by_hash → [green]còn[/green] (tag {store.by_hash(last, tags[last]).hash})")
explain("bộ nhớ agent PHẢI có giới hạn — LRU đảm bảo 'đứa mới dùng gần nhất sống sót'")

# ---------------------------------------------------------------------------
table = Table(title="Tổng kết: EditStore trả lời 4 câu hỏi của agent", show_lines=False)
table.add_column("Câu hỏi", style="bold")
table.add_column("API", style="magenta")
table.add_column("Kết quả trong demo")
table.add_row("Model đã thấy dòng nào?", "record / record_seen_lines", f"UC1: {sorted(snap.seen_lines)}")
table.add_row("File này bây giờ là phiên bản nào?", "by_hash / by_content", f"UC2-3: tag mới {tag2}, stale bị chặn")
table.add_row("Model có đang chạy vòng lặp?", "record_noop", f"UC5: chặn ở lần {NOOP_HARD_LIMIT}")
table.add_row("Đổi tên / xóa file thì sao?", "relocate / invalidate", "UC6-8: provenance đi theo / dọn sạch")
console.print()
console.print(table)
console.print()
console.print("[bold green]✓ Demo hoàn tất — store là 'bộ nhớ sự thật' của agent: mọi tra cứu đều qua tag.[/bold green]")
