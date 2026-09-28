"""Module khởi tạo và đóng gói Agent Harness với Deep Agents."""

import os

from deepagents import HarnessProfile, create_deep_agent, register_harness_profile
from deepagents.backends import FilesystemBackend
from langgraph.graph.state import CompiledStateGraph

from dino_coding.config import config
from dino_coding.prompt import build_coding_system_prompt
from dino_coding.tools.base import initial_tools
from dino_coding.tools.ast_tools import ast_tools
from dino_coding.tools.editor import edit
from dino_coding.tools.fs import file_tools
from dino_coding.tools.todo import TodoMiddleware

def _get_workspace_root() -> str:
    """Workspace root dùng chung bởi cả custom tools lẫn deepagents backend."""
    return os.getenv("DINO_WORKSPACE", os.path.join(os.getcwd(), "workspace"))


# Loại bỏ built-in read_file/write_file/edit_file/delete vì custom hashline
# tools đã thay thế. Giữ ls/glob/grep/execute làm công cụ bổ trợ.
# Profile đăng ký một lần trước khi tạo agent.
_EXCLUDED_BUILTINS = frozenset({"read_file", "write_file", "edit_file", "delete"})


def create_my_coding_agent() -> CompiledStateGraph:
    """Khởi tạo Deep Agent với bộ tool VFS Phase 2.

    - Custom tools (read, write, edit): hashline engine tự xây.
    - Built-in tools (ls, glob, grep, execute): giữ lại từ deepagents
      để agent có khả năng tìm kiếm/chạy lệnh.
    - Built-in read_file/write_file/edit_file/delete: loại bỏ vì trùng
      chức năng và không có bảo vệ hashline.
    """
    llm = config.get_llm()
    system_prompt = build_coding_system_prompt()
    workspace_root = _get_workspace_root()

    # Backend trỏ đúng workspace root, virtual_mode=False để
    # ls/glob/grep thao tác trên ổ đĩa thật
    backend = FilesystemBackend(root_dir=workspace_root, virtual_mode=False)
    todo_middleware = TodoMiddleware()

    agent: CompiledStateGraph = create_deep_agent(
        model=llm,
        tools=[*initial_tools, *file_tools, edit, *ast_tools],
        system_prompt=system_prompt,
        middleware=[todo_middleware],
        backend=backend,
    )
    return agent


# Đăng ký profile loại bỏ built-in file tools cho mọi provider.
# Phải chạy TRƯỚC create_deep_agent() — module-level đảm bảo điều này.
for _provider in ("openai", "anthropic", "google_genai", "deepseek"):
    register_harness_profile(
        _provider,
        HarnessProfile(excluded_tools=_EXCLUDED_BUILTINS),
    )
