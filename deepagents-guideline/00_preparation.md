# Chuẩn bị



## Skills



- **langchain-dev-guide**

```bash
npx skills add ob-labs/agentseek --skill langchain-dev-guide
```

- **langsmith-trace**

```bash
npx skills add ob-labs/agentseek --skill langsmith-trace
```

## AgentSeek

> Sau khi hoàn thành chương này, bạn sẽ có một ứng dụng research DeepAgents chạy được. AgentSeek sẽ đảm nhận kiểm tra môi trường, cài dependencies cho dự án và khởi chạy backend/frontend.
>
> Các lệnh trong bài được xác minh ngày 2026-08-18 với AgentSeek `0.1.2`. AgentSeek và template sẽ tiếp tục cập nhật; nếu tên task khác với bài viết, hãy lấy output của `agentseek task --list` làm chuẩn.

### AgentSeek quản lý những gì

AgentSeek là một công cụ template và lifecycle dành cho phát triển ứng dụng AI. Bạn tạo dự án từ template, rồi dùng một tập lệnh cố định để quản lý các dự án khác nhau:

| Giai đoạn | Lệnh                | Mục đích                                  |
| --------- | ------------------- | ----------------------------------------- |
| Tạo       | `agentseek create`  | Sinh dự án có thể chỉnh sửa từ template   |
| Xem       | `agentseek info`    | Xem entry point, yêu cầu môi trường và task của dự án |
| Chuẩn bị  | `agentseek task`    | Chạy các task một lần do template khai báo, chẳng hạn cài dependencies |
| Kiểm tra  | `agentseek doctor`  | Kiểm tra tĩnh file, uv, Node.js, npm và biến môi trường |
| Chạy      | `agentseek dev`     | Khởi chạy các tiến trình phát triển local do template khai báo |

Mỗi dự án được sinh ra đều chứa `.agentseek/lifecycle.toml`. File này khai báo template hiện tại cần những công cụ, biến môi trường, task và local service nào. AgentSeek đọc file này chứ không tiếp quản code framework của ứng dụng.

### 1. Chuẩn bị môi trường local

Chương này dùng template `deepagents/research`. Bạn cần:

| Dependency   | Yêu cầu             | Mục đích                       |
| ------------ | ------------------- | ------------------------------ |
| Python       | 3.12 hoặc 3.13      | Chạy AgentSeek và backend DeepAgents |
| uv           | Bản stable hiện tại | Cài CLI và Python dependencies |
| Node.js, npm | Bản LTS hiện tại    | Chạy frontend React            |

#### Học viên Windows: ưu tiên dùng WSL2

Các lệnh của khóa học chủ yếu viết cho môi trường Bash. Học viên dùng Windows 10 2004+ hoặc Windows 11 nên dùng WSL2 + Ubuntu để chạy trực tiếp các lệnh macOS / Linux / WSL2 phía sau. Hãy cài đặt trong **PowerShell quyền Administrator**:

```
wsl --install
```

Sau khi cài xong, khởi động lại Windows; lần đầu mở Ubuntu, hãy tạo username và password Linux theo hướng dẫn. Sau đó xác nhận trong PowerShell rằng bản phân phối đang dùng WSL 2, rồi vào Ubuntu:

```
wsl -l -v
wsl -d Ubuntu
```

