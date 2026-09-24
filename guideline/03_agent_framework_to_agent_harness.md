# Chương 1: Từ Agent Framework đến Agent Harness — logic ra đời của Deep Agents

Phần nhận thức EP.01

> Chương này là phần mở đầu của serie *Deep Agents thực chiến*. Chúng ta chưa vội viết code, mà trả lời trước một câu hỏi gốc rễ: trong khi lĩnh vực phát triển Agent ngày nay đã có quá nhiều framework như vậy, tại sao Deep Agents vẫn cần tồn tại? Nó giải quyết vấn đề gì?

## Một tình huống thực tế

Giả sử bạn cần xây dựng một AI coding assistant. Nó phải:

- Đọc các file source code trong dự án
- Hiểu cấu trúc code, lập kế hoạch chỉnh sửa
- Thực hiện chỉnh sửa theo từng bước và theo dõi tiến độ
- Khi phát hiện vấn đề mới trong quá trình xử lý, có thể "delegate" sub-task cho các Agent chuyên biệt
- Ghi nhớ preference của người dùng xuyên suốt hội thoại nhiều lượt

Nếu bạn tự dựng từ đầu bằng LangChain, bạn sẽ nhận ra mình đang reinventing the wheel: tự viết tool đọc/ghi file, tự viết logic theo dõi task, tự viết cơ chế điều phối sub-Agent… mà những năng lực này, gần như bất kỳ ứng dụng Agent "nghiêm túc" nào cũng cần.

Đó chính là vấn đề Deep Agents muốn giải quyết.

## Ba tầng của phát triển Agent

Trong tech stack của LangChain, phát triển Agent được chia thành ba tầng. Hiểu đúng ba tầng này là chìa khóa để hiểu định vị của Deep Agents.

### Tầng dưới: Agent Runtime (tầng runtime) — LangGraph

**Agent Runtime** là nền móng của toàn bộ tech stack, nó giải quyết vấn đề "làm thế nào để Agent chạy một cách đáng tin cậy":

- **Durable Execution**: Agent crash giữa chừng vẫn có thể resume từ đúng điểm dừng
- **Streaming**: cho người dùng xem realtime quá trình suy nghĩ và thao tác của Agent
- **Human-in-the-Loop**: tạm dừng trước các thao tác quan trọng, chờ phê duyệt của con người
- **Persistence**: lưu context xuyên qua nhiều cuộc hội thoại

LangGraph chính là runtime tầng dưới này. Nó cung cấp một execution engine dựa trên Graph, hỗ trợ đầy đủ các tính năng production-grade nói trên. Bạn có thể hiểu nó như "hệ điều hành" của thế giới Agent — mọi ứng dụng tầng trên đều chạy trên nó.

Các đối thủ cùng tầng gồm: Temporal, Inngest và các durable execution engine khác.

### Tầng giữa: Agent Framework (tầng framework) — LangChain

**Agent Framework** được xây trên Runtime, mang lại trải nghiệm phát triển ở tầng cao hơn: model abstraction, tool interface, Agent loop, Middleware, v.v.

LangChain chính là một framework như vậy. **LangChain 1.0 được xây trên LangGraph** — nó tận dụng graph execution engine và năng lực state management của LangGraph, nhưng expose ra bên ngoài một API gọn gàng hơn. Khi dùng LangChain, thường bạn không cần chạm trực tiếp vào API tầng dưới của LangGraph:

> **Đoạn minh họa**: ở đây chỉ thể hiện hình thái API của `create_agent()`; `web_search` và `calculator` đại diện cho các tool do ứng dụng tự triển khai và đăng ký, không phải hàm toàn cục mà LangChain tự động cung cấp.

```
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-4.1",
    tools=[web_search, calculator],
    system_prompt="You are a helpful assistant."
)
```

Giá trị của tầng framework nằm ở **chuẩn hóa** và **dễ tiếp cận**. Bạn không cần bận tâm execution engine tầng dưới hay logic persist state, framework đã xử lý giúp bạn.

Các đối thủ cùng tầng gồm: Vercel AI SDK, CrewAI, OpenAI Agents SDK, Google ADK, LlamaIndex, v.v.

### Tầng trên: Agent Harness (tầng bộ công cụ) — Deep Agents

Đây là tầng trên cùng, cũng là nhân vật chính của serie khóa học này.

**Agent Harness** là một bộ Agent "mở hộp là dùng được" (out-of-the-box). Trên nền Runtime và Framework, nó **prebuilt sẵn một bộ tool interface và middleware framework đã được kiểm chứng**. Từ v0.7, Harness vẫn cung cấp các năng lực này, nhưng không còn mặc định bật mọi chiến lược cho tất cả ứng dụng.

Hiểu concept này thế nào? Hãy lấy một ví von:

