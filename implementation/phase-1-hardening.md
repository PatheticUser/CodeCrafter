# Phase 1 — Codebase Hardening

> **Effort:** ~3 days · **Dependencies:** None  
> **Goal:** Transform the current flat-file prototype into a production-grade Python package before layering API and frontend on top.

---

## 1.1 Configuration System Overhaul

### Why This Matters
The current `config.py` hardcodes every value — model URLs, token limits, directory paths. This means:
- Changing behavior between dev/staging/prod requires editing source code
- Secrets (future JWT keys, DB passwords) would live in version control
- No validation — a typo in a model name silently breaks everything

### What To Do

1. **Install `pydantic-settings`** — this is the standard for Python config management. It reads from `.env` files, environment variables, and provides type validation out of the box.

2. **Create a single `Settings` class** that replaces `config.py` entirely. Every current constant (`OLLAMA_BASE_URL`, `DEFAULT_MODEL`, `MAX_TOKENS`, etc.) becomes a typed field with a default value. Group fields logically: app metadata, Ollama config, agent behavior, paths, future DB/auth settings.

3. **Environment enum** — define `development`, `staging`, `production` environments. Behavior like debug mode, docs visibility, and log format should switch based on this single value.

4. **Path handling** — use `pathlib.Path` instead of `os.path.join`. Compute `workspace_dir` and `sessions_dir` relative to `base_dir` in a post-init hook so they're always consistent.

5. **Create `.env.example`** — committed to git, documents every available setting with sane defaults and comments. Create `.env` (gitignored) for local overrides.

6. **Add `.env` to `.gitignore` immediately** — this is non-negotiable. Secrets must never touch version control.

### Best Practices
- **Never import individual constants** — import the `settings` singleton and access `settings.max_tokens`. This ensures all config flows through one validated object.
- **Fail fast on invalid config** — Pydantic raises on startup if a required field is missing or has wrong type. This is far better than a runtime crash 30 minutes into a session.
- **Document units in field names** — `jwt_expire_minutes` not `jwt_expire`. `rate_limit_per_minute` not `rate_limit`.
- **Secrets get `SecretStr` type** — Pydantic's `SecretStr` prevents accidental logging of sensitive values. Use for JWT secrets, DB passwords, API keys.

### Acceptance
- [ ] `config.py` deleted, all imports point to new settings module
- [ ] `uv run python -c "from src.core.settings import settings; print(settings.app_name)"` works
- [ ] Changing `.env` values changes runtime behavior without touching code
- [ ] No hardcoded values remain in any source file

---

## 1.2 Project Restructure

### Why This Matters
Current layout has:
- No `src/` package boundary — imports are fragile and won't work in installed packages
- Empty directories (`services/`, `commands/`, `tools/`) that confuse contributors
- `functions/` naming is non-standard — `tools/` is the convention for agent tool functions
- UI, session management, and agent logic all live at root level with no clear boundaries

### Target Structure

Reorganize into a proper Python package under `src/` with clear module boundaries:

- **`src/core/`** — settings, agent loop, API client, workspace scanner. The brain.
- **`src/tools/`** — all 9 tool implementations + a registry module. Completely self-contained — each tool is a pure function that takes a workspace path and arguments, returns a string.
- **`src/sessions/`** — session persistence. Currently JSON files, will migrate to DB in Phase 2.
- **`src/cli/`** — terminal-specific code: display formatting, spinner, input loop, ANSI colors. Nothing here should be imported by the API layer.
- **`src/api/`** — empty for now, populated in Phase 2.
- **`tests/`** — at project root, mirrors `src/` structure.

### What To Do

1. **Create `src/` directory** with `__init__.py` containing version string.

2. **Move modules** — this is mechanical but must be done carefully:
   - `functions/*.py` → `src/tools/*.py`
   - `core/` → `src/core/`
   - `chat_session/` → `src/sessions/`
   - `ui/` → `src/cli/`
   - New `config.py` → `src/core/settings.py` (from step 1.1)

3. **Create `src/tools/registry.py`** — extract `get_available_tools()` and `execute_tool()` from `main.py` into this module. The registry should be a class that auto-discovers tools and provides a clean interface.

