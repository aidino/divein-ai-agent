# Chương 6: Async Sub-Agents — Để Main Agent Điều Phối Nhiều Tác Vụ Ngầm Song Song

> Ở chương trước, chúng ta đã tìm hiểu về Sub-Agent đồng bộ (Synchronous Sub-Agent), nơi Main Agent ủy quyền qua công cụ `task` và **bị chặn (block) để chờ** Sub-Agent chạy xong. Tuy nhiên, khi một tác vụ phụ tốn vài phút hay thậm chí hàng chục phút, Main Agent sẽ rơi vào "trạng thái đơ (freeze)" trước mặt người dùng — không thể tiếp tục trò chuyện, cũng không thể can thiệp điều chỉnh hướng đi. Chương này sẽ đưa bạn khám phá tính năng preview quan trọng từ bản Deep Agents 0.5.0: **Async Sub-Agent (Sub-Agent Bất Đồng Bộ)** — Main Agent nhận ngay mã Task ID rồi quay lại tiếp tục trò chuyện với người dùng, trong khi Sub-Agent âm thầm chạy ngầm phía sau; người dùng có thể tra cứu tiến độ, bổ sung yêu cầu hoặc hủy ngang bất kỳ lúc nào.

> ⚠️ **LƯU Ý VỀ MÔI TRƯỜNG VÀ MÔ HÌNH VẬN HÀNH (PREVIEW FEATURE)**
> 
> Async Sub-Agent là tính năng thử nghiệm (**preview feature**) từ `deepagents>=0.5.0`, vẫn đang được hoàn thiện nên API có thể thay đổi trong tương lai. Khác với các chương trước khi bạn chỉ cần gọi trực tiếp `agent.invoke()` trong một tiến trình Python thông thường, các ví dụ trong chương này yêu cầu chạy trong môi trường **LangGraph Server hỗ trợ Agent Protocol**.
> 
> Trước khi bắt đầu, cần nắm vững 4 yếu tố then chốt:
> 1. Khai báo Main Agent và các Async Sub-Agent trong file cấu hình `langgraph.json`.
> 2. Giá trị `AsyncSubAgent.graph_id` bắt buộc phải khớp chính xác với tên graph được đăng ký trong cấu hình.
> 3. Khởi động máy chủ cục bộ bằng lệnh `langgraph dev`.
> 4. Cung cấp đủ số lượng worker slot chạy song song thông qua cờ `--n-jobs-per-worker`.
> 
> *(Bạn hoàn toàn không cần server đám mây để học chương này: bài viết cung cấp sẵn một ví dụ tối thiểu hoàn chỉnh chạy cục bộ qua cơ chế ASGI ngay bên dưới).*

---

## Nút Thắt Cổ Chai Của Sub-Agent Đồng Bộ

Hãy nhìn lại mô hình gọi Sub-Agent đồng bộ ở Chương 5:

```python
# Main Agent gọi Sub-Agent đồng bộ
result = task(name="researcher", task="Nghiên cứu chuyên sâu hệ sinh thái LangGraph")
# Tại thời điểm này, Main Agent HOÀN TOÀN BỊ ĐÓNG BĂNG để chờ đợi...
# Quá trình này có thể kéo dài 60s, 120s hoặc lâu hơn nữa.
# Người dùng chỉ biết ngồi nhìn biểu tượng loading quay tròn trong vô vọng!
```

Mô hình đồng bộ bộc lộ sự bất lực trong 2 tình huống thực tế:
1. **Các tác vụ dài hơi (Long-running tasks)**: Nghiên cứu thị trường sâu, di chuyển mã nguồn quy mô lớn, cào và xử lý dữ liệu hàng loạt — thời gian chạy từ vài phút đến cả tiếng đồng hồ.
2. **Các tác vụ cần tương tác giữa chừng (Interactive tasks)**: Khi Sub-Agent đang chạy được 50%, người dùng chợt nhớ ra cần bổ sung điều kiện (*"Tìm thêm số liệu năm 2024 nhé"*, *"Đổi sang nguồn dữ liệu khác đi"*). Nhưng ở chế độ đồng bộ, người dùng hoàn toàn bị khóa miệng, không thể chen ngang.

