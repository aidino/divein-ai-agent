import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain.agents.middleware.types import ModelRequest, ModelResponse

from dino_coding.tools.todo.tracker import TodoTracker
from dino_coding.tools.todo.types import TodoParams, InitPhaseInput
from dino_coding.tools.todo.middleware import (
    TodoMiddleware,
    MUTATING_TOOLS,
    DEFAULT_MUTATION_THRESHOLD,
    DEFAULT_MAX_NUDGES_PER_PROMPT,
    MID_RUN_NUDGE_PROMPT,
    COMPLETION_REMINDER_PROMPT,
)


def test_todo_middleware_initialization():
    tracker = TodoTracker()
    middleware = TodoMiddleware(tracker=tracker, mutation_threshold=5, max_nudges_per_prompt=3)
    assert middleware.tracker is tracker
    assert middleware.mutation_threshold == 5
    assert middleware.max_nudges_per_prompt == 3
    assert middleware.consecutive_mutations == 0
    assert middleware.nudges_sent == 0
    assert len(middleware.tools) == 1
    assert middleware.tools[0].name == "todo"

    # Default tracker initialization
    default_middleware = TodoMiddleware()
    assert isinstance(default_middleware.tracker, TodoTracker)
    assert default_middleware.mutation_threshold == DEFAULT_MUTATION_THRESHOLD
    assert default_middleware.max_nudges_per_prompt == DEFAULT_MAX_NUDGES_PER_PROMPT


def test_record_tool_call_and_mutation_tracking():
    middleware = TodoMiddleware(mutation_threshold=3)

    for tool in MUTATING_TOOLS:
        middleware.record_tool_call(tool)
    assert middleware.consecutive_mutations == len(MUTATING_TOOLS)

    # Non-mutating tool like read doesn't increment
    middleware.record_tool_call("read")
    assert middleware.consecutive_mutations == len(MUTATING_TOOLS)

    # todo resets consecutive_mutations
    middleware.record_tool_call("todo")
    assert middleware.consecutive_mutations == 0


def test_should_nudge_and_consume_nudge():
    middleware = TodoMiddleware(mutation_threshold=3, max_nudges_per_prompt=2)

    assert not middleware.should_nudge()
    assert middleware.consume_nudge() is None

    middleware.record_tool_call("edit")
    middleware.record_tool_call("write")
    assert not middleware.should_nudge()

    middleware.record_tool_call("execute")
    assert middleware.should_nudge()

    # First nudge consumed
    nudge = middleware.consume_nudge()
    assert nudge == MID_RUN_NUDGE_PROMPT
    assert middleware.nudges_sent == 1
    assert middleware.consecutive_mutations == 0
    assert not middleware.should_nudge()

    # Reach threshold again
    middleware.record_tool_call("edit")
    middleware.record_tool_call("edit")
    middleware.record_tool_call("edit")
    assert middleware.should_nudge()

    # Second nudge consumed
    nudge2 = middleware.consume_nudge()
    assert nudge2 == MID_RUN_NUDGE_PROMPT
    assert middleware.nudges_sent == 2
    assert middleware.consecutive_mutations == 0

    # Reach threshold 3rd time - should NOT nudge because max_nudges_per_prompt == 2
    middleware.record_tool_call("edit")
    middleware.record_tool_call("edit")
    middleware.record_tool_call("edit")
    assert not middleware.should_nudge()
    assert middleware.consume_nudge() is None


def test_get_open_tasks_count():
    tracker = TodoTracker()
    tracker.execute_op(
        TodoParams(
            op="init",
            list=[
                    InitPhaseInput(
                        phase="Phase 1",
                        items=["Task 1", "Task 2", "Task 3"],
                    )
                ],
            )
    )
    middleware = TodoMiddleware(tracker=tracker)
    assert middleware.get_open_tasks_count() == 3

    # Start task 1 -> still open (in_progress)
    tracker.execute_op(TodoParams(op="start", task="Task 1"))
    assert middleware.get_open_tasks_count() == 3

    # Mark task 1 done -> 2 open
    tracker.execute_op(TodoParams(op="done", task="Task 1"))
    assert middleware.get_open_tasks_count() == 2

    # Drop task 2 -> 1 open
    tracker.execute_op(TodoParams(op="drop", task="Task 2"))
    assert middleware.get_open_tasks_count() == 1

    # Block task 3 -> blocked is not pending or in_progress -> 0 open
    tracker.execute_op(TodoParams(op="block", task="Task 3", reason="blocked reason"))
    assert middleware.get_open_tasks_count() == 0


def test_wrap_model_call_injects_nudge_when_threshold_reached():
    middleware = TodoMiddleware(mutation_threshold=2)

    # Simulate prior messages in request with mutating tool calls
    request_messages = [
        HumanMessage(content="Please edit files"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "edit", "args": {}, "id": "call_1"},
                {"name": "write", "args": {}, "id": "call_2"},
            ],
        ),
        ToolMessage(content="ok", tool_call_id="call_1"),
        ToolMessage(content="ok", tool_call_id="call_2"),
    ]

    request = ModelRequest(
        model=None,  # type: ignore
        messages=request_messages,
    )

    captured_request = None

    def dummy_handler(req: ModelRequest) -> ModelResponse:
        nonlocal captured_request
        captured_request = req
        return ModelResponse(result=[AIMessage(content="done")])

    response = middleware.wrap_model_call(request, dummy_handler)

    assert captured_request is not None
    # SystemMessage nudge should be injected into request.messages
    has_nudge = any(
        isinstance(m, SystemMessage) and m.content == MID_RUN_NUDGE_PROMPT
        for m in captured_request.messages
    )
    assert has_nudge
    assert middleware.nudges_sent == 1
    assert middleware.consecutive_mutations == 0


def test_wrap_model_call_completion_reminder():
    tracker = TodoTracker()
    tracker.execute_op(
        TodoParams(
            op="init",
            list=[
                    InitPhaseInput(
                        phase="Phase 1",
                        items=["Task A", "Task B"],
                    )
                ],
            )
    )
    middleware = TodoMiddleware(tracker=tracker)

    request = ModelRequest(
        model=None,  # type: ignore
        messages=[HumanMessage(content="finish task")],
    )

    # Model finishes (no tool calls) while 2 open tasks remain
    def dummy_handler(req: ModelRequest) -> ModelResponse:
        return ModelResponse(result=[AIMessage(content="All done!")])

    response = middleware.wrap_model_call(request, dummy_handler)
    assert isinstance(response, ModelResponse)
    last_msg = response.result[0]
    assert isinstance(last_msg, AIMessage)
    expected_reminder = COMPLETION_REMINDER_PROMPT.format(count=2)
    assert expected_reminder in last_msg.content
