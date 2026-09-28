"""Kịch bản nghiệm thu Phase 3 — "Multi-Phase Refactoring Sprint" (E2E acceptance).

Chạy:  uv run python scripts/acceptance_phase3.py

Kịch bản kiểm thử tích hợp đầy đủ không cần LLM, tự assert và exit code 0:
- Check 1: Tool `todo` op='init' với 3 phases tạo checklist, task đầu tiên thành in_progress.
- Check 2: op='done' ở task 1 auto-advance con trỏ sang task 2 của phase 1.
- Check 3: op='block' ở task 2 kèm lý do đánh dấu blocked và advance sang task 1 của phase 2.
- Check 4: Out-of-order completion: hoàn thành task ở phase 3 không làm mất các task đã xong trước đó.
- Check 5: op='unblock' task 2 khôi phục về trạng thái hợp lệ mà không làm hỏng các task khác.
- Check 6: `TodoMiddleware` theo dõi đột biến: gọi edit/write 12 lần kích hoạt should_nudge(), gọi `todo` reset bộ đếm.
- Check 7: Tất cả tasks hoàn thành ('done') -> 0 open tasks.
"""

from __future__ import annotations

import sys
from dino_coding.tools.todo.middleware import TodoMiddleware
from dino_coding.tools.todo.tool import get_todo_tool
from dino_coding.tools.todo.tracker import TodoTracker

FAILURES: list[str] = []


def check(step_no: int, name: str, ok: bool, detail: str = "") -> None:
    mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    print(f"  [{mark}] Check {step_no}: {name}" + (f" — {detail}" if detail and ok else ""))
    if not ok:
        FAILURES.append(f"Check {step_no} - {name}" + (f": {detail}" if detail else ""))


def section(title: str) -> None:
    print(f"\n\033[36m=== {title} ===\033[0m")


