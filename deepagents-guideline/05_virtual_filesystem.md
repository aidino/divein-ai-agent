# Chương 3: Hệ Thống Tập Tin Ảo (Virtual File System) — Trọng Tâm Context Engineering Của Deep Agents

> Ở chương trước, chúng ta đã chạy thử Deep Agent đầu tiên. Chương này sẽ đi sâu vào đổi mới cốt lõi nhất của Deep Agents — **Hệ thống tập tin ảo (Virtual File System - VFS)**. Hiểu được cơ chế này, bạn sẽ nắm được triết lý thiết kế cơ bản giúp Deep Agents khác biệt hoàn toàn so với các Agent framework truyền thống khác.

---

## Tại sao lại dùng "Hệ thống tập tin" để quản lý Context?

Trong Chương 1, chúng ta đã đề cập rằng quy trình phát triển Agent truyền thống mắc phải một tử huyệt nghiêm trọng: **Mọi thông tin đều bị nhồi nhét trực tiếp vào prompt**. Toàn bộ nội dung file, kết quả tìm kiếm web, các bước tính toán trung gian — tất cả chen chúc trong một lịch sử hội thoại (conversation history) ngày càng phình to không kiểm soát.

> 💡 **Giải thích thêm (Vấn đề của việc nhồi nhét Context):**
> Khi context phình to, hệ thống gặp phải 3 vấn đề lớn:
> 1. **Context Window Exhaustion:** Vượt quá giới hạn token của LLM hoặc làm tăng chi phí API theo hàm mũ.
> 2. **Lost in the Middle:** Các mô hình LLM thường chú ý tốt ở phần đầu và phần cuối context, nhưng dễ bị "quên" hoặc suy giảm khả năng suy luận đối với các thông tin nằm ở lưng chừng prompt dài.
> 3. **Distraction & Hallucination:** Quá nhiều dữ liệu rác (nhiễu) khiến LLM dễ bị phân tâm, dẫn đến hallucination (ảo tưởng) hoặc gọi sai tool.

Giải pháp mang tính đột phá của Deep Agents là: **Cung cấp cho Agent một hệ thống tập tin (File System)**.

Ý tưởng này thực chất rất trực quan và mô phỏng chính xác cách con người làm việc:

- Bạn không bao giờ mở tung tất cả tài liệu rồi trải la liệt trên mặt bàn cùng một lúc.
- Bạn sẽ **phân loại và lưu trữ tài liệu vào từng ngăn/thư mục**, khi nào cần đến mới lấy ra đọc.
- Bạn sử dụng công cụ **tìm kiếm (search)** để định vị nhanh phần nội dung cần thiết.
- Bạn ghi chú các kết quả trung gian vào **giấy ghi chú (scratchpad/notes)** thay vì cố ghi nhớ mọi thứ trong đầu.

Deep Agents cho phép Agent làm việc y như vậy. Framework cung cấp một bộ công cụ thao tác file hoàn chỉnh, giúp Agent có thể đọc dữ liệu theo nhu cầu (on-demand), lưu trữ có cấu trúc và tìm kiếm định vị chính xác như một kỹ sư thực thụ.

---

## Các Built-in Filesystem Tools (Công cụ tích hợp sẵn)

Deep Agents (từ bản v0.7) hiện cung cấp **7 built-in file tools**. Sơ đồ dưới đây minh họa 6 năng lực đọc, ghi và tìm kiếm cốt lõi ban đầu, phiên bản hiện tại đã bổ sung thêm công cụ `delete`:

| Tool | Công dụng | Tương tự trong thực tế |
|---|---|---|
| `ls` | Liệt kê các file trong thư mục kèm metadata (kích thước, thời gian sửa đổi) | Mở thư mục xem bên trong có gì |
| `read_file` | Đọc nội dung file, hỗ trợ phân trang theo offset và giới hạn số dòng (limit); hỗ trợ native đa phương thức (hình ảnh, video, audio, PDF/PPT) | Lật mở một tập tài liệu ra đọc |
| `write_file` | Tạo file mới, hoặc ghi đè toàn bộ (overwrite) file đã có | Viết một bản ghi nhớ mới hoặc viết lại toàn bộ bản thảo |
| `edit_file` | Thay thế chuỗi ký tự chính xác (exact string replacement) trên file có sẵn | Dùng bút đỏ sửa một đoạn văn bản |
| `delete` | Xóa file hoặc thư mục | Dọn dẹp tài liệu không còn dùng |
| `glob` | Tìm kiếm file theo pattern / mẫu khớp (ví dụ: `**/*.py`) | Tìm tài liệu trong tủ hồ sơ theo nhãn dán |
| `grep` | Tìm kiếm nội dung bên trong file theo chuỗi ký tự chính xác (literal match); hỗ trợ trích xuất nội dung hoặc đếm số lượng | Tra cứu từ khóa trong toàn bộ tài liệu (Full-text search) |

![Virtual File System: ls, read_file, write_file, edit_file, glob, grep](../public/imgs/07-infographic-six-tools.png)