Tệ hại hơn cả: trong suốt thời gian Sub-Agent đang cày cuốc, **bản thân Main Agent cũng bị phong tỏa luồng thực thi**. Người dùng muốn hỏi một câu chuyện phiếm bên lề hoặc nhờ định dạng một đoạn text cũng không thể làm được.

Async Sub-Agent ra đời để giải quyết triệt để 2 vấn đề này: **Giải phóng hoàn toàn luồng trò chuyện của Main Agent** và **Hỗ trợ can thiệp, điều khiển tác vụ ngay khi đang chạy**.

---

## So Sánh Chi Tiết: Sync vs. Async Sub-Agents

| Tiêu chí | Sync Sub-Agent (Đồng bộ) | Async Sub-Agent (Bất đồng bộ) |
|---|---|---|
| **Mô hình thực thi** | **Blocking**: Main Agent phải đợi Sub-Agent xong hẳn mới được chạy tiếp | **Non-blocking**: Main Agent nhận ngay `task_id` trong vài mili-giây rồi nhả quyền kiểm soát |
| **Tính đồng thời** | Có thể gọi song song nhưng Main Agent vẫn bị block toàn bộ thời gian chờ | Chạy song song độc lập hoàn toàn, Main Agent tự do trò chuyện |
| **Bổ sung chỉ thị giữa chừng** | ❌ **Không hỗ trợ** | ✅ **Hỗ trợ** qua công cụ `update_async_task` |
| **Hủy bỏ tác vụ** | ❌ **Không hỗ trợ** | ✅ **Hỗ trợ** qua công cụ `cancel_async_task` |
| **Quản lý trạng thái (Statefulness)** | Stateless: Mỗi lần gọi là một phiên độc lập | Stateful: Sub-Agent sở hữu thread riêng, tích lũy lịch sử hội thoại liên tục |
| **Kịch bản phù hợp** | Tác vụ ngắn hạn dưới 5 giây, hỏi-đáp nhanh gọn | Tác vụ nặng kéo dài từ vài phút trở lên, cần theo dõi và can thiệp linh hoạt |

![So sánh Sync vs Async: Bên trái bị block và phải chờ đợi; Bên phải nhận Task ID ngay, tự do chat, tra cứu tiến độ, bổ sung lệnh hoặc hủy](../public/imgs/15-comparison-sync-vs-async.png)

> 💡 **Quy tắc lựa chọn nhanh:**
> - Nếu tác vụ phụ cam kết hoàn tất trong **dưới 5 giây** $\rightarrow$ Dùng **Sync Sub-Agent** (đơn giản, ít tốn tài nguyên hạ tầng).
> - Nếu tác vụ kéo dài **từ vài phút trở lên** và người dùng cần tương tác liên tục $\rightarrow$ Dùng **Async Sub-Agent**.

---

## Cấu Hình Async Sub-Agent

