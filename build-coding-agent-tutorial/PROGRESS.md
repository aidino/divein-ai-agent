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
| **01** | **Hello Harness & Context Core**<br>*(từ `agent-loop.ts`, `append-only-context.ts`)* | [`phase_01_hello_agent.md`](phase_01_hello_agent.md) | ✅ Hoàn thành | ✅ **Đã hoàn thành** | Khởi tạo Deep Agent, quản lý tin nhắn Append-Only, stream token v3 qua Rich CLI. |
| **02** | **Robust VFS & Hashline Editing**<br>*(từ `crates/pi-edit`, `read-summary.ts`)* | [`phase_02_file_operations.md`](phase_02_file_operations.md) | ✅ Hoàn thành | 🟡 **Đang học** | Porting engine mỏ neo dòng/hash từ Rust sang Python; Smart Read phân trang & tóm tắt. Code mẫu đã kiểm chứng 11/11 unit test + E2E (read→edit→stale-guard→CRLF). |
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
| **28/09/2026** | **Quyết định 9**: Chuẩn hóa kiến trúc gói theo `src-layout` (`src/dino_coding/`) và cấu hình `[project.scripts] dino-coding`. | Cập nhật cấu trúc thư mục, code mẫu và lệnh gọi trực tiếp `uv run dino-coding` trong `phase_01_hello_agent.md`. | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 10**: Hiển thị trực quan Tool Call và Tool Result trên CLI (khắc phục điểm mù tool execution). | Cập nhật `src/dino_coding/main.py` để bóc tách `AIMessage(tool_calls)` và `ToolMessage(content)` từ state messages, giúp người dùng quan sát minh bạch toàn bộ quá trình Agent gọi công cụ. | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 11**: Đặt engine port trong package con `src/dino_coding/tools/hashline/` phản chiếu 1-1 cấu trúc crate `pi-edit` (text/types/store/messages/tokenizer/input/parser/apply/patcher), còn `tools/editor.py` chỉ là tool wrapper (tương đương `EditTool` của omp). | Áp dụng trong `phase_02_file_operations.md` mục 2 & 4; người học đối chiếu từng file Python với file Rust tương ứng khi debug. | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 12**: Phân cấp phạm vi porting Phase 2 — Port 100% (file_hash xxh32, EditStore snapshot/clipboard/no-op, tokenizer/parser PUT-CUT-REM-MV + `@register`, materialize, seen-lines guard, mismatch diagnostics, path policy); Điều chỉnh (read tool dùng JSON args `path/offset/limit` thay selector inline, outline summary heuristic regex thay tree-sitter, preview `±N|` qua difflib); Defer (block ops `N*` trả lỗi `BLOCK_RESOLVER_UNAVAILABLE` trung thực như omp khi thiếu resolver, boundary/landing repair, streaming preview, fuzzy recovery). | Bảng phân loại chi tiết ở mục 1.3 của `phase_02_file_operations.md`; các mục defer ghi rõ điều kiện nâng cấp ở mục 8 (block resolver sẽ tái sử dụng ast-grep ở Phase 2.5). | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 13**: Toàn bộ chuỗi model-facing (tool description, error, warning) giữ nguyên tiếng Anh chuẩn oh-my-pi vì các model được huấn luyện trên chuỗi gốc; tiếng Việt chỉ dùng cho prose tutorial và CLI hiển thị. | Code mẫu trong `phase_02_file_operations.md` (module `messages.py` port nguyên văn `messages.rs` + `mismatch.rs`). | ✅ Đã áp dụng |
| **28/09/2026** | **Quyết định 14**: Kiểm chứng code mẫu tutorial bằng thực thi thật trước khi bàn giao: trích 14 module + 11 unit test từ tài liệu, chạy bằng venv của dự án → 11/11 pass, E2E read→edit→tag-chaining→stale-reject→unseen-guard→CRLF-restore đều đúng; phát hiện và sửa 4 lỗi trong bản nháp (thiếu import `target_register`, rich markup nuốt header `[path#TAG]`, universal newlines phá detect CRLF, block code markdown bị fence nội bộ cắt sớm → đổi sang fence 4-backtick). | Quy chuẩn mới: mọi phase sau biên soạn xong phải qua vòng "extract & run" tương tự trước khi giao. | ✅ Đã áp dụng |

---

## 🎯 Sprint Trước: Phase 1 — Hello Harness & Context Core (✅ Hoàn thành)

* **Tài liệu học tập**: [`phase_01_hello_agent.md`](phase_01_hello_agent.md)
* **Trạng thái thực hành**: Đã chạy thành công 3/3 kịch bản kiểm thử trên provider `zai`.
* **Ghi nhận phản hồi thực tế từ bạn**:
  1. *Test 1 (Environment Info Tool)*: ✅ Thành công. Agent tự gọi tool và trả về đúng thông số hệ điều hành Linux kernel 7.0, Python 3.12.13 trong virtualenv `.venv`.
  2. *Test 2 (Code Analysis Tool)*: ✅ Logic thành công (kết quả 2 dòng, 31 ký tự do tool trả về). Cải tiến bóc tách `AIMessage.tool_calls` và `ToolMessage.content` vào `src/dino_coding/main.py`.
  3. *Test 3 (Append-Only Context Memory)*: ✅ Thành công. Agent truy xuất chính xác ngữ cảnh câu hỏi và kết quả phân tích ở lượt trước.
  4. *Cấu trúc dự án*: Chuẩn hóa theo `src-layout` (`src/dino_coding/`), kích hoạt `[project.scripts] dino-coding` chạy trực tiếp bằng `uv run dino-coding`.

---

## 🎯 Sprint Hiện tại: Phase 2 — Robust VFS & Hashline Editing (🟡 Đang học)

* **Tài liệu hướng dẫn**: [`phase_02_file_operations.md`](phase_02_file_operations.md) — ✅ đã biên soạn và kiểm chứng code mẫu (11/11 unit test + E2E read→edit→guard).
* **Mục tiêu kỹ thuật**:
  1. **Porting Hashline Editing Engine**: Chuyển giao giải pháp mỏ neo dòng/hash từ Rust (`crates/pi-edit`) sang Python (`src/dino_coding/tools/hashline/` + `tools/editor.py`), giải quyết triệt để lỗi hallucinatory line number và stale-edit khi sửa code.
  2. **Smart Read Tool**: Công cụ đọc file thông minh có phân trang (`offset`/`limit`), header snapshot `[path#TAG]`, dòng `N:TEXT` và outline summary heuristic cho file lớn (lấy cảm hứng từ `read-summary.ts`).
  3. **Tích hợp vào Agent**: Nối `read`/`write`/`edit` vào `create_deep_agent`, cập nhật System Prompt (không meta-leakage) và kiểm thử 3 kịch bản terminal `uv run dino-coding` (Smart Read mint tag → Edit chuẩn → Stale tag self-healing).
* **Lộ trình tự học trong tài liệu**: Lý thuyết 3 bệnh của `str_replace` → dựng 13 module nhỏ (mỗi module gắn file Rust gốc để đối chiếu) → `uv run pytest tests/ -q` (11 test) → 3 kịch bản terminal → checklist nghiệm thu 11 mục.
* **Điểm mới so với kế hoạch ban đầu**: thêm `tools/hashline/diffpreview.py` (preview nén `±N|` bằng difflib) và bộ unit test engine chạy trước khi gặp LLM (Quyết định 14).
