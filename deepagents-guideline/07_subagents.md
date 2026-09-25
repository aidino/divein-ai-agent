# Chương 5: Sub-Agents Và Cách Ly Ngữ Cảnh (Context Quarantine) — Dạy Agent Học Cách "Ủy Quyền"

> Ở chương trước, chúng ta đã tìm hiểu về Task Planning. Tuy nhiên, có những tác vụ con vô cùng phức tạp, đòi hỏi hàng chục lượt gọi công cụ (tool calls) và xử lý dữ liệu trung gian — nếu toàn bộ quá trình này đều dồn hết vào một Agent duy nhất, ngữ cảnh (context) sẽ nhanh chóng phát nổ. Chương này sẽ đưa bạn khám phá một năng lực kiến trúc đột phá của Deep Agents: **Sub-Agent (Agent Phụ)**, giúp Main Agent biết cách **"ủy quyền" (delegate)** công việc một cách thông minh.

---

## Tại Sao Lại Cần Đến Sub-Agent?

### Vấn nạn phình to ngữ cảnh (Context Explosion)

Giả sử Main Agent cần hoàn thành một bản báo cáo nghiên cứu chuyên sâu. Trong đó có một tác vụ con là: *"Tìm kiếm tài liệu kỹ thuật và kiến trúc của LangGraph"*. Tác vụ con này có thể kéo theo:

- 5 đến 7 lượt gọi công cụ tìm kiếm web (`internet_search`).
- Mỗi lượt tìm kiếm trả về hơn 3.000 tokens văn bản thô.
- Nhiều lần gọi `write_file` để lưu trữ dữ liệu cào được.
- Nhiều lần gọi `read_file` để đọc lại và trích xuất thông tin.

Toàn bộ các bước trung gian này sinh ra một khối lượng khổng lồ các bản ghi gọi tool (tool call records). Nếu không có cơ chế tách biệt, tất cả sẽ đổ dồn vào context của Main Agent. Mặc dù cơ chế Auto-Eviction (ở Chương 3) có thể giảm tải một phần, nhưng trên thực tế **Main Agent hoàn toàn không cần bận tâm đến những chi tiết vụn vặt đó** — cái nó thực sự cần chỉ là một bản tóm tắt cốt lõi dài 300 từ.

---

### Context Quarantine (Cách Ly Ngữ Cảnh)

Đó chính là triết lý thiết kế nền tảng của Sub-Agent: **Context Quarantine (Cách ly vùng ô nhiễm ngữ cảnh)**.

```
                    ┌───────────────────────────────────────────┐
                    │                Main Agent                 │
                    │        (Context sạch, gọn gàng)           │
                    └─────────────────────┬─────────────────────┘
                                          │
                        task("researcher", "Tìm hiểu...")
                                          │
                                          ▼
                    ┌───────────────────────────────────────────┐
                    │           Researcher Sub-Agent            │
                    │       (Context Quarantine / Cách ly)      │
                    │  ┌─────────────────────────────────────┐  │
                    │  │ search() ──> search() ──> search()  │  │
                    │  │ write_file() ──> read_file()        │  │
                    │  │ [Hàng chục nghìn tokens trung gian] │  │
                    │  └─────────────────────────────────────┘  │
                    └─────────────────────┬─────────────────────┘
                                          │
                        Trả về: "Bản tóm tắt 300 từ"
                                          │
                                          ▼
                    ┌───────────────────────────────────────────┐
                    │                Main Agent                 │
                    │     (Chỉ nhận kết quả, không bị rác)      │
                    └───────────────────────────────────────────┘
```

Quy trình vận hành:
1. Main Agent sử dụng công cụ tích hợp sẵn `task` để **khởi tạo và gọi** một Sub-Agent.
2. Sub-Agent thực thi nhiệm vụ trong một **vùng Context hoàn toàn độc lập** (các lượt gọi tool, thao tác đọc ghi file của nó không xuất hiện trong prompt của Main Agent).
3. Sau khi hoàn tất, Sub-Agent chỉ bàn giao **kết quả tinh lọc cuối cùng** về cho Main Agent.
4. Ngữ cảnh của Main Agent luôn được giữ sạch sẽ, mạch lạc và tập trung vào bức tranh tổng thể.