Nếu `wsl -l -v` hiển thị version 1, hãy tham khảo [tài liệu cài đặt WSL của Microsoft](https://learn.microsoft.com/windows/wsl/install) để nâng cấp lên WSL 2. Khi dùng công cụ Linux của WSL2, nên đặt dự án trong thư mục thuộc Linux filesystem như `~/projects/`, đừng đặt dưới `/mnt/c/`; cũng đừng trộn lẫn Python, uv, Node.js, npm hay Git giữa Windows và WSL. Xem thêm [hướng dẫn môi trường phát triển WSL của Microsoft](https://learn.microsoft.com/windows/wsl/setup/environment).

Nếu chính sách thiết bị, quyền admin hay điều kiện ảo hóa không cho phép cài WSL2, bạn có thể ở lại PowerShell Windows nguyên sinh và dùng các lệnh PowerShell được đánh dấu trong bài.

macOS / Linux / WSL2 cài `uv`:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

PowerShell Windows nguyên sinh cài `uv`:

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Cài AgentSeek:

```
uv tool install --upgrade agentseek
```

Nếu PowerShell Windows nguyên sinh báo thư mục tool của uv không nằm trong PATH, hãy chạy:

```
uv tool update-shell
```

Sau đó đóng và mở lại PowerShell rồi mới kiểm tra version. Nếu chỉ muốn có hiệu lực ngay trong phiên hiện tại, có thể tạm thêm thư mục tool mà uv trả về:

```
$env:Path = "$(uv tool dir --bin);$env:Path"
```

Cách viết tạm thời này không thay đổi PATH vĩnh viễn. Hành vi của `uv tool update-shell` lấy [tài liệu CLI chính thức của uv](https://docs.astral.sh/uv/reference/cli/) làm chuẩn.

Xác nhận các lệnh đã dùng được:

```
agentseek version
agentseek --help
```

Bạn sẽ thấy `create`, `info`, `task`, `doctor` và `dev` trong phần trợ giúp. Khi xác minh bài này, output version là `AGENTSEEK v0.1.2`; sau này số version có thể khác.

### 2. Chọn và tạo template

Xem các template mà CLI hiện nhận diện:

```
agentseek create --list-templates --checkout main
```

Lệnh này liệt kê các template đang đăng ký trên nhánh `main` của template repository; nếu không có `--checkout main`, danh sách đến từ thư mục bị khóa theo version AgentSeek hiện tại và có thể chưa kèm lô template mới nhất. Khóa học dùng `deepagents/research`, gồm DeepAgents research Agent, tìm kiếm Tavily và frontend React.

Tạo dự án và lấy lô template mới nhất từ nhánh `main` của template repository:

```
agentseek create deepagents/research --checkout main --no-input
```

`--checkout main` khiến AgentSeek đọc nhánh `main` hiện tại của template repository lúc tạo, thay vì chỉ dùng thư mục khóa sẵn trong CLI. Nó phù hợp khi học theo template mới nhất; sau khi template cập nhật, file và dependencies của dự án sinh ra cũng có thể thay đổi. Nếu bạn cần bài tập tái hiện chính xác một kết quả cụ thể, hãy thay `main` bằng commit SHA đầy đủ đã ghi lại lúc đó.

Vào thư mục đã sinh:

```
cd research_deepagent
```

Nếu muốn tùy chỉnh tên dự án, model và port, hãy bỏ `--no-input` rồi điền các biến template theo hướng dẫn.

### 3. Xem cấu hình lifecycle

Trước tiên xem tóm tắt dự án:

```
agentseek info
```

Tiếp theo xem các task một lần do template cung cấp:

```
agentseek task --list
```

Template `deepagents/research` hiện tại liệt kê hai task chuẩn bị:

```
sync      Install Python dependencies with uv.
frontend  Install frontend dependencies.
```

Tên task thuộc cấu hình của template. Sau này nếu output thay đổi, hãy chạy task cài dependencies tương ứng theo output.

Các file quan trọng trong dự án:

```
research_deepagent/
├── .agentseek/lifecycle.toml
├── .env.example
├── frontend/
│   ├── .env.example
│   ├── package.json
│   └── src/
├── langgraph.json
├── pyproject.toml
└── src/research_deepagent/
    ├── agent.py
    ├── prompts.py
    └── tools.py
```

### 4. Cài dependencies cho dự án

Chạy task dependencies backend do template khai báo:

```
agentseek task sync
```

Cài dependencies frontend:

```
agentseek task frontend
```

Hai task này hiện lần lượt chạy `uv sync` và `npm install --prefix frontend`. Bạn có thể xem lệnh thực tế trong `.agentseek/lifecycle.toml`.

### 5. Cấu hình model và dịch vụ tìm kiếm

Copy file môi trường của backend và frontend:

```
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Mở `.env` và điền Key cho model và dịch vụ tìm kiếm. Khóa học mặc định dùng giao diện tương thích OpenAI do nhà tài trợ khóa học SiliconFlow cung cấp, và chọn GLM làm model demo:

```
AGENTSEEK_MODEL_PROVIDER=openai
AGENTSEEK_MODEL=zai-org/GLM-5.2
OPENAI_API_BASE=https://api.siliconflow.cn/v1
OPENAI_API_KEY=<your-siliconflow-api-key>

TAVILY_API_KEY=<your-tavily-api-key>

LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
```

SiliconFlow cung cấp giao diện tương thích OpenAI nên provider vẫn viết `openai` và credentials vẫn đặt trong `OPENAI_API_KEY`; đừng đổi sang các biến như `SILICONFLOW_API_KEY`, `GLM_API_KEY` mà template không khai báo. `<your-siliconflow-api-key>` và `<your-tavily-api-key>` là placeholder — hãy thay bằng giá trị của bạn và đừng commit Key thật lên Git.

Chương này đã chạy thật với `zai-org/GLM-5.2` ngày 15/07/2026. Model sẽ được ra mắt, gỡ bỏ hoặc đổi tên; nếu tên này không còn khả dụng, hãy copy model ID đầy đủ của GLM đang khả dụng tại [SiliconFlow Models](https://cloud.siliconflow.cn/models).

Nếu bạn đã có OpenAI Key, có thể dùng OpenAI:

```
AGENTSEEK_MODEL_PROVIDER=openai
AGENTSEEK_MODEL=gpt-4.1-mini
OPENAI_API_BASE=
OPENAI_API_KEY=<your-openai-api-key>
```

Khi dùng Anthropic, đổi model provider, tên model và Key:

```
AGENTSEEK_MODEL_PROVIDER=anthropic
AGENTSEEK_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=<your-anthropic-api-key>
```

Khi dùng Gemini:

```
AGENTSEEK_MODEL_PROVIDER=google_genai
AGENTSEEK_MODEL=gemini-2.5-pro
GOOGLE_API_KEY=<your-google-api-key>
```

Các dịch vụ tương thích OpenAI khác cũng dùng `AGENTSEEK_MODEL_PROVIDER=openai`, cấu hình địa chỉ, credentials và model qua `OPENAI_API_BASE`, `OPENAI_API_KEY` và model ID đầy đủ.

> Ghi chú developer: giao diện tương thích OpenAI phù hợp để tích hợp nhanh, nhưng không có nghĩa mọi trường mở rộng và hành vi tool đều giống nhau. Chương này đã xác minh output streaming cơ bản và Tool Call với SiliconFlow + GLM; nếu bạn định đổi sang model reasoning, parse `reasoning_content` hay tùy chỉnh tool protocol, hãy dùng `langchain-dev-guide` kiểm tra ranh giới tương thích ở chương tiếp theo trước.

`TAVILY_API_KEY` dùng cho tìm kiếm web của research Agent. Bạn có thể tạo Key tại [Tavily](https://app.tavily.com/).

### 6. Kiểm tra điều kiện khởi chạy

Chạy readiness check:

```
agentseek doctor
```

AgentSeek sẽ kiểm tra uv, Node.js, npm, các file bắt buộc, thư mục dependencies và biến môi trường. Nếu kiểm tra thất bại, hãy sửa từng mục rồi mới tiếp tục khởi chạy.

Xem trước tiến trình phát triển mà không khởi chạy service:

```
agentseek dev --dry-run
```

Bạn sẽ thấy hai tiến trình:

- LangGraph backend, mặc định tại `http://127.0.0.1:2024`
- React frontend, mặc định tại `http://127.0.0.1:5174`

### 7. Tùy chọn: bật LangSmith Trace cho chương sau

Chương sau sẽ dùng `langsmith-trace` phân tích quá trình research này. Nếu bạn định tiếp tục phần thực hành đó, trước tiên hãy bật Trace trong `.env`:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your-langsmith-api-key>
LANGSMITH_PROJECT=deepagents-course
```

`<your-langsmith-api-key>` là placeholder. Hãy tạo Key riêng tại [LangSmith](https://smith.langchain.com/settings) và chỉ ghi giá trị thật vào `.env` — file không bị commit lên Git.

LangChain và LangGraph tự động ghi Trace, không cần sửa code ứng dụng. `LANGSMITH_PROJECT` dùng để gom các run của chương này vào project `deepagents-course`; nếu bỏ qua, Trace thường sẽ vào project `default`.

Đừng ghi Key thật trực tiếp vào lệnh Shell và đừng dùng `--api-key`. Nội dung lệnh có thể lọt vào Shell history, danh sách process hoặc log của coding assistant.

Trace có thể chứa prompt, tham số tool và output của model. Chương này chỉ dùng câu hỏi research công khai. Nếu input của bạn có dữ liệu nhạy cảm, hãy đọc thiết lập data masking của LangSmith trước, đừng sao chép nguyên cấu hình của chương này.

Nếu bạn tạm không dùng LangSmith, hãy giữ:

```
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
```

### 8. Khởi chạy và xác nhận kết nối backend/frontend

Khởi chạy backend/frontend:

```
agentseek dev
```

Giữ terminal này chạy. Mở một terminal khác vào cùng thư mục dự án, kiểm tra hai service:

```
agentseek doctor --live
```

Mở `http://127.0.0.1:5174` và nhập:

```
Research what LangGraph 1.0 added vs 0.x. Cite sources.
```

Template `main` của AgentSeek sẽ tiếp tục cập nhật. Trước khi chạy, hãy xem cấu hình Agent của dự án được sinh ra: nếu `TodoListMiddleware` được truyền vào tường minh, giao diện và Trace dưới đây sẽ xuất hiện Todo; nếu không bật, v0.7 sẽ không có `write_todos`, thiếu panel kế hoạch không có nghĩa là chạy thất bại.

Khi chạy bình thường, bạn sẽ thấy:

- Khi Todo được bật, Agent tạo kế hoạch research và cập nhật trạng thái todo
- Khi model chọn ủy quyền, giao diện hiển thị thẻ task của research sub-Agent
- Báo cáo cuối hiển thị link nguồn từ kết quả tìm kiếm
- Câu trả lời cuối được render bằng Markdown kèm link nguồn

Deep research sẽ thực hiện nhiều lượt gọi model, tìm kiếm và đọc trang web; với các model khác nhau có thể mất vài phút. Trong lúc chạy, hãy giữ `agentseek dev` và trang frontend mở; sau khi trang sinh thread URL, bạn có thể dùng nó để mở lại cùng một phiên hội thoại.

Nếu bạn đã bật LangSmith ở mục trước, có thể mở [LangSmith](https://smith.langchain.com/) trong lúc chạy và vào project `deepagents-course`. Trace mới nhất sẽ xuất hiện trước khi research hoàn tất; đợi báo cáo cuối sinh xong rồi hãy kiểm tra tổng thời gian.

Bạn sẽ tìm được:

- Trace gốc tên `research`
- Sub-Agent `research-agent`
- Các lượt gọi model `ChatOpenAI`
- Các lượt gọi tìm kiếm `tavily_search`
- File tool và các lớp bọc middleware; khi template bật Todo sẽ có thêm `write_todos`

Bài này đã hoàn thành 4/4 task trong lần chạy thật với SiliconFlow GLM, mất khoảng 473,5 giây. Con số này chỉ xác nhận quy trình 5–10 phút đã chạy thông; model, mạng, kết quả tìm kiếm và số Run của bạn có thể khác.

Chương sau không yêu cầu bạn hiểu mọi node middleware. Bạn chỉ cần giữ lại Trace này và biết cách phân biệt luồng gốc, sub-Agent, lượt gọi model thực tế và lượt gọi tool.

Quay lại terminal đang chạy `agentseek dev`, nhấn `Ctrl+C` để dừng backend/frontend.

### Xử lý sự cố mạng

`agentseek create` cần truy cập GitHub. Trước tiên kiểm tra kết nối repository:

Nếu terminal hiện `Could not resolve host`, `Connection timed out` hoặc `Failed to connect`, thường nên xử lý mạng trước, thay vì kết luận ngay AgentSeek CLI bị lỗi.

```
git ls-remote https://github.com/agentseek-ai/agentseek-templates.git
```

Nếu kết nối thất bại, hãy sửa mạng hoặc cấu hình proxy của terminal hiện tại trước. AgentSeek cache thư mục template remote vào thư mục người dùng của Cookiecutter; đừng xóa hay ghi đè cache chỉ để bypass vấn đề kết nối, nếu không có thể mất cache đang dùng được, hoặc lâu dài dùng một template cũ không cập nhật.

#### Đặt proxy cho terminal hiện tại

Nếu mạng đội nhóm bắt buộc dùng proxy, nên mở một terminal chuyên dụng mới rồi đặt các biến môi trường proxy chuẩn. Cách này không làm rối terminal phát triển bạn đang dùng; nếu terminal mới đã có biến proxy do đội nhóm cấp, hãy giữ cấu hình gốc, đừng ghi đè trực tiếp. macOS hoặc Linux:

```
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export NO_PROXY=127.0.0.1,localhost
```

Windows PowerShell:

```
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
$env:NO_PROXY="127.0.0.1,localhost"
```

`127.0.0.1:7890` chỉ là ví dụ, hãy thay bằng địa chỉ proxy bạn thực sự dùng. `NO_PROXY` giúp không gửi backend LangGraph local (port `2024`) và frontend (port `5174`) qua proxy.

Các biến này thường được kế thừa bởi Git, uv, npm, Python HTTP client và các tiến trình con của `agentseek dev` khởi động trong cùng terminal. Sau khi đặt, chạy lại `git ls-remote`; các lệnh `agentseek create`, task cài đặt và `agentseek dev` phía sau cũng nên khởi động từ cùng terminal đó.

Nếu đây là terminal mở riêng cho chương này, xong việc chỉ cần đóng. Chỉ khi chắc chắn các biến này vốn rỗng và do bạn đặt theo ví dụ của chương, mới chạy trên macOS hoặc Linux:

```
unset HTTP_PROXY HTTPS_PROXY NO_PROXY
```

Windows PowerShell chạy:

```
Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:NO_PROXY -ErrorAction SilentlyContinue
```

#### Đặt proxy riêng cho Git

Nếu trình duyệt và API của model truy cập được, chỉ riêng `git ls-remote` thất bại, có thể xem trước Git đã cấu hình proxy chưa:

```
git config --global --get http.proxy
```

Nếu lệnh không có output, hãy đặt theo địa chỉ thực tế. `http.proxy` của Git áp dụng cho cả remote HTTP và HTTPS:

```
git config --global http.proxy http://127.0.0.1:7890
git config --global --get http.proxy
```

`--global` ảnh hưởng đến mọi repository của user hiện tại. Chỉ khi chắc chắn giá trị này do bạn thêm mới theo ví dụ trên và trước đó không có cấu hình khác, mới xóa khi không còn cần, tránh sau này đổi mạng mà Git vẫn nối vào proxy cũ:

```
git config --global --unset http.proxy
```

#### Phân biệt proxy, package mirror và API Base

- `HTTP_PROXY`, `HTTPS_PROXY` đảm nhiệm chuyển tiếp network request, có thể ảnh hưởng đến Git, việc cài dependencies và các cuộc gọi API lúc runtime.
- `UV_INDEX_URL` và npm registry chỉ thay đổi nguồn tải package Python, Node.js; không giải quyết được kết nối tới GitHub, SiliconFlow hay Tavily.
- `OPENAI_API_BASE=https://api.siliconflow.cn/v1` chỉ định địa chỉ dịch vụ model, không phải network proxy.

Chỉ dùng proxy và package mirror do đội nhóm phê duyệt hoặc mà bạn tin tưởng. Tính khả dụng và bảo mật của các địa chỉ tăng tốc GitHub công cộng sẽ thay đổi; đừng hardcode chúng vào template dự án.

Nếu tải Python dependencies chậm, có thể tạm chỉ định mirror PyPI do đội nhóm phê duyệt cho một lần sync. Địa chỉ Alibaba Cloud dưới đây đã được xác minh khả dụng ngày 15/07/2026:

macOS / Linux / WSL2:

```
UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple agentseek task sync
```

PowerShell Windows nguyên sinh (nên chạy trong terminal tạm mở mới):

```
$env:UV_INDEX_URL = "https://mirrors.aliyun.com/pypi/simple"
agentseek task sync
Remove-Item Env:UV_INDEX_URL -ErrorAction SilentlyContinue
```

Nếu trước khi đặt, terminal hiện tại đã có `UV_INDEX_URL`, đừng chạy lệnh xóa cuối cùng; hãy khôi phục giá trị gốc sau khi sync, hoặc đóng luôn terminal chuyên dụng đã mở cho lần sync này.

Điều này chỉ thay đổi nguồn package Python của task `sync`, không giải quyết kết nối tới GitHub, SiliconFlow hay Tavily. npm registry cũng tương tự; dịch vụ mirror sẽ thay đổi, hãy xác minh lại nguồn và tính khả dụng trước khi dùng.

#### Dùng template repository đã tải về

Nếu bạn đã tải ZIP hoặc clone AgentSeek Templates repository trên máy khác truy cập được GitHub, có thể copy toàn bộ thư mục sang máy hiện tại rồi chỉ định trực tiếp đường dẫn tuyệt đối đến template:

```
agentseek create /absolute/path/to/agentseek-templates/templates/deepagents/research --no-input
```

Đường dẫn này không sửa cache template remote dùng chung, cũng không cần cố định nhánh hay commit. Dùng đường dẫn template local phù hợp với trường hợp mạng bị giới hạn nhưng bạn đã lấy template repository bằng cách khác.

Trong lần rà soát này, service tăng tốc công cộng `ghproxy.net` vẫn trả về HEAD hiện tại qua `git ls-remote`, nhưng shallow clone đầy đủ bị ngắt kết nối sau hơn một phút. Vì vậy chương này không đưa service tăng tốc công cộng vào lệnh đề xuất; nếu đội nhóm có GitHub mirror đã được audit, có thể dùng nó tải full repository rồi tạo dự án bằng đường dẫn local phía trên.

### Kết quả sau khi hoàn thành chương

Bạn hiện có:

- Một dự án `deepagents/research` có thể chỉnh sửa
- Một quy trình phát triển local được khai báo bởi `.agentseek/lifecycle.toml`
- Backend/frontend kiểm tra được bằng `agentseek doctor`, khởi chạy bằng `agentseek dev`
- Nếu đã bật LangSmith, một Trace research thật để chương sau phân tích

Chương sau sẽ cài `langchain-dev-guide` và `langsmith-trace` cho coding assistant, giúp bạn tiếp tục chỉnh sửa và debug dự án này.

Nguồn tham khảo: [AgentSeek 快速开始](https://github.com/ob-labs/agentseek/blob/main/docs/get-started/index.zh.md), [CLI 参考](https://github.com/ob-labs/agentseek/blob/main/docs/reference/cli.zh.md), [AgentSeek Templates](https://github.com/agentseek-ai/agentseek-templates), [deepagents/research 模板](https://github.com/agentseek-ai/agentseek-templates/tree/main/templates/deepagents/research), [SiliconFlow OpenAI 兼容配置](https://docs.siliconflow.cn/docs/usercases/use-siliconcloud-in-KiloCode), [LangSmith Tracing Quickstart](https://docs.langchain.com/langsmith/observability-quickstart).

### Tài nguyên liên quan

AgentSeek CLI tạo ứng dụng từ template — [Video讲解 Bilibili](https://www.bilibili.com/video/BV1cYEt6FEAq/)

---

### AgentSeek – Phần chuẩn bị (phần 2): Cài dev skills cho AI coding assistant

> Sau khi hoàn thành chương này, Codex, Claude Code hoặc các công cụ tương thích khác có thể dùng `langchain-dev-guide` và `langsmith-trace` trong dự án hiện tại.
>
> Các lệnh trong bài được xác minh ngày 15/07/2026. Skills CLI sẽ tiếp tục cập nhật; hãy lấy output của `npx skills --help` làm chuẩn.
> Học viên Windows hãy tiếp tục dùng môi trường đã chọn ở chương trước: người dùng WSL2 thực hiện các lệnh macOS / Linux / WSL2 (Bash) trong bài; học viên ở lại Windows nguyên sinh thực hiện các lệnh PowerShell tương ứng. Đừng trộn lẫn hai bộ môi trường Python, Node.js hay Git trong cùng một dự án.

#### Sự khác biệt giữa hai loại Skill

Chương này cài dev skills cho coding assistant. Chúng giúp Codex, Claude Code, Cursor… chỉnh sửa và debug dự án.

Chương 7 của khóa học giới thiệu DeepAgents runtime Skill. Runtime Skill được cung cấp cho Agent của bạn qua `create_deep_agent(skills=[...])`. Cả hai đều dùng `SKILL.md`, nhưng phục vụ đối tượng khác nhau:

| Loại                          | Người dùng                    | Cách cài hoặc load                       | Chương này có liên quan không |
| ----------------------------- | ----------------------------- | ---------------------------------------- | ------------------------------ |
| Dev skills cho coding assistant | Codex, Claude Code, Cursor… | `npx skills add ...`                     | Có                             |
| DeepAgents runtime Skill      | Deep Agent bạn tự xây         | `create_deep_agent(skills=[...])`        | Không, xem chương 7           |

#### 1. Xem dev skills của AgentSeek

Skills CLI chạy qua npm. Trước tiên xác nhận Node.js và npm đã được cài:

```
node --version
npm --version
```

Vào dự án được sinh ở chương trước:

```
cd research_deepagent
```

Xem các skill mà AgentSeek repository cung cấp:

```
npx skills add ob-labs/agentseek --list
```

Các skill trong repository sẽ tiếp tục tăng; danh sách thực tế lấy output của lệnh làm chuẩn. Khóa học tập trung dùng hai skill sau:

| Skill                 | Mục đích                                     |
| --------------------- | -------------------------------------------- |
| `langchain-dev-guide` | Hướng dẫn phát triển LangChain, LangGraph và DeepAgents |
| `langsmith-trace`     | Quy trình truy vấn và debug LangSmith Trace  |

Các skill khác xuất hiện trong output không liên quan đến quy trình chuẩn bị của khóa học, có thể tạm bỏ qua.

#### 2. Cài vào dự án hiện tại

Chạy lệnh sau:

```
npx skills add ob-labs/agentseek --skill langchain-dev-guide --skill langsmith-trace
```

Skills CLI sẽ phát hiện các coding assistant có sẵn trên máy. Theo hướng dẫn, chọn Codex, Claude Code hoặc công cụ bạn đang dùng rồi xác nhận cài đặt.

Bạn cũng có thể chỉ định công cụ trực tiếp. Cài vào Codex:

```
npx skills add ob-labs/agentseek --skill langchain-dev-guide --skill langsmith-trace --agent codex --yes
```

Cài vào Claude Code:

```
npx skills add ob-labs/agentseek --skill langchain-dev-guide --skill langsmith-trace --agent claude-code --yes
```

Chương này dùng cài đặt cấp dự án (project-level), không thêm `--global`. Skill chỉ tác động đến dự án hiện tại, và cũng giúp bạn dễ dàng kiểm tra nội dung sau khi cài rồi mới quyết định có đưa chúng vào version control hay không.

#### 3. Kiểm tra vị trí cài đặt

Liệt kê các skill đã cài trong dự án hiện tại và trong thư mục user:

```
npx skills list
```

Các coding assistant đọc các thư mục khác nhau:

| Coding assistant | Thư mục cấp dự án   | Thư mục global       |
| ---------------- | ------------------- | -------------------- |
| Codex            | `.agents/skills/`   | `~/.agents/skills/`  |
| Claude Code      | `.claude/skills/`   | `~/.claude/skills/`  |
| Cursor           | `.agents/skills/`   | `~/.agents/skills/`  |

Cài cấp dự án là hành vi mặc định. `--global` sẽ ghi vào thư mục cấp user, không ghi vào `.agents/skills/` của dự án hiện tại.

Nếu bạn chọn Codex, có thể kiểm tra entry point của skill:

```
ls .agents/skills/langchain-dev-guide/SKILL.md
ls .agents/skills/langsmith-trace/SKILL.md
```

Nếu bạn chọn Claude Code, hãy thay đường dẫn bằng `.claude/skills/`.

#### 4. Dùng langchain-dev-guide

`langchain-dev-guide` tổng hợp các vấn đề cấu hình và runtime thường gặp khi phát triển trong hệ sinh thái LangChain, chủ yếu bao gồm:

- Model, filesystem, sub-Agent và long-term memory của DeepAgents
- Giao diện tương thích OpenAI và cách tích hợp model nội địa Trung Quốc
- Middleware, streaming output và orchestration đa Agent
- Structured output, Tool Call và các vấn đề runtime context

Nhập một task cụ thể vào coding assistant, và nêu rõ tên skill:

```
Hãy dùng langchain-dev-guide kiểm tra cấu hình model của dự án deepagents/research này.
Khóa học mặc định dùng GLM qua giao diện tương thích OpenAI của SiliconFlow.
Hãy đối chiếu các biến môi trường, và nêu ranh giới tương thích của các capability như Tool Call, reasoning_content.
```

Coding assistant sẽ đọc `langchain-dev-guide/SKILL.md` trước, rồi đọc các tài liệu tham khảo mà nó trích dẫn khi cần. Bạn có thể yêu cầu assistant nêu rõ đã dùng file tham khảo nào để xác nhận skill đã có hiệu lực.

Một ví dụ khác:

```
Hãy dùng langchain-dev-guide để thêm một Middleware tùy chỉnh cho research Agent này.
Kiểm tra thứ tự thực thi của Middleware và quy tắc hợp nhất state_schema trước, rồi mới đưa ra phương án sửa đổi.
```

#### 5. Thực hành: dùng langsmith-trace định vị một lượt gọi chậm (5–10 phút)

Phần này dùng Trace được sinh bởi `deepagents/research` ở chương trước. Sau khi xong, bạn sẽ chỉ ra được research chậm ở đâu, căn cứ phán đoán là gì, và bước tiếp theo tối ưu thế nào.

Xác nhận trước khi bắt đầu:

- Chương trước đã bật `LANGSMITH_TRACING=true`
- `.env` đã set `LANGSMITH_API_KEY` và `LANGSMITH_PROJECT=deepagents-course`
- Có ít nhất một Trace `research` đã hoàn tất trong `deepagents-course` hoặc `default`
- Dự án hiện tại đã cài `langsmith-trace`

##### 5.1 Kiểm tra CLI và xác thực

Trước tiên xác nhận LangSmith CLI có dùng được không.

macOS / Linux / WSL2:

```
command -v langsmith
langsmith --version
```

PowerShell Windows nguyên sinh:

```
if (Get-Command langsmith -ErrorAction SilentlyContinue) {
  langsmith --version
} else {
  Write-Warning "LangSmith CLI chưa được cài; hãy thực hiện bước cài đặt Windows phía dưới trước."
}
```

Nếu lệnh không tồn tại, dùng script cài đặt chính thức của LangSmith CLI.

macOS / Linux / WSL2:

```
curl -fsSL https://cli.langsmith.com/install.sh | sh
```

PowerShell Windows nguyên sinh:

```
irm https://cli.langsmith.com/install.ps1 | iex
```

Sau khi cài xong, đóng và mở lại terminal rồi chạy `langsmith --version`. Nếu vẫn không tìm thấy lệnh, hãy sửa PATH theo output của installer. Script cài đặt và version mới nhất xem tại [repository chính thức của LangSmith CLI](https://github.com/langchain-ai/langsmith-cli).

Package `langsmith` trên PyPI là Python SDK, không cung cấp file thực thi CLI dùng ở đây; đừng dùng `uv tool install langsmith` để cài LangSmith CLI.

LangSmith CLI đọc credentials từ biến môi trường. Hãy load `.env` tại thư mục gốc dự án.

macOS / Linux / WSL2:

```
set -a
source .env
set +a
```

PowerShell Windows nguyên sinh:

```
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
    $value = $matches[2] -replace '^"(.*)"$', '$1'
    Set-Item -Path "Env:$($matches[1])" -Value $value
  }
}
```

Đoạn PowerShell chỉ load các dòng `KEY=value` thường gặp trong `.env` của khóa học và bỏ qua comment cùng các định dạng khác; nó không thực thi `.env` như một script PowerShell.

Xác nhận credentials hợp lệ và tìm project gần đây có run:

```
langsmith --format pretty project list
```

Bạn sẽ thấy `deepagents-course` trong danh sách. Nếu Trace `research` gần nhất đã vào `default`, có thể đổi tên project trong các lệnh phía sau thành `default` để phân tích trực tiếp Trace sẵn có. `LANGSMITH_PROJECT` chỉ ảnh hưởng đến các run trong tương lai; chỉ khi cả hai project đều chưa có Trace `research` hoàn tất mới cần sửa cấu hình và chạy lại câu hỏi research.

Đừng ghi Key thật vào lệnh Shell và đừng dùng `--api-key`. Lệnh có thể lọt vào Shell history, danh sách process hoặc log của coding assistant.

##### 5.2 Tìm Trace đầy đủ

Trước tiên liệt kê các Trace gốc gần đây:

```
langsmith trace list --project deepagents-course --name research --include-metadata --limit 5
```

Copy `trace_id` của node gốc `research` mới nhất có trạng thái hoàn tất, rồi xem cây run đầy đủ:

```
langsmith trace get <trace-id> --project deepagents-course --include-metadata
```

`<trace-id>` là placeholder, hãy thay bằng ID thật trả về ở bước trước. Bạn sẽ thấy node gốc `research`, sub-Agent `research-agent`, các lượt gọi model `ChatOpenAI`, lượt gọi tool `tavily_search`, cùng nhiều lớp bọc middleware.

##### 5.3 Để coding assistant phân tích bottleneck

Nhập vào Codex, Claude Code hoặc coding assistant khác đã cài skill:

```
Hãy dùng langsmith-trace phân tích Trace research đã hoàn thành gần nhất trong LangSmith project vừa xác nhận.
Ưu tiên dùng deepagents-course; nếu Trace nằm trong default thì dùng default.

Hãy xác nhận project và trace_id trước, rồi phân biệt:
1. Luồng research gốc;
2. Sub-Agent research-agent;
3. Lượt gọi model thực tế có run_type=llm;
4. Lượt gọi tool thực tế như tavily_search.

Tìm riêng lượt gọi model leaf chậm nhất và lượt gọi tool thực tế chậm nhất.
Đừng lấy luôn Trace gốc, lớp bọc sub-Agent task hay lớp bọc middleware làm bottleneck.
Với các Run ứng viên, dùng run get --include-io để kiểm tra input, output và error.

Cuối cùng xuất bảng: lượt gọi, loại, thời gian, bằng chứng phán đoán, nguyên nhân khả dĩ, đề xuất bước tiếp theo.
Không xuất API Key hay credentials khác.
```

Skill sẽ thu hẹp phạm vi theo kiểu run trước, đừng xuất input/output của tất cả Run cùng lúc:

```
langsmith run list --trace-ids <trace-id> --project deepagents-course --run-type llm --include-metadata --limit 100
langsmith run list --trace-ids <trace-id> --project deepagents-course --run-type tool --include-metadata --limit 100
```

LangSmith API hiện giới hạn mỗi lần `run list` tối đa 100. Trace research phức tạp có thể vượt số lượng này; hãy lọc bằng `--run-type` trước, cần thì thu hẹp thêm bằng `--name`, tránh kết quả bị cắt cụt hoặc xuất quá nhiều IO ra terminal. Trong kết quả tool, `task` là lớp bọc sub-Agent, đừng coi nó là bottleneck tool thực tế. Hệ phân cấp đầy đủ vẫn lấy `trace get` làm chuẩn.

Sau khi tìm được `run_id` ứng viên, dùng tường minh `--include-io` để xem một lượt gọi:

```
langsmith run get <run-id> --include-io --include-metadata
```

Đừng thay bằng `run get --full`. Ở một số version CLI, `--full` có thể trả về input/output rỗng; dùng tường minh `--include-io` ổn định hơn.

##### 5.4 Kiểm tra kết quả phân tích

Một lần phân tích đạt chuẩn tối thiểu bao gồm:

| Mục kiểm tra        | Tiêu chí hoàn thành                            |
| ------------------- | ---------------------------------------------- |
| Chọn Trace          | Dùng Trace `research` đã hoàn thành gần nhất   |
| Phân biệt tầng cấp | Phân biệt được luồng gốc, sub-Agent, model và tool |
| Bottleneck model    | Tìm được Run leaf `run_type=llm` chậm nhất     |
| Bottleneck tool     | Tìm được Run tool thực tế chậm nhất, ví dụ `tavily_search` |
| Bằng chứng          | Đưa ra `run_id`, thời gian, trạng thái và kết quả kiểm tra input/output |
| Đề xuất             | Đề xuất tương ứng với bằng chứng, chứ không chỉ nói "đổi model nhanh hơn" |

Trace research được đo trong bài gồm 162 Run, 0 lỗi, tổng thời gian khoảng 472,9 giây. Sau khi truy vấn đủ 22 Run model theo kiểu, lượt gọi `ChatOpenAI` leaf chậm nhất khoảng 85,9 giây; sau khi truy vấn đủ 17 Run tool và loại bỏ lớp bọc `task`, tool thực tế chậm nhất là `tavily_search` khoảng 25,1 giây. Kết quả của bạn sẽ thay đổi theo model, mạng, câu hỏi và version template; đừng coi các con số này là kỳ vọng cố định.

Trace có thể lưu prompt, tham số tool và output của model. Nếu bạn xử lý dữ liệu nhạy cảm, có thể đặt `LANGSMITH_HIDE_INPUTS=true` và `LANGSMITH_HIDE_OUTPUTS=true`; khi bật, input/output của Run dùng để phân tích nội dung ở phần này sẽ bị ẩn.

#### 6. Cập nhật skill

Chỉ cập nhật skill trong dự án hiện tại:

```
npx skills update -p
```

Nếu sau này bạn dùng cài đặt global, chỉ cập nhật skill global:

```
npx skills update -g
```

Sau khi cập nhật, chạy lại:

```
npx skills list
```

#### 7. Tùy chọn: cài vào thư mục user

Nếu bạn muốn dùng hai skill này trong mọi dự án, có thể chạy:

```
npx skills add ob-labs/agentseek --skill langchain-dev-guide --skill langsmith-trace --global
```

Cài global phù hợp cho cá nhân dùng lâu dài. Dự án đội nhóm vẫn nên giữ cài đặt cấp dự án, để các skill dự án cần có thể được thành viên khác thấy và dùng.

#### Gỡ skill

Khi không còn cần các skill cấp dự án này, có thể gỡ:

```
npx skills remove langchain-dev-guide langsmith-trace --yes
```

#### Kết quả sau khi hoàn thành chương

Bạn hiện có:

- `langchain-dev-guide` và `langsmith-trace` đã cài trong dự án hiện tại
- Bộ lệnh kiểm tra, cập nhật và gỡ dev skill
- Ranh giới rõ ràng giữa skill của coding assistant và DeepAgents runtime Skill

Tiếp theo, bạn có thể để coding assistant dùng hai skill này chỉnh sửa ứng dụng research được sinh ở chương trước, hoặc học tiếp DeepAgents runtime Skills ở chương 7.

Nguồn tham khảo: [AgentSeek Skills](https://github.com/ob-labs/agentseek/tree/main/skills), [Skills CLI](https://github.com/vercel-labs/skills), [langchain-dev-guide](https://github.com/ob-labs/agentseek/tree/main/skills/langchain-dev-guide), [langsmith-trace](https://github.com/ob-labs/agentseek/tree/main/skills/langsmith-trace), [LangSmith CLI](https://docs.langchain.com/langsmith/langsmith-cli), [LangSmith 数据脱敏](https://docs.langchain.com/langsmith/mask-inputs-outputs).

#### Tài nguyên liên quan

Hướng dẫn phát triển LangChain / DeepAgents — [Video讲解 Bilibili](https://www.bilibili.com/video/BV1GVJP6UEaB/), [Ảnh bài viết Xiaohongshu](http://xhslink.com/o/8b9xPADEwDL)

LangSmith Trace: theo dõi và debug chuỗi gọi — [Video讲解 Bilibili](https://www.bilibili.com/video/BV1xFjA6ZEWB/), [Ảnh bài viết Xiaohongshu](http://xhslink.com/o/1eXpfomXOi6)