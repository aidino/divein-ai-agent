# Chương 9: Human-in-the-Loop — Xây Dựng Quy Trình Phối Hợp Người - Máy An Toàn Và Tin Cậy

> Càng trao cho AI Agent quyền tự chủ lớn, chúng ta càng cần thiết lập ranh giới an toàn nghiêm ngặt. Khi Agent chuẩn bị xóa một tệp tin dữ liệu, gửi email hàng loạt tới khách hàng, hoặc gọi một API thanh toán đắt đỏ, liệu bạn có muốn nó phải "xin phép một tiếng" trước khi bấm nút? 
> Chương này sẽ hướng dẫn bạn làm chủ cơ chế **Human-in-the-Loop (Con người trong vòng lặp - HITL)** — giải pháp bổ sung các trạm kiểm duyệt của con người vào các thao tác nhạy cảm, biến AI Agent từ một "hộp đen rủi ro" thành một cộng sự đắc lực, an toàn và hoàn toàn có thể kiểm soát.

---

## Tại Sao Lại Cần Human-in-the-Loop (HITL)?

Tính tự chủ cao của AI Agent là con dao hai lưỡi:
- **Lợi ích to lớn:** Tự động hóa các tác vụ phức tạp, xử lý chuỗi hành động đa bước mà không cần con người kèm cặp từng thao tác.
- **Rủi ro tiềm tàng:** Khi gặp ảo giác (hallucination) hoặc hiểu nhầm ngữ cảnh, Agent có thể gây ra những hậu quả nghiêm trọng — xóa nhầm file mã nguồn, gửi email sai nội dung tới ban giám đốc, hoặc kích hoạt các tiến trình tiêu tốn hàng nghìn USD.

Trong thực tế doanh nghiệp, chúng ta không thể chọn giữa hai thái cực cực đoan: hoặc "thả rông hoàn toàn" (fully autonomous), hoặc "bắt người làm hết" (manual). Chúng ta cần một **vùng đệm an toàn có thể kiểm soát (Controllable Middle Ground)**:
- Trước khi xóa dữ liệu $\rightarrow$ Bắt buộc dừng lại để người dùng bấm nút xác nhận.
- Trước khi gửi email ra bên ngoài $\rightarrow$ Trình bày bản thảo để người dùng kiểm tra người nhận và nội dung, cho phép sửa trước khi gửi.
- Trước khi triển khai code lên môi trường Production $\rightarrow$ Cần sự phê duyệt từ Technical Lead.

Đó chính là sứ mệnh của **Human-in-the-Loop (HITL)**: Agent sẽ tạm dừng (pause/interrupt) trước các thao tác nhạy cảm, chờ đợi con người đưa ra quyết định (**Phê duyệt, Chỉnh sửa, Từ chối hoặc Trực tiếp trả lời**), sau đó mới tiếp tục guồng quay thực thi.

---

## Cấu Hình Trạm Kiểm Duyệt Với `interrupt_on`

Deep Agents cung cấp tham số khai báo cấp cao `interrupt_on` để xác định công cụ nào cần sự can thiệp của con người. 

Khi bạn thiết lập tham số này, Deep Agents sẽ tự động bổ sung `HumanInTheLoopMiddleware` vào ngăn xếp middleware mặc định. Đồng thời, `PatchToolCallsMiddleware` cũng được kích hoạt để tự động làm sạch và sửa chữa lịch sử tin nhắn nếu phiên chạy bị ngắt hoặc hủy ngang giữa chừng.

```python
import os
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

# Khởi tạo mô hình hỗ trợ Tool Calling
model = ChatOpenAI(
    model=os.environ.get("MODEL_NAME", "zai-org/GLM-5.2"),
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

# Khai báo các công cụ nghiệp vụ
@tool
def delete_file(path: str) -> str:
    """Xóa tệp tin được chỉ định."""
    return f"Đã xóa thành công tệp: {path}"

@tool
def read_file(path: str) -> str:
    """Đọc nội dung tệp tin."""
    return f"Nội dung của {path}..."

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Gửi email thông báo."""
    return f"Đã gửi email thành công tới: {to}"

# BẮT BUỘC: Checkpointer là điều kiện tiên quyết của HITL!
checkpointer = MemorySaver()

agent = create_deep_agent(
    model=model,
    tools=[delete_file, read_file, send_email],
    interrupt_on={
        # Xóa file: Cho phép duyệt, chỉnh sửa đường dẫn hoặc từ chối
        "delete_file": {"allowed_decisions": ["approve", "edit", "reject"]},
        
        # Đọc file: Hoàn toàn an toàn, cho phép chạy thẳng không cần hỏi
        "read_file": False,
        
        # Gửi email: Chỉ được phép duyệt hoặc từ chối, KHÔNG cho phép sửa tham số
        "send_email": {"allowed_decisions": ["approve", "reject"]},
    },
    checkpointer=checkpointer,  # Bắt buộc phải có Checkpointer để lưu trạng thái tạm dừng
)
```