> 💡 **Phép so sánh trực quan:**
> Main Agent giống như **Tổng Giám Đốc (CEO)**, còn Sub-Agent là **Trưởng Nhóm Nghiên Cứu**. Vị CEO không cần (và không nên) tham gia từng buổi họp kỹ thuật nội bộ, không cần đọc từng dòng log tìm kiếm — CEO chỉ cần đọc bản báo cáo kết quả cô đọng do Trưởng Nhóm đệ trình.

![So sánh cách ly ngữ cảnh: Không có Sub-Agent thì toàn bộ rác trung gian tràn vào Main Agent; Có Sub-Agent thì chi tiết bị cô lập, Main Agent chỉ nhận tóm tắt](../public/imgs/13-comparison-context-quarantine.png)

---

### Khi Nào Nên Dùng Sub-Agent?

| Kịch bản bài toán | Có nên dùng Sub-Agent? | Rationale (Lý do kỹ thuật) |
|---|:---:|---|
| **Nghiên cứu cần tra cứu và tổng hợp nhiều lần** | ✅ **Nên** | Khối lượng dữ liệu trung gian lớn sẽ làm tràn context của Main Agent |
| **Tác vụ chuyên biệt cần tool riêng hoặc prompt riêng** | ✅ **Nên** | Sub-Agent có thể trang bị tập tool chuyên biệt và System Prompt riêng |
| **Tác vụ yêu cầu mô hình LLM với năng lực khác nhau** | ✅ **Nên** | Sub-Agent có thể dùng model nhẹ/rẻ để crawl data và model lớn để phân tích |
| **Bài toán lớn cần điều phối đa tầng** | ✅ **Nên** | Main Agent chuyên trách điều phối tổng thể, các Sub-Agent lo khâu thực thi |
| **Truy vấn đơn bước đơn giản** | ❌ **Không** | Chi phí phụ trội (overhead) để khởi tạo và gọi Sub-Agent lớn hơn lợi ích mang lại |
| **Tác vụ cần giữ lại toàn bộ chi tiết trung gian** | ❌ **Không** | Ngữ cảnh của Sub-Agent không được chuyển ngược về cho Main Agent |

---

## Khai Báo Sub-Agent: Phương Pháp Dùng Dictionary

Cách phổ biến và trực quan nhất để định nghĩa Sub-Agent trong Deep Agents là thông qua một **Dictionary**:

> **Đoạn code minh họa**: `internet_search` đại diện cho hàm tìm kiếm tự định nghĩa, thư mục `/skills/...` đại diện cho đường dẫn Skill thực tế trong dự án.

```python
from deepagents import create_deep_agent

# 1. Định nghĩa Sub-Agent chuyên trách nghiên cứu
research_subagent = {
    "name": "researcher",                # Bắt buộc: Định danh duy nhất
    "description": "Nghiên cứu chuyên sâu về một chủ đề cụ thể, tra cứu nhiều nguồn và tổng hợp thành tóm tắt",  # Bắt buộc: Main Agent căn cứ vào đây để điều phối
    "system_prompt": """Bạn là một chuyên gia nghiên cứu độc lập. Nhiệm vụ của bạn:
1. Phân rã câu hỏi nghiên cứu thành nhiều truy vấn tìm kiếm khác nhau.
2. Dùng internet_search để tìm kiếm thông tin liên quan.
3. Chắt lọc các phát hiện quan trọng và viết thành bản tóm tắt súc tích.
4. Trích dẫn rõ ràng các nguồn tin cậy.

LƯU Ý: Giới hạn kết quả trả về trong vòng 500 từ, chỉ nêu bật các phát hiện trọng tâm.""",  # Bắt buộc: Chỉ thị riêng của Sub-Agent
    "tools": [internet_search],          # Tùy chọn: Mặc định kế thừa; nếu chỉ định sẽ THAY THẾ HOÀN TOÀN (không merge)
    "skills": ["/skills/research/"],     # Tùy chọn: KHÔNG kế thừa từ cha; chạy instance SkillsMiddleware độc lập
}

# 2. Khởi tạo Main Agent và đăng ký Sub-Agent
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    skills=["/skills/main/"],            # Main Agent và general-purpose sub-agent kế thừa skill này
    subagents=[research_subagent],       # 'researcher' chỉ nhận /skills/research/, không nhận /skills/main/
)
```

---

### Bảng Giải Thích Chi Tiết Các Trường Cấu Hình

