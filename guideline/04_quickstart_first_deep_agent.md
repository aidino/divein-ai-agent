# Chương 2: Quickstart — Dựng Deep Agent đầu tiên của bạn trong 5 phút

Phần nhận thức EP.02

> Chương trước chúng ta đã hiểu định vị thiết kế của Deep Agents. Chương này bước vào phần thực hành — từ cài đặt đến chạy, dẫn bạn hoàn thành research assistant đầu tiên biết tìm kiếm internet và viết report.

## Chuẩn bị môi trường

### Cài đặt Deep Agents

Deep Agents được phát hành dưới dạng một Python package độc lập. Ví dụ trong chương này kết nối model qua `ChatOpenAI`, nên cần cài thêm `langchain-openai`. Chọn tool quản lý package bạn quen dùng:

```
# pip
pip install deepagents langchain-openai

# uv (khuyến nghị, nhanh hơn)
uv pip install deepagents langchain-openai

# poetry
poetry add deepagents langchain-openai
```

Yêu cầu Python bản bản 3.11+.

### Cấu hình API Key

Deep Agents hỗ trợ nhiều nhà cung cấp model. Bạn cần cấu hình ít nhất một API Key của model.

Serie này khuyến nghị dùng [SiliconFlow](https://siliconflow.cn/) làm nhà cung cấp model. Lý do rất đơn giản:

- **Kết nối trực tiếp từ Trung Quốc**, không cần proxy
- **Tương thích OpenAI interface**, chi phí kết nối gần như bằng không
- **Cung cấp nhiều model miễn phí**, phù hợp học tập và thử nghiệm; phạm vi cụ thể và quy tắc rate limit lấy theo trang nền tảng
- **Lựa chọn model phong phú**: Qwen, DeepSeek, GLM v.v. — các model open source chủ lưu đều dùng được

Đăng ký [nền tảng SiliconFlow](https://cloud.siliconflow.cn/), tạo Key ở [trang API Key](https://cloud.siliconflow.cn/account/ak), rồi cấu hình biến môi trường:

```
export SILICONFLOW_API_KEY="your-siliconflow-key"
# Tùy chọn: chỉ định model qua biến môi trường, thuận tiện chuyển đổi tổng thể, không phải sửa code từng chỗ
export MODEL_NAME="Qwen/Qwen2.5-7B-Instruct"   # Hiện miễn phí, hỗ trợ Tools, phù hợp học tập
```

> Dĩ nhiên, bạn cũng có thể dùng nhà cung cấp khác (Anthropic, OpenAI, Google, v.v.), chỉ cần cấu hình API Key tương ứng. Toàn bộ code ví dụ của serie này mặc định dùng SiliconFlow, nhưng nguyên lý hoàn toàn giống nhau.
>
> **Lưu ý bảo trì version model**: ví dụ của serie này mặc định dùng `Qwen/Qwen2.5-7B-Instruct` (hiện miễn phí, nhẹ, hỗ trợ tool calling, phù hợp nhập môn và task đơn giản). Với các kịch bản phức tạp — lập kế hoạch task, tóm tắt context, điều phối nhiều sub-Agent — cũng như các ví dụ nâng cao có Middleware xếp chồng (stack), model nhỏ (như 7B) thường không chạy ổn định hết toàn bộ luồng; khuyến nghị đổi sang model mạnh hơn, hỗ trợ tool calling, ví dụ `zai-org/GLM-5.2`. Model trên nền tảng, giá và phạm vi miễn phí sẽ thay đổi; khuyến nghị quản lý tên model bằng biến môi trường `MODEL_NAME` như trên; trước khi dùng hãy xem [model plaza](https://cloud.siliconflow.cn/models), [trang giá](https://siliconflow.cn/pricing) và [thông báo cập nhật](https://api-docs.siliconflow.cn/docs/release-notes/overview).

## Hello World: Deep Agent đơn giản nhất

Hãy bắt đầu từ ví dụ đơn giản nhất — một Agent trả lời được câu hỏi về thời tiết:

```
import os
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent

# Kết nối model qua SiliconFlow (tương thích OpenAI interface)
model = ChatOpenAI(
    # Model miễn phí hiện tại, có thể ghi đè bằng biến môi trường MODEL_NAME (ví dụ zai-org/GLM-5.2 trả phí)
    model=os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct"),
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_deep_agent(
    model=model,
    tools=[get_weather],
    system_prompt="You are a helpful assistant.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Thời tiết hôm nay ở Bắc Kinh thế nào?"}]}
)

print(result["messages"][-1].content)
```

Chỉ vài dòng code, một Agent có năng lực tool calling đã chạy được. Hãy cùng mổ xẻ các phần then chốt.

### Các tham số cốt lõi của `create_deep_agent()`

```
agent = create_deep_agent(
    model=model,                           # Model instance hoặc chuỗi
    tools=[get_weather],                   # Danh sách custom tool
    system_prompt="You are a helpful...",  # System prompt
)
```

| Tham số         | Mô tả                                                       | Giá trị mặc định              |
| --------------- | ----------------------------------------------------------- | ----------------------------- |
| `model`         | Model instance (như `ChatOpenAI`) hoặc chuỗi `provider:model_name` | `claude-sonnet-4-6` (có thể ghi đè) |
| `tools`         | Danh sách hàm custom tool                                   | `[]`                          |
| `system_prompt` | System prompt, định nghĩa vai trò và hành vi của Agent      | Base prompt mặc định của v0.7 là rỗng |

Lưu ý, ngoài `tools` bạn truyền vào, Deep Agent còn cung cấp các năng lực Harness như file system và sub-Agent. v0.7 không còn mặc định bật lập kế hoạch task; khi cần `write_todos`, hãy thêm `TodoListMiddleware` một cách tường minh. Nhờ đó, task ngắn không phải trả chi phí cố định cho planning tool và prompt, còn task dài có thể chủ động chọn lớp scaffolding này.

### Input/output của `agent.invoke()`

Input là một dict chứa `messages`, tuân theo định dạng message chuẩn:

```
{"messages": [{"role": "user", "content": "Câu hỏi của bạn"}]}
```

Output cũng là một dict, `result["messages"]` chứa toàn bộ lịch sử hội thoại, message cuối cùng chính là câu trả lời cuối của Agent:

```
result["messages"][-1].content  # Text trả lời của Agent
```

## Viết custom tool

Tool definition trong Deep Agents rất đơn giản — **một hàm Python bình thường đã là một tool**. Agent hiểu tool này làm được gì qua signature của hàm (tên tham số và type annotation) và docstring.

### Ba yếu tố của tool definition

```
def internet_search(
    query: str,                          # 1. Tên tham số + type annotation
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
) -> dict:                               # 2. Return type
    """Run a web search for the given query."""  # 3. Docstring
    # Logic thực tế của tool
    return tavily_client.search(query, max_results=max_results, topic=topic)
```

Thiếu một trong ba yếu tố đều không được:

| Yếu tố             | Tác dụng                                | Ảnh hưởng tới Agent                          |
| ------------------ | --------------------------------------- | -------------------------------------------- |
| **Type annotation**| Cho Agent biết tham số nào nên truyền kiểu gì | Thiếu type annotation, Agent có thể truyền sai kiểu |
| **Docstring**      | Cho Agent biết công dụng của tool       | Thiếu docstring, Agent không biết khi nào nên dùng tool này |
| **Giá trị mặc định** | Đánh dấu tham số nào là tùy chọn      | Agent chỉ cần điền tham số bắt buộc, giảm xác suất lỗi |

> Bạn có thể hình dung docstring như "hướng dẫn sử dụng" dành cho Agent — viết càng rõ ràng, Agent dùng càng chính xác.

## Thử sức đầu tay: viết một calculator Agent

Trước khi xem tool search thật, hãy tự viết 1–2 tool bằng "ba yếu tố" vừa học để hiểu sâu hơn. Ví dụ này không phụ thuộc bất kỳ external API nào, thuần logic local là chạy được — để bạn tập trung vào "cách thiết kế tool" thay vì "cách cấu hình dịch vụ bên ngoài".

Tái dùng `model` ở trên, chúng ta định nghĩa hai tool nhỏ: một làm phép tính số học cơ bản, một quy đổi đơn vị tiền tệ. Để ý cách mỗi tool hiện thực hóa ba yếu tố — **type annotation + docstring + giá trị mặc định**:

```
def calculate(expression: str) -> float:
    """Evaluate a math expression and return the result.

    Args:
        expression: A math expression, e.g. "1 + 2 * 3".
    """
    # Chỉ để minh họa; dự án thực tế nên dùng thư viện parse an toàn thay vì eval
    return eval(expression)

def convert_currency(amount: float, from_currency: str, to_currency: str = "CNY") -> dict:
    """Convert an amount from one currency to another.

    Args:
        amount: The amount to convert.
        from_currency: The source currency code, e.g. "USD".
        to_currency: The target currency code, defaults to "CNY".
    """
    # Dùng tỷ giá cố định để minh họa; kịch bản thực tế có thể kết nối exchange rate API
    rates = {"USD": 7.2, "CNY": 1.0, "EUR": 7.8}
    cny = amount * rates[from_currency]
    return {"amount": round(cny / rates[to_currency], 2), "currency": to_currency}
```

Giao chúng cho Agent, kèm một "nhân cách" (persona) rõ ràng:

```
agent = create_deep_agent(
    model=model,
    tools=[calculate, convert_currency],
    system_prompt="Bạn là một trợ lý tính toán, có thể giúp người dùng làm phép tính toán học và quy đổi tiền tệ.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Hãy đổi 100 USD ra CNY cho tôi, rồi nhân kết quả với hệ số lạm phát 1.08."}]}
)
print(result["messages"][-1].content)
```

Chỉ một đoạn code ngắn, bạn đã tự hoàn thành thiết kế hai tool. Để ý vài điểm then chốt: tham số của `calculate` nhận cả biểu thức bằng chuỗi (type annotation cho Agent biết cần truyền text chứ không phải số); `to_currency` của `convert_currency` có giá trị mặc định, nên khi chỉ quan tâm quy đổi ra CNY, Agent chỉ cần điền hai tham số đầu. Đây chính là "ba yếu tố" trong thiết kế thực tế — **type annotation quyết định hình thái input, docstring quyết định thời điểm gọi, giá trị mặc định giảm số trường bắt buộc**.

Nắm được phương pháp thiết kế này, sang phần sau khi đưa external API thật vào, bạn sẽ không thấy bỡ ngỡ nữa.

## Thực chiến: Xây dựng một research assistant

> Đọc lần đầu có thể tạm bỏ qua phần này; các chương sau sẽ từng bước mở rộng external tool và điều phối nhiều bước. Nếu bạn đã quen hệ sinh thái LangChain, có thể làm theo luôn; nếu chưa, khuyến nghị luyện tập kỹ các tool đơn giản phía trước, chạy thuận rồi mới quay lại.

Giờ chúng ta xây một Agent thực sự dùng được — một assistant biết tìm kiếm internet và viết research report.

### Step 1: Cài dependency

Chúng ta dùng [Tavily](https://docs.tavily.com/documentation/api-credits) làm search API (gói miễn phí hiện tại gồm 1.000 Credits mỗi tháng), và SiliconFlow làm nhà cung cấp model:

```
pip install deepagents langchain-openai tavily-python
```

Cấu hình API Key:

```
export SILICONFLOW_API_KEY="your-siliconflow-key"
export TAVILY_API_KEY="your-tavily-key"
```

### Step 2: Định nghĩa search tool

```
import os
from typing import Literal
from tavily import TavilyClient

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search for the given query.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        topic: The topic category for the search.
        include_raw_content: Whether to include raw page content.
    """
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
```

### Step 3: Tạo Agent và cấu hình system prompt

System prompt là "nhân cách" của Agent — nó định nghĩa vai trò, năng lực và cách làm việc của Agent:

```
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware

# Kết nối model qua SiliconFlow (Qwen2.5-7B miễn phí hiện tại chạy được; task phức tạp có thể đổi GLM-5.2)
model = ChatOpenAI(
    model=os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct"),  # Có thể ghi đè bằng MODEL_NAME
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

research_instructions = """Bạn là một research assistant chuyên nghiệp.
Công việc của bạn là nghiên cứu sâu, sau đó viết một bản research report hoàn chỉnh.

Bạn có thể dùng tool internet_search để tìm kiếm thông tin trên internet.
"""

agent = create_deep_agent(
    model=model,
    tools=[internet_search],
    system_prompt=research_instructions,
    middleware=[TodoListMiddleware()],
)
```

System prompt chỉ cần nêu mục tiêu nghiên cứu, yêu cầu về bằng chứng và ranh giới output. Tham số và interface của `internet_search` đã được tool Schema diễn đạt, không cần copy lại một lần hướng dẫn sử dụng chung; chỉ khi nghiệp vụ thực sự đòi hỏi thứ tự gọi hoặc phạm vi nguồn cụ thể, mới bổ sung quy tắc tương ứng.

### Step 4: Chạy Agent

```
result = agent.invoke(
    {"messages": [{"role": "user", "content": "LangGraph là gì?"}]}
)

print(result["messages"][-1].content)
```

## Agent đã làm gì phía sau?

Khi bạn gọi `agent.invoke()`, Deep Agent tự động thực hiện một loạt thao tác. Đây chính là giá trị của nó với tư cách một Harness — bạn chỉ viết vài dòng code, nhưng workflow phía sau Agent phức tạp hơn những gì bạn thấy nhiều:

1. **Lập kế hoạch task** — vì ví dụ bật tường minh `TodoListMiddleware`, Agent có thể gọi `write_todos`, phân rã "nghiên cứu LangGraph" thành nhiều sub-step
2. **Tìm kiếm thông tin** — gọi tool `internet_search` bạn cung cấp, thực hiện nhiều lần search
3. **Quản lý context** — gọi `write_file` built-in để ghi lượng lớn kết quả search vào virtual file system, tránh tràn context
4. **Delegate sub-task (nếu cần)** — gọi tool `task` built-in, giao sub-task phức tạp cho sub-Agent chuyên biệt
5. **Tổng hợp report** — đọc thông tin đã chỉnh lý từ file system, viết report cuối cùng

Trong quá trình này, Agent có thể đã gọi tool 10+ lần, nhưng bạn chỉ cần một lần gọi `invoke()`.

![Đằng sau agent.invoke() là gì? Lập kế hoạch task → Tìm kiếm thông tin → Quản lý context → Delegate sub-task (nếu cần) → Tổng hợp report; bạn chỉ viết 1 dòng gọi, Agent tự động hoàn thành 10+ lần tool call](https://datawhalechina.github.io/deepagents-in-action/imgs/05-flowchart-agent-workflow.png)

> [!NOTE]
> **Lưu ý v0.7**: quy trình lập kế hoạch trong hình tương ứng task nghiên cứu phức tạp "đã bật Todo". Khi không truyền `TodoListMiddleware`, Agent sẽ không có `write_todos` và state `todos`; ngay cả khi đã bật, model cũng sẽ căn cứ task để quyết định có thực sự gọi tool hay không — không được coi mỗi bước trong hình là một giao thức thực thi cố định.

## Lựa chọn model

Deep Agents hỗ trợ bất kỳ LangChain Chat Model nào triển khai Tool Calling.

### Trước tiên hiểu hai interface chuẩn

Ngành LLM hiện nay đã hình thành hai giao thức interface chuẩn de facto:

- **OpenAI-compatible interface** (`/chat/completions`): chuẩn được áp dụng rộng rãi nhất, hầu hết nền tảng trong và ngoài Trung Quốc đều tương thích
- **Anthropic-compatible interface** (`/messages`): protocol gốc của Anthropic, một số nền tảng cũng cung cấp bản tương thích

SiliconFlow hỗ trợ đồng thời cả hai interface, nghĩa là bạn có thể dùng `ChatOpenAI` hoặc `ChatAnthropic` để kết nối model trên cùng một nền tảng.

![So sánh hai interface chuẩn của LLM: OpenAI-compatible (/chat/completions, phổ biến nhất ngành) và Anthropic-compatible (/messages); SiliconFlow tương thích cả hai, có thể kết nối các model GLM, Kimi, Qwen, DeepSeek, v.v.](https://datawhalechina.github.io/deepagents-in-action/imgs/06-comparison-api-interfaces.png)

### Cách 1: OpenAI-compatible interface (khuyến nghị)

Phần lớn nền tảng model Trung Quốc (SiliconFlow, DeepSeek, Zhipu AI, Alibaba Cloud Bailian, v.v.) đều tương thích OpenAI interface. Chỉ cần đặt `base_url` qua `ChatOpenAI` là kết nối được:

```
from langchain_openai import ChatOpenAI

# SiliconFlow (model miễn phí hiện tại, phù hợp học tập)
model = ChatOpenAI(
    model="Qwen/Qwen2.5-7B-Instruct",
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)
agent = create_deep_agent(model=model)

# SiliconFlow (model khuyến nghị cho task phức tạp)
model = ChatOpenAI(
    model="zai-org/GLM-5.2",
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)
agent = create_deep_agent(model=model)
```

> Mô thức `base_url` này là cách phổ quát để kết nối các nền tảng Trung Quốc — đổi URL và Key là chuyển được sang DeepSeek, Zhipu, Alibaba Cloud v.v.

### Cách 2: Anthropic-compatible interface

Nếu bạn thích message format của Anthropic, SiliconFlow cũng cung cấp interface tương thích:

```
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(
    model="zai-org/GLM-5.2",
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn",
)
agent = create_deep_agent(model=model)
```

### Cách 3: String format (phù hợp kết nối trực tiếp nền tảng gốc)

Nếu bạn dùng thẳng official API của Anthropic hoặc OpenAI (không qua nền tảng bên thứ ba), có thể dùng string format gọn hơn:

```
# Kết nối trực tiếp official API của Anthropic (cần cấu hình ANTHROPIC_API_KEY)
agent = create_deep_agent(model="anthropic:claude-sonnet-4-6")

# Kết nối trực tiếp official API của OpenAI (cần cấu hình OPENAI_API_KEY)
agent = create_deep_agent(model="openai:gpt-4.1")
```

### Model khuyến nghị

**[Model trên nền tảng SiliconFlow](https://www.siliconflow.cn/models):**

Các model sau đều hỗ trợ tool calling (Tools), dùng trực tiếp được với Deep Agents:

**Model miễn phí hiện tại (phù hợp học tập và thử nghiệm):**

| Model                         | Số tham số | Đặc điểm                                                                                              |
| ----------------------------- | ---------- | ----------------------------------------------------------------------------------------------------- |
| `Qwen/Qwen2.5-7B-Instruct`    | 7B         | Hiểu tiếng Trung tốt, hỗ trợ Tools, nhẹ và nhanh; bản miễn phí hiện tại có [Rate Limits](https://docs.siliconflow.cn/docs/userguide/faqs/rate-limit-and-upgradation) cố định |

**Model khuyến nghị (phù hợp sử dụng thực tế):**

| Model                              | Số tham số             | Đặc điểm                                                                          |
| ---------------------------------- | ---------------------- | --------------------------------------------------------------------------------- |
| `zai-org/GLM-5.2`                  | 753B                   | Hướng tới task Agent long-range, hỗ trợ tool calling và context 1M                |
| `moonshotai/Kimi-K2.7-Code`        | 1T (MoE, 32B active)   | Hướng tới task code long-range, hỗ trợ tool call nhiều bước, input hình ảnh và context 256K |
| `deepseek-ai/DeepSeek-V4-Pro`      | 1.6T (MoE, 49B active) | Hỗ trợ tool calling, ba mức reasoning strength và context 1M                      |
| `nex-agi/Nex-N2-Pro`               | 397B                   | Đã kết thúc trải nghiệm miễn phí; hiện input ¥1.75/M Tokens, output ¥7/M Tokens, cache hit ¥0.175/M Tokens |
| `Qwen/Qwen3.6-35B-A3B`             | 35B (MoE, 3B active)   | Hỗ trợ mode thinking/non-thinking, tool calling, input hình ảnh và context 256K   |
| `deepseek-ai/DeepSeek-V4-Flash`    | 284B (MoE, 13B active) | Hỗ trợ tool calling và context 1M, phù hợp kiểm soát chi phí chạy thử             |

> **Cập nhật trạng thái (2026-07-22)**: trải nghiệm miễn phí của `nex-agi/Nex-N2-Pro` đã kết thúc, nền tảng tính phí theo lượng dùng từ 2026-06-26. Serie này vẫn dùng `Qwen/Qwen2.5-7B-Instruct` (miễn phí hiện tại) để hạ rào cản nhập môn; các kịch bản phức tạp như lập kế hoạch task, điều phối nhiều Agent có thể đổi sang model mạnh hơn như `zai-org/GLM-5.2`, `moonshotai/Kimi-K2.7-Code`. Giá và tình trạng khả dụng có thể tiếp tục thay đổi, hãy lấy [trang giá](https://siliconflow.cn/pricing) và [thông báo cập nhật](https://api-docs.siliconflow.cn/docs/release-notes/overview) làm chuẩn.

## Debug và tracing: LangSmith

Khi hành vi Agent không như mong đợi, bạn cần thấy được "nó đang nghĩ gì bên trong". LangSmith là nền tảng observability của LangChain, ghi lại từng lần model call, tool call và biến đổi state của Agent.

### Cấu hình nhanh

```
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY="your-langsmith-key"
```

Sau khi set biến môi trường, không cần sửa bất kỳ dòng code nào, lịch sử chạy của Agent sẽ tự động upload lên LangSmith.

### Bạn sẽ thấy gì

Trong panel Trace của LangSmith, bạn có thể thấy:

- Toàn bộ chuỗi ra quyết định của Agent (input/output của mỗi lần model call)
- Tham số và giá trị trả về của tool call
- Quá trình thực thi của sub-Agent
- Token tiêu thụ và thời gian từng bước
- Biến đổi của các file trong virtual file system

Điều này then chốt để hiểu "tại sao Agent lại ra quyết định này", nhất là khi debug các task phức tạp nhiều bước.

## Code hoàn chỉnh

Gộp toàn bộ nội dung trên lại, dưới đây là code hoàn chỉnh chạy được:

```
import os
from typing import Literal
from langchain_openai import ChatOpenAI
from tavily import TavilyClient
from deepagents import create_deep_agent

# 1. Cấu hình model (kết nối qua SiliconFlow, model miễn phí hiện tại chạy được)
model = ChatOpenAI(
    model=os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct"),  # Task phức tạp có thể đổi "zai-org/GLM-5.2"
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

# 2. Khởi tạo search client
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# 3. Định nghĩa search tool
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search for the given query.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        topic: The topic category for the search.
        include_raw_content: Whether to include raw page content.
    """
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

# 4. Định nghĩa system prompt
research_instructions = """Bạn là một research assistant chuyên nghiệp.
Công việc của bạn là nghiên cứu sâu, sau đó viết một bản research report hoàn chỉnh.

Bạn có thể dùng tool internet_search để tìm kiếm thông tin trên internet.
"""

# 5. Tạo Agent
agent = create_deep_agent(
    model=model,
    tools=[internet_search],
    system_prompt=research_instructions,
)

# 6. Chạy
result = agent.invoke(
    {"messages": [{"role": "user", "content": "LangGraph là gì?"}]}
)
print(result["messages"][-1].content)
```

## Tóm tắt

Trong chương này, chúng ta đã hoàn thành hành trình từ không đến một:

1. **Dựng môi trường**: `pip install deepagents langchain-openai` + cấu hình SiliconFlow API Key
2. **Kết nối Model**: qua `ChatOpenAI` + `base_url` kết nối SiliconFlow, kết nối trực tiếp; nền tảng hiện có model miễn phí
3. **API cốt lõi**: `create_deep_agent(model, tools, system_prompt)` tạo Agent, `agent.invoke()` để chạy
4. **Custom tool**: hàm Python + type annotation + docstring = một tool, Agent tự hiểu
5. **Năng lực tự động**: bạn chỉ truyền vào một tool, Agent tự động có đầy đủ năng lực file system, lập kế hoạch task, sub-Agent
6. **Debug tracing**: set `LANGSMITH_TRACING=true` là thấy được toàn bộ chuỗi ra quyết định của Agent

Chương sau, chúng ta sẽ đi sâu vào innovation cốt lõi nhất của Deep Agents — virtual file system, hiểu nó giải bài toán quản lý context bằng Context Engineering thế nào.

## Tải slide bài giảng

[Lec 03: Quickstart](https://datawhalechina.github.io/deepagents-in-action/pdfs/ch02.pdf)

## Tài nguyên liên quan

Lec 03: Quickstart — [Video bài giảng Bilibili](https://www.bilibili.com/video/BV1PUDWBvEVC/) · [Ảnh bài viết Xiaohongshu](http://xhslink.com/o/4ZmCJdkB490)

---

Nguồn: [Deep Agents 实战 — 第 2 章：快速上手 — 5 分钟构建你的第一个 Deep Agent](https://datawhalechina.github.io/deepagents-in-action/chapters/ch02-quickstart/)
