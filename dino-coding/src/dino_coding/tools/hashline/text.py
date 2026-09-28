"""Chuẩn hóa văn bản và content-hash cho hashline engine.

Port rút gọn của crates/pi-edit/src/text.rs và store::file_hash.
Không module nào trong đây được chạm filesystem.
"""

from __future__ import annotations

import re

import xxhash

# Escape tường minh như omp: `pub const BOM: &str = "\u{FEFF}";`
# KHÔNG gõ ký tự \ufeff literal — nó vô hình, linter/formatter có thể xóa mất
# và biến BOM thành chuỗi rỗng (khi đó startswith("") luôn True, strip_bom
# sẽ cắt ký tự đầu của MỌI file một cách âm thầm).
BOM = "\ufeff"


def strip_bom(content: str) -> str:
    """Tách UTF-8 BOM ở đầu nội dung. ← port text::strip_bom"""
    return content[1:] if content.startswith(BOM) else content


def normalize_to_lf(text: str) -> str:
    """Đổi mọi CRLF / CR còn sót thành LF. ← port text::normalize_to_lf"""
    return text.replace("\r\n", "\n").replace("\r", "\n")


# Regex compile MỘT LẦN ở mức module — mô phỏng `static XXX_RE: LazyLock<Regex>`
# của omp; tránh khởi tạo lại object pattern qua mỗi lần gọi hàm.
_SEEN_PREFIX_RE = re.compile(r"^[ *]?(\d+)(?:-(\d+))?:")


class LineEnding:
    """Phát hiện và khôi phục kiểu xuống dòng. ← port text::detect_line_ending"""

    LF = "lf"
    CRLF = "crlf"

    @staticmethod
    def detect(content: str) -> str:
        """Kiểu xuống dòng của DÒNG ĐẦU thắng. ← port text::detect_line_ending

        Chuẩn Rust so sánh VỊ TRÍ: \\r\\n chỉ thắng khi xuất hiện TRƯỚC \\n
        đầu tiên ("first line ending style"), không phải "có \\r\\n bất kỳ
        đâu" — file trộn "a\\nb\\r\\nc" có dòng đầu LF nên cả file là LF.
        """
        lf = content.find("\n")
        if lf == -1:
            return LineEnding.LF
        crlf = content.find("\r\n")
        return LineEnding.CRLF if crlf != -1 and crlf < lf else LineEnding.LF

    @staticmethod
    def restore(text: str, ending: str) -> str:
        """Ghi đĩa theo kiểu dòng gốc của file. ← port text::restore_line_endings

        omp giữ bất biến "text đầu vào luôn LF" bằng kiến trúc crate; Python
        không có cơ chế nào giữ giúp nên ta chủ động normalize bên trong —
        caller vô tình truyền text còn \r\n sẽ không bị nhân đôi thành \r\r\n.
        Chi phí 1 pass, chỉ trả lời đúng trong mọi tình huống (hàm total).
        """
        text = normalize_to_lf(text)
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

    normalized = "\n".join(line.rstrip(" \t\r") for line in text.split("\n"))
    digest = xxhash.xxh32(normalized.encode("utf-8")).intdigest()
    return f"{digest & 0xFFFF:04X}"


def payload_hash(text: str) -> int:
    """Khóa 64-bit ổn định cho patch input thô — dùng chống vòng lặp no-op. ← port store::payload_hash"""

    return xxhash.xxh64(text.encode("utf-8")).intdigest()


def seen_lines_from_body(body: str) -> list[int]:
    """Trích số dòng hiển thị từ một body dạng hashline. ← port store::seen_lines_from_body

    Mỗi dòng khớp `^[ *]?(\\d+)(-(\\d+))?:` đóng góp endpoint(s) của nó.
    Dòng `5-12:...` đóng góp cả 5 và 12 (guard cần biên, không cần từng dòng giữa).
    """
    prefix = _SEEN_PREFIX_RE
    seen: list[int] = []
    for row in body.split("\n"):
        match = prefix.match(row)
        if not match:
            continue
        seen.append(int(match.group(1)))
        if match.group(2):
            seen.append(int(match.group(2)))
    return seen
