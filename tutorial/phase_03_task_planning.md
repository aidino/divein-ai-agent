# Phase 3: Task Planning — Phân rã công việc phức tạp
> **Prerequisite**: Phase 2
> **Thời gian ước tính**: 2-3 giờ  
> **Bạn sẽ học**: Cách giúp Agent lập kế hoạch, tránh trôi ngữ cảnh, tích hợp middleware và cơ chế tóm tắt.

## Mục tiêu
Agent có khả năng tự động phân rã các yêu cầu lập trình lớn thành một danh sách công việc (todo list) tường minh. Agent biết theo dõi tiến độ, cập nhật trạng thái sau mỗi bước, và không bao giờ bị lạc đề (context drift) kể cả khi ngữ cảnh trở nên quá dài.

## Concept chính

### Tại Sao Lập Kế Hoạch Lại Quan Trọng Đối Với Coding Agent?
Khi xử lý các tác vụ code phức tạp (multi-step coding tasks) như xây dựng một tính năng mới hay refactor mã nguồn, nếu không có kế hoạch, Agent rất dễ gặp các vấn đề:
- Bỏ sót các bước quan trọng (ví dụ: quên viết test).
- Thực hiện lại các hành động thừa thãi (ví dụ: tìm kiếm lại một thông tin đã tìm).
- Trôi ngữ cảnh (Context Drift): Khi lịch sử log quá dài, mô hình quên mất mục tiêu cốt lõi ban đầu.
Task Planning đóng vai trò như một "chiếc la bàn" định hướng, bẻ nhỏ tác vụ để trị.

### TodoListMiddleware & Cơ Chế Hoạt Động
`TodoListMiddleware` là cầu nối kích hoạt khả năng lập kế hoạch:
- Tiêm công cụ `write_todos` vào Agent.
- Mở kênh trạng thái riêng biệt `state['todos']` để lưu trữ danh sách độc lập với tin nhắn.
- Tự động chèn (inject) các chỉ dẫn về lập kế hoạch vào System Prompt.

### Vòng Đời Của Một Nhiệm Vụ (Task Schema & Lifecycle)
Mỗi task có cấu trúc đơn giản: `{content, status: pending|in_progress|completed}`.
Vòng đời 3 pha bao gồm:
1. **Lập kế hoạch**: Tất cả các task bắt đầu ở trạng thái `pending`.
2. **Thực thi tuần tự**: Agent đổi trạng thái sang `in_progress`, gọi công cụ (vd: viết code), sau đó đánh dấu `completed`.
3. **Điều chỉnh động**: Agent có thể thêm, bớt hoặc sửa đổi task linh hoạt khi phát sinh vấn đề mới.

### Kiến Trúc Middleware: Node-style vs Wrap-style
LangChain chia middleware thành 2 loại hook:
- **Node-style hooks** (`before_agent`, `before_model`, `after_model`, `after_agent`): Chạy như các node độc lập trên đồ thị LangGraph, phù hợp để kiểm tra dữ liệu, ngắt luồng (interrupt) chờ con người duyệt.
- **Wrap-style hooks** (`wrap_model_call`, `wrap_tool_call`): Hoạt động như decorator bao bọc việc gọi mô hình, lý tưởng cho việc retry tự động, fallback model hay nén ngữ cảnh.

### SummarizationMiddleware & "Mỏ Neo Nhận Thức"
Khi ngữ cảnh quá dài, `SummarizationMiddleware` (wrap-style) sẽ nén các tin nhắn cũ lại. Điều kỳ diệu là danh sách `todos` vẫn được giữ nguyên. Lúc này, Todo List trở thành "mỏ neo nhận thức" (cognitive anchor), giúp Agent biết mình đang ở đâu, đã làm gì và cần làm gì tiếp theo, dù chi tiết các bước trước đã bị tóm tắt.