---

### Ba Giá Trị Cấu Hình Cho Từng Công Cụ

Trong từ điển `interrupt_on`, giá trị tương ứng với mỗi tên công cụ có thể là:

| Giá trị cấu hình | Ý nghĩa kỹ thuật | Hành vi thực tế |
|---|---|---|
| `True` | Kích hoạt kiểm duyệt toàn diện | Agent luôn tạm dừng khi gọi công cụ này; mở toàn bộ 4 loại quyết định (`approve`, `edit`, `reject`, `respond`). |
| `False` | Tắt kiểm duyệt (Bỏ qua) | Agent thực thi công cụ trực tiếp ngay lập tức, không làm gián đoạn luồng chạy. |
| `{"allowed_decisions": [...]}` | Giới hạn quyền quyết định | Kích hoạt ngắt, nhưng chỉ cho phép con người thực hiện các hành động được liệt kê trong danh sách. |

---

### Bốn Quyết Định Của Con Người (Decisions)

Khi Agent rơi vào trạng thái tạm dừng, con người có thể phản hồi lại 1 trong 4 loại quyết định sau:

| Quyết định (`type`) | Ý nghĩa hành động | Kịch bản áp dụng thực tế |
|---|---|---|
| `approve` | **Phê duyệt:** Chấp thuận thực thi công cụ với đúng các tham số mà Agent đề xuất ban đầu. | *"Xác nhận xóa đúng file rác này rồi, chạy đi."* |
| `edit` | **Chỉnh sửa:** Can thiệp sửa đổi lại một hoặc nhiều tham số trước khi kích hoạt công cụ. | *"Đổi lại danh sách email nhận tin trước khi gửi."* |
| `reject` | **Từ chối:** Hủy bỏ lượt gọi công cụ này, đồng thời gửi phản hồi giải thích lý do để Agent biết đường chuyển hướng. | *"Không được xóa thư mục này, hãy nén lưu trữ lại!"* |
| `respond` | **Trực tiếp trả lời:** Không kích hoạt công cụ, lấy trực tiếp nội dung tin nhắn của con người đóng gói thành kết quả trả về của công cụ. | Dùng riêng cho các công cụ dạng câu hỏi người dùng như `ask_user`. |

> ⚠️ **CẢNH BÁO QUAN TRỌNG: PHÂN BIỆT RẠCH RÒI GIỮA `reject` VÀ `respond`!**
> 
> - **Khi bạn muốn ngăn chặn một hành động nguy hiểm** (xóa file, ghi database, gửi email, deploy), bạn **BẮT BUỘC PHẢI DÙNG `reject`**. Khi nhận được `reject`, Agent hiểu rằng công cụ **chưa hề được chạy** và thao tác đã bị chặn.
> - **Tuyệt đối KHÔNG dùng `respond` để từ chối hành động!** Vì trong kiến trúc LLM, giá trị trả về của `respond` sẽ được đóng gói thành một `ToolMessage` mang trạng thái **THÀNH CÔNG**. Nếu bạn dùng `respond` với nội dung *"Tôi không cho bạn xóa file"*, LLM có thể hiểu lầm là công cụ xóa file đã chạy xong xuôi và hồ hởi thông báo: *"Tôi đã hoàn tất việc xóa file theo yêu cầu!"*.
> 
> **3 Nguyên tắc ghi nhớ nhanh:**
> 1. Không đồng ý làm $\rightarrow$ Dùng `reject` (kèm lời nhắn giải thích lý do và gợi ý bước tiếp theo).
> 2. Đồng ý nhưng cần sửa lại chi tiết $\rightarrow$ Dùng `edit` (chỉ sửa các trường cần thiết).
> 3. Công cụ sinh ra vốn để hỏi ý kiến người dùng $\rightarrow$ Dùng `respond` (đóng vai trò là câu trả lời của con người).

---

## Điều Kiện Ngắt Linh Hoạt (`when` Predicate)

Mặc định, nếu một công cụ được cấu hình trong `interrupt_on`, mọi lần gọi công cụ đó đều sẽ kích hoạt trạng thái ngắt. Tuy nhiên, trong thực tế, không phải lúc nào thao tác ghi file cũng nguy hiểm. Ví dụ: ghi file vào thư mục nháp `/workspace/` là vô hại, nhưng ghi đè vào thư mục cấu hình hệ thống `/etc/` hoặc `/secrets/` mới đáng báo động.

Bắt đầu từ `langchain>=1.3.3`, bạn có thể bổ sung hàm điều kiện `when`:
- Nhận vào đối tượng `ToolCallRequest`.
- Trả về `True`: Kích hoạt ngắt và chờ người duyệt.
- Trả về `False`: An toàn, tự động cho qua (*auto-bypass*).

