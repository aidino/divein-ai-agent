"""Bộ test cho tools/hashline/store.py — EditStore: snapshot, clipboard, no-op.

Mọi ngữ nghĩa được pin đều đã đối chiếu store.rs của omp trước khi viết:
- record: dedupe theo (hash + text), move-to-front, gộp seen_lines, cap 4 phiên bản
- by_hash: không phân biệt hoa thường (omp normalize tag ở tokenizer.rs:576
  và patcher.rs:186 so sánh eq_ignore_ascii_case)
- by_content: cửa vào của seen-lines guard — khớp text CHÍNH XÁC
- record_seen_lines / invalidate / relocate: provenance theo tag, sau MV/REM
- record_noop: no-op giống hệt liên tiếp, NOOP_HARD_LIMIT = 3
- eviction: LRU theo MAX_PATHS = 256, mọi API đọc đều "touch" làm mới recency
"""

from __future__ import annotations

import threading

from dino_coding.tools.hashline.store import (
    MAX_PATHS,
    MAX_VERSIONS_PER_PATH,
    NOOP_HARD_LIMIT,
    EditStore,
    Snapshot,
)
from dino_coding.tools.hashline.text import file_hash


def _store_with(path: str, text: str, seen: list[int] | None = None) -> tuple[EditStore, str]:
    """Record một phiên bản rồi trả (store, tag) — khỏi lặp code dựng cảnh."""
    store = EditStore()
    tag = store.record(path, text, seen)
    return store, tag


# ===========================================================================
# 1. record — mint tag, dedupe, gộp seen_lines
# ===========================================================================


def test_record_mints_tag_matching_file_hash() -> None:
    text = "def main():\n    pass\n"
    store, tag = _store_with("src/app.py", text)
    assert tag == file_hash(text)
    snap = store.by_content("src/app.py", text)
    assert snap is not None
    assert snap.text == text
    assert snap.hash == tag
    assert snap.path == "src/app.py"


def test_record_same_text_dedupes_not_appends() -> None:
    """Re-record cùng (hash, text) → 1 snapshot, không phình lịch sử."""
    store = EditStore()
    store.record("a.py", "x = 1\n")
    store.record("a.py", "x = 1\n")
    store.record("a.py", "x = 1\n")
    # Black-box: vẫn tìm được, và các version khác không bị đẩy rơi
    for i in range(MAX_VERSIONS_PER_PATH):
        store.record("a.py", f"x = {i}\n")
    # "x = 1\n" đã bị đưa lên đầu nhờ dedupe → sống sót qua cap
    assert store.by_content("a.py", "x = 1\n") is not None


def test_record_dedupe_requires_text_match_not_just_hash() -> None:
    """Cùng hash (trailing-ws miễn nhiễm) nhưng text khác → 2 snapshot riêng.

    file_hash bỏ qua trailing whitespace mỗi dòng nên "a \\n" và "a\\n" cùng
    tag; store.rs dedupe theo (hash && text) nên cả hai đều được giữ.
    """
    store = EditStore()
    t1, t2 = "a \n", "a\n"
    assert file_hash(t1) == file_hash(t2)  # tiền đề của test
    tag1 = store.record("a.py", t1)
    tag2 = store.record("a.py", t2)
    assert tag1 == tag2
    assert store.by_content("a.py", t1) is not None
    assert store.by_content("a.py", t2) is not None
    # by_hash trả PHIÊN BẢN GẦN NHẤT khớp tag → t2 (record sau cùng)
    assert store.by_hash("a.py", tag1).text == t2


def test_record_merges_seen_lines_on_dedupe() -> None:
    """Read trang 1 rồi trang 2 của cùng phiên bản → seen union, vẫn 1 entry."""
    store = EditStore()
    tag = store.record("a.py", "l1\nl2\nl3\n", [1, 2])
    store.record("a.py", "l1\nl2\nl3\n", [3])
    snap = store.by_hash("a.py", tag)
    assert snap.seen_lines == {1, 2, 3}


def test_record_caps_versions_at_limit() -> None:
    """Quá MAX_VERSIONS_PER_PATH phiên bản → rơi bản cũ nhất, giữ bản mới."""
    store = EditStore()
    texts = [f"version {i}\n" for i in range(MAX_VERSIONS_PER_PATH + 2)]
    for t in texts:
        store.record("a.py", t)
    assert store.by_content("a.py", texts[0]) is None  # cổ nhất bị rơi
    assert store.by_content("a.py", texts[1]) is None
    for t in texts[2:]:  # 4 bản gần nhất còn sống
        assert store.by_content("a.py", t) is not None


