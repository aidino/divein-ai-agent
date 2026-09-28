"""Entrypoint chính của Coding Agent CLI."""

import sys
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from dino_coding.agent import create_my_coding_agent

console = Console()


def run_interactive_session():
    """Khởi chạy phiên làm việc tương tác qua terminal."""
    console.print(
        Panel.fit(
            "[bold cyan]🤖 Dino Coding Agent — Phase 2: VFS & Hashline[/bold cyan]\n"
            "[dim]Gõ 'exit' hoặc 'quit' để thoát.[/dim]",
            border_style="cyan",
        )
    )

    try:
        agent = create_my_coding_agent()
    except Exception as e:
        console.print(f"[bold red]Lỗi khởi tạo Agent:[/bold red] {e}")
        sys.exit(1)

    # Lưu trữ lịch sử tin nhắn trong session (Append-Only Context)
    messages = []

    while True:
        try:
            user_input = console.input("\n[bold green]Bạn ➔ [/bold green]").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[yellow]Tạm biệt![/yellow]")
                break

            # Nối tin nhắn của người dùng vào context
            messages.append(HumanMessage(content=user_input))

            console.print("[bold blue]Dino Coding Agent đang suy nghĩ...[/bold blue]")

            # Chạy agent với state messages hiện tại
            final_state = agent.invoke({"messages": messages})

            # 1. Xác định các tin nhắn mới sinh ra trong lượt hội thoại này
            new_messages = final_state["messages"][len(messages):]
            messages = final_state["messages"]

            # 2. Duyệt qua các tin nhắn trung gian để hiển thị Tool Calls & Tool Results
            for msg in new_messages[:-1]:
                if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.get("name", "unknown")
                        tool_args = tool_call.get("args", {})
                        args_str = f"({tool_args})" if tool_args else "()"
                        console.print(
                            f"[bold yellow]⚙️  Tool Call:[/bold yellow] [bold cyan]{tool_name}[/bold cyan] [dim]{args_str}[/dim]"
                        )
                elif isinstance(msg, ToolMessage):
                    console.print(f"[bold green]↳ Tool Result:[/bold green] [dim]{msg.content}[/dim]\n")

            # 3. Hiển thị tin nhắn phản hồi cuối cùng của Agent
            if not new_messages:
                console.print("[dim]Agent không phản hồi.[/dim]")
                continue
            ai_message = new_messages[-1]
            console.print("\n[bold magenta]Dino Coding Agent:[/bold magenta]")
            console.print(Markdown(str(ai_message.content)))

        except KeyboardInterrupt:
            console.print("\n[yellow]Đã hủy lượt xử lý hiện tại.[/yellow]")
        except Exception as err:
            console.print(f"[bold red]Đã xảy ra lỗi:[/bold red] {err}")


if __name__ == "__main__":
    run_interactive_session()