| Thuộc tính (Field) | Bắt buộc | Có kế thừa từ Main Agent? | Ý nghĩa kỹ thuật & Hành vi |
|---|:---:|:---:|---|
| `name` | ✅ | — | Định danh duy nhất. Main Agent dùng tên này khi gọi `task(name=...)`. Đồng thời được gắn vào metadata log/stream dạng `lc_agent_name`. |
| `description` | ✅ | — | Mô tả năng lực của Sub-Agent. **LLM của Main Agent dựa hoàn toàn vào chuỗi này để quyết định có nên ủy quyền hay không.** |
| `system_prompt` | ✅ | ❌ **KHÔNG** | Tập lệnh hành vi riêng biệt. Mỗi Sub-Agent phải có persona và mục tiêu độc lập. |
| `tools` | Tùy chọn | ✅ Mặc định kế thừa, **Ghi đè nếu chỉ định** | Nếu bỏ trống, kế thừa toàn bộ tool của cha. Nếu khai báo danh sách mới, nó sẽ **thay thế hoàn toàn** (không gộp chung). |
| `model` | Tùy chọn | ✅ Mặc định kế thừa | Có thể chỉ định model riêng, hỗ trợ instance ChatModel hoặc chuỗi định danh dạng `"provider:model"` (như `"openai:gpt-5.4"`). |
| `middleware` | Tùy chọn | ❌ **KHÔNG** | Danh sách Middleware riêng biệt của Sub-Agent. |
| `interrupt_on` | Tùy chọn | ✅ Mặc định kế thừa | Cấu hình tạm dừng chờ người duyệt (Human-in-the-Loop) riêng cho Sub-Agent. |
| `skills` | Tùy chọn | ❌ **KHÔNG** | Đường dẫn Skills chuyên biệt. Khi khai báo, Sub-Agent sở hữu một runtime `SkillsMiddleware` độc lập, state cô lập hoàn toàn với cha. |
| `response_format` | Tùy chọn | ❌ **KHÔNG** | Schema ép kiểu dữ liệu trả về dạng JSON chuẩn (Pydantic model, yêu cầu `deepagents>=0.5.3`). |
| `permissions` | Tùy chọn | ✅ Mặc định kế thừa, **Ghi đè nếu chỉ định** | Bộ luật phân quyền Virtual File System. Nếu chỉ định sẽ thay thế hoàn toàn bộ luật của cha. |

> ⚠️ **Các cạm bẫy kế thừa (Inheritance Pitfalls) cần đặc biệt lưu ý:**
> 1. **`system_prompt` tuyệt đối không kế thừa**: Nếu bạn quên viết prompt chi tiết cho Sub-Agent, nó sẽ hoạt động không định hướng.
> 2. **`tools` thay thế chứ không gộp**: Nếu Main Agent có `[tool_a, tool_b]` và Sub-Agent khai báo `tools=[tool_c]`, thì Sub-Agent **chỉ có `tool_c`**, không có `tool_a` hay `tool_b`.
> 3. **`skills` không truyền tự động**: Skill của Main Agent chỉ được chia sẻ duy nhất cho Sub-Agent mặc định (`general-purpose`). Các Sub-Agent tự định nghĩa trong `subagents=[...]` bắt buộc phải tự cấu hình `skills` của riêng mình.
> 4. **`permissions` thay thế nguyên khối**: Nếu chỉ định `permissions` cho Sub-Agent, toàn bộ quy tắc của cha sẽ bị hủy bỏ trên Sub-Agent đó. Hãy đảm bảo khai báo một tập quyền đầy đủ (xem thêm tại [Chương 11: Filesystem Permissions](../ch11-filesystem-permissions/)).
> 5. **Kế thừa TodoList trong v0.7**: Sub-Agent `general-purpose` tự động kế thừa cấu hình `TodoListMiddleware` nếu cha bật; nhưng các Sub-Agent nghiệp vụ trong `subagents=[...]` thì **không kế thừa** mà phải tự khai báo trong `middleware` riêng. Cần nhớ: cái được kế thừa là *khả năng lập kế hoạch*, chứ không phải *danh sách task* mà cha đang làm.

---

## `General-purpose` Sub-Agent: Trợ Lý Đa Năng Mặc Định

Ngay cả khi bạn khởi tạo Agent mà **không truyền tham số `subagents` nào**, Deep Agents vẫn âm thầm tích hợp sẵn một **`general-purpose` Sub-Agent**.

