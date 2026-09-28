# 🦕 Dino Coding Agent

AI Coding Agent xây dựng bằng Python, sử dụng framework [DeepAgents](https://github.com/langchain-ai/deepagents) và port Hashline Editing Engine từ [oh-my-pi](../sample-code/oh-my-pi/).

## Cài đặt

```bash
# Yêu cầu Python >= 3.12 và uv
uv sync
```

Tạo file `.env` từ mẫu:

```bash
cp .env.example .env
# Điền API key cho provider bạn muốn dùng
```

## Chạy CLI

```bash
uv run dino-coding
```

## Chạy Tests

```bash
uv run pytest
```

## Chạy Demo (không cần API key)

```bash
# Demo EditStore — 9 use cases quản lý snapshot, clipboard, no-op guard
uv run python scripts/demo_store.py

# Demo Engine — vòng đời edit đầy đủ: write → read → edit → stale → unseen → CUT/PASTE
uv run python scripts/demo_engine.py
```

## Kiến trúc

```
src/dino_coding/
├── main.py              # CLI entrypoint (Rich Console)
├── agent.py             # create_deep_agent() wrapper
├── config.py            # Multi-provider LLM config
├── prompt.py            # System prompt
└── tools/
    ├── base.py          # Phase 1 tools
    ├── fs.py            # Smart read/write with snapshot tags
    ├── editor.py        # Hashline edit tool
    ├── workspace.py     # Path policy (chống path traversal)
    └── hashline/        # Editing engine (port of pi-edit)
        ├── text.py      # BOM, normalize, line ending, xxhash
        ├── types.py     # Pure dataclasses
        ├── messages.py  # Model-facing error strings
        ├── store.py     # EditStore (snapshots, clipboard, no-op)
        ├── tokenizer.py # Lexer
        ├── input.py     # Patch splitter
        ├── parser.py    # Token → Edit executor
        ├── apply.py     # Clipboard resolve + materialize
        ├── patcher.py   # Stage orchestrator
        └── diffpreview.py
```

## Tiến độ

- [x] **Phase 1**: Hello Harness — CLI, LLM config, Append-Only context
- [x] **Phase 2**: VFS & Hashline Editing — Dual anchor protocol, seen-lines guard, no-op escalation
- [ ] **Phase 2.5**: Codebase Intelligence — ast-grep, block ops `N*`
