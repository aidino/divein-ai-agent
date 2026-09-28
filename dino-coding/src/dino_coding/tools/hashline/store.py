"""EditStore: snapshot phiên bản file, clipboard registers, vòng lặp no-op.

Port rút gọn của crates/pi-edit/src/store.rs (một instance dùng chung cả session).
"""

from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field
from typing import Optional

from dino_coding.tools.hashline.text import file_hash

# ← port các hằng số store.rs
MAX_PATHS = 256                 # DEFAULT_MAX_PATHS
MAX_VERSIONS_PER_PATH = 4       # DEFAULT_MAX_VERSIONS_PER_PATH
MAX_SNAPSHOT_FILE_BYTES = 4 * 1024 * 1024  # file lớn hơn không bao giờ snapshot
NOOP_HARD_LIMIT = 3             # no-op giống hệt liên tiếp → leo thang lỗi


@dataclass
class Snapshot:
    """Một phiên bản toàn văn của file tại một thời điểm. ← port store::Snapshot"""
    path: str
    text: str
    hash: str
    seen_lines: Optional[set[int]] = None  # None = không ghi provenance


@dataclass
class Clipboard:
    """Clipboard xâu xuyên một lần apply; register có tên tồn tại qua các lần gọi.
    ← port store::Clipboard
    """
    anon: list[list[str]] = field(default_factory=list)      # các CUT ẩn danh pendings
    named: dict[str, list[str]] = field(default_factory=dict)


class EditStore:
    """Bộ nhớ chia sẻ vòng đời session. ← port store::EditStore"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._histories: dict[str, list[Snapshot]] = {}
        self._clipboard_named: dict[str, list[str]] = {}
        self._noop: dict[str, tuple[int, int]] = {}
        self._order: list[str] = []  # FIFO cho eviction

    # ---------- snapshot ----------

    def record(self, path: str, text: str, seen_lines: Optional[list[int]] = None) -> str:
        """Ghi nhận một phiên bản text dưới path chuẩn, trả về tag. ← port EditStore::record

        Nếu phiên bản (hash + text) đã tồn tại: đưa lên đầu lịch sử và gộp seen_lines.
        """
        tag = file_hash(text)
        with self._lock:
            versions = self._histories.setdefault(path, [])
            for i, snap in enumerate(versions):
                if snap.hash == tag and snap.text == text:
                    moved = versions.pop(i)
                    self._merge_seen(moved, seen_lines)
                    versions.insert(0, moved)
                    self._touch(path)
                    return tag
            snap = Snapshot(path=path, text=text, hash=tag, seen_lines=None)
            self._merge_seen(snap, seen_lines)
            versions.insert(0, snap)
            del versions[MAX_VERSIONS_PER_PATH:]
            self._touch(path)
            self._evict()
            return tag

    def by_hash(self, path: str, tag: str) -> Optional[Snapshot]:
        """Phiên bản gần nhất khớp tag (không phân biệt hoa thường).

        Trả về BẢN SAO — store.rs:263 `.map(|v| v.snapshot.clone())`;
        caller mutate snapshot trả về không phá trạng thái nội bộ.
        """
        with self._lock:
            self._touch(path)
            for snap in self._histories.get(path, []):
                if snap.hash.upper() == tag.upper():
                    return copy.deepcopy(snap)
        return None

    def by_content(self, path: str, text: str) -> Optional[Snapshot]:
        """Phiên bản có text khớp chính xác — cửa vào của seen-lines guard."""
        with self._lock:
            self._touch(path)
            for snap in self._histories.get(path, []):
                if snap.text == text:
                    return copy.deepcopy(snap)
        return None

    def record_seen_lines(self, path: str, tag: str, lines: list[int]) -> None:
        """Gộp thêm dòng đã hiển thị vào phiên bản khớp tag. ← port EditStore::record_seen_lines"""
        with self._lock:
            self._touch(path)
            for snap in self._histories.get(path, []):
                if snap.hash.upper() == tag.upper():
                    self._merge_seen(snap, lines)
                    return

    def invalidate(self, path: str) -> None:
        """Xóa lịch sử một path (sau khi file bị REM)."""
        with self._lock:
            self._histories.pop(path, None)
            if path in self._order:
                self._order.remove(path)

    def relocate(self, src: str, dest: str) -> None:
        """Chuyển lịch sử source sang destination (sau MV). ← port EditStore::relocate"""
        with self._lock:
            source = self._histories.pop(src, None)
            if source is None:
                return
            for snap in source:
                snap.path = dest
            existing = self._histories.pop(dest, [])
            merged, seen_tags = [], set()
            for snap in source + existing:
                if snap.hash not in seen_tags:
                    seen_tags.add(snap.hash)
                    merged.append(snap)
            self._histories[dest] = merged[:MAX_VERSIONS_PER_PATH]
            if src in self._order:
                self._order.remove(src)
            self._touch(dest)

    # ---------- clipboard ----------

    def start_clipboard_batch(self) -> Clipboard:
        """Bắt đầu một batch với các register có tên đã lưu. ← port EditStore::start_clipboard_batch

        Rust clone sâu (Clipboard::start_batch: `named: source.named.clone()`);
        Python phải copy từng list giá trị — `dict(...)` chỉ copy vỏ ngoài.
        """
        with self._lock:
            return Clipboard(
                anon=[],
                named={name: list(lines) for name, lines in self._clipboard_named.items()},
            )

    def commit_clipboard(self, batch: Clipboard) -> None:
        """Công bố register có tên sau khi batch thành công. ← port commit_clipboard

        commit_from bên Rust cũng clone (`extend(named.clone())`) — batch đã
        công bố tách rời khỏi register trong store.
        """
        with self._lock:
            self._clipboard_named.update(
                {name: list(lines) for name, lines in batch.named.items()}
            )

    # ---------- no-op guard ----------

    def record_noop(self, path: str, payload: int) -> tuple[int, bool]:
        """Đếm no-op giống hệt liên tiếp. ← port EditStore::record_noop

        Trả về (số lần liên tiếp, đã chạm ngưỡng NOOP_HARD_LIMIT?).
        """
        with self._lock:
            prev_hash, count = self._noop.get(path, (payload, 0))
            count = count + 1 if prev_hash == payload else 1
            self._noop[path] = (payload, count)
            return count, count >= NOOP_HARD_LIMIT

    def reset_noop(self, path: str) -> None:
        with self._lock:
            self._noop.pop(path, None)

    # ---------- nội bộ ----------

    @staticmethod
    def _merge_seen(snap: Snapshot, lines: Optional[list[int]]) -> None:
        if lines is None:
            return
        if snap.seen_lines is None:
            snap.seen_lines = set()
        snap.seen_lines.update(lines)

    def _touch(self, path: str) -> None:
        if path in self._order:
            self._order.remove(path)
        self._order.append(path)

    def _evict(self) -> None:
        while len(self._order) > MAX_PATHS:
            oldest = self._order.pop(0)
            self._histories.pop(oldest, None)
