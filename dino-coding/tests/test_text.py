"""Bộ test chuyên sâu cho hashline text engine (text.py).

Chạy: uv run pytest tests/test_text.py -v

Nguyên tắc thiết kế:
1. KAT (Known-Answer Test) — pin giá trị hash chính tínnh tính bằng thuật toán
   chuẩn (xxh32 seed 0 & 0xFFFF, xxh64) để bắt regression algorithm (đổi seed,
   đổi mask, đổi normalize đều làm test đỏ ngay).
2. Boundary — mọi mép biên: chuỗi rỗng, chỉ-BOM, BOM giữa dòng, số 0, leading
   zero, range đảo chiều, file trộn 3 kiểu newline.
3. Invariant (bất biến) — các tính chất engine dựa vào: normalize/restore
   idempotent, hash bất biến qua chu kỳ read→edit→write (roundtrip).
4. Fixture file phức tạp — sinh module Python ~600 dòng thật (class, decorator,
   docstring, unicode, trailing whitespace), ghi đĩa dạng Windows (BOM + CRLF)
   rồi test toàn bộ pipeline như edit engine sẽ làm.
5. Property-style — vòng lặp seeded (deterministic) kiểm bất biến trên dữ liệu
   ngẫu nhiên, thay vì chỉ từng case tay.
"""

from __future__ import annotations

import random
import re
from pathlib import Path

import pytest

from dino_coding.tools.hashline.text import (
    BOM, LineEnding, _SEEN_PREFIX_RE, file_hash, normalize_to_lf,
    payload_hash, seen_lines_from_body, strip_bom,
)

# ---------------------------------------------------------------------------
# KAT — giá trị pin, nguồn gốc: tính trực tiếp bằng thuật toán chuẩn.
# Nếu một trong các giá trị này đổi → có ai đó đã thay đổi thuật toán hash
# (seed/mask/normalize) và MỌI tag đã lưu trong snapshot store sẽ vô hiệu.
# ---------------------------------------------------------------------------
KAT_HASH_EMPTY = "5D05"          # file_hash("")
KAT_HASH_FUNC = "213F"           # file_hash("def f():\n    return 1\n")
KAT_HASH_UNICODE = "B8ED"        # file_hash("print('héllo 🎉')\n")
KAT_HASH_TWO_LINES = "9A46"      # file_hash("a\nb\n")
KAT_PAYLOAD_EMPTY = 17241709254077376921  # payload_hash("")

TAG_RE = re.compile(r"^[0-9A-F]{4}$")


# ===========================================================================
# 1. strip_bom
# ===========================================================================

@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("hello world", "hello world"),           # không BOM — nguyên vẹn
        (f"{BOM}hello world", "hello world"),     # BOM đầu — lột đúng 1 ký tự
        ("", ""),                                 # chuỗi rỗng
        (BOM, ""),                                # chỉ toàn BOM
        (f"{BOM}{BOM}x", f"{BOM}x"),              # 2 BOM liên tiếp — chỉ lột 1
        (f"a{BOM}b", f"a{BOM}b"),                 # BOM GIỮA chuỗi — không đụng
        ("\r\nx", "\r\nx"),                       # CRLF đầu không phải BOM
    ],
)
def test_strip_bom_boundaries(content: str, expected: str) -> None:
    assert strip_bom(content) == expected


def test_strip_bom_never_drops_first_char_of_normal_file() -> None:
    """Hồi quy cho bug chết người: nếu BOM bị biến thành chuỗi rỗng
    (linter xóa ký tự vô hình), startswith('') luôn True và MỌI file
    mất ký tự đầu. Test này pin độ dài: chỉ trừ đúng 1 khi có BOM."""
    normal = "def f():\n    return 1\n"
    assert len(strip_bom(normal)) == len(normal)
    assert len(strip_bom(BOM + normal)) == len(normal)  # BOM không tính vào str len


# ===========================================================================
# 2. normalize_to_lf
# ===========================================================================

