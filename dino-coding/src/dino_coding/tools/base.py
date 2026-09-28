"""Module định nghĩa các công cụ tùy biến cơ bản cho Agent."""

import platform
import sys
from langchain_core.tools import tool


@tool
def get_environment_info() -> str:
    """Trả về thông tin chi tiết về môi trường runtime hiện tại (Hệ điều hành, phiên bản Python, kiến trúc máy tính).
    
    Sử dụng công cụ này khi cần kiểm tra tương thích môi trường trước khi lập trình.
    """
    return (
        f"OS: {platform.system()} {platform.release()} ({platform.machine()})\n"
        f"Python Version: {sys.version.split()[0]}\n"
        f"Executable: {sys.executable}"
    )


@tool
def echo_code_analysis(code_snippet: str) -> str:
    """Công cụ giả lập phân tích sơ bộ một đoạn code ngắn và đếm số dòng, số ký tự.
    
    Args:
        code_snippet: Chuỗi văn bản chứa mã nguồn cần phân tích.
    """
    lines = code_snippet.splitlines()
    num_lines = len(lines)
    num_chars = len(code_snippet)
    return f"Phân tích hoàn tất: {num_lines} dòng mã, {num_chars} ký tự."


# Danh sách các tools mở đầu cho Phase 1
initial_tools = [get_environment_info, echo_code_analysis]