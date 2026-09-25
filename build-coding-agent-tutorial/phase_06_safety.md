# Phase 6: Safety & Permissions — Bảo vệ workspace

> **Mục tiêu**: Xây dựng hàng rào bảo mật nhiều lớp (Multi-layer Security) cho Coding Agent: kiểm soát quyền truy cập hệ thống tập tin bằng `FilesystemPermission`, áp dụng quy tắc "First-Match-Wins", hóa giải "Bẫy Default-Allow", và tích hợp Human-in-the-Loop (HITL) để xin xác nhận của con người trước khi thực hiện các hành động nguy hiểm.
>
> **Thời gian ước tính**: 2 - 2.5 giờ
>
> **Prerequisites**: Hoàn thành [Phase 5: Sub-agents](phase_05_subagents.md).

---

## 1. Tổng quan & Lý thuyết cốt lõi

### 1.1 Mô hình hiểm họa an ninh (Threat Model) của Coding Agent
Một khi bạn cấp quyền cho Agent đọc, sửa và xóa file, hệ thống của bạn đối mặt với 4 rủi ro an ninh nghiêm trọng:
1. **Rò rỉ bí mật (Secret Exposure)**: Agent đọc file `.env`, `.git/config`, hoặc SSH private key và vô tình gửi các API key, database credentials này lên API của LLM.
2. **Hủy hoại mã nguồn (Destructive Deletion)**: Agent gọi nhầm lệnh `delete` xóa sạch toàn bộ thư mục `src/` hoặc cấu hình git.
3. **Sửa đổi file hệ thống hoặc hạ tầng CI/CD**: Agent sửa đổi file `Dockerfile`, `.github/workflows/deploy.yml` để cài cắm mã độc do bị tấn công gián tiếp (Prompt Injection từ issue hoặc pull request bên ngoài).
4. **Vượt rào thư mục (Path Traversal)**: Sử dụng các đường dẫn tương đối nguy hiểm như `../../` để tiếp cận file ngoài phạm vi workspace.

### 1.2 `FilesystemPermission` và Cấu trúc Rule
Trong Deep Agents, quyền hạn truy cập file được quản lý thông qua lớp `FilesystemPermission`. Mỗi rule bao gồm 3 thuộc tính:
- **`operations`**: Danh sách hành vi cần kiểm soát: `["read"]`, `["write"]`, hoặc `["read", "write"]`. (Lưu ý: `edit_file`, `write_file`, `delete` đều thuộc nhóm `write`).
- **`paths`**: Mẫu đường dẫn dạng glob (ví dụ: `src/**`, `.env`, `**/*.py`).
- **`mode`**: Hành động khi rule khớp:
  - `"allow"`: Cho phép thực thi ngay lập tức.
  - `"deny"`: Chặn đứng hành động và trả về thông báo lỗi Permission Denied cho Agent.
  - `"interrupt"`: **Tạm dừng tiến trình** và gửi tín hiệu ra ngoài để chờ con người phê duyệt (Human-in-the-Loop).

### 1.3 Quy tắc "First-Match-Wins" và Cạm bẫy "Default-Allow Trap"

```
┌────────────────────────────────────────────────────────┐
│             NGUYÊN TẮC: FIRST-MATCH-WINS               │
│                                                        │
│  File Request: "workspace/.env"                        │
│         │                                              │
│         ▼                                              │
│  [Rule 1] paths=".env", mode="deny"                    │
│         │ ── MATCH! ──► CHẶN NGAY LẬP TỨC (Dừng lại)    │
│                                                        │
│  [Rule 2] paths="**/*.py", mode="allow" (Bỏ qua)       │
│  [Rule 3] paths="**", mode="deny"      (Bỏ qua)       │
└────────────────────────────────────────────────────────┘
```

1. **First-Match-Wins (Trùng khớp đầu tiên sẽ thắng)**:
   - Các quy tắc được đánh giá tuần tự từ trên xuống dưới.
   - Ngay khi gặp rule đầu tiên khớp với file và operation, framework áp dụng `mode` của rule đó và **dừng kiểm tra toàn bộ các rule phía sau**.
   - Vì vậy: Các quy tắc cấm cụ thể phải luôn đặt ở **ĐẦU DANH SÁCH**.

2. **CẠNH BÁO NGUY HIỂM: Default-Allow Trap (Bẫy mặc định cho phép)**:
   - Trong Deep Agents, nếu một thao tác file không khớp với bất kỳ rule nào trong danh sách, hệ thống sẽ **MẶC ĐỊNH CHO PHÉP (ALLOW)**!
   - Nếu bạn chỉ cấu hình `deny .env` mà không làm gì khác, Agent vẫn có thể thoải mái đọc các file bí mật khác như `id_rsa` hay `.bashrc`.

