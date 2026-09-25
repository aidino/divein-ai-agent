# Chương 8: Long-Term Memory — Bộ Nhớ Dài Hạn Giúp Agent Duy Trì Tri Thức Xuyên Suốt Mọi Cuộc Hội Thoại

> Ở các chương trước, chúng ta đã nắm vững các năng lực nền tảng của Deep Agents: Hệ thống tệp tin ảo (Virtual File System - VFS), Lập kế hoạch tác vụ (Task Planning & TodoList), Sub-Agents và Skills. 
> Cơ chế `Checkpointer` của LangGraph rất xuất sắc trong việc lưu trữ trạng thái của **cùng một phiên hội thoại (Thread)**. Tuy nhiên, khi người dùng mở một cuộc trò chuyện mới (Thread ID mới), toàn bộ bối cảnh đó sẽ biến mất! Để Agent có thể ghi nhớ sở thích cá nhân, phong cách viết code của bạn, hoặc tích lũy tri thức dự án qua nhiều ngày làm việc, chúng ta cần trang bị cho Agent **Long-Term Memory (Bộ nhớ dài hạn)**. Chương này sẽ hướng dẫn bạn cách thiết kế và hiện thực hóa điều đó.

---

## Nguyên Lý Hoạt Động Của Memory Trong Deep Agents

Deep Agents coi **Bộ nhớ (Memory) là công dân hạng nhất (First-Class Citizen)** — Agent tương tác với bộ nhớ dưới dạng các **tệp tin (Files)** thông qua các công cụ đọc/ghi quen thuộc, trong khi lập trình viên sử dụng các **Backend** để điều phối xem những tệp tin này được lưu trữ vật lý ở đâu.

Quy trình vận hành bộ nhớ gồm 3 bước tuần tự:

1. **Chuẩn bị hạ tầng lưu trữ và tệp tin (Storage & File Preparation):** Cấu hình `Backend` và `Store` (ví dụ: `PostgresStore` hoặc `InMemoryStore`), đồng thời khởi tạo sẵn các tệp tin bộ nhớ cần thiết.
2. **Nạp bộ nhớ vào ngữ cảnh (Loading Memory):** 
   - Tham số `memory=["/memories/preferences.md"]` nhận danh sách các đường dẫn tệp tin cụ thể; toàn bộ nội dung của các tệp tin này sẽ được **bơm trực tiếp vào System Prompt** của Agent ngay khi khởi động.
   - Tham số `skills=["/skills/"]` nhận danh sách thư mục; hệ thống chỉ trích xuất metadata (name + description) đưa vào System Prompt, còn nội dung chi tiết sẽ do Agent chủ động đọc theo nhu cầu (*Progressive Disclosure*).
3. **Cập nhật và tiến hóa bộ nhớ (Memory Updating - Tùy chọn):** Thông qua System Prompt, bạn quy ước rõ khi nào Agent cần ghi nhớ thông tin và phải ghi vào tệp tin nào. Khi hội thoại diễn ra, Agent sẽ gọi các công cụ như `edit_file` hoặc `write_file` để cập nhật dữ liệu cho các phiên tương lai.

> ⚠️ **LƯU Ý KỸ THUẬT QUAN TRỌNG TỪ PHIÊN BẢN `deepagents>=0.7.10`:**
> 
> Khai báo `memory=["/memories/preferences.md"]` thuần túy là một **cấu hình đọc (Read Configuration)**:
> - Trong bản 0.7.10, nếu tệp tin được khai báo trong `memory=` **chưa tồn tại** trong Store, framework sẽ âm thầm bỏ qua, **không tự động tạo file mới** và cũng không đưa đường dẫn đó vào System Prompt.
> - Khai báo `memory=` không ép buộc được hành vi ghi của Agent. Nếu bạn muốn Agent lưu sở thích vào đúng file `preferences.md`, bạn **bắt buộc phải chỉ định rõ quy ước đường dẫn trong `system_prompt`** (hoặc chuẩn bị sẵn tệp tin khởi tạo ban đầu).

Trong thực tế doanh nghiệp, hai mô hình phổ biến nhất là:
- **Agent-Scoped Memory (Bộ nhớ cấp Agent):** Dùng chung cho toàn bộ người dùng, giúp Agent tích lũy tri thức chung và tự hoàn thiện mình.
- **User-Scoped Memory (Bộ nhớ cấp Người dùng):** Cách ly tuyệt đối theo từng `user_id`, đảm bảo quyền riêng tư và sở thích cá nhân.

---

## Hai Loại "Ký Ức" Của AI Agent

Tương tự như con người có trí nhớ ngắn hạn và trí nhớ dài hạn — bạn nhớ câu nói vừa diễn ra 5 giây trước (ngắn hạn), đồng thời nhớ tên tuổi, sở thích ăn uống của mình từ nhiều năm qua (dài hạn). AI Agent cũng cần hai cơ chế kỹ thuật riêng biệt để mô phỏng hai tầng ký ức này:

### 1. Trí Nhớ Ngắn Hạn (Short-Term Memory / Thread-Scoped)

Như đã tìm hiểu ở Chương 3 và 5, mặc định `StateBackend` lưu trữ tệp tin và tin nhắn ngay trong **State** của LangGraph. Đây chính là trí nhớ ngắn hạn:
- **Phạm vi hiệu lực:** Chỉ tồn tại trong cùng một luồng hội thoại (`thread_id`).
- **Khả năng duy trì:** Không bị mất đi giữa các lượt chat qua lại trong cùng một phiên (nhờ cơ chế `Checkpointer`).
- **Vòng đời:** Biến mất ngay khi đổi sang `thread_id` mới — mỗi cuộc trò chuyện mới là một trang giấy trắng.

