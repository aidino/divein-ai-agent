# Chương 7: Skills — Gói Năng Lực Tái Sử Dụng Cho Agent

> **Công cụ (Tools)** là các thao tác mang tính nguyên tử (atomic operations) — tìm kiếm một lần, đọc một tệp tin, gọi một endpoint API. Tuy nhiên, có những năng lực phức tạp không thể giải quyết bằng một thao tác đơn lẻ, mà đòi hỏi sự kết hợp giữa **quy trình đa bước (multi-step workflow) + tri thức nghiệp vụ chuyên sâu (domain knowledge) + tài nguyên biểu mẫu (templates/assets)**. 
> Ví dụ: *"Thực hiện code review theo chuẩn quy ước của dự án"*, *"Tra cứu tài liệu mới nhất của LangGraph rồi giải đáp thắc mắc"*, hay *"Lập báo cáo kỹ thuật chuẩn mẫu doanh nghiệp"*. Những tác vụ này không đơn thuần là một công cụ, mà là cả một tập hợp các chỉ dẫn và quy trình bài bản. Đó chính là bài toán cốt lõi mà **Skills (Kỹ năng)** giải quyết.

---

## Skills Là Gì?

Một **Skill** về bản chất là một thư mục có cấu trúc, trong đó hạt nhân là tệp tin `SKILL.md`, đi kèm các tài nguyên tùy chọn như script thực thi, tài liệu tham khảo và biểu mẫu mẫu (templates). 