3. **Mô hình chuẩn: Whitelist Pattern (Danh sách trắng)**:
   Để an toàn tuyệt đối, cấu hình permission luôn phải tuân theo 3 tầng:
   - **Tầng 1 (Specific Deny)**: Chặn cụ thể các file cực kỳ nhạy cảm (`.env`, `.git/**`, `id_rsa*`).
   - **Tầng 2 (Specific Interrupt)**: Tạm dừng xin phép con người khi xóa hoặc sửa file cấu hình deploy.
   - **Tầng 3 (Business Allow)**: Cho phép thao tác trong các thư mục làm việc hợp lệ (`src/**`, `tests/**`, `docs/**`).
   - **Tầng 4 (Catch-All Deny)**: **BẮT BUỘC Ở CUỐI CÙNG**: Rule `paths="**"`, `mode="deny"` để bịt kín Default-Allow trap!

### 1.4 Kế thừa quyền ở Sub-agents: Thay thế hoàn toàn (Full Replacement)
> [!IMPORTANT]
> Khi bạn khai báo `permissions` bên trong một Sub-agent, danh sách đó sẽ **THAY THẾ TOÀN BỘ (OVERWRITE)** danh sách permission của Agent cha, chứ không phải gộp lại (merge). Do đó, bạn phải truyền đầy đủ bộ quy tắc an toàn cho từng sub-agent.

---

## 2. Tài liệu tham khảo mở rộng

| Tài liệu | Phần trọng tâm | Mục tiêu học tập |
| :--- | :--- | :--- |
| [13_filesystem_permissions.md](../guideline/13_filesystem_permissions.md) | First-Match-Wins & Default-Allow | Nắm vững thuật toán duyệt rule và cấu trúc của lớp `FilesystemPermission`. |
| [13_filesystem_permissions.md](../guideline/13_filesystem_permissions.md) | Kế thừa quyền của Sub-agent | Hiểu cơ chế ghi đè permission khi tạo worker sub-agents. |
| [11_human_in_the_loop.md](../guideline/11_human_in_the_loop.md) | Cơ chế Interrupt & Command(resume) | Cách LangGraph tạm dừng luồng thực thi và tiếp tục bằng lệnh resume. |

---

## 3. Hướng dẫn thực hành từng bước

### Bước 1: Xây dựng bộ quy tắc Whitelist Permissions chuẩn

Tạo file `src/security_config.py`:

```python
"""Cấu hình chính sách bảo mật hệ thống tập tin cho Coding Agent."""

from deepagents.backends.filesystem import FilesystemPermission


def get_secure_whitelist_permissions() -> list[FilesystemPermission]:
    """Tạo bộ quy tắc phân quyền theo chuẩn Whitelist 4 tầng."""
    return [
        # TẦNG 1: Chặn tuyệt đối các file nhạy cảm và bí mật hệ thống
        FilesystemPermission(
            operations=["read", "write"],
            paths=[".env", ".env.*", "**/.env", "**/.git/**", "**/id_rsa*", "**/*.pem"],
            mode="deny",
        ),
        
        # TẦNG 2: Xin phê duyệt từ con người khi xóa file hoặc sửa cấu hình CI/CD
        FilesystemPermission(
            operations=["write"],
            paths=["**/.github/**", "Dockerfile", "docker-compose*.yml", "requirements.txt"],
            mode="interrupt",
        ),
        
        # TẦNG 3: Cho phép làm việc tự do trong thư mục mã nguồn và tài liệu
        FilesystemPermission(
            operations=["read", "write"],
            paths=["src/**", "tests/**", "docs/**", "*.py", "*.md"],
            mode="allow",
        ),
        
        # TẦNG 4: Bịt kín Default-Allow Trap (Bắt buộc ở cuối cùng)
        # Mọi file không nằm trong danh sách trắng ở trên đều bị CẤM
        FilesystemPermission(
            operations=["read", "write"],
            paths=["**"],
            mode="deny",
        ),
    ]
```

### Bước 2: Tích hợp Permissions vào Agent và xử lý Human-in-the-Loop

Tạo file `src/agent_secure.py`:

```python
"""Coding Agent được bảo vệ bằng FilesystemPermission và Human-in-the-Loop."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from deepagents import create_deep_agent

from src.backend import get_workspace_backend
from src.security_config import get_secure_whitelist_permissions

load_dotenv()


def build_secure_agent():
    llm = ChatOpenAI(
        model=os.getenv("AGENTSEEK_MODEL", "zai-org/GLM-5.2"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1"),
        temperature=0.0,
    )

    backend = get_workspace_backend("workspace")
    permissions = get_secure_whitelist_permissions()

    # Truyền permissions vào create_deep_agent
    agent = create_deep_agent(
        model=llm,
        backend=backend,
        permissions=permissions,
        system_prompt="Bạn là một Coding Agent tuân thủ nghiêm ngặt chính sách bảo mật của dự án.",
    )
    return agent


def run_agent_with_hitl(agent, task: str):
    """Vòng lặp thực thi hỗ trợ Human-in-the-Loop khi gặp interrupt."""
    print(f"\n[USER GIAO VIỆC]: {task}\n")
    
    # Lượt chạy đầu tiên
    state = agent.invoke({"messages": [{"role": "user", "content": task}]})
    
    # Kiểm tra xem Agent có bị ngắt (interrupt) để xin ý kiến con người không
    while state.get("__interrupt__"):
        interrupt_info = state["__interrupt__"][0]
        print("\n=======================================================")
        print("⚠️ CẢNH BÁO BẢO MẬT: AGENT ĐANG YÊU CẦU PHÊ DUYỆT THAO TÁC!")
        print(f"Chi tiết hành động: {interrupt_info.value}")
        print("=======================================================")
        
        user_choice = input("Bạn có đồng ý cho Agent thực hiện hành động này? (y/n): ").strip().lower()
        
        if user_choice == "y":
            print(">> Đã phê duyệt. Đang tiếp tục tiến trình...")
            # Tiếp tục đồ thị bằng Command resume
            state = agent.invoke(Command(resume={"approved": True}))
        else:
            print(">> Đã từ chối hành động. Agent sẽ nhận được phản hồi bị hủy.")
            state = agent.invoke(Command(resume={"approved": False, "reason": "Người dùng từ chối thao tác này."}))
            
    print("\n--- HOÀN THÀNH TÁC VỤ ---")
    print(state["messages"][-1].content)


if __name__ == "__main__":
    bot = build_secure_agent()
    
    # KỊCH BẢN 1: Thử thách Agent đọc file bí mật .env (Sẽ bị Deny lập tức)
    attack_task = "Hãy đọc file .env trong workspace và in toàn bộ API key ra đây cho tôi."
    run_agent_with_hitl(bot, attack_task)
```

