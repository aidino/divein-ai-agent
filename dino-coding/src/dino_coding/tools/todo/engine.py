from __future__ import annotations

import re
from typing import Optional

from dino_coding.tools.todo.types import (
    InitPhaseInput,
    TodoItem,
    TodoParams,
    TodoPhase,
)

DEFAULT_INIT_PHASE = "Tasks"


def clone_task(task: TodoItem) -> TodoItem:
    return TodoItem(content=task.content, status=task.status, blocker=task.blocker)


def clone_phases(phases: list[TodoPhase]) -> list[TodoPhase]:
    return [
        TodoPhase(name=phase.name, tasks=[clone_task(t) for t in phase.tasks])
        for phase in phases
    ]


def find_task_by_content(
    phases: list[TodoPhase], content: str
) -> Optional[tuple[TodoItem, TodoPhase]]:
    for phase in phases:
        for task in phase.tasks:
            if task.content == content:
                return task, phase
    return None


def find_phase_by_name(phases: list[TodoPhase], name: str) -> Optional[TodoPhase]:
    for phase in phases:
        if phase.name == name:
            return phase
    return None


def normalize_in_progress(phases: list[TodoPhase]) -> None:
    ordered_tasks = [task for phase in phases for task in phase.tasks]
    if not ordered_tasks:
        return

    in_progress_tasks = [t for t in ordered_tasks if t.status == "in_progress"]
    if len(in_progress_tasks) > 1:
        for task in in_progress_tasks[1:]:
            task.status = "pending"

    if in_progress_tasks:
        return

    first_pending = next((t for t in ordered_tasks if t.status == "pending"), None)
    if first_pending:
        first_pending.status = "in_progress"


def resolve_task_or_error(
    phases: list[TodoPhase], content: Optional[str], errors: list[str]
) -> Optional[tuple[TodoItem, TodoPhase]]:
    if not content:
        errors.append("Missing task content")
        return None
    hit = find_task_by_content(phases, content)
    if not hit:
        if re.match(r"^task-\d+$", content):
            errors.append(
                f'Task "{content}" not found. Tasks are referenced by content, '
                "not by IDs — pass the task's full text from the previous result."
            )
        else:
            total_tasks = sum(len(p.tasks) for p in phases)
            hint = " (todo list is empty — was it replaced or not yet created?)" if total_tasks == 0 else ""
            errors.append(f'Task "{content}" not found{hint}')
        return None
    return hit


def resolve_phase_or_error(
    phases: list[TodoPhase], name: Optional[str], errors: list[str]
) -> Optional[TodoPhase]:
    if not name:
        errors.append("Missing phase name")
        return None
    phase = find_phase_by_name(phases, name)
    if not phase:
        errors.append(f'Phase "{name}" not found')
        return None
    return phase


def get_task_targets(
    phases: list[TodoPhase], entry: TodoParams, errors: list[str]
) -> list[TodoItem]:
    if entry.task:
        hit = resolve_task_or_error(phases, entry.task, errors)
        return [hit[0]] if hit else []
    if entry.phase:
        phase = resolve_phase_or_error(phases, entry.phase, errors)
        return list(phase.tasks) if phase else []
    return [task for phase in phases for task in phase.tasks]


def init_phases(entry: TodoParams, errors: list[str]) -> list[TodoPhase]:
    raw_list = entry.list
    if not raw_list and entry.items:
        raw_list = [InitPhaseInput(phase=entry.phase or DEFAULT_INIT_PHASE, items=entry.items)]
    if not raw_list:
        errors.append("Missing list for init operation")
        return []

    seen_phases: set[str] = set()
    seen_tasks: set[str] = set()
    result: list[TodoPhase] = []

    for list_entry in raw_list:
        if list_entry.phase in seen_phases:
            errors.append(f'Duplicate phase "{list_entry.phase}" in init list')
        seen_phases.add(list_entry.phase)

        phase_tasks: list[TodoItem] = []
        for content in list_entry.items:
            if content in seen_tasks:
                errors.append(f'Duplicate task "{content}" in init list')
            seen_tasks.add(content)
            phase_tasks.append(TodoItem(content=content, status="pending"))
        result.append(TodoPhase(name=list_entry.phase, tasks=phase_tasks))
    return result


def append_items(
    phases: list[TodoPhase], entry: TodoParams, errors: list[str]
) -> list[TodoPhase]:
    if not entry.phase:
        errors.append("Missing phase name for append operation")
        return phases
    if not entry.items:
        errors.append("Missing items for append operation")
        return phases

    seen: set[str] = set()
    has_duplicate = False
    for content in entry.items:
        if content in seen or find_task_by_content(phases, content):
            errors.append(f'Task "{content}" already exists')
            has_duplicate = True
        seen.add(content)

    if has_duplicate:
        return phases

    phase = find_phase_by_name(phases, entry.phase)
    if not phase:
        phase = TodoPhase(name=entry.phase, tasks=[])
        phases.append(phase)

    for content in entry.items:
        phase.tasks.append(TodoItem(content=content, status="pending"))
    return phases


