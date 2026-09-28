"""Unit test cho hashline engine — chạy: uv run pytest tests/ -q"""

import pytest

from dino_coding.tools.hashline.apply import apply_edits
from dino_coding.tools.hashline.input import split_patch
from dino_coding.tools.hashline.parser import parse_patch
from dino_coding.tools.hashline.patcher import EditRejected, stage_patch
from dino_coding.tools.hashline.store import EditStore
from dino_coding.tools.hashline.text import file_hash, seen_lines_from_body
from dino_coding.tools.workspace import WorkspacePolicy


def test_file_hash_ignores_trailing_whitespace() -> None:
    assert file_hash("def f():\n    return 1\n") == file_hash("def f():\n    return 1   \n")


def test_file_hash_format_is_4_uppercase_hex() -> None:
    tag = file_hash("hello\n")
    assert len(tag) == 4 and int(tag, 16) >= 0 and tag == tag.upper()


def test_seen_lines_from_body_ranges() -> None:
    body = "1:a\n5-12:b\nplain text\n13:c"
    assert seen_lines_from_body(body) == [1, 5, 12, 13]


def _store_with(path: str, text: str, seen: list[int] | None = None) -> EditStore:
    store = EditStore()
    tag = store.record(path, text, seen)
    return store, tag


def test_replace_range_roundtrip(tmp_path) -> None:
    (tmp_path / "a.py").write_text("one\ntwo\nthree\n")
    store = EditStore()
    tag = store.record("a.py", "one\ntwo\nthree\n", [1, 2, 3])
    workspace = WorkspacePolicy(str(tmp_path))
    patch = split_patch(f"[a.py#{tag}]\nPUT 2.=2:\n+TWO")
    staged = stage_patch(patch, "x", store, workspace)
    assert staged[0].after == "one\nTWO\nthree\n"


def test_insert_before_after(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("b\n")
    store = EditStore()
    tag = store.record("a.txt", "b\n", [1])
    workspace = WorkspacePolicy(str(tmp_path))
    patch = split_patch(f"[a.txt#{tag}]\nPUT >1:\n+after\nPUT <1:\n+before")
    staged = stage_patch(patch, "x", store, workspace)
    assert staged[0].after == "before\nb\nafter\n"


def test_stale_tag_rejected(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("v1\n")
    store, tag = _store_with("a.txt", "v1\n", [1])
    (tmp_path / "a.txt").write_text("v1\nsneaky external change\n")
    workspace = WorkspacePolicy(str(tmp_path))
    patch = split_patch(f"[a.txt#{tag}]\nPUT 1.=1:\n+changed")
    with pytest.raises(EditRejected, match="file changed between read and edit"):
        stage_patch(patch, "x", store, workspace)


def test_unseen_lines_guard(tmp_path) -> None:
    (tmp_path / "big.txt").write_text("".join(f"line{i}\n" for i in range(1, 51)))
    text = "".join(f"line{i}\n" for i in range(1, 51))
    store, tag = _store_with("big.txt", text, seen=[1, 2, 3])  # mới thấy dòng 1-3
    workspace = WorkspacePolicy(str(tmp_path))
    patch = split_patch(f"[big.txt#{tag}]\nPUT 40.=40:\n+hacked")
    with pytest.raises(EditRejected, match="never displayed"):
        stage_patch(patch, "x", store, workspace)
    # Retry sau khi reveal: guard ghi nhận seen mới → thành công
    patch2 = split_patch(f"[big.txt#{tag}]\nPUT 40.=40:\n+hacked")
    staged = stage_patch(patch2, "x2", store, workspace)
    assert staged[0].after.split("\n")[39] == "hacked"


def test_noop_loop_escalates(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("same\n")
    store, tag = _store_with("a.txt", "same\n", [1])
    workspace = WorkspacePolicy(str(tmp_path))
    payload = f"[a.txt#{tag}]\nPUT 1.=1:\n+same"
    for _ in range(2):
        stage_patch(split_patch(payload), payload, store, workspace)  # vẫn OK (soft hint)
    with pytest.raises(EditRejected, match="STOP"):
        stage_patch(split_patch(payload), payload, store, workspace)


def test_cut_paste_register_across_files(tmp_path) -> None:
    (tmp_path / "src.py").write_text("keep\nMOVE ME\nkeep2\n")
    (tmp_path / "dst.py").write_text("header\n")
    store = EditStore()
    tag_src = store.record("src.py", "keep\nMOVE ME\nkeep2\n", [1, 2, 3])
    tag_dst = store.record("dst.py", "header\n", [1])
    workspace = WorkspacePolicy(str(tmp_path))
    patch = split_patch(
        f"[src.py#{tag_src}]\nCUT 2.=2 @fn\n"
        f"[dst.py#{tag_dst}]\nPUT >1 @fn"
    )
    staged = stage_patch(patch, "x", store, workspace)
    assert staged[0].after == "keep\nkeep2\n"
    assert staged[1].after == "header\nMOVE ME\n"
    # stage_patch chỉ tính in-memory; đĩa do editor._commit ghi (nghiệm thu ở mục 6)


def test_rem_and_mv(tmp_path) -> None:
    (tmp_path / "old.txt").write_text("data\n")
    store, tag = _store_with("old.txt", "data\n", [1])
    workspace = WorkspacePolicy(str(tmp_path))
    patch = split_patch(f"[old.txt#{tag}]\nMV renamed.txt")
    staged = stage_patch(patch, "x", store, workspace)
    assert staged[0].op == "move" and staged[0].move_to.endswith("renamed.txt")


def test_apply_edits_bucket_order_stability() -> None:

    parsed = parse_patch("PUT 1.=1:\n+A\nPUT 3.=3:\n+C")
    new_text, first, _ = apply_edits("x\ny\nz\n", parsed.edits)
    assert new_text == "A\ny\nC\n"
    assert first == 1


def test_store_returns_copies_not_internal_state() -> None:
    """store.rs:263 trả `.snapshot.clone()` — port Python phải deepcopy:
    caller mutate snapshot trả về không được phá seen_lines trong store.
    """
    store, tag = _store_with("a.py", "x\n", [1])
    snap = store.by_hash("a.py", tag)
    snap.seen_lines.add(999)  # mutate bản trả về
    assert store.by_hash("a.py", tag).seen_lines == {1}


def test_clipboard_named_register_is_deep_copied() -> None:
    """Clipboard::start_batch bên Rust clone sâu (`named.clone()`) — dict()
    của Python chỉ copy vỏ: phải copy từng list giá trị.
    """
    store = EditStore()
    batch = store.start_clipboard_batch()
    batch.named["reg"] = ["v1"]
    store.commit_clipboard(batch)
    batch.named["reg"].append("mutated-after-commit")  # sửa ngoài batch
    assert store.start_clipboard_batch().named["reg"] == ["v1"]
