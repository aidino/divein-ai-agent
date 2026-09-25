# Phase 2.5: Codebase Intelligence — Hiểu codebase lớn
> **Prerequisite**: Phase 2
> **Thời gian ước tính**: 2-3 giờ  
> **AgentSeek template tham khảo**: `deepagents/powercontext`
> **Bạn sẽ học**: Cách giúp Coding Agent hiểu toàn bộ kiến trúc dự án lớn bằng cách kết hợp AST, GraphRAG và MCP, vượt qua giới hạn của tìm kiếm text thông thường.

## Mục tiêu
Xây dựng một lớp "trí tuệ codebase" (Codebase Intelligence) cho Agent, giúp nó không chỉ tìm kiếm được các chuỗi văn bản thuần túy mà còn hiểu được ngữ nghĩa, cấu trúc hàm và mối quan hệ phụ thuộc chéo trong các repository quy mô lớn.

## Concept chính

### Vấn đề của Codebase lớn
Dùng `grep` hay `glob` rất hiệu quả cho dự án nhỏ. Tuy nhiên, ở các repository lớn, tìm kiếm text bộc lộ nhược điểm:
- **Token explosion**: Lệnh `grep` có thể trả về quá nhiều kết quả, làm phình context.
- **Thiếu ngữ nghĩa (No semantic understanding)**: Tìm "module xác thực" sẽ không ra kết quả nếu code dùng từ khóa `auth_provider`.
- **Mù phụ thuộc (No dependency awareness)**: Khó biết hàm nào đang gọi hàm nào chỉ bằng cách quét text.

### Phương pháp tiếp cận 3 tầng (3-tier approach)
Để xử lý codebase khổng lồ, ta cung cấp cho Agent 3 tầng tìm kiếm:
1. **Deterministic (Xác định)**: Tìm kiếm cú pháp bằng `grep` và phân tích cây cú pháp trừu tượng (AST) để lập call graph (đồ thị hàm) hoặc repo maps.
2. **Semantic (Ngữ nghĩa)**: Áp dụng GraphRAG để truy xuất ý định ngữ nghĩa của code.
3. **Agentic (Tự chủ)**: Giao quyền cho Agent tự quyết định khi nào cần tìm chính xác (`grep`), khi nào cần tìm ngữ nghĩa.

### AST Indexing với Tree-sitter
Tree-sitter phân tách mã nguồn thành dạng cây cấu trúc (AST). Nhờ công cụ này, Agent có thể lập bảng ký hiệu (symbol tables), trích xuất danh sách class/hàm và tạo một bản đồ repository (repo map) cô đọng mà không cần đọc logic chi tiết của từng dòng code.

