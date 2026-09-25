# Phase 2: File Operations — Đọc, ghi, tìm kiếm code
> **Prerequisite**: Phase 1
> **Thời gian ước tính**: 2-3 giờ  
> **Bạn sẽ học**: Cách Coding Agent tương tác với mã nguồn qua Hệ thống tập tin ảo (Virtual File System), các công cụ file thao tác chính xác, và cơ chế quản lý context tự động.

## Mục tiêu
Trang bị cho Coding Agent khả năng đọc hiểu, tìm kiếm và chỉnh sửa an toàn các file source code thực tế trong dự án, đồng thời đảm bảo context window không bị tràn khi làm việc với codebase lớn.

## Concept chính

### 7 Built-in File Tools
Deep Agents cung cấp 7 công cụ tích hợp sẵn đóng vai trò như đôi tay và đôi mắt của Agent:
- `ls`, `glob`, `grep`: Định vị và tìm kiếm file/code.
- `read_file`: Đọc nội dung mã nguồn.
- `write_file`, `edit_file`, `delete`: Chỉnh sửa và xóa file.
Với một coding agent, việc chọn đúng công cụ là sống còn (ví dụ: dùng `grep` để tìm vị trí hàm thay vì đọc toàn bộ thư mục).

### Phương pháp Surgical (Chỉnh sửa chính xác)
Trong v0.7+, `write_file` sẽ ghi đè toàn bộ file hiện có. Do đó, với Coding Agent, bạn phải ưu tiên sử dụng `edit_file` (thay thế chính xác `old_string` thành `new_string`) cho các file code đã có sẵn. Cách tiếp cận "surgical" (phẫu thuật) này giúp hạn chế rủi ro LLM làm hỏng các đoạn code không liên quan. `write_file` chỉ nên dùng khi tạo file code hoàn toàn mới.

### FilesystemBackend và StateBackend
Để Agent chạm được vào mã nguồn thật, bạn cần đổi từ `StateBackend` (chỉ lưu nháp trên RAM cho dev/testing) sang `FilesystemBackend` trỏ tới thư mục dự án. Đặc biệt, phải luôn bật `virtual_mode=True` để "nhốt" Agent trong thư mục dự án (sandbox), ngăn chặn các tấn công path traversal ra ngoài hệ thống.

### Đọc và tìm kiếm phân trang an toàn
- **grep output_modes**: Hỗ trợ trả về `files_with_matches` (danh sách file), `content` (nội dung khớp), `count` (thống kê).
- **read_file pagination**: Hỗ trợ `offset` và `limit`. Khi Agent đọc một file code lớn, nó không đọc một mạch mà đọc từng phần, framework trả về thông tin phân trang để Agent tự biết đọc tiếp.

### Tự động quản lý Context (Auto-eviction & Summarization)
- **Auto-eviction**: Khi output của một tool quá lớn (>20K tokens), framework tự động ghi kết quả này vào file ảo ở hệ thống tệp và chỉ trả về đoạn preview cho cuộc hội thoại.
- **Conversation Summarization**: Khi lịch sử chat chạm ngưỡng ~85% context window, framework tự động tóm tắt các tin nhắn cũ để duy trì phiên làm việc mượt mà.

## 📖 Đọc tài liệu

Bảng chỉ dẫn đọc — đọc theo thứ tự trước khi code:

| # | Tài liệu | Phần cần đọc | Bạn sẽ hiểu được gì |
|---|----------|-------------|---------------------|
| 1 | file:///home/lai/Documents/divein-ai-agent/guideline/01_deepagent_version_update.md | Phần 6. File tool | Những rào chắn đã bị gỡ bỏ ở v0.7 (`write_file` ghi đè toàn bộ) |
| 2 | file:///home/lai/Documents/divein-ai-agent/guideline/05_virtual_filesystem.md | Các Built-in Filesystem Tools | 7 file tools hoạt động ra sao và sự khác biệt giữa các Backend |
| 3 | file:///home/lai/Documents/divein-ai-agent/guideline/05_virtual_filesystem.md | Tự Động Quản Lý Context | Cơ chế Auto-eviction và tóm tắt hội thoại |

## 🧭 Hướng dẫn thực hiện

### Bước 1: Cấu hình FilesystemBackend
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/05_virtual_filesystem.md
**Làm gì**: Khởi tạo `FilesystemBackend` trỏ đến thư mục mã nguồn mục tiêu với `virtual_mode=True`. Đưa backend này vào API khởi tạo.
**Tại sao**: Coding Agent cần truy cập vào hệ thống tệp của dự án để thao tác. `virtual_mode` bảo vệ hệ điều hành của bạn khỏi các hành động đọc/ghi vượt quá ranh giới workspace.

### Bước 2: Thiết kế Workflow vào System Prompt
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/01_deepagent_version_update.md
**Làm gì**: Cập nhật system prompt để dạy Agent quy trình làm việc: Dùng `ls`/`grep` để tìm vị trí -> `read_file` đọc logic code -> `edit_file` để sửa chính xác. Nhấn mạnh việc cấm dùng `write_file` để sửa file đang có.
**Tại sao**: Agent có thể có xu hướng ghi đè toàn bộ file. Dạy nó workflow "surgical" sẽ bảo toàn mã nguồn gốc.

### Bước 3: Thử nghiệm phân trang và giới hạn kết quả
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/05_virtual_filesystem.md
**Làm gì**: Đặt yêu cầu cho agent tìm một từ khóa phổ biến trong repo, quan sát cách `grep` trả về `truncated=True`. Thử cho agent đọc một file rất lớn để thấy `read_file` phân trang bằng offset.
**Tại sao**: Hiểu được cách Deep Agents ngăn chặn tràn context window giúp bạn biết giới hạn khi vận hành Agent trên các dự án khổng lồ.

## ✅ Checkpoint — Tự kiểm tra
- Agent có thể chỉnh sửa thành công một hàm nhỏ trong file code bằng cách dùng `edit_file` chưa?
- Khi bạn yêu cầu Agent thử đọc file bên ngoài thư mục dự án, nó có bị chặn lại bởi `virtual_mode` không?
- Bạn đã thấy Agent tự động đọc nối tiếp file dài nhờ phân trang chưa?

## ⚠️ Lưu ý quan trọng
- **Nguy cơ ghi đè**: Ở v0.7, `write_file` sẽ ghi đè lập tức nội dung cũ. Hãy kiểm soát cẩn thận hành vi này.
- **Parsing kết quả tool**: Nếu code của bạn tự động bóc tách kết quả từ tool (ví dụ split tab), hãy chú ý cập nhật logic phân tích do một số định dạng trả về đã thay đổi.

## 🔗 Tham khảo thêm
- Khám phá `FilesystemPermission` để kiểm soát các tác vụ nhạy cảm như xóa file hoặc ghi đè thư mục quan trọng.
</Phase 2: File Operations — Đọc, ghi, tìm kiếm code>
