"""Module khởi tạo và đóng gói Agent Harness với Deep Agents."""

from deepagents import create_deep_agent
from langgraph.graph.state import CompiledStateGraph
from dino_coding.config import config
from dino_coding.prompt import build_coding_system_prompt
from dino_coding.tools.base import initial_tools


def create_my_coding_agent() -> CompiledStateGraph:
    """Khởi tạo một instance Deep Agent hoàn chỉnh với cấu hình và công cụ Phase 1."""
    # 1. Lấy LLM instance chuẩn hóa
    llm = config.get_llm()

    # 2. Xây dựng prompt nền tảng
    system_prompt = build_coding_system_prompt()

    # 3. Tạo Deep Agent thông qua API cấp cao
    # create_deep_agent tự động gắn kèm các middleware quản lý context và tool loop
    agent: CompiledStateGraph = create_deep_agent(
        model=llm,
        tools=initial_tools,
        system_prompt=system_prompt,
    )

    return agent
