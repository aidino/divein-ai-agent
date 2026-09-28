from __future__ import annotations

from typing import Any, Callable, Optional, Sequence
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from dino_coding.tools.todo.tracker import TodoTracker
from dino_coding.tools.todo.tool import get_todo_tool

MUTATING_TOOLS: frozenset[str] = frozenset({"edit", "write", "ast_edit", "execute"})
DEFAULT_MUTATION_THRESHOLD = 12
DEFAULT_MAX_NUDGES_PER_PROMPT = 2
MID_RUN_NUDGE_PROMPT = (
    "System reminder: Bạn đã thực hiện nhiều thao tác sửa code liên tiếp mà chưa cập nhật tiến độ. "
    "Hãy dùng `todo` để cập nhật checklist hoặc đánh dấu công việc đã hoàn thành."
)
COMPLETION_REMINDER_PROMPT = (
    "System reminder: Còn {count} công việc chưa hoàn thành trong checklist. "
    "Hãy tiếp tục giải quyết hoặc dùng op `block`/`drop` nếu gặp trở ngại."
)


class TodoMiddleware(AgentMiddleware[Any, Any, Any]):
    """Middleware injecting todo tool, tracking mutations, and enforcing reminder loop."""

    tools: Sequence[BaseTool]

    def __init__(
        self,
        tracker: Optional[TodoTracker] = None,
        mutation_threshold: int = DEFAULT_MUTATION_THRESHOLD,
        max_nudges_per_prompt: int = DEFAULT_MAX_NUDGES_PER_PROMPT,
    ) -> None:
        self.tracker = tracker if tracker is not None else TodoTracker()
        self.mutation_threshold = mutation_threshold
        self.max_nudges_per_prompt = max_nudges_per_prompt
        self.consecutive_mutations: int = 0
        self.nudges_sent: int = 0
        self.tools = [get_todo_tool(self.tracker)]
        self._processed_msg_ids: set[str] = set()
        self._processed_tool_call_ids: set[str] = set()

    def _record_tool_call_once(self, tool_name: str, tool_call_id: Optional[str] = None) -> None:
        """Records a tool call only once based on its ID if available."""
        if tool_call_id:
            if tool_call_id in self._processed_tool_call_ids:
                return
            self._processed_tool_call_ids.add(tool_call_id)
        self.record_tool_call(tool_name)
    def record_tool_call(self, tool_name: str) -> None:
        """Records a tool call to update consecutive mutations counter."""
        if tool_name == "todo":
            self.consecutive_mutations = 0
        elif tool_name in MUTATING_TOOLS:
            self.consecutive_mutations += 1

    def should_nudge(self) -> bool:
        """Determines if a mid-run nudge should be sent."""
        return (
            self.consecutive_mutations >= self.mutation_threshold
            and self.nudges_sent < self.max_nudges_per_prompt
        )

    def consume_nudge(self) -> Optional[str]:
        """Consumes a nudge if eligible, resetting counter and incrementing nudges_sent."""
        if self.should_nudge():
            self.nudges_sent += 1
            self.consecutive_mutations = 0
            return MID_RUN_NUDGE_PROMPT
        return None

    def get_open_tasks_count(self) -> int:
        """Returns count of tasks with status 'pending' or 'in_progress' from tracker."""
        count = 0
        for phase in self.tracker.phases:
            for task in phase.tasks:
                if task.status in ("pending", "in_progress"):
                    count += 1
        return count

    def wrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
    ) -> ModelResponse[Any] | AIMessage:
        """Intercepts model call to track tool calls, inject nudges, and remind open tasks."""
        # Check request.messages for tool calls
        for idx, msg in enumerate(request.messages):
            msg_id = getattr(msg, "id", None) or f"msg_{idx}_{type(msg).__name__}"
            if msg_id in self._processed_msg_ids:
                continue
            self._processed_msg_ids.add(msg_id)

            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                    tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                    if name:
                        self._record_tool_call_once(name, tc_id)

        # Check if we should inject mid-run nudge
        nudge_content = self.consume_nudge()
        current_request = request
        if nudge_content is not None:
            updated_messages = list(request.messages) + [SystemMessage(content=nudge_content)]
            current_request = request.override(messages=updated_messages)

        response = handler(current_request)

        # Inspect response
        ai_msg: Optional[AIMessage] = None
        has_tool_calls = False

        if isinstance(response, ModelResponse):
            for res_msg in response.result:
                if isinstance(res_msg, AIMessage):
                    ai_msg = res_msg
                    if res_msg.tool_calls:
                        has_tool_calls = True
                        for tc in res_msg.tool_calls:
                            name = (
                                tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                            )
                            tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                            if name:
                                self._record_tool_call_once(name, tc_id)
        elif isinstance(response, AIMessage):
            ai_msg = response
            if response.tool_calls:
                has_tool_calls = True
                for tc in response.tool_calls:
                    name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                    tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                    if name:
                        self._record_tool_call_once(name, tc_id)

        # If model is finishing (no tool calls) and tasks remain open, append completion reminder
        if not has_tool_calls:
            open_count = self.get_open_tasks_count()
            if open_count > 0:
                reminder = COMPLETION_REMINDER_PROMPT.format(count=open_count)
                if isinstance(response, ModelResponse) and ai_msg is not None:
                    new_content = f"{ai_msg.content}\n\n{reminder}" if ai_msg.content else reminder
                    new_ai_msg = AIMessage(
                        content=new_content,
                        tool_calls=ai_msg.tool_calls,
                        id=ai_msg.id,
                        additional_kwargs=ai_msg.additional_kwargs,
                        response_metadata=ai_msg.response_metadata,
                    )
                    # Replace ai_msg in result
                    new_result = [
                        new_ai_msg if m is ai_msg else m for m in response.result
                    ]
                    return ModelResponse(
                        result=new_result,
                        structured_response=response.structured_response,
                    )
                elif isinstance(response, AIMessage):
                    new_content = f"{response.content}\n\n{reminder}" if response.content else reminder
                    return AIMessage(
                        content=new_content,
                        tool_calls=response.tool_calls,
                        id=response.id,
                        additional_kwargs=response.additional_kwargs,
                        response_metadata=response.response_metadata,
                    )

        return response
