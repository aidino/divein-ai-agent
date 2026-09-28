"""Test Phase 2.5 — ast_grep / ast_edit / block resolver.

Chạy: uv run pytest tests/test_ast.py -q
"""

from __future__ import annotations

import os

import pytest

import dino_coding.tools.workspace as ws_mod
from dino_coding.tools.ast_tools import ast_edit, ast_grep
from dino_coding.tools.astfind import (
    collect_files,
    find_matches,
    pattern_is_valid,
    pattern_variables,
)
from dino_coding.tools.astlang import is_supported_file, resolve_language
from dino_coding.tools.astrewrite import (
    RewriteConflict,
    apply_edits,
    expand_template,
    rewrite_target,
    rewrite_text,
)
from dino_coding.tools.hashline.block import (
    BlockUnresolved,
    block_range_at,
    find_enclosing_block,
    find_next_block,
    resolve_block_edits,
)
from dino_coding.tools.hashline.types import Anchor, EditBlock


# ===========================================================================
# 0. Fixture — workspace tạm cô lập (thừa hưởng khuôn Phase 2)
# ===========================================================================

SAMPLE = (
    "import os\n"
    "\n"
    "\n"
    "def slow(a, b):\n"
    "    total = a + b\n"
    "    return total\n"
    "\n"
    "class Calc:\n"
    "    def run(self, x):\n"
    "        print(x)\n"
    "        return slow(x, 1)\n"
    "\n"
    "print('done')\n"
)


@pytest.fixture()
def agent_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_WORKSPACE", str(tmp_path))
    ws_mod._WORKSPACE = None
    ws_mod._STORE = None
    yield tmp_path
    ws_mod._WORKSPACE = None
    ws_mod._STORE = None