def test_normalize_mixed_three_newline_styles() -> None:
    """Một chuỗi trộn CRLF + CR đơn (old Mac) + LF — chuẩn hết về LF."""
    assert normalize_to_lf("a\r\nb\rc\nd") == "a\nb\nc\nd"


@pytest.mark.parametrize(
    "text",
    ["", "\n", "\r", "\r\n", "\r\n\r\n", "a", "line1\r\nline2\r", "🚀\r\n🚀\r"],
)
def test_normalize_to_lf_is_idempotent(text: str) -> None:
    """Bất biến: normalize(normalize(x)) == normalize(x)."""
    once = normalize_to_lf(text)
    assert normalize_to_lf(once) == once


def test_normalize_preserves_content_without_cr() -> None:
    """Không có \\r → trả nguyên văn (không tạo object mới vô ích trên đường nóng)."""
    clean = "def f():\n    return 1\n"
    assert normalize_to_lf(clean) == clean


# ===========================================================================
# 3. LineEnding.detect
# ===========================================================================

@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("def foo():\r\n    return 42\r\n", LineEnding.CRLF),
        ("def foo():\n    return 42\n", LineEnding.LF),
        ("single_line_code", LineEnding.LF),          # không có newline nào
        ("a\rb", LineEnding.LF),                      # CR đơn lẻ không tính
        ("a\r\nb\nc\n", LineEnding.CRLF),             # \r\n xuất hiện TRƯỚC \n đầu
    ],
)
def test_detect_basic(content: str, expected: str) -> None:
    assert LineEnding.detect(content) == expected


def test_detect_first_line_ending_style_wins() -> None:
    """Chuẩn omp (text.rs::detect_line_ending): so sánh VỊ TRÍ — kiểu xuống dòng
    của DÒNG ĐẦU thắng, không phải 'có \\r\\n bất kỳ đâu nào'.

        pub fn detect_line_ending(content: &str) -> LineEnding {
            let Some(lf) = content.find('\\n') else { return LineEnding::Lf; };
            match content.find("\\r\\n") {
                _ => LineEnding::Lf,
            }
        }

    File trộn "a\\nb\\r\\nc": dòng đầu kết thúc bằng LF → cả file được coi là LF.
    Test này ĐỎ với detect() hiện tại (`find("\\r\\n") != -1` là đủ CRLF) —
    đó chính là bằng chứng bug port tồn tại; sửa detect theo Rust rồi test xanh.
    """
    assert LineEnding.detect("a\nb\r\nc\n") == LineEnding.LF


# ===========================================================================
# 4. LineEnding.restore
# ===========================================================================

def test_restore_roundtrip_lf() -> None:
    assert LineEnding.restore("x\ny\n", LineEnding.LF) == "x\ny\n"


def test_restore_encodes_crlf() -> None:
    assert LineEnding.restore("x\ny", LineEnding.CRLF) == "x\r\ny"


def test_restore_defensive_against_crlf_input() -> None:
    """Caller quên normalize truyền thẳng CRLF → KHÔNG được tạo \\r\\r\\n."""
    bad = "a\r\nb\r\n"
    fixed = LineEnding.restore(bad, LineEnding.CRLF)
    assert fixed == "a\r\nb\r\n"
    # Kiểm tra trực tiếp:
    assert fixed.count("\r") == fixed.count("\n") == 2


@pytest.mark.parametrize("ending", [LineEnding.LF, LineEnding.CRLF])
def test_restore_is_idempotent(ending: str) -> None:
    """Bất biến: restore(restore(x)) == restore(x) — ghi 2 lần không đổi bytes."""
    once = LineEnding.restore("a\nb\n", ending)
    assert LineEnding.restore(once, ending) == once


def test_restore_normalize_hash_roundtrip_invariant() -> None:
    """Bất biến lõi của engine: hash KHÔNG đổi qua chu kỳ
    write(CRLF) → read → normalize → hash. Nếu vỡ, tag mint lúc read sẽ
    không khớp khi đọc lại chính file vừa ghi."""
    original = "def f():\n    return 1\n"
    on_disk = LineEnding.restore(original, LineEnding.CRLF)
    reread = normalize_to_lf(on_disk)
    assert file_hash(reread) == file_hash(original)


