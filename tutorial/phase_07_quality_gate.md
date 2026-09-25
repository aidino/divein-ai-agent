# Phase 7: Quality Gate — Tự động verify kết quả
> **Prerequisite**: Phase 6
> **Thời gian ước tính**: 2-3 giờ  
> **AgentSeek template tham khảo**: `langchain/rubric`
> **Bạn sẽ học**: The 'Illusion of Completion', RubricMiddleware, Cơ chế 4 vai trò, Evidence Tool, Thiết kế Rubric, Fail-closed verification, TDD loop cho agent.

## Mục tiêu
Ngăn chặn ảo giác hoàn thành của LLM bằng cách thiết lập một cổng kiểm tra chất lượng (Quality Gate) tự động đánh giá và chấm điểm kết quả của agent, buộc agent phải sửa lỗi cho đến khi mọi bài test (evidence) được pass.

## Concept chính

### The 'Illusion of Completion'
LLM thường mắc phải "Ảo giác hoàn thành" (Illusion of Completion) — chúng tự tin tuyên bố đã làm xong việc dù mã nguồn sinh ra bị lỗi hoặc thiếu tính năng. Tự bản thân model đánh giá chính mình thường thất bại do nó cùng mang một điểm mù (blind spots). Do đó cần một kiến trúc phân lập để verify.

### RubricMiddleware & Cơ Chế Bốn Vai Trò (Four Roles)
Được quản lý thông qua `RubricMiddleware`, quá trình kiểm duyệt xoay quanh 4 vai trò:
1. **Working Model**: Mô hình sinh mã nguồn (model lớn, đắt tiền, tập trung logic).
2. **Rubric**: Tập hợp các tiêu chí đánh giá nghiêm ngặt, rõ ràng.
3. **Grader Model**: Mô hình chấm điểm dựa trên rubric (thường là model nhỏ, nhanh, chi phí thấp).
4. **Evidence Tool**: Công cụ cung cấp bằng chứng khách quan (test runner, linter). KHÔNG dùng LLM để tự nhận xét khách quan.

### Evidence Tool
Công cụ này phải trả về bằng chứng cụ thể và có tính quyết định (deterministic) như `{ok: boolean, failures: string[]}` thay vì cảm tính. Grader Model dùng kết quả này để đối chiếu với Rubric.

### Thiết kế Rubric & Cơ chế Fail-Closed
- **Atomic & Observable**: Rubric criteria phải được chia nhỏ (atomic), có thể quan sát (observable) bằng evidence. 
- **Fail-closed verification**: Kết quả chỉ được tính là PASS khi trạng thái là `satisfied` VÀ không có tính năng nào là `unverified`. Nếu thiếu bằng chứng, mặc định là Rớt (Fail).
- **Frozen criteria (`_rubric_criteria`)**: Đóng băng rubric trong suốt quá trình chạy. Không cho phép LLM tự động sửa đổi hoặc "nhẹ tay" các tiêu chí sau nhiều lần lặp.

### Vòng lặp TDD cho Coding Agents
Quy trình: Viết code (Working Model) → Chạy bài test (Evidence Tool do Grader điều khiển) → Phát hiện Fail → Feed lại lỗi (Feedback) → Sửa code (Fix) → Chạy lại bài test → Pass (Thoát vòng lặp).

### Kiến Trúc 2 Mô Hình & Bảo Vệ Khỏi Prompt Injection
Kiến trúc này giúp tối ưu hóa chi phí (hai mô hình) và kiểm soát an toàn qua transcript limits, đồng thời cẩn trọng không chèn trực tiếp nội dung web không xác định vào prompt của Grader để chống prompt injection.

## 📖 Đọc tài liệu

Bảng chỉ dẫn đọc — đọc theo thứ tự trước khi code:

| # | Tài liệu | Phần cần đọc | Bạn sẽ hiểu được gì |
|---|----------|-------------|---------------------|
| 1 | [15_grading_rubrics.md](file:///home/lai/Documents/divein-ai-agent/guideline/15_grading_rubrics.md) | Toàn bộ tài liệu | Các thành phần của RubricMiddleware, cách thiết kế criteria và evidence tool. |

## 🧭 Hướng dẫn thực hiện

### Bước 1: Xây dựng Evidence Tool
**Đọc**: [15_grading_rubrics.md](file:///home/lai/Documents/divein-ai-agent/guideline/15_grading_rubrics.md)
**Làm gì**: Thiết lập một tool chạy lệnh (như `pytest` hoặc `npm test`) và trả về chuỗi JSON rõ ràng chứa `ok` và các `failures`.
**Tại sao**: Khẳng định sự thật bằng kết quả test hệ thống thay vì lời nói của LLM.

### Bước 2: Tạo tĩnh (Freeze) các Rubric Criteria
**Đọc**: [15_grading_rubrics.md](file:///home/lai/Documents/divein-ai-agent/guideline/15_grading_rubrics.md)
**Làm gì**: Xác định rõ các tiêu chí thành công của task bằng một danh sách không thể thay đổi (`_rubric_criteria`) và chuyển cho Grader.
**Tại sao**: Ngăn chặn tình trạng agent "di dời vạch đích" khi không giải quyết được vấn đề.

### Bước 3: Tích hợp RubricMiddleware
**Đọc**: [15_grading_rubrics.md](file:///home/lai/Documents/divein-ai-agent/guideline/15_grading_rubrics.md)
**Làm gì**: Đặt Working Model vào vòng lặp của RubricMiddleware, thiết lập model nhỏ làm Grader Model. Trả kết quả feedback về lại cho Working Model khi rớt.
**Tại sao**: Tạo thành vòng lặp TDD khép kín, tối ưu khả năng code của agent.

## ✅ Checkpoint — Tự kiểm tra
- Cố tình để Working Model sinh ra code có lỗi logic. Verify xem hệ thống có tự động lặp lại quy trình sửa lỗi hay không.
- Kiểm tra số vòng lặp tối đa, đảm bảo hệ thống tự ngắt và trả lỗi khi agent bị bế tắc (tránh chạy vô hạn).
- Đảm bảo điểm số và kết quả phê duyệt đến từ kết quả test chứ không phải tự LLM nghĩ ra.

## ⚠️ Lưu ý quan trọng
- Không bao giờ để một model tự chấm điểm code của chính nó nếu không có evidence khách quan.
- Kết quả không verified = Fail.
- Giới hạn số lượng token/tin nhắn trong vòng lặp để tránh chi phí tăng vọt.

## 🔗 Tham khảo thêm
- Tích hợp thêm các Evidence tool khác như Static Code Analysis, Linter hoặc Coverty.
- Tham khảo AgentSeek template: `langchain/rubric`.