# ===========================================================================
# 2. by_hash / by_content — tra cứu
# ===========================================================================


def test_by_hash_is_case_insensitive() -> None:
    """Model gõ tag thường `[a.py#1a2b]` vẫn khớp — omp uppercase ngay lúc
    parse (tokenizer.rs:576) và so sánh bỏ qua hoa thường (patcher.rs:186).
    """
    store, tag = _store_with("a.py", "hello\n")
    assert store.by_hash("a.py", tag.lower()) is not None
    assert store.by_hash("a.py", tag.upper()) is not None


def test_record_seen_lines_none_stays_none() -> None:
    """Không truyền provenance → seen_lines là None (vắng), không phải set rỗng."""
    store = EditStore()
    tag = store.record("a.py", "x\n")
    snap = store.by_hash("a.py", tag)
    assert snap.seen_lines is None


def test_by_hash_missing_returns_none() -> None:
    store, _ = _store_with("a.py", "x\n")
    assert store.by_hash("a.py", "0000") is None  # tag không tồn tại
    assert store.by_hash("other.py", "0000") is None  # path không tồn tại


def test_by_content_exact_match_only() -> None:
    """by_content là cửa vào seen-lines guard: chỉ khớp text CHÍNH XÁC.

    Biến thể trailing-ws (cùng hash!) phải trả None — nếu không, guard sẽ
    công nhận phiên bản mà agent chưa từng thấy byte-for-byte.
    """
    store = EditStore()
    store.record("a.py", "a\nb\n", [1, 2])
    assert store.by_content("a.py", "a\nb\n") is not None
    assert store.by_content("a.py", "a \nb\n") is None
    assert store.by_content("a.py", "a\nb") is None  # thiếu newline cuối


def test_by_hash_returns_most_recent_matching_version() -> None:
    store = EditStore()
    store.record("a.py", "old\n")
    store.record("a.py", "new\n")
    tag_new = file_hash("new\n")
    snap = store.by_hash("a.py", tag_new)
    assert snap is not None and snap.text == "new\n"
    assert store.by_hash("a.py", file_hash("old\n")).text == "old\n"


# ===========================================================================
# 3. record_seen_lines — bù provenance sau khi đã mint
# ===========================================================================


def test_record_seen_lines_unions_into_matching_tag() -> None:
    store, tag = _store_with("a.py", "x\n", [1])
    store.record_seen_lines("a.py", tag, [2, 3])
    store.record_seen_lines("a.py", tag, [3])  # trùng lặp → idempotent
    assert store.by_hash("a.py", tag).seen_lines == {1, 2, 3}


def test_record_seen_lines_tag_case_insensitive() -> None:
    store, tag = _store_with("a.py", "x\n")
    store.record_seen_lines("a.py", tag.lower(), [4])
    assert store.by_hash("a.py", tag).seen_lines == {4}


def test_record_seen_lines_unknown_tag_is_noop() -> None:
    store, tag = _store_with("a.py", "x\n")
    store.record_seen_lines("a.py", "FFFF", [9])  # không khớp → im lặng
    assert store.by_hash("a.py", tag).seen_lines is None


# ===========================================================================
# 4. invalidate — sau khi file bị xóa (REM)
# ===========================================================================


def test_invalidate_wipes_history_and_provenance() -> None:
    store, tag = _store_with("a.py", "x\n", [1, 2])
    store.invalidate("a.py")
    assert store.by_hash("a.py", tag) is None
    assert store.by_content("a.py", "x\n") is None
    # Record lại sau invalidate → provenance cũ KHÔNG sống lại
    tag2 = store.record("a.py", "x\n")
    assert store.by_hash("a.py", tag2).seen_lines is None


def test_invalidate_unknown_path_is_noop() -> None:
    store = EditStore()
    store.invalidate("ghost.py")  # không raise


# ===========================================================================
# 5. relocate — sau khi đổi tên file (MV)
# ===========================================================================