# ===========================================================================
# 5. file_hash — KAT + bất biến trailing-whitespace
# ===========================================================================

def test_file_hash_known_answers() -> None:
    assert file_hash("") == KAT_HASH_EMPTY
    assert file_hash("def f():\n    return 1\n") == KAT_HASH_FUNC
    assert file_hash("print('héllo 🎉')\n") == KAT_HASH_UNICODE
    assert file_hash("a\nb\n") == KAT_HASH_TWO_LINES


@pytest.mark.parametrize("text", ["", "a", "def f():\n    return 1\n", "🚀\n"])
def test_file_hash_format_is_4_uppercase_hex(text: str) -> None:
    tag = file_hash(text)
    assert TAG_RE.fullmatch(tag), f"tag sai định dạng: {tag!r}"


@pytest.mark.parametrize(
    ("base", "variant"),
    [
        ("def f():\n    return 1\n", "def f():\n    return 1   \n"),      # space
        ("def f():\n    return 1\n", "def f():\n    return 1\t\n"),       # tab
        ("def f():\n    return 1\n", "def f():\n    return 1 \t \n"),     # trộn
        ("def f():\n    return 1\n", "def f():\r\n    return 1\t\r\n"),   # CRLF+tab
        ("a\nb", "a\nb   "),  # cuối file không newline + trailing space
    ],
)
def test_file_hash_ignores_trailing_whitespace(base: str, variant: str) -> None:
    assert file_hash(base) == file_hash(variant)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("a\nb\n", "a\nc\n"),                    # đổi nội dung trong dòng
        ("a\nb\n", "a\nb\n\n"),                  # thêm dòng trống THẬT
        ("a\n b\n", "a\nb\n"),                   # space ĐẦU dòng (indent) phải khác
        ("def f():\n    return 1\n", ""),        # rỗng vs có nội dung
    ],
)
def test_file_hash_distinguishes_real_content_changes(left: str, right: str) -> None:
    """Trailing-whitespace miễn dịch, nhưng mọi thay đổi nội dung thật phải đổi tag
    (các cặp này đã được xác minh khác hash — pin deterministic)."""
    assert file_hash(left) != file_hash(right)


def test_file_hash_is_deterministic_across_calls() -> None:
    assert file_hash("stable input\n") == file_hash("stable input\n")


def test_file_hash_collision_space_is_16_bits() -> None:
    """Không gian tag chỉ 16 bit (65.536 giá trị) — bài học thiết kế quan trọng:
    với 65.536 chuỗi khác nhau chỉ sinh được ~41.5k tag duy nhất (birthday
    occupancy ≈ 65536 × (1 − 1/e) ≈ 41.455 — đo thực tế: 41.501).
    Engine an toàn vì tag luôn đi kèm path + so khớp by_content, nhưng KHÔNG
    bao giờ dùng tag làm khóa định danh duy nhất toàn session."""
    tags = {file_hash(f"line {i}") for i in range(65_536)}
    assert all(TAG_RE.fullmatch(tag) for tag in tags)
    assert len(tags) > 40_000  # pin ngưỡng an toàn dưới giá trị đo 41.501


# ===========================================================================
# 6. payload_hash
# ===========================================================================

def test_payload_hash_known_answer_and_stability() -> None:
    assert payload_hash("") == KAT_PAYLOAD_EMPTY
    assert payload_hash("same patch") == payload_hash("same patch")
    assert payload_hash("patch A") != payload_hash("patch B")


def test_payload_hash_is_64_bit_unsigned() -> None:
    value = payload_hash("x")
    assert isinstance(value, int) and 0 <= value < 2**64


def test_payload_hash_sensitive_to_every_byte() -> None:
    """Khác file_hash, payload_hash KHÔNG normalize — từng byte đều quan trọng
    (chống no-op loop phải phân biệt được payload 'gần giống')."""
    assert payload_hash("a b") != payload_hash("a  b")
    assert payload_hash("a b") != payload_hash("a b ")