> [!NOTE]
> **Lưu ý ở bản v0.7**: Hình vẽ trên vẫn giữ góc nhìn 6 công cụ ban đầu của khóa học. Phiên bản hiện tại đã bổ sung `delete`, và hành vi của `write_file` là **ghi đè hoàn toàn** (overwrite) file nếu đã tồn tại cùng đường dẫn. Khi chỉ muốn sửa đổi cục bộ một vài dòng, Agent bắt buộc phải dùng `edit_file`.

Ở bản v0.7, ranh giới trả về của các thao tác đọc và tìm kiếm cũng được tinh chỉnh:
- `read_file` sẽ trả về thông tin phân trang (pagination) kèm offset của đoạn tiếp theo.
- `grep` và `glob` có thể trả về kết quả hợp lệ nhưng chưa đầy đủ, đồng thời đánh dấu `truncated=True` để báo hiệu kết quả đã bị cắt ngắn.
- `grep` (khi đối diện với Agent) mặc định giữ lại tối đa 1.000 kết quả khớp. Việc tool call trả về thành công chỉ chứng tỏ tool đã thực thi bình thường, **không đồng nghĩa với việc đã lấy hết toàn bộ dữ liệu**. Agent cần thu hẹp phạm vi thư mục hoặc bổ sung điều kiện tìm kiếm để truy vấn tiếp.

Nếu ứng dụng của bạn trực tiếp parse chuỗi text trả về từ tool, bạn cần cập nhật parser:
- Khi không có dữ liệu, `ls` / `glob` giờ đây trả về chuỗi `No files found`.
- Giữa số dòng và nội dung văn bản trong `read_file` hiện sử dụng **hai dấu cách** (`  `), không còn dùng ký tự Tab (`\t`).
- Cách tiếp cận an toàn và bền vững nhất là ưu tiên trích xuất kết quả có cấu trúc từ Backend, coi text trả về cho LLM chỉ là giao thức hiển thị (presentation protocol).

