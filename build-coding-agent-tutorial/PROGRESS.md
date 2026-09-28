# 📊 Tiến độ Học tập & Biên soạn: Coding Agent Tutorial (V3 — oh-my-pi Standard)

> **Mục đích**: Theo dõi tiến độ biên soạn của trợ lý, tiến độ tự code và nghiệm thu của bạn, đồng thời lưu trữ lại toàn bộ các quyết định kiến trúc và góp ý quan trọng qua từng bài học để tránh trôi ngữ cảnh.

---

## 🧭 Nguyên tắc Làm việc Đồng hành

1. **Một phase tại một thời điểm**: Trợ lý chỉ biên soạn bài tiếp theo sau khi bạn đã thực hành xong bài hiện tại và xác nhận nghiệm thu.
2. **Framework duy nhất**: Chỉ dùng **`deepagents`** (LangChain ecosystem, Python 3.12+, `uv`).
3. **Chuẩn hóa 100% theo `oh-my-pi`**:
   - Cái gì dùng lại được ➔ Hướng dẫn tích hợp trực tiếp (`ast-grep`, `git worktree`, Language Server `pyright`/`ruff`).
   - Cái gì cần chuyển ngữ ➔ Hướng dẫn porting sang Python (Hashline edit engine từ `crates/pi-edit`, Persistent REPL loopback từ `eval.ts`, Time-Traveling Stream Rules từ `stream/`).
   - Loại bỏ 100% LightRAG và các khái niệm cũ không liên quan.
4. **Code mẫu hoàn chỉnh từng module nhỏ**: Đầy đủ code, có type hints, docstring và giải thích lý do thiết kế để bạn tự tay ráp nối và làm chủ.

---

## 📌 Bảng Tổng hợp Tiến độ 10 Phase

| Phase | Tên Phase & Cảm hứng từ `oh-my-pi` | Tài liệu Hướng dẫn | Biên soạn | Học tập & Code | Ghi chú & Trọng tâm Kỹ thuật |
|:---:|:---|:---|:---:|:---:|:---|
| **00** | **Design Architecture V3.1** | [`00_design_report.md`](00_design_report.md) | ✅ Hoàn thành | ✅ Đã duyệt | Bản đặc tả kiến trúc chuẩn, phân loại Reuse vs Porting. |
| **01** | **Hello Harness & Context Core**<br>*(từ `agent-loop.ts`, `append-only-context.ts`)* | [`phase_01_hello_agent.md`](phase_01_hello_agent.md) | ✅ Hoàn thành | 🟡 **Đang học** | Khởi tạo Deep Agent, quản lý tin nhắn Append-Only, stream token v3 qua Rich CLI. |
| **02** | **Robust VFS & Hashline Editing**<br>*(từ `crates/pi-edit`, `read-summary.ts`)* | `phase_02_file_operations.md` | ⏳ Chờ Phase 1 | ⚪ Chưa bắt đầu | Porting engine mỏ neo dòng/hash từ Rust sang Python; Smart Read phân trang & tóm tắt. |
| **02.5**| **Codebase Intelligence với ast-grep**<br>*(từ `ast-grep.ts`, `ast-edit.ts`)* | `phase_025_codebase_intelligence.md` | ⏳ Chờ Phase 2 | ⚪ Chưa bắt đầu | Tích hợp `ast-grep` (`sg`) / `ast-grep-py` để search và refactor code theo cú pháp AST. (Bỏ LightRAG). |
| **03** | **Cognitive Anchor: Task & Plan**<br>*(từ `todo.ts`, `compaction.ts`)* | `phase_03_task_planning.md` | ⏳ Chờ | ⚪ Chưa bắt đầu | `TodoListMiddleware` phân cấp + `SummarizationMiddleware` tự nén ngữ cảnh khi đạt 85% token window. |
| **04** | **Execution Engine & Loopback Bridge**<br>*(từ `eval.ts`, `src/eval/py/runner.py`)* | `phase_04_code_execution.md` | ⏳ Chờ | ⚪ Chưa bắt đầu | Persistent Python REPL chạy ngầm (NDJSON) có IPC loopback cho phép script test gọi lại tool Agent. |
| **05** | **Subagents & Git Worktree Isolation**<br>*(từ `task/worktree.ts`, `structured-subagent.ts`)* | `phase_05_subagents.md` | ⏳ Chờ | ⚪ Chưa bắt đầu | Cấp Git Worktree riêng cho từng subagent, triệt tiêu xung đột ghi đè code, trả về Structured JSON. |
| **06** | **IDE Wiring: LSP & Self-Healing**<br>*(từ `lsp/writethrough.ts`)* | `phase_06_ide_wiring_lsp.md` | ⏳ Chờ | ⚪ Chưa bắt đầu | Bắt diagnostics từ compiler/linter (`ruff`/`pyright`) ngay sau khi ghi file để Agent tự sửa lỗi. |
| **07** | **Safety & Stream Rules (TTSR)**<br>*(từ `stream/` TTSR, `approval.ts`)* | `phase_07_safety_ttsr.md` | ⏳ Chờ | ⚪ Chưa bắt đầu | Quét regex trên stream realtime, ngắt token nguy hiểm, chèn luật phạt và duyệt Human-in-the-Loop. |
| **08** | **Dual-Model Advisor & Quality Gate**<br>*(từ `advisor/index.ts`, `review.ts`)* | `phase_08_advisor_quality_gate.md` | ⏳ Chờ | ⚪ Chưa bắt đầu | Model cố vấn thứ 2 chạy song song chấm điểm rủi ro P0-P3 và thẩm định diff qua Rubric. |
| **09** | **Continuous Learning & Production**<br>*(từ `memories/index.ts`)* | `phase_09_production_memory.md` | ⏳ Chờ | ⚪ Chưa bắt đầu | Bộ ba công cụ `retain` - `learn` - `recall`, lưu trữ ký ức dự án dài hạn xuyên suốt các phiên làm việc. |

*Chú thích trạng thái:*  
* ✅ **Hoàn thành / Đã duyệt**: Đã hoàn tất và được nghiệm thu.  
* 🟡 **Đang học / Đang xử lý**: Trọng tâm công việc ở thời điểm hiện tại.  
* ⏳ **Chờ**: Sẽ biên soạn tuần tự ngay khi phase trước hoàn tất.  
* ⚪ **Chưa bắt đầu**: Chưa triển khai.

---

## 📝 Nhật ký Góp ý & Quyết định Kiến trúc (Decision Log)

| Ngày | Quyết định / Góp ý từ bạn | Hành động & Thay đổi tương ứng | Trạng thái |
|:---:|:---|:---|:---:|
| **28/09/2026** | **Quyết định 1**: Bổ sung 2 phase trọng tâm: *IDE Wiring (LSP & Self-Healing)* và *Git Worktree Isolation cho Subagents*. | Tách lộ trình thành 10 Phase độc lập, phản ánh đúng các đột phá thực tế của `oh-my-pi`. | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 2**: Cung cấp code mẫu hoàn chỉnh cho từng module nhỏ để bạn tự tay ráp nối và debug. | Quy chuẩn hóa mỗi bài tutorial gồm 6 phần với code mẫu từng file (`config.py`, `prompt.py`, `agent.py`, v.v.). | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 3**: Môi trường mặc định là Python 3.12+ và `uv`, không mở rộng thêm ngôn ngữ khác tránh phức tạp. | Chuẩn hóa toàn bộ stack thực hành trên Python, `ruff`, `pyright`, `pytest`. | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 4**: Bỏ hoàn toàn LightRAG/AgentSeek; giữ duy nhất `deepagents`; tất cả công cụ còn lại chuẩn hóa 100% theo `oh-my-pi` (chỉ rõ Reuse vs Porting). | Viết lại `00_design_report.md` V3.1: thay LightRAG bằng `ast-grep` / `ast-edit`, bổ sung bảng phân loại Reuse vs Porting cho từng tool. | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 5**: Tạo file tiến độ tổng thể (`PROGRESS.md`) để theo dõi xuyên suốt, học xong phase nào mới viết phase tiếp theo. | Khởi tạo file `PROGRESS.md`, cập nhật link từ `README.md`, sẵn sàng cập nhật sau mỗi buổi học. | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 6**: Chuẩn hóa chữ ký Type-safe LangChain 1.x cho `src/config.py` (`SecretStr`, `max_completion_tokens`, `cast(ProviderType)`). | Kiểm chứng qua Pyright 1.1.414 (0 errors, 0 warnings); cập nhật mã nguồn mẫu và bổ sung callout gỡ lỗi type trong `phase_01_hello_agent.md`. | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 7**: Khắc phục lỗi build `pyproject.toml` bằng cách cấu hình `[tool.uv] package = false`. | Xác định dự án là standalone CLI application, không cần đóng gói wheel; `uv sync` giải quyết 0 error, 0 warning; cập nhật hướng dẫn trong `phase_01_hello_agent.md`. | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 8**: Loại bỏ rò rỉ ngữ cảnh bài học (Tutorial Meta-Leakage) trong `src/prompt.py`. | Xóa câu "Hiện tại bạn đang ở Phase 1...", thay bằng 3 trụ cột kỹ thuật phần mềm chuẩn mực từ `oh-my-pi` (Engineering Rules, Tool Discipline, Completeness Contract). | ✅ Đã áp dụng |

---

## 🎯 Sprint Hiện tại: Phase 1 — Hello Harness & Context Core

* **Tài liệu học tập**: [`phase_01_hello_agent.md`](phase_01_hello_agent.md)
* **Mục tiêu của bạn**:
  1. Khởi tạo project với `uv init` và cài đặt `deepagents`, `langchain-openai`, `rich`.
  2. Tạo 5 module: `src/config.py`, `src/prompt.py`, `src/tools/base.py`, `src/agent.py`, `src/main.py`.
  3. Chạy lệnh `uv run python src/main.py` và kiểm tra 3 kịch bản: Tool Calling tự động, Phân tích mã, và Trí nhớ ngữ cảnh Append-Only.
* **Ghi nhận phản hồi sau khi hoàn thành**:
  *(Sẽ được điền sau khi bạn thực hành xong Phase 1 và chia sẻ kết quả hoặc góp ý)*