# ===========================================================================
# 7. seen_lines_from_body — boundary & negative
# ===========================================================================

def test_seen_lines_typical_read_output() -> None:
    """Đúng ngữ cảnh read output: marker `*` (anchor) và ` ` (context) của
    thông báo lỗi mismatch, range `N-M:` đóng góp cả 2 biên."""
    body = (
        "1: def hello():\n"
        "*2:     pass\n"
        " 3-6:     # comments block\n"
        "10: return True\n"
        "invalid line without line number prefix\n"
        "15-20: ending block"
    )
    assert seen_lines_from_body(body) == [1, 2, 3, 6, 10, 15, 20]


def test_seen_lines_zero_and_leading_zero_are_captured_as_ints() -> None:
    r"""Pin hành vi (khớp regex Rust `(\d+)`): '0:' cho line 0 (không tồn tại
    hệ 1-index — vô hại vì read không bao giờ emit), '007:' → 7."""
    assert seen_lines_from_body("0:zero\n007:james\n20-15:rev") == [0, 7, 20, 15]


@pytest.mark.parametrize(
    "row",
    [
        "1x: not a row",          # số xen ký tự trước `:` → không khớp
        "10 no colon",            # thiếu `:`
        "-5:negative",            # dấu trừ không thuộc \d+ ở đầu
        "line 5: text",           # chữ trước số
        "…",                      # dòng elision của summary
        "",                       # dòng trống
    ],
)
def test_seen_lines_rejects_non_prefix_rows(row: str) -> None:
    assert seen_lines_from_body(row) == []


def test_seen_lines_elision_footer_is_not_content() -> None:
    """Footer summary `[…130ln elided...]` và notice `[Showing lines...]`
    không được贡 hiến dòng seen."""
    body = "[src/a.py#A1B2]\n1:x\n2:y\n[Showing lines 1-2 of 500. Use offset=3 to continue]"
    assert seen_lines_from_body(body) == [1, 2]


def test_seen_prefix_re_pattern_is_module_level_and_frozen() -> None:
    """Bảo vệ cấu trúc: pattern compile 1 lần mức module, đúng nguyên văn omp."""
    assert _SEEN_PREFIX_RE.pattern == r"^[ *]?(\d+)(?:-(\d+))?:"


# ===========================================================================
# 8. Fixture file phức tạp — pipeline như edit engine thật
# ===========================================================================

def _build_complex_module(num_classes: int = 12, methods_per_class: int = 8) -> str:
    """Sinh module Python phức tạp: class + decorator + docstring + type hints
    + comment + unicode + trailing whitespace cố ý (để test hash immunity)."""
    header = (
        '"""Module sinh tự động cho test — kiểm tra pipeline text engine."""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
    )
    blocks = [header]
    for c in range(num_classes):
        lines = [
            f"class Service{c:02d}:",
            f'    """Service số {c} — héllo 🎉 (unicode ép tình huống UTF-8)."""',
            "",
        ]
        for m in range(methods_per_class):
            lines += [
                "    @staticmethod",
                f"    def method_{m}(value: int) -> int:",
                f"        '''Tính toán bước {m}.'''",
                f"        step = value * {m + 1} + {c}",
                "        return step   ",  # trailing spaces cố ý
                "",
            ]
        blocks.append("\n".join(lines))
    return "\n".join(blocks) + "\n"


COMPLEX_MODULE = _build_complex_module()  # ~12 × 50 ≈ 600 dòng