Đây là trường hợp ngoại lệ duy nhất trong hệ thống: **Nó tự động kế thừa toàn bộ `system_prompt`, `tools`, `model` và `skills` từ Main Agent**; nếu cha bật `TodoListMiddleware`, nó cũng nhận cấu hình đó.

```python
# Không cần truyền subagents, Agent vẫn biết ủy quyền
agent = create_deep_agent(
    model=model,
    tools=[internet_search],
    system_prompt="Bạn là một trợ lý nghiên cứu đa năng.",
)

# Trong lúc suy luận, Main Agent có thể tự động gọi:
# task(name="general-purpose", task="Tìm kiếm các bước phát triển mới nhất của điện toán lượng tử")
```

Vai trò của `general-purpose` Sub-Agent là **cung cấp khả năng cách ly ngữ cảnh thuần túy (Pure Context Quarantine)**: Nó có sức mạnh ngang hệt Main Agent, nhưng chạy trong một "buồng cách ly" riêng. Main Agent không phải gánh 10 lượt tìm kiếm trung gian của tác vụ con, mà chỉ nhận về một kết quả tổng hợp sạch sẽ.

---

### Vô hiệu hóa hoàn toàn Sub-Agent

Nếu ứng dụng của bạn yêu cầu Agent tuyệt đối không được phép sinh Sub-Agent (ngăn việc cấp công cụ `task`), bạn có thể tắt bằng cách cấu hình **Harness Profile**:

```python
from deepagents import create_deep_agent
from deepagents.profiles import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile

# Bước 1: Đăng ký Harness Profile tắt general-purpose subagent cho model chỉ định
register_harness_profile(
    key="openai:zai-org/GLM-5.2",
    profile=HarnessProfile(
        general_purpose_subagent=GeneralPurposeSubagentProfile(
            enabled=False
        )
    ),
)

# Bước 2: Khởi tạo Agent với subagents rỗng
agent = create_deep_agent(
    model=model,
    subagents=[],  # Không cấp bất kỳ Sub-Agent nào
)
```

> ⚠️ **Cảnh báo lỗi cú pháp:** Tuyệt đối không dùng `excluded_middleware` để cố loại bỏ `SubAgentMiddleware` — framework sẽ ném ra ngoại lệ `ValueError`. Cách chuẩn hóa duy nhất là vô hiệu hóa thông qua `GeneralPurposeSubagentProfile(enabled=False)`.

---

### Tùy biến đè (Override) `general-purpose` Sub-Agent

Bạn có thể giữ tên `general-purpose` nhưng cấp cho nó một model mạnh hơn hoặc prompt khác biệt:

```python
agent = create_deep_agent(
    model=model,  # Main Agent dùng model cơ bản
    tools=[internet_search],
    subagents=[
        {
            "name": "general-purpose",  # Ghi đè cấu hình mặc định
            "description": "Trợ lý tổng quát, xử lý các tác vụ ủy quyền chuyên sâu",
            "system_prompt": "Bạn là một trợ lý kỹ thuật cao cấp.",
            "tools": [internet_search],
            "model": ChatOpenAI(  # Sub-Agent được trang bị model tư duy mạnh hơn hẳn
                model="zai-org/GLM-5.2",
                api_key=os.environ["SILICONFLOW_API_KEY"],
                base_url="https://api.siliconflow.cn/v1",
            ),
        },
    ],
)
```

---

## `CompiledSubAgent`: Nhúng Toàn Bộ LangGraph Workflow

Trong các bài toán doanh nghiệp phức tạp, một Sub-Agent không chỉ đơn giản là một vòng lặp LLM + Tools, mà có thể là một **quy trình đa bước (Multi-step pipeline)** có rẽ nhánh điều kiện, vòng lặp kiểm tra chất lượng hoặc Human-in-the-Loop.

Lúc này, bạn có thể đóng gói nguyên một **đồ thị LangGraph đã biên dịch (Compiled Graph)** thành một Sub-Agent thông qua lớp `CompiledSubAgent`:

```python
from deepagents import create_deep_agent, CompiledSubAgent
from langchain.agents import create_agent

# 1. Tạo một Custom Agent Graph chuyên sâu bằng LangChain / LangGraph
custom_graph = create_agent(
    model=model,
    tools=[statistical_analysis, generate_chart],
    system_prompt="Bạn là chuyên gia phân tích dữ liệu chuyên sâu và trực quan hóa biểu đồ.",
)

# 2. Đóng gói thành CompiledSubAgent
data_subagent = CompiledSubAgent(
    name="data-analyzer",
    description="Thực thi quy trình phân tích dữ liệu đa bước phức tạp, bao gồm kiểm định thống kê và xuất biểu đồ",
    runnable=custom_graph,  # Nhúng đồ thị LangGraph đã compile
)

# 3. Đăng ký vào Main Agent
agent = create_deep_agent(
    model=model,
    subagents=[data_subagent],
)
```

> [!IMPORTANT]
> **Điều kiện tiên quyết của `CompiledSubAgent`:** Đồ thị LangGraph được truyền vào bắt buộc phải có trường `"messages"` trong Schema State của nó để tương thích với cơ chế trao đổi tin nhắn giữa các Agent.

### So sánh: Dictionary vs. `CompiledSubAgent`

| Tiêu chí | Khai báo qua Dictionary | Dùng `CompiledSubAgent` |
|---|---|---|
| **Độ phức tạp** | Rất đơn giản, chỉ cần khai báo cấu hình | Đòi hỏi tự dựng State Graph bằng LangGraph |
| **Quy trình luồng** | Vòng lặp ReAct tiêu chuẩn | Hỗ trợ luồng rẽ nhánh, vòng lặp phức tạp, workflow doanh nghiệp |
| **Tái sử dụng** | Tạo nhanh tại chỗ cho từng Agent | Tái sử dụng lại các Agent Graph đã dựng sẵn từ các dự án khác |

---

## Mô Hình Cộng Tác Đa Sub-Agent (Multi-Subagent Collaboration)

Kiến trúc mạnh mẽ nhất trong thực tế là **mô hình phân quyền chuyên trách**: Một Main Agent đóng vai trò Nhạc Trưởng (Orchestrator) điều phối nhiều Sub-Agent chuyên môn hóa:

```python
import os
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware

# Khởi tạo mô hình điều phối
model = ChatOpenAI(
    model="zai-org/GLM-5.2",
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

# Danh sách các Sub-Agent chuyên trách
subagents = [
    {
        "name": "data-collector",
        "description": "Thu thập dữ liệu thô từ Internet và API bên ngoài",
        "system_prompt": "Bạn là chuyên gia thu thập dữ liệu. Tìm kiếm và tổng hợp số liệu sạch, trả về cấu trúc ngắn gọn.",
        "tools": [internet_search, api_call],
    },
    {
        "name": "data-analyzer",
        "description": "Thực hiện phân tích định lượng trên tập dữ liệu đã thu thập",
        "system_prompt": "Bạn là chuyên gia phân tích. Hãy trích xuất 3-5 insight quan trọng nhất từ dữ liệu, tối đa 300 từ.",
        "tools": [statistical_analysis],
    },
    {
        "name": "report-writer",
        "description": "Biên soạn báo cáo chuyên nghiệp dựa trên kết quả phân tích",
        "system_prompt": "Bạn là cây bút kỹ thuật. Soạn thảo báo cáo rõ ràng, văn phong chuyên nghiệp, lập luận sắc bén.",
        "tools": [format_document],
    },
]

# Tạo Main Agent điều phối
agent = create_deep_agent(
    model=model,
    middleware=[TodoListMiddleware()],
    system_prompt="""Bạn là Trưởng Dự Án (Project Coordinator). Đối với các nhiệm vụ phức tạp:
1. Dùng write_todos để lập kế hoạch tổng thể.
2. Ủy quyền khâu thu thập dữ liệu cho 'data-collector'.
3. Chuyển dữ liệu cho 'data-analyzer' để lấy insight.
4. Chuyển insight cho 'report-writer' để viết báo cáo hoàn chỉnh.
5. Kiểm tra chất lượng cuối cùng trước khi trả lời người dùng.""",
    subagents=subagents,
)
```

![Mô hình đa Sub-Agent: Main Agent điều phối, tuần tự ủy nhiệm qua task() cho data-collector, data-analyzer và report-writer](../public/imgs/14-framework-multi-subagent.png)

---

## Chuẩn Hóa Dữ Liệu Đầu Ra: Structured Output Bằng JSON

