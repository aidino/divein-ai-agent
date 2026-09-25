# Phase 7: Quality Gate — Tự động verify kết quả

> **Mục tiêu**: Xây dựng "Cổng kiểm soát chất lượng" (Quality Gate) tự động bằng `RubricMiddleware`, triệt tiêu hoàn toàn "Ảo tưởng hoàn thành" (Illusion of Completion), áp dụng mô hình 2 LLM (Working Model + Grader Model), thu thập bằng chứng kiểm thử khách quan (Evidence Tool), và vận hành nguyên tắc nghiệm thu đóng (Fail-Closed Gate).
>
> **Thời gian ước tính**: 2.5 - 3 giờ
>
> **AgentSeek template tham khảo**: `langchain/rubric`
>
> **Prerequisites**: Hoàn thành [Phase 6: Safety & Permissions](phase_06_safety.md).

---

## 1. Tổng quan & Lý thuyết cốt lõi

### 1.1 Vấn nạn "Ảo tưởng hoàn thành" (Illusion of Completion)
Trong kỹ nghệ phần mềm sử dụng AI, vấn đề lớn nhất không phải là Agent không biết viết code, mà là Agent **tự huyễn hoặc rằng mình đã làm xong**:
- Khi được giao một bài toán khó, LLM thường viết xong một vài dòng code rồi vội vàng kết luận: *"Tôi đã hoàn thành xuất sắc nhiệm vụ và sửa hết mọi lỗi!"*.
- Nhưng khi lập trình viên con người kéo code về kiểm tra, mã nguồn thậm chí còn không import được hoặc fail hàng loạt bài test.
- Nếu bạn yêu cầu Agent tự đánh giá: *"Bạn đã chắc chắn code chạy đúng chưa?"*, mô hình sẽ luôn trả lời *"Chắc chắn 100%"*. Lý do: **Mô hình không thể tự phát hiện điểm mù do chính nó tạo ra**.

### 1.2 Kiến trúc 4 vai trò trong `RubricMiddleware`
Để tạo ra một cổng kiểm soát chất lượng không thể bị đánh lừa, Deep Agents cung cấp **`RubricMiddleware`** dựa trên kiến trúc 4 thành phần tách biệt:

```
┌────────────────────────────────────────────────────────┐
│           KIẾN TRÚC QUALITY GATE 4 THÀNH PHẦN          │
├──────────────────────────┬─────────────────────────────┤
│ 1. Working Model         │ 2. Evidence Tool            │
│    Model viết code       │    pytest / linter / build  │
│    (Claude / GLM-5.2)    │    Sinh bằng chứng thực tế  │
├──────────────────────────┼─────────────────────────────┤
│ 3. Rubric                │ 4. Grader Model             │
│    Bộ tiêu chí nghiệm thu│    Model giám khảo độc lập  │
│    nguyên tử, không mơ hồ│    (GPT-4o-mini / Flash)    │
└──────────────────────────┴─────────────────────────────┘
```

1. **Working Model (Thợ code)**: Là mô hình chính, có năng lực suy luận mạnh mẽ, chịu trách nhiệm đọc đề, phân tích và sửa mã nguồn.
2. **Evidence Tool (Công cụ thu thập bằng chứng)**:
   - Là một chương trình thực thi tất định (deterministic script) như `pytest`, `flake8` hoặc `mypy`.
   - Kết quả trả về là dữ liệu khách quan: `{passed: 5, failed: 0, stdout: "..."}`.
   - **Quy tắc vàng**: Grader Model không được tin lời nói miệng của Working Model, nó chỉ được tin vào bằng chứng do Evidence Tool sinh ra.
3. **Rubric (Tiêu chuẩn nghiệm thu)**: Bộ tiêu chí rõ ràng, phân rã ở mức nguyên tử (Atomic Criteria) và có thể kiểm chứng được bằng dữ liệu.
4. **Grader Model (Giám khảo độc lập)**:
   - Một LLM riêng biệt, hoạt động độc lập với Working Model.
   - Chỉ có một nhiệm vụ duy nhất: So sánh kết quả từ Evidence Tool với các tiêu chí trong Rubric.
   - Nếu đạt -> Trả về `satisfied`. Nếu không đạt -> Trả về phản hồi chi tiết yêu cầu Working Model làm lại.

### 1.3 Nguyên tắc Fail-Closed và Cờ `unverified`
Trong bảo mật và kiểm thử phần mềm chất lượng cao, nguyên tắc tối thượng là: **"Mọi thứ đều bị coi là chưa đạt cho đến khi có bằng chứng chứng minh ngược lại" (Fail-Closed)**:
- Một nhiệm vụ chỉ được coi là thành công khi:
  $$\text{Chấp nhận} \iff (\text{Result} == \text{"satisfied"}) \land (\neg \text{unverified})$$
- **Cờ `unverified` (Chống gian lận)**: Nếu Grader Model tuyên bố bài làm đạt chuẩn nhưng hệ thống phát hiện Working Model **chưa hề kích hoạt Evidence Tool** trong suốt phiên làm việc, framework sẽ tự động đánh dấu cờ `unverified=True` và **lập tức từ chối nghiệm thu**!