Skills tuân thủ đặc tả mở [Agent Skills Specification](https://agentskills.io/specification). Đây **không phải** là một chuẩn độc quyền của Deep Agents, mà là một chuẩn công nghiệp mở (open standard) đang được cộng đồng AI đón nhận rộng rãi.

Tính đến năm 2026, đã có **hơn 30 công cụ và nền tảng AI Agent hàng đầu** áp dụng chuẩn Agent Skills:

| Phân loại | Sản phẩm tiêu biểu |
|---|---|
| **Coding Agents** | Claude Code, OpenAI Codex, Gemini CLI, Cursor, VS Code |
| **Agent Frameworks** | Deep Agents, Goose, Roo Code, Amp, Letta |
| **Enterprise Platforms** | GitHub, Databricks, Snowflake, Spring AI |
| **Specialized Tools** | JetBrains Junie, Mistral Vibe, Laravel Boost, Qodo |

> 💡 **Ý nghĩa thực tiễn của chuẩn mở:**
> Việc tuân theo một đặc tả chuẩn hóa đồng nghĩa với việc bạn chỉ cần viết một Skill một lần duy nhất là có thể tái sử dụng trên mọi nền tảng tương thích. Tri thức nghiệp vụ và quy trình mà đội ngũ của bạn tích lũy sẽ không bị khóa chặt vào một công cụ hay nhà cung cấp độc quyền (no vendor lock-in).
>
> **Phép ẩn dụ:** *Skills đối với AI Agent cũng tương tự như các npm package đối với hệ sinh thái Node.js hay thư viện pip đối với Python* — một cơ chế đóng gói, phân phối và tái sử dụng năng lực đã được chuẩn hóa.

![Hệ sinh thái Agent Skills: Hơn 30 công cụ phát triển AI phổ biến đã áp dụng chuẩn mở này](https://datawhalechina.github.io/deepagents-in-action/imgs/19-infographic-skills-ecosystem.png)

---

### Cấu Trúc Thư Mục Chuẩn Theo Đặc Tả

Một thư mục Skill chuẩn hóa có cấu trúc phân cấp như sau:

```text
skills/
└── langgraph-docs/
    ├── SKILL.md              # Bắt buộc: Metadata (frontmatter) + Chỉ dẫn cốt lõi (Markdown body)
    ├── scripts/              # Tùy chọn: Các script có thể thực thi (Python, Bash, JS/TS, v.v.)
    │   └── fetch_docs.py
    ├── references/           # Tùy chọn: Tài liệu tham khảo chi tiết, kiến trúc, style guide
    │   ├── api-patterns.md
    │   └── style-guide.md
    └── assets/               # Tùy chọn: Biểu mẫu báo cáo, file cấu hình, JSON schema, data mẫu
        ├── report-template.md
        └── schema.json
```

| Thư mục / Tệp tin | Mục đích sử dụng | Thời điểm nạp vào Context (Loading Timing) |
|---|---|---|
| `SKILL.md` | Chứa metadata nhận diện và chỉ dẫn thực hiện nghiệp vụ | Phần **metadata** nạp vào system prompt ngay khi khởi động; phần **nội dung chi tiết** chỉ được Agent đọc theo nhu cầu (*on-demand*). |
| `scripts/` | Các script tự động hóa (Python, Bash, Node.js...) | Chỉ được gọi hoặc thực thi khi quy trình chỉ dẫn yêu cầu. |
| `references/` | Tài liệu mở rộng, bảng tra cứu API, hướng dẫn quy chuẩn | Agent chỉ đọc khi cần đào sâu chi tiết kỹ thuật chuyên biệt. |
| `assets/` | File tĩnh, schemas, template mẫu markdown/JSON | Agent đọc khi cần lấy khung dàn ý hoặc cấu trúc dữ liệu chuẩn. |

---

## Cấu Trúc Của Tệp `SKILL.md`

Hạt nhân của mỗi Skill là tệp tin `SKILL.md`, cấu thành từ hai phần rõ rệt: **YAML Frontmatter** (khai báo siêu dữ liệu) và **Markdown Body** (nội dung chỉ dẫn thực thi).

### 1. YAML Frontmatter

Frontmatter nằm ở phần đầu tệp tin, được bao bọc giữa hai hàng dấu gạch ngang gập ba `---`. Phần này định nghĩa danh tính, phạm vi hoạt động và ràng buộc của Skill:

| Trường (Field) | Bắt buộc | Kiểu dữ liệu / Quy cách | Ý nghĩa kỹ thuật |
|---|:---:|---|---|
| `name` | ✅ Có | String (1–64 ký tự) | Tên định danh của Skill, chỉ gồm chữ cái viết thường, chữ số và dấu gạch nối (`-`). **Bắt buộc phải trùng khớp với tên thư mục chứa nó**. |
| `description` | ✅ Có | String (Tối đa 1024 ký tự) | Mô tả chi tiết tính năng và **điều kiện kích hoạt**. Đây là cơ sở duy nhất để Agent quyết định có dùng Skill hay không. |
| `license` | ❌ Không | String | Tên giấy phép mã nguồn mở hoặc sở hữu trí tuệ (MIT, Apache-2.0, Proprietary...). |
| `compatibility` | ❌ Không | String (Tối đa 500 ký tự) | Ràng buộc môi trường vận hành (ví dụ: cần kết nối Internet, cần cài đặt Docker CLI, yêu cầu Python 3.11+...). |
| `metadata` | ❌ Không | Object / Key-Value | Các cặp khóa-giá trị tùy biến mở rộng (ví dụ: `author`, `version`, `entrypoint` cho code interpreter). |
| `allowed-tools` | ❌ Không | String (Phân tách bởi dấu cách) | Danh sách các công cụ được ủy quyền trước mà Skill này được phép sử dụng. |

### 2. Markdown Body

Ngay bên dưới phần Frontmatter là toàn bộ nội dung hướng dẫn chi tiết theo định dạng Markdown. Đây chính là "kịch bản hành động" mà Agent sẽ đọc và tuân theo khi Skill này được kích hoạt.

Dưới đây là một ví dụ hoàn chỉnh về tệp `SKILL.md`:

```markdown
---
name: langgraph-docs
description: Use this skill for requests related to LangGraph in order to fetch relevant documentation to provide accurate, up-to-date guidance.
---

# langgraph-docs

## Overview
This skill explains how to access LangGraph documentation to help answer questions and guide implementation.

## Instructions

### 1. Fetch the documentation index
Use the fetch_url tool to read the following URL:
https://docs.langchain.com/llms.txt

### 2. Select relevant documentation
Based on the question, identify 2-4 most relevant documentation URLs from the index. Prioritize:
- Specific how-to guides for implementation questions
- Core concept pages for understanding questions
- Tutorials for end-to-end examples
- Reference docs for API details

### 3. Fetch and synthesize
Use the fetch_url tool to read the selected documentation URLs, then answer the user's question.
```

---

### `description` Là Trường Quan Trọng Nhất

Trong toàn bộ cấu trúc Skill, trường `description` nắm giữ vai trò quyết định sự thành bại. 

> ⚠️ **Lý do kỹ thuật cốt lõi:**
> Để tiết kiệm ngữ cảnh (token) và tối ưu độ trễ, Agent **không đọc trước nội dung phần Body** của tất cả các Skill. Agent chỉ "nhìn thấy" danh sách các cặp `name` và `description` trong System Prompt. Do đó, chất lượng của câu mô tả `description` quyết định 100% việc Skill có được kích hoạt đúng lúc hay không.

#### So sánh cách viết Description:

* **Description chuẩn mực (Cụ thể, nêu rõ tín hiệu và ngữ cảnh kích hoạt):**
  ```yaml
  # Tiếng Anh
  description: Use this skill for requests related to LangGraph in order to fetch relevant documentation to provide accurate, up-to-date guidance.
  
  # Hoặc mô tả tác vụ chuyên môn rõ ràng
  description: Sử dụng kỹ năng này khi người dùng yêu cầu kiểm tra chất lượng mã nguồn, lỗ hổng bảo mật hoặc hiệu năng ứng dụng. Thực hiện review có cấu trúc và xuất báo cáo chuẩn Markdown.
  ```

* **Description yếu kém (Chung chung, mơ hồ, thiếu tín hiệu nhận dạng):**
  ```yaml
  # Quá ngắn gọn và vô thưởng vô phạt
  description: A helpful skill for developers.
  
  # Không có tiêu chí kích hoạt cụ thể
  description: Dùng để xử lý nhiều loại tác vụ khác nhau trong dự án.
  ```

> ⚠️ **Hậu quả của một Description tồi:**
> 1. **Bỏ sót kích hoạt (Missed Recall / False Negative):** Khi người dùng đặt câu hỏi thuộc đúng chuyên môn của Skill, nhưng Agent không nhận diện được sự liên quan nên bỏ qua, dẫn đến việc trả lời sai lệch hoặc thiếu thông tin.
> 2. **Kích hoạt nhầm (False Recall / False Positive):** Khi câu hỏi không liên quan nhưng mô tả quá chung chung khiến Agent gọi nhầm Skill, làm lãng phí token và gây loãng mạch suy luận.

---

## Progressive Disclosure: Cơ Chế Nạp Dần (Hiển Thị Tiệm Tiến)

Quyết định kiến trúc quan trọng nhất của cơ chế Skills chính là **Progressive Disclosure (Khai báo lũy tiến / Nạp dần theo nhu cầu)**. Thay vì nhồi nhét toàn bộ tài liệu và mã lệnh vào Context Window của Agent ngay từ đầu, hệ thống phân tách việc nạp thông tin thành 3 cấp độ:

![Cấu trúc nạp 3 tầng của Skill: Metadata → Chỉ dẫn cốt lõi → Tài nguyên phụ trợ](https://datawhalechina.github.io/deepagents-in-action/imgs/20-framework-skill-structure.png)

### Cơ Chế Nạp 3 Tầng (3-Level Loading Mechanism)

| Cấp độ (Level) | Nội dung được nạp | Thời điểm nạp | Thực thể xử lý |
|---|---|---|---|
| **Level 1: Metadata** | `name` + `description` + đường dẫn file | Khởi tạo Agent (Startup phase) | `SkillsMiddleware` |
| **Level 2: Instructions** | Nội dung phần Markdown Body của `SKILL.md` | Khi Agent đánh giá câu hỏi của người dùng khớp với `description` | Mô hình LLM tự quyết định gọi công cụ `read_file` |
| **Level 3: Resources** | Các file phụ trợ nằm trong `scripts/`, `references/`, `assets/` | Khi chỉ dẫn trong Level 2 yêu cầu tra cứu tài liệu chuyên sâu | Mô hình LLM tự quyết định đọc thêm theo nhu cầu |

### Luồng Hoạt Động Chi Tiết (Step-by-Step Workflow)

1. **Giai đoạn khởi động (Startup Phase):** 
   - `SkillsMiddleware` quét qua các thư mục con trong đường dẫn cấu hình.
   - Trích xuất trường `name` và `description` từ phần YAML Frontmatter của các tệp `SKILL.md`.
   - Bơm danh sách các cặp `[name: description, path]` vào System Prompt của Agent. Toàn bộ phần nội dung Body bên dưới **chưa hề được đưa vào context**.
2. **Giai đoạn đối khớp và đọc hướng dẫn (Match & Read Phase):** 
   - Người dùng gửi một câu lệnh hoặc câu hỏi.
   - LLM đọc System Prompt, đối chiếu yêu cầu của người dùng với danh sách `description` của các Skills.
   - Nếu phát hiện Skill phù hợp, LLM sẽ chủ động phát lệnh gọi công cụ hệ thống tệp tin: `read_file(path="/skills/<skill-name>/SKILL.md")`.
   - Nội dung chi tiết của `SKILL.md` được trả về qua Tool Output và chính thức đi vào Context Window của lượt hội thoại hiện tại.
3. **Giai đoạn thực thi (Execution Phase):** 
   - Agent thực hiện từng bước chỉ dẫn vừa đọc được.
   - Nếu trong `SKILL.md` có chỉ dẫn: *"Hãy tham khảo cấu trúc lỗi tại `references/error-codes.md` hoặc chạy script `scripts/fetch.py`"*, Agent sẽ tiếp tục phát sinh các lệnh gọi công cụ đọc file hoặc thực thi script tương ứng. Giai đoạn này do LLM tự do điều phối, middleware không can thiệp.

---

### Minh Họa Quy Trình Đối Khớp Thực Tế

![Progressive Disclosure: Khởi động chỉ nạp metadata, Agent đánh giá sự phù hợp rồi mới đọc SKILL.md](https://datawhalechina.github.io/deepagents-in-action/imgs/21-flowchart-progressive-disclosure.png)

> ℹ️ *Ghi chú về sơ đồ:* Cụm từ "chỉ đọc frontmatter" biểu thị rằng trong bộ nhớ ngữ cảnh của mô hình LLM chỉ chứa metadata. Ở bước khởi động ban đầu, middleware của hệ thống vẫn phải mở file trên đĩa để bóc tách thông tin frontmatter này.

**Kịch bản diễn giải thực tế:**

```text
1. Người dùng gửi lệnh:
   "Hãy giải thích giúp tôi cơ chế interrupt trong LangGraph hoạt động như thế nào?"

2. Luồng suy luận của Agent (LLM Thinking):
   - Đang có danh sách các Skills khả dụng: [code-review, langgraph-docs, db-migrate]
   - So sánh câu hỏi: "LangGraph interrupt"
   - Khớp với description của langgraph-docs: "Use this skill for requests related to LangGraph..."
   - Quyết định: Cần tham khảo quy trình tra cứu tài liệu LangGraph chuẩn!

3. Hành động công cụ:
   Agent gọi -> read_file(path="/skills/langgraph-docs/SKILL.md")

4. Agent nhận được nội dung hướng dẫn:
   - Bước 1: Đọc chỉ mục qua fetch_url("https://docs.langchain.com/llms.txt")
   - Bước 2: Tìm URL về interrupt
   - Bước 3: Đọc tài liệu chi tiết và tổng hợp câu trả lời cho người dùng.

5. Agent tuần tự thực thi theo đúng kịch bản nghiệp vụ.
```

---

### Tại Sao Phải Thiết Kế Theo Hướng Progressive Disclosure?

Thiết kế này mang lại 3 ưu thế vượt trội:

1. **Tiết kiệm Token vượt bậc (Massive Token Savings):** 
   Nếu bạn có 30 Skills, mỗi Skill dài 2.000 từ (~3.000 tokens): việc nhồi toàn bộ vào System Prompt sẽ tiêu tốn ngay lập tức **90.000 tokens** cho mỗi lượt gọi, khiến chi phí tăng vọt và làm chậm tốc độ phản hồi. Với Progressive Disclosure, 30 Skills chỉ tiêu tốn khoảng **500 - 800 tokens** cho danh sách description ban đầu.
2. **Loại bỏ hiện tượng loãng chú ý (Attention Dilution & Interference):** 
   Khi System Prompt quá dài với hàng chục bộ quy tắc không liên quan, mô hình LLM dễ gặp hiện tượng "Lost in the middle" hoặc bị phân tâm bởi các quy tắc xung đột nhau. Chỉ nạp nội dung của Skill thực sự cần thiết giúp Agent tập trung 100% năng lực vào nhiệm vụ hiện tại.
3. **Khả năng mở rộng không giới hạn (Infinite Scalability):** 
   Số lượng Skills của dự án có thể tăng từ 5 lên 50 hay 100 gói năng lực mà không làm sụp đổ giới hạn Context Window của mô hình. Chi phí khởi động chỉ tăng tuyến tính rất nhỏ theo số lượng dòng description.

---

## Các Phương Thức Lưu Trữ Và Nạp Skills (Storage Backends)

Cách thức nạp Skills phụ thuộc vào **Backend** hệ thống tệp tin mà bạn thiết lập cho Deep Agents. Thư viện cung cấp 3 loại Backend chính, phù hợp với từng môi trường triển khai thực tế.

![3 loại Storage Backend cho Skills: Filesystem, State, Store](https://datawhalechina.github.io/deepagents-in-action/imgs/22-arch-skills-backends.png)

---

### 1. Cơ Bản Nhất: `FilesystemBackend` (Đọc trực tiếp từ đĩa cứng)

`FilesystemBackend` đọc trực tiếp các thư mục và tệp tin Skill từ hệ thống tệp tin cục bộ của máy chủ. Đây là phương thức lý tưởng nhất cho quá trình phát triển cục bộ (Local Development) và các ứng dụng CLI:

```python
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

# Khởi tạo backend trỏ tới thư mục gốc của dự án
backend = FilesystemBackend(root_dir="./my-project", virtual_mode=True)

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    backend=backend,
    skills=["/skills/"],  # Đường dẫn ảo tới thư mục chứa các Skills con
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What is LangGraph?"}]},
    config={"configurable": {"thread_id": "1"}},
)
```

> 🔍 **Những điểm mấu chốt cần lưu ý:**
> - Tham số `skills` nhận một **danh sách các đường dẫn** (list of paths). Mỗi đường dẫn phải trỏ tới thư mục cha chứa các thư mục Skill con.
> - Ví dụ: Khai báo `skills=["/skills/"]` tương ứng với việc hệ thống sẽ quét các thư mục con như `/skills/langgraph-docs/SKILL.md`. Tuyệt đối không truyền đường dẫn file trực tiếp như `skills=["/skills/myskill.md"]` vì không đúng quy ước đóng gói thư mục.
> - Đường dẫn dùng dấu gạch chéo xuôi (`/`), mang tính tương đối so với `root_dir` của Backend. Trong ví dụ trên, `/skills/` tương ứng với thư mục vật lý `./my-project/skills/`.
> - Tham số `virtual_mode=True` giúp kích hoạt tính năng **Path Sandboxing** (chroot ảo) — ngăn chặn Agent truy cập trái phép ra ngoài phạm vi thư mục dự án được chỉ định.
> - Khi nhiều đường dẫn chứa Skill trùng tên, quy tắc **phần tử đứng sau ghi đè phần tử đứng trước (Last Wins)** sẽ được áp dụng.

---

### 2. `StateBackend`: Bơm Skills Trực Tiếp Qua Agent State

`StateBackend` không sử dụng đĩa cứng vật lý mà lưu trữ toàn bộ cây thư mục ảo ngay bên trong **State** của LangGraph. Phương thức này cực kỳ phù hợp cho môi trường **Serverless (AWS Lambda, Cloud Run)** hoặc các tình huống cần tải động nội dung Skill từ API/URL bên ngoài vào phiên chạy:

```python
from urllib.request import urlopen
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.backends.utils import create_file_data
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
backend = StateBackend()

# Tải nội dung Skill từ một URL từ xa (hoặc lấy từ Database/S3)
skill_url = "https://raw.githubusercontent.com/langchain-ai/deepagents/refs/heads/main/libs/code/examples/skills/langgraph-docs/SKILL.md"
with urlopen(skill_url) as response:
    skill_content = response.read().decode('utf-8')

# Bắt buộc phải đóng gói qua create_file_data
skills_files = {
    "/skills/langgraph-docs/SKILL.md": create_file_data(skill_content),
}

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    backend=backend,
    skills=["/skills/"],
    checkpointer=checkpointer,
)

# Nạp file thông qua trường 'files' trong payload invoke
result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "What is langgraph?"}],
        "files": skills_files,  # Bơm cây file ảo vào State của Agent
    },
    config={"configurable": {"thread_id": "12345"}},
)
```

> ⚠️ **LƯU Ý KỸ THUẬT VỀ `create_file_data()`:**
> - `StateBackend` lưu trữ file dưới dạng cấu trúc dữ liệu nội bộ (chứa metadata thời gian tạo, quyền hạn, v.v.). Do đó, bạn **bắt buộc** phải dùng hàm tiện ích `create_file_data(skill_content)` để chuẩn hóa dữ liệu. Nếu bạn truyền trực tiếp một chuỗi ký tự (raw string) vào `files`, hệ thống sẽ ném lỗi kiểm tra kiểu dữ liệu (Schema Validation Error).
> - Đường dẫn ảo bắt buộc phải bắt đầu bằng dấu gạch chéo `/` (định dạng đường dẫn tuyệt đối).
> - Do lưu trong State, nếu bạn không dùng bộ lưu trữ bền vững (Checkpointer), các file này sẽ chỉ tồn tại trong vòng đời của phiên thực thi đó. Mỗi lần gọi `agent.invoke` ở một thread mới, bạn cần truyền lại dữ liệu qua tham số `files`.

---

### 3. `StoreBackend`: Lưu Trữ Bền Vững Đa Luồng (Cross-Thread Persistence)

Khác với `StateBackend` chỉ nằm trong phạm vi State của một Thread, `StoreBackend` tận dụng cơ chế **LangGraph Store** để lưu trữ lâu dài. Ưu điểm nổi bật nhất: **Bạn chỉ cần ghi file Skill vào Store một lần duy nhất, tất cả các Thread, phiên chat và người dùng đều có thể truy cập được.**

```python
from urllib.request import urlopen
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

# Khởi tạo Store (trong thực tế có thể là PostgresStore, RedisStore...)
store = InMemoryStore()

# Cấu hình namespace lưu trữ tệp tin
backend = StoreBackend(namespace=lambda _rt: ("filesystem",))

# Tải nội dung Skill từ xa
skill_url = "https://raw.githubusercontent.com/langchain-ai/deepagents/refs/heads/main/libs/code/examples/skills/langgraph-docs/SKILL.md"
with urlopen(skill_url) as response:
    skill_content = response.read().decode('utf-8')

# Ghi tệp tin vào Store MỘT LẦN DUY NHẤT
store.put(
    namespace=("filesystem",),
    key="/skills/langgraph-docs/SKILL.md",
    value=create_file_data(skill_content),
)

# Khởi tạo Agent kết nối với Store
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    backend=backend,
    store=store,
    skills=["/skills/"],
)

# Các lần invoke sau không cần truyền lại tham số 'files' nữa!
result = agent.invoke(
    {"messages": [{"role": "user", "content": "What is langgraph?"}]},
    config={"configurable": {"thread_id": "12345"}},
)
```

> 💡 **So sánh nhanh giữa StateBackend và StoreBackend:**
> - `StateBackend`: Thích hợp cho dữ liệu tạm thời, ngắn hạn, hoặc khi mỗi request có một tập Skills hoàn toàn khác biệt do phía client gửi lên.
> - `StoreBackend`: Thích hợp cho môi trường Production đa người dùng, lưu trữ thư viện tri thức chung của hệ thống, giúp giảm thiểu overhead nạp dữ liệu qua mạng trong mỗi lượt gọi API.

---

### Đa Nguồn Skills Và Quy Tắc Ưu Tiên (Multi-source Skills & Priority)

Deep Agents cho phép bạn cấu hình nạp Skills từ nhiều thư mục nguồn khác nhau. Khi phát hiện các Skill bị trùng tên giữa các nguồn, cơ chế **Last Wins (Phần tử khai báo sau cùng sẽ chiếm quyền ưu tiên cao nhất)** sẽ được áp dụng:

```python
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    skills=[
        "/skills/shared/",    # Thư viện Skills chung của toàn công ty
        "/skills/project/",   # Skills chuyên biệt của dự án hiện tại (ưu tiên cao hơn)
    ],
)
```

Kiến trúc này mở đường cho chiến lược phân tầng tri thức rõ ràng trong doanh nghiệp:

| Tầng quản trị | Đường dẫn gợi ý | Nội dung & Phạm vi |
|---|---|---|
| **Cấp Tổ chức (Organization)** | `/skills/org/` | Quy chuẩn bảo mật, tuân thủ pháp lý, văn hóa doanh nghiệp chung |
| **Cấp Đội ngũ (Team)** | `/skills/team/` | Quy trình Agile, tiêu chuẩn Code Review của team, hướng dẫn CI/CD |
| **Cấp Dự án (Project)** | `/skills/project/` | Kiến trúc module đặc thù, kịch bản test riêng, cấu hình deployment cụ thể |

> *Ví dụ:* Nếu `/skills/shared/` đã có Skill `code-review`, nhưng team dự án muốn siết chặt thêm các quy tắc riêng bằng cách tạo thêm một Skill `code-review` đặt trong `/skills/project/`, thì phiên bản trong `/skills/project/` sẽ tự động ghi đè và có hiệu lực.

---

### Nạp Động Skills Trong Runtime (Dynamic Loading)

Do tham số `skills` nhận vào một danh sách Python thuần túy, bạn hoàn toàn có thể sinh danh sách này một cách linh hoạt tại thời điểm chạy ứng dụng dựa trên vai trò của người dùng (RBAC), cấu hình tenant của khách hàng SaaS hoặc loại yêu cầu:

```python
from deepagents import create_deep_agent

# Ma trận phân quyền Skills theo vai trò người dùng
SKILLS_BY_ROLE = {
    "engineering": ["/skills/code-review/", "/skills/testing/", "/skills/deployment/"],
    "data": ["/skills/sql-analysis/", "/skills/visualization/", "/skills/data-pipeline/"],
    "support": ["/skills/ticket-triage/", "/skills/runbook/"],
}

def create_agent_for_user(user_role: str):
    """Khởi tạo Agent với bộ Skills được may đo chính xác cho từng đối tượng."""
    return create_deep_agent(
        model="anthropic:claude-sonnet-4-6",
        skills=SKILLS_BY_ROLE.get(user_role, []),
    )
```

**Các mẫu hình nạp động phổ biến:**
- **Dựa trên Role của người dùng:** Lập trình viên chỉ tiếp cận các Skill về code; chuyên viên dữ liệu chỉ thấy các Skill về SQL và Dashboard.
- **Dựa trên gói dịch vụ (Multi-tenant SaaS):** Khách hàng gói Enterprise được mở khóa thêm các Skill phân tích chuyên sâu nâng cao.
- **Dựa trên môi trường:** Môi trường `staging` nạp thêm các Skill debug và dump log; môi trường `production` chỉ nạp các Skill vận hành an toàn.

---

## Skills Và Sub-Agents (Kế Thừa Năng Lực)

![Quy tắc kế thừa Skills giữa Main Agent và các Sub-Agent](https://datawhalechina.github.io/deepagents-in-action/imgs/24-arch-skills-subagent.png)

Khi xây dựng hệ thống đa tác tử (Multi-Agent Systems), việc phân chia Skills giữa **Main Agent** và các **Sub-Agent** tuân thủ các quy tắc tường minh sau:

1. **Sub-Agent Đa Năng (General-Purpose Subagent):** Tự động kế thừa toàn bộ danh sách Skills của Main Agent mà không cần khai báo thêm bất kỳ cấu hình nào.
2. **Sub-Agent Tùy Biến (Custom Subagent):** **Mặc định KHÔNG kế thừa** bất kỳ Skill nào từ Main Agent. Muốn cấp quyền cho Sub-Agent này, bạn phải khai báo tường minh qua tham số `skills` trong cấu hình của nó.
3. **Cách ly trạng thái tuyệt đối (Complete State Isolation):** Mỗi Agent sở hữu một không gian trạng thái file hoàn toàn độc lập. Mọi hành vi sửa đổi, tạo mới hay xóa file Skill của Agent này sẽ không làm biến dạng môi trường của Agent khác.

```python
from deepagents import create_deep_agent

# Định nghĩa một Custom Sub-Agent chuyên trách nghiên cứu
research_subagent = {
    "name": "researcher",
    "description": "Research assistant with specialized skills",
    "system_prompt": "You are a researcher specialized in academic information synthesis.",
    "tools": [web_search],
    # Sub-Agent này chỉ được tiếp cận 2 bộ Skills chuyên biệt sau:
    "skills": ["/skills/research/", "/skills/web-search/"],
}

# Main Agent điều phối
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    skills=["/skills/main/"],       # Dành cho Main Agent và các General-purpose Subagent
    subagents=[research_subagent],   # researcher chỉ sở hữu bộ Skills riêng của nó
)
```

> 💡 **Ý nghĩa kiến trúc:**
> Thiết kế này đảm bảo nguyên lý **Trách nhiệm đơn lẻ (Single Responsibility Principle)**: Một Agent chuyên viết báo cáo không nên và không cần biết đến các Skill liên quan đến triển khai hạ tầng k8s của Main Agent. Sự cách ly này cũng loại bỏ hoàn toàn các lỗi xung đột tài nguyên (race condition) khi nhiều Agent chạy ngầm đồng thời.

---

## Quản Trị Quyền Hạn Đối Với Skills (Skill Permissions)

![Cơ chế kiểm soát quyền hạn: Phân tầng Shared và Personal Skills](https://datawhalechina.github.io/deepagents-in-action/imgs/23-arch-skills-permissions.png)

Trong môi trường triển khai doanh nghiệp, việc bảo vệ tính toàn vẹn của thư viện Skills đòi hỏi phải quản trị chặt chẽ theo 3 khía cạnh:
1. **Khả năng nhìn thấy (Visibility):** Agent có quyền phát hiện và đọc tệp tin Skill hay không.
2. **Quyền ghi (Write Access):** Agent có được phép tự ý sửa đổi hoặc ghi đè nội dung tệp `SKILL.md` hay không.
3. **Quy trình phê duyệt (Approval):** Các thao tác sửa đổi có bắt buộc phải qua sự đồng thuận của con người (Human-in-the-loop) hay không.

---

### 1. Kịch Bản Chỉ Đọc (Read-only Skills — Kho Tri Thức Doanh Nghiệp)

Trong hầu hết các doanh nghiệp, thư viện Skill do đội ngũ chuyên gia kiểm duyệt chặt chẽ trước khi ban hành. Agent chỉ được phép học và làm theo, **tuyệt đối không được tự ý sửa đổi**.

Để hiện thực hóa điều này, ta sử dụng `FilesystemPermission` kết hợp với `CompositeBackend`:

```python
from dataclasses import dataclass
from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

@dataclass(frozen=True)
class TenantContext:
    org_id: str

def org_skill_namespace(rt):
    org_id = getattr(rt.context, "org_id", "default-org")
    return ("curated-skills", org_id)

store = InMemoryStore()
# Lưu ý về key trong Store: xem giải thích chi tiết bên dưới
store.put(
    namespace=("curated-skills", "org-acme"),
    key="/test-skill/SKILL.md",
    value=create_file_data("""---
name: test-skill
description: Kỹ năng chuẩn hóa dùng để xác thực khả năng đọc tri thức doanh nghiệp.
---

# test-skill
Quy trình chuẩn...
"""),
)

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    context_schema=TenantContext,
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            # Định tuyến đường dẫn /skills/ sang StoreBackend
            "/skills/": StoreBackend(namespace=org_skill_namespace),
        },
    ),
    skills=["/skills/"],
    permissions=[
        # CHẶN TOÀN BỘ THAO TÁC GHI VÀO /skills/**
        FilesystemPermission(
            operations=["write"],
            paths=["/skills/**"],
            mode="deny",
        ),
    ],
    store=store,
)
```

> ⚠️ **LƯU Ý KỸ THUẬT CỰC KỲ QUAN TRỌNG VỀ PATH STRIPPING TRONG `CompositeBackend`:**
> 
> Bạn cần phân biệt rõ ràng giữa **Đường dẫn nhìn thấy bởi Agent (Agent-visible path)** và **Đường dẫn lưu trữ nội bộ (Store-internal key)**:
> - Khi Agent truy cập `/skills/test-skill/SKILL.md`, `CompositeBackend` nhận diện tiền tố khớp với route `"/skills/"`.
> - `CompositeBackend` sẽ **tước bỏ tiền tố này (strip mount prefix)** và chuyển đường dẫn còn lại là `/test-skill/SKILL.md` cho `StoreBackend` bên trong xử lý.
> - **Hệ quả khi ghi trước dữ liệu:** Khi dùng lệnh `store.put()`, bạn **phải** đặt key là `/test-skill/SKILL.md`. Nếu bạn nhầm lẫn đặt là `/skills/test-skill/SKILL.md`, khi lớp vỏ bọc bên ngoài gắn lại tiền tố, đường dẫn thực tế sẽ bị biến thành `/skills/skills/test-skill/SKILL.md` và Agent sẽ gặp lỗi 404 không tìm thấy file!
> - *(Chỉ khi bạn dùng trực tiếp `StoreBackend` làm backend gốc mà không bọc qua `CompositeBackend`, key trong Store mới giữ nguyên tiền tố `/skills/...`)*.

**Cơ chế hoạt động của `mode="deny"`:**
Agent vẫn đọc và tìm kiếm các Skill bình thường, nhưng nếu cố tình gọi các công cụ sửa đổi như `write_file`, `edit_file` hay lệnh `delete` (trong bản v0.7+), hệ thống tệp tin ảo sẽ chặn đứng hành động này ngay lập tức và trả về thông báo lỗi: `PermissionDeniedError: Write operation denied on /skills/...`.

---

### 2. Kịch Bản Ghi Cần Phê Duyệt (`mode="interrupt"` — Human-in-the-loop)

Trong một số tình huống, bạn muốn Agent tự do đề xuất cải tiến nội dung của Skill sau quá trình học hỏi từ người dùng, nhưng **chỉ được phép lưu lại khi có sự kiểm duyệt và đồng ý của con người**:

```python
from deepagents import FilesystemPermission, create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    skills=["/skills/personal/"],
    permissions=[
        FilesystemPermission(
            operations=["write"],
            paths=["/skills/**"],
            mode="interrupt",  # Khi Agent ghi file, luồng thực thi sẽ tạm dừng để chờ phê duyệt!
        ),
    ],
    checkpointer=MemorySaver(),  # Bắt buộc phải có Checkpointer để lưu snapshot tiến trình
)
```

> 🔍 **Cơ chế vận hành của chế độ `interrupt`:**
> 1. Khi Agent phát sinh hành động ghi vào `/skills/**`, LangGraph sẽ **ngắt luồng thực thi (suspend/interrupt)** ngay trước khi tệp tin bị thay đổi.
> 2. Toàn bộ nội dung thay đổi (diff) sẽ được hiển thị ra giao diện cho người quản trị xem xét (ví dụ: giao diện LangGraph Studio UI).
> 3. Nếu con người bấm **Phê duyệt (Approve)**, tiến trình được đánh thức và ghi file thành công.
> 4. Nếu con người bấm **Từ chối (Reject)**, thao tác bị hủy bỏ và Agent sẽ nhận được phản hồi để điều chỉnh lại chiến lược.
> 
> *Yêu cầu kỹ thuật:* Tính năng này có từ `deepagents>=0.6.8` và bắt buộc phải gắn `checkpointer` (như `MemorySaver` hoặc `PostgresSaver`) để phục hồi trạng thái biểu đồ sau khi ngắt.

---

### 3. Mô Hình Kết Hợp: Thư Viện Doanh Nghiệp (Shared) + Không Gian Cá Nhân (Personal)

Đây là mô hình kiến trúc phổ biến và hoàn thiện nhất trong các ứng dụng Agent doanh nghiệp:
- **Shared Skills:** Dùng chung cho toàn công ty, được lưu trữ tập trung, cấp quyền **Read-Only (deny)**.
- **Personal Skills:** Dành riêng cho từng cá nhân người dùng, có quyền ghi tự do để Agent tự thích nghi và cá nhân hóa theo phong cách của chủ sở hữu.

```python
from dataclasses import dataclass
from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

@dataclass(frozen=True)
class TenantContext:
    org_id: str
    user_id: str

def shared_skill_namespace(rt):
    org_id = getattr(rt.context, "org_id", "default-org")
    return ("curated-skills", org_id)

def personal_skill_namespace(rt):
    # Nếu chạy qua LangGraph Server có xác thực danh tính
    if rt.server_info and rt.server_info.user:
        return ("user-skills", rt.server_info.user.identity)
    # Nếu chạy cục bộ qua context
    user_id = getattr(rt.context, "user_id", "local-user")
    return ("user-skills", user_id)

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    context_schema=TenantContext,
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/skills/shared/": StoreBackend(namespace=shared_skill_namespace),
            "/skills/personal/": StoreBackend(namespace=personal_skill_namespace),
        },
    ),
    skills=[
        "/skills/shared/",    # Khai báo trước: Ưu tiên thấp hơn
        "/skills/personal/",  # Khai báo sau: Chiếm ưu tiên cao hơn (Override)
    ],
    permissions=[
        # Khóa cứng không cho sửa đổi thư viện dùng chung
        FilesystemPermission(
            operations=["write"],
            paths=["/skills/shared/**"],
            mode="deny",
        ),
        # Thư mục /skills/personal/** không bị cấm nên Agent được tự do ghi!
    ],
)
```

> 💡 **Quy tắc ghi đè cá nhân hóa (Last-wins personalization):**
> Trong cấu hình trên, `/skills/personal/` được đặt sau `/skills/shared/` trong mảng `skills`. Do đó, nếu người dùng tạo một bản sao Skill trùng tên trong không gian cá nhân của mình để tùy biến thêm vài bước, phiên bản cá nhân sẽ tự động ghi đè lên phiên bản chung của công ty mà hoàn toàn không ảnh hưởng đến các đồng nghiệp khác.

---

## Thực Thi Mã Nguồn Thông Qua Skills (Code Execution)

![Hai phương thức thực thi mã với Skills: Sandbox Scripts vs Interpreter Skills](https://datawhalechina.github.io/deepagents-in-action/imgs/25-arch-skills-code-execution.png)

Skills không chỉ dừng lại ở các tài liệu hướng dẫn bằng văn bản thuần túy, mà còn có khả năng mang theo **mã nguồn thực thi**. Deep Agents hỗ trợ hai mô hình thực thi mã mạnh mẽ:

---

### Mô Hình 1: Sandbox Scripts (Chạy Script Trong Môi Trường Cách Ly)

Một Skill có thể chứa các script tự động hóa viết bằng Python, Bash, Shell... nằm trong thư mục con `scripts/`. Agent có thể đọc nội dung script từ bất kỳ Backend nào, nhưng để **chạy** chúng, hệ thống cần một Backend hỗ trợ thực thi cách ly an toàn (ví dụ: `DaytonaSandbox`).

**Cấu trúc thư mục:**
```text
skills/
└── arxiv-search/
    ├── SKILL.md
    └── scripts/
        └── search.py
```

**Nội dung `SKILL.md`:**
```markdown
---
name: arxiv-search
description: Search the arXiv preprint repository for research papers. Use when the user asks about academic papers, recent research, or scientific literature.
---

# arxiv-search

Search arXiv for papers matching the user's query.

## Instructions

1. Run `scripts/search.py` with the user's query as an argument.
2. Parse the results and present them with title, authors, abstract summary, and link.
3. If the user asks for more detail on a specific paper, fetch the full abstract.
```

**Cơ chế vận hành:**
- Backend Sandbox (như Docker hoặc Daytona) khởi chạy một container riêng biệt. Agent phát lệnh chạy script và đọc kết quả trả về từ `stdout`.
- Nếu file Skill được lưu ở bên ngoài Sandbox (ví dụ trên `StateBackend`), middleware tùy chỉnh sẽ tự động đồng bộ:
  - Hook `before_agent`: Tải trước các script từ bộ nhớ lên môi trường Sandbox.
  - Hook `after_agent`: Thu thập các tệp tin kết quả được sinh ra trong container lưu ngược lại.

---

### Mô Hình 2: Interpreter Skills (Nhúng Năng Lực Trực Tiếp Vào REPL)

Mô hình này cho phép Agent `import` trực tiếp các hàm tiện ích đã được kiểm thử nghiêm ngặt vào môi trường Code Interpreter của nó, thay vì bắt Agent phải tự sinh lại mã nguồn từ đầu mỗi khi cần tính toán:

> ⚠️ **Điều kiện tiên quyết:**
> Interpreter Skills yêu cầu cài đặt gói mở rộng QuickJS: `pip install -U "deepagents[quickjs]"` hoặc `uv add "deepagents[quickjs]"`. Đòi hỏi `langchain-quickjs>=0.2.0` và môi trường Python `>=3.11`. Trình thông dịch chạy trong môi trường bộ nhớ của QuickJS, cực kỳ thích hợp cho các hàm tiện ích JavaScript/TypeScript mang tính tất định (deterministic).

**3 bước thiết lập một Interpreter Skill:**
1. Khai báo tệp tin đầu vào trong frontmatter qua trường `metadata.entrypoint` (chỉ định file JS/TS).
2. Cấu hình `CodeInterpreterMiddleware` trỏ cùng backend chứa Skills.
3. Agent thực hiện `await import("@/skills/<skill-name>")` ngay trong khối code thực thi.

**Cấu trúc thư mục:**
```text
skills/
└── order-helpers/
    ├── SKILL.md
    └── scripts/
        └── index.ts
```

**Tệp `SKILL.md`:**
````markdown
---
name: order-helpers
description: Helper functions for normalizing and grouping order records.
metadata:
  entrypoint: scripts/index.ts
---

# order-helpers

Use this skill when order records need deterministic cleanup or aggregation.

Import these utilities into the REPL:

```typescript
const { groupByStatus } = await import("@/skills/order-helpers");
groupByStatus(...);
```
````

**Triển khai logic TypeScript (`scripts/index.ts`):**
```typescript
interface Order {
  id: string;
  status: string;
}

export function groupByStatus(orders: Order[]) {
  return orders.reduce((acc, order) => {
    acc[order.status] = acc[order.status] ?? [];
    acc[order.status].push(order);
    return acc;
  }, {});
}
```

**Cấu hình Agent trong Python:**
```python
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from langchain_quickjs import CodeInterpreterMiddleware

backend = StateBackend()

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    backend=backend,
    skills=["/skills/"],
    middleware=[CodeInterpreterMiddleware(skills_backend=backend)],
)
```

> 💡 **Ưu thế vượt trội của Interpreter Skills:**
> - **Tính tất định 100% (Determinism):** Các hàm toán học, gom cụm dữ liệu, xử lý chuỗi phức tạp được viết bằng code chuẩn và unit test đầy đủ sẽ loại bỏ hoàn toàn hiện tượng "ảo giác" (hallucination) thường thấy khi bắt LLM tự suy luận mã.
> - **Tiết kiệm Token khổng lồ:** Thay vì để Agent viết ra 50 dòng thuật toán phức tạp trong mỗi lượt phản hồi, Agent chỉ cần viết 1 dòng lệnh `import` và gọi hàm.

---

## Bảng So Sánh Toàn Diện: Skills vs. Memory vs. Tools

Trong Deep Agents, có 3 cơ chế chính để trang bị năng lực cho Agent. Mỗi cơ chế phục vụ một mục đích chuyên biệt trong kiến trúc tổng thể:

| Tiêu chí | Skills | Memory (`AGENTS.md`) | Tools (Công cụ) |
|---|---|---|---|
| **Bản chất cốt lõi** | Quy trình nghiệp vụ & kiến thức chuyên sâu nạp theo nhu cầu (**Progressive Disclosure**) | Bối cảnh và quy chuẩn mang tính cố định, lâu dài | Các thao tác lập trình mang tính nguyên tử (Atomic Operations) |
| **Thời điểm nạp** | Chỉ nạp nội dung khi Agent nhận diện câu hỏi phù hợp | Nạp vào System Prompt ngay khi khởi động Agent | Luôn sẵn sàng cho Agent gọi ở mọi lượt chat |
| **Định dạng cấu hình** | Thư mục chuẩn hóa có tệp `SKILL.md` | Tệp tin `AGENTS.md` | Các hàm Python (decorated functions) gán vào Agent |
| **Quy tắc giải quyết xung đột** | Phần tử đứng sau ghi đè (`Last Wins`) | Gộp nội dung (Merge giữa cấp người dùng và cấp dự án) | Định nghĩa trực tiếp khi khởi tạo Agent |
| **Kịch bản phù hợp nhất** | Tập chỉ dẫn quy trình dài, phức tạp của từng bài toán cụ thể | Các quy ước chung của dự án, ngôn ngữ giao tiếp ưa thích, vai trò Agent | Khi Agent cần tương tác với thế giới bên ngoài (gọi API, truy vấn DB, đọc ghi file) |

### Khung Tư Duy Lựa Chọn Nhanh (Mental Model)

Để dễ nhớ, bạn có thể hình dung:
- 🛠️ **Tools = Đôi bàn tay (Verbs):** Hành động thực thi tức thời (Tìm kiếm web, gửi email, truy vấn cơ sở dữ liệu).
- 🧠 **Memory (`AGENTS.md`) = Bản sắc & Thói quen:** Luôn ghi nhớ trong đầu (Tôi là trợ lý AI, luôn trả lời bằng tiếng Việt, code theo chuẩn PEP 8).
- 📚 **Skills = Sách hướng dẫn chuyên ngành (Playbooks):** Để trên giá sách, khi nào gặp đúng dự án hay bài toán khó mới lấy cuốn sách đó xuống đọc và làm theo từng bước.

> ℹ️ **Mối liên hệ liên tục giữa Skills và Memory:**
> Skills và Memory thực chất nằm trên một dải quang phổ liên tục (Continuum). Trong quá trình làm việc, Agent hoàn toàn có thể tự ghi chép hoặc cập nhật thêm các Skills mới vào thư mục của mình. Do đó, bạn có thể xem Skills chính là một dạng **Bộ nhớ dài hạn có khả năng nạp tiệm tiến (Progressive-disclosure Long-term Memory)**.

---

## Best Practices: Bí Quyết Xây Dựng Skills Đạt Hiệu Quả Cao

Dựa trên kinh nghiệm thực chiến và chuẩn đặc tả Agent Skills, dưới đây là 4 nguyên tắc vàng bạn nên tuân thủ:

### 1. Frontmatter Phải Ngắn Gọn Và Cực Kỳ Chuẩn Xác
Trường `description` trong Frontmatter là chiếc "chìa khóa" duy nhất để Agent quyết định có mở Skill hay không. Hãy mô tả chính xác **tín hiệu kích hoạt (Triggers)** và **kết quả đầu ra kỳ vọng**.
- ✅ **Nên viết:** `description: Sử dụng khi người dùng hỏi về định nghĩa Node, State Management, cơ chế Interrupt hoặc cấu hình Deployment trong LangGraph. Hướng dẫn tra cứu tài liệu mới nhất và cung cấp mã nguồn mẫu.`
- ❌ **Không nên viết:** `description: Hỗ trợ người dùng giải quyết các vấn đề lập trình.`

### 2. Giới Hạn Phần Thân `SKILL.md` Dưới 500 Dòng (~5.000 Tokens)
Nội dung của tệp `SKILL.md` chỉ nên tập trung vào khung quy trình xương sống (Core Workflow). Tất cả các bảng tra cứu chi tiết, danh sách mã lỗi, hướng dẫn API dài dòng nên được tách ra các file tài liệu con đặt trong thư mục `references/`:
```text
skills/
└── api-design/
    ├── SKILL.md              # Quy trình cốt lõi (< 500 dòng)
    └── references/
        ├── rest-conventions.md   # Chi tiết quy chuẩn REST
        └── error-codes.md        # Bảng tra cứu mã lỗi đầy đủ
```
Trong `SKILL.md`, bạn chỉ cần viết: *"Khi cần kiểm tra cấu trúc mã lỗi chi tiết, hãy đọc `references/error-codes.md`"*. Agent sẽ chỉ đọc file con đó khi thực sự cần.

### 3. Viết Cho Agent Đọc, Không Phải Cho Con Người
Agent tư duy và xử lý tốt nhất khi nhận được các chỉ dẫn dạng thuật toán và bước tuần tự. Hãy xây dựng tài liệu theo các yếu tố:
- **Các bước 1-2-3 rõ ràng:** Tránh viết các đoạn văn nghị luận dài dòng; hãy dùng danh sách gạch đầu dòng đánh số thứ tự.
- **Cây quyết định nhánh rẽ:** Nêu rõ các điều kiện logic (*"Nếu người dùng yêu cầu X thì thực hiện A; ngược lại nếu yêu cầu Y thì thực hiện B"*).
- **Ví dụ Input/Output mẫu:** Cung cấp định dạng dữ liệu đầu vào và cấu trúc Markdown đầu ra mong muốn.
- **Kịch bản xử lý sự cố (Edge Cases):** Nêu rõ Agent phải làm gì nếu API bị timeout hoặc không tìm thấy tài liệu.

### 4. Kiểm Soát Chặt Chẽ Số Lượng Skills (Chất Lượng Hơn Số Lượng)
Một tập hợp 10 Skills được định nghĩa sắc bén sẽ mang lại hiệu quả vượt trội so với một mớ hỗn độn 50 Skills mập mờ:
- Càng nhiều Skills với mô tả chồng chéo, Agent càng dễ rơi vào trạng thái bối rối, dẫn đến gọi nhầm Skill hoặc xung đột chỉ thị.
- Hãy định kỳ rà soát thư viện Skills: gộp các kỹ năng có điểm tương đồng, loại bỏ các kỹ năng lỗi thời và phân rã những kỹ năng quá đồ sộ.

---

## Tổng Kết

Trong chương này, chúng ta đã nắm bắt trọn vẹn sức mạnh của cơ chế **Skills** trong Deep Agents:

1. **Cấu trúc chuẩn hóa:** Một thư mục chứa `SKILL.md` kèm các tài nguyên tùy chọn (`scripts/`, `references/`, `assets/`), tương thích với chuẩn mở quốc tế **Agent Skills Specification**.
2. **Cơ chế nạp 3 tầng (Progressive Disclosure):** Khởi động nhẹ nhàng với Metadata $\rightarrow$ Đọc chỉ dẫn chi tiết khi khớp nhu cầu $\rightarrow$ Đào sâu tài nguyên khi có lệnh. Giúp tiết kiệm tối đa token và triệt tiêu hiện tượng loãng chú ý.
3. **Linh hoạt Backend:** Lựa chọn giữa `FilesystemBackend` (cục bộ), `StateBackend` (serverless/động qua API) và `StoreBackend` (chia sẻ bền vững đa luồng).
4. **Quy tắc kế thừa đa tác tử:** Sub-Agent đa năng tự động kế thừa; Custom Sub-Agent được cô lập hoàn toàn nhằm đảm bảo tính toàn vẹn trạng thái.
5. **Bảo mật & Phân quyền:** Hỗ trợ chặn cứng (`mode="deny"`) cho tri thức dùng chung và kiểm duyệt con người (`mode="interrupt"`) cho các thao tác nhạy cảm.
6. **Thực thi mã nguồn:** Tự động hóa qua Sandbox Scripts và tối ưu hóa tính tất định bằng Interpreter Skills nhúng QuickJS.
7. **Định vị rõ ràng:** Tools là thao tác nguyên tử; Memory là bối cảnh cố định; Skills là quy trình nghiệp vụ nạp theo nhu cầu.

Ở chương tiếp theo, chúng ta sẽ bước sang một cấu phần quan trọng khác trong việc xây dựng Agent thông minh: **Long-term Memory (Bộ Nhớ Dài Hạn)** — giúp Agent ghi nhớ và duy trì kiến thức xuyên suốt qua nhiều phiên làm việc và cuộc hội thoại khác nhau.