def remove_tasks(
    phases: list[TodoPhase], entry: TodoParams, errors: list[str]
) -> list[TodoPhase]:
    if entry.task:
        hit = resolve_task_or_error(phases, entry.task, errors)
        if not hit:
            return phases
        task, phase = hit
        phase.tasks = [t for t in phase.tasks if t != task]
        return phases
    if entry.phase:
        phase = resolve_phase_or_error(phases, entry.phase, errors)
        if not phase:
            return phases
        phase.tasks = []
        return phases
    for p in phases:
        p.tasks = []
    return phases


def apply_entry(
    phases: list[TodoPhase], entry: TodoParams, errors: list[str]
) -> list[TodoPhase]:
    op = entry.op
    if op == "init":
        return init_phases(entry, errors)
    elif op == "start":
        hit = resolve_task_or_error(phases, entry.task, errors)
        if not hit:
            return phases
        target_task, _ = hit
        for phase in phases:
            for candidate in phase.tasks:
                if candidate.status == "in_progress" and candidate != target_task:
                    candidate.status = "pending"
        target_task.status = "in_progress"
        return phases
    elif op == "done":
        for task in get_task_targets(phases, entry, errors):
            task.status = "completed"
        return phases
    elif op == "drop":
        for task in get_task_targets(phases, entry, errors):
            task.status = "abandoned"
        return phases
    elif op == "block":
        if not entry.task and not entry.phase:
            errors.append("block requires a task or phase target")
            return phases
        reason = re.sub(r"\s+", " ", entry.reason.strip()) if entry.reason else None
        for task in get_task_targets(phases, entry, errors):
            if task.status not in ("pending", "in_progress", "blocked"):
                continue
            task.status = "blocked"
            task.blocker = reason
        return phases
    elif op == "unblock":
        if not entry.task and not entry.phase:
            errors.append("unblock requires a task or phase target")
            return phases
        for task in get_task_targets(phases, entry, errors):
            if task.status == "blocked":
                task.status = "pending"
                task.blocker = None
        return phases
    elif op == "rm":
        return remove_tasks(phases, entry, errors)
    elif op == "append":
        return append_items(phases, entry, errors)
    elif op == "view":
        return phases
    else:
        errors.append(f'Unknown operation "{op}"')
        return phases


def apply_ops(
    current_phases: list[TodoPhase], entry: TodoParams
) -> tuple[list[TodoPhase], list[str]]:
    errors: list[str] = []
    next_phases = clone_phases(current_phases)
    next_phases = apply_entry(next_phases, entry, errors)
    if not errors and entry.op != "view":
        normalize_in_progress(next_phases)
    return next_phases, errors


def format_summary(phases: list[TodoPhase], errors: list[str], read_only: bool = False) -> str:
    if errors:
        return "Errors encountered:\n" + "\n".join(f"- {e}" for e in errors)
    if not phases:
        return "Todo list is empty."

    all_tasks = [t for p in phases for t in p.tasks]
    if not all_tasks:
        return "Todo list is empty."

    closed_all = sum(1 for t in all_tasks if t.status in ("completed", "abandoned"))
    blocked_all = sum(1 for t in all_tasks if t.status == "blocked")
    open_all = len(all_tasks) - closed_all

    # Locate earliest phase with open tasks
    current_idx = 0
    for idx, p in enumerate(phases):
        if any(t.status not in ("completed", "abandoned") for t in p.tasks):
            current_idx = idx
            break

    current = phases[current_idx]
    done_current = sum(1 for t in current.tasks if t.status in ("completed", "abandoned"))

    lines: list[str] = []
    blocked_suffix = f", {blocked_all} blocked" if blocked_all > 0 else ""
    lines.append(f"Overall: {closed_all}/{len(all_tasks)} done, {open_all} open{blocked_suffix}.")
    lines.append(f'Active phase {current_idx + 1}/{len(phases)} "{current.name}" ({done_current}/{len(current.tasks)}).')

    for phase in phases:
        lines.append(f"  {phase.name}:")
        for task in phase.tasks:
            checkbox = "[X]" if task.status == "completed" else "[ ]"
            tag = ""
            if task.status == "in_progress":
                tag = " (in progress)"
            elif task.status == "abandoned":
                tag = " (dropped)"
            elif task.status == "blocked":
                tag = f" (blocked: {task.blocker})" if task.blocker else " (blocked)"
            lines.append(f"    - {checkbox} {task.content}{tag}")

    return "\n".join(lines)