def _read_raw(path: Path) -> str:
    """Đọc giữ nguyên \\r\\n (Python 3.12: Path.read_text chưa nhận newline=)."""
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _write_raw(path: Path, content: str) -> None:
    """Ghi không biến đổi newline."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(content)



@pytest.fixture()
def windows_style_file(tmp_path: Path) -> Path:
    """File 'Windows': UTF-8 BOM + CRLF + nội dung phức tạp ~600 dòng."""
    path = tmp_path / "services.py"
    on_disk = BOM + LineEnding.restore(COMPLEX_MODULE, LineEnding.CRLF)
    path.write_bytes(on_disk.encode("utf-8"))
    return path


def test_full_pipeline_on_complex_windows_file(windows_style_file: Path) -> None:
    """Toàn bộ chu trình engine trên file phức tạp:
    read bytes → decode → strip BOM → detect ending → normalize LF →
    hash (tag) → edit nội dung → hash mới → restore CRLF → ghi lại →
    đọc lại → tag KHÔNG đổi thêm (idempotent), bytes giữ đúng kiểu Windows.
    """
    raw = _read_raw(windows_style_file)

    # --- Bước đọc (giống patcher.read_target) ---
    assert raw.startswith(BOM)
    ending = LineEnding.detect(raw)
    assert ending == LineEnding.CRLF
    text = normalize_to_lf(strip_bom(raw))
    assert "\r" not in text
    tag_before = file_hash(text)

    # --- Bước edit (giống apply_edits trên text LF) ---
    assert "class Service00:" in text
    edited = text.replace(
        "    def method_0(value: int) -> int:",
        "    def method_0(value: int, *, retry: bool = False) -> int:",
        1,
    )
    assert edited != text
    tag_after = file_hash(edited)
    assert tag_after != tag_before
    assert len({tag_before, tag_after}) == 2  # cả hai đều 4-hex hợp lệ

    # --- Bước ghi (giống editor._commit) ---
    _write_raw(windows_style_file, LineEnding.restore(edited, ending))

    # --- Đọc lại: ổn định, không trôi ---
    raw2 = _read_raw(windows_style_file)
    text2 = normalize_to_lf(strip_bom(raw2))
    assert text2 == edited
    assert file_hash(text2) == tag_after          # tag ổn định qua roundtrip
    assert LineEnding.detect(raw2) == LineEnding.CRLF
    assert raw2.count("\r\n") == edited.count("\n")  # mọi \n đều thành \r\n
    assert "retry: bool = False" in text2


def test_hash_stability_after_trailing_ws_noise(windows_style_file: Path) -> None:
    """Formatter只 thêm/xóa trailing whitespace 600 dòng → tag PHẢI giữ nguyên."""
    raw = _read_raw(windows_style_file)
    text = normalize_to_lf(strip_bom(raw))
    noisy = "\n".join(
        line + " \t" * (i % 3) for i, line in enumerate(text.split("\n"))
    )
    assert noisy != text
    assert file_hash(noisy) == file_hash(text)


# ===========================================================================
# 9. Property-style — bất biến trên dữ liệu ngẫu nhiên seeded (deterministic)
# ===========================================================================

_ALPHABET = list("abc \t\r\n«»🎉def():#=-")  # gồm CR, LF, tab, unicode


def _random_texts(count: int, seed: int = 20260928) -> list[str]:
    rng = random.Random(seed)
    return [
        "".join(rng.choice(_ALPHABET) for _ in range(rng.randint(0, 120)))
        for _ in range(count)
    ]


@pytest.mark.parametrize("text", _random_texts(200), ids=lambda t: f"len={len(t)}")
def test_random_normalize_idempotent_and_cr_free(text: str) -> None:
    once = normalize_to_lf(text)
    assert normalize_to_lf(once) == once
    assert "\r" not in once  # CR không thể sống sót qua normalize


@pytest.mark.parametrize("text", _random_texts(200), ids=lambda t: f"len={len(t)}")
def test_random_hash_invariant_across_normalize_restore_cycle(text: str) -> None:
    """Bất biến tổng quát nhất: mọi đường đi (normalize trước hay restore trước)
    đều hội tụ về cùng một dạng LF → cùng một tag."""
    left = file_hash(normalize_to_lf(text))
    right = file_hash(
        normalize_to_lf(LineEnding.restore(normalize_to_lf(text), LineEnding.CRLF))
    )
    assert left == right