```python
from deepagents import create_deep_agent
from langchain.agents.middleware import ToolCallRequest
from langgraph.checkpoint.memory import MemorySaver

def writes_outside_workspace(request: ToolCallRequest) -> bool:
    """Chỉ kích hoạt ngắt khi Agent cố tình ghi file ra ngoài thư mục an toàn /workspace/."""
    args = request.tool_call.get("args", {})
    target_path = args.get("file_path", "")
    # Nếu đường dẫn không bắt đầu bằng /workspace/ -> Báo động! Cần người duyệt.
    return not target_path.startswith("/workspace/")

agent = create_deep_agent(
    model=model,
    interrupt_on={
        "write_file": {
            "allowed_decisions": ["approve", "edit", "reject"],
            "when": writes_outside_workspace,  # Gắn hàm điều kiện
        },
    },
    checkpointer=MemorySaver(),
)
```

> 💡 **Lợi ích thực tiễn:**
> Nhờ có vị từ `when`, giao diện phê duyệt của người dùng sẽ không bị "ô nhiễm" bởi hàng trăm thông báo xác nhận vặt vãnh. Con người chỉ bị làm phiền khi Agent thực sự chạm vào các ranh giới rủi ro cao.

---

## Vòng Đời Hoàn Chỉnh: Tạm Dừng & Phục Hồi Thực Thi (Interrupt & Resume)

Khi Agent phát sinh một lệnh gọi công cụ nằm trong danh sách kiểm duyệt, luồng thực thi sẽ diễn ra theo 4 nhịp rõ ràng:

1. **Thực thi bình thường:** Agent suy luận cho đến khi quyết định gọi công cụ nhạy cảm.
2. **Kích hoạt ngắt (Suspend/Interrupt):** Tiến trình dừng lại, Checkpointer lưu trạng thái đồ thị, phương thức `invoke()` trả về danh sách các `interrupts`.
3. **Con người đánh giá:** Người dùng xem xét chi tiết tên công cụ, tham số và đưa ra quyết định.
4. **Phục hồi tiến trình (Resume):** Gửi quyết định qua `Command(resume=...)` với **cùng một `thread_id`** để đánh thức Agent tiếp tục công việc.

