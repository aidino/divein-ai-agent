"""Chuẩn hóa văn bản và content-hash cho hashline engine.

Port rút gọn của crates/pi-edit/src/text.rs và store::file_hash.
Không module nào trong đây được chạm filesystem.
"""

from __future__ import annotations

BOM=""