### GraphRAG với LightRAG
LightRAG (https://github.com/HKUDS/LightRAG) xây dựng đồ thị thực thể và mối quan hệ cho repository. Nó cung cấp:
- **Dual-level retrieval**: Khả năng truy xuất cục bộ chi tiết và truy xuất toàn cục khái quát.
- **Incremental updates**: Cập nhật đồ thị cực nhanh mỗi khi có file code thay đổi.
- **5 query modes**: Hỗ trợ nhiều cách đặt câu hỏi đa chiều.

### Tích hợp: Custom Tool hay MCP Server?
Có hai cách đưa LightRAG và AST vào hệ thống:
- **Custom Tool**: Bọc engine truy vấn vào một tool Python thông thường. Cách này áp dụng trong template `deepagents/powercontext` với `seekdb`.
- **MCP Server**: Triển khai engine Intelligence thành một Model Context Protocol (MCP) Server độc lập. Giải pháp này phù hợp cho hệ thống lớn, tách bạch hạ tầng lập chỉ mục và logic của Agent.

### Hybrid Retrieval (Truy xuất lai)
- **Small Repo**: `grep` và các công cụ mặc định là đủ.
- **Large Repo**: Kết hợp Vector search (ngữ nghĩa) + Keyword search (từ khóa) + Structural search (cấu trúc từ AST) để LLM có được thông tin đầy đủ và chính xác nhất.

## 📖 Đọc tài liệu

Bảng chỉ dẫn đọc — đọc theo thứ tự trước khi code:

| # | Tài liệu | Phần cần đọc | Bạn sẽ hiểu được gì |
|---|----------|-------------|---------------------|
| 1 | file:///home/lai/Documents/divein-ai-agent/guideline/05_virtual_filesystem.md | Các hạn chế của tìm kiếm file | Hiểu tại sao `grep` và `glob` có thể bị cắt cụt (truncated) trong codebase lớn |
| 2 | file:///home/lai/Documents/divein-ai-agent/guideline/14_mcp.md | Toàn bộ khái niệm MCP | Cách tích hợp một hệ thống bên ngoài thành MCP Server chuẩn giao tiếp với Agent |
| 3 | (Tài liệu ngoài) | GitHub LightRAG / Tree-sitter | Cấu trúc và hoạt động của GraphRAG và AST |

## 🧭 Hướng dẫn thực hiện

### Bước 1: Lựa chọn kiến trúc tích hợp
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/14_mcp.md
**Làm gì**: Chọn kiến trúc tích hợp: Nhúng trực tiếp qua Custom Tool (như `powercontext`) hoặc dựng MCP Server độc lập. Đối với dự án lớn, xây dựng MCP Server cho Code Intelligence là lựa chọn tối ưu.
**Tại sao**: Tách biệt logic lập chỉ mục giúp Agent không bị quá tải khi xử lý repository kích thước lớn, đồng thời dễ dàng cập nhật độc lập.

### Bước 2: Thiết kế công cụ truy xuất Semantic và AST
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/14_mcp.md
**Làm gì**: Định nghĩa các công cụ MCP hoặc Custom tool như `semantic_search_codebase` hoặc `get_class_structure`.
**Tại sao**: Cung cấp trực tiếp API khai thác quan hệ ngữ nghĩa sẽ giúp Agent tiếp cận ngay lập tức với insight của dự án thay vì bắt LLM đọc chay code.

### Bước 3: Đào tạo tư duy cho Agent
**Làm gì**: Viết system prompt để hướng dẫn Agent chiến lược phân tầng: dùng RAG/Semantic search để tìm hiểu tính năng khái quát -> dùng AST để xem cấu trúc file/class -> dùng `grep` và `read_file` để tìm điểm sửa cụ thể.
**Tại sao**: Trang bị nhiều công cụ có thể làm LLM rối. Phân tầng tư duy giúp Agent biết chọn công cụ nào phù hợp cho từng giai đoạn phân tích.

## ✅ Checkpoint — Tự kiểm tra
- Agent có biết sử dụng công cụ semantic search để tìm kiếm các concept mở thay vì chỉ dùng keyword match không?
- Agent có thể xuất cấu trúc tổng quan của class (thông qua AST) mà không cần tải toàn bộ nội dung file không?
- Nếu dùng MCP, việc cập nhật mã nguồn có được lập chỉ mục lại (incremental update) một cách trơn tru không?

## ⚠️ Lưu ý quan trọng
- **Chi phí Lập chỉ mục (Indexing Cost)**: Tạo GraphRAG tốn chi phí LLM. Đừng quên cấu hình loại trừ các thư mục không cần thiết (log, node_modules) khi indexing.
- **Tránh trùng lặp công cụ**: Khi đã có công cụ truy xuất ngữ nghĩa, cần điều chỉnh hoặc giới hạn lại công cụ tìm kiếm cơ bản để Agent không bị phân tâm.

## 🔗 Tham khảo thêm
- Tìm hiểu template `deepagents/powercontext` và `seekdb` để áp dụng ngay mô hình Hybrid Retrieval.
- Sử dụng chuẩn MCP để liên kết sức mạnh Intelligence cho mọi sub-agent trong hệ thống.
</Phase 2.5: Codebase Intelligence — Hiểu codebase lớn>