def main() -> int:
    section("Kịch bản nghiệm thu E2E Phase 3: Multi-Phase Refactoring Sprint")

    tracker = TodoTracker()
    todo_tool = get_todo_tool(tracker)

    # -------------------------------------------------------------------------
    # Check 1: todo init with 3 phases creates checklist with 1st task in_progress
    # -------------------------------------------------------------------------
    init_res = todo_tool.invoke({
        "op": "init",
        "list": [
            {
                "phase": "Khảo sát & Phân tích",
                "items": ["Audit legacy endpoints", "Document breaking changes"],
            },
            {
                "phase": "Triển khai & Refactor",
                "items": ["Migrate database schema", "Rewrite authentication service"],
            },
            {
                "phase": "Kiểm thử & Bàn giao",
                "items": ["Run integration test suite", "Update deployment runbook"],
            },
        ],
    })

    phases = tracker.phases
    check1_ok = (
        len(phases) == 3
        and phases[0].name == "Khảo sát & Phân tích"
        and phases[0].tasks[0].status == "in_progress"
        and phases[0].tasks[1].status == "pending"
        and phases[1].tasks[0].status == "pending"
        and "Audit legacy endpoints (in progress)" in init_res
    )
    check(
        1,
        "todo tool `init` với 3 phases khởi tạo đúng và task 1 chuyển sang in_progress",
        check1_ok,
        "Phase 1 task 1 là in_progress, các task còn lại là pending",
    )

    # -------------------------------------------------------------------------
    # Check 2: done on task 1 auto-advances con trỏ to task 2 in phase 1
    # -------------------------------------------------------------------------
    done_res = todo_tool.invoke({
        "op": "done",
        "task": "Audit legacy endpoints",
    })

    phases = tracker.phases
    check2_ok = (
        phases[0].tasks[0].status == "completed"
        and phases[0].tasks[1].status == "in_progress"
        and "Audit legacy endpoints" in done_res
        and "Document breaking changes (in progress)" in done_res
    )
    check(
        2,
        "op='done' ở task 1 tự động advance con trỏ sang task 2 trong cùng phase",
        check2_ok,
        "Task 1 completed, Task 2 chuyển thành in_progress",
    )

    # -------------------------------------------------------------------------
    # Check 3: block on task 2 with reason marks it blocked and advances to phase 2 task 1
    # -------------------------------------------------------------------------
    block_res = todo_tool.invoke({
        "op": "block",
        "task": "Document breaking changes",
        "reason": "Chờ spec hoàn chỉnh từ Product Owner",
    })

    phases = tracker.phases
    check3_ok = (
        phases[0].tasks[1].status == "blocked"
        and phases[0].tasks[1].blocker == "Chờ spec hoàn chỉnh từ Product Owner"
        and phases[1].tasks[0].status == "in_progress"
        and "blocked: Chờ spec hoàn chỉnh từ Product Owner" in block_res
        and "Migrate database schema (in progress)" in block_res
    )
    check(
        3,
        "op='block' ở task 2 lưu lý do và auto-advance sang task 1 của phase 2",
        check3_ok,
        "Task 2 blocked kèm reason, Phase 2 Task 1 nhận cờ in_progress",
    )

    # -------------------------------------------------------------------------
    # Check 4: Out-of-order completion: completing task in phase 3 does not erase prior tasks
    # -------------------------------------------------------------------------
    done_p3_res = todo_tool.invoke({
        "op": "done",
        "task": "Update deployment runbook",
    })
    assert "Update deployment runbook" in done_p3_res

    phases = tracker.phases
    t_p3 = next(t for t in phases[2].tasks if t.content == "Update deployment runbook")
    check4_ok = (
        t_p3.status == "completed"
        and phases[0].tasks[0].status == "completed"
        and phases[0].tasks[1].status == "blocked"
        and phases[1].tasks[0].status == "in_progress"
    )
    check(
        4,
        "Hoàn thành task out-of-order ở phase 3 không làm mất trạng thái các task trước",
        check4_ok,
        "Task phase 3 completed, task 1 vẫn completed, task 2 vẫn blocked, active pointer giữ nguyên",
    )

    # -------------------------------------------------------------------------
    # Check 5: unblock task 2 restores it to pending without corrupting other tasks
    # -------------------------------------------------------------------------
    unblock_res = todo_tool.invoke({
        "op": "unblock",
        "task": "Document breaking changes",
    })
    assert "Document breaking changes" in unblock_res

    phases = tracker.phases
    t_p1_2 = phases[0].tasks[1]
    check5_ok = (
        t_p1_2.blocker is None
        and t_p1_2.status in ("pending", "in_progress")
        and phases[0].tasks[0].status == "completed"
        and phases[2].tasks[1].status == "completed"
    )
    check(
        5,
        "op='unblock' task 2 khôi phục trạng thái và xóa sạch blocker",
        check5_ok,
        f"Task 2 blocker=None, status={t_p1_2.status}, các task khác toàn vẹn",
    )

    # -------------------------------------------------------------------------
    # Check 6: TodoMiddleware mutation counter: 12 edits trigger nudge, todo resets
    # -------------------------------------------------------------------------
    middleware = TodoMiddleware(tracker=tracker, mutation_threshold=12)

    # Ban đầu mutation count = 0, should_nudge = False
    initial_nudge = middleware.should_nudge()

    # Thực hiện 11 lần mutation (edit/write)
    for _ in range(11):
        middleware.record_tool_call("edit")
    nudge_at_11 = middleware.should_nudge()

    # Thao tác thứ 12 (write) chạm ngưỡng
    middleware.record_tool_call("write")
    nudge_at_12 = middleware.should_nudge()

    # Gọi tool todo -> counter reset về 0
    middleware.record_tool_call("todo")
    nudge_after_todo = middleware.should_nudge()

    check6_ok = (
        not initial_nudge
        and not nudge_at_11
        and nudge_at_12
        and not nudge_after_todo
        and middleware.consecutive_mutations == 0
    )
    check(
        6,
        "TodoMiddleware theo dõi đột biến: 12 thao tác sửa code kích hoạt nudge, todo reset counter",
        check6_ok,
        "Nudge trigger tại đúng threshold=12 và giải phóng ngay khi gọi todo",
    )

    # -------------------------------------------------------------------------
    # Check 7: All tasks marked done -> 0 open tasks
    # -------------------------------------------------------------------------
    # Hoàn thành tất cả các task còn lại
    remaining_tasks = [
        "Document breaking changes",
        "Migrate database schema",
        "Rewrite authentication service",
        "Run integration test suite",
    ]
    for task_name in remaining_tasks:
        todo_tool.invoke({"op": "done", "task": task_name})

    final_phases = tracker.phases
    all_final_tasks = [t for p in final_phases for t in p.tasks]
    open_tasks = [t for t in all_final_tasks if t.status not in ("completed", "abandoned")]

    final_summary_res = todo_tool.invoke({"op": "view"})

    check7_ok = (
        len(open_tasks) == 0
        and all(t.status == "completed" for t in all_final_tasks)
        and "Overall: 6/6 done, 0 open" in final_summary_res
    )
    check(
        7,
        "Tất cả task hoàn thành -> 0 open tasks, tổng kết 6/6 done",
        check7_ok,
        "Toàn bộ sprint refactor đã hoàn tất không còn sót task nào",
    )

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    section("Kết quả nghiệm thu Phase 3")
    if FAILURES:
        print(f"\033[31mFAIL: {len(FAILURES)} check(s) thất bại!\033[0m")
        for fail in FAILURES:
            print(f"  - {fail}")
        return 1

    print("\033[32mALL 7 CHECKS PASSED — Phase 3 Cognitive Anchor hoạt động hoàn hảo!\033[0m\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