- **Runtime** cung cấp cho bạn bàn làm việc, nguồn điện, đồ bảo hộ an toàn (hạ tầng tầng dưới)
- **Framework** cung cấp cho bạn búa, cưa, đinh (dev tool chuẩn hóa)
- **Harness** giao thẳng cho bạn một phòng tool đã setup sẵn, tool hay dùng treo trên tường, quy trình làm việc dán sẵn trên bảng trắng (mở hộp là dùng được)

Deep Agents chính là một Harness như vậy. Nó tận dụng các building block cốt lõi của LangChain (model, tool interface), chạy trên runtime của LangGraph, và prebuilt sẵn:

| Năng lực                    | Mô tả                                                                                        |
| --------------------------- | -------------------------------------------------------------------------------------------- |
| Virtual file system         | `read_file`, `write_file`, `edit_file`, `delete`, `ls`, `glob`, `grep` — bảy file tool        |
| Lập kế hoạch task           | Bật `TodoListMiddleware` theo nhu cầu để có `write_todos`, phân rã task phức tạp thành các bước track được |
| Delegate sub-Agent          | Tool `task`, cho phép Agent giao sub-task cho các Agent chuyên biệt                          |
| Long-term Memory            | Dựa trên LangGraph Memory Store, hỗ trợ memory persisted xuyên qua nhiều cuộc hội thoại       |

Các đối thủ cùng tầng gồm: Claude Agent SDK của Anthropic, Manus, v.v.

### Tổng quan quan hệ ba tầng

Tóm tắt bằng một bảng (từ tầng dưới lên tầng trên):

| Tầng                 | Đại diện    | Giá trị cốt lõi                                        | Kịch bản phù hợp                              |
| -------------------- | ----------- | ------------------------------------------------------ | --------------------------------------------- |
| Runtime (tầng dưới)  | LangGraph   | Durable Execution, Streaming, Human-in-the-Loop, Persistence | Agent chạy dài hạn cần điều khiển tinh và workflow phức tạp |
| Framework (tầng giữa)| LangChain   | Model abstraction, tool interface, Agent loop, Middleware | Tiếp cận nhanh, xây ứng dụng Agent chuẩn hóa   |
| Harness (tầng trên)  | Deep Agents | Tool interface prebuilt, middleware framework, sub-Agent, long-term memory | Task phức tạp nhiều bước, Agent có tính tự chủ cao |

Ba tầng không thay thế lẫn nhau, mà được xây đắp từ dưới lên. LangGraph là runtime tầng dưới, LangChain xây trên LangGraph để cung cấp abstraction cao hơn, còn Deep Agents xây trên cả hai để cung cấp năng lực Agent mở hộp là dùng được. Bạn có thể chọn làm việc ở tầng khác nhau tùy nhu cầu — cần linh hoạt tối đa thì dùng trực tiếp LangGraph, cần phát triển nhanh thì dùng LangChain, cần giải quyết task phức tạp thì dùng Deep Agents.

