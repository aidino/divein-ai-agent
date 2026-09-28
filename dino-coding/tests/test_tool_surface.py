"""Test bề mặt tool: tokenizer, diffpreview, messages, workspace policy,
và E2E read → write → edit (không cần LLM — gọi tool trực tiếp).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dino_coding.tools import workspace as ws_mod
from dino_coding.tools.editor import edit
from dino_coding.tools.fs import read, write
from dino_coding.tools.hashline import messages
from dino_coding.tools.hashline.diffpreview import compact_preview
from dino_coding.tools.hashline.tokenizer import (
    classify_line,
    is_op_line,
    parse_header,
    parse_hunk_header,
    target_register,
)
from dino_coding.tools.workspace import PathOutsideWorkspace, WorkspacePolicy


# ===========================================================================
# 1. Tokenizer — phân loại dòng & parse op header
# ===========================================================================


class TestParseHeader:
    def test_full_header(self) -> None:
        assert parse_header("[src/app.py#A1B2]") == ("src/app.py", "A1B2")

    def test_lowercase_tag_normalized_uppercase(self) -> None:
        assert parse_header("[a.py#ab12]") == ("a.py", "AB12")

    def test_bare_path_no_tag(self) -> None:
        assert parse_header("[a.py]") == ("a.py", None)

    def test_plain_line_is_not_header(self) -> None:
        assert parse_header("PUT 1.=1:") is None
        assert parse_header("hello") is None


class TestParseHunkHeader:
    def test_replace_range(self) -> None:
        target, takes_body = parse_hunk_header("PUT 1.=2 @r:")
        assert takes_body is True
        assert target.range.start.line == 1 and target.range.end.line == 2
        assert target_register(target) == "r"

    def test_insert_before_after(self) -> None:
        before, _ = parse_hunk_header("PUT <3:")
        after, _ = parse_hunk_header("PUT >4:")
        assert before.anchor.line == 3
        assert after.anchor.line == 4

    def test_eof_and_register(self) -> None:
        target, takes_body = parse_hunk_header("PUT >$ @x:")
        assert target_register(target) == "x"
        assert takes_body is True

    def test_cut_captures_register_and_takes_no_body(self) -> None:
        target, takes_body = parse_hunk_header("CUT 2.=5 @fn")
        assert takes_body is False
        assert target_register(target) == "fn"
        assert target.range.start.line == 2 and target.range.end.line == 5

    def test_bare_cut(self) -> None:
        target, takes_body = parse_hunk_header("CUT 4.=4")
        assert target_register(target) is None
        assert takes_body is False

    def test_body_lines_are_not_ops(self) -> None:
        assert is_op_line("PUT 1.=1:")
        assert is_op_line("CUT 2.=3")
        assert not is_op_line("+body row")
        assert not is_op_line("plain text")


class TestClassifyLine:
    def test_all_five_kinds(self) -> None:
        assert classify_line("[a.py#ABCD]", 1).__class__.__name__ == "HeaderToken"
        assert classify_line("PUT 1.=1:", 2).__class__.__name__ == "OpToken"
        assert classify_line("+payload", 3).__class__.__name__ == "PayloadToken"
        assert classify_line("plain", 4).__class__.__name__ == "RawToken"
        assert classify_line("", 5).__class__.__name__ == "BlankToken"

    def test_payload_strips_plus_sign(self) -> None:
        token = classify_line("+    indented()", 7)
        assert token.text == "    indented()"


# ===========================================================================
# 1b. Parser — contamination guard
# ===========================================================================


class TestContaminationCheck:
    """← tests cho _contamination_check (port parser.rs::contamination_message)."""

    def _check(self, text: str, line_num: int = 1) -> None:
        from dino_coding.tools.hashline.parser import Executor
        ex = Executor()
        ex._contamination_check(text, line_num)

    def test_apply_patch_sentinel_rejected(self) -> None:
        for sentinel in [
            "*** Update File: src/app.py",
            "*** Add File: new.py",
            "*** Delete File: old.py",
            "*** Move to: dest.py",
        ]:
            with pytest.raises(ValueError, match="apply_patch sentinel"):
                self._check(sentinel)

    def test_unified_diff_hunk_rejected(self) -> None:
        with pytest.raises(ValueError, match="unified-diff hunk header"):
            self._check("@@ -10,5 +10,7 @@")

    def test_at_at_brackets_rejected(self) -> None:
        with pytest.raises(ValueError, match="bracketed hunk header"):
            self._check("@@ something else @@")

    def test_lone_number_rejected(self) -> None:
        with pytest.raises(ValueError, match="hunk headers need a verb"):
            self._check("42")

    def test_bare_two_number_range_rejected(self) -> None:
        with pytest.raises(ValueError, match="bare range hunk header"):
            self._check("3 5:")

    def test_clean_text_passes(self) -> None:
        # Các dòng hợp lệ không nên gây lỗi
        self._check("def hello():")
        self._check("import os")
        self._check("# comment")
        self._check("  ")  # whitespace-only


# ===========================================================================
# 2. diffpreview — nén diff `±N|`
# ===========================================================================


class TestCompactPreview:
    def test_replacement_rows(self) -> None:
        out = compact_preview(["a", "b"], ["a", "B"])
        assert out == "-2|b\n+2|B"

    def test_pure_insert(self) -> None:
        out = compact_preview(["a"], ["a", "b", "c"])
        assert out == "+2|b\n+3|c"

    def test_pure_delete(self) -> None:
        out = compact_preview(["a", "b", "c"], ["a"])
        assert out == "-2|b\n-3|c"

    def test_identical_inputs_produce_empty_preview(self) -> None:
        assert compact_preview(["x", "y"], ["x", "y"]) == ""

    def test_truncation_keeps_head_and_tail(self) -> None:
        before = [f"old{i}" for i in range(50)]
        after = [f"new{i}" for i in range(50)]
        out = compact_preview(before, after, max_rows=10)
        assert "… (" in out and "more rows)" in out
        assert out.count("\n") == 10  # đúng max_rows dòng


# ===========================================================================
# 3. messages — chuỗi model-facing (giữ nguyên tiếng Anh)
# ===========================================================================


class TestMessages:
    def test_missing_snapshot_tag_mentions_path_and_hint(self) -> None:
        text = messages.missing_snapshot_tag_message("a.py")
        assert "a.py" in text and "read" in text

    def test_format_numbered_line(self) -> None:
        assert messages.format_numbered_line(3, "hi") == "3:hi"

    def test_no_change_diagnostic_names_path(self) -> None:
        assert "a.py" in messages.no_change_diagnostic("a.py")

    def test_out_of_range_reports_both_numbers(self) -> None:
        text = messages.format_out_of_range(99, 10)
        assert "99" in text and "10 lines" in text

    def test_unseen_lines_message_lists_numbers(self) -> None:
        text = messages.unseen_lines_message(
            path="a.py",
            unseen=[7, 9],
            tag="ABCD",
            revealed=[(7, "line seven")],
            truncated=False,
        )
        assert "7" in text and "9" in text and "ABCD" in text and "a.py" in text

    def test_model_facing_strings_are_english(self) -> None:
        """Chuỗi model-facing phải tiếng Anh — models được train trên chúng."""
        assert messages.missing_snapshot_tag_message("a.py").isascii()
        assert messages.format_out_of_range(3, 9).isascii()


# ===========================================================================
# 4. WorkspacePolicy — cô lập path
# ===========================================================================


class TestWorkspacePolicy:
    def test_resolve_inside_root(self, tmp_path: Path) -> None:
        policy = WorkspacePolicy(str(tmp_path))
        resolved = policy.resolve("src/app.py")
        assert resolved == str(tmp_path / "src" / "app.py")

    def test_escape_with_dotdot_rejected(self, tmp_path: Path) -> None:
        policy = WorkspacePolicy(str(tmp_path))
        with pytest.raises(PathOutsideWorkspace):
            policy.resolve("../outside.py")

    def test_absolute_path_outside_rejected(self, tmp_path: Path) -> None:
        policy = WorkspacePolicy(str(tmp_path))
        with pytest.raises(PathOutsideWorkspace):
            policy.resolve("/etc/passwd")

    def test_empty_path_rejected(self, tmp_path: Path) -> None:
        policy = WorkspacePolicy(str(tmp_path))
        with pytest.raises(PathOutsideWorkspace):
            policy.resolve("   ")

    def test_surrounding_quotes_stripped(self, tmp_path: Path) -> None:
        policy = WorkspacePolicy(str(tmp_path))
        assert policy.resolve('"a.py"') == str(tmp_path / "a.py")

    def test_canonical_key_is_forward_slash_relative(self, tmp_path: Path) -> None:
        policy = WorkspacePolicy(str(tmp_path))
        key = policy.canonical_key(str(tmp_path / "src" / "deep" / "a.py"))
        assert key == "src/deep/a.py"


# ===========================================================================
# 5. E2E tools read/write/edit — workspace thật, không LLM
# ===========================================================================


@pytest.fixture()
def agent_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Trỏ singleton workspace/store vào tmp — sạch cho mỗi test."""
    monkeypatch.setenv("DINO_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(ws_mod, "_WORKSPACE", None)
    monkeypatch.setattr(ws_mod, "_STORE", None)
    return tmp_path


def _read_result(path: str, **kwargs: int) -> str:
    return read.invoke({"path": path, **kwargs})


def _write_result(path: str, content: str) -> str:
    return write.invoke({"path": path, "content": content})


def _edit_result(patch: str) -> str:
    return edit.invoke({"input": patch})


def _header_of(tool_output: str) -> str:
    return tool_output.splitlines()[0]


class TestReadTool:
    def test_missing_file_error_mentions_write(self, agent_workspace: Path) -> None:
        out = _read_result("ghost.py")
        assert out.startswith("Error:") and "write" in out

    def test_numbered_rows_and_header(self, agent_workspace: Path) -> None:
        _write_result("a.py", "one\ntwo\nthree\n")
        out = _read_result("a.py")
        assert _header_of(out).startswith("[a.py#")
        assert out.splitlines()[1:] == ["1:one", "2:two", "3:three"]

    def test_pagination_and_continue_notice(self, agent_workspace: Path) -> None:
        content = "".join(f"line{i}\n" for i in range(1, 11))
        _write_result("ten.txt", content)
        page1 = _read_result("ten.txt", offset=1, limit=4)
        assert "1:line1" in page1 and "4:line4" in page1
        assert "Use offset=5" in page1
        page2 = _read_result("ten.txt", offset=5, limit=4)
        assert "5:line5" in page2 and "8:line8" in page2

    def test_bom_and_crlf_are_normalized_in_output(self, agent_workspace: Path) -> None:
        raw = "\ufefffirst\r\nsecond\r\n"
        (agent_workspace / "win.py").write_bytes(raw.encode("utf-8"))
        out = _read_result("win.py")
        assert "1:first" in out and "2:second" in out
        assert "\r" not in out

    def test_large_python_file_summarized_to_outline(self, agent_workspace: Path) -> None:
        body = "".join(
            f"def fn_{i}(x):\n    y = {i}\n    return y + x\n\n" for i in range(40)
        )
        _write_result("big.py", body)  # 160 dòng ≥ SUMMARY_MIN_LINES
        out = _read_result("big.py")
        assert "def fn_0(x):" in out          # xương được giữ
        assert "def fn_39(x):" in out
        assert "elided" in out                 # notice vùng gấp
        assert "return y + x" not in out       # thân hàm bị gấp
        # Dòng outline là anchor hợp lệ; dòng bị gấp KHÔNG được đánh số
        assert "2:" not in out

    def test_explicit_range_bypasses_summary(self, agent_workspace: Path) -> None:
        body = "".join(f"line{i}\n" for i in range(1, 151))
        _write_result("big.txt", body)
        out = _read_result("big.txt", offset=10, limit=5)
        assert "10:line10" in out and "14:line14" in out
        assert "elided" not in out


class TestWriteTool:
    def test_create_returns_header_for_edit(self, agent_workspace: Path) -> None:
        out = _write_result("new.py", "x = 1\n")
        assert out.startswith("Created new.py")
        assert "[new.py#" in out
        assert (agent_workspace / "new.py").read_text(encoding="utf-8") == "x = 1\n"

    def test_overwrite_verb_and_crlf_normalized(self, agent_workspace: Path) -> None:
        _write_result("b.txt", "old\n")
        out = _write_result("b.txt", "a\r\nb\r\n")
        assert out.startswith("Overwrote")
        assert (agent_workspace / "b.txt").read_bytes() == b"a\nb\n"

    def test_trailing_newline_added_if_missing(self, agent_workspace: Path) -> None:
        _write_result("c.txt", "no newline")
        assert (agent_workspace / "c.txt").read_bytes() == b"no newline\n"

    def test_escape_path_rejected(self, agent_workspace: Path) -> None:
        out = _write_result("../evil.txt", "x\n")
        assert out.startswith("Error:")


class TestEditToolE2E:
    def test_full_cycle_write_read_edit(self, agent_workspace: Path) -> None:
        _write_result("calc.py", "def calc():\n    return 1\n")
        tag = _header_of(_read_result("calc.py")).split("#")[1].rstrip("]")
        out = _edit_result(
            f"[calc.py#{tag}]\nPUT 2.=2:\n+    return 42"
        )
        assert out.startswith("[calc.py#")            # tag mới cho lần sau
        assert "42" in out                             # preview có nội dung mới
        assert (agent_workspace / "calc.py").read_text(
            encoding="utf-8"
        ) == "def calc():\n    return 42\n"

    def test_stale_tag_rejected_with_guidance(self, agent_workspace: Path) -> None:
        _write_result("s.py", "a\n")
        tag = _header_of(_read_result("s.py")).split("#")[1].rstrip("]")
        _write_result("s.py", "changed externally\n")  # file đổi sau read
        out = _edit_result(f"[s.py#{tag}]\nPUT 1.=1:\n+new")
        assert out.startswith("Edit rejected:")
        assert (agent_workspace / "s.py").read_text(encoding="utf-8") == "changed externally\n"

    def test_unseen_lines_rejected_before_mutation(self, agent_workspace: Path) -> None:
        content = "".join(f"row{i}\n" for i in range(1, 11))
        _write_result("u.txt", content)
        out = _read_result("u.txt", offset=1, limit=3)  # chỉ thấy 1-3
        tag = _header_of(out).split("#")[1].rstrip("]")
        result = _edit_result(f"[u.txt#{tag}]\nPUT 7.=7:\n+hacked")
        assert result.startswith("Edit rejected:")
        assert (agent_workspace / "u.txt").read_text(encoding="utf-8") == content

    def test_cut_paste_register_across_files(self, agent_workspace: Path) -> None:
        _write_result("src.py", "keep\nMOVE ME\nkeep2\n")
        _write_result("dst.py", "header\n")
        tag_src = _header_of(_read_result("src.py")).split("#")[1].rstrip("]")
        tag_dst = _header_of(_read_result("dst.py")).split("#")[1].rstrip("]")
        out = _edit_result(
            f"[src.py#{tag_src}]\nCUT 2.=2 @fn\n"
            f"[dst.py#{tag_dst}]\nPUT >1 @fn"
        )
        assert "src.py" in out and "dst.py" in out
        assert (agent_workspace / "src.py").read_text(encoding="utf-8") == "keep\nkeep2\n"
        assert (agent_workspace / "dst.py").read_text(encoding="utf-8") == "header\nMOVE ME\n"

    def test_rem_deletes_file_and_invalidates(self, agent_workspace: Path) -> None:
        _write_result("gone.py", "data\n")
        tag = _header_of(_read_result("gone.py")).split("#")[1].rstrip("]")
        out = _edit_result(f"[gone.py#{tag}]\nREM")
        assert "Deleted" in out
        assert not (agent_workspace / "gone.py").exists()
        assert _read_result("gone.py").startswith("Error:")  # store đã invalidate

    def test_crlf_file_preserved_byte_exact(self, agent_workspace: Path) -> None:
        (agent_workspace / "win.py").write_bytes("def f():\r\n    return 1\r\n".encode())
        tag = _header_of(_read_result("win.py")).split("#")[1].rstrip("]")
        _edit_result(f"[win.py#{tag}]\nPUT 2.=2:\n+    return 2")
        assert (agent_workspace / "win.py").read_bytes() == "def f():\r\n    return 2\r\n".encode()