Một Async Sub-Agent được khai báo thông qua class `AsyncSubAgent`. Mỗi instance sẽ trỏ tới một dịch vụ tương thích với chuẩn [Agent Protocol](https://github.com/langchain-ai/agent-protocol) (phổ biến nhất là LangSmith Deployments hoặc máy chủ LangGraph Server do bạn tự host):

```python
from deepagents import AsyncSubAgent, create_deep_agent

async_subagents = [
    AsyncSubAgent(
        name="researcher",
        description="Agent nghiên cứu sâu, chuyên tìm kiếm nhiều nguồn và tổng hợp tài liệu",
        graph_id="researcher",
        # Không truyền url → Mặc định dùng truyền thông nội bộ ASGI (cùng deployment với Main Agent)
    ),
    AsyncSubAgent(
        name="coder",
        description="Agent lập trình, chuyên sinh mã, tái cấu trúc và code review",
        graph_id="coder",
        # url="https://coder-deployment.langsmith.dev"  # Tùy chọn: Gọi qua mạng HTTP từ xa
    ),
]

agent = create_deep_agent(
    model="google_genai:gemini-3.5-flash",
    subagents=async_subagents,
)
```

### Bảng giải thích các thuộc tính của `AsyncSubAgent`:

| Thuộc tính | Bắt buộc | Ý nghĩa kỹ thuật |
|---|:---:|---|
| `name` | ✅ | Định danh duy nhất để Main Agent nhận biết khi gọi lệnh |
| `description` | ✅ | Mô tả chuyên môn, giúp Main Agent đưa ra quyết định ủy quyền chính xác |
| `graph_id` | ✅ | Tên định danh của graph/assistant trên Agent Protocol server (phải khớp chính xác với key trong `langgraph.json`) |
| `url` | Tùy chọn | Nếu bỏ trống: Dùng cơ chế **ASGI in-process**. Nếu khai báo URL: Chuyển sang gọi qua **HTTP từ xa** |
| `headers` | Tùy chọn | Header HTTP tùy biến (dùng truyền API Key / Authentication khi tự host server riêng) |

---

## 5 "Chiếc Remote Điều Khiển" Của Main Agent

Khi bạn khai báo danh sách `AsyncSubAgent`, lớp `AsyncSubAgentMiddleware` sẽ tự động trang bị cho Main Agent **5 công cụ điều khiển từ xa** để thao tác với các tác vụ chạy ngầm:

```
                          ┌────────────────────────┐
                          │       Main Agent       │
                          └───────────┬────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
   [start_async_task]         [check_async_task]       [update_async_task]
   (Khởi chạy, lấy ID)       (Kiểm tra trạng thái)     (Bổ sung yêu cầu mới)
            │                         │
            ▼                         ▼
   [cancel_async_task]        [list_async_tasks]
   (Hủy ngang tác vụ)        (Liệt kê toàn bộ task)
```

| Công cụ (Tool) | Chức năng | Dữ liệu trả về |
|---|---|---|
| `start_async_task` | Khởi động một tác vụ ngầm mới | **Task ID** (trả về tức thì, không chờ) |
| `check_async_task` | Truy vấn tiến độ hiện tại và kết quả | Trạng thái (`running`, `success`, `error`) + Kết quả nếu xong |
| `update_async_task` | Bổ sung thêm chỉ thị mới vào tác vụ đang chạy | Xác nhận cập nhật + Trạng thái mới |
| `cancel_async_task` | Yêu cầu dừng khẩn cấp tác vụ đang chạy | Thông báo xác nhận hủy |
| `list_async_tasks` | Xem danh sách tất cả các tác vụ đang quản lý | Danh sách tổng quan trạng thái các task |

---

### Một Kịch Bản Vận Hành Hoàn Chỉnh

Hãy theo dõi cuộc trò chuyện mẫu dưới đây để thấy sự mượt mà của mô hình bất đồng bộ:

```text
Người dùng: Hãy nghiên cứu chuyên sâu giúp tôi về kiến trúc đa Agent của LangGraph.
Main Agent ──> Gọi start_async_task(description="Nghiên cứu kiến trúc đa Agent...", subagent_type="researcher")
           <── Nhận ngay task_id: "abc-123"
Main Agent ──> Phản hồi người dùng: "Tôi đã giao việc cho researcher chạy ngầm (Task ID: abc-123). 
               Trong lúc chờ, bạn có thể hỏi tôi việc khác hoặc yêu cầu kiểm tra tiến độ bất kỳ lúc nào!"

Người dùng: Tiện tay format giúp tôi đoạn mã Python này với.
Main Agent ──> [Xử lý format code ngay lập tức, trong khi researcher vẫn đang miệt mài cào dữ liệu ở background]

Người dùng: Tác vụ nghiên cứu lúc nãy đã có tin gì mới chưa?
Main Agent ──> Gọi check_async_task("abc-123")
           <── status: "running"
Main Agent ──> Phản hồi người dùng: "Tác vụ vẫn đang chạy, bot đã duyệt qua 4 nguồn tài liệu, dự kiến xong sau ít phút nữa."

Người dùng: Nhớ tập trung phân tích kỹ 3 mô hình này nhé: supervisor, network, và hierarchical.
Main Agent ──> Gọi update_async_task("abc-123", "Bổ sung: Chú trọng 3 mô hình supervisor, network, hierarchical")
           <── Xác nhận đã chèn chỉ thị mới vào luồng đang chạy của researcher

Người dùng: Thôi, tôi đổi ý rồi, không cần nghiên cứu nữa đâu.
Main Agent ──> Gọi cancel_async_task("abc-123")
           <── status: "cancelled"
Main Agent ──> Phản hồi người dùng: "Đã hủy bỏ tác vụ nghiên cứu thành công!"
```

![Vòng đời Async Sub-Agent: launch -> tiếp tục chat -> check -> update -> cancel -> list. Main Agent không bao giờ bị nghẽn](../public/imgs/16-flowchart-async-lifecycle.png)

---

### Bản Chất Kỹ Thuật Bên Dưới Của 5 Công Cụ

Hiểu rõ cơ chế tầng sâu giúp bạn viết prompt điều hướng mô hình chuẩn xác hơn:

- **`start_async_task` (Launch)**: Gửi request tới Agent Protocol service để **tạo mới một Thread** và khởi động một Run với prompt ban đầu. Hàm lập tức trả về `thread_id` (chính là `task_id`) cho Main Agent mà **hoàn toàn không thăm dò (polling) chờ đợi**.
- **`check_async_task` (Check)**: Đọc trạng thái Run hiện tại. Nếu Run đã kết thúc (`success`), nó đọc tiếp State của Thread con để bóc tách kết quả cuối cùng; nếu vẫn đang chạy, báo về `running`.
- **`update_async_task` (Update)**: Kích hoạt một Run mới trên **chính Thread con đó** với chiến lược ngắt đa nhiệm (`interrupt`). Run cũ bị dừng lại, Sub-Agent được tái khởi động với toàn bộ lịch sử trò chuyện trước đó cộng thêm chỉ thị mới của người dùng. **Task ID được giữ nguyên không đổi**.
- **`cancel_async_task` (Cancel)**: Gọi lệnh `runs.cancel()` trên máy chủ để chấm dứt tiến trình chạy ngầm, đồng thời đánh dấu trạng thái cục bộ là `"cancelled"`.
- **`list_async_tasks` (List)**: Quét danh bạ tất cả các task đã giao. Với các task đã đóng (`success`, `error`, `cancelled`), lấy dữ liệu từ bộ nhớ cache; với các task còn dang dở, gửi truy vấn song song lên máy chủ để cập nhật trạng thái thời gian thực.

![Sơ đồ tuần tự tương tác 3 bên: User, Main Agent và Agent Protocol service qua các nhịp Non-blocking](../public/imgs/17-sequence-async-protocol.png)

---

## Tại Sao Metadata Của Task Phải Lưu Ở State Channel Riêng Biệt?

Trong State Graph của Main Agent, có một channel chuyên biệt mang tên **`async_tasks`**, hoàn toàn tách rời khỏi mảng lịch sử tin nhắn (`messages`). Channel này lưu trữ:
- `task_id`, `subagent_type`, `thread_id`, `run_id`, `status`
- Các mốc thời gian: `created_at`, `last_checked_at`, `last_updated_at`

> 💡 **Giải thích kiến trúc: Tại sao không lưu Task ID trong `ToolMessage` như thông thường?**
> Bởi vì Deep Agents sở hữu cơ chế **tự động tóm tắt và nén lịch sử hội thoại** (đã học ở Chương 3 và Chương 4). 
> Nếu Task ID chỉ sống trong một `ToolMessage` bình thường, thì khi cuộc trò chuyện kéo dài và chạm ngưỡng token, cơ chế Summarization sẽ nén hoặc cắt tỉa các tin nhắn cũ. Hậu quả là: **Main Agent sẽ bị "mất trí nhớ hoàn toàn" về các task nó đã giao**, không còn biết ID là gì để gọi `check` hay `cancel`!
>
> Bằng việc tách sang channel `async_tasks` độc lập: Lịch sử tin nhắn cứ thoải mái bị cắt gọt nén gọn, nhưng danh sách các tác vụ ngầm thì **bất tử**, Main Agent luôn tra cứu lại được qua `list_async_tasks`.

---

## Hai Phương Thức Truyền Tải: ASGI vs. HTTP

### 1. ASGI In-process (Cùng một Deployment — Khuyến nghị dùng)
Khi `AsyncSubAgent` không khai báo thuộc tính `url`, LangGraph SDK sẽ sử dụng **cơ chế truyền tải ASGI nội bộ**: Lời gọi giữa Main Agent và Sub-Agent thực chất là lời gọi hàm trực tiếp trong cùng process bộ nhớ, hoàn toàn không đi qua mạng Internet.

**Ưu thế vượt trội:**
- **Zero Network Latency**: Độ trễ mạng bằng 0.
- **Không cần cấu hình chứng thực phức tạp**: Các Agent sống chung một nhà nên tự động tin tưởng nhau.
- **Vẫn cách ly trạng thái tuyệt đối**: Sub-Agent vẫn chạy trên Thread riêng biệt của Agent Server.

---

### 2. HTTP Remote (Tách biệt máy chủ)
Khi bạn khai báo thêm tham số `url`, SDK sẽ chuyển sang gửi request qua mạng Internet:

```python
AsyncSubAgent(
    name="heavy-analyzer",
    description="Agent xử lý mô hình AI nặng trên cụm GPU riêng",
    graph_id="analyzer",
    url="https://gpu-agents.internal.mycompany.com",
    headers={"Authorization": "Bearer internal-secret-token"},
)
```

**Khi nào nên dùng HTTP từ xa?**
- Sub-Agent đòi hỏi phần cứng đặc thù (cần GPU xịn, dung lượng RAM lớn).
- Sub-Agent có chu kỳ Scale (Auto-scaling) độc lập với Main Agent.
- Sub-Agent do một **team kỹ thuật khác** trong công ty phát triển và duy trì vòng đời release riêng.

---

## Hướng Dẫn Thực Hành: Xây Dựng Bản Demo Tối Thiểu (Chạy Local 100% Qua ASGI)

Dưới đây là dự án thực hành hoàn chỉnh, có thể copy và chạy ngay lập tức trên máy cục bộ để tận mắt thấy cơ chế non-blocking:

### Cấu trúc thư mục dự án:
```text
async-subagent-demo/
├── .env
├── langgraph.json
├── requirements.txt
├── run_demo.py
└── graphs/
    ├── researcher.py
    └── supervisor.py
```

### Bước 1: Cài đặt thư viện
```bash
uv venv
source .venv/bin/activate
uv pip install -U "langgraph-cli[inmem]"
uv pip install deepagents>=0.5.0 langgraph langgraph-sdk langchain-openai
```

### Bước 2: Cấu hình biến môi trường (`.env`)
```dotenv
# Dùng OpenAI
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=lsv2-...

# HOẶC dùng SiliconFlow (tương thích OpenAI API):
# SILICONFLOW_API_KEY=your-key
# MODEL_NAME=zai-org/GLM-5.2
```

### Bước 3: Cấu hình `langgraph.json`
Đăng ký cả `supervisor` và `researcher` trên cùng một Agent Server để kích hoạt đường truyền **ASGI nội bộ**:

```json
{
  "dependencies": ["./"],
  "graphs": {
    "supervisor": "./graphs/supervisor.py:graph",
    "researcher": "./graphs/researcher.py:graph"
  },
  "env": "./.env"
}
```

### Bước 4: Tạo Sub-Agent chạy ngầm giả lập (`graphs/researcher.py`)
Chúng ta cố tình cài đặt hàm `asyncio.sleep(8)` (ngủ 8 giây) để quan sát rõ rệt hành vi chạy nền không làm nghẽn Main Agent:

```python
import asyncio
from langgraph.graph import END, START, MessagesState, StateGraph

async def slow_research(state: MessagesState):
    last_human = state["messages"][-1].content if state["messages"] else "Không có nhiệm vụ."
    # Giả lập tác vụ cào dữ liệu tốn 8 giây
    await asyncio.sleep(8)
    return {
        "messages": [
            {
                "role": "ai",
                "content": (
                    "[researcher đã xử lý xong sau 8 giây]\n"
                    f"Đề tài đã nhận: {last_human}\n"
                    "Kết luận: Async Sub-Agent đã phản hồi task_id tức thì, "
                    "chạy ngầm thành công và có thể cập nhật kết quả bất kỳ lúc nào."
                ),
            }
        ]
    }

builder = StateGraph(MessagesState)
builder.add_node("slow_research", slow_research)
builder.add_edge(START, "slow_research")
builder.add_edge("slow_research", END)
graph = builder.compile()
```

### Bước 5: Tạo Supervisor Main Agent (`graphs/supervisor.py`)
```python
import os
from deepagents import AsyncSubAgent, create_deep_agent

graph = create_deep_agent(
    model=os.environ.get("MODEL_NAME", "openai:gpt-4.1-mini"),
    system_prompt=(
        "Bạn là Agent giám sát (supervisor). Khi người dùng yêu cầu tác vụ nghiên cứu dài hạn, "
        "bạn PHẢI lập tức ủy quyền cho async subagent tên là 'researcher'. "
        "Sau khi gọi start_async_task, hãy trả task_id về cho người dùng và DỪNG LẠI NGAY. "
        "TUYỆT ĐỐI KHÔNG tự ý gọi check_async_task trừ khi người dùng chủ động hỏi tiến độ. "
        "Nếu người dùng muốn thay đổi yêu cầu, hãy gọi update_async_task."
    ),
    subagents=[
        AsyncSubAgent(
            name="researcher",
            description="Dùng cho các nghiên cứu tốn thời gian chạy nền.",
            graph_id="researcher",  # Khớp với key trong langgraph.json, không truyền url để chạy ASGI
        )
    ]
)
```

> ⚠️ **Lưu ý về Checkpointer:**
> Khi chạy qua `langgraph dev`, nền tảng đã tích hợp sẵn hệ thống lưu trữ trạng thái chuyên nghiệp. **Tuyệt đối không truyền `checkpointer=InMemorySaver()` vào `create_deep_agent()`** trong file này, nếu không máy chủ sẽ báo lỗi `ValueError`.

### Bước 6: Khởi động Agent Server cục bộ
Mở terminal và gán tối thiểu 4 worker slots (để đủ chỗ cho 1 Supervisor + các Sub-Agent chạy cùng lúc):

```bash
langgraph dev --n-jobs-per-worker 4
```
Terminal sẽ hiển thị địa chỉ API: `http://127.0.0.1:2024`.

### Bước 7: Viết script kiểm thử tương tác (`run_demo.py`)
Script này mô phỏng người dùng liên tục tương tác trên **cùng một Thread**:

```python
import asyncio
from pprint import pprint
from langgraph_sdk import get_client

client = get_client(url="http://127.0.0.1:2024")
assistant_id = "supervisor"

async def main():
    # 1. Tạo thread hội thoại mới
    thread = await client.threads.create()
    thread_id = thread["thread_id"]
    print("Khởi tạo thread_id =", thread_id)

    # 2. Giao việc cho researcher chạy ngầm
    print("\n[User]: Hãy giao việc nghiên cứu bất đồng bộ cho researcher...")
    first = await client.runs.wait(
        thread_id,
        assistant_id,
        input={"messages": [{"role": "user", "content": "Hãy giao việc cho researcher: Tóm tắt hành vi Async Subagent."}]}
    )
    print("\n=== Phản hồi lượt 1 (Trả về ngay lập tức, không chờ 8s) ===")
    pprint(first["messages"][-1]["content"])

    # 3. Ngay lập tức hỏi tiến độ khi tác vụ vẫn đang chạy
    print("\n[User]: Tác vụ đang chạy thế nào rồi?")
    second = await client.runs.wait(
        thread_id,
        assistant_id,
        input={"messages": [{"role": "user", "content": "Tác vụ chạy ngầm lúc nãy tiến triển sao rồi?"}]}
    )
    print("\n=== Phản hồi lượt 2 (Thấy trạng thái running) ===")
    pprint(second["messages"][-1]["content"])

    # 4. Bổ sung chỉ thị mới vào task đang chạy
    print("\n[User]: Bổ sung thêm yêu cầu mới...")
    third = await client.runs.wait(
        thread_id,
        assistant_id,
        input={"messages": [{"role": "user", "content": "Bổ sung: Viết kết quả dưới dạng 3 dấu gạch đầu dòng nhé."}]}
    )
    print("\n=== Phản hồi lượt 3 (Đã inject thêm chỉ thị) ===")
    pprint(third["messages"][-1]["content"])

asyncio.run(main())
```

Chạy file: `python run_demo.py`. Bạn sẽ chứng kiến phản hồi lượt 1 trả về ngay lập tức với Task ID mà không hề bị đứng hình 8 giây!

---

## 3 Mô Hình Kiến Trúc Triển Khai (Deployment Topologies)

| Mô hình | Đặc điểm cấu trúc | Khi nào nên áp dụng? |
|---|---|---|
| **Single Deployment (Đơn khối)** | Toàn bộ Main Agent và Sub-Agent khai báo chung một `langgraph.json`, chạy 100% qua **ASGI** | **Khuyến nghị cho 90% dự án mới**: Dễ quản trị, không sợ lỗi mạng, độ trễ bằng 0. |
| **Split Deployment (Phân tán)** | Main Agent nằm ở server A, Sub-Agent nằm ở server B, kết nối qua **HTTP** | Khi Sub-Agent đòi hỏi cấu hình tài nguyên quá lệch (GPU chuyên dụng) hoặc scale độc lập. |
| **Hybrid (Lai ghép)** | Đa số Sub-Agent chạy ASGI tại chỗ, chỉ 1-2 Sub-Agent đặc thù gọi qua HTTP từ xa | Tối ưu hóa giữa chi phí bảo trì cục bộ và nhu cầu mở rộng linh hoạt cho tác vụ siêu nặng. |

---

## Cẩm Nang Xử Lý Lỗi (Troubleshooting)

### 1. Main Agent vừa giao việc xong đã tự động gọi `check_async_task` liên tục
- **Hiện tượng**: Agent biến cuộc gọi bất đồng bộ thành một vòng lặp kiểm tra liên hồi (giả đồng bộ).
- **Khắc phục**: Thêm lời nhắc nghiêm khắc vào `system_prompt` của Main Agent: *"Sau khi nhận được task_id, bạn PHẢI trao quyền phản hồi lại cho người dùng ngay lập tức. TUYỆT ĐỐI KHÔNG tự ý thăm dò trạng thái trừ khi người dùng ra lệnh."*

### 2. Báo cáo trạng thái cũ mèm (Stale Status)
- **Hiện tượng**: Người dùng hỏi tiến độ, Main Agent đọc lại câu trả lời cũ trong lịch sử chat thay vì gọi tool mới.
- **Khắc phục**: Nhắc trong prompt: *"Trạng thái task trong lịch sử hội thoại LUÔN LUÔN là dữ liệu cũ. Khi được hỏi tiến độ, BẮT BUỘC phải gọi check_async_task để lấy tin mới nhất từ hệ thống."*

### 3. Task ID bị LLM tự ý cắt ngắn
- **Hiện tượng**: Task ID là `task-987-xyz-123`, nhưng model tự ý viết tắt thành `task-987...`, dẫn đến việc gọi `check` bị báo lỗi không tìm thấy.
- **Khắc phục**: Hướng dẫn model: *"Giữ nguyên vẹn 100% chuỗi ký tự của task_id, không bao giờ được viết tắt hay sửa đổi."*

### 4. Lệnh `start_async_task` bị treo vĩnh viễn
- **Nguyên nhân**: **Hết slot Worker!** Nếu bạn có 1 Supervisor và 3 Sub-Agent chạy cùng lúc, bạn cần tối thiểu 4 slots. Nếu máy chủ chỉ có 1 hoặc 2 workers, các tác vụ con sẽ xếp hàng vô tận.
- **Khắc phục**: Luôn khởi động với cờ tăng dung lượng worker: `langgraph dev --n-jobs-per-worker 10`.

---

## Tổng Kết (Key Takeaways)

1. **Phá vỡ thế bế tắc**: Async Sub-Agent mang lại khả năng xử lý song song thực thụ — Main Agent không còn bị phong tỏa luồng khi điều hành các tác vụ con nặng nề.
2. **5 Remote Controls**: `start`, `check`, `update`, `cancel`, `list` cung cấp khả năng can thiệp toàn diện vào vòng đời tác vụ ngầm.
3. **Bảo toàn ID qua State Channel**: Nhờ lưu trữ trên channel `async_tasks` độc lập, dữ liệu task không bao giờ bị xóa mất khi cơ chế Context Summarization kích hoạt nén lịch sử chat.
4. **Bắt đầu bằng Single ASGI**: Tận dụng cơ chế truyền thông nội bộ ASGI để có tốc độ cao nhất và cấu hình đơn giản nhất trước khi tính đến việc phân tán microservices qua HTTP.

Ở **Chương 7**, chúng ta sẽ khám phá khái niệm **Skills** — các gói đóng gói kỹ năng có khả năng tái sử dụng, giúp trang bị tri thức chuyên ngành và quy trình nghiệp vụ mẫu cho Agent một cách bài bản!