def write_file(root, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(content)


# ===========================================================================
# 1. astlang — suy ngôn ngữ
# ===========================================================================

def test_resolve_language_alias_wins_over_extension():
    assert resolve_language("cpp", "header.h") == "cpp"     # override thắng
    assert resolve_language(None, "header.h") == "c"        # .h mặc định C
    assert resolve_language("", "app.py") == "python"       # chuỗi rỗng = bỏ qua
    assert resolve_language(None, "data.bin") is None


def test_is_supported_file_explicit_lang_accepts_everything():
    assert is_supported_file("notes.txt", "python") is True
    assert is_supported_file("notes.txt", None) is False
    assert is_supported_file("app.py", None) is True


# ===========================================================================
# 2. astfind — engine tìm kiếm
# ===========================================================================

def test_pattern_variables_ordered_unique():
    assert pattern_variables("f($A, $B, $A)") == ["A", "B"]
    assert pattern_variables("console.log($$$)") == []
    assert pattern_variables("$A == $A") == ["A"]


def test_pattern_is_valid_detects_garbage():
    assert pattern_is_valid("print($$$A)", "python") is True
    assert pattern_is_valid("f($A, $B)", "python") is True
    assert pattern_is_valid("def def def(", "python") is False
    assert pattern_is_valid("class $_ {", "python") is False


def test_find_matches_call_shape_ignores_comment_lines(agent_workspace):
    code = SAMPLE + "# print('not a call')\n"
    write_file(agent_workspace, "app.py", code)
    result = find_matches("print($$$ARGS)", str(agent_workspace))
    assert result.total_matches == 2          # comment không phải node call
    meta = result.matches[1].meta             # print('done') — ARGS='done'
    assert meta == {"ARGS": "'done'"}
    first = result.matches[0]                 # print(x) — dòng 10, cột 9
    assert (first.start_line, first.start_column) == (10, 9)
    # text node bắt đầu tại cột node — không chứa khoảng thụt lề phía trước
    assert first.text == "print(x)"


def test_find_matches_multiline_match_spans_lines(agent_workspace):
    write_file(agent_workspace, "app.py", SAMPLE)
    result = find_matches(
        "def slow($A, $B):\n    $$$BODY\n    return $$$RET", str(agent_workspace)
    )
    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.start_line == 4 and match.end_line == 6


def test_find_matches_parse_error_file_still_searched(agent_workspace):
    write_file(agent_workspace, "broken.py", "def f(:\n    print('a'\n")
    write_file(agent_workspace, "ok.py", "print('b')\n")
    result = find_matches("print($$$)", str(agent_workspace))
    # chuỗi hỏng trong ERROR region không sinh node call — chỉ ok.py match;
    # nhưng broken.py vẫn ĐƯỢC QUÉT (files_searched) và được báo lỗi parse
    assert result.total_matches == 1
    assert result.files_with_matches == 1
    assert result.files_searched == 2
    assert any("parse error" in e for e in result.parse_errors)


def test_find_matches_skip_and_limit(agent_workspace):
    write_file(agent_workspace, "many.py", "".join(f"print({i})\n" for i in range(10)))
    result = find_matches("print($N)", str(agent_workspace), skip=2, limit=3)
    assert [m.start_line for m in result.matches] == [3, 4, 5]
    assert result.total_matches == 10
    assert result.limit_reached is True
    tail = find_matches("print($N)", str(agent_workspace), skip=8, limit=3)
    assert len(tail.matches) == 2
    assert tail.limit_reached is False


def test_collect_files_skips_hidden_and_caches(agent_workspace):
    write_file(agent_workspace, "a.py", "x = 1\n")
    write_file(agent_workspace, "sub/b.py", "x = 2\n")
    write_file(agent_workspace, ".git/c.py", "x = 3\n")
    write_file(agent_workspace, "__pycache__/d.py", "x = 4\n")
    assert collect_files(str(agent_workspace)) == ["a.py", "sub/b.py"]
    assert collect_files(str(agent_workspace / "a.py")) == ["a.py"]

# ===========================================================================
# 3. astrewrite — template + apply_edits + rewrite toàn phần
# ===========================================================================

def test_expand_template_multi_var_is_source_slice():
    from ast_grep_py import SgRoot

    source = "f(a, b, c)\n"
    node = SgRoot(source, "python").root().find_all(pattern="f($$$A)")[0]
    # slice nguồn giữ nguyên "a, b, c" — KHÔNG dựng từ danh sách node
    assert expand_template("g($$$A)", node, source) == "g(a, b, c)"
    single = SgRoot("print('x')\n", "python").root().find_all(pattern="print($X)")[0]
    assert expand_template("log($X)", single, "print('x')\n") == "log('x')"
    # biến không từng được bắt → bỏ trống (đúng replacer.rs: omit bytes)
    assert expand_template("h($Z)", single, "print('x')\n") == "h()"


def test_apply_edits_sort_dedupe_overlap():
    source = "abcdef"
    # (pos, deleted, inserted) — edit trùng byte-identical gộp làm một
    assert apply_edits(source, [(0, 1, "X"), (0, 1, "X"), (5, 1, "Z")]) == "XbcdeZ"
    with pytest.raises(RewriteConflict, match="Overlapping"):
        apply_edits(source, [(1, 3, "X"), (2, 2, "Y")])
    # áp từ cuối lên: offset phía trước không xê dịch
    assert apply_edits("one two", [(0, 3, "ONE"), (4, 3, "TWO")]) == "ONE TWO"


def test_rewrite_text_multi_rule_single_parse():
    source = "old(1)\nold(2)\nkeep(3)\n"
    changes, out = rewrite_text(source, "python", [("old($N)", "new($N)")])
    assert out == "new(1)\nnew(2)\nkeep(3)\n"
    assert len(changes) == 2 and changes[0].start_line == 1


def test_rewrite_text_identical_edits_from_two_rules_dedupe():
    source = "dup(1)\n"
    changes, out = rewrite_text(
        source, "python",
        [("dup($N)", "twin($N)"), ("dup($A)", "twin($A)")],  # cùng kết quả
    )
    assert out == "twin(1)\n"
    assert len(changes) == 1  # một edit deterministic, không phải hai


def test_rewrite_text_conflicting_rules_abort():
    source = "f(a, b)\n"
    with pytest.raises(RewriteConflict):
        rewrite_text(source, "python",
                     [("f($A, $B)", "g($A)"), ("f($A, $B)", "h($B)")])


def test_rewrite_target_stages_writes_until_clean(agent_workspace):
    write_file(agent_workspace, "good.py", "old(1)\n")
    write_file(agent_workspace, "bad.py", "f(a, b)\n")
    captured: list[str] = []

    def writer(path, text):
        captured.append(os.path.basename(path))

    # rule xung đột trên bad.py → RewriteConflict lan lên, KHÔNG ghi file nào
    with pytest.raises(RewriteConflict):
        rewrite_target(
            [("old($N)", "new($N)"), ("f($A, $B)", "g($A)"),
             ("f($A, $B)", "h($B)")],
            str(agent_workspace), apply=True, writer=writer,
        )
    assert captured == []  # atomic: flush chỉ diễn ra khi cả pass sạch lỗi


def test_rewrite_target_dry_run_and_apply(agent_workspace):
    write_file(agent_workspace, "x.py", "old(1)\nold(2)\n")
    preview = rewrite_target([("old($N)", "new($N)")], str(agent_workspace))
    assert preview.applied is False
    assert (agent_workspace / "x.py").read_text() == "old(1)\nold(2)\n"
    applied = rewrite_target([("old($N)", "new($N)")], str(agent_workspace),
                             apply=True)
    assert applied.total_replacements == 2
    assert (agent_workspace / "x.py").read_text() == "new(1)\nnew(2)\n"


def test_rewrite_target_delete_with_empty_out(agent_workspace):
    write_file(agent_workspace, "d.py", "print('a')\nkeep()\nprint('b')\n")
    result = rewrite_target([("print($$$)", "")], str(agent_workspace), apply=True)
    assert result.total_replacements == 2
    assert (agent_workspace / "d.py").read_text() == "\nkeep()\n\n"


# ===========================================================================
# 4. block resolver — trả nợ Phase 2
# ===========================================================================

def test_block_range_at_function_and_class():
    assert block_range_at(SAMPLE, "app.py", 4) == (4, 6)    # def slow
    assert block_range_at(SAMPLE, "app.py", 8) == (8, 11)   # class Calc
    assert block_range_at(SAMPLE, "app.py", 9) == (9, 11)   # def run


def test_block_range_at_rejects_bad_anchors():
    assert block_range_at(SAMPLE, "app.py", 5) == (5, 5)  # statement 1 dòng;
    # resolve_block_edits chặn case này qua single-line error — không phải ở đây
    assert block_range_at(SAMPLE, "app.py", 7) is None   # dòng trống
    assert block_range_at(SAMPLE, "app.py", 12) is None  # dòng trống cuối class — span dừng ở 11
    assert block_range_at(SAMPLE, "data.bin", 4) is None # ngôn ngữ không hỗ trợ
    # chuỗi hở mới sinh ERROR node — `def broken(:` + pass bị recovery âm thầm
    assert block_range_at("def broken(:\n    print('a'\n", "b.py", 1) is None


def test_block_suggestions():
    assert find_next_block(7, SAMPLE, "app.py") == (8, 11)
    assert find_enclosing_block(10, SAMPLE, "app.py") == (9, 11)


def test_resolve_block_replace_lowering():
    edits = [EditBlock(Anchor(4), ["def slow(a, b):", "    return a * b"],
                       None, None, 1, 0)]
    lowered, warnings = resolve_block_edits(edits, SAMPLE, "app.py")
    kinds = [type(e).__name__ for e in lowered]
    # thay block = insert trước (replacement) + delete từng dòng span
    assert kinds == ["EditInsert", "EditInsert", "EditDelete",
                     "EditDelete", "EditDelete"]
    assert warnings == []
    assert lowered[0].cursor.kind == "before"
    assert lowered[0].cursor.anchor == Anchor(4)
    assert lowered[0].replacement is True


def test_resolve_block_cut_lowers_to_cut_plus_deletes():
    edits = [EditBlock(Anchor(4), [], "cut", "fn", 1, 0)]
    lowered, _ = resolve_block_edits(edits, SAMPLE, "app.py")
    kinds = [type(e).__name__ for e in lowered]
    assert kinds[0] == "EditCut"
    assert kinds[1:] == ["EditDelete"] * 3


def test_resolve_block_unresolved_raises_with_next_hint():
    edits = [EditBlock(Anchor(7), [], None, None, 1, 0)]   # dòng trống
    with pytest.raises(BlockUnresolved, match="next multi-line block"):
        resolve_block_edits(edits, SAMPLE, "app.py")


def test_resolve_block_single_line_statement_raises():
    code = "print('a')\nprint('b')\n"
    edits = [EditBlock(Anchor(1), ["x"], None, None, 1, 0)]
    with pytest.raises(BlockUnresolved, match="single-line block"):
        resolve_block_edits(edits, code, "app.py")


# ===========================================================================
# 5. Tool E2E — không cần LLM
# ===========================================================================

def test_ast_grep_mints_tag_and_seen_lines(agent_workspace):
    write_file(agent_workspace, "app.py", SAMPLE)
    out = ast_grep.invoke({"pat": "print($$$ARGS)", "path": "app.py"})
    assert out.splitlines()[0].startswith("[app.py#")
    assert "*10:print(x)" in out          # text node = từ cột node, không thụt lề
    assert "  meta: ARGS='done'" in out



def test_ast_grep_directory_target_deep_mints_correct_path(agent_workspace):
    """Regression: engine trả path tương đối SCOPE; tool phải đổi về tương đối
    workspace trước khi mint tag — directory-target sâu hơn 1 cấp từng mở
    sai file (hiện 'file unreadable' thay vì match row)."""
    write_file(agent_workspace, "pkg/deep/app.py", SAMPLE)
    out = ast_grep.invoke({"pat": "print($$$)", "path": "pkg/deep"})
    assert out.splitlines()[0].startswith("[pkg/deep/app.py#")
    assert "unreadable" not in out
    assert "10:print(x)" in out


def test_ast_edit_directory_target_deep_applies(agent_workspace):
    write_file(agent_workspace, "pkg/deep/app.py", SAMPLE)
    applied = ast_edit.invoke({
        "ops": [{"pat": "print($$$ARGS)", "out": "log($$$ARGS)"}],
        "paths": ["pkg/deep"], "apply": True,
    })
    assert "[pkg/deep/app.py#" in applied
    assert "log(x)" in (agent_workspace / "pkg/deep/app.py").read_text()


def test_ast_grep_search_hit_is_edit_anchor(agent_workspace):
    """Search hit đủ điều kiện làm anchor — không cần read lại file."""
    write_file(agent_workspace, "app.py", SAMPLE)
    out = ast_grep.invoke({"pat": "print($$$)", "path": "app.py"})
    header = out.splitlines()[0]                       # [app.py#TAG]
    from dino_coding.tools.editor import edit

    result = edit.invoke({"input": f"{header}\nPUT 10.=10:\n+        log(x)"})
    # kết quả thành công = header TAG mới + diff preview ±N| (không phải "applied")
    assert result.startswith("[app.py#")
    assert "+10|" in result
    assert "log(x)" in (agent_workspace / "app.py").read_text()


def test_ast_grep_no_matches_with_parse_hint(agent_workspace):
    write_file(agent_workspace, "broken.py", "def f(:\n    print('a'\n")
    out = ast_grep.invoke({"pat": "print($$$)", "path": "broken.py"})
    assert "No matches found" in out
    assert "narrow `path`" in out


def test_ast_grep_rejects_escaping_path(agent_workspace):
    out = ast_grep.invoke({"pat": "print($$$)", "path": "../../etc"})
    assert out.startswith("Error:")


def test_ast_edit_preview_then_apply_cycle(agent_workspace):
    write_file(agent_workspace, "app.py", SAMPLE)
    preview = ast_edit.invoke({
        "ops": [{"pat": "print($$$ARGS)", "out": "log($$$ARGS)"}],
        "paths": ["app.py"],
    })
    assert preview.startswith("Staged as a proposal")
    assert "-10:print(x)" in preview
    assert "+10:log(x)" in preview
    assert (agent_workspace / "app.py").read_text() == SAMPLE   # chưa ghi

    applied = ast_edit.invoke({
        "ops": [{"pat": "print($$$ARGS)", "out": "log($$$ARGS)"}],
        "paths": ["app.py"], "apply": True,
    })
    assert applied.startswith("Applied 2 replacement(s) in 1 file(s).")
    assert "[app.py#" in applied          # fresh tag sau apply
    assert "log(x)" in (agent_workspace / "app.py").read_text()


def test_ast_edit_stale_preview_detected(agent_workspace):
    write_file(agent_workspace, "app.py", SAMPLE)
    ast_edit.invoke({"ops": [{"pat": "print($$$)", "out": "log($$$)"}],
                     "paths": ["app.py"]})                      # preview
    write_file(agent_workspace, "app.py", "print('gone')\n")    # đổi ngoài
    out = ast_edit.invoke({"ops": [{"pat": "print($$$)", "out": "log($$$)"}],
                           "paths": ["app.py"], "apply": True})
    assert out.startswith("Error: Preview is stale")
    # từ chối TRƯỚC khi ghi — file giữ nguyên nội dung mới, không áp diff nào
    assert (agent_workspace / "app.py").read_text() == "print('gone')\n"


def test_ast_edit_stale_detected_when_only_content_changed(agent_workspace):
    """Stale theo CONTENT TAG: comment appends ngoài vùng match không đổi
    số replacement nhưng vẫn phải bị chặn — closure omp chặn theo file đổi,
    không theo diff đếm được."""
    write_file(agent_workspace, "app.py", SAMPLE)
    ast_edit.invoke({"ops": [{"pat": "print($$$)", "out": "log($$$)"}],
                     "paths": ["app.py"]})                      # preview
    with open(agent_workspace / "app.py", "a", encoding="utf-8", newline="") as fh:
        fh.write("# review hotfix\n")   # cùng số match, nội dung khác
    out = ast_edit.invoke({"ops": [{"pat": "print($$$)", "out": "log($$$)"}],
                           "paths": ["app.py"], "apply": True})
    assert out.startswith("Error: Preview is stale")
    assert "contents changed" in out
    assert "log(" not in (agent_workspace / "app.py").read_text()


def test_ast_edit_duplicate_pattern_rejected(agent_workspace):
    write_file(agent_workspace, "app.py", SAMPLE)
    out = ast_edit.invoke({
        "ops": [{"pat": "print($$$)", "out": "a"},
                {"pat": "print($$$)", "out": "b"}],
        "paths": ["app.py"],
    })
    assert out.startswith("Error: Duplicate rewrite pattern")


def test_edit_tool_block_op_now_resolves(agent_workspace):
    """Regression Phase 2: `PUT N*:` từng bị chặn BLOCK_RESOLVER_UNAVAILABLE —
    giờ phải thay cả thân hàm slow() bằng 2 dòng mới."""
    write_file(agent_workspace, "app.py", SAMPLE)
    from dino_coding.tools.editor import edit

    # Pattern phải là node đơn: def thiếu thân không parse. Pattern đa dòng
    # $$$BODY vừa match vừa RENDER dòng 4-6 → seen-lines đủ cho `PUT 4*:`.
    out = ast_grep.invoke({
        "pat": "def slow($A, $B):\n    $$$BODY", "path": "app.py",
    })
    assert out.startswith("[app.py#")
    assert "*4:def slow(a, b):" in out
    header = out.splitlines()[0]
    result = edit.invoke({"input": (
        f"{header}\nPUT 4*:\n+def slow(a, b):\n+    return a * b"
    )})
    assert result.startswith("[app.py#")   # block 4-6 bị thay, tag mới trả về
    text = (agent_workspace / "app.py").read_text()
    assert "return a * b" in text
    assert "total = a + b" not in text
