# Phase 4: Code Execution — Chạy code an toàn (3 options)
> **Prerequisite**: Phase 3
> **Thời gian ước tính**: 3-4 giờ  
> **AgentSeek template tham khảo**: `deepagents/sandbox`
> **Bạn sẽ học**: Cách quyết định nơi thực thi code của Agent, cô lập rủi ro và các giải pháp Sandbox hiện hành.

## Mục tiêu
Trang bị cho Agent khả năng biên dịch, chạy code và kiểm thử (test) mà không làm nguy hiểm đến máy chủ chủ quản (Host). Agent sẽ hoạt động như một thực thể chấp hành (executor) an toàn.

## Concept chính

### Câu hỏi nền tảng: Thực thi code ở đâu?
Agent của bạn tạo ra code, nhưng **chạy code đó ở đâu**? Chạy thẳng trên máy tính của bạn rất nguy hiểm (có thể xóa file, lộ biến môi trường). Do đó, ta có 3 lựa chọn kiến trúc cơ bản.

### Option A: LocalShellBackend (Chỉ dành cho Dev)
Thực thi trực tiếp trên hệ điều hành máy chủ qua LocalShellBackend.
- Cấp công cụ `execute()` để gọi lệnh bash/sh cục bộ.
- **Rủi ro**: Rất cao. Một câu lệnh `rm -rf` sai lầm có thể phá hủy dự án. Không bao giờ dùng cho Production.
- **Ứng dụng**: Phù hợp cho môi trường Dev khép kín, hoặc bọc thành các "công cụ hẹp" (custom tools) chỉ được phép chạy những lệnh định sẵn như `run_tests` hay `run_linter`.

### Option B: Docker Container — AIO Sandbox
Sử dụng một container Docker cô lập như All-in-One (AIO) Sandbox (ví dụ từ `agent-infra/sandbox`).
- Container bao gồm đủ Browser, Shell, Virtual Filesystem, kết nối MCP và VSCode.
- Cung cấp API truy cập dễ dàng. 
- Mẫu **Sandbox-as-Tool**: Agent chạy trên máy chủ Host an toàn, nhưng khi cần thực thi lệnh, nó gửi RPC sang Docker Sandbox. API Key được giữ lại ở Host, bảo mật tuyệt đối.

### Option C: Cloud Sandbox
Giải pháp hạ tầng được quản lý hoàn toàn trên đám mây, cực kỳ mạnh mẽ cho Production.
- **LangSmith Sandboxes**: Dựa trên microVM, cho phép copy-on-write forks, chụp snapshot nhanh, có Auth Proxy giúp bảo mật token.
- **E2B**: Nền tảng nổi tiếng dựa trên Firecracker microVM, hỗ trợ SDK phong phú.
- **Daytona**: Tạo môi trường chuẩn hóa OCI container, tối ưu cho luồng làm việc git-first.

### CodeInterpreterMiddleware: In-Process QuickJS
Một giải pháp hoàn toàn khác: thay vì dùng Sandbox/Container, sử dụng QuickJS được nhúng trực tiếp trong cùng process.
- Cơ chế **Programmatic Tool Calling (PTC)**: LLM sinh ra mã JavaScript để gọi các công cụ nội bộ theo dạng lô (`Promise.all`).
- Lý tưởng cho các thao tác phân loại mảng, đối chiếu, lọc dữ liệu (batch file analysis) mà không cần mạng lưới Sandbox cồng kềnh.

### Interpreter vs Sandbox: Khi Nào Dùng Gì?
- **Interpreter**: Dùng để phân tích dữ liệu, tổng hợp JSON, sắp xếp mảng nội bộ. Nhanh, nhẹ, an toàn tuyệt đối, không có quyền truy cập OS.
- **Sandbox**: Dùng khi cần chạy shell (`bash`, `pip install`), biên dịch phần mềm, chạy unit tests, hay dựng môi trường hệ điều hành thực thụ.

### An toàn bảo mật (Security Considerations)
Dù dùng giải pháp Sandbox nào, Agent vẫn có thể bị tiêm nhiễm ngữ cảnh (Prompt Injection) để đọc dữ liệu nhạy cảm hoặc tấn công qua mạng. Giải pháp luôn là:
- Ranh giới rõ ràng: Tuyệt đối không nhét Agent Loop + API Keys vào trong Sandbox.
- Áp dụng Sandbox-as-Tool Pattern.

## 📖 Đọc tài liệu

Bảng chỉ dẫn đọc — đọc theo thứ tự trước khi code:

| # | Tài liệu | Phần cần đọc | Bạn sẽ hiểu được gì |
|---|----------|-------------|---------------------|
| 1 | file:///home/lai/Documents/divein-ai-agent/guideline/05_virtual_filesystem.md | Toàn bộ chương | Cơ sở về Virtual File System và cách LocalShellBackend cấp quyền. |
| 2 | file:///home/lai/Documents/divein-ai-agent/guideline/12_sandboxes.md | Toàn bộ chương | Các mô hình Sandbox (Cloud, Docker), khái niệm Sandbox-as-Tool và ranh giới bảo mật. |
| 3 | file:///home/lai/Documents/divein-ai-agent/guideline/17_interpreters.md | Toàn bộ chương | Cách CodeInterpreterMiddleware hoạt động và khi nào nên dùng Interpreter thay thế. |

## 🧭 Hướng dẫn thực hiện

Mô tả **các bước cần làm** ở mức concept (KHÔNG viết code):

### Bước 1: Quyết định kiến trúc Sandbox
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/12_sandboxes.md
**Làm gì**: Lựa chọn backend phù hợp (LangSmith, E2B hoặc Docker). Cấu hình kết nối Sandbox làm Backend cho Agent thay vì dùng Local Disk.
**Tại sao**: Phân tách ranh giới giữa bộ não (LLM, Memory ở Host) và cơ bắp (thực thi ở Sandbox), đảm bảo an ninh tuyệt đối cho hệ thống.

### Bước 2: Thiết lập Control Plane và Execution Plane
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/12_sandboxes.md
**Làm gì**: Lập trình luồng tải mã nguồn vào Sandbox (Seed data) trước khi chạy Agent, và luồng trích xuất kết quả (Download artifacts) sau khi chạy xong. Đảm bảo Agent chỉ thao tác trên không gian thực thi của Sandbox.
**Tại sao**: Agent không thể tự đoán cấu trúc máy chủ của bạn; dữ liệu phải được gieo vào vùng cô lập một cách có chủ đích.

### Bước 3: Bổ sung CodeInterpreterMiddleware (Tùy chọn cho phân tích)
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/17_interpreters.md
**Làm gì**: Nạp `CodeInterpreterMiddleware` vào middleware stack để Agent có khả năng dùng `eval` và thao tác dữ liệu qua JS.
**Tại sao**: Dùng cho những tác vụ lọc và xử lý lô (batch processing) quá nhỏ hoặc chuyên biệt mà đưa vào Sandbox OS lại là quá dư thừa.

## ✅ Checkpoint — Tự kiểm tra
- Giao cho Agent viết một đoạn script Python tính giai thừa và yêu cầu nó chạy `pytest`. Agent thực thi trong Sandbox thành công và trả về log.
- Cố tình bảo Agent thực thi `cat /etc/passwd` hoặc `env`. Xác nhận nó chỉ lấy được thông tin của container/microVM, không phải của máy chủ thực.
- Sử dụng PTC (Interpreter) để tổng hợp một file log 10,000 dòng, xem Agent chỉ trả về tóm tắt cuối cùng.

## ⚠️ Lưu ý quan trọng
- Không bao giờ truyền Token hay API Key quan trọng vào biến môi trường của Sandbox.
- Code đầu ra của Sandbox (output của `execute`) có thể rất dài. Hệ thống cần cắt bớt (truncate) và lưu vào file tạm để Agent dùng `read_file` đọc lại, tránh gây quá tải (Context Overflow).

## 🔗 Tham khảo thêm
- Khám phá LangSmith Service URLs để xem trực tiếp ứng dụng web mà Agent vừa lập trình bên trong Sandbox.
</Phase 4: Code Execution — Chạy code an toàn (3 options)>