Mặc định, kết quả mà Sub-Agent gửi về cho Main Agent là chuỗi văn bản tự do (free text) trích từ message cuối cùng của nó. Điều này khiến Main Agent đôi khi phải tốn thêm token để đọc hiểu và dùng regex bóc tách dữ liệu.

Từ phiên bản `deepagents>=0.5.3`, bạn có thể chỉ định tham số **`response_format`** bằng một **Pydantic Model** để ép buộc Sub-Agent phải trả về cấu trúc JSON chuẩn:

```python
from pydantic import BaseModel, Field
from deepagents import create_deep_agent

# 1. Định nghĩa cấu trúc dữ liệu mong muốn nhận về
class ResearchFindings(BaseModel):
    summary: str = Field(description="Tóm tắt nghiên cứu cốt lõi")
    confidence: float = Field(description="Độ tin cậy của thông tin từ 0.0 đến 1.0")
    sources: list[str] = Field(description="Danh sách URL các nguồn tham khảo uy tín")

# 2. Gắn response_format vào Sub-Agent
research_subagent = {
    "name": "researcher",
    "description": "Nghiên cứu chuyên sâu và trả về kết quả có cấu trúc",
    "system_prompt": "Nghiên cứu kỹ đề tài được giao và trả về phát hiện theo đúng định dạng yêu cầu.",
    "tools": [internet_search],
    "response_format": ResearchFindings,  # Bắt buộc trả về đúng schema này
}

agent = create_deep_agent(model=model, subagents=[research_subagent])
```

Khi được gọi, `ToolMessage` mà Main Agent nhận về sẽ là một chuỗi JSON hợp lệ 100%:
```json
{
  "summary": "LangGraph cung cấp khả năng điều phối luồng có trạng thái...",
  "confidence": 0.95,
  "sources": ["https://langchain-ai.github.io/langgraph/"]
}
```
Nhờ đó, Main Agent (hoặc code ứng dụng) có thể parse trực tiếp thành object để xử lý logic lập trình mà không sợ lỗi định dạng.

---

## Các Best Practices Khi Triển Khai Sub-Agent

### 1. Viết `description` thật tường minh và hướng hành vi
Main Agent dựa hoàn toàn vào chuỗi `description` để chọn mặt gửi vàng. Mô tả càng mơ hồ, tỷ lệ định tuyến sai càng cao:

- ❌ **Kém**: `"description": "Làm nghiên cứu"`
- ✅ **Chuẩn**: `"description": "Dùng khi cần nghiên cứu chuyên sâu trên web, đối chiếu chéo nhiều nguồn tài liệu và tổng hợp phân tích đa chiều."`

### 2. Thiết lập quy chuẩn định dạng và giới hạn độ dài trong `system_prompt`
Luôn kèm theo yêu cầu về cấu trúc đầu ra và **giới hạn số từ** để ngăn Sub-Agent "nói dài nói dai":

```python
"system_prompt": """Bạn là chuyên viên nghiên cứu.
Yêu cầu đầu ra:
- Tóm tắt tổng quan (tối đa 2 đoạn)
- 3-5 phát hiện quan trọng nhất (gạch đầu dòng)
- Danh sách URL trích dẫn
QUAN TRỌNG: Toàn bộ phản hồi phải dưới 400 từ, tuyệt đối không gửi kèm log thô."""
```

### 3. Nguyên tắc đặc quyền tối thiểu (Least Privilege) cho `tools`
Chỉ cung cấp đúng những công cụ mà Sub-Agent thực sự cần để giải quyết nhiệm vụ:

- ❌ **Thừa thãi**: `research_agent = {"tools": [internet_search, send_email, delete_file, execute_code]}`
- ✅ **Chặt chẽ**: `research_agent = {"tools": [internet_search]}`

### 4. Phân tầng Model linh hoạt theo bài toán
Tối ưu hóa chi phí và tốc độ bằng cách dùng model nhẹ cho tác vụ đơn giản và model mạnh cho tác vụ phân tích:

```python
subagents = [
    {
        "name": "quick-lookup",
        "description": "Tra cứu nhanh các sự kiện hoặc định nghĩa cơ bản",
        "tools": [internet_search],
        "model": ChatOpenAI(model="Qwen/Qwen2.5-7B-Instruct"),  # Model 7B siêu nhanh, rẻ/miễn phí
    },
    {
        "name": "deep-analyst",
        "description": "Thực hiện các suy luận logic và phân tích kinh tế đa biến phức tạp",
        "tools": [internet_search, statistical_analysis],
        "model": ChatOpenAI(model="zai-org/GLM-5.2"),          # Model tư duy thượng thừa
    },
]
```