> 💡 **Mối quan hệ giữa Tool và Permission:**
> Tool quy định Agent **có khả năng làm được gì** (khả năng kỹ thuật). Còn luật phân quyền (permission rules) quyết định một hành động cụ thể **có được phép làm hay không**.
> Ví dụ: `write_file` và `edit_file` mặc định là thao tác file thông thường, nhưng thông qua `FilesystemPermission`, bạn có thể từ chối thẳng thừng các đường dẫn nhạy cảm (như `/etc/` hay file cấu hình production), hoặc tạm dừng luồng thực thi để đợi con người phê duyệt (Human-in-the-Loop approval). Quy trình gián đoạn (interrupt) và phục hồi (resume) chi tiết được trình bày tại [Chương 9: Filesystem Permission Interrupt](../ch09-human-in-the-loop/#文件系统权限中断).

---

### `read_file`: Không chỉ đơn thuần là "Đọc file"

`read_file` sở hữu hai đặc tính cực kỳ quan trọng giúp tối ưu hóa ngữ cảnh và mở rộng năng lực xử lý:

#### Đặc tính 1: Đọc phân đoạn (Chunking / Offset Reading)
Đối với các file dung lượng lớn (mã nguồn hàng nghìn dòng, log hệ thống), `read_file` cho phép đọc theo vị trí bắt đầu (`offset`) và số lượng dòng (`limit`), ngăn chặn việc vô tình đổ toàn bộ file dung lượng khủng vào context:

```python
# Mặc định đọc tối đa 100 dòng đầu tiên
read_file("/workspace/report.md")

# Bắt đầu đọc từ dòng 100, lấy tiếp 50 dòng
read_file("/workspace/report.md", offset=100, limit=50)
```

#### Đặc tính 2: Native Multimodal Support (Hỗ trợ đa phương thức nguyên bản)
`read_file` không chỉ xử lý text thuần túy — nó nhận diện và hỗ trợ nguyên bản nhiều định dạng đa phương tiện, trả về trực tiếp các khối nội dung đa phương thức (multimodal content blocks), giúp Agent có thể "nhìn thấy" ảnh, "nghe" âm thanh và "đọc hiểu" tài liệu phức tạp:

| Loại tệp | Các định dạng được hỗ trợ |
|---|---|
| **Hình ảnh** | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.heic`, `.heif` |
| **Video** | `.mp4`, `.mpeg`, `.mov`, `.avi`, `.flv`, `.mpg`, `.webm`, `.wmv`, `.3gpp` |
| **Âm thanh** | `.wav`, `.mp3`, `.aiff`, `.aac`, `.ogg`, `.flac` |
| **Tài liệu** | `.pdf`, `.ppt`, `.pptx` |

> 💡 **Giải thích thêm:**
> Thay vì chuyển đổi file PDF hay ảnh thành text qua OCR rời rạc bên ngoài làm mất cấu trúc không gian (layout), `read_file` đóng gói file thành dạng dữ liệu đa phương thức chuẩn mà các Vision-Language Models (như GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro) có thể tiếp nhận trực tiếp qua API. Điều này cho phép Agent phân tích biểu đồ, giao diện UI, slide thuyết trình hay biên bản họp âm thanh một cách tự nhiên.

---

### `grep`: Ba chế độ xuất kết quả (Output Modes)

`grep` là vũ khí lợi hại giúp Agent nhanh chóng định vị thông tin giữa hàng trăm tệp mã nguồn mà không cần duyệt từng file. Nó hỗ trợ 3 chế độ:

- **`files_with_matches`**: Chỉ trả về danh sách đường dẫn các file có chứa từ khóa (phù hợp để định vị nhanh phạm vi).
- **`content`**: Trả về chi tiết các dòng khớp từ khóa kèm ngữ cảnh xung quanh (phù hợp để đọc sâu và phân tích logic).
- **`count`**: Trả về tổng số lượng vị trí khớp (phù hợp để thống kê tổng quan, đếm tần suất xuất hiện).

```python
# Tìm tất cả các file Python có chứa chữ "TODO"
grep("TODO", glob="**/*.py", output_mode="files_with_matches")

# Xem chi tiết nội dung định nghĩa hàm
grep("def create_agent", output_mode="content")
```

---

## Tự Động Quản Lý Context: Không Chỉ Là Lưu File

Giá trị lớn nhất của Hệ thống tập tin ảo không chỉ dừng lại ở việc "chứa file", mà nằm ở sự phối hợp nhịp nhàng với **cơ chế tự động quản lý ngữ cảnh (Context Management)** của Deep Agents.

### 1. Tự động dọn dẹp kết quả lớn (Large Result Auto-Eviction)

Khi dữ liệu đầu vào hoặc kết quả đầu ra của một lần gọi tool vượt quá 20.000 tokens (ngưỡng này tùy biến được qua tham số `tool_token_limit_before_evict`), Deep Agents sẽ tự động kích hoạt chu trình:

1. Ghi toàn bộ nội dung khổng lồ đó **vào Hệ thống tập tin ảo**.
2. Trong lịch sử hội thoại của Agent, nội dung ban đầu được **thay thế bằng đường dẫn file + bản xem trước (preview) 10 dòng đầu tiên**.
3. Khi cần xem chi tiết, Agent có thể **chủ động đọc lại** qua `read_file` hoặc tra cứu bằng `grep`.

Ví dụ khi Agent gọi tool tìm kiếm và nhận về lượng dữ liệu quá lớn:

```text
Kết quả gốc: [50.000 tokens kết quả tìm kiếm web]

Sau khi kích hoạt Auto-Eviction:
"Kết quả đã được lưu trữ tại /workspace/search_results_001.md,
 Bản xem trước 10 dòng đầu:
   1  # Search Results for 'LangGraph'
   2
   3  ## Result 1: Official Documentation
   4  ..."
```

Cơ chế này diễn ra **hoàn toàn tự động ngầm bên dưới** — Agent không cần phải viết code dọn dẹp thủ công, nhưng vẫn bảo toàn khả năng truy cập lại toàn vẹn dữ liệu bất cứ lúc nào thông qua `read_file` hoặc `grep`.

---

### 2. Tóm tắt lịch sử hội thoại (Conversation Summarization)

Khi tổng lượng token trong context chạm ngưỡng cấu hình, Deep Agents sẽ kích hoạt tiến trình **tự động tóm tắt (auto-summarization)**. Hàm `create_deep_agent()` nếu nhận diện được kích thước context window từ model profile sẽ mặc định lấy **85% kích thước cửa sổ** làm ngưỡng; nếu thiếu thông tin này, nó sẽ áp dụng ngưỡng token cố định hoặc theo giá trị bạn thiết lập thủ công:

1. Ghi toàn bộ các message cũ cần tóm tắt **vào Storage Backend**, bảo lưu vĩnh viễn để tra cứu sau này nếu cần.
2. Dùng LLM tạo một bản tóm tắt có cấu trúc (gồm: mục tiêu ban đầu, các sản phẩm đã tạo ra, các bước tiếp theo cần làm), đồng thời đính kèm đường dẫn lưu trữ file lịch sử.
3. Thay thế nội dung gửi cho LLM ở lượt tiếp theo thành: **"Bản tóm tắt + Các message gần nhất"**. Khi tóm tắt bình thường, các message gốc trong LangGraph State vẫn được giữ lại đầy đủ.

> 💡 **Điểm mấu chốt cần phân biệt:**
> Cần phân định rõ giữa **"Lịch sử message được lưu trữ"** và **"Nội dung mà LLM thực sự nhìn thấy trong prompt hiện tại"**.
> - Bản tóm tắt (Summary) giúp cắt ngắn input đưa vào LLM, tránh tràn cửa sổ ngữ cảnh.
> - File lịch sử lưu ở Backend đóng vai trò như bản sao lưu chi tiết (archive). Việc Agent có thể đọc ngược lại chi tiết lịch sử hay không phụ thuộc vào việc Backend có lưu thành công và file còn tồn tại hay không.
> - Chi tiết so sánh giữa hai Middleware tóm tắt cùng tên có thể xem tại [Chương 4: SummarizationMiddleware](../ch04-task-planning/#summarizationmiddleware上下文压缩的真身).

![Context Auto-Management: Dọn dẹp kết quả lớn thành tham chiếu file; Middleware tóm tắt lưu message cũ và đổi input của model thành tóm tắt + message gần đây](../public/imgs/08-flowchart-context-management.png)

---

## Các Storage Backend Có Thể Cắm Rút (Pluggable Backends)

Cho đến lúc này, "Hệ thống tập tin ảo" vẫn là một khái niệm trừu tượng. Dữ liệu thực tế được lưu vào đâu phụ thuộc vào **Backend (Hậu phương lưu trữ)** được chọn.

Kiến trúc Backend của Deep Agents mang tính **module hóa (pluggable)** — bạn có thể linh hoạt hoán đổi chiến lược lưu trữ tùy theo từng bài toán.

```
                    ┌─────────────────────────┐
                    │      Deep Agent         │
                    │ (ls, read, write, edit) │
                    └────────────┬────────────┘
                                 │
           ┌─────────────────────┴─────────────────────┐
           ▼                                           ▼
┌──────────────────────┐                     ┌───────────────────┐
│     StateBackend     │                     │ FilesystemBackend │
│ (LangGraph State)    │                     │   (Local Disk)    │
└──────────────────────┘                     └───────────────────┘
           │                                           │
           ▼                                           ▼
┌──────────────────────┐                     ┌───────────────────┐
│     StoreBackend     │                     │ Sandbox Backend   │
│ (Cross-thread Store) │                     │ (Daytona, Modal)  │
└──────────────────────┘                     └───────────────────┘
```

---

### 1. `StateBackend` (Mặc định): Lưu trữ tạm thời trong phiên

```python
from deepagents import create_deep_agent

# Mặc định sử dụng StateBackend, không cần chỉ định thủ công
agent = create_deep_agent(model=model)
```

File được lưu trực tiếp bên trong `AgentState` của LangGraph (dưới dạng cấu trúc dữ liệu in-memory).

**Đặc điểm:**
- **Bền vững trong cùng một thread hội thoại**: Trải qua nhiều vòng hỏi-đáp (multi-turn conversation) trong cùng thread thì file không bị mất.
- **Biến mất khi kết thúc thread**: Chuyển sang một `thread_id` mới là dữ liệu file sẽ bị xóa sạch.
- **Chia sẻ giữa Agent cha và Sub-Agent**: Main Agent và Sub-Agent trong cùng luồng có thể nhìn thấy file của nhau.

**Kịch bản phù hợp:** Lựa chọn mặc định cho hầu hết các tác vụ thông thường — đóng vai trò như "giấy nháp" (scratchpad) cho Agent.

---

### 2. `FilesystemBackend`: Đĩa cứng cục bộ

```python
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model=model,
    backend=FilesystemBackend(root_dir=".", virtual_mode=True)
)
```

File được đọc và ghi trực tiếp lên **hệ thống tập tin của máy tính vật lý / máy chủ**.

**Đặc điểm:**
- Tham số `root_dir` chỉ định thư mục gốc mà Agent được phép truy cập; đường dẫn tương đối sẽ được giải quyết thành đường dẫn tuyệt đối (`Path(root_dir).resolve()`), `"."` đại diện cho thư mục làm việc hiện tại (working directory).
- `virtual_mode=True` kích hoạt cơ chế sandbox đường dẫn (ngăn chặn tấn công path traversal như `../`, ký tự `~` hoặc các đường dẫn tuyệt đối nhảy ra ngoài thư mục gốc). **RẤT KHUYẾN NGHỊ BẬT**. Nếu để mặc định `virtual_mode=False`, dù bạn có đặt `root_dir`, Agent vẫn có thể đọc/ghi ngoài phạm vi cho phép.
- Mọi chỉnh sửa file trên đĩa cứng là **thật và không thể đảo ngược** (permanent & irreversible).

**Kịch bản phù hợp:** CLI hỗ trợ lập trình viên (coding assistant) chạy trên máy cá nhân, pipeline CI/CD tự động sửa code.

> 💡 **Cảnh báo phiên bản:** Từ bản 0.5.0, nếu không khai báo rõ ràng `virtual_mode` sẽ có Deprecation Warning, và từ bản 0.6.0 trở đi tham số này trở thành bắt buộc. Hãy luôn cấu hình tường minh `virtual_mode=True`.

> ⚠️ **Cảnh báo an ninh:** Agent có thể đọc toàn bộ file nằm trong `root_dir`, bao gồm cả file cấu hình `.env`, secret keys hay token bảo mật. Tuyệt đối **KHÔNG** sử dụng backend này trong các dịch vụ Web công cộng hoặc API mở. Với môi trường production, hãy dùng Sandbox Backend và kết hợp cơ chế kiểm duyệt Human-in-the-Loop.

---

### 3. `LocalShellBackend`: Thực thi Shell trực tiếp trên máy chủ

```python
from deepagents.backends import LocalShellBackend