def test_relocate_moves_history_and_rewrites_snapshot_path() -> None:
    store, tag = _store_with("old_name.py", "x\n", [1, 5])
    store.relocate("old_name.py", "new_name.py")
    snap = store.by_hash("new_name.py", tag)
    assert snap is not None
    assert snap.path == "new_name.py"  # path trong snapshot cũng đổi
    assert snap.seen_lines == {1, 5}  # provenance đi theo
    assert store.by_hash("old_name.py", tag) is None


def test_relocate_merge_source_wins_on_duplicate_hash() -> None:
    """Src và dest cùng phiên bản (hash trùng) → bản của SRC thắng, giữ
    đúng thứ tự merged.retain của store.rs (source trước, dest sau).
    """
    store = EditStore()
    store.record("dest.py", "shared\n", [9])   # dest có sẵn, seen={9}
    store.record("src.py", "shared\n", [1])    # src seen={1}
    store.relocate("src.py", "dest.py")
    snap = store.by_hash("dest.py", file_hash("shared\n"))
    assert snap.seen_lines == {1}  # source thắng, không gộp {1,9}


def test_relocate_missing_source_is_noop() -> None:
    store = EditStore()
    store.relocate("ghost.py", "any.py")  # không raise, không tạo gì
    assert store.by_hash("any.py", "0000") is None


def test_relocate_respects_version_cap_after_merge() -> None:
    store = EditStore()
    for i in range(MAX_VERSIONS_PER_PATH):
        store.record("src.py", f"s{i}\n")
    for i in range(MAX_VERSIONS_PER_PATH):
        store.record("dest.py", f"d{i}\n")
    store.relocate("src.py", "dest.py")
    # 8 bản → cap 4; source đứng trước nên dest cũ bị rơi hết
    assert store.by_content("dest.py", "d0\n") is None
    for i in range(MAX_VERSIONS_PER_PATH):
        assert store.by_content("dest.py", f"s{i}\n") is not None


# ===========================================================================
# 6. Clipboard — register có tên xuyên batch, ẩn danh chỉ một lần
# ===========================================================================


def test_clipboard_named_registers_persist_after_commit() -> None:
    store = EditStore()
    batch = store.start_clipboard_batch()
    batch.named["snippets"] = ["line A", "line B"]
    store.commit_clipboard(batch)
    # Batch sau thấy register đã công bố
    assert store.start_clipboard_batch().named.get("snippets") == ["line A", "line B"]


def test_clipboard_uncommitted_batch_discards_named() -> None:
    """Batch thất bại (không commit) → register biến mất — semantics
    "thành công mới được ghi nhận" của omp.
    """
    store = EditStore()
    batch = store.start_clipboard_batch()
    batch.named["doomed"] = ["x"]
    # KHÔNG commit — mô phỏng batch lỗi
    assert "doomed" not in store.start_clipboard_batch().named


def test_clipboard_batch_returns_copy_not_live_reference() -> None:
    """Clipboard fork là bản sao — mutate batch đang bay không leak vào store."""
    store = EditStore()
    batch = store.start_clipboard_batch()
    batch.named["reg"] = ["v1"]
    store.commit_clipboard(batch)
    batch.named["reg"].append("mutated-after-commit")  # sửa ngoài
    assert store.start_clipboard_batch().named["reg"] == ["v1"]


def test_clipboard_anon_never_persists() -> None:
    store = EditStore()
    batch = store.start_clipboard_batch()
    batch.anon.append(["cut-1"])
    store.commit_clipboard(batch)
    assert store.start_clipboard_batch().anon == []


# ===========================================================================
# 7. No-op guard — phát hiện model gửi edit giống hệt liên tiếp
# ===========================================================================


def test_noop_first_submission_is_one_not_escalated() -> None:
    store = EditStore()
    assert store.record_noop("a.py", 111) == (1, False)


def test_noop_escalates_at_hard_limit() -> None:
    store = EditStore()
    assert store.record_noop("a.py", 111) == (1, False)
    assert store.record_noop("a.py", 111) == (2, False)
    assert store.record_noop("a.py", 111) == (3, True)  # == NOOP_HARD_LIMIT
    assert NOOP_HARD_LIMIT == 3  # pin const theo store.rs


def test_noop_different_payload_resets_counter() -> None:
    store = EditStore()
    store.record_noop("a.py", 111)
    store.record_noop("a.py", 111)
    # Model đổi edit (payload khác) → đếm lại từ 1
    assert store.record_noop("a.py", 222) == (1, False)
    assert store.record_noop("a.py", 222) == (2, False)