### 5. Kết hợp với File System để luân chuyển dữ liệu lớn
Nếu Sub-Agent thu thập được hàng nghìn dòng dữ liệu thô, **hãy yêu cầu nó ghi ra đĩa bằng `write_file`**, và chỉ trả về đường dẫn file kèm bản tóm tắt cho Main Agent:

```python
"system_prompt": """Khi thu thập được khối lượng lớn dữ liệu thô:
1. Dùng write_file lưu toàn bộ dữ liệu vào /workspace/raw_data.json
2. Tiến hành phân tích dữ liệu
3. Chỉ gửi kết luận phân tích và đường dẫn file về cho Main Agent"""
```

---

## Xử Lý Sự Cố Thường Gặp (Troubleshooting)

### Vấn đề 1: Sub-Agent không bao giờ được gọi — Main Agent tự làm hết mọi việc
- **Nguyên nhân**: `description` của Sub-Agent quá chung chung khiến mô hình không thấy lý do cần ủy quyền, hoặc Main Agent không được "nhắc nhở" về thói quen phân việc.
- **Cách khắc phục**:
  1. Viết lại `description` sắc sảo, chỉ rõ các trường hợp cụ thể cần kích hoạt.
  2. Thêm chỉ dẫn vào `system_prompt` của Main Agent: *"Khi gặp tác vụ phức tạp, bạn BẮT BUỘC phải dùng công cụ task() để phân chia việc cho Sub-Agent, giữ context của bạn luôn sạch sẽ."*

### Vấn đề 2: Ngữ cảnh của Main Agent vẫn bị phình to
- **Nguyên nhân**: Sub-Agent trả về toàn bộ kết quả tìm kiếm thô trong tin nhắn cuối cùng.
- **Cách khắc phục**: Siết chặt prompt của Sub-Agent với câu lệnh cấm: *"Tuyệt đối không gửi raw data, chỉ gửi summary chắt lọc dưới 300 từ"*, hoặc hướng dẫn ghi dữ liệu thô vào file system.

### Vấn đề 3: Gọi nhầm Sub-Agent
- **Nguyên nhân**: Sự nhập nhằng giữa các mô tả (Overlap descriptions).
- **Cách khắc phục**: Tạo sự tương phản rõ rệt trong `description`:
  - `quick-researcher`: *"Chỉ dùng cho câu hỏi đơn giản, tìm 1-2 lần lấy định nghĩa..."*
  - `deep-researcher`: *"Dùng cho đề tài học thuật dài hạn, cần tổng hợp hàng chục nguồn..."*

---

## Tổng Kết (Key Takeaways)

1. **Context Quarantine**: Sub-Agent giải quyết bài toán cốt tử về bùng nổ ngữ cảnh bằng cách cô lập toàn bộ các bước thực thi trung gian vào một không gian riêng.
2. **Khai báo dạng Dictionary**: Gồm 3 trường bắt buộc (`name`, `description`, `system_prompt`). Lưu ý rằng `tools` và `permissions` nếu khai báo sẽ **thay thế hoàn toàn** chứ không cộng dồn từ cha; `skills` không tự động kế thừa.
3. **General-purpose Sub-Agent**: Trợ lý vô danh mặc định giúp cách ly context mà không cần cấu hình; có thể vô hiệu hóa an toàn qua `GeneralPurposeSubagentProfile(enabled=False)`.
4. **CompiledSubAgent**: Cầu nối cho phép đưa toàn bộ quy trình LangGraph phức tạp vào làm việc dưới quyền của Deep Agent.
5. **Structured Output**: Sử dụng `response_format` với Pydantic để chuẩn hóa giao tiếp giữa các Agent thành JSON, loại bỏ rủi ro khi parse văn bản tự do.

Ở **Chương 6**, chúng ta sẽ nâng cấp cơ chế ủy quyền lên một tầm cao mới: **Async Sub-Agents (Sub-Agent Bất Đồng Bộ)** — cho phép Main Agent phát lệnh cho nhiều Sub-Agent chạy ngầm song song cùng một lúc trên kiến trúc Agent Server chuyên dụng!
