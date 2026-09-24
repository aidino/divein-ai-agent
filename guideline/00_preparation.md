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