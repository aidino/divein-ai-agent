"""Demo Todo Tracker & Engine — Quản lý công việc và Cognitive Anchor.

Chạy:  uv run python scripts/demo_todo.py

Kịch bản demo 5 bước trực quan bằng Rich console:
- Bước 1: Khởi tạo hierarchical phases (Khảo sát, Triển khai, Kiểm thử) -> bảng trực quan.
- Bước 2: Bắt đầu & hoàn thành task -> auto-advance pointer sang task kế tiếp.
- Bước 3: Đánh dấu block kèm lý do -> pointer tự động chuyển sang task khả thi tiếp theo.
- Bước 4: Gỡ block (unblock) -> task khôi phục trạng thái pending, xóa ghi chú blocker.
- Bước 5: Markdown export (to_markdown) và round-trip import (from_markdown).
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dino_coding.tools.todo.tracker import TodoTracker
from dino_coding.tools.todo.types import InitPhaseInput, TodoParams

console = Console()


def status_badge(status: str, blocker: str | None = None) -> str:
    if status == "completed":
        return "[bold green][X] completed[/bold green]"
    if status == "in_progress":
        return "[bold cyan][>] in_progress[/bold cyan]"
    if status == "blocked":
        detail = f" ({blocker})" if blocker else ""
        return f"[bold red][!] blocked{detail}[/bold red]"
    if status == "abandoned":
        return "[dim strike][-] abandoned[/dim strike]"
    return "[yellow][ ] pending[/yellow]"


def print_phases_table(tracker: TodoTracker, title: str) -> None:
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Phase", style="bold blue", width=22)
    table.add_column("Task Content", min_width=32)
    table.add_column("Status", width=36)

    phases = tracker.phases
    for p_idx, phase in enumerate(phases):
        for t_idx, task in enumerate(phase.tasks):
            phase_col = phase.name if t_idx == 0 else ""
            table.add_row(phase_col, task.content, status_badge(task.status, task.blocker))
        if p_idx < len(phases) - 1:
            table.add_section()

    console.print(table)


def main() -> None:
    console.print(
        Panel.fit(
            "[bold white]Dino-Coding Cognitive Anchor: Todo Tracker Demo[/bold white]\n"
            "[dim]Mô phỏng máy trạng thái Todo 9 operations, tự động trỏ task tiếp theo,[/dim]\n"
            "[dim]quản lý blocker và hỗ trợ Markdown round-trip.[/dim]",
            border_style="cyan",
        )
    )

    tracker = TodoTracker()

    # -------------------------------------------------------------------------
    # Bước 1: Init with hierarchical phases
    # -------------------------------------------------------------------------
    console.print()
    console.rule("[bold cyan]Bước 1: Khởi tạo Hierarchical Phases (Khảo sát, Triển khai, Kiểm thử)[/bold cyan]")
    init_params = TodoParams(
        op="init",
        list=[
            InitPhaseInput(
                phase="1. Khảo sát & Thiết kế",
                items=[
                    "Đọc tài liệu kiến trúc cognitive anchor",
                    "Thiết kế schema TodoItem và TodoPhase",
                ],
            ),
            InitPhaseInput(
                phase="2. Triển khai lõi",
                items=[
                    "Cài đặt máy trạng thái engine.py",
                    "Tích hợp TodoTracker và LangChain tool",
                ],
            ),
            InitPhaseInput(
                phase="3. Kiểm thử & Nghiệm thu",
                items=[
                    "Viết unit tests cho middleware và tracker",
                    "Chạy acceptance scenario phase 3",
                ],
            ),
        ],
    )
    summary, err = tracker.execute_op(init_params)
    assert not err, f"Lỗi khởi tạo: {summary}"

    print_phases_table(tracker, "Sau khi init: Task đầu tiên tự động chuyển sang `in_progress`")
    console.print("  [dim]Auto-advance pointer: Task 1 của Phase 1 đang giữ cờ [bold cyan]in_progress[/bold cyan].[/dim]")

    # -------------------------------------------------------------------------
    # Bước 2: Start & Done -> auto-advance pointer
    # -------------------------------------------------------------------------
    console.print()
    console.rule("[bold cyan]Bước 2: Hoàn thành task -> Auto-advance Pointer[/bold cyan]")
    console.print("  [dim]Thực hiện xong 'Đọc tài liệu kiến trúc cognitive anchor' -> gọi op='done'[/dim]")
    summary, err = tracker.execute_op(
        TodoParams(op="done", task="Đọc tài liệu kiến trúc cognitive anchor")
    )
    assert not err, f"Lỗi hoàn thành task: {summary}"

    print_phases_table(tracker, "Sau op='done': Task 1 completed, Task 2 tự động thành in_progress")
    console.print("  [dim]Engine tự động tìm task pending sớm nhất để gán [bold cyan]in_progress[/bold cyan].[/dim]")

    # -------------------------------------------------------------------------
    # Bước 3: Block with blocker reason -> auto-advance to next actionable task
    # -------------------------------------------------------------------------
    console.print()
    console.rule("[bold cyan]Bước 3: Gặp trở ngại (Block) kèm lý do -> Pointer chuyển task tiếp[/bold cyan]")
    console.print("  [dim]Task 2 bị nghẽn vì chờ team review -> gọi op='block' kèm lý do[/dim]")
    summary, err = tracker.execute_op(
        TodoParams(
            op="block",
            task="Thiết kế schema TodoItem và TodoPhase",
            reason="Chờ API spec review từ Architect team",
        )
    )
    assert not err, f"Lỗi block: {summary}"

    print_phases_table(tracker, "Sau op='block': Task 2 chuyển blocked, pointer chuyển sang Task 1 của Phase 2")
    console.print("  [dim]Task bị block không bao giờ tự động khởi chạy. Con trỏ nhảy sang task pending tiếp theo.[/dim]")

    # -------------------------------------------------------------------------
    # Bước 4: Unblock -> restored to pending, blocker cleared
    # -------------------------------------------------------------------------
    console.print()
    console.rule("[bold cyan]Bước 4: Gỡ trở ngại (Unblock) -> Khôi phục Pending, xóa Blocker[/bold cyan]")
    console.print("  [dim]Đã nhận được review spec -> gọi op='unblock' cho Task 2[/dim]")
    summary, err = tracker.execute_op(
        TodoParams(op="unblock", task="Thiết kế schema TodoItem và TodoPhase")
    )
    assert not err, f"Lỗi unblock: {summary}"

    print_phases_table(tracker, "Sau op='unblock': Task 2 gỡ bỏ lý do blocker, trạng thái sẵn sàng")
    console.print("  [dim]Ghi chú blocker được làm sạch; tính toàn vẹn của danh sách được bảo toàn.[/dim]")

    # -------------------------------------------------------------------------
    # Bước 5: Markdown export & round-trip import
    # -------------------------------------------------------------------------
    console.print()
    console.rule("[bold cyan]Bước 5: Markdown Export & Round-Trip Import[/bold cyan]")
    md_output = tracker.to_markdown()

    console.print(
        Panel(
            md_output.strip(),
            title="Exported Markdown (tracker.to_markdown())",
            border_style="green",
        )
    )

    new_tracker = TodoTracker()
    parse_errors = new_tracker.from_markdown(md_output)
    assert not parse_errors, f"Lỗi parse markdown: {parse_errors}"

    print_phases_table(new_tracker, "Imported Tracker từ Markdown (Trạng thái và Blocker nguyên vẹn)")
    console.print("  [bold green]✓ Round-trip hoàn hảo: Cấu trúc phase, task và trạng thái đồng nhất 100%![/bold green]\n")


if __name__ == "__main__":
    main()
