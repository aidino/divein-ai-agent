# Phase 5: Sub-agents — Phân chia chuyên môn
> **Prerequisite**: Phase 4
> **Thời gian ước tính**: 3-4 giờ  
> **AgentSeek template tham khảo**: `deepagents/subagents-dynamic`
> **Bạn sẽ học**: Xây dựng kiến trúc điều phối nhiều Sub-agent (Nhạc trưởng và Chuyên gia) bằng cơ chế cách ly ngữ cảnh và biên hoạ động (Dynamic).

## Mục tiêu
Dạy Main Agent cách quản lý một đội ngũ "lập trình viên chuyên trách". Cấu hình kiến trúc Coordinator pattern, trong đó các Sub-agent như Researcher, Coder và Tester hoạt động độc lập mà không làm ô nhiễm bộ nhớ của nhau.

## Concept chính

### Công Cụ `task` Và Delegation Mechanism
`task` là công cụ cốt lõi để Main Agent ủy quyền cho Sub-agent. Dựa trên tham số `description`, Main Agent truyền đạt định hướng. Quá trình này giúp **Cách ly Ngữ cảnh (Context Quarantine)**: các chi tiết cào web, dò bug, đọc log của Sub-agent bị nhốt kín; Main Agent chỉ nhận lại một báo cáo tổng hợp.

### Subagent Declaration: Khai báo Chuyên Gia
Một Sub-agent được khai báo dưới dạng Dictionary gồm:
- `name`: Định danh.
- `model`: Mô hình LLM (có thể dùng model nhỏ cho việc đọc mã, model lớn cho việc suy luận khó).
- `tools`: Công cụ hẹp (Least Privilege).
- `system_prompt`: Tập lệnh hành vi riêng biệt.
- `middleware`: Stack xử lý độc lập.

### Designing Specialized Subagents for Coding
Phân tầng kiến trúc điển hình trong dự án phần mềm:
- **Researcher**: Chỉ được cấp quyền `read_file`, `grep`, `glob`. Nhiệm vụ đọc mã nguồn, tìm hiểu luồng dữ liệu. (Read-only)
- **Coder**: Được cấp quyền `read_file`, `edit_file`, `write_file`. Nhiệm vụ viết mã, thay thế nội dung. (Read+Write)
- **Tester**: Cấp quyền `execute` hoặc giao tiếp thẳng với Sandbox. Nhiệm vụ chạy test, biên dịch, phát hiện lỗi. (Execution)

### Coordinator Pattern
Main Agent sắm vai trò Nhạc Trưởng (Orchestrator). Nó không tự code, mà dùng `TodoListMiddleware` để lên kế hoạch. Sau đó gọi Researcher đi tìm chỗ cần sửa -> Gọi Coder thực hiện sửa -> Gọi Tester để chạy kiểm thử.

### Async Subagents & Dynamic Subagents
Khi một tác vụ yêu cầu xử lý hàng loạt (VD: review 24 file code):
- **Dynamic Subagents**: Main Agent sinh mã JavaScript (thông qua QuickJS Interpreter), mã JS sử dụng lệnh `task()` trong vòng lặp hoặc `Promise.all` để chạy song song hàng loạt phiên bản Sub-agent (Fan-out & Verify pattern). Lọc và gom nhóm kết quả ngay trong code.
- **Async Subagents**: Khởi tạo tác vụ chạy ngầm trên kiến trúc Agent Server dài hạn, sau đó truy vấn lại.
- **Classification & Routing**: Dùng JS để đọc mảng đầu vào, phân loại và gọi các Sub-agent (bug-fixer, feature-analyst) tương ứng.

### Khi Nào Dùng Gì?
- **Sync Subagent (Công cụ task thông thường)**: Gọi 1 tác vụ đơn lẻ, tuyến tính.
- **Dynamic Subagent (Qua mã QuickJS)**: Xử lý theo lô, song song, phân loại, cần tổng hợp mảng kết quả bằng lập trình.
- **Async Subagent**: Tác vụ chạy nền lâu dài, bất đồng bộ không cần chờ kết quả ngay lập tức.