> *Hình tượng hóa:* Giống như chiếc bàn làm việc của bạn trong ngày — mọi tài liệu, ghi chú của tác vụ hiện tại được bày ra bàn để xử lý. Hết ngày dọn bàn là sạch trơn.

### 2. Trí Nhớ Dài Hạn (Long-Term Memory / Cross-Thread)

Những tri thức cần tồn tại xuyên suốt nhiều ngày, nhiều phiên làm việc và nhiều chủ đề khác nhau:
- **Sở thích cá nhân:** *"Tôi thích code ngắn gọn, biến đặt tiếng Anh, chú thích tiếng Việt"*.
- **Bối cảnh dự án:** *"Dự án này sử dụng kiến trúc FastAPI + Next.js + PostgreSQL"*.
- **Kết quả nghiên cứu tích lũy:** Dữ liệu nghiên cứu thị trường thu thập qua nhiều tuần.
- **Sự tự cải tiến (Self-Improvement):** Các bài học kinh nghiệm mà Agent đúc rút sau khi bị người dùng sửa lỗi.

Những thông tin này không được phép mất đi khi đóng tab hay đổi phiên chat. Chúng cần một hạ tầng lưu trữ bền vững (Persistent Store) có khả năng truy cập xuyên suốt mọi `thread_id`.

