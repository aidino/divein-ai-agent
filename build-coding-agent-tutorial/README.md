# 🤖 Coding Agent Tutorial V3 — Xây dựng Coding Agent Đỉnh cao với Deep Agents

> Bộ tutorial 10 phần hướng dẫn bạn **tự tay xây dựng** một Coding Agent hoàn chỉnh,
> kế thừa kiến trúc thực chiến từ **`oh-my-pi` (omp)** và sử dụng framework **`deepagents`** (LangChain ecosystem).
> 
> **Đặc điểm nổi bật**: Đầy đủ lý thuyết chuyên sâu, phân tích so sánh thực tế, lệnh cài đặt tường minh, và **mã nguồn mẫu hoàn chỉnh cho từng module nhỏ** để bạn tự tay ráp nối, thử nghiệm và làm chủ công nghệ.
> 
> 📊 **Theo dõi tiến độ học tập & biên soạn**: Xem chi tiết tại [**`PROGRESS.md`**](PROGRESS.md).

---

## 📋 Yêu cầu Môi trường

- Python 3.12+
- `uv` (Trình quản lý package siêu tốc: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Git (cho tính năng cô lập worktree)
- API key của một trong các nhà cung cấp: SiliconFlow (DeepSeek V3/R1), OpenAI, Anthropic, hoặc Google Gemini.

---

## 🗺️ Lộ trình 10 Phases

| Phase | Tài liệu hướng dẫn | Mục tiêu trọng tâm | Cảm hứng từ `oh-my-pi` |
|:---:|:---|:---|:---|
| **00** | [Design Report V3](00_design_report.md) | Báo cáo kiến trúc tổng quan & bản đồ so sánh thực chiến | Toàn cảnh kiến trúc `oh-my-pi` |
| **01** | [Hello Harness & Context Core](phase_01_hello_agent.md) | Khởi tạo Agent Harness, quản lý ngữ cảnh bất biến, stream token v3 | `agent-loop.ts`, `AppendOnlyContext` |
| **02** | [Robust VFS & Hashline Editing](phase_02_file_operations.md) | Phẫu thuật sửa code theo mỏ neo dòng/hash, Smart Read phân trang | `crates/pi-edit`, `read-summary.ts` |
| **02.5**| [Codebase Intelligence](phase_025_codebase_intelligence.md) | Tìm kiếm & refactor cấu trúc code với `ast-grep` và `ast-edit` | `ast-grep.ts`, `ast-edit.ts` |
| **03** | [Cognitive Anchor: Task & Plan](phase_03_task_planning.md) | TodoList phân cấp, tự động nén ngữ cảnh khi vượt ngưỡng 85% | `todo.ts`, `plan-mode/` |
| **04** | [Execution & Loopback Bridge](phase_04_code_execution.md) | Persistent Python REPL sandbox tích hợp cầu nối loopback gọi tool | `eval.ts`, `bash.ts` |
| **05** | [Subagents & Git Worktrees](phase_05_subagents.md) | Điều phối multi-agent trên các Git Worktree độc lập, chống xung đột | `task/worktree.ts`, `structured-subagent.ts` |
| **06** | [IDE Wiring: LSP & Self-Healing](phase_06_ide_wiring_lsp.md) | Bắt diagnostics compiler/linter (`ruff`/`pyright`), tự động sửa lỗi | `lsp/writethrough.ts` |
| **07** | [Safety & Stream Rules (TTSR)](phase_07_safety_ttsr.md) | Time-Traveling Stream Rules, ngắt token nguy hiểm & duyệt HITL | `stream/` TTSR, `approval.ts` |
| **08** | [Dual-Model Advisor & Quality Gate](phase_08_advisor_quality_gate.md) | Model cố vấn độc lập chấm điểm P0-P3 qua RubricMiddleware | `advisor/index.ts`, `review.ts` |
| **09** | [Memory & Production](phase_09_production_memory.md) | Ký ức codebase dài hạn (`retain`/`recall`) và đóng gói CLI hoàn chỉnh | `memories/`, `autolearn/` |

---

## 💡 Phương pháp Học & Thực hành

1. **Học từng Phase một**: Đọc kỹ phần lý thuyết để hiểu tường tận *tại sao* kỹ thuật này ra đời và *cách các agent hàng đầu giải quyết*.
2. **Khảo sát Code mẫu**: Mỗi bài hướng dẫn chia nhỏ mã nguồn thành các module độc lập (`config.py`, `prompt.py`, `agent.py`, `tools/`). Hãy đọc hiểu từng module trước khi tự gõ lại.
3. **Thực hành kiểm thử (Hands-on)**: Chạy kịch bản kiểm thử mẫu ở cuối mỗi phase.
4. **Nghiệm thu**: Đối chiếu với Checklist ở cuối bài. Khi bạn đã hiểu và code chạy trơn tru, hãy chuyển sang phase tiếp theo!