## 📖 Đọc tài liệu

Bảng chỉ dẫn đọc — đọc theo thứ tự trước khi code:

| # | Tài liệu | Phần cần đọc | Bạn sẽ hiểu được gì |
|---|----------|-------------|---------------------|
| 1 | file:///home/lai/Documents/divein-ai-agent/guideline/07_subagents.md | Toàn bộ chương | Cơ chế cách ly ngữ cảnh, cấu hình dictionary của Sub-agent và Coordinator pattern. |
| 2 | file:///home/lai/Documents/divein-ai-agent/guideline/08_async_subagents.md | Toàn bộ chương | Phân biệt xử lý nền bất đồng bộ. |
| 3 | file:///home/lai/Documents/divein-ai-agent/guideline/18_dynamic_subagents.md | Toàn bộ chương | Khái niệm Dynamic Subagents: dùng LLM sinh mã JS để gọi `task()` hàng loạt xử lý lô, fan-out song song. |

## 🧭 Hướng dẫn thực hiện

Mô tả **các bước cần làm** ở mức concept (KHÔNG viết code):

### Bước 1: Khai báo danh sách Sub-Agents chuyên trách
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/07_subagents.md
**Làm gì**: Định nghĩa 3 dictionary cấu hình cho Researcher, Coder, Tester. Bố trí `system_prompt` nghiêm ngặt và cấp phát các `tools` tương ứng (không cấp thừa quyền).
**Tại sao**: Tạo nên đội ngũ chuyên gia làm nền tảng cho việc ủy quyền an toàn.

### Bước 2: Thiết lập Main Agent (Coordinator)
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/07_subagents.md
**Làm gì**: Khởi tạo Main Agent, truyền danh sách `subagents`. Khuyến khích Main Agent sử dụng TodoList để làm công tác quản trị. Hướng dẫn trong prompt cách phân bổ quy trình tuần tự.
**Tại sao**: Để LLM hiểu vai trò điều phối của mình, tránh việc tự ý ôm đồm công việc.

### Bước 3: Mở rộng thành Dynamic Subagents (Biên hoạ lô)
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/18_dynamic_subagents.md
**Làm gì**: Tích hợp `CodeInterpreterMiddleware`, đặt `timeout` đủ dài, kích hoạt cờ `subagents=True`. Tạo Prompt hướng dẫn Agent dùng `Promise.all` và hàm `task()` trong JavaScript để review nhiều file cùng lúc.
**Tại sao**: Giúp hệ thống mở rộng khả năng từ review 1 file sang hàng chục file mà không gây sụp đổ ngữ cảnh.

## ✅ Checkpoint — Tự kiểm tra
- Yêu cầu Agent sửa một tính năng phức tạp. Agent gọi Researcher để đọc toàn bộ kiến trúc -> gọi Coder -> gọi Tester. Ngữ cảnh của Main Agent chỉ chứa tóm tắt.
- Chạy review mã nguồn cho 5 file cùng lúc. Kiểm tra log thấy Main Agent sinh ra mã JS kích hoạt song song 5 tiến trình Sub-agent và lấy về báo cáo JSON cuối cùng.
- Cố tình bảo Coder chạy lệnh Sandbox, nó bị từ chối vì chỉ có quyền File. 

## ⚠️ Lưu ý quan trọng
- Khi gọi Dynamic Subagents, hàm `task()` trong JS yêu cầu `description` tự chứa đầy đủ thông tin (Stateless), vì Sub-agent không biết ngữ cảnh cũ.
- `system_prompt` của Sub-agent không được kế thừa từ Main Agent. Hãy tự viết chỉ dẫn đầy đủ cho từng Sub-agent.
- Cẩn thận với `timeout` của QuickJS khi gọi nhiều Sub-agent, cần nới rộng lên 60-120s.

## 🔗 Tham khảo thêm
- Sử dụng `response_format` (Pydantic) trên Sub-agent để ép kiểu kết quả về chuẩn JSON, dễ tổng hợp.
</Phase 5: Sub-agents — Phân chia chuyên môn>
