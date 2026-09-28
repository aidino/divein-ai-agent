"""Path policy: cô lập mọi thao tác file vào workspace root.

Port rút gọn của crates/pi-edit/src/path_policy.rs.
"""

from __future__ import annotations

import os

from dino_coding.tools.hashline.store import EditStore


class PathOutsideWorkspace(ValueError):
    """Model cố truy cập ngoài workspace root."""


class WorkspacePolicy:
    def __init__(self, root: str) -> None:
        self.root = os.path.realpath(root)
        os.makedirs(self.root, exist_ok=True)

    def resolve(self, display_path: str) -> str:
        """Đường dẫn hiển thị (model-facing) → absolute an toàn."""
        cleaned = display_path.strip().strip("\"'")
        if not cleaned:
            raise PathOutsideWorkspace("Empty path.")
        candidate = os.path.realpath(os.path.join(self.root, cleaned))
        if candidate != self.root and not candidate.startswith(self.root + os.sep):
            raise PathOutsideWorkspace(
                f"Path escapes the workspace root: {display_path}"
            )
        return candidate

    def canonical_key(self, absolute_path: str) -> str:
        """Khóa chuẩn cho EditStore (display path tương đối root)."""
        real = os.path.realpath(absolute_path)
        return os.path.relpath(real, self.root).replace(os.sep, "/")

    def display(self, absolute_path: str) -> str:
        return self.canonical_key(absolute_path)


_WORKSPACE: WorkspacePolicy | None = None


def get_workspace() -> WorkspacePolicy:
    """Singleton policy — root mặc định `$DINO_WORKSPACE` hoặc `./workspace`."""
    global _WORKSPACE
    if _WORKSPACE is None:
        root = os.getenv("DINO_WORKSPACE", os.path.join(os.getcwd(), "workspace"))
        _WORKSPACE = WorkspacePolicy(root)
    return _WORKSPACE


_STORE: EditStore | None = None


def get_store() -> EditStore:
    """Singleton EditStore dùng chung bởi read/write/edit."""
    global _STORE

    if _STORE is None:
        _STORE = EditStore()
    return _STORE