agent = create_deep_agent(
    model=model,
    backend=LocalShellBackend(root_dir=".", virtual_mode=True, env={"PATH": "/usr/bin:/bin"})
)
```

`LocalShellBackend` là bản mở rộng của `FilesystemBackend`. Ngoài các công cụ thao tác file, nó **cung cấp thêm công cụ `execute`**, cho phép Agent gõ lệnh Terminal trực tiếp trên máy chủ.

**Đặc điểm:**
- Lệnh được thực thi qua hàm Python `subprocess.run(shell=True)`, **hoàn toàn không có cơ chế cô lập sandbox**.
- Hỗ trợ các tham số kiểm soát như `timeout` (mặc định 120s), `max_output_bytes` (mặc định 100.000 bytes), và biến môi trường `env`.
- Dù `root_dir` được đặt làm thư mục làm việc khi chạy lệnh, câu lệnh Shell vẫn có thể truy cập bất kỳ đường dẫn nào trên hệ điều hành nếu user hiện tại có quyền.

**Kịch bản phù hợp:** Trợ lý lập trình cá nhân trên máy dev riêng của bạn, nơi bạn hoàn toàn tin tưởng vào hành vi của Agent.

> ⚠️ **CẢNH BÁO NGUY HIỂM TỘT CÙNG:**
> Agent có khả năng chạy bất kỳ câu lệnh Shell nào, bao gồm `rm -rf /`, cài cắm mã độc, gửi dữ liệu ra máy chủ ngoài hoặc làm treo hệ thống bằng cách ngốn sạch CPU/RAM.
> **TUYỆT ĐỐI KHÔNG DÙNG TRONG PRODUCTION HOẶC MÔI TRƯỜNG NHIỀU NGƯỜI DÙNG.**

**Các lớp phòng vệ bắt buộc nếu phải chạy thử trên máy dev cá nhân:**
1. Trỏ `root_dir` vào một thư mục tạm riêng biệt, không trỏ vào thư mục Home (`~`) hoặc thư mục cha của toàn bộ repo.
2. Thiết lập rõ `virtual_mode=True`, và chỉ truyền danh sách biến môi trường tối thiểu qua `env={"PATH": "/usr/bin:/bin"}` để hạn chế tầm với của lệnh.
3. Không đặt file `.env`, private key SSH, AWS credentials trong thư mục Agent có quyền đọc.
4. Cấu hình Human-in-the-Loop để phê duyệt trước khi Agent thực thi các lệnh nguy hiểm (`rm`, `mv`, cài đặt package qua mạng, thay đổi config hệ thống).
5. Khi cần chạy code không đáng tin cậy hoặc phục vụ user bên ngoài, hãy chuyển thẳng sang **Sandbox Backend**, không dùng `LocalShellBackend`.

---

### 4. `StoreBackend`: Lưu trữ bền vững xuyên phiên (Cross-session Persistence)

```python
from langgraph.store.memory import InMemoryStore
from deepagents.backends import StoreBackend

