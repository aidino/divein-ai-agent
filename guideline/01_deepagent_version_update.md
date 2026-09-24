# Deep Agents v0.7: Harness nhẹ hơn, minh bạch hơn và cấu hình được hơn

> Một Deep Agent đang chạy thực tế sau khi nâng cấp lên v0.7: hóa đơn có thể giảm, cũng có thể không thay đổi rõ rệt; nó có thể tiếp tục hoàn thành task ổn định, cũng có thể đột nhiên không còn sinh Todo. Nguyên nhân là v0.7 đã điều chỉnh phạm vi những quyết định mà Harness mặc định đưa ra thay ứng dụng.

Khóa học này bắt đầu từ Deep Agents 0.5, và các chương trước vẫn giữ lại dấu vết framework tiến hóa dần qua 0.5, 0.6. v0.7 tiếp tục con đường học tập đó và đẩy baseline của khóa học thêm một bước: nó giảm bớt ngữ cảnh chung cố định phải mang theo mỗi lượt, trả các chiến lược như lập kế hoạch về lại cho ứng dụng, và bổ sung đầy đủ khả năng cấu hình cho file tool và Middleware. Bạn đọc mới có thể bắt đầu trực tiếp với bản patch 0.7.x mới nhất; bạn đọc cũ nên hoàn thành các kiểm tra migration của chương này trước rồi mới tiếp tục các thí nghiệm phía sau.

Deep Agents v0.7 gỡ bỏ một loạt scaffolding không còn cần thiết phổ quát: base prompt mặc định trở nên rỗng, mô tả tool rút ngắn, `TodoListMiddleware` đổi sang bật theo nhu cầu. Framework cũng mở khả năng thay thế tại chỗ (in-place) cho Middleware, và điều chỉnh cả năng lực lẫn semantics output của file tool.

Thay đổi về kiến trúc rất rõ: lớp mặc định mỏng hơn, các chiến lược trước đây giấu trong framework giờ cần ứng dụng chọn một cách tường minh.