![So sánh 2 loại bộ nhớ: Ngắn hạn (Checkpointer, trong cùng thread) vs Dài hạn (Store, xuyên thread), kết hợp qua CompositeBackend](https://datawhalechina.github.io/deepagents-in-action/imgs/26-comparison-memory-types.png)

---

## Checkpointer: Nền Tảng Của Trí Nhớ Ngắn Hạn

Trước khi đi sâu vào bộ nhớ dài hạn, hãy hiểu thật rõ cơ chế `Checkpointer` của LangGraph — "xương sống" của trí nhớ ngắn hạn.

```python
from langgraph.checkpoint.memory import MemorySaver
from deepagents import create_deep_agent

checkpointer = MemorySaver()

agent = create_deep_agent(
    model="google_genai:gemini-3.5-flash",
    checkpointer=checkpointer,
)

# Phiên 1 (thread_id: "conversation-001"): Agent nhớ bối cảnh
config_1 = {"configurable": {"thread_id": "conversation-001"}}
agent.invoke({"messages": [{"role": "user", "content": "Tôi tên là Hoàng Nam"}]}, config=config_1)
res = agent.invoke({"messages": [{"role": "user", "content": "Tôi tên là gì?"}]}, config=config_1)
print(res["messages"][-1].content)  # -> "Bạn tên là Hoàng Nam."

# Phiên 2 (thread_id: "conversation-002"): Mở cuộc trò chuyện mới
config_2 = {"configurable": {"thread_id": "conversation-002"}}
res2 = agent.invoke({"messages": [{"role": "user", "content": "Tôi tên là gì?"}]}, config=config_2)
print(res2["messages"][-1].content)  # -> Agent hoàn toàn không biết bạn là ai!
```

### Cách Checkpointer Hoạt Động Ngầm:
- Sau mỗi bước (step) hoặc lượt gọi công cụ của Agent, Checkpointer tự động chụp lại một snapshot trạng thái: lịch sử hội thoại (`messages`), cây thư mục ảo (`files`), và danh sách việc cần làm (`todos`).
- Khi gọi `agent.invoke()` với cùng một `thread_id`, Checkpointer tải lại toàn bộ snapshot gần nhất từ bộ nhớ/database để Agent tiếp tục suy luận.
- **Ranh giới:** Checkpointer thiết kế cách ly hoàn toàn theo `thread_id`. Trừ phi bạn can thiệp, hai thread khác nhau không thể nhìn thấy trạng thái của nhau.

---

### Chiến Lược Quản Trị Trí Nhớ Ngắn Hạn (Context Window Management)

Khi một cuộc hội thoại kéo dài hàng trăm lượt, danh sách `messages` sẽ nhanh chóng chạm ngưỡng giới hạn của Context Window. Có 3 chiến lược giải quyết:

| Chiến lược | Cơ chế thực hiện | Đánh giá & Ngữ cảnh áp dụng |
|---|---|---|
| **Trim (Cắt tỉa)** | Chỉ giữ lại $N$ tin nhắn gần nhất, xóa bỏ các tin nhắn cũ hơn. | Rất nhanh, đơn giản, nhưng làm mất hoàn toàn bối cảnh lúc bắt đầu cuộc trò chuyện. |
| **Delete (Xóa chọn lọc)** | Dùng lệnh `RemoveMessage` để loại bỏ chính xác các tin nhắn cụ thể. | Thích hợp khi cần làm sạch dữ liệu nhạy cảm (mật khẩu, token) khỏi bộ nhớ đệm. |
| **Summarize (Tóm tắt)** | Dùng một LLM phụ để cô đọng lịch sử trò chuyện cũ thành một đoạn tóm tắt súc tích. | **Tối ưu nhất**: Bảo tồn trọn vẹn ngữ nghĩa cốt lõi mà không làm phình to context. |

Trong Deep Agents, **chiến lược Summarize đã được tích hợp sẵn mặc định** thông qua `SummarizationMiddleware`:
- Mặc định, khi dung lượng tin nhắn đạt tới **85% Context Window** của mô hình, middleware sẽ tự động kích hoạt tóm tắt.
- Cơ chế này nén các tin nhắn gửi tới LLM, trong khi lịch sử gốc trong State vẫn được bảo lưu trọn vẹn.
- Từ bản `deepagents>=0.7.0`, bạn có thể thay thế toàn bộ instance `SummarizationMiddleware` mặc định bằng cấu hình tùy biến của riêng mình (chỉnh ngưỡng kích hoạt, prompt tóm tắt, mô hình tóm tắt riêng).

#### Tự xây dựng Middleware cắt tỉa tin nhắn bằng `@before_model`:

Nếu bạn muốn áp dụng chiến lược Trim thủ công cho các mô hình nhỏ, bạn có thể viết middleware can thiệp trước khi gọi LLM:

```python
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langchain.agents import AgentState
from langchain.agents.middleware import before_model
from langgraph.runtime import Runtime
from deepagents import create_deep_agent

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict | None:
    """Chỉ giữ lại 3 tin nhắn gần nhất và System Message đầu tiên."""
    messages = state["messages"]
    if len(messages) <= 4:
        return None  # Chưa vượt ngưỡng, không cần can thiệp

    system_msg = messages[0]  # Giữ lại System Message định hướng
    recent_msgs = messages[-3:]  # Giữ lại 3 tin nhắn trao đổi gần nhất
    
    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),  # Xóa toàn bộ tin nhắn đệm cũ
            system_msg,
            *recent_msgs,
        ]
    }

agent = create_deep_agent(
    model="google_genai:gemini-3.5-flash",
    middleware=[trim_messages],
)
```

---

### Mở Rộng: Tùy Biến `AgentState` Và `ToolRuntime`

LangChain và LangGraph cho phép bạn bổ sung thêm các trường dữ liệu tùy biến vào `AgentState`, và cấp quyền cho công cụ đọc/ghi các trường này thông qua tham số ẩn `ToolRuntime`:

```python
from langchain.agents import create_agent, AgentState
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command
from langchain.messages import ToolMessage

# 1. Định nghĩa cấu trúc State tùy biến
class CustomAgentState(AgentState):
    user_id: str
    user_preferences: dict

# 2. Công cụ ĐỌC trực tiếp từ State
@tool
def get_user_profile(runtime: ToolRuntime) -> str:
    """Truy xuất thông tin người dùng từ State nội bộ."""
    user_id = runtime.state.get("user_id", "unknown")
    prefs = runtime.state.get("user_preferences", {})
    return f"Người dùng {user_id}, tùy chọn hiện tại: {prefs}"

# 3. Công cụ GHI đè trực tiếp vào State bằng Command
@tool
def update_theme_preference(new_theme: str, runtime: ToolRuntime):
    """Cập nhật giao diện người dùng ưa thích trực tiếp vào State."""
    current_prefs = runtime.state.get("user_preferences", {})
    current_prefs["theme"] = new_theme
    
    # Bắn Command để cập nhật State của đồ thị
    return Command(update={
        "user_preferences": current_prefs,
        "messages": [
            ToolMessage("Đã cập nhật giao diện thành công.", tool_call_id=runtime.tool_call_id)
        ]
    })
```

> 💡 **Khái niệm then chốt:**
> - `runtime.state` dùng để **Đọc (Read)** trạng thái hiện tại.
> - `Command(update={...})` dùng để **Ghi (Write)** ngược lại vào State mà không cần thông qua LLM sinh text.

---

## `CompositeBackend`: Trái Tim Của Kiến Trúc Bộ Nhớ Dài Hạn

Làm thế nào để kết hợp hài hòa giữa **Tệp tin tạm thời** (chỉ cần dùng trong 1 phiên) và **Tệp tin bộ nhớ dài hạn** (cần lưu vĩnh viễn)? Câu trả lời chính là `CompositeBackend`.

`CompositeBackend` hoạt động như một bộ định tuyến tệp tin (File Router):
- Mọi thao tác tệp tin thông thường (như `/workspace/draft.txt`, `/temp.py`) $\rightarrow$ Đi vào `StateBackend` (tự động giải phóng sau khi xong phiên).
- Mọi thao tác tệp tin bắt đầu bằng `/memories/` $\rightarrow$ Tự động chuyển hướng sang `StoreBackend` (lưu trữ bền vững trong cơ sở dữ liệu).

Đối với Agent, nó **không cần biết** đằng sau có bao nhiêu loại database. Agent chỉ việc gọi các công cụ tiêu chuẩn như `read_file`, `write_file`, `edit_file`. Đường dẫn của tệp tin sẽ quyết định số phận lưu trữ của nó!

---

### Định Danh Runtime Và Quản Trị `namespace`

`StoreBackend` phân tách dữ liệu của các cá nhân, các Agent và các tổ chức khác nhau thông qua khái niệm **`namespace` (Không gian tên)** — về mặt kỹ thuật, đây là một Tuple chứa các chuỗi định danh (ví dụ: `("user-123", "memories")`).

Khi triển khai trên **LangSmith / LangGraph Server**, `rt.server_info` sẽ tự động cung cấp danh tính người dùng (`user.identity`) và ID trợ lý (`assistant_id`). Tuy nhiên, khi chạy thử nghiệm cục bộ với `agent.invoke()`, biến này có thể bị rỗng. Do đó, mã nguồn chuẩn nên có cơ chế fallback an toàn:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class MemoryContext:
    user_id: str = "local-user"
    org_id: str = "default-org"

def assistant_namespace(rt):
    """Namespace dùng chung cho toàn bộ Agent."""
    if rt.server_info:
        return (rt.server_info.assistant_id,)
    return ("local-agent",)

def user_namespace(rt):
    """Namespace cách ly riêng biệt cho từng người dùng."""
    if rt.server_info and rt.server_info.user:
        return (rt.server_info.user.identity,)
    user_id = getattr(rt.context, "user_id", "local-user")
    return (user_id,)

def org_namespace(rt):
    """Namespace chia sẻ cấp tổ chức / công ty."""
    org_id = getattr(rt.context, "org_id", "default-org")
    return (org_id,)
```

Khi chạy cục bộ, bạn chỉ cần truyền ngữ cảnh qua tham số `context`:

```python
agent.invoke(
    {"messages": [{"role": "user", "content": "Hãy ghi nhớ tôi thích code TypeScript"}]},
    context=MemoryContext(user_id="user-456", org_id="acme-corp"),
    config={"configurable": {"thread_id": "thread-01"}},
)
```

---

### Ba Phạm Vi (Scopes) Của Ký Ức Dài Hạn

![3 phạm vi bộ nhớ: Agent-scoped (dùng chung), User-scoped (cách ly user), Org-scoped (chính sách tổ chức)](https://datawhalechina.github.io/deepagents-in-action/imgs/28-arch-scoped-memory.png)

#### 1. Agent-Scoped Memory (Bộ nhớ cấp Agent — Dùng chung cho mọi User)
Tất cả người dùng khi trò chuyện đều đóng góp vào một kho kiến thức chung của Agent. `namespace` được cấu hình là `(assistant_id, "memories")`:

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    model="google_genai:gemini-3.5-flash",
    context_schema=MemoryContext,
    memory=["/memories/AGENTS.md"],  # Tự động nạp vào System Prompt khi khởi động
    skills=["/skills/"],             # Thư viện Skills
    backend=CompositeBackend(
        default=StateBackend(),       # Mọi file tạm đi vào State
        routes={
            # Toàn bộ file trong /memories/ được lưu chung cho Agent
            "/memories/": StoreBackend(
                namespace=lambda rt: (*assistant_namespace(rt), "memories"),
            ),
            "/skills/": StoreBackend(
                namespace=lambda rt: (*assistant_namespace(rt), "skills"),
            ),
        },
    ),
)
```

#### 2. User-Scoped Memory (Bộ nhớ cấp Người dùng — Cách ly theo User ID)
Mỗi người dùng có một tệp `preferences.md` riêng biệt. Người dùng A không bao giờ nhìn thấy hay bị ảnh hưởng bởi sở thích của người dùng B:

```python
agent = create_deep_agent(
    model="google_genai:gemini-3.5-flash",
    context_schema=MemoryContext,
    memory=["/memories/preferences.md"],
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            # Namespace gắn chặt với user_id của từng người
            "/memories/": StoreBackend(
                namespace=lambda rt: (*user_namespace(rt), "memories"),
            ),
        },
    ),
)
```

#### 3. Organization-Scoped Memory (Bộ nhớ cấp Tổ chức / Doanh nghiệp)
Chứa các quy định tuân thủ bảo mật, chính sách giá, cẩm nang ứng xử của toàn công ty. Thông thường bộ nhớ này được đặt ở chế độ **Read-Only (Chỉ đọc)** đối với Agent để chống tấn công Prompt Injection (xem chi tiết ở phần Quản trị quyền hạn).

---

## Thực Chiến: Toàn Trình Lưu Trữ & Truy Cập Xuyên Hội Thoại (Cross-Thread)

Hãy cùng theo dõi kịch bản hoàn chỉnh: **Cuộc hội thoại 1 ghi nhận sở thích $\rightarrow$ Kiểm tra dữ liệu trong Store $\rightarrow$ Cuộc hội thoại 2 (Thread ID mới hoàn toàn) tự động áp dụng sở thích đó.**

![Quy trình ký ức xuyên hội thoại: Thread 1 ghi vào Store, Thread 2 đọc từ Store](https://datawhalechina.github.io/deepagents-in-action/imgs/27-flowchart-cross-thread.png)

```python
from dataclasses import dataclass
from uuid import uuid4

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

@dataclass
class UserContext:
    user_id: str

# 1. Khởi tạo Store và ngữ cảnh
store = InMemoryStore()
user = UserContext(user_id="developer-alex")
user_namespace = (user.user_id, "memories")
memory_virtual_path = "/memories/preferences.md"

# 2. KHỞI TẠO FILE TRƯỚC TRONG STORE:
# Lưu ý: CompositeBackend tự động tước tiền tố "/memories/",
# nên key lưu trữ trong Store phải là "/preferences.md"
store.put(
    user_namespace,
    "/preferences.md",
    create_file_data("# User Preferences\nChưa có ghi chú nào."),
)

# 3. Tạo Deep Agent với quy ước System Prompt chặt chẽ
agent = create_deep_agent(
    model="google_genai:gemini-3.5-flash",
    context_schema=UserContext,
    store=store,
    checkpointer=InMemorySaver(),
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(
                namespace=lambda rt: (rt.context.user_id, "memories"),
            ),
        },
    ),
    memory=[memory_virtual_path],
    system_prompt=(
        f"Khi người dùng yêu cầu ghi nhớ sở thích hoặc nguyên tắc làm việc, "
        f"hãy đọc file {memory_virtual_path}, sau đó dùng công cụ edit_file để cập nhật. "
        "Giữ nguyên các sở thích cũ đã có, chỉ bổ sung thêm điều mới. "
        "Chỉ thông báo cho người dùng là đã ghi nhớ sau khi công cụ edit_file thực thi thành công."
    ),
)

# ==============================================================================
# CUỘC HỘI THOẠI 1 (Thread 001): Người dùng thiết lập quy tắc
# ==============================================================================
thread_1 = str(uuid4())
print(f"--- BẮT ĐẦU PHIÊN CHAT 1 (Thread ID: {thread_1}) ---")

agent.invoke(
    {
        "messages": [
            {
                "role": "user", 
                "content": "Hãy ghi nhớ sở thích lập trình của tôi: luôn viết chú thích hàm bằng tiếng Việt và đặt tên biến theo chuẩn camelCase."
            }
        ]
    },
    context=user,
    config={"configurable": {"thread_id": thread_1}},
)

# 4. KIỂM CHỨNG TẬN GỐC TRONG STORE:
# Không chỉ tin lời LLM nói "Tôi đã nhớ", ta kiểm tra trực tiếp dữ liệu nhị phân trong Store
saved_file = store.get(user_namespace, "/preferences.md")
assert saved_file is not None, "Lỗi: File preferences.md chưa được tạo trong Store!"
saved_content = saved_file.value["content"]
print("\n[Kiểm toán Store] Nội dung file preferences.md thực tế:")
print(saved_content)
assert "tiếng Việt" in saved_content and "camelCase" in saved_content, "Lỗi: Nội dung chưa được ghi đúng!"

# ==============================================================================
# CUỘC HỘI THOẠI 2 (Thread 002): Một phiên hoàn toàn mới, kiểm tra trí nhớ dài hạn
# ==============================================================================
thread_2 = str(uuid4())
print(f"\n--- BẮT ĐẦU PHIÊN CHAT 2 (Thread ID MỚI: {thread_2}) ---")

# Lưu ý: Ta hoàn toàn KHÔNG nhắc lại sở thích ở câu lệnh này!
response = agent.invoke(
    {
        "messages": [
            {
                "role": "user", 
                "content": "Viết giúp tôi một hàm kiểm tra số nguyên tố bằng Python."
            }
        ]
    },
    context=user,
    config={"configurable": {"thread_id": thread_2}},
)

print("\n[Kết quả phản hồi của Agent ở Thread mới]:")
print(response["messages"][-1].content)
```

> 🔍 **Tại sao kiểm tra ở Thread mới lại thành công?**
> Khi `thread_2` bắt đầu, `create_deep_agent` thực thi bước khởi tạo:
> 1. Đọc danh sách `memory=["/memories/preferences.md"]`.
> 2. Gửi truy vấn sang `StoreBackend` với namespace `("developer-alex", "memories")`.
> 3. Lấy được nội dung: *"luôn viết chú thích hàm bằng tiếng Việt và đặt tên biến camelCase"*.
> 4. Bơm trực tiếp khối văn bản này vào **System Prompt** của `thread_2`.
> 5. LLM khi sinh code tự khắc tuân thủ theo nguyên tắc này dù người dùng không nhắc lại một chữ nào!

---

## Bốn Kịch Bản Thực Tế Điển Hình

### 1. Ký Ức Sở Thích Cá Nhân (User Preference Memory)
Agent nhớ phong cách hành văn, độ dài phản hồi mong muốn (ngắn gọn hay chi tiết), múi giờ, ngôn ngữ ưa thích của từng người dùng. Mỗi khi người dùng đổi ý, Agent dùng `edit_file` cập nhật vào `/memories/preferences.md`.

### 2. Agent Tự Hoàn Thiện Bản Thân (Self-Improving Agent)
Bằng cách cấu hình `memory=["/memories/AGENTS.md"]` trỏ tới `assistant_namespace`:
- Mỗi khi người dùng góp ý: *"Lần sau trả lời lỗi cú pháp đừng giải thích dài dòng nữa, chỉ cần đưa code sửa thôi"*.
- Agent tự động mở tệp `/memories/AGENTS.md` và ghi thêm bài học kinh nghiệm vào danh mục quy tắc của chính mình.
- Tri thức này sẽ vĩnh viễn trở thành kim chỉ nam cho Agent trong các lần phục vụ tiếp theo.

### 3. Tích Lũy Cơ Sở Tri Thức Dự Án (Knowledge Base Accumulation)
Trong một dự án phần mềm kéo dài nhiều tháng:
- **Phiên 1:** Đọc hiểu kiến trúc hạ tầng và lưu lại vào `/memories/project/architecture.md`.
- **Phiên 2:** Phân tích quy ước đặt tên database và lưu vào `/memories/project/db-schema.md`.
- **Phiên 3:** Agent đóng vai trò như một Senior Tech Lead kỳ cựu, giải đáp mọi thắc mắc dựa trên toàn bộ tài liệu đã tích lũy.

### 4. Điều Phối Nghiên Cứu Chuyên Sâu (Long-running Research)
Nghiên cứu thị trường phức tạp không thể hoàn tất trong 15 phút:
```python
memory=[
    "/memories/research/sources.md",   # Danh mục tài liệu tham khảo đã duyệt
    "/memories/research/notes.md",     # Ghi chú thô các phát hiện mới
    "/memories/research/draft.md",     # Bản thảo báo cáo đang viết dở
]
```
Mỗi ngày, Agent tiến hành thu thập thêm thông tin từ một vài nguồn, cập nhật tiến độ vào `notes.md`. Nghiên cứu được tiếp tục một cách liền mạch mà không sợ tràn Context Window.

---

## 6 Chiều Kích Kiến Trúc Của Hệ Thống Memory

Tài liệu thiết kế kiến trúc chính thức của Deep Agents chia bộ nhớ thành 6 chiều kích độc lập có thể tùy biến:

| Chiều kích (Dimension) | Câu hỏi thiết kế cốt lõi | Các tùy chọn giải pháp |
|---|---|---|
| **1. Thời gian duy trì (Duration)** | Dữ liệu cần tồn tại trong bao lâu? | **Ngắn hạn** (trong 1 Thread qua Checkpointer) / **Dài hạn** (Xuyên thread qua Store). |
| **2. Bản chất thông tin (Information Type)** | Nội dung ghi nhớ thuộc thể loại gì? | **Episodic** (Hồi ức sự kiện) / **Procedural** (Kỹ năng, Skills) / **Semantic** (Sự thật & Sở thích). |
| **3. Phạm vi tiếp cận (Scope)** | Ai có quyền nhìn thấy dữ liệu này? | **User-scoped** (Cá nhân) / **Agent-scoped** (Nội bộ Agent) / **Org-scoped** (Toàn doanh nghiệp). |
| **4. Chiến lược cập nhật (Update Strategy)** | Ghi vào bộ nhớ ở thời điểm nào? | **Hot Path** (Ghi tức thời trong hội thoại) / **Background Consolidation** (Xử lý hậu kỳ ngầm). |
| **5. Cơ chế truy xuất (Retrieval Method)** | Đưa vào não Agent bằng cách nào? | **Nạp tĩnh đầu phiên** (`memory=`) / **Nạp tiệm tiến theo nhu cầu** (Tools & Skills). |
| **6. Quản trị an toàn (Permissions)** | Agent có được phép sửa không? | **Đọc & Ghi (Read-Write)** / **Chỉ đọc (Read-Only)** / **Cần duyệt (Interrupt)**. |

---

## Các Kỹ Thuật Nâng Cao

### 1. Episodic Memory (Ký Ức Hồi Ức — Tìm Lại Các Cuộc Trò Chuyện Cũ)

Khác với Semantic Memory chỉ lưu các gạch đầu dòng ngắn gọn, **Episodic Memory** lưu lại toàn bộ diễn biến lịch sử: *Người dùng đã gặp lỗi gì, các bước sửa lỗi diễn ra theo thứ tự nào, kết quả ra sao*.

Nhờ `Checkpointer`, toàn bộ các Thread cũ đều được lưu lại trong Database. Chúng ta chỉ cần cung cấp cho Agent một công cụ tìm kiếm lịch sử gọi qua `langgraph_sdk`:

```python
from langgraph_sdk import get_client
from langchain.tools import tool, ToolRuntime

sdk_client = get_client(url="<DEPLOYMENT_URL>")

@tool
async def search_past_conversations(query: str, runtime: ToolRuntime) -> str:
    """Tìm kiếm lại các cuộc hội thoại trong quá khứ của người dùng để lấy bối cảnh."""
    user_id = runtime.context.user_id
    
    # Tìm kiếm các Thread thuộc về user này
    threads = await sdk_client.threads.search(
        metadata={"user_id": user_id},
        limit=3,
    )
    
    past_history = []
    for th in threads:
        history = await sdk_client.threads.get_history(thread_id=th["thread_id"])
        past_history.append(history)
        
    return str(past_history)
```

> *Ví dụ ứng dụng:* Một Coder Agent khi gặp một lỗi compiler hiếm gặp có thể tra cứu: *"Tuần trước tôi đã từng gặp lỗi tương tự ở module nào và fix ra sao?"*, sau đó tái sử dụng lại giải pháp mà không cần tìm kiếm Google từ đầu.

---

### 2. Background Consolidation (Hợp Nhất Ký Ức Hậu Kỳ Bằng Cron Job)

Việc bắt Agent phải vừa trả lời người dùng, vừa cập nhật file bộ nhớ ngay trong phiên chat (Hot Path) có 2 nhược điểm lớn:
1. Làm tăng độ trễ (latency) của câu trả lời.
2. Dễ làm phân tâm mạch suy luận chính của Agent.

Giải pháp chuyên nghiệp cho Production là **Background Consolidation (Hợp nhất bộ nhớ ngầm)**:
- Trong phiên chat, Agent chỉ tập trung trao đổi với người dùng.
- Cứ sau mỗi 6 tiếng, một **Consolidation Agent chuyên trách** sẽ được kích hoạt ngầm bằng Cron Job để quét toàn bộ các đoạn chat phát sinh, chắt lọc các sự thật quan trọng, loại bỏ các thông tin rác đã hết hạn và ghi vào tệp `preferences.md`.

```python
from datetime import datetime, timedelta, timezone
from deepagents import create_deep_agent
from langchain.tools import tool, ToolRuntime
from langgraph_sdk import get_client

sdk_client = get_client(url="<DEPLOYMENT_URL>")

@tool
async def extract_recent_dialogues(runtime: ToolRuntime) -> str:
    """Quét các đoạn chat của người dùng trong vòng 6 giờ qua."""
    user_id = runtime.context.user_id
    six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
    
    threads = await sdk_client.threads.search(
        metadata={"user_id": user_id},
        updated_after=six_hours_ago.isoformat(),
        limit=20,
    )
    return str([t["values"]["messages"] for t in threads])

# Agent chuyên trách tinh lọc tri thức
consolidation_agent = create_deep_agent(
    model="google_genai:gemini-3.5-flash",
    system_prompt=(
        "Bạn là thư ký tinh lọc tri thức. Hãy rà soát các cuộc trò chuyện gần đây, "
        "trích xuất các sở thích lập trình mới của người dùng và cập nhật vào /memories/preferences.md. "
        "Loại bỏ các thông tin trùng lặp hoặc mâu thuẫn."
    ),
    tools=[extract_recent_dialogues],
)

# Lên lịch chạy định kỳ mỗi 6 tiếng bằng Cron Job
cron_job = await sdk_client.crons.create(
    assistant_id="consolidation_agent",
    schedule="0 */6 * * *",
    input={"messages": [{"role": "user", "content": "Tiến hành quét và đồng bộ ký ức."}]},
)
```

---

### 3. Xử Lý Xung Đột Ghi Đồng Thời (Concurrency & Race Conditions)

Khi một hệ thống phục vụ hàng ngàn người dùng hoặc khi nhiều Sub-Agents cùng chạy song song, việc ghi đè vào cùng một tệp tin bộ nhớ sẽ dẫn đến xung đột **Last-Write-Wins (Bản ghi sau vô tình xóa mất bản ghi trước)**.

**Chiến lược phòng ngừa tiêu chuẩn:**
1. **Phân rã tệp tin theo chuyên đề:** Thay vì gom tất cả vào một file `memory.md` khổng lồ, hãy chia nhỏ thành `/memories/ui-prefs.md`, `/memories/backend-prefs.md`, `/memories/credentials.md`.
2. **Kỹ thuật Append-Only Log:** Trong phiên chat nóng, chỉ cho phép Agent ghi nối tiếp vào một file log theo dạng sự kiện: `/memories/events/2026-09-thread-123.md`. Việc tổng hợp và loại bỏ trùng lặp sẽ do Consolidation Agent xử lý tuần tự sau đó.
3. **Phân quyền chặt chẽ:** Chỉ mở quyền ghi cho không gian cá nhân của người dùng; toàn bộ tri thức của tổ chức phải được cấu hình Read-Only.

---

## Lộ Trình Nâng Cấp Store: Từ Thử Nghiệm Đến Production

| Giai đoạn | Giải pháp đề xuất | Bản chất kỹ thuật & Ưu/Nhược điểm |
|---|---|---|
| **Phát triển & Thử nghiệm (Local Dev)** | `InMemoryStore` | Dữ liệu lưu trong RAM của tiến trình Python. Khởi động tức thì, không cần cài đặt. **Nhược điểm:** Mất toàn bộ dữ liệu khi tắt máy hoặc restart server. |
| **Triển khai Thực tế (Production)** | `PostgresStore` | Dữ liệu lưu vào bảng trong cơ sở dữ liệu PostgreSQL. Bền vững vĩnh viễn, hỗ trợ transaction an toàn và mở rộng quy mô đa container. |
| **Đám mây Quản lý (Managed Cloud)** | **LangSmith Deployments** | Nền tảng tự động cấu hình Store ngầm ở tầng hạ tầng. Lập trình viên không cần truyền tham số `store=` vào hàm `create_deep_agent`. |

### Cấu Hình `PostgresStore` Cho Môi Trường Production:

Cài đặt thư viện:
```bash
pip install langgraph-checkpoint-postgres
```

Triển khai mã nguồn:
```python
import os
from langgraph.store.postgres import PostgresStore
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

db_uri = os.environ["DATABASE_URL"]  # postgresql://user:pass@localhost:5432/dbname

# Sử dụng context manager hoặc khởi tạo trong lifecycle của ứng dụng FastAPI
with PostgresStore.from_conn_string(db_uri) as store:
    # BẮT BUỘC: Gọi store.setup() ở lần chạy đầu tiên để tạo các bảng cơ sở dữ liệu cần thiết
    store.setup()

    agent = create_deep_agent(
        model="google_genai:gemini-3.5-flash",
        store=store,
        backend=CompositeBackend(
            default=StateBackend(),
            routes={
                "/memories/": StoreBackend(
                    namespace=lambda rt: (rt.context.user_id, "memories"),
                ),
            },
        ),
        memory=["/memories/preferences.md"],
    )
```

---

## Chi Tiết Kỹ Thuật: Định Dạng Tệp Tin & Lưu Ý Mount Path

### Định dạng dữ liệu bên trong Store (V2 Format)
Từ bản `deepagents>=0.5`, các tệp tin được lưu trong Store tuân thủ định dạng JSON v2 như sau:

```json
{
    "content": "Dòng 1\nDòng 2\nDòng 3",
    "encoding": "utf-8",
    "created_at": "2026-09-25T10:00:00Z",
    "modified_at": "2026-09-25T10:30:00Z"
}
```

> ⚠️ Tuyệt đối không tự gõ JSON này bằng tay! Khi khởi tạo dữ liệu ban đầu từ script Python bên ngoài, hãy luôn sử dụng hàm trợ giúp `create_file_data("nội dung file")`.

---

### Bảng Đối Chiếu Key Trong Store Khi Dùng `CompositeBackend`

Đây là lỗi phổ biến nhất khiến các lập trình viên mất hàng giờ debug khi tích hợp `CompositeBackend` với `StoreBackend`:

| Phương thức cấu hình Backend | Đường dẫn Agent nhìn thấy | Store Key thực tế cần ghi |
|---|---|---|
| **Dùng trực tiếp `StoreBackend` làm gốc** | `/skills/langgraph-docs/SKILL.md` | `/skills/langgraph-docs/SKILL.md` |
| **Bọc qua `CompositeBackend(routes={"/skills/": ...})`** | `/skills/langgraph-docs/SKILL.md` | **`/langgraph-docs/SKILL.md`** *(Đã tước bỏ prefix)* |
| **Bọc qua `CompositeBackend(routes={"/memories/": ...})`** | `/memories/preferences.md` | **`/preferences.md`** *(Đã tước bỏ prefix)* |

```python
# Ví dụ nạp dữ liệu chuẩn xác trước khi chạy:
store.put(
    ("my-agent", "memories"),
    "/AGENTS.md",                # Đúng! Agent sẽ thấy là /memories/AGENTS.md
    create_file_data("## Hướng dẫn ứng xử chung..."),
)

store.put(
    ("my-agent", "skills"),
    "/my-skill/SKILL.md",        # Đúng! Agent sẽ thấy là /skills/my-skill/SKILL.md
    create_file_data("---\nname: my-skill\ndescription: ...\n---\n"),
)
```

---

## 6 Best Practices Khi Thiết Kế Bộ Nhớ Cho Agent

1. **Đặt tên đường dẫn có tính mô tả cao:** Phân chia thư mục rõ ràng theo ngữ nghĩa để Agent và con người đều dễ quản lý:
   - `/memories/AGENTS.md`: Quy tắc hành vi của Agent.
   - `/memories/preferences.md`: Sở thích cá nhân người dùng.
   - `/memories/projects/fintech/stack.md`: Kiến trúc dự án cụ thể.
   - `/policies/compliance.md`: Chính sách tuân thủ của doanh nghiệp (Read-Only).
2. **Luôn đi đôi giữa `memory=` và chỉ dẫn Prompt:** Dùng tham số `memory=` để chỉ định file nạp vào ngữ cảnh, đồng thời dùng `system_prompt` để hướng dẫn Agent chính xác khi nào và ghi vào đâu.
3. **Phân nhỏ tệp tin theo chủ đề:** Tránh nhồi nhét mọi thứ vào một tệp khổng lồ. Việc chia nhỏ vừa giúp giảm xung đột ghi đồng thời, vừa giúp tiết kiệm token khi chỉ cần nạp những tệp thực sự liên quan.
4. **Cô lập Namespace đa tầng:** Trong hệ thống Multi-Agent và Multi-Tenant, hãy xây dựng namespace gồm cả `assistant_id` và `user_id`:
   ```python
   namespace = lambda rt: (rt.server_info.assistant_id, rt.context.user_id, "memories")
   ```
5. **Lựa chọn Store phù hợp với từng giai đoạn:** Bắt đầu nhẹ nhàng với `InMemoryStore` để test logic, sau đó chuyển sang `PostgresStore` hoặc LangSmith khi đưa vào khai thác thực tế.
6. **Kiểm toán thao tác ghi bằng Tracing:** Mọi hành vi cập nhật file bộ nhớ đều là các lượt Tool Call (`write_file`, `edit_file`). Hãy bật tính năng Tracing trên LangSmith để kiểm soát xem Agent có ghi nhầm hoặc bị tiêm nhiễm thông tin độc hại hay không.

---

## Tổng Kết

Trong chương này, chúng ta đã chinh phục mảnh ghép quan trọng giúp AI Agent trở nên thông minh và gắn kết hơn với người dùng:

1. **Phân biệt hai tầng ký ức:** Trí nhớ ngắn hạn (Thread-scoped via `Checkpointer`) giúp duy trì hội thoại hiện tại; Trí nhớ dài hạn (Cross-thread via `StoreBackend`) giúp tích lũy tri thức bền vững.
2. **Cơ chế định tuyến `CompositeBackend`:** Giúp trừu tượng hóa hạ tầng — Agent thao tác với toàn bộ bộ nhớ dưới dạng các tệp tin ảo quen thuộc.
3. **Ba phạm vi ký ức:** `Agent-scoped` (học hỏi tập thể), `User-scoped` (cá nhân hóa riêng tư), và `Org-scoped` (chuẩn mực doanh nghiệp).
4. **Quản trị an toàn:** Phối hợp giữa quyền chỉ đọc (Read-Only) cho các chính sách quan trọng và cơ chế kiểm duyệt của con người (*Human-in-the-loop*).
5. **Kỹ thuật Production:** Ứng dụng `PostgresStore` và mô hình **Background Consolidation** ngầm để tối ưu hóa hiệu năng và loại trừ xung đột dữ liệu.

Ở chương tiếp theo, chúng ta sẽ tìm hiểu về **Human-in-the-Loop (Con Người Can Thiệp Vào Vòng Lặp)** — cách thiết lập các điểm ngắt (Interrupts) để con người phê duyệt các thao tác nhạy cảm trước khi Agent chính thức thực thi.
