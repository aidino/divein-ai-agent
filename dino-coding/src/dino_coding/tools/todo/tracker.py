from __future__ import annotations

from dino_coding.tools.todo.engine import apply_ops, clone_phases, format_summary
from dino_coding.tools.todo.markdown import markdown_to_phases, phases_to_markdown
from dino_coding.tools.todo.types import TodoParams, TodoPhase


class TodoTracker:
    """In-memory state manager that holds the canonical todo state for an agent session."""

    def __init__(self) -> None:
        self._phases: list[TodoPhase] = []

    @property
    def phases(self) -> list[TodoPhase]:
        """Returns a defensive clone of the internal phases."""
        return clone_phases(self._phases)

    def set_phases(self, phases: list[TodoPhase]) -> None:
        """Sets internal phases to a defensive clone of the provided phases."""
        self._phases = clone_phases(phases)

    def execute_op(self, params: TodoParams) -> tuple[str, bool]:
        """Executes a todo operation.

        Returns (summary, error_occurred).
        Rolls back (leaves state unchanged) on error.
        """
        updated_phases, errors = apply_ops(self._phases, params)
        if errors:
            return format_summary(self._phases, errors), True

        if params.op != "view":
            self._phases = updated_phases

        return format_summary(self._phases, []), False

    def to_markdown(self) -> str:
        """Serializes current phases to markdown format."""
        return phases_to_markdown(self._phases)

    def from_markdown(self, md: str) -> list[str]:
        """Parses markdown into phases. Updates state only if no errors occur."""
        phases, errors = markdown_to_phases(md)
        if not errors:
            self._phases = phases
        return errors

    def reset(self) -> None:
        """Clears all todo state."""
        self._phases = []
