from __future__ import annotations

import re
from dino_coding.tools.todo.types import TodoItem, TodoPhase, TodoStatus

STATUS_TO_MARKER: dict[TodoStatus, str] = {
    "pending": " ",
    "in_progress": "/",
    "completed": "x",
    "abandoned": "-",
    "blocked": "!",
}

MARKER_TO_STATUS: dict[str, TodoStatus] = {
    " ": "pending",
    "": "pending",
    "x": "completed",
    "X": "completed",
    "/": "in_progress",
    ">": "in_progress",
    "-": "abandoned",
    "~": "abandoned",
    "!": "blocked",
}

# Regex to match task items like:
# - [ ] task description <!-- blocker: reason -->
# Supports -, *, + bullet points, leading indentation, escaped brackets \[ \], empty brackets [].
TASK_PATTERN = re.compile(
    r"^\s*[-*+]\s*\\?\[\s*(.*?)\s*\\?\]\s+(.*?)\s*$"
)

# Regex to extract trailing HTML blocker comment: <!-- blocker: <reason> -->
BLOCKER_COMMENT_PATTERN = re.compile(
    r"\s*<!--\s*blocker:\s*(.*?)\s*-->\s*$"
)

# Regex to match heading lines like: # Phase Name
HEADING_PATTERN = re.compile(r"^\s*#+\s*(.*?)\s*$")


def phases_to_markdown(phases: list[TodoPhase]) -> str:
    """Serializes a list of TodoPhase into markdown checklist format."""
    if not phases:
        return "# Todos\n"

    sections: list[str] = []
    for phase in phases:
        lines: list[str] = [f"# {phase.name}"]
        for task in phase.tasks:
            marker = STATUS_TO_MARKER.get(task.status, " ")
            line = f"- [{marker}] {task.content}"
            if task.status == "blocked" and task.blocker:
                line += f" <!-- blocker: {task.blocker} -->"
            lines.append(line)
        sections.append("\n".join(lines))

    return "\n\n".join(sections) + "\n"


def markdown_to_phases(md: str) -> tuple[list[TodoPhase], list[str]]:
    """Parses markdown checklist format into a list of TodoPhase and any errors."""
    phases: list[TodoPhase] = []
    errors: list[str] = []

    current_phase: TodoPhase | None = None

    for line_num, line in enumerate(md.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        # Check for task first, since indented headings are rare but task regex is specific
        task_match = TASK_PATTERN.match(line)
        if task_match:
            marker = task_match.group(1)
            raw_content = task_match.group(2)

            blocker: str | None = None
            blocker_match = BLOCKER_COMMENT_PATTERN.search(raw_content)
            if blocker_match:
                blocker = blocker_match.group(1)
                content = BLOCKER_COMMENT_PATTERN.sub("", raw_content).strip()
            else:
                content = raw_content.strip()

            if marker in MARKER_TO_STATUS:
                status = MARKER_TO_STATUS[marker]
            else:
                status = "pending"
                errors.append(f"Line {line_num}: Unknown status marker '{marker}', defaulted to 'pending'")

            item = TodoItem(content=content, status=status, blocker=blocker)

            if current_phase is None:
                current_phase = TodoPhase(name="Tasks")
                phases.append(current_phase)

            current_phase.tasks.append(item)
            continue

        # Check for heading
        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            heading_text = heading_match.group(1)
            current_phase = TodoPhase(name=heading_text)
            phases.append(current_phase)
            continue

    return phases, errors