### PatchToolCallsMiddleware: Sức Chịu Đựng Lỗi (Fault Tolerance)
Trong quá trình code, người dùng có thể ngắt (interrupt) ngang hoặc mạng bị rớt khi tool đang chạy. Điều này tạo ra các `tool_calls` không có phản hồi tương ứng, làm crash API trong lần chạy sau. `PatchToolCallsMiddleware` quét lịch sử, tự động chèn các thông báo giả lập hủy bỏ để vá lỗi giao thức, giúp tiến trình chạy tiếp tục an toàn.

## 📖 Đọc tài liệu

Bảng chỉ dẫn đọc — đọc theo thứ tự trước khi code:

| # | Tài liệu | Phần cần đọc | Bạn sẽ hiểu được gì |
|---|----------|-------------|---------------------|
| 1 | file:///home/lai/Documents/divein-ai-agent/guideline/06_task_planning.md | Toàn bộ chương | Hiểu bản chất Task Planning, cách cấu hình Middleware, sự phân biệt Node/Wrap-style hooks và cách Todo list kết hợp cùng Summarization. |

## 🧭 Hướng dẫn thực hiện

Mô tả **các bước cần làm** ở mức concept (KHÔNG viết code):

### Bước 1: Khởi tạo Middleware Stack
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/06_task_planning.md
**Làm gì**: Nạp vào cấu hình `create_deep_agent` danh sách các middleware bao gồm `TodoListMiddleware`, `PatchToolCallsMiddleware`, và cấu hình `SummarizationMiddleware` với giới hạn token cụ thể.
**Tại sao**: Thiết lập bộ khung vững chắc để Agent biết lập kế hoạch, biết tự nén khi đầy bộ nhớ và biết tự sửa khi bị gián đoạn.

### Bước 2: Thiết kế System Prompt Ưu Tiên Lập Kế Hoạch (Planning-first)
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/06_task_planning.md
**Làm gì**: Bổ sung vào system prompt chỉ dẫn nghiêm ngặt yêu cầu Agent luôn phải gọi `write_todos` trước khi bắt tay vào thao tác file hay viết code. Hướng dẫn Agent cập nhật trạng thái `in_progress` và `completed` một cách kịp thời.
**Tại sao**: LLM cần một sự định hướng rõ ràng về quy trình. Thiếu prompt, mô hình có thể phớt lờ công cụ lập kế hoạch.

### Bước 3: Kiểm tra sự bền bỉ của Todo List qua Nén Ngữ Cảnh
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/06_task_planning.md
**Làm gì**: Giả lập một tác vụ dài để buộc `SummarizationMiddleware` kích hoạt nén tin nhắn. Xác nhận danh sách `todos` vẫn toàn vẹn và Agent vẫn bám sát công việc.
**Tại sao**: Khẳng định sự tồn tại độc lập của `todos` ngoài không gian message history, đảm bảo Agent duy trì được tư duy dài hạn.

## ✅ Checkpoint — Tự kiểm tra
- Giao một tác vụ đa bước, Agent lập tức phân rã thành danh sách công việc.
- Quan sát thấy Agent hoàn thành tuần tự và chủ động đánh dấu `completed`.
- Cố tình ngắt (Cancel) tiến trình khi Agent đang gọi tool, sau đó chạy tiếp mà Agent không bị lỗi 400 Bad Request.

## ⚠️ Lưu ý quan trọng
- Trạng thái `completed` chỉ là nhận thức tự đánh giá của LLM. Trong một dự án code thực tế, thành công phải được xác nhận bằng Unit Test hoặc linter, không thể hoàn toàn tin vào việc Agent "báo cáo đã xong".
- Tránh dùng `TodoListMiddleware` cho các tác vụ hỏi đáp 1 bước đơn giản để tiết kiệm token và thời gian.

## 🔗 Tham khảo thêm
- Kết hợp Planning với Checkpointer để Todo list sống sót qua nhiều phiên khởi động lại ứng dụng.
</Phase 3: Task Planning — Phân rã công việc phức tạp>