Chương này lấy [`deepagents==0.7.0` changelog](https://docs.langchain.com/oss/python/releases/changelog#deepagents-v0-7-0) và [blog phát hành Deep Agents v0.7](https://www.langchain.com/blog/deep-agents-v0-7) làm baseline cho hành vi phát hành ban đầu, đồng thời tiếp tục đối chiếu các báo cáo đánh giá, tài liệu chính thức và PR triển khai mà chúng trỏ tới. Trọng tâm là nhận diện ứng dụng bị ảnh hưởng, quyết định có khôi phục default cũ hay không, và xác minh hành vi sau nâng cấp.

Việc học và migration hằng ngày nên cài bản patch 0.7.x hiện tại, đồng thời giới hạn trong cùng một minor version:

```
uv add --upgrade "deepagents>=0.7,<0.8"
uv run python -c "import deepagents; print(deepagents.__version__)"
```

Hãy commit `uv.lock` của dự án, hoặc lưu snapshot môi trường tương đương, mới ghi lại được version chính xác thực tế được resolve. Nếu muốn tái hiện từng mục trong changelog phát hành đầu của v0.7.0, hãy pin version trong một môi trường tạm riêng:

```
uv add "deepagents==0.7.0"
```

Đừng nâng cấp tại chỗ trực tiếp trong môi trường production. v0.7 đồng thời thay đổi Middleware mặc định, giao diện tương thích Backend và output của file tool; chỉ nhìn "import có thành công không" không chứng minh được migration đã xong.

## 1. Trước tiên xác định những chính sách mặc định nào đã thay đổi

Nhìn từ góc độ người dùng, v0.7 có bốn nhóm thay đổi; nhìn từ góc độ kiến trúc, chúng cùng chỉ một hướng.

| Thay đổi bề mặt | Phán đoán thiết kế | Trách nhiệm ứng dụng cần tiếp nhận |
| --------------- | ------------------ | ---------------------------------- |
| Base prompt mặc định rỗng, mô tả tool rút ngắn | Model hiện đại hiểu interface từ tool Schema tốt hơn, không cần đọc lại giải thích kiểu tutorial | Viết rõ system prompt thực sự thuộc về nghiệp vụ, và dùng Trace kiểm tra xung đột và trùng lặp |
| Todo không còn bật mặc định | Lập kế hoạch tường minh không phải lợi ích phổ quát cho mọi task | Quyết định có khôi phục hay không dựa trên độ dài task, khả năng model và nhu cầu UI |
| Middleware cùng tên có thể thay thế tại chỗ | Stack built-in nên cung cấp default hợp lý, nhưng không nên khóa cứng threshold, model và prompt | Quản lý tường minh cấu hình đầy đủ và phạm vi kế thừa của instance thay thế |
| File tool mạnh hơn và có ranh giới hơn | Agent cần xử lý file và thư mục lớn hiệu quả, đồng thời tránh tìm kiếm vô hạn | Rà soát lại delete, ghi đè (overwrite), parse output, permission và truncation kết quả |

Duyệt changelog từng dòng rồi hỏi máy móc "tính năng này tôi có dùng không" rất dễ bỏ qua dependency ngầm. Hãy trả lời các câu hỏi sau trước:

1. Trước đây ứng dụng của tôi phụ thuộc vào những **default ngầm** nào?
2. Default nào vẫn có giá trị trong task của tôi và nên được khôi phục tường minh?
3. Những chỗ nào tiêu thụ **raw text của file tool hoặc giao diện tương thích Backend**?
4. Tôi dùng đánh giá nghiệp vụ nào để chứng minh Harness nhẹ hơn không làm thay đổi hành vi then chốt?

Toàn bộ nội dung phía sau xoay quanh bốn câu hỏi này.

## 2. Hiểu đúng "giảm 65% input Token nền"

Hai con số chính thức đưa ra mô tả những phạm vi khác nhau:

- Mô tả tool Schema của Agent mặc định giảm từ **4.005 Token xuống 2.302 Token**, mức giảm 43%. Trong đó mô tả tool `task` giảm từ 1.664 xuống 389 Token, là khoản cắt giảm đơn lẻ lớn nhất.
- Cộng thêm base prompt rỗng và Todo chuyển thành tùy chọn, input của một lượt đơn giản của Agent mặc định giảm từ **5.395 Token xuống 1.895 Token**, tức input nền giảm khoảng 65%.

Hai con số này cho thấy "chi phí cố định của framework phải mang theo mỗi lượt" giảm rõ rệt, nhưng không thể suy ra "tổng chi phí của bất kỳ ứng dụng nào cũng giảm 65%". Một lượt gọi thật còn bao gồm:

- Tin nhắn người dùng và lịch sử hội thoại
- Skills, Memory và system prompt riêng của ứng dụng
- Tham số và kết quả của các lượt gọi tool
- Trace của sub-Agent
- Summarization và retry khi thất bại
- Cache hit và quy tắc tính phí của nhà cung cấp model

Nếu một task long-range vốn đã có hàng trăm nghìn Token lịch sử và kết quả tool, bớt khoảng 3.500 input Token nền vẫn có giá trị, nhưng tỉ lệ trên tổng chi phí sẽ không là 65%.

### 2.1 Đánh giá end-to-end thể hiện "xu hướng tổng thể", không phải lợi ích đồng nhất

[Hệ thống đánh giá Deep Agents](https://www.langchain.com/blog/how-we-benchmark-deep-agents) mới của chính thức không còn chỉ dựa vào các bài unit nhỏ, mà bao phủ ba loại công việc của Agent:

| Loại đánh giá           | Quan sát gì                                | Vì sao liên quan đến nâng cấp                   |
| ----------------------- | ------------------------------------------ | ----------------------------------------------- |
| Autonomous              | Các task end-to-end như lập trình, phân tích dữ liệu, dùng tool long-range | Kiểm tra sau khi gỡ scaffolding, Agent còn tự chủ hoàn thành công việc nhiều bước không |
| Conversational          | Hội thoại nhiều lượt mô phỏng người dùng tham gia | Kiểm tra prompt mặc định ít hơn có ảnh hưởng đến câu hỏi tiếp theo, việc chọn tool và mục tiêu phiên không |
| Long-context / Retrieval | Truy xuất và tổng hợp câu trả lời trong long context kèm theo task | Kiểm tra Prompt nhẹ hơn có làm model mất năng lực long-context không |

Task đánh giá Harbor đồng thời gồm môi trường chạy, mô tả task và script nghiệm thu. Điểm số dựa trên file Agent chỉnh sửa và trạng thái môi trường, chứ không chỉ dựa vào câu trả lời cuối có "giống đáp án" hay không. Mỗi task còn được chạy lặp lại để giảm dao động ngẫu nhiên do tính không xác định (non-determinism) của Agent.

Trong so sánh chéo version giữa v0.6.12 và v0.7, phía chính thức chạy 36 task, mỗi task 3 rollout, phủ bốn model. Kết quả chính xác có giá trị định hướng hơn nhiều so với "tiết kiệm hơn một cách phổ quát":

| Model                | Reward | Token   | Chi phí  | Cách đọc đúng                                       |
| -------------------- | ------ | ------- | -------- | --------------------------------------------------- |
| `gpt-5.6-luna`       | +3,8%  | -35,5%  | -15,2%   | Token và chi phí giảm rõ nhất; thay đổi Reward vẫn nằm trong khoảng không chắc chắn |
| `gemini-3.6-flash`   | -6,7%  | -4,7%   | -8,1%    | Cả ba khoảng tin cậy đều vượt qua số 0, không thể căn cứ vào đây mà khẳng định chắc chắn tốt hơn hay tệ hơn |
| `claude-sonnet-4-6`  | +3,1%  | +31,3%  | +36,8%   | Hai task tự trị độ khó cao cho trace dài hơn, triệt tiêu phần tiết kiệm từ base Prompt |
| `claude-opus-4-8`    | -5,1%  | -25,4%  | -16,4%   | Token giảm rõ rệt; thay đổi Reward và chi phí vẫn không thể coi là kết luận phổ quát |

Khoảng tin cậy Reward của tất cả model đều vượt qua số 0, nên kết luận chính thức là "chất lượng tổng thể không có regression đo được", không thể viết lại thành "v0.7 làm mọi model tăng chất lượng". Mức giảm Token của Luna và Opus rõ hơn, mức giảm chi phí của Luna cũng rõ hơn; kết quả của Sonnet cho thấy overhead nền thấp hơn không bảo đảm trace của Agent ngắn hơn.

### 2.2 Hướng dẫn thực tế cho dự án

Nghiệm thu nâng cấp tối thiểu phải ghi chép tách biệt ba loại chỉ số:

1. **Overhead nền**: input tokens của lượt đơn giản, xác minh Harness mặc định thực sự nhẹ đi.
2. **Hiệu quả trace**: số lượt model, số lượt gọi tool, số lượt gọi sub-Agent và số retry cần để hoàn thành cùng một task.
3. **Kết quả nghiệp vụ**: task có qua nghiệm thu thật hay không, chứ không phải văn bản cuối trông có vẻ hợp lý hay không.

Nếu chỉ so sánh mục đầu tiên, rất dễ rút ra kết luận sai trong các kịch bản kiểu Sonnet. Quyết định production nên dựa trên model, prompt, tập tool và phân bố task của chính bạn.

## 3. Prompt mặc định rỗng: tách chỉ dẫn nghiệp vụ khỏi interface của tool

v0.7 gỡ bỏ base prompt chung mà Deep Agents trước đây thêm vào, đồng thời xóa các hướng dẫn sử dụng Middleware trùng lặp với tool Schema. Cái bị xóa ở đây là "cách làm việc chung do framework viết hộ", không phải các thông tin chỉ biết lúc runtime như Skills, Memory hay routing đường dẫn file.

Đằng sau thay đổi này là hai nguyên tắc context engineering:

- **Interface hơn ví dụ**: tên tool, kiểu tham số, enum và ràng buộc rõ ràng có thể diễn đạt trực tiếp các hành động khả dụng; quá nhiều ví dụ few-shot ngược lại có thể giới hạn model vào đúng đường khám phá mà ví dụ thể hiện.
- **Tránh lặp lại**: cùng một ràng buộc viết vào cả system prompt lẫn mô tả tool sẽ không tự động nhận được mức tuân thủ gấp đôi, nhưng lại tăng vĩnh viễn input mỗi lượt và tăng xác suất xung đột.

Hướng này nhất quán với điều Anthropic chia sẻ trong [kinh nghiệm context engineering cho thế hệ model mới](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models): họ tinh giản mạnh system prompt của Claude Code cho các model mạnh hơn, và nhấn mạnh dẫn dắt model qua thiết kế interface thay vì qua hàng loạt ví dụ tool call.

### 3.1 System prompt tùy chỉnh giờ "có tiếng nói quyết định" hơn

Trước đây, `system_prompt` ứng dụng truyền vào sẽ cùng base prompt của framework hợp thành ngữ cảnh. Ngay cả khi hai đoạn không xung đột trực tiếp, chúng vẫn có thể quy định lặp giọng điệu, lập kế hoạch hay cách làm việc. Lớp nền mặc định của v0.7 rỗng, nên ý nghĩa prompt của ứng dụng trực tiếp hơn:

```
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=model,
    system_prompt=(
        "Bạn là trợ lý migration code. Hãy đọc ràng buộc version và điểm vào test trong repository trước, "
        "chỉ sửa các file liên quan đến mục tiêu migration; sau khi xong hãy chạy test sẵn có của dự án, "
        "và báo cáo rõ những phần chưa xác minh được."
    ),
)
```

Đừng vì "bản cũ có một đoạn base Prompt dài" mà copy toàn bộ nội dung cũ vào ứng dụng. Hãy bắt đầu từ những ràng buộc task thực sự cần, rồi bổ sung qua các case thất bại. Nếu không, bạn sẽ mang trở lại đúng chi phí cố định và xung đột tiềm ẩn mà v0.7 vừa gỡ bỏ.

Có thể chẩn đoán khác biệt hành vi sau nâng cấp theo trình tự sau:

1. Kiểm tra tool Schema đã diễn đạt ràng buộc chưa, đừng vội dán lặp vào system prompt.
2. Kiểm tra ứng dụng có phụ thuộc các hành vi chung trong base Prompt cũ không, ví dụ chủ động xác minh, báo cáo tiến độ hoặc hỏi ít.
3. Chỉ bổ sung các quy tắc ảnh hưởng đến kết quả nghiệp vụ, và dựng mẫu đánh giá cho chúng.
4. Quan sát LangSmith Trace, xác nhận prompt mới không khiến model sinh thêm giải thích, lập kế hoạch hay lặp vòng.

## 4. Todo chuyển thành tùy chọn: lập kế hoạch là một chiến lược, không phải phí cố định

`create_deep_agent()` ở v0.7 không còn cài `TodoListMiddleware` mặc định. Khi không bật tường minh, ba thứ sau biến mất cùng nhau:

- Tool `write_todos`
- State channel `todos`
- Prompt lập kế hoạch Todo

Sau khi so sánh trên GPT-5.6 Terra, Claude Opus 4.8 và GLM 5.2, phía chính thức không quan sát thấy Todo mang lại mức tăng độ chính xác có ý nghĩa thống kê; Token sử dụng của hai trong ba model còn cao hơn. Vì vậy framework không còn bắt mọi lượt gọi trả phí cho lập kế hoạch tường minh.

Điều này không đồng nghĩa "Todo vô dụng". Giá trị của nó tùy thuộc vào task và sản phẩm:

| Tình huống                               | Khuyến nghị                                 | Lý do                                        |
| ---------------------------------------- | -------------------------------------------- | -------------------------------------------- |
| Hỏi đáp một bước, lượt gọi tool ngắn     | Giữ tắt                                      | Bản thân kế hoạch có thể còn dài hơn task    |
| Task long-range, nhiều giai đoạn, dễ sót bước | Bật                                     | Trạng thái tường minh giúp model giữ mục tiêu qua nhiều lượt |
| Model yếu hơn hoặc dễ mất dòng chính     | Làm đánh giá A/B trước, thường đáng thử      | Model yếu phụ thuộc scaffolding bên ngoài nhiều hơn |
| UI cần hiển thị kế hoạch, bước hiện tại và tiến độ | Bật                             | Todo đồng thời là giao thức trạng thái sản phẩm, không chỉ là prompt cho model |
| Batch xử lý nền, chỉ quan tâm sản phẩm cuối | Tắt mặc định, rồi quyết định bằng đánh giá | Người dùng không cần kế hoạch hiển thị; tránh chi phí cố định trước |

Khi cần khôi phục, import từ LangChain Middleware:

```
from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware

agent = create_deep_agent(
    model=model,
    middleware=[TodoListMiddleware()],
)
```

### 4.1 Chú ý phạm vi kế thừa của Todo

Cài đặt của v0.7 cố ý phân biệt hai loại sub-Agent:

- Sub-Agent `general-purpose` mặc định kế thừa instance Todo mà main Agent truyền vào tường minh.
- `subagents=[...]` kiểu khai báo (declarative) có stack Middleware độc lập, không tự kế thừa Todo của main Agent, cần bật trong spec riêng.

```
from langchain.agents.middleware import TodoListMiddleware

researcher = {
    "name": "researcher",
    "description": "Thực hiện các research task cần nhiều bước truy xuất và xác minh",
    "system_prompt": "Hãy lập kế hoạch các bước thu thập chứng cứ trước, rồi hoàn thành từng mục và đánh dấu trạng thái.",
    "middleware": [TodoListMiddleware()],
}

agent = create_deep_agent(
    model=model,
    subagents=[researcher],
)
```

OpenAI Codex harness profile là ngoại lệ: system prompt của nó phụ thuộc tường minh vào `write_todos`, nên profile tự động giữ Todo. Khi migration đừng chỉ đoán tập tool theo version package; hãy lấy profile thực tế và Trace làm chuẩn.

Nếu Todo được dùng cho tiến độ frontend, test nâng cấp phải phủ state channel, chứ không thể chỉ xác nhận câu trả lời cuối vẫn được sinh. Chương 4 [Lập kế hoạch và phân rã task](https://datawhalechina.github.io/deepagents-in-action/chapters/ch04-task-planning/) giải thích cơ chế hoạt động của Todo; phần này quan tâm cách quyết định có trả phí cho nó sau v0.7 hay không.

## 5. Ghi đè Middleware tại chỗ: khả năng cấu hình không đồng nghĩa cấu hình tự động hợp nhất

Trước đây, nếu ứng dụng truyền một `SummarizationMiddleware` tùy chỉnh vào `middleware=`, framework sẽ báo lỗi trùng tên vì nó trùng tên với instance mặc định. v0.7 đổi sang khớp theo `.name`: khi instance tùy chỉnh trùng tên với một Middleware built-in, nó thay thế instance mặc định ngay tại chỗ.

Điều này cho phép ứng dụng tinh chỉnh model tóm tắt, threshold kích hoạt và prompt mà không phải tháo cả Harness:

```
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.middleware import SummarizationMiddleware

backend = StateBackend()

agent = create_deep_agent(
    model=model,
    backend=backend,
    middleware=[
        SummarizationMiddleware(
            model=summary_model,
            backend=backend,
            trigger=("fraction", 0.5),
            keep=("messages", 20),
            summary_prompt=(
                "Tóm tắt phần hội thoại trước đó, giữ nguyên đường dẫn file, "
                "các quyết định đã chốt, việc chưa xong và nguyên nhân thất bại."
            ),
        )
    ],
)
```

Tóm tắt mặc định thường kích hoạt khi context window dùng đến khoảng 85%. Với các ứng dụng nhiều kết quả tool, hội thoại dài dễ gặp context rot, kéo sớm xuống 50% có thể ổn định hơn, nhưng tăng tần suất tóm tắt và rủi ro mất thông tin. Threshold không phải càng thấp càng tốt; cần đồng thời kiểm tra chi phí các lượt tóm tắt và tỉ lệ thành công task phía sau.

### 5.1 Quy tắc ghi đè và quy tắc kế thừa

Theo [cài đặt ghi đè Middleware](https://github.com/langchain-ai/deepagents/pull/4251), quy tắc của v0.7 là:

1. `.name` trùng với instance built-in: thay thế ngay tại chỗ, giữ nguyên thứ tự tương đối của stack.
2. Không có instance mặc định cùng tên: chèn sau các Middleware lõi và trước phần đuôi profile / prompt caching / memory.
3. Sub-Agent `general-purpose` mặc định kế thừa phần ghi đè của main Agent lên instance mặc định.
4. Sub-Agent kiểu khai báo tự dựng stack riêng, cần cấu hình trong spec của từng cái.
5. Một số Middleware bắt buộc nằm ở đuôi vẫn giữ thứ tự định sẵn, ví dụ logic loại trừ tool phải chạy sau khi tool được inject xong.

### 5.2 Bẫy dễ bị bỏ qua nhất: đây là thay thế cả instance

Ghi đè cùng tên không phải merge cấp trường (field-level). Sau khi truyền `FilesystemMiddleware` hay `SummarizationMiddleware` tùy chỉnh, framework sẽ không bổ từng trường Backend, mô tả tool, trạng thái permission hay tham số khởi tạo khác từ instance mặc định vào instance mới.

Vì vậy hãy tuân theo hai quy tắc:

- Dùng chung một instance Backend, tránh main Agent và Middleware thực tế đọc/ghi hai không gian file khác nhau.
- Xem instance thay thế như một cấu hình hoàn chỉnh để rà soát lại, đừng chỉ chú ý đúng một trường mình muốn sửa.

Trong `deepagents==0.7.0`, file permission do framework inject vào `FilesystemMiddleware` mặc định qua cấu hình private. Nếu ứng dụng vừa dùng `permissions=` cấp ngoài cùng (top-level), vừa thay cả file Middleware, không thể giả định các quy tắc từ chối tự động hợp nhất vào instance mới. Cách an toàn hơn là nâng cấp lên bản patch 0.7.x mới đã được kiểm chứng, tránh phụ thuộc tham số private, và làm regression test bằng các lượt gọi allow/denied thật. Tool biến mất khỏi giao diện model không có nghĩa ranh giới permission vẫn còn hiệu lực.

## 6. File tool: hiệu quả hơn, nhưng cũng càng cần rà soát lại side effect

Filesystem là tầng quản lý ngữ cảnh của Deep Agents. v0.7 vừa bổ sung năng lực, vừa đặt ranh giới cho tìm kiếm thư mục lớn.

| Thay đổi                | Hành vi v0.7                                        | Tác động lên ứng dụng hiện có                |
| ----------------------- | --------------------------------------------------- | -------------------------------------------- |
| `write_file`            | Khi đích đã tồn tại thì ghi đè toàn bộ ngay        | Logic bảo vệ cũ kiểu "đã tồn tại thì báo lỗi" sẽ mất tác dụng |
| `delete`                | Gia nhập file tool mặc định, xóa được file hoặc xóa thư mục đệ quy | Mặt tool thêm side effect rủi ro cao, cần permission, phê duyệt hoặc allowlist |
| Phân trang `read_file`  | Trả về tổng số dòng, số dòng còn lại và `offset` tiếp theo | Agent nhảy thẳng tới trang sau hoặc cuối file, giảm đọc lặp mù quáng |
| `grep` / `glob` timeout | Trả về các kết quả hợp lệ đã tìm được và đánh dấu `truncated` | "Thành công" có thể chỉ là thành công một phần; bên gọi phải giữ semantics không đầy đủ |
| Số match của `grep`     | Tool Agent mặc định tối đa 1.000 match và tiêu thụ streaming output `rg` local | Tránh chiếm vô hạn memory và context ở repo lớn; query rộng cần chủ động thu hẹp |
| `ls` / `glob` rỗng      | Text thành `No files found`, không còn là `[]`      | Code parse raw output cần sửa lại            |
| Cột số dòng `read_file` | Sau số dòng dùng hai dấu cách, không còn độ rộng cố định cộng Tab | Parser cắt theo Tab hoặc mô phỏng `cat -n` sẽ hỏng |

### 6.1 Trách nhiệm giữa ghi đè và chỉnh sửa chính xác rõ ràng hơn

Semantics khuyến nghị hiện nay:

- Viết lại toàn bộ file: dùng `write_file`
- Chỉ sửa một phần: `read_file` trước, rồi dùng `edit_file` để thay thế chuỗi chính xác

Cách này tránh việc gửi cả file cũ về lại model làm `edit_file.old_string` chỉ để viết lại toàn bộ, giảm Token không cần thiết. Nhưng nó cũng gỡ bỏ một lớp bảo vệ chống ghi đè nhầm. Với các đường dẫn nhạy cảm như cấu hình, credentials, script production, đừng dựa vào hành vi báo lỗi cũ; hãy dùng tường minh `FilesystemPermission`, HITL hoặc bộ tool chỉ đọc.

### 6.2 `delete` là thao tác ghi, và xóa thư mục kiểu tất cả hoặc không

Backend hỗ trợ xóa sẽ expose `delete` cho Agent. Khi xóa thư mục đệ quy, tầng permission kiểm tra đích và toàn bộ đường dẫn con cháu: chỉ cần một đường dẫn bất kỳ trúng quy tắc từ chối, cả thao tác xóa không được thực hiện, thay vì để lại một cây thư mục xóa dở. Symlink chỉ xóa chính link, không đi theo đến đích.

Nếu ứng dụng không cần xóa, theo nguyên tắc least privilege thì đừng expose nó:

```
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.middleware import FilesystemMiddleware

backend = StateBackend()

agent = create_deep_agent(
    model=model,
    backend=backend,
    middleware=[
        FilesystemMiddleware(
            backend=backend,
            tools=["read_file", "ls", "glob", "grep"],
        )
    ],
)
```

Allowlist này chỉ kiểm soát tám file tool built-in, không xóa các tool tùy chỉnh của ứng dụng. `read_file` là năng lực bắt buộc của `FilesystemMiddleware`, không thể loại khỏi danh sách; `execute` và `delete` vẫn tiếp tục bị giới hạn bởi năng lực Backend — allowlist chỉ thu hẹp được, không thể biến ra năng lực Backend không hỗ trợ.

Các bản sửa sau của v0.7 còn bảo đảm tool bị loại sẽ được gỡ khỏi registry `ToolNode`, chứ không chỉ ẩn với model. Phần ghi đè cùng tên của main Agent sẽ truyền cho sub-Agent `general-purpose` mặc định; sub-Agent kiểu khai báo vẫn phải giới hạn riêng.

Tool allowlist giải quyết "model có thể gọi những tool built-in nào", không phải toàn bộ kiểm soát truy cập file. Ranh giới của quy tắc cấp đường dẫn, Shell, tool tùy chỉnh và MCP xem tại [Chương 11: Filesystem permission](https://datawhalechina.github.io/deepagents-in-action/chapters/ch11-filesystem-permissions/).

### 6.3 Kết quả tìm kiếm một phần không phải là lỗi, nhưng cũng không phải tập đầy đủ

Trước đây `grep` / `glob` trên thư mục lớn có thể timeout, treo, hoặc vứt mất các match đã tìm được. v0.7 trả về các match hiện có, dùng `truncated=True` biểu thị kết quả chưa đầy đủ. Với tool Agent-facing, kết quả một phần sau timeout có thể là `ToolMessage` thành công, và model nhận gợi ý "thu hẹp đường dẫn hoặc pattern".

Ứng dụng tiêu thụ trực tiếp kết quả Backend cần phân biệt rõ:

```
result = backend.grep("TODO", path="/workspace")

if result.error:
    raise RuntimeError(result.error)

for match in result.matches or []:
    consume(match)

if result.truncated:
    schedule_narrower_search()
```

Không thể suy từ "không có exception" rằng tìm kiếm đã đầy đủ, cũng không được vì `truncated=True` mà vứt các match hợp lệ đã trả về. `CompositeBackend` sẽ lan truyền `truncated=True` khi bất kỳ kết quả routing nào chưa đầy đủ.

Giới hạn 1.000 match của `grep` là default hướng model của `FilesystemMiddleware`, model có thể điều chỉnh qua `max_count`; khi gọi trực tiếp Backend, mặc định vẫn là không giới hạn. `context_lines` ở v0.7.0 ban đầu chỉ có trong interface gọi trực tiếp của `FilesystemBackend.grep()` local, và không đồng thời trở thành tham số thống nhất cho mọi Backend và tool của model. Đừng thấy changelog ghi "context lines tùy chọn" mà coi mọi `grep` Agent-facing đều hỗ trợ cùng một Schema.

### 6.4 Metadata phân trang tối ưu trace, không chỉ là định dạng output

Với `read_file(offset=..., limit=...)`, khi không có metadata phân trang, model phải đoán file còn nội dung không và trang sau bắt đầu từ đâu. Phần đuôi của v0.7 báo dải dòng đã đọc, tổng số dòng, số dòng còn lại và `offset` tiếp theo.

Trong đánh giá chính thức trên file 301 dòng, cả hai model đều giảm ổn định số lần đọc xuống hai và nhảy thẳng tới cuối file. Thay đổi loại này giải thích vì sao tối ưu Harness không thể chỉ nhìn Prompt Token: phản hồi tool tốt hơn thay đổi cả trace gọi.

## 7. v0.6 → v0.7: các thay đổi tương thích có thể chặn nâng cấp

Todo là breaking change rõ nhất, nhưng không phải duy nhất. Tầng tương thích Backend và parse raw output dễ bộc lộ vấn đề hơn sau khi đã lên production.

### 7.1 Backend Factory bị gỡ bỏ

Backend Factory đã deprecated từ v0.5 nay chính thức bị xóa ở v0.7. `create_deep_agent()` giờ nhận instance `BackendProtocol` cụ thể, thay vì callable tạo Backend theo runtime.

```
# v0.6.x: cách viết tương thích cũ
agent = create_deep_agent(
    backend=lambda runtime: StoreBackend(),
    store=store,
)
```

Nên migration sang instance tường minh, và cấu hình namespace cho `StoreBackend`:

```
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend

backend = StoreBackend(
    namespace=lambda runtime: (runtime.server_info.user.identity,),
)

agent = create_deep_agent(
    model=model,
    backend=backend,
    store=store,
)
```

Thay đổi này không chỉ là siết kiểu (type). assistant-id namespace fallback ngầm trước đây bị gỡ; ứng dụng phải làm rõ file thuộc user, tenant hay phạm vi nghiệp vụ nào. Thiết kế namespace sai có thể dẫn tới đọc chéo user; đừng nhét đại một hằng số chỉ để pass type check.

Đồng thời cần xử lý các mục tương thích sau:

- Xóa usage của `BackendFactory`, `BACKEND_TYPES`, `FileFormat` và `Unset`
- Xóa tham số cũ `StateBackend(runtime=...)`, `StoreBackend(runtime=...)`
- Migration `ls_info`, `glob_info`, `grep_raw` và interface `read()` thuần chuỗi cũ
- Dùng API `ls` / `glob` / `grep` / `ReadResult` hiện tại
- Xóa `SummarizationMiddleware(history_path_prefix=...)`; việc offload lịch sử đổi sang dùng Backend đã cấu hình
- Nắm rõ `FilesystemBackend` và `LocalShellBackend` mặc định `virtual_mode=True`

`FileData.content` của file mới dùng string. `list[str]` do version cũ persist vẫn đọc được, và sẽ được chuyển đổi ở lần ghi đè hoặc chỉnh sửa kế tiếp, nên không cần viết lại toàn bộ file sẵn có một lần chỉ vì nâng cấp; nhưng serializer và Backend tùy chỉnh nên chấp nhận đồng thời dữ liệu thời kỳ migration.

### 7.2 Parser output tool thô phải được rà riêng

Nếu ứng dụng chỉ trả kết quả tool về lại model, thay đổi format thường do model tự thích nghi. Nếu ứng dụng tự parse `ToolMessage.content`, các cách viết sau đều đáng kiểm tra:

- So kết quả thư mục rỗng với chuỗi `"[]"`
- Chạy `split("\t", 1)` cho từng dòng `read_file`
- Giả định số dòng luôn chiếm độ rộng cố định
- Coi `ToolMessage.status == "success"` là tìm kiếm đã đầy đủ
- Giả định `write_file` chắc chắn thất bại khi file đã tồn tại

Với logic tiêu thụ bằng máy, ưu tiên kết quả có cấu trúc của Backend; đừng coi format text dành cho model đọc là một giao thức ổn định.

### 7.3 Quét tĩnh trước, rồi chạy test migration thật

Có thể bắt đầu từ vài nhóm tìm kiếm sau:

```
rg -n 'BackendFactory|BACKEND_TYPES|FileFormat|Unset|history_path_prefix' .
rg -n 'ls_info|glob_info|grep_raw' .
rg -n 'backend\s*=\s*(lambda|[A-Za-z_][A-Za-z0-9_]*_factory)' .
rg -n 'split\("\\t"|cat -n|No files found|write_file' .
```

Kết quả tìm kiếm không phải bằng chứng migration hoàn tất. Nó chỉ tìm ra các symbol cũ phổ biến, không tìm được dependency ngầm của code nghiệp vụ vào Todo state, sự tồn tại của tool hay semantics lỗi.

## 8. Hai nhóm năng lực "quan tâm theo nhu cầu"

Các cập nhật dưới đây có giá trị, nhưng không nên chiếm hết sự chú ý migration của mọi độc giả.

### 8.1 Prompt Caching cấp Provider

- Người dùng AWS Bedrock có thể dùng hỗ trợ Prompt caching qua `deepagents[aws]`.
- Khi cài version tương thích của `langchain-fireworks`, Deep Agents tự động thêm Fireworks prompt-cache session affinity cho main Agent và sub-Agent.

Chúng tối ưu việc tái sử dụng cache của provider cụ thể, không thay đổi cách gọi chung cho mọi model. Khi nghiệm thu, hãy kiểm tra Token đọc/ghi cache, session / thread affinity và hóa đơn thật, thay vì chỉ xác nhận Middleware đã load.

### 8.2 NVIDIA Nemotron 3 Ultra Harness Profile

v0.7 cung cấp Harness profile built-in cho Nemotron 3 Ultra, phủ các điểm vào như NVIDIA / ChatNVIDIA, Baseten, Fireworks, OpenRouter, Nebius và Together, kèm fix tương thích tool call, kiểm soát vòng lặp, bảo vệ final answer và đánh dấu NIM app-origin.

Loại cài đặt này đặt các khác biệt riêng của model vào Harness profile; quy tắc nghiệp vụ vẫn giữ tại chỗ gọi của ứng dụng. Nếu không dùng Nemotron, phần này không chặn nâng cấp; nếu dùng, cần chú ý thêm các vòng sửa lỗi có thể tăng do profile, và Trace sau khi tool call sai được tự động sửa.

## 9. Nâng cấp từ baseline 0.5/0.6 của khóa học lên 0.7

Nếu bạn đã chạy thông các ví dụ đầu khóa học, không cần làm lại từ đầu. Giữ nguyên task, input và Trace cũ làm nhóm đối chứng, rồi nâng cấp theo bảy bước dưới đây; chính các kết quả cũ này giúp bạn phán đoán v0.7 giảm chi phí cố định hay thay đổi hành vi thật.

### Bước 1: Ghi lại baseline v0.6

Chọn task đại diện cho phân bố production, tối thiểu phủ:

- Một task hỏi đáp ngắn hoặc dùng một tool
- Một task long-range nhiều bước
- Một task có gọi sub-Agent
- Một task đọc phân trang file lớn hoặc tìm kiếm thư mục lớn
- Một task bị từ chối quyền hoặc cần phê duyệt thủ công (HITL)

Lưu tỉ lệ thành công, input / output Token, số lượt model, số lượt gọi tool, số sub-Agent, độ trễ và chi phí.

### Bước 2: Nâng cấp lên 0.7.x hiện tại trong môi trường cách ly

Dùng `deepagents>=0.7,<0.8` để lấy bản patch hiện tại và khóa snapshot dependency của dự án; chỉ khi điều tra một hành vi phát hành ban đầu nào đó mới dùng `==0.7.0` tái hiện riêng. Đừng để "nâng cấp Deep Agents" trộn lẫn với "đồng thời nâng cấp model, prompt và tool nghiệp vụ" trong cùng một đợt thay đổi.

### Bước 3: Migration các API sẽ báo lỗi trực tiếp

Xử lý Backend factory, Store namespace tường minh, các symbol bị gỡ, `history_path_prefix` và method Backend cũ. Mục tiêu giai đoạn này là để ứng dụng khởi tạo và gọi cơ bản được.

### Bước 4: Tường minh hóa từng chính sách mặc định vốn phụ thuộc trước đây

Làm rõ:

- Có cần Todo không? Main Agent và từng sub-Agent khai báo có nhất quán không?
- System prompt tùy chỉnh có thiếu các hành vi nghiệp vụ then chốt mà lớp mặc định cũ từng cung cấp không?
- Có cần ghi đè model, threshold hay prompt của Summarization không?
- `delete` và ghi đè có phù hợp với mô hình permission không?
- File tool có nên thu hẹp bằng allowlist không?

### Bước 5: Viết lại test parse raw output

Thêm các mẫu: thư mục rỗng, file thụt đầu bằng Tab, file phân trang, tìm kiếm bị cắt cụt, ghi đè file đã tồn tại, từ chối xóa đệ quy. Test riêng kết quả Backend có cấu trúc và text Agent-facing; đừng trộn thành một giao thức.

### Bước 6: So sánh cùng task trong LangSmith

So sánh từng Trace v0.6 và v0.7:

| Quan sát                   | Tín hiệu bất thường                     | Hành động khả dĩ                                        |
| -------------------------- | ---------------------------------------- | -------------------------------------------------------- |
| Input tokens lượt đầu      | Không giảm rõ rệt                        | Kiểm tra xem Prompt ứng dụng, Skills, Memory hay mô tả tool có đang chiếm phần chủ đạo |
| Số lượt model              | Tăng rõ rệt                              | Kiểm tra việc gỡ Todo, mô tả tool quá ngắn hoặc model vào vòng lặp |
| `write_todos` / `todos`    | UI phụ thuộc nhưng đã biến mất           | Khôi phục tường minh `TodoListMiddleware`                 |
| Điểm kích hoạt Summarization | Quá muộn gây context rot, hoặc quá sớm mất thông tin | Dùng ghi đè cùng tên để chỉnh `trigger`, `keep` và prompt tóm tắt |
| Tìm kiếm file              | Vẫn kết luận thẳng sau `truncated`       | Dẫn model thu hẹp đường dẫn, hoặc để bên gọi tiếp tục tìm theo mảnh |
| Side effect file           | Xuất hiện ghi đè hoặc xóa ngoài ý muốn   | Thu hẹp tool, tăng cường permission đường dẫn hoặc thêm HITL |

### Bước 7: Tăng dần traffic, để nghiệm thu nghiệp vụ quyết định có tiếp tục hay không

Trước hết cho một phần traffic vào v0.7, so sánh tỉ lệ thành công và chi phí của cùng loại task. Token nền giảm là tín hiệu tốt, nhưng chỉ khi kết quả nghiệp vụ ổn định và trace không phình bất thường thì migration mới thực sự hoàn tất.

## 10. Bảng quyết định cuối cùng

| Nếu ứng dụng của bạn…                          | Hành động khuyến nghị của v0.7                      |
| ---------------------------------------------- | ----------------------------------------------------- |
| Chỉ làm task ngắn, không có UI tiến độ         | Giữ Todo tắt, tận hưởng lớp mặc định nhẹ hơn         |
| Chạy task long-range hoặc model yếu hơn        | Bật Todo tường minh, và xác minh lợi ích bằng đánh giá nghiệp vụ |
| Dùng tóm tắt hội thoại                         | Chỉnh threshold bằng `SummarizationMiddleware` cùng tên, nhưng xem nó là cấu hình của instance hoàn chỉnh |
| Parse raw text của file tool                   | Liệt kê migration output format là blocker, ưu tiên chuyển sang kết quả có cấu trúc |
| Expose filesystem thật                         | Rà soát `delete`, ghi đè, allowlist, permission đường dẫn và HITL |
| Dùng StoreBackend                              | Gỡ factory, thiết kế namespace tường minh, và test cô lập tenant |
| Phụ thuộc cache của Provider hoặc Nemotron     | Xác minh Trace và hóa đơn của profile / integration tương ứng, đừng coi là lợi ích phổ quát |

Giá trị thực dụng của v0.7 nằm ở việc vạch lại ranh giới: lớp mặc định giữ nhẹ, interface tool diễn đạt năng lực, ứng dụng chọn chiến lược, đánh giá kiểm tra kết quả. Khi model và task tiếp tục thay đổi, sự phân công này dễ bảo trì hơn một system prompt chung không ngừng phình to.

## Tài liệu tham khảo

- [Blog phát hành Deep Agents v0.7](https://www.langchain.com/blog/deep-agents-v0-7)
- [`deepagents` v0.7.0 changelog và lưu ý migration](https://docs.langchain.com/oss/python/releases/changelog#deepagents-v0-7-0)
- [How we benchmark Deep Agents](https://www.langchain.com/blog/how-we-benchmark-deep-agents)
- [Customize Deep Agents: ghi đè Middleware](https://docs.langchain.com/oss/python/deepagents/customization#override-a-default-middleware-instance)
- [Deep Agents Overview: Task planning](https://docs.langchain.com/oss/python/deepagents/overview#task-planning)
- [Deep Agents Overview: Virtual filesystem access](https://docs.langchain.com/oss/python/deepagents/overview#virtual-filesystem-access)
- [PR #5009: tinh giản mô tả tool built-in và đánh giá chéo model](https://github.com/langchain-ai/deepagents/pull/5009)
- [PR #4929: Todo chuyển thành opt-in và kết quả thí nghiệm đầy đủ](https://github.com/langchain-ai/deepagents/pull/4929)
- [PR #4251: ghi đè Middleware mặc định theo tên](https://github.com/langchain-ai/deepagents/pull/4251)
- [PR #4541: gỡ tầng tương thích Backend](https://github.com/langchain-ai/deepagents/pull/4541)
- [PR #4109: `write_file` hỗ trợ ghi đè](https://github.com/langchain-ai/deepagents/pull/4109)
- [PR #4540: metadata phân trang `read_file`](https://github.com/langchain-ai/deepagents/pull/4540)
- [PR #4063: kết quả một phần của `grep` / `glob` và `truncated`](https://github.com/langchain-ai/deepagents/pull/4063)
- [PR #4570: giới hạn match `grep` và streaming output](https://github.com/langchain-ai/deepagents/pull/4570)
- [PR #4706: context lines của `grep` trên Backend local](https://github.com/langchain-ai/deepagents/pull/4706)
- [PR #3851: xóa đệ quy và semantics permission](https://github.com/langchain-ai/deepagents/pull/3851)
- [PR #4325: allowlist file tool](https://github.com/langchain-ai/deepagents/pull/4325)
- [PR #4698: tool bị loại không thể thực thi](https://github.com/langchain-ai/deepagents/pull/4698)

## Tài nguyên liên quan

Cập nhật version Deep Agents v0.7 — [Video讲解 Bilibili](https://www.bilibili.com/video/BV1gPtf6XELh/), [Ảnh bài viết Xiaohongshu](https://xhslink.cn/o/9ei512nEQph)