agent = create_deep_agent(
    model=model,
    backend=StoreBackend(
        namespace=lambda rt: (rt.server_info.user.identity,),  # Cô lập dữ liệu theo từng user
    ),
    store=InMemoryStore()  # Dùng khi dev local; khi deploy lên LangSmith Platform có thể bỏ qua
)
```

File được lưu trữ vào hạ tầng `BaseStore` của LangGraph.

**Đặc điểm:**
- **Lưu trữ xuyên thread (Cross-thread persistence)**: Các phiên hội thoại khác nhau của cùng một user đều có thể truy cập chung một kho file.
- Tham số `namespace` kiểm soát việc phân vùng dữ liệu: `lambda rt: (rt.server_info.user.identity,)` đảm bảo người dùng A không bao giờ đọc được dữ liệu của người dùng B.
- Môi trường dev dùng `InMemoryStore`, còn khi deploy lên LangSmith hoặc LangGraph Cloud thì hệ thống tự động gắn store cơ sở dữ liệu chuyên dụng.

**Kịch bản phù hợp:** Lưu trữ trí nhớ dài hạn (Long-term memory), cấu hình sở thích của người dùng qua các phiên làm việc, xây dựng kho tri thức cá nhân tích lũy dần.

> 💡 **Xử lý `namespace` khi chạy Local:**
> Từ bản v0.5.0, `namespace` là tham số bắt buộc. Khi chạy trên LangGraph Cloud/LangSmith, `rt.server_info.user.identity` sẽ tự động lấy ID của user đăng nhập. Tuy nhiên khi gọi `agent.invoke()` tại máy local, `rt.server_info` sẽ có giá trị `None` và gây crash lỗi nếu truy cập trực tiếp. Hãy dùng hàm fallback an toàn như sau:
>
> ```python
> namespace=lambda rt: (
>     (rt.server_info.user.identity,)
>     if rt.server_info else
>     ("local-user",)
> ),
> ```

---

### 5. `CompositeBackend`: Định tuyến kết hợp (Hybrid Routing)

Đây là mô hình linh hoạt và mạnh mẽ nhất trong thực tế — **mỗi đường dẫn thư mục sẽ được định tuyến đến một Backend khác nhau**:

> ⚠️ **Lưu ý tương thích bản v0.7**: Tham số `backend=` bắt buộc phải nhận một instance cụ thể như `CompositeBackend(...)`. Cách dùng factory function dạng `backend=lambda rt: ...` đã bị loại bỏ hoàn toàn. Riêng `StoreBackend(namespace=lambda rt: ...)` vẫn hỗ trợ vì lambda này dùng để tính toán namespace lưu trữ lúc runtime, không phải để tạo backend instance.

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

agent = create_deep_agent(
    model=model,
    backend=CompositeBackend(
        default=StateBackend(),            # Mặc định: Lưu nháp tạm thời trong phiên
        routes={
            "/memories/": StoreBackend(     # Đường dẫn /memories/: Lưu vĩnh viễn xuyên phiên
                namespace=lambda rt: (
                    (rt.server_info.user.identity,)
                    if rt.server_info else
                    ("local-user",)
                ),
            ),
        }
    ),
    store=InMemoryStore()
)
```

**Hiệu quả đạt được:**
- Khi Agent ghi file vào `/workspace/plan.md` → Tự động định tuyến vào `StateBackend` (dữ liệu tạm, mất khi hết phiên).
- Khi Agent ghi file vào `/memories/preferences.txt` → Tự động lưu vào `StoreBackend` (dữ liệu bền vững, cô lập theo user ID).
- Các lệnh tìm kiếm `ls`, `glob`, `grep` sẽ **tự động tổng hợp kết quả từ tất cả các backend**, đồng thời bảo lưu tiền tố đường dẫn nguyên vẹn.

Kiến trúc này giúp Agent vừa có một "tập giấy nháp tốc độ cao" (`State`), vừa sở hữu một "kho ký ức vĩnh cửu" (`Store`) mà không cần thay đổi cách Agent gọi lệnh.

---

### 6. Sandbox Backend: Thực thi Code trong môi trường cô lập

Khi tích hợp các Sandbox Backend chuyên nghiệp trên đám mây (như Modal, Daytona, Runloop, E2B...), ngoài các công cụ thao tác file, Agent sẽ được cấp công cụ `execute` nhưng chạy hoàn toàn bên trong Container/VM biệt lập:

```python
# Sandbox backend tự động cung cấp công cụ execute an toàn
agent = create_deep_agent(
    model=model,
    backend=sandbox  # Instance của dịch vụ sandbox
)

# Agent giờ đây có thể an tâm chạy các lệnh cài đặt và phân tích dữ liệu:
# execute("pip install pandas && python analyze.py")
```

*(Chi tiết về cách cấu hình Sandbox sẽ được trình bày chuyên sâu tại Chương 10).*

---

### Bảng Hướng Dẫn Lựa Chọn Backend

| Tình huống sử dụng | Backend khuyến nghị | Lý do lựa chọn |
|---|---|---|
| **Học tập và thử nghiệm** | `StateBackend` (Mặc định) | Cấu hình bằng 0, tự động dọn rác sau mỗi phiên test |
| **Trợ lý lập trình cục bộ** | `FilesystemBackend` | Thao tác trực tiếp trên các file source code của dự án |
| **Cần ghi nhớ thông tin xuyên phiên** | `CompositeBackend` | Kết hợp hài hòa giữa vùng tạm thời và vùng ký ức lâu dài |
| **Cần chạy code hoặc Terminal** | Sandbox Backend | Đảm bảo an toàn tuyệt đối, cô lập môi trường thực thi |
| **Triển khai Production quy mô lớn** | `StoreBackend` hoặc `CompositeBackend` | Hỗ trợ lưu trữ bền vững, mở rộng ngang (scalable) tốt |

---

## Tùy Biến Backend và Thiết Lập Chính Sách An Toàn

### 1. Phân quyền khai báo: `FilesystemPermission`

Cách đơn giản và tường minh nhất để kiểm soát quyền truy cập đường dẫn mà không cần sửa code backend là dùng `FilesystemPermission`:

```python
from deepagents import create_deep_agent, FilesystemPermission
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    model=model,
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(
                namespace=lambda rt: (
                    (rt.server_info.user.identity,)
                    if rt.server_info else
                    ("local-user",)
                ),
            ),
        },
    ),
    permissions=[
        FilesystemPermission(
            operations=["write"],
            paths=["/policies/**"],
            mode="deny",           # Chặn tuyệt đối hành vi ghi đè vào thư mục /policies/
        ),
    ],
)
```

> 💡 **Cơ chế đánh giá quyền hạn (First-match-wins):**
> Các quy tắc quyền hạn được đối chiếu tuần tự theo thứ tự khai báo trong mảng `permissions`. Quy tắc đầu tiên đồng thời khớp cả `operations` (loại thao tác) và `paths` (đường dẫn dạng glob pattern) sẽ quyết định kết quả. Nếu duyệt hết danh sách mà không có quy tắc nào khớp, hành động sẽ được **mặc định cho phép (allow by default)**. Do đó, hãy luôn đặt các quy tắc cụ thể/chặt chẽ lên trước các quy tắc bao quát.

Ba chế độ (`mode`) của `FilesystemPermission`:

| `mode` | Hành vi hệ thống | Kịch bản áp dụng |
|---|---|---|
| `"allow"` | Cho phép thao tác tiếp tục thực thi | Đặt ngoại lệ cho các thư mục con cụ thể trong vùng cấm |
| `"deny"` | Từ chối ngay lập tức, trả lỗi về cho Agent | Các đường dẫn nhạy cảm tuyệt đối không cho phép ai đụng vào |
| `"interrupt"` | Tạm dừng toàn bộ luồng chạy của Agent và chờ con người xét duyệt | Các đường dẫn nhạy cảm có thể sửa nhưng bắt buộc phải có Human Review |

> [!NOTE]
> Chế độ `mode="interrupt"` yêu cầu phải cấu hình Checkpointer trong LangGraph và sử dụng giao thức nối lại `Command(resume=...)`. Chi tiết sẽ được trình bày tại [Chương 9: Human-in-the-Loop](../ch09-human-in-the-loop/#文件系统权限中断) và [Chương 11: Filesystem Permissions](../ch11-filesystem-permissions/).

---

### 2. Hiện thực Custom Backend qua `BackendProtocol`

Nếu các backend có sẵn không đáp ứng được yêu cầu (ví dụ: bạn muốn lưu trữ file trực tiếp lên Amazon S3, MinIO, Azure Blob hay bảng cơ sở dữ liệu PostgreSQL), bạn chỉ cần implement giao diện chuẩn `BackendProtocol`:

```python
from deepagents.backends.protocol import (
    BackendProtocol, WriteResult, EditResult, DeleteResult,
    LsResult, ReadResult, GrepResult, GlobResult,
)

class S3Backend(BackendProtocol):
    def __init__(self, bucket: str, prefix: str = ""):
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")

    def ls(self, path: str) -> LsResult:
        # Liệt kê các S3 Objects, trả về danh sách FileInfo
        ...

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        # Đọc dữ liệu S3 Object, trả về ReadResult(file_data=...) hoặc ReadResult(error=...)
        ...

    def write(self, file_path: str, content: str) -> WriteResult:
        # Đẩy dữ liệu lên S3, với backend lưu trữ ngoài thì files_update=None
        ...

    def edit(self, file_path: str, old_string: str, new_string: str,
             replace_all: bool = False) -> EditResult:
        # Đọc từ S3 → Thay thế chuỗi → Ghi đè lại lên S3
        ...

    def grep(self, pattern: str, path: str | None = None, glob: str | None = None) -> GrepResult:
        # Tìm kiếm chuỗi trong các file trên S3
        ...

    def glob(self, pattern: str, path: str = "/") -> GlobResult:
        # Khớp pattern tên file trên S3, trả về danh sách FileInfo
        ...

    def delete(self, file_path: str) -> DeleteResult:
        # Xóa file hoặc tiền tố thư mục trên S3; cần implement khi mở tool delete cho Agent
        ...
```

> 💡 **Lưu ý khi mở rộng v0.7:**
> Bộ interface cốt lõi của `BackendProtocol` bao gồm `ls`, `read`, `write`, `edit`, `grep`, `glob`. Để Agent có thể sử dụng tính năng xóa file ở bản v0.7, Backend bắt buộc phải hiện thực thêm phương thức `delete()` và trả về `DeleteResult`. Các lớp bọc bảo vệ (wrapper) cũng cần chuyển tiếp hoặc chặn phương thức `delete` đồng bộ, không được chỉ bảo vệ mỗi `write()` và `edit()`.

---

### 3. Chính sách an toàn nâng cao: `PolicyWrapper`

Trong các tình huống doanh nghiệp cần kiểm soát gắt gao (như Rate Limiting, Audit Logging ghi vết kiểm toán, lọc kiểm tra dữ liệu độc hại), bạn có thể áp dụng hai mẫu thiết kế sau:

#### Cách 1: Kế thừa trực tiếp từ Backend có sẵn
Thích hợp khi bạn muốn can thiệp sâu vào một backend cụ thể (ví dụ: `FilesystemBackend`):

```python
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import WriteResult, EditResult, DeleteResult

class GuardedBackend(FilesystemBackend):
    def __init__(self, *, deny_prefixes: list[str], **kwargs):
        super().__init__(**kwargs)
        self.deny_prefixes = [p if p.endswith("/") else p + "/" for p in deny_prefixes]

    def write(self, file_path: str, content: str) -> WriteResult:
        if any(file_path.startswith(p) for p in self.deny_prefixes):
            return WriteResult(error=f"Quyền ghi bị từ chối: {file_path}")
        return super().write(file_path, content)

    def edit(self, file_path: str, old_string: str, new_string: str,
             replace_all: bool = False) -> EditResult:
        if any(file_path.startswith(p) for p in self.deny_prefixes):
            return EditResult(error=f"Quyền chỉnh sửa bị từ chối: {file_path}")
        return super().edit(file_path, old_string, new_string, replace_all)

    def delete(self, file_path: str) -> DeleteResult:
        if any(file_path.startswith(p) for p in self.deny_prefixes):
            return DeleteResult(error=f"Quyền xóa bị từ chối: {file_path}")
        return super().delete(file_path)
```

#### Cách 2: Universal Wrapper (Bộ bọc đa năng áp dụng cho mọi Backend)
Sử dụng mẫu thiết kế Decorator/Proxy để bọc ngoài bất kỳ backend nào mà không phụ thuộc vào lớp con:

```python
from deepagents.backends.protocol import BackendProtocol, WriteResult, EditResult, DeleteResult

class PolicyWrapper(BackendProtocol):
    def __init__(self, inner: BackendProtocol, deny_prefixes: list[str]):
        self.inner = inner
        self.deny_prefixes = [p if p.endswith("/") else p + "/" for p in deny_prefixes]

    def _deny(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.deny_prefixes)

    # Ủy quyền toàn bộ các thao tác đọc và tra cứu cho backend bên trong
    def ls(self, path): return self.inner.ls(path)
    def read(self, file_path, offset=0, limit=2000): return self.inner.read(file_path, offset=offset, limit=limit)
    def grep(self, pattern, path=None, glob=None): return self.inner.grep(pattern, path, glob)
    def glob(self, pattern, path="/"): return self.inner.glob(pattern, path)

    # Chặn đứng các hành vi thay đổi dữ liệu nếu vi phạm danh sách cấm
    def write(self, file_path: str, content: str) -> WriteResult:
        if self._deny(file_path):
            return WriteResult(error=f"Quyền ghi bị từ chối: {file_path}")
        return self.inner.write(file_path, content)

    def edit(self, file_path: str, old_string: str, new_string: str,
             replace_all: bool = False) -> EditResult:
        if self._deny(file_path):
            return EditResult(error=f"Quyền chỉnh sửa bị từ chối: {file_path}")
        return self.inner.edit(file_path, old_string, new_string, replace_all)

    def delete(self, file_path: str) -> DeleteResult:
        if self._deny(file_path):
            return DeleteResult(error=f"Quyền xóa bị từ chối: {file_path}")
        return self.inner.delete(file_path)
```

---

## Tổng kết (Takeaways)

Chương này đã dẫn dắt bạn đi sâu vào trái tim Context Engineering của Deep Agents:

1. **Triết lý thiết kế**: Giúp Agent làm việc tương tự như con người — đọc dữ liệu theo nhu cầu, lưu trữ có cấu trúc, tìm kiếm chính xác thay vì nhồi nhét mọi thứ vào prompt.
2. **7 Built-in Tools hoàn chỉnh**: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep` tạo thành một vòng đời quản lý file khép kín.
3. **Quản lý Context tự động**:
   - Tự động di tản dữ liệu lớn (>20K tokens) ra file và chỉ để lại đường dẫn tham chiếu kèm bản xem trước ngắn.
   - Tự động tóm tắt message cũ vào Storage Backend khi chạm ngưỡng giới hạn và chuyển context gửi sang mô hình thành "Bản tóm tắt + Các message mới nhất".
4. **Hệ thống Backend cắm rút linh hoạt**:
   - `StateBackend`: Lưu nháp tạm thời.
   - `FilesystemBackend`: Truy cập đĩa cứng máy chủ kèm chế độ `virtual_mode` chống path traversal.
   - `LocalShellBackend`: Chạy Shell cục bộ (chỉ dùng cho môi trường dev tin cậy).
   - `StoreBackend`: Bền vững xuyên phiên hội thoại có phân vùng namespace.
   - `CompositeBackend`: Định tuyến lai theo tiền tố đường dẫn thư mục.
   - **Sandbox Backend**: Môi trường chạy code an toàn tuyệt đối trên Container/Cloud.
5. **Kiểm soát phân quyền & An toàn thông tin**: Sử dụng `FilesystemPermission` theo cơ chế khai báo (first-match-wins) hoặc viết các custom class như `GuardedBackend` / `PolicyWrapper` để kiểm soát các tác vụ nhạy cảm.
6. **Lưu ý nâng cấp v0.7**: Không còn sử dụng factory function `backend=lambda rt: ...`; bắt buộc khởi tạo trực tiếp instance của Backend.

Ở chương tiếp theo, chúng ta sẽ tìm hiểu một năng lực trụ cột khác của Deep Agents — **Task Planning (Lập kế hoạch công việc)** và cách thức kích hoạt `write_todos` một cách bài bản trong phiên bản v0.7!