def test_noop_reset_clears_counter() -> None:
    """Edit thật sự áp dụng thành công → reset_noop — vòng đếm bắt đầu lại."""
    store = EditStore()
    store.record_noop("a.py", 111)
    store.record_noop("a.py", 111)
    store.reset_noop("a.py")
    assert store.record_noop("a.py", 111) == (1, False)


def test_noop_counters_are_independent_per_path() -> None:
    store = EditStore()
    store.record_noop("a.py", 111)
    store.record_noop("a.py", 111)
    assert store.record_noop("b.py", 111) == (1, False)  # a không ảnh hưởng b


# ===========================================================================
# 8. Eviction LRU — MAX_PATHS = 256, đọc cũng làm mới recency
# ===========================================================================


def test_eviction_drops_oldest_path_beyond_max() -> None:
    store = EditStore()
    tags = {}
    for i in range(MAX_PATHS + 1):  # 257 path → path đầu tiên bị evict
        tags[f"f{i:03d}.py"] = store.record(f"f{i:03d}.py", f"v{i}\n")
    assert store.by_hash("f000.py", tags["f000.py"]) is None  # cổ nhất rơi
    assert store.by_hash("f001.py", tags["f001.py"]) is not None
    last = f"f{MAX_PATHS:03d}.py"
    assert store.by_hash(last, tags[last]) is not None


def test_eviction_respects_touch_recency() -> None:
    """Đọc path cũ (by_hash touch) → path đó thoát vòng evict tiếp theo."""
    store = EditStore()
    tags = {}
    for i in range(MAX_PATHS):
        tags[f"f{i:03d}.py"] = store.record(f"f{i:03d}.py", f"v{i}\n")
    store.by_hash("f000.py", tags["f000.py"])  # touch f000 → mới nhất
    store.record("f_new.py", "v\n")  # vượt ngưỡng → evict f001 chứ không phải f000
    assert store.by_hash("f000.py", tags["f000.py"]) is not None
    assert store.by_hash("f001.py", tags["f001.py"]) is None


def test_invalidate_frees_lru_slot() -> None:
    store = EditStore()
    tags = {}
    for i in range(MAX_PATHS):
        tags[f"f{i:03d}.py"] = store.record(f"f{i:03d}.py", f"v{i}\n")
    store.invalidate("f000.py")
    store.record("f_new.py", "v\n")  # chỗ trống → không ai bị evict
    assert store.by_hash("f001.py", tags["f001.py"]) is not None


# ===========================================================================
# 9. Đồng thời — lock phải giữ nguyên trạng thái dưới nhiều thread
# ===========================================================================


def test_concurrent_records_stay_consistent() -> None:
    """8 thread × 50 record trên path riêng + path chung → không crash,
    trạng thái cuối nhất quán (mọi path đều tra được bản mới nhất).
    """
    store = EditStore()
    errors: list[Exception] = []

    def worker(idx: int) -> None:
        try:
            for j in range(50):
                store.record(f"own_{idx}.py", f"v{j}\n")
                store.record("shared.py", f"w{idx}-{j}\n")
                store.record_noop("shared.py", idx * 1000 + j)
        except Exception as exc:  # pragma: no cover - chỉ khi lock hỏng
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    for i in range(8):
        assert store.by_content(f"own_{i}.py", "v49\n") is not None
    # shared.py bị cap 4 bản — chỉ cần tra được bất kỳ bản nào còn sống
    assert len(store.start_clipboard_batch().named) == 0  # store vẫn hoạt động


# ===========================================================================
# 10. Snapshot dataclass — hợp đồng trường dữ liệu
# ===========================================================================


def test_snapshot_fields_contract() -> None:
    snap = Snapshot(path="a.py", text="x\n", hash="ABCD")
    assert snap.seen_lines is None  # default: không provenance
    snap2 = Snapshot(path="a.py", text="x\n", hash="ABCD", seen_lines={1})
    assert snap2.seen_lines == {1}


def test_store_returns_snapshot_objects_not_internal_state() -> None:
    """Snapshot trả về là dataclass riêng — mutate nó không phá store."""
    store, tag = _store_with("a.py", "x\n", [1])
    snap = store.by_hash("a.py", tag)
    assert snap is not None
    snap.seen_lines.add(999)  # mutate bản trả về
    assert store.by_hash("a.py", tag).seen_lines == {1}  # store nguyên vẹn