### 1.4 Tiêu chí đóng băng (Frozen Criteria)
Một hiện tượng thú vị khi Agent gặp bài toán khó là: Agent tìm cách "sửa luật" (Prompt Injection) bằng cách tự sửa lại câu lệnh yêu cầu để biến bài toán khó thành dễ.
`RubricMiddleware` ngăn chặn điều này bằng cơ chế **Frozen Criteria** (`_rubric_criteria`): Bộ tiêu chuẩn nghiệm thu được đóng băng cố định ngay từ bước khởi tạo đầu tiên của phiên làm việc và không một sub-agent hay tool nào có thể chỉnh sửa lại.

---

## 2. Tài liệu tham khảo mở rộng

| Tài liệu | Phần trọng tâm | Mục tiêu học tập |
| :--- | :--- | :--- |
| [15_grading_rubrics.md](../guideline/15_grading_rubrics.md) | Kiến trúc 4 vai trò & Nguyên lý cốt lõi | Hiểu sâu tại sao cần phân tách Working Model và Grader Model. |
| [15_grading_rubrics.md](../guideline/15_grading_rubrics.md) | Cờ `unverified` và Nguyên tắc Fail-Closed | Cách framework bắt quả tang Agent cố tình lách luật không chạy test. |
| [15_grading_rubrics.md](../guideline/15_grading_rubrics.md) | Frozen Criteria & Chống Criteria Drift | Cơ chế đóng băng tiêu chuẩn qua các chu kỳ phản hồi lặp lại. |

---

## 3. Hướng dẫn thực hành từng bước

### Bước 1: Xây dựng Evidence Tool trả về bằng chứng cấu trúc

Evidence Tool phải trả về dữ liệu có cấu trúc rõ ràng để Grader Model dễ dàng đánh giá:

Tạo file `src/tools/evidence_collector.py`:

```python
"""Evidence Tool thu thập bằng chứng kiểm thử khách quan cho Quality Gate."""

import subprocess
import os
import json
from langchain_core.tools import tool


@tool
def collect_test_evidence(test_file: str = "tests/test_math.py") -> str:
    """Chạy kiểm thử unit test bằng pytest và xuất bằng chứng nghiệm thu có cấu trúc.
    
    Returns:
        Chuỗi JSON chứa:
        - success (bool): True nếu toàn bộ test passed, False nếu có bất kỳ lỗi nào.
        - total_tests (int): Tổng số ca test.
        - passed_tests (int): Số ca test thành công.
        - failed_tests (int): Số ca test thất bại.
        - failure_details (list): Chi tiết các assertion lỗi nếu có.
    """
    workspace_dir = os.path.abspath("workspace")
    full_path = os.path.join(workspace_dir, test_file)
    
    env = os.environ.copy()
    env["PYTHONPATH"] = workspace_dir
    
    cmd = ["pytest", full_path, "-v", "--tb=short"]
    
    try:
        proc = subprocess.run(cmd, cwd=workspace_dir, env=env, capture_output=True, text=True, timeout=30)
        output = proc.stdout + "\n" + proc.stderr
        
        is_success = (proc.returncode == 0)
        
        evidence = {
            "execution_tool": "pytest",
            "target_file": test_file,
            "success": is_success,
            "exit_code": proc.returncode,
            "raw_output_snippet": output[-500:],  # Lấy 500 ký tự cuối
        }
        return json.dumps(evidence, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
```

### Bước 2: Thiết lập Rubric Criteria và Grader Model

Tạo file `src/quality_gate.py`:

```python
"""Cấu hình RubricMiddleware và khởi tạo Coding Agent có Quality Gate."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.middleware.rubric import RubricMiddleware

from src.backend import get_workspace_backend
from src.tools.evidence_collector import collect_test_evidence

load_dotenv()

# BỘ TIÊU CHÍ NGHIỆM THU NGUYÊN TỬ (RUBRIC)
SOFTWARE_QUALITY_RUBRIC = """
TIÊU CHUẨN NGHIỆM THU CHẤT LƯỢNG MÃ NGUỒN:
1. Tính đúng đắn (Correctness): Toàn bộ các ca kiểm thử trong `tests/test_math.py` phải đạt trạng thái PASS 100%. 
   Bằng chứng bắt buộc: Phải có kết quả thực thi từ tool `collect_test_evidence` với trường `"success": true`.
2. Tính toàn vẹn (Integrity): Mã nguồn không được chứa các lệnh in tạm thời vô nghĩa (như print('debug')) và phải có docstring rõ ràng cho mọi hàm mới.
3. Nguyên tắc bằng chứng (Evidence Rule): Nếu không có kết quả gọi tool `collect_test_evidence` trong phiên làm việc, đánh giá là UNSATISFIED ngay lập tức!
"""


def build_agent_with_quality_gate():
    # 1. Working Model: Dùng model mạnh để viết code
    working_model = ChatOpenAI(
        model=os.getenv("AGENTSEEK_MODEL", "zai-org/GLM-5.2"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1"),
        temperature=0.1,
    )

    # 2. Grader Model: Dùng model nhẹ, chi phí rẻ và khách quan để làm giám khảo
    grader_model = ChatOpenAI(
        model=os.getenv("AGENTSEEK_MODEL", "zai-org/GLM-5.2"),  # Hoặc dùng model rẻ hơn như gpt-4o-mini
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1"),
        temperature=0.0,
    )

    backend = get_workspace_backend("workspace")

    # 3. Khởi tạo RubricMiddleware
    rubric_middleware = RubricMiddleware(
        grader_model=grader_model,
        rubric=SOFTWARE_QUALITY_RUBRIC,
        evidence_tools=["collect_test_evidence"],  # Bắt buộc phải có bằng chứng từ tool này
    )

    system_prompt = """Bạn là một Senior Developer làm việc trong dự án có hệ thống Quality Gate tự động.
Mọi công việc của bạn chỉ được nghiệm thu khi bạn chạy tool `collect_test_evidence` và đạt kết quả 100% pass!
Tuyệt đối không tự ý tuyên bố xong việc khi chưa thu thập bằng chứng kiểm thử!
"""

    agent = create_deep_agent(
        model=working_model,
        tools=[collect_test_evidence],
        backend=backend,
        middleware=[rubric_middleware],
        system_prompt=system_prompt,
    )
    return agent


if __name__ == "__main__":
    bot = build_agent_with_quality_gate()
    
    task = (
        "Kiểm tra lại toàn bộ file `src/math_service.py` và `tests/test_math.py`. "
        "Hãy đảm bảo tất cả các test case đều chạy đúng và thu thập bằng chứng nghiệm thu."
    )
    
    print(f"[YÊU CẦU NGHIỆM THU]: {task}\n")
    response = bot.invoke({"messages": [{"role": "user", "content": task}]})
    
    print("\n--- KẾT QUẢ NGHIỆM THU TỪ QUALITY GATE ---")
    print(response["messages"][-1].content)
```

---

## 4. Kịch bản thực chiến (End-to-End Walkthrough)

Chạy thử nghiệm Agent với Quality Gate:

```bash
python -m src.quality_gate
```

**Quan sát chu trình kiểm duyệt tự động**:
1. **Lượt 1 (Working Model sửa code)**: Working Model đọc code, sửa một hàm trong `math_service.py`. Nó định tuyên bố hoàn tất.
2. **Quality Gate can thiệp (Grader Model đánh giá)**:
   - Grader Model kiểm tra lịch sử: Thấy Working Model **chưa hề gọi** `collect_test_evidence`.
   - Cờ `unverified` được bật!
   - Grader Model phản hồi ngược lại cho Working Model: *"Từ chối nghiệm thu: Bạn chưa cung cấp bằng chứng thực thi từ collect_test_evidence!"*.
3. **Lượt 2 (Working Model buộc phải tuân thủ)**:
   - Nhận được phản hồi từ chối, Working Model lập tức gọi tool `collect_test_evidence()`.
   - Tool chạy pytest thật và trả về JSON: `{"success": true, "exit_code": 0}`.
4. **Quality Gate nghiệm thu lần 2**:
   - Grader Model đọc JSON bằng chứng: Thấy `"success": true` khớp tiêu chí 1 của Rubric.
   - Grader Model phê duyệt: `satisfied` (Không có cờ unverified).
5. **Hoàn tất**: Tiến trình kết thúc, người dùng nhận được kết quả kèm báo cáo kiểm thử được chứng thực.

---

## 5. Checkpoint — Tự kiểm tra

- [ ] Nếu bạn cố tình xóa tool `collect_test_evidence` hoặc không cho Agent gọi tool, Agent **không bao giờ có thể tự kết thúc thành công** (luôn bị Grader Model bắt bẻ).
- [ ] Khi test trong workspace bị fail, Grader Model từ chối nghiệm thu và chỉ rõ thông báo lỗi pytest cho Working Model sửa tiếp.
- [ ] Khi toàn bộ test pass và có output JSON bằng chứng, Grader Model tự động phê chuẩn nghiệm thu.

---

## 6. Lỗi thường gặp & Best Practices

1. **Viết Rubric quá chung chung hoặc mang tính cảm tính**:
   - *Sai*: "Code phải viết đẹp, sạch sẽ". (LLM không thể đo lường tính "đẹp").
   - *Đúng*: "Code phải pass pytest và không có cảnh báo nào từ flake8 khi kiểm tra file".
2. **Dùng model quá yếu làm Grader Model**:
   - Grader Model cần khả năng tuân thủ cấu trúc logic nghiêm ngặt để không bị Working Model "thao túng tâm lý". Hãy dùng ít nhất các model tier GPT-4o-mini hoặc tương đương.
3. **Quên khai báo `evidence_tools`**:
   - Luôn liệt kê tên tool thực tế vào tham số `evidence_tools=["..."]` để middleware tự động kích hoạt cơ chế chống gian lận `unverified`.