![Kiến trúc ba tầng của phát triển Agent: tầng dưới LangGraph (Runtime), tầng giữa LangChain (Framework), tầng trên Deep Agents (Harness), LangSmith bên cạnh xuyên suốt cung cấp observability](https://datawhalechina.github.io/deepagents-in-action/imgs/01-framework-three-layer-architecture.png)

## Tại sao cần Agent Harness?

Bạn có thể hỏi: runtime và framework đã cung cấp mọi thứ cần để xây Agent, tại sao còn cần một Harness?

Câu trả lời đến từ một quan sát: **các sản phẩm Agent thành công đều trông khá giống nhau**.

Nhìn những sản phẩm Agent trên thị trường thực sự hoàn thành được task phức tạp — Claude Code, Manus, Cursor — tuy mỗi cái có nét riêng, nhưng năng lực cốt lõi lại giống nhau một cách đáng ngạc nhiên:

1. **Đều có năng lực thao tác file system**: đọc/ghi, tìm kiếm, chỉnh sửa file
2. **Đều có năng lực lập kế hoạch task**: phân rã task lớn thành các bước nhỏ
3. **Đều có năng lực delegate sub-task**: giao một phần việc cho sub-Agent
4. **Đều có chiến lược quản lý context**: tránh hội thoại quá dài khiến LLM "mất trí nhớ"

Những điểm chung này không phải trùng hợp. Khi task mà Agent đối mặt đủ phức tạp, các năng lực này là bắt buộc. Giá trị của Agent Harness nằm ở chỗ: **cố hóa những pattern đã được kiểm chứng, để bạn không phải implement lại từ đầu mỗi lần**.

## Ý tưởng thiết kế cốt lõi của Deep Agents: Context Engineering

Lõi kỹ thuật của Deep Agents có thể gói gọn trong một concept: **Context Engineering**.

### Vấn đề của cách làm truyền thống

Trong phát triển Agent truyền thống, mọi thông tin đều được nhét vào prompt:

```
System: Bạn là một trợ lý lập trình.
User: Hãy giúp tôi refactor code trong src/.
[Kèm theo: toàn bộ nội dung 20 file, tổng cộng 50000 token]
```

Cách làm này có vài vấn đề chí mạng:

- **Tràn context window**: LLM có giới hạn token, chỉ cần file nhiều lên một chút là không chứa nổi
- **Attention bị pha loãng**: thông tin càng nhiều, mức độ chú ý của LLM dành cho thông tin then chốt càng thấp
- **Không scale được**: không xử lý nổi dự án với quy mô bất kỳ

### Cách làm của Deep Agents

Giải pháp của Deep Agents là đưa vào một **virtual file system**, để Agent làm việc giống như con người:

- Khi cần đọc file, gọi `read_file` để đọc theo nhu cầu
- Khi cần ghi lại kết quả trung gian, gọi `write_file` ghi vào file
- Khi cần tìm kiếm, gọi `grep` hoặc `glob`
- File lớn chỉ đọc đúng phần cần (tham số `offset` / `limit`)

Như vậy, context của Agent chỉ giữ lại thông tin thực sự cần cho bước hiện tại, phần còn lại được lưu trong file system, cần thì lấy ra.

Tinh tế hơn, "file system" này là **ảo và pluggable**:

- Có thể là lưu trữ tạm trong memory (dùng khi phát triển, debug)
- Có thể là đĩa local (xử lý file thật)
- Có thể là database persisted (giữ memory xuyên session)
- Có thể là sandbox từ xa (thực thi code an toàn)
- Thậm chí có thể dùng hỗn hợp (các path khác nhau được route tới backend khác nhau)

Đây chính là Context Engineering — **không phải nhét mọi thông tin lên cho LLM, mà là xây cho LLM một hạ tầng để lấy và quản lý thông tin một cách hiệu quả**.

![So sánh Context Engineering: bên trái Prompt Stuffing truyền thống dẫn tới tràn context, attention bị pha loãng, không scale được; bên phải Deep Agents đọc theo nhu cầu qua virtual file system, đạt được lưu trữ cấu trúc hóa và mở rộng không giới hạn](https://datawhalechina.github.io/deepagents-in-action/imgs/02-comparison-context-engineering.png)

## Deep Agents vs các đối thủ

Trên thị trường có ba Agent Harness chính: Deep Agents, Claude Agent SDK, Codex SDK. Chúng ta hãy xem điểm giống và khác của chúng.

### Khác biệt về định vị

| Chiều               | Deep Agents                                            | Claude Agent SDK              | Codex SDK    |
| ------------------ | ------------------------------------------------------ | ----------------------------- | ------------ |
| **Mục đích**       | Agent đa dụng (kể cả lập trình)                        | AI coding Agent tùy chỉnh     | Agent lập trình prebuilt |
| **Model hỗ trợ**   | Model-agnostic (Anthropic, OpenAI, Google, open source… 100+) | Khóa vào dòng Claude    | Khóa vào dòng OpenAI |
| **Ngôn ngữ SDK**   | Python + TypeScript                                    | Python + TypeScript           | TypeScript   |
| **Môi trường thực thi** | Local + sandbox từ xa + virtual file system       | Local                         | Local + cloud |
| **Giấy phép open source** | MIT                                             | MIT (tầng dưới Claude Code là độc quyền) | Apache-2.0 |

### So sánh năng lực cốt lõi

Ba bên rất gần nhau ở tầng tool cốt lõi — đọc/ghi file, thực thi Shell, tìm kiếm, lập kế hoạch, sub-Agent, MCP, Human-in-the-Loop, Skills — đều được phủ.

Khác biệt thực sự nằm ở tầng kiến trúc:

**Lợi thế riêng của Deep Agents:**

- **Linh hoạt về model**: đổi nhà cung cấp model bất cứ lúc nào, không khóa vào bất kỳ vendor nào. Điều này then chốt với ứng dụng doanh nghiệp
- **Long-term Memory**: memory persisted xuyên session, xuyên thread thông qua Memory Store. Cả Claude Agent SDK lẫn Codex SDK đều không hỗ trợ tính năng này
- **Virtual file system + backend pluggable**: trừu tượng hóa thao tác file thành một interface thống nhất, backend có thể là memory, đĩa, database hoặc sandbox
- **Mô hình Sandbox-as-Tool**: Agent chạy ở local, nhưng có thể gửi các thao tác nhất định (như thực thi code) tới sandbox từ xa để chạy. Đây là thiết kế riêng của Deep Agents
- **Deploy production**: deploy qua LangGraph Platform, kết hợp LangSmith để có đầy đủ observability

**Lợi thế riêng của Claude Agent SDK:**

- Tích hợp sâu với model Claude
- Hệ thống Hooks, thuận tiện cho việc chặn và điều khiển hành vi Agent
- Hỗ trợ tầng HTTP/WebSocket tùy chỉnh và deploy dạng container

**Lợi thế riêng của Codex SDK:**

- Chế độ sandbox cấp OS (`read-only`, `workspace-write`, `danger-full-access`)
- Mode MCP Server built-in
- Môi trường thực thi trên cloud

![So sánh ba Agent Harness: Deep Agents (model-agnostic, virtual file system, long-term memory), Claude Agent SDK (tích hợp sâu Claude, hệ thống Hooks), Codex SDK (sandbox cấp OS, mode MCP Server); năng lực chung gồm đọc/ghi file, thực thi Shell, lập kế hoạch, sub-Agent, v.v.](https://datawhalechina.github.io/deepagents-in-action/imgs/03-comparison-harness-competitors.png)

### Chọn thế nào?

- **Nếu cần linh hoạt về model và memory xuyên session** → Deep Agents
- **Nếu team bạn dùng toàn diện Claude** → Claude Agent SDK
- **Nếu team bạn dùng toàn diện OpenAI** → Codex SDK
- **Nếu cần giải pháp deploy production và observability trọn vẹn** → Deep Agents + LangSmith

## Toàn cảnh kỹ thuật của Deep Agents

Cuối cùng, tóm tắt bằng một hình vị trí của Deep Agents trong toàn bộ hệ sinh thái LangChain:

![Toàn cảnh kỹ thuật Deep Agents: tầng trên cùng Deep Agents (Harness) gồm năm module: file system tool, lập kế hoạch task, sub-Agent, storage backend pluggable, long-term memory; tầng giữa LangChain (Framework) và LangGraph (Runtime); tầng dưới LangSmith cung cấp observability](https://datawhalechina.github.io/deepagents-in-action/imgs/04-framework-tech-panorama.png)

> [!NOTE]
> **Lưu ý v0.7**: hình này ghi lại bức tranh năng lực ở giai đoạn đầu của khóa học; bản thân các năng lực vẫn còn, nhưng cách lắp đặt mặc định đã thay đổi. File tool hiện tại gồm `delete` mới thêm; lập kế hoạch task cần truyền `TodoListMiddleware` một cách tường minh; base prompt mặc định rỗng, business prompt do ứng dụng tự định nghĩa.

## Tóm tắt

Trong chương này, chúng ta đã hiểu định vị thiết kế của Deep Agents:

1. **Phát triển Agent chia thành ba tầng**: Runtime (LangGraph) → Framework (LangChain) → Harness (Deep Agents), xây đắp từ dưới lên
2. **Giá trị của Agent Harness** nằm ở việc cố hóa các năng lực chung của những sản phẩm Agent thành công (file system, lập kế hoạch task, sub-Agent, long-term memory) thành component mở hộp là dùng được
3. **Context Engineering** là ý tưởng cốt lõi của Deep Agents — quản lý context theo nhu cầu bằng virtual file system, thay vì nhét mọi thông tin vào prompt
4. **So với đối thủ**, lợi thế lớn nhất của Deep Agents là tính model-agnostic, backend pluggable của virtual file system, long-term memory, và giải pháp deploy production trọn vẹn

Chương sau, chúng ta sẽ bắt tay thực hành: dựng Deep Agent đầu tiên trong 5 phút.

## Tải slide bài giảng

[Lec 01: Kiến trúc ba tầng của Agent và định vị Deep Agents](https://datawhalechina.github.io/deepagents-in-action/pdfs/ch01-1.pdf) · [Lec 02: Context Engineering và so sánh đối thủ](https://datawhalechina.github.io/deepagents-in-action/pdfs/ch01-2.pdf)

## Tài nguyên liên quan

Lec 01: Kiến trúc ba tầng của Agent và định vị Deep Agents — [Video bài giảng Bilibili](https://www.bilibili.com/video/BV1CPXpBYEui/) · [Ảnh bài viết Xiaohongshu](http://xhslink.com/o/9hQBZz7x08e)

Lec 02: Context Engineering và so sánh đối thủ — [Video bài giảng Bilibili](https://www.bilibili.com/video/BV1Lm9FBfEXC/) · [Ảnh bài viết Xiaohongshu](http://xhslink.com/o/44JWgAHK0kJ)

---

Nguồn: [Deep Agents 实战 — 第 1 章：从 Agent Framework 到 Agent Harness](https://datawhalechina.github.io/deepagents-in-action/chapters/ch01-agent-harness/)
