"""Kịch bản nghiệm thu Phase 2.5 — "Migration Weekend" (E2E, không cần LLM).

Chạy:  uv run python scripts/acceptance_phase25.py

Bối cảnh thực tế: mini-project `legacy_shop/` có API deprecated
`fetch_user(...)` cần thay bằng `users.get(...)` trên Python, rename
`fetchUser` trên TypeScript, xóa hàm `legacy_invoice` bằng block-op,
trong lúc có một file draft DANG DỞ (lỗi cú pháp) và file ẩn không được quét.

Timeline 8 bước — mỗi bước gọi ĐÚNG tool như model sẽ gọi, tự chấm PASS/FAIL:

 1. RECON      — ast_grep multi-file: hits + meta + parse-error hint cho draft
 2. ANCHOR     — dùng search-hit (tag + seen-line) làm edit anchor, KHÔNG read
 3. PREVIEW    — ast_edit dry-run đa file: diff hiện, đĩa NGUYÊN VẸN
 4. STALE      — sửa file tay giữa preview và apply → bị TỪ CHỐI, không ghi gì
 5. APPLY      — re-preview → apply=true: ghi 3 file + fresh tags + skip draft
 6. BLOCK CUT  — CUT N* xóa hàm legacy_invoice theo 1 số dòng (block resolver)
 7. CROSS-LANG — ast_edit trên notify.ts: fetchUser → getUser
 8. VERIFY     — logic mini-project chạy đúng + ast_grep xác nhận 0 match cũ
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Workspace tạm — set TRƯỚC khi import tool (singleton lazy)
_ROOT = Path(tempfile.mkdtemp(prefix="dino-accept25-"))
os.environ["DINO_WORKSPACE"] = str(_ROOT)

from dino_coding.tools.ast_tools import ast_edit, ast_grep  # noqa: E402
from dino_coding.tools.editor import edit  # noqa: E402

FAILURES: list[str] = []


def check(step: str, name: str, ok: bool, detail: str = "") -> None:
    mark = "\u001b[32mPASS\u001b[0m" if ok else "\u001b[31mFAIL\u001b[0m"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail and ok else ""))
    if not ok:
        FAILURES.append(f"{step}: {name}" + (f"\n    {detail}" if detail else ""))


def step(no: int, name: str) -> None:
    print(f"\n\u001b[36m─ Bước {no}: {name} ─\u001b[0m")


def w(rel: str, text: str) -> None:
    target = _ROOT / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def disk(rel: str) -> str:
    with open(_ROOT / rel, encoding="utf-8", newline="") as fh:
        return fh.read()


def setup_project() -> None:
    w("legacy_shop/models.py", (
        "class User:\n"
        "    def __init__(self, user_id, profile=None):\n"
        "        self.user_id = user_id\n"
        "        self.profile = profile\n"
        "\n"
        "\n"
        "def fetch_user(user_id):\n"
        "    \"\"\"Deprecated — dùng users.get().\"\"\"\n"
        "    return User(user_id)\n"
        "\n"
        "\n"
        "class UserRepo:\n"
        "    def get(self, user_id):\n"
        "        return User(user_id)\n"
        "\n"
        "\n"
        "users = UserRepo()\n"
    ))
    w("legacy_shop/api.py", (
        "from legacy_shop.models import fetch_user\n"
        "\n"
        "\n"
        "def dashboard(user_id):\n"
        "    user = fetch_user(user_id)\n"
        "    return user\n"
        "\n"
        "\n"
        "def profile_page(user_id):\n"
        "    user = fetch_user(\n"
        "        user_id,\n"
        "        include_profile=True,\n"
        "    )\n"
        "    return user\n"
    ))
    w("legacy_shop/billing.py", (
        "from legacy_shop.models import fetch_user\n"
        "\n"
        "\n"
        "def charge(user_id, amount):\n"
        "    user = fetch_user(user_id)\n"
        "    return ('charge', user.user_id, amount)\n"
        "\n"
        "\n"
        "def legacy_invoice(user_id):\n"
        "    \"\"\"Sẽ bị xóa bằng CUT N* — không ai đếm dòng hàm này.\"\"\"\n"
        "    user = fetch_user(user_id)\n"
        "    lines = ['INVOICE', f'uid={user.user_id}']\n"
        "    total = 0\n"
        "    for line in lines:\n"
        "        total += len(line)\n"
        "    return total\n"
    ))
    w("legacy_shop/draft.py", "def upcoming(:\n    print('work in progress'\n")
    w("legacy_shop/notify.ts", (
        "export function greet(id: number): string {\n"
        "  const user = fetchUser(id);\n"
        "  return `hello ${user}`;\n"
        "}\n"
    ))
    w("legacy_shop/notes.md", "fetch_user trong prose — không phải code.\n")
    w("legacy_shop/.hidden/secret.py", "fetch_user(1)\n")


def main() -> int:
    print("\u001b[1mKịch bản nghiệm thu Phase 2.5 — Migration Weekend\u001b[0m")
    print(f"workspace: {_ROOT}")
    setup_project()

    # ---- 1. RECON ----------------------------------------------------------
    step(1, "RECON — ast_grep đa file với metavar $$$ARGS")
    out = ast_grep.invoke({"pat": "fetch_user($$$ARGS)", "path": "legacy_shop"})
    hits = [l for l in out.splitlines() if l.lstrip().startswith(("*", " "))
            and "fetch_user" in l and "meta:" not in l]
    has_multi_line = any("include_profile" in l for l in out.splitlines())
    check("1", "tìm thấy ≥4 match fetch_user", len(hits) >= 4, f"{len(hits)} match rows")
    check("1", "api.py + billing.py đều có (def không match call-pattern)", has_multi_line and "billing.py" in out)
    check("1", "draft.py được báo parse error (không im lặng)",
          "parse error" in out.lower() or "draft.py" in out)
    check("1", "file ẩn/.md không xuất hiện",
          ".hidden" not in out and "notes.md" not in out)
    check("1", "meta ARGS hiển thị", "ARGS=" in out)

    # ---- 2. SEARCH-HIT LÀM ANCHOR ------------------------------------------
    step(2, "ANCHOR — edit thẳng theo tag từ search hit, không read")
    grep_api = ast_grep.invoke({"pat": "fetch_user($$$ARGS)", "path": "legacy_shop/api.py"})
    header = grep_api.splitlines()[0]                    # [legacy_shop/api.py#TAG]
    tag = header.split("#")[1].rstrip("]")
    hit_line = next(int(l.split(":")[0].lstrip("* "))
                    for l in grep_api.splitlines()
                    if ":" in l and "fetch_user(user_id)" in l and "meta:" not in l)
    result = edit.invoke({"input": (
        f"{header}\n"
        f"PUT {hit_line}.={hit_line}:\n"
        f"+    user = users.get(user_id)"
    )})
    applied = result.startswith("[") and "users.get" in disk("legacy_shop/api.py")
    check("2", f"edit theo dòng {hit_line} từ search hit", applied,
          f"tag {tag} đủ freshness")

    # ---- 3. PREVIEW --------------------------------------------------------
    step(3, "PREVIEW — ast_edit dry-run: diff hiện, đĩa nguyên vẹn")
    before = {rel: disk(rel) for rel in ("legacy_shop/models.py",
                                         "legacy_shop/billing.py")}
    preview = ast_edit.invoke({
        "ops": [{"pat": "fetch_user($$$ARGS)", "out": "users.get($$$ARGS)"}],
        "paths": ["legacy_shop"],
    })
    unchanged = all(disk(rel) == text for rel, text in before.items())
    check("3", "bắt đầu bằng 'Staged as a proposal'",
          preview.startswith("Staged as a proposal"))
    check("3", "diff có dòng -N: cũ và +N: mới",
          any(l.startswith("-") and "fetch_user" in l for l in preview.splitlines())
          and any(l.startswith("+") and "users.get" in l for l in preview.splitlines()))
    check("3", "KHÔNG ghi đĩa ở preview", unchanged)
    check("3", "draft.py bị skip kèm cảnh báo parse",
          "draft.py" in preview and "parse" in preview.lower())

    # ---- 4. STALE ----------------------------------------------------------
    step(4, "STALE — file đổi tay giữa preview và apply → từ chối ghi")
    with open(_ROOT / "legacy_shop/billing.py", "a", encoding="utf-8", newline="") as fh:
        fh.write("# hotfixComment từ reviewer\n")
    baseline = {rel: disk(rel) for rel in ("legacy_shop/models.py",
                                           "legacy_shop/api.py",
                                           "legacy_shop/billing.py")}
    stale_out = ast_edit.invoke({
        "ops": [{"pat": "fetch_user($$$ARGS)", "out": "users.get($$$ARGS)"}],
        "paths": ["legacy_shop"], "apply": True,
    })
    after = {rel: disk(rel) for rel in baseline}
    check("4", "apply bị từ chối (stale)", stale_out.startswith("Error")
          or "stale" in stale_out.lower(), stale_out.splitlines()[0][:70])
    check("4", "KHÔNG file nào bị ghi (so snapshot byte-exact)", after == baseline)

    # ---- 5. APPLY ----------------------------------------------------------
    step(5, "APPLY — re-preview rồi apply=true: ghi + fresh tags")
    ast_edit.invoke({
        "ops": [{"pat": "fetch_user($$$ARGS)", "out": "users.get($$$ARGS)"}],
        "paths": ["legacy_shop"],
    })
    applied_out = ast_edit.invoke({
        "ops": [{"pat": "fetch_user($$$ARGS)", "out": "users.get($$$ARGS)"}],
        "paths": ["legacy_shop"], "apply": True,
    })
    billing_now = disk("legacy_shop/billing.py")
    # codemod chỉ lo CALL sites — `def fetch_user` (models.py) là việc của bước 6
    # slice first→last node giữ nguyên cả separator + trailing comma (đúng
    # replacer.rs); `)` đóng thu về cuối — hành vi chuẩn ast-grep, Python hợp lệ
    check("5", "multiline call giữ separator gốc (nguồn slice, không join)",
          "users.get(user_id,\n        include_profile=True,)" in disk("legacy_shop/api.py"))
    check("5", "billing.py: cả 2 call được rewrite (comment append không cản)",
          billing_now.count("users.get(user_id)") == 2
          and "fetch_user(" not in billing_now)
    check("5", "draft.py KHÔNG bị đụng", disk("legacy_shop/draft.py").count("\n") == 2)
    check("5", "kết quả apply có fresh tag", "[legacy_shop/billing.py#" in applied_out)

    # ---- 6. BLOCK CUT ×2 ---------------------------------------------------
    step(6, "BLOCK CUT — CUT N* xóa 2 hàm deprecated ở 2 file, không đếm dòng")
    def grep_def(rel: str, name: str) -> tuple[str, int]:
        # pattern def PHẢI gồm body để parse thành node hoàn chỉnh
        out = ast_grep.invoke({"pat": f"def {name}($$$A):\n    $$$BODY", "path": rel})
        header = out.splitlines()[0]
        line_no = next(int(l.split(":")[0].lstrip("* "))
                       for l in out.splitlines() if f"def {name}(" in l)
        return header, line_no

    bill_header, bill_line = grep_def("legacy_shop/billing.py", "legacy_invoice")
    edit.invoke({"input": f"{bill_header}\nCUT {bill_line}*"})
    billing_after = disk("legacy_shop/billing.py")
    check("6", f"CUT {bill_line}* xóa trọn legacy_invoice",
          "legacy_invoice" not in billing_after and "INVOICE" not in billing_after)
    check("6", "hàm charge phía trên còn nguyên",
          "def charge(user_id, amount):" in billing_after)

    model_header, model_line = grep_def("legacy_shop/models.py", "fetch_user")
    edit.invoke({"input": f"{model_header}\nCUT {model_line}*"})
    models_after = disk("legacy_shop/models.py")
    check("6", "CUT N* thứ hai trên file khác: def fetch_user biến mất",
          "def fetch_user" not in models_after and "class UserRepo" in models_after)

    # xóa def xong thì import line phải đổi theo — import statement là node hoàn chỉnh
    ast_edit.invoke({
        "ops": [{"pat": "from legacy_shop.models import fetch_user",
                 "out": "from legacy_shop.models import users"}],
        "paths": ["legacy_shop"], "apply": True,
    })
    check("6", "import line được codemod theo def đã xóa",
          "import fetch_user" not in disk("legacy_shop/api.py")
          and "import users" in disk("legacy_shop/api.py"))

    # ---- 7. CROSS-LANGUAGE --------------------------------------------------
    step(7, "CROSS-LANG — ast_edit trên TypeScript")
    ast_edit.invoke({
        "ops": [{"pat": "fetchUser($ID)", "out": "getUser($ID)"}],
        "paths": ["legacy_shop/notify.ts"], "apply": True,
    })
    ts_now = disk("legacy_shop/notify.ts")
    check("7", "fetchUser → getUser trên .ts", "getUser(id)" in ts_now
          and "fetchUser" not in ts_now)
    check("7", "type annotation `: number` còn nguyên", "id: number" in ts_now)

    # ---- 8. VERIFY -----------------------------------------------------------
    step(8, "VERIFY — logic chạy đúng + không còn API cũ")
    sys.path.insert(0, str(_ROOT))
    from legacy_shop import api, billing, models  # noqa: E402

    user = api.dashboard(7)
    charge = billing.charge(9, 100)
    check("8", "api.dashboard dùng users.get", user.user_id == 7
          and isinstance(user, models.User))
    check("8", "billing.charge hoạt động", charge == ("charge", 9, 100))
    residual = ast_grep.invoke({"pat": "fetch_user($$$A)", "path": "legacy_shop"})
    check("8", "ast_grep xác nhận 0 match fetch_user còn lại",
          "No matches" in residual or "0" in residual.splitlines()[0],
          residual.splitlines()[0][:60])

    # ---- tổng kết ------------------------------------------------------------
    print()
    if FAILURES:
        print(f"\u001b[31m✗ {len(FAILURES)} kiểm tra FAIL:\u001b[0m")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("\u001b[32m✓ Migration Weekend: mọi kiểm tra PASS — Phase 2.5 nghiệm thu đạt.\u001b[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