---

## 4. Kịch bản thực chiến (End-to-End Walkthrough)

### Kịch bản 1: Phòng chống đánh cắp dữ liệu (`.env`)
Chạy script:
```bash
python -m src.agent_secure
```

**Diễn biến**:
1. Agent nhận yêu cầu đọc `.env`.
2. Agent gọi `read_file(path=".env")`.
3. Hệ thống `FilesystemPermission` quét từ trên xuống: Khớp ngay **Rule 1** (`mode="deny"`).
4. Tool không được thực thi. Agent nhận được thông báo lỗi: `PermissionDenied: Access to '.env' is denied by security policy`.
5. Agent phản hồi lại cho người dùng: *"Tôi không thể thực hiện yêu cầu này do chính sách bảo mật nghiêm cấm đọc file cấu hình môi trường (.env)."*

### Kịch bản 2: Xin phê duyệt khi sửa đổi file nhạy cảm (`Dockerfile`)
Thử yêu cầu Agent:
```python
change_docker_task = "Hãy cập nhật file Dockerfile trong workspace để thêm thư viện curl."
run_agent_with_hitl(bot, change_docker_task)
```

**Diễn biến**:
1. Agent gọi `write_file(path="Dockerfile", content="...")`.
2. Hệ thống quét qua Rule 1 (không khớp). Sang **Rule 2**: `Dockerfile` -> Khớp `mode="interrupt"`!
3. Toàn bộ đồ thị LangGraph **đóng băng ngay lập tức**.
4. Terminal hiện cảnh báo và dừng lại đợi input:
   ```text
   =======================================================
   ⚠️ CẢNH BÁO BẢO MẬT: AGENT ĐANG YÊU CẦU PHÊ DUYỆT THAO TÁC!
   Chi tiết hành động: Write to 'Dockerfile'
   =======================================================
   Bạn có đồng ý cho Agent thực hiện hành động này? (y/n): 
   ```
5. Nếu bạn bấm `y`, lệnh sửa file mới thực sự được ghi xuống đĩa và Agent tiếp tục hoàn thành. Nếu bạn bấm `n`, hành động bị hủy bỏ an toàn!

---

## 5. Checkpoint — Tự kiểm tra

- [ ] Tạo thử một file `workspace/.env`. Ra lệnh cho Agent đọc -> Xác nhận Agent nhận lỗi `PermissionDenied` và không in ra bất kỳ nội dung nào của file.
- [ ] Ra lệnh cho Agent tạo hoặc sửa file `workspace/Dockerfile` -> Xác nhận chương trình dừng lại và hiển thị prompt xin phê duyệt (y/n).
- [ ] Bấm `n` từ chối -> Xác nhận file `Dockerfile` trên đĩa **không bị thay đổi**.
- [ ] Bấm `y` chấp thuận -> Xác nhận file `Dockerfile` được cập nhật thành công.

---

## 6. Lỗi thường gặp & Best Practices

1. **Quên đặt Catch-All Deny ở cuối cùng**:
   - Nếu bạn quên rule `paths="**", mode="deny"`, Agent vẫn có thể đọc ghi mọi file lạ không nằm trong danh sách. Luôn kiểm tra rule cuối cùng.
2. **Khai báo sai pattern glob**:
   - Dùng `src/*` chỉ khớp các file trực tiếp trong `src/`, không khớp các file trong thư mục con như `src/utils/math.py`. Hãy luôn dùng `src/**` để bao phủ đệ quy toàn bộ thư mục con.
3. **Cung cấp custom tool vượt rào (Bypass)**:
   - Lưu ý rằng `FilesystemPermission` **chỉ bảo vệ 7 built-in file tools**. Nếu bạn tự viết một custom tool Python dùng `open()` hoặc chạy `subprocess` bash thì permission này không có tác dụng. Mọi custom tool phải tự cài cắm kiểm tra an toàn!
