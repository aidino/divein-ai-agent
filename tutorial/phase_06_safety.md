# Phase 6: Safety & Permissions — Bảo vệ workspace
> **Prerequisite**: Phase 5
> **Thời gian ước tính**: 1-2 giờ  
> **Bạn sẽ học**: Security threat model, FilesystemPermission, 'First-Match-Wins' rule, 'Default-Allow' trap, Whitelist pattern, Interrupt mode, HumanInTheLoopMiddleware, Subagent permission inheritance, PolicyWrapper.

## Mục tiêu
Thiết lập cơ chế phân quyền an toàn, ngăn chặn agent vô tình (hoặc cố ý) chỉnh sửa, xóa các file nhạy cảm, và đưa con người vào vòng lặp (Human-in-the-loop) để phê duyệt các hành động quan trọng trong hệ thống coding agent.

## Concept chính

### Security Threat Model cho Coding Agents
Các rủi ro bảo mật chính đối với agent bao gồm: path traversal (truy cập vượt ra ngoài workspace), secret exposure (đọc nhầm file `.env` chứa mật khẩu), accidental deletion (xóa nhầm dữ liệu hệ thống), và prompt injection (bị thao túng để chạy mã độc). Agent có quyền can thiệp vào máy của người dùng, nên việc bảo vệ là tối quan trọng.

### FilesystemPermission & Kiến trúc phân quyền
Framework quản lý file system qua các thao tác (`read`, `write`), đường dẫn (sử dụng glob patterns), và chế độ (mode: `allow`, `deny`, `interrupt`). 
Nguyên tắc cốt lõi:
- **First-Match-Wins**: Các rule được duyệt từ trên xuống dưới; rule nào khớp đầu tiên sẽ được áp dụng và bỏ qua các rule sau.
- **The 'Default-Allow' trap**: Nguy hiểm lớn nhất là nếu KHÔNG CÓ rule nào khớp với đường dẫn, framework mặc định CHO PHÉP (ALLOW). 
- **Whitelist pattern**: Pattern an toàn nhất là: (1) deny cụ thể các file/thư mục nhạy cảm → (2) allow các file/thư mục nghiệp vụ → (3) deny toàn bộ phần còn lại (catch-all).

### Bảo vệ Sensitive Files
Những thư mục như `.env`, `.git/**`, `node_modules/**`, `deploy/**` phải được cấu hình `deny` ngay từ những rule đầu tiên để không bị ảnh hưởng, dù là read hay write.

### Interrupt mode & HumanInTheLoopMiddleware
Sử dụng mode `interrupt` cho phép tạm dừng tiến trình thực thi của Agent để chờ con người phê duyệt (thông qua `Command(resume=...)`). `HumanInTheLoopMiddleware` sử dụng lệnh `interrupt()` ở các hook kiểu node-style, giúp kiểm soát tốt các luồng công việc rủi ro.

### Kế thừa quyền của Subagent (Full Replacement)
Khi khởi tạo một subagent, nếu truyền vào cấu hình permission, quyền này sẽ THAY THẾ HOÀN TOÀN (replaces) quyền của parent agent, KHÔNG PHẢI GỘP LẠI (merges). Điều này đảm bảo subagent chỉ chạy đúng trong scope hẹp của nó.

### PolicyWrapper & Phạm vi giới hạn (Scope limitation)
- **PolicyWrapper**: Có thể dùng để bọc các rule tĩnh thành luật động: audit logging, secret scanning, hoặc rate limiting.
- **Giới hạn**: Quyền hạn `FilesystemPermission` CHỈ áp dụng cho các built-in file tools. Custom tools, MCP tools hay sandbox execute sẽ không bị chặn bởi các rule này, do đó cần thiết kế bảo mật riêng.

## 📖 Đọc tài liệu

Bảng chỉ dẫn đọc — đọc theo thứ tự trước khi code:

| # | Tài liệu | Phần cần đọc | Bạn sẽ hiểu được gì |
|---|----------|-------------|---------------------|
| 1 | [13_filesystem_permissions.md](file:///home/lai/Documents/divein-ai-agent/guideline/13_filesystem_permissions.md) | Toàn bộ tài liệu | Hiểu về First-Match-Wins, Default-Allow trap và cách viết Whitelist pattern. |
| 2 | [11_human_in_the_loop.md](file:///home/lai/Documents/divein-ai-agent/guideline/11_human_in_the_loop.md) | Cơ chế Interrupt | Cách dùng HumanInTheLoopMiddleware để xin ý kiến con người ở các bước nhạy cảm. |

## 🧭 Hướng dẫn thực hiện

### Bước 1: Áp dụng Whitelist Pattern cho Workspace
**Đọc**: [13_filesystem_permissions.md](file:///home/lai/Documents/divein-ai-agent/guideline/13_filesystem_permissions.md)
**Làm gì**: Tạo một mảng rules cho Agent. Bắt đầu bằng việc `deny` quyền đọc/ghi vào `.env` và `.git/**`. Tiếp theo, `allow` thư mục `src/**`. Cuối cùng, bắt buộc thêm rule `deny` với `*` (catch-all).
**Tại sao**: Nếu bỏ quên rule catch-all, bạn sẽ sập bẫy "Default-Allow" và Agent có thể thao tác file ở bất cứ đâu.

### Bước 2: Bật Interrupt cho Hành Động Ghi
**Đọc**: [11_human_in_the_loop.md](file:///home/lai/Documents/divein-ai-agent/guideline/11_human_in_the_loop.md)
**Làm gì**: Sửa rule `allow` đối với thư mục code quan trọng thành `interrupt` cho thao tác `write`. Cấu hình `HumanInTheLoopMiddleware` để Agent dừng lại hỏi người dùng.
**Tại sao**: Mang lại sự an tâm tuyệt đối, Agent chỉ code tự động nhưng quyết định lưu vào file là do con người phê duyệt.

### Bước 3: Cấu hình Quyền Tối Thiểu Cho Subagent
**Đọc**: [13_filesystem_permissions.md](file:///home/lai/Documents/divein-ai-agent/guideline/13_filesystem_permissions.md)
**Làm gì**: Cấu hình permission riêng cho một subagent chuyên test để nó chỉ được đọc thư mục `tests/**` mà không được ghi vào file source. Nhớ rằng permission này sẽ ghi đè permission của parent.
**Tại sao**: Thực thi nguyên tắc Least Privilege (Quyền hạn tối thiểu).

## ✅ Checkpoint — Tự kiểm tra
- Chạy Agent yêu cầu đọc nội dung file `.env`. Nếu agent bị báo lỗi chặn quyền, bước phân quyền thành công.
- Yêu cầu Agent sửa một file trong `src/`, xem tiến trình có bị `interrupt` chờ bạn duyệt qua terminal/UI hay không.
- Nhớ kiểm tra xem custom tool của bạn có tình cờ bypass qua cơ chế bảo mật file hay không.

## ⚠️ Lưu ý quan trọng
- Luôn nhớ đặt quy tắc catch-all `deny` ở cuối danh sách.
- Khi truyền Permission cho Subagent, nhớ là nó KHÔNG MERGE với Parent. Subagent sẽ mất hết quyền của parent nếu bạn không định nghĩa đầy đủ.
- Permission này không bảo vệ MCP hay Sandbox Tools!

## 🔗 Tham khảo thêm
- Tích hợp thêm các hệ thống quét mã độc vào `PolicyWrapper` ở môi trường production.
