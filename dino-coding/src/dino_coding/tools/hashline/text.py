"""Chuẩn hóa văn bản và content-hash cho hashline engine.

Port rút gọn của crates/pi-edit/src/text.rs và store::file_hash.
Không module nào trong đây được chạm filesystem.
"""

from __future__ import annotations

# BOM: Là hằng số đại diện cho ký tự Unicode \ufeff (Zero Width No-Break Space).
# BOM viết tắt của Byte Order Mark (Dấu thứ tự byte).
# Nguồn gốc: Ban đầu, BOM được thiết kế cho các bảng mã UTF-16 và UTF-32 để máy tính xác định thứ tự byte là Big-Endian (MSB trước) hay Little-Endian (LSB trước).

# Trong UTF-8: Thứ tự byte trong UTF-8 là cố định, do đó UTF-8 hoàn toàn không cần BOM.
# Tuy nhiên, một số hệ điều hành và công cụ (đặc biệt là môi trường Windows như Notepad, PowerShell, Visual Studio cũ)
# thường thêm chuỗi byte EF BB BF vào đầu file để đánh dấu rằng tệp này dùng UTF-8.

# Đặc tính: Khi decode sang string trong ngôn ngữ lập trình, chuỗi byte này trở thành ký tự \ufeff.
# Đây là một ký tự vô hình (không có độ rộng) nên mắt thường nhìn trên trình soạn thảo sẽ không thấy bất kỳ dấu hiệu khác lạ nào.
BOM = "\ufeff"


def strip_bom(content: str) -> str:
    """Tách UTF-8 BOM ở đầu nội dung"""
    return content[1:] if content.startswith(BOM) else content

# Hàm normalize_to_lf có nhiệm vụ chuẩn hóa mọi ký tự ngắt dòng (newline) trong văn bản về một chuẩn duy nhất là LF
# (\n – chuẩn của Unix/Linux/macOS hiện đại).
def normalize_to_lf(text: str) -> str:
    """Đổi mọi CRLF / CR còn sót thành LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")

class LineEnding:
    """Phát hiện và khôi phục kiểu xuống dòng."""

    LF = "lf"
    CRLF = "crlf"

    @staticmethod
    def detect(content: str) -> str:
        crlf = content.find("\r\n")
        if crlf != -1:
            return LineEnding.CRLF
        return LineEnding.LF

    @staticmethod
    def restore(text: str, ending: str) -> str:
        """Nội dung engine luôn là LF; ghi đĩa theo kiểu dòng gốc của file."""
        if ending == LineEnding.CRLF:
            return text.replace("\n", "\r\n")
        return text

def file_hash(text: str) -> str:
    """Content tag 4-hex cho một phiên bản file. ← port store::file_hash

    Thuật toán (phải khớp byte với Rust):
    1. Với TỪNG dòng, bỏ mọi khoảng trắng cuối dòng (space/tab/CR).
       → model làm rơi trailing space không làm đổi tag.
    2. xxh32 (seed 0) toàn văn bản đã chuẩn hóa.
    3. AND 0xFFFF, format 4 ký tự HEX VIẾT HOA.

    Ví dụ: "def f():\\n    return 1\\n" và "def f():\\n    return 1   \\n"
    cho cùng một tag.
    """
    import xxhash

    normalized = "\n".join(line.rstrip(" \t\r") for line in text.split("\n"))
    digest = xxhash.xxh32(normalized.encode("utf-8")).intdigest()
    return f"{digest & 0xFFFF:04X}"


def payload_hash(text: str) -> int:
    """Khóa 64-bit ổn định cho patch input thô — dùng chống vòng lặp no-op. ← port store::payload_hash"""
    import xxhash

    return xxhash.xxh64(text.encode("utf-8")).intdigest()


def seen_lines_from_body(body: str) -> list[int]:
    """Trích số dòng hiển thị từ một body dạng hashline. ← port store::seen_lines_from_body

    Mỗi dòng khớp `^[ *]?(\\d+)(-(\\d+))?:` đóng góp endpoint(s) của nó.
    Dòng `5-12:...` đóng góp cả 5 và 12 (guard cần biên, không cần từng dòng giữa).
    """
    import re

    prefix = re.compile(r"^[ *]?(\d+)(?:-(\d+))?:")
    seen: list[int] = []
    for row in body.split("\n"):
        match = prefix.match(row)
        if not match:
            continue
        seen.append(int(match.group(1)))
        if match.group(2):
            seen.append(int(match.group(2)))
    return seen