4. **Delete empty directories** — `services/`, `commands/`, old `tools/` (the one at root that's empty).

5. **Update all imports project-wide** — every `from config import X` becomes `from src.core.settings import settings`. Every `from functions.run_code import run_code` becomes `from src.tools.run_code import run_code`. Use find-and-replace but verify each one.

6. **Update `pyproject.toml`** — add `[project.scripts]` entry point so CLI runs via `codecrafter` command instead of `uv run main.py`.

### Best Practices
- **Never have cross-layer imports** — `src/cli/` may import from `src/core/` and `src/tools/`, but `src/core/` must never import from `src/cli/`. This is critical: the API layer will also import from `src/core/`, and it must not pull in terminal/ANSI dependencies.
- **Each `__init__.py` should have `__all__`** — explicit public API for each module.
- **Keep a `main.py` shim at project root** — a thin wrapper that imports and calls `src.cli.main:main()` for backward compatibility during transition. Delete it once Phase 2 is stable.

### Acceptance
- [ ] `uv run python -m src.cli.main` launches the CLI identically to current `uv run main.py`
- [ ] No import errors from any module
- [ ] Empty directories removed
- [ ] `pyproject.toml` has a `[project.scripts]` entry

---

## 1.3 Agent Loop Extraction

### Why This Matters
`main.py` is 564 lines that mix three concerns:
1. CLI input/output (terminal formatting, user prompts, banner display)
2. Agent logic (system prompt building, tool execution loop, error detection, auto-fix)
3. Session management (save/load/clear commands)

This makes it impossible to reuse the agent logic from an API endpoint. The API would need to duplicate the entire agent loop.

### What To Do

1. **Create `src/core/agent.py`** — an `AgentLoop` class that encapsulates all agent behavior:
   - Takes a list of messages as input
   - Builds the system prompt with workspace context
   - Runs the multi-step tool execution loop
   - Returns structured results (text, tool calls, token usage)
   - Handles error detection, auto-fix injection, and model fallback
   - Knows NOTHING about terminals, ANSI codes, or HTTP

2. **Define clear data structures** — create dataclasses for agent responses. Each step in the agent loop produces an `AgentResponse` with optional fields: `text`, `tool_calls`, `tool_results`, `is_final`, `token_usage`. This replaces the current approach of printing directly.

3. **Extract helper functions from `main.py`**:
   - `build_system_prompt()` → method on `AgentLoop`
   - `has_execution_error()` → stays in `src/core/agent.py` as private helper
   - `should_fallback()` → stays in `src/core/agent.py` as private helper
   - `execute_tool()` → moves to `src/tools/registry.py`

4. **Slim down CLI main** — after extraction, `src/cli/main.py` should only:
   - Parse CLI arguments
   - Create an `AgentLoop` instance
   - Run an input loop (read user text → call `agent.run_turn()` → display results)
   - Handle session commands (`help`, `sessions`, `exit`)

### Design Principles
- **The agent is a pure function** — `run_turn(messages, workspace_dir) → list[AgentResponse]`. No side effects except tool execution (which is scoped to the workspace).
- **Streaming support from day one** — design `run_turn` to optionally yield responses as a generator. This makes WebSocket streaming (Phase 2) trivial: each `yield` becomes a WebSocket message.
- **Model fallback is internal** — the caller doesn't need to know about fallback. The agent tries models, falls back, and reports which model actually responded.

### Best Practices
- **Don't pass the OpenAI client around** — the `AgentLoop` owns its client. External code just calls `run_turn()`.
- **Limit the agent's API surface** — ideally just: `__init__(model)`, `run_turn(messages, workspace)`, and maybe `run_turn_streaming(messages, workspace)`.
- **Keep the `<think>` block stripping** — the regex removal of `<think>...</think>` blocks from reasoning models is important. It stays in the agent, not in display code.

### Acceptance
- [ ] `AgentLoop` class exists with `run_turn()` method
- [ ] CLI uses `AgentLoop` — no agent logic remains in CLI main
- [ ] Can instantiate `AgentLoop` in a Python script without any terminal side effects
- [ ] All existing agent behaviors preserved (auto-fix, fallback, code-block detection, context trimming)

---

## 1.4 Testing Foundation

### Why This Matters
Zero tests means zero confidence. Every future change (API, Docker, refactor) risks silently breaking existing functionality. Tools that execute code and modify files are especially dangerous to change without test coverage.

### What To Do

1. **Install test dependencies** — `pytest`, `pytest-asyncio` (needed for Phase 2 async tests), `pytest-cov` for coverage reporting.

2. **Create `tests/` directory** with:
   - `conftest.py` — shared fixtures: temporary workspace directories, sample files, mock settings
   - `test_tools.py` — tests for all 9 tool functions
   - `test_agent.py` — tests for agent loop (will need a mock LLM client)
   - `test_sessions.py` — tests for session create/save/load/delete/corrupt-recovery

3. **Tool tests are the priority** — each tool is a pure function with clear inputs and outputs. Test:
   - **Happy path** — tool works correctly with valid input
   - **Path traversal** — `../../etc/passwd` is rejected
   - **Missing files** — graceful error, not an exception
   - **Edge cases** — empty files, very large output, binary files, Unicode filenames
   - **Blocked commands** — `run_command` rejects `rm -rf /`, `shutdown`, fork bombs

4. **Session tests** — test the full lifecycle:
   - Create → save → load → verify messages match
   - Corrupt JSON file → recovery creates backup + starts fresh
   - Max messages trimming works correctly
   - Session listing returns correct metadata

5. **Configure pytest in `pyproject.toml`** — set test paths, async mode, coverage thresholds.

### Best Practices
- **Use `tmp_path` fixture** — pytest provides temporary directories that auto-cleanup. Never use the real workspace for tests.
- **Don't mock too much** — tool functions are pure, test them with real file operations on temp dirs. Only mock the LLM client (OpenAI SDK).
- **Coverage target: 80%+ on `src/tools/`** — these are the most critical and most testable modules.
- **Name tests descriptively** — `test_run_code_rejects_path_traversal` not `test_run_code_3`.
- **Each test is independent** — no shared state between tests, no ordering dependencies.

### Acceptance
- [ ] `uv run pytest` runs and all tests pass
- [ ] Coverage report shows 80%+ on `src/tools/`
- [ ] Path traversal tests exist for every file-accessing tool
- [ ] Command blocklist tests verify all dangerous patterns

---

## 1.5 Linting & Formatting

### What To Do

1. **Install `ruff`** — single tool for both linting and formatting. Replaces flake8 + isort + black with one fast tool.

2. **Configure in `pyproject.toml`**:
   - Line length: 100 (not 79 — modern screens are wide)
   - Target: Python 3.11
   - Rules: enable `E` (pycodestyle), `F` (pyflakes), `I` (isort), `N` (naming), `W` (warnings), `UP` (pyupgrade for modern syntax)

3. **Run `ruff check --fix`** — auto-fix what it can.

4. **Run `ruff format`** — apply consistent formatting across entire codebase.

5. **Add type hints to all function signatures** — not full mypy strictness yet, but every function should declare parameter types and return types. This is documentation that the compiler checks.

### Best Practices
- **Run ruff in CI** (Phase 5) — linting failures block merges.
- **Don't fight the formatter** — pick a style and stick with it. Developer preferences don't matter; consistency matters.
- **Use `# noqa` sparingly** — if you're suppressing a lint rule, add a comment explaining why.

### Acceptance
- [ ] `uv run ruff check src/ tests/` returns 0 errors
- [ ] `uv run ruff format --check src/ tests/` returns 0 changes needed
- [ ] All public functions have type hints
- [ ] No `__pycache__/` directories in the repo

---

## 1.6 Cleanup

### What To Do

1. **Delete empty directories** — `services/`, `commands/`, root-level `tools/` (all contain only `__pycache__/`)
2. **Delete all `__pycache__/`** — `find . -type d -name __pycache__ -exec rm -rf {} +`
3. **Add `py.typed` marker** — signals to type checkers that this package ships type information
4. **Update README.md** — reflect new directory structure, new CLI command, updated architecture diagram
5. **Update `.gitignore`** — add `.env`, `.ruff_cache/`, `.pytest_cache/`, `*.egg-info/`, `htmlcov/`

### Acceptance
- [ ] No empty directories in repo
- [ ] No `__pycache__/` directories
- [ ] `.gitignore` covers all generated artifacts
- [ ] README reflects current project structure

---

## Phase 1 Final Checklist

Before moving to Phase 2, verify:

- [ ] CLI works identically to pre-refactor: `uv run python -m src.cli.main`
- [ ] All tests pass: `uv run pytest`
- [ ] Linting clean: `uv run ruff check src/`
- [ ] Config loads from `.env`
- [ ] `AgentLoop` is transport-agnostic (no CLI imports)
- [ ] `ToolRegistry` provides clean tool access
- [ ] No hardcoded values, no empty dirs, no `__pycache__/`
- [ ] Single commit with message: `refactor: restructure to src/ package with settings, agent extraction, and test foundation`