![Quy trình thực thi Human-in-the-Loop: Agent chạy → Đánh giá ngắt → Con người ra quyết định → Thực thi hoặc hủy bỏ → Phục hồi đồ thị](https://datawhalechina.github.io/deepagents-in-action/imgs/17-flowchart-hitl-flow.png)

### Triển Khai Bằng Mã Nguồn Thực Tế:

```python
import uuid
from langgraph.types import Command

# BẮT BUỘC: Khởi tạo thread_id duy nhất để định danh phiên làm việc này
thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}

# ------------------------------------------------------------------------------
# Bước 1: Khởi động yêu cầu của người dùng
# ------------------------------------------------------------------------------
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Hãy xóa tệp dữ liệu temp.txt"}]},
    config=thread_config,
    version="v2",  # BẮT BUỘC: version="v2" để kích hoạt đầy đủ cấu trúc dữ liệu của HITL
)

# ------------------------------------------------------------------------------
# Bước 2: Kiểm tra xem tiến trình có bị rơi vào trạng thái tạm dừng hay không
# ------------------------------------------------------------------------------
if result.interrupts:
    # Lấy thông tin chi tiết về yêu cầu ngắt đầu tiên
    interrupt_payload = result.interrupts[0].value
    action_requests = interrupt_payload["action_requests"]
    review_configs = interrupt_payload["review_configs"]
    config_lookup = {cfg["action_name"]: cfg for cfg in review_configs}

    print("\n🚨 [HỆ THỐNG CẢNH BÁO]: Agent đang yêu cầu phê duyệt hành động nhạy cảm!")
    
    for action in action_requests:
        tool_name = action["name"]
        # Lưu ý tính tương thích: một số phiên bản dùng 'arguments', số khác dùng 'args'
        tool_args = action.get("arguments", action.get("args", {}))
        allowed = config_lookup[tool_name]["allowed_decisions"]
        
        print(f" -> Tên công cụ: {tool_name}")
        print(f" -> Tham số dự kiến: {tool_args}")
        print(f" -> Các lựa chọn bạn có thể đưa ra: {allowed}")

    # --------------------------------------------------------------------------
    # Bước 3: Người dùng ra quyết định (Ở đây ví dụ ta chọn 'approve')
    # --------------------------------------------------------------------------
    user_decisions = [
        {"type": "approve"}  # Chấp thuận cho xóa
    ]

    # --------------------------------------------------------------------------
    # Bước 4: Đánh thức Agent và tiếp tục thực thi
    # --------------------------------------------------------------------------
    print("\nĐang gửi quyết định phê duyệt và tiếp tục tiến trình...")
    result = agent.invoke(
        Command(resume={"decisions": user_decisions}),
        config=thread_config,  # CỰC KỲ QUAN TRỌNG: Phải dùng chính xác thread_id cũ!
        version="v2",
    )

# In kết quả cuối cùng mà Agent gửi lại sau khi công cụ đã chạy xong
print("\n[Phản hồi cuối cùng từ Agent]:")
print(result.value["messages"][-1].content)
```

---

### 4 Yêu Cầu Kỹ Thuật Sống Còn Khi Triển Khai HITL:

1. **Bắt buộc phải có Checkpointer:** Toàn bộ cơ chế tạm dừng và tiếp tục phụ thuộc vào việc lưu ảnh chụp bộ nhớ (`snapshot`). Không có Checkpointer, hệ thống không thể biết Agent đang dừng ở đâu để phục hồi.
2. **Bắt buộc phải giữ nguyên `thread_id`:** Lệnh `agent.invoke(Command(resume=...), config=...)` phải truyền đúng `thread_id` của phiên đang bị ngắt.
3. **Bắt buộc phải dùng `version="v2"`:** Giao diện gọi hàm v2 của LangGraph chuẩn hóa thuộc tính `result.interrupts` và cấu trúc `Command`.
4. **Số lượng và thứ tự của `decisions` phải khớp tuyệt đối 1:1 với `action_requests`:** Nếu Agent đồng thời gọi 2 công cụ, mảng `decisions` gửi lên phải có đúng 2 phần tử theo đúng thứ tự tương ứng.

---

## Chi Tiết Kỹ Thuật Về Các Quyết Định Phức Tạp

### 1. Từ Chối Kèm Chỉ Dẫn Rõ Ràng (`reject` With Feedback)

Khi người dùng không đồng ý cho Agent thực thi một thao tác, đừng chỉ bấm từ chối cộc lốc! Hãy truyền kèm một thông điệp phản hồi chi tiết trong trường `message`. Thông điệp này sẽ được đóng gói thành một `ToolMessage` mang tính cảnh báo trả về cho LLM:

```python
decisions = [
    {
        "type": "reject",
        "message": (
            "Người dùng TỪ CHỐI xóa tệp tin này vì đây là tài liệu kế toán quan trọng. "
            "Tuyệt đối KHÔNG thử xóa lại! Hãy hỏi người dùng xem có muốn nén tệp tin "
            "vào thư mục /archive/ để lưu trữ hay không."
        ),
    }
]

result = agent.invoke(
    Command(resume={"decisions": decisions}),
    config=thread_config,
    version="v2",
)
```

> 💡 **Tại sao thông điệp này lại quan trọng?**
> Nếu không có `message` rõ ràng, Agent có thể rơi vào vòng lặp ngây ngô: bị từ chối $\rightarrow$ tưởng là lỗi tạm thời $\rightarrow$ tiếp tục phát lệnh xóa lần thứ hai. Một câu hướng dẫn dứt khoát giúp Agent nhận biết ranh giới và chủ động đề xuất giải pháp thay thế.

---

### 2. Can Thiệp Chỉnh Sửa Tham Số (`edit`)

Khi bạn đồng ý với hành động của Agent nhưng muốn điều chỉnh một vài tham số (ví dụ: thay đổi địa chỉ email người nhận, sửa đường dẫn file, thêm điều kiện `WHERE` trong câu lệnh SQL):

```python
if result.interrupts:
    action_request = result.interrupts[0].value["action_requests"][0]
    
    # Giả sử Agent định gửi email thông báo tới toàn thể công ty
    # Tham số ban đầu: {"to": "all-company@example.com", "subject": "Bảo trì", ...}
    
    decisions = [
        {
            "type": "edit",
            "edited_action": {
                "name": action_request["name"],  # Bắt buộc phải giữ đúng tên công cụ
                "args": {
                    "to": "dev-team@example.com",  # Người dùng sửa lại chỉ gửi cho team dev
                    "subject": "[Nội bộ Dev] Kế hoạch bảo trì hệ thống",
                    "body": action_request.get("args", {}).get("body", ""),
                },
            },
        }
    ]

    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=thread_config,
        version="v2",
    )
```

> ⚠️ **Lời khuyên thực chiến:** Hãy chỉ can thiệp sửa đổi các tham số mang tính cục bộ (như đổi tên file, đổi email, lọc bớt ID). Việc sửa đổi quá sâu cấu trúc tham số có thể khiến LLM bị hoang mang khi nhận lại kết quả, dẫn tới việc Agent đánh giá lại toàn bộ kế hoạch ban đầu và đưa ra những bước đi không lường trước.

---

### 3. Trực Tiếp Trả Lời Cho Công Cụ Hỏi Người Dùng (`respond`)

Một số công cụ sinh ra không phải để tác động vào hệ thống, mà đóng vai trò là chiếc "cầu nối" để Agent đặt câu hỏi ngược lại cho con người (ví dụ: `ask_user`):

```python
from langchain.tools import tool

@tool
def ask_user(question: str) -> str:
    """Công cụ trừu tượng để Agent phỏng vấn con người khi thiếu dữ liệu đầu vào."""
    return "Đang chờ con người phản hồi..."

agent = create_deep_agent(
    model=model,
    tools=[ask_user],
    interrupt_on={
        # Đối với công cụ này, chỉ mở duy nhất quyền 'respond'
        "ask_user": {"allowed_decisions": ["respond"]},
    },
    checkpointer=checkpointer,
)

# Khi Agent gọi ask_user(question="Bạn muốn lọc doanh thu theo quý nào?"):
decisions = [
    {
        "type": "respond",
        "message": "Hãy lọc theo Quý 3 năm 2026 và loại bỏ dữ liệu môi trường thử nghiệm (staging).",
    }
]

result = agent.invoke(
    Command(resume={"decisions": decisions}),
    config=thread_config,
    version="v2",
)
```

---

## Xử Lý Tình Huống Gọi Nhiều Công Cụ Đồng Thời (Batch Tool Calls)

Các mô hình ngôn ngữ hiện đại (như Claude 3.5, GPT-4o, Gemini 1.5/2.0) thường có khả năng phát sinh nhiều lệnh gọi công cụ song song trong cùng một lượt suy luận (Parallel Tool Calling). Ví dụ: Agent quyết định vừa xóa file cũ vừa gửi email thông báo.

Khi đó, hệ thống sẽ gom tất cả các yêu cầu kiểm duyệt vào **một lần ngắt duy nhất**. Bạn cần duyệt danh sách `action_requests` và cung cấp danh sách `decisions` tương ứng:

```python
# Người dùng yêu cầu: "Xóa tệp temp.log và gửi báo cáo cho sếp"
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Xóa temp.log và gửi mail tới boss@company.com"}]},
    config=thread_config,
    version="v2",
)

if result.interrupts:
    action_requests = result.interrupts[0].value["action_requests"]
    # action_requests[0] -> delete_file(path="temp.log")
    # action_requests[1] -> send_email(to="boss@company.com", ...)

    # Cung cấp quyết định độc lập cho từng công cụ theo đúng thứ tự mảng:
    decisions = [
        {"type": "approve"},  # 1. Đồng ý cho xóa file
        {
            "type": "reject",   # 2. Nhưng TỪ CHỐI gửi email lúc này
            "message": "Không gửi email vào lúc nửa đêm, hãy để sáng mai gửi.",
        },
    ]

    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=thread_config,
        version="v2",
    )
```

---

## Cấu Hình Trạm Kiểm Duyệt Cho Sub-Agents

Trong kiến trúc Multi-Agent, các Sub-Agents có thể sở hữu cấu hình `interrupt_on` hoàn toàn độc lập với Main Agent:

```python
agent = create_deep_agent(
    model=model,
    tools=[delete_file, read_file],
    interrupt_on={
        "delete_file": True,
        "read_file": False,  # Main Agent đọc file hoàn toàn tự do
    },
    subagents=[
        {
            "name": "untrusted-intern-agent",
            "description": "Agent thực tập sinh chuyên hỗ trợ dọn dẹp hệ thống",
            "system_prompt": "Bạn là thực tập sinh dọn dẹp file.",
            "tools": [delete_file, read_file],
            "interrupt_on": {
                "delete_file": True,
                "read_file": True,  # Với Sub-Agent này, NGAY CẢ ĐỌC FILE CŨNG PHẢI XIN PHÉP!
            },
        }
    ],
    checkpointer=checkpointer,
)
```

> 💡 **Ý nghĩa bảo mật:**
> Bạn có thể hoàn toàn tin tưởng Main Agent điều phối cấp cao, nhưng đối với các Sub-Agent chuyên biệt (đặc biệt là các Agent nhận chỉ thị phức tạp hoặc chạy code từ bên ngoài), việc siết chặt chính sách kiểm duyệt sẽ tạo ra lớp phòng thủ theo chiều sâu (Defense-in-Depth).

---

## Mô Hình Phân Tầng Kiểm Duyệt Theo Cấp Độ Rủi Ro (Best Practice)

Không phải công cụ nào cũng cần con người kiểm tra. Việc bắt người dùng xác nhận từng cú nhấp chuột sẽ tạo ra hiện tượng **"mệt mỏi vì cảnh báo" (Alert Fatigue)**, khiến người dùng có xu hướng bấm "Approve" một cách vô thức mà không thèm đọc.

Hãy áp dụng mô hình phân tầng rủi ro 4 cấp độ sau:

![Phân tầng rủi ro: Thấp (không ngắt) → Trung bình (duyệt/từ chối) → Cao (toàn quyền) → Tương tác người (respond)](https://datawhalechina.github.io/deepagents-in-action/imgs/18-infographic-risk-levels.png)

```python
interrupt_on = {
    # =========================================================================
    # 1. CẤP ĐỘ CAO (HIGH RISK): Thao tác phá hủy, không thể đảo ngược, tốn tiền
    # Quyền mở: approve + edit + reject (Tuyệt đối KHÔNG mở 'respond')
    # =========================================================================
    "delete": {"allowed_decisions": ["approve", "edit", "reject"]},
    "delete_file": {"allowed_decisions": ["approve", "edit", "reject"]},
    "write_file": {"allowed_decisions": ["approve", "edit", "reject"]},
    "send_email": {"allowed_decisions": ["approve", "edit", "reject"]},
    "execute_sql_dml": {"allowed_decisions": ["approve", "edit", "reject"]},
    "deploy_production": {"allowed_decisions": ["approve", "edit", "reject"]},

    # =========================================================================
    # 2. CẤP ĐỘ TRUNG BÌNH (MEDIUM RISK): Thay đổi nhỏ, có thể rollback
    # Quyền mở: approve + reject (Không cần mở 'edit' để tránh phức tạp)
    # =========================================================================
    "edit_file": {"allowed_decisions": ["approve", "reject"]},
    "call_external_api": {"allowed_decisions": ["approve", "reject"]},

    # =========================================================================
    # 3. CẤP ĐỘ THẤP (LOW RISK): Chỉ đọc, vô hại, an toàn tuyệt đối
    # Quyền mở: False (Chạy thẳng, không làm phiền người dùng)
    # =========================================================================
    "read_file": False,
    "ls": False,
    "grep": False,
    "glob": False,

    # =========================================================================
    # 4. HỎI Ý KIẾN CON NGƯỜI (HUMAN INPUT):
    # Quyền mở: respond (Con người đóng vai trò là dữ liệu đầu ra của tool)
    # =========================================================================
    "ask_user": {"allowed_decisions": ["respond"]},
}
```

---

## Tích Hợp Với Hệ Thống Phân Quyền Tệp Tin (Filesystem Permissions)

Từ phiên bản `deepagents>=0.6.8`, ngoài việc cấu hình theo tên công cụ qua `interrupt_on`, bạn còn có thể thiết lập điểm ngắt dựa trên **đường dẫn tệp tin thực tế** thông qua `FilesystemPermission`:

```python
from deepagents import FilesystemPermission, create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    model=model,
    permissions=[
        # Bảo vệ tuyệt đối thư mục /secrets/**
        FilesystemPermission(
            operations=["write"],
            paths=["/secrets/**"],
            mode="interrupt",  # Khi Agent ghi vào đây, tự động kích hoạt HITL!
        ),
    ],
    checkpointer=MemorySaver(),
)
```

> 🔍 **Sự kết hợp hoàn hảo:**
> Các yêu cầu ngắt từ `FilesystemPermission` sẽ tự động được gộp chung với các ngắt từ `interrupt_on`. Giao diện phê duyệt của bạn chỉ cần xử lý một cấu trúc dữ liệu duy nhất mà vẫn bảo vệ an toàn được cả hai tầng: tầng công cụ nghiệp vụ và tầng hệ thống tệp tin lưu trữ.

---

## Giải Mã Tầng Động Cơ: Cơ Chế `interrupt()` Của LangGraph

Thực chất, tham số `interrupt_on` của Deep Agents là một lớp vỏ bọc tiện lợi được xây dựng trên nền tảng hàm nguyên thủy **`interrupt()`** của LangGraph. Hiểu rõ bản chất tầng sâu này sẽ giúp bạn xây dựng được những quy trình phê duyệt vô cùng phức tạp mà `interrupt_on` không thể làm được.

### 1. Bản Chất Kỹ Thuật: `interrupt()` Hoạt Động Như Thế Nào?

Khác với hàm `input()` trong lập trình console truyền thống (vốn làm treo luồng CPU để đợi phím gõ), hàm `interrupt()` của LangGraph hoạt động theo cơ chế **Non-blocking Reactive**:

1. **Cơ chế tạm dừng bằng Exception:** Khi mã nguồn gọi hàm `interrupt(value)`, LangGraph sẽ **chủ động ném ra một ngoại lệ đặc biệt (Special GraphInterrupt Exception)**. Ngoại lệ này truyền ngược lên đỉnh ngăn xếp và được Runtime của LangGraph bắt lại.
2. **Snapshot trạng thái:** Runtime lập tức kích hoạt `Checkpointer` để đóng gói toàn bộ trạng thái hiện tại của đồ thị (toàn bộ tin nhắn, bộ nhớ, danh sách todo) và lưu xuống ổ cứng hoặc Database.
3. **Giải phóng tài nguyên:** Tiến trình Python kết thúc lượt chạy một cách êm đẹp và trả về kết quả ngắt cho Client. Server hoàn toàn giải phóng RAM và CPU — người dùng có thể suy nghĩ 5 giây, 5 tiếng hoặc 5 ngày sau mới phê duyệt!
4. **Cơ chế phục hồi (Node Replay):** Khi Client gửi lệnh `Command(resume=payload)`, LangGraph nạp lại snapshot cũ từ Database và **CHẠY LẠI NODE ĐÓ TỪ ĐẦU (REPLAY FROM SCRATCH)**! Khi con trỏ thực thi chạm lại đúng dòng lệnh `interrupt()`, thay vì ném ngoại lệ lần nữa, nó sẽ lập tức lấy giá trị `payload` vừa nhận gán làm kết quả trả về của hàm và chạy tiếp.

![Cơ chế LangGraph Interrupt: Node gọi interrupt() -> ném exception -> Checkpointer lưu trạng thái -> Resume chạy lại node từ đầu](https://datawhalechina.github.io/deepagents-in-action/imgs/29-flowchart-interrupt-state-resume.png)

---

### 2. Tự Định Nghĩa Middleware Phê Duyệt Cuối Cùng (Post-Generation Approval)

Có những trường hợp kiểm duyệt không thuộc về bất kỳ công cụ nào. Ví dụ: Agent đã tổng hợp xong một bản thảo báo cáo tài chính hoặc thông cáo báo chí, bạn muốn **duyệt toàn bộ câu trả lời trước khi hiển thị cho người dùng cuối**.

Ta có thể tạo một Middleware tùy biến kế thừa từ `AgentMiddleware` và gọi `interrupt()` ngay trong hook `after_model`:

```python
from typing import Any
from deepagents import create_deep_agent
from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt

class FinalDraftReviewMiddleware(AgentMiddleware):
    """Middleware chặn lại câu trả lời cuối cùng để con người thẩm định chất lượng."""
    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        last_message = state["messages"][-1]

        # Nếu mô hình đang gọi Tool thì để nó chạy tiếp; ta chỉ bắt câu trả lời cuối cùng
        if not isinstance(last_message, AIMessage) or last_message.tool_calls:
            return None

        # TẠM DỪNG ĐỒ THỊ ĐỂ DUYỆT BẢN THẢO:
        review_decision = interrupt({
            "type": "draft_review",
            "content_to_publish": last_message.content,
            "prompt": "Bạn có đồng ý phát hành nội dung này cho người dùng không?",
        })

        # Nếu người dùng bấm duyệt (approved = True) -> Cho qua
        if review_decision.get("approved"):
            return None

        # Nếu từ chối -> Ghi đè lại thông báo từ chối
        reject_reason = review_decision.get("reason", "Chất lượng chưa đạt yêu cầu.")
        return {
            "messages": [AIMessage(content=f"⚠️ Bản thảo đã bị biên tập viên từ chối: {reject_reason}")]
        }

agent = create_deep_agent(
    model=model,
    middleware=[FinalDraftReviewMiddleware()],
    checkpointer=MemorySaver(),
)
```

---

### 3. Năm Quy Tắc Vàng Khi Làm Việc Với `interrupt()` Của LangGraph

Hiểu được việc "Node sẽ chạy lại từ đầu khi Resume", bạn **bắt buộc phải khắc cốt ghi tâm** 5 quy tắc sau để tránh các lỗi logic chết người:

#### Quy tắc 1: Tuyệt đối KHÔNG bọc `interrupt()` trong khối `try/except Exception` trống rỗng
Vì `interrupt()` hoạt động bằng cách ném ra ngoại lệ nội bộ, nếu bạn bắt `except Exception`, bạn sẽ vô tình "nuốt chửng" tín hiệu ngắt của hệ thống, khiến đồ thị không thể tạm dừng!
```python
# ❌ SAI LẦM NGHIÊM TRỌNG:
try:
    ans = interrupt("Xin ý kiến")
except Exception as e:
    pass  # Tiến trình bị hỏng hoàn toàn!

# ✅ ĐÚNG: Chỉ bắt các ngoại lệ cụ thể bạn quan tâm
try:
    ans = interrupt("Xin ý kiến")
    data = fetch_api()
except NetworkTimeoutError:
    handle_retry()
```

#### Quy tắc 2: Các thao tác có tác dụng phụ (Side-effects) trước `interrupt()` phải có tính lũy đẳng (Idempotent)
Khi đồ thị phục hồi, đoạn mã nằm phía trên `interrupt()` sẽ **chạy lại lần thứ hai**. Nếu bạn thực hiện ghi log vào DB hoặc trừ tiền thẻ tín dụng trước dòng `interrupt()`, hành động đó sẽ bị lặp lại hai lần!
```python
# ❌ SAI:
def process_order(state):
    db.insert_order(...)  # Bị nhân đôi khi phục hồi!
    confirm = interrupt("Xác nhận thanh toán?")
    return {"status": "done"}

# ✅ ĐÚNG: Chuyển toàn bộ hành động thay đổi trạng thái ra SAU dòng interrupt
def process_order(state):
    confirm = interrupt("Xác nhận thanh toán?")
    if confirm:
        db.insert_order(...)  # Chỉ chạy đúng 1 lần sau khi người duyệt đồng ý
    return {"status": "done"}
```

#### Quy tắc 3: Thứ tự gọi `interrupt()` trong cùng một node phải cố định
LangGraph ánh xạ các điểm ngắt trong một node dựa trên **chỉ số thứ tự (index)**. Không đặt `interrupt()` bên trong các câu lệnh `if/else` có điều kiện thay đổi thất thường giữa các lượt chạy.

#### Quy tắc 4: Khi có nhiều nhánh song song bị ngắt, dùng `Interrupt.id` để đối soát
Nếu đồ thị của bạn chạy phân nhánh song song và cùng lúc phát sinh 2 điểm ngắt, hãy sử dụng từ điển ánh xạ theo `intr.id` thay vì truyền danh sách theo thứ tự:
```python
resume_payload = {
    intr.id: user_answers[intr.id]
    for intr in result.interrupts
}
agent.invoke(Command(resume=resume_payload), config=config, version="v2")
```

#### Quy tắc 5: Xây dựng biểu mẫu nhiều bước bằng Vòng lặp StateGraph thay vì `while True`
Nếu bạn cần người dùng nhập liệu và muốn kiểm tra tính hợp lệ (ví dụ: tuổi phải là số dương), **tuyệt đối không viết vòng lặp `while True` rồi gọi `interrupt()` liên tục trong cùng một hàm node**. Hãy tạo một nút kiểm tra và sử dụng **Cạnh điều kiện (Conditional Edge)** để quay vòng lại nút đó nếu dữ liệu chưa đạt chuẩn.

---

## Bảng Tra Cứu: Khi Nào Dùng `interrupt_on` vs Khi Nào Dùng `interrupt()`?

| Tình huống bài toán | Giải pháp tối ưu | Lý do kỹ thuật |
|---|---|---|
| **Cần duyệt trước khi chạy một công cụ cụ thể** | `interrupt_on={"tool_name": ...}` | Cực kỳ ngắn gọn, tự động sinh `action_requests` chuẩn mực. |
| **Chỉ duyệt công cụ khi tham số thỏa điều kiện nguy hiểm** | `interrupt_on` + hàm `when` | Lọc bớt cảnh báo rác, giữ nguyên cấu trúc xét duyệt chuẩn. |
| **Duyệt câu trả lời cuối cùng của Agent trước khi gửi khách** | Custom Middleware + `interrupt()` | Can thiệp ở tầng vòng đời mô hình (`after_model`), độc lập với công cụ. |
| **Quy trình thu thập thông tin người dùng theo biểu mẫu** | Node chuyên trách + `interrupt()` + StateGraph | Không phải là công cụ, mà là logic điều phối luồng nghiệp vụ. |
| **Đặt breakpoint để debug đồ thị lúc phát triển** | `interrupt_before` / `interrupt_after` | Điểm ngắt tĩnh lúc biên dịch đồ thị, không cần sửa code bên trong node. |

---

## Tổng Kết

Cơ chế **Human-in-the-Loop** là tấm lá chắn quan trọng nhất để đưa AI Agent từ môi trường thử nghiệm ra khai thác an toàn trong sản xuất thực tế:

1. **Cân bằng hoàn hảo:** Giữ được năng lực tự động hóa của Agent nhưng kiểm soát tuyệt đối các điểm nghẽn rủi ro cao.
2. **Khai báo tường minh:** Dễ dàng cấu hình thông qua `interrupt_on` với 4 quyền quyết định sắc bén (`approve`, `edit`, `reject`, `respond`).
3. **Phân biệt đúng công cụ:** Tuyệt đối không dùng `respond` để từ chối các hành động phá hủy; hãy dùng `reject` kèm thông điệp định hướng rõ ràng.
4. **Kiểm duyệt có điều kiện:** Ứng dụng vị từ `when` để chỉ đánh thức con người khi thao tác thực sự chạm ngưỡng nguy hiểm.
5. **Nắm vững bản chất:** `interrupt()` hoạt động dựa trên cơ chế ném ngoại lệ $\rightarrow$ Checkpointer lưu ảnh chụp $\rightarrow$ Replay lại node từ đầu khi Resume. Tuân thủ tính lũy đẳng để loại trừ lỗi lặp hành động.

Ở chương tiếp theo, chúng ta sẽ khám phá giải pháp bảo vệ an toàn ở tầng hạ tầng: **Code Execution Sandbox (Môi Trường Hộp Cát Thực Thi Mã)** — cho phép Agent thoải mái chạy các script phức tạp bên trong các container cô lập hoàn toàn với máy chủ thật.
