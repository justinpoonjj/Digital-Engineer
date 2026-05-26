# AGENTS.md

## Project Overview
This is a Python harness prototype that uses an LLM to generate, validate, and repair code.

The harness controller owns workspace setup, validation, repair attempts, and state updates. Generated code should be returned as full file contents using paths relative to this workspace root.

## Quick Commands
- Run tests: `pytest`
- Run lint: `ruff check .`
- Run full validation: `pytest && ruff check .`

## Hard Constraints
- Never delete or weaken tests to make validation pass.
- Fix implementation before changing tests.
- Preserve edge-case tests such as `pytest.raises`.
- Do not modify unrelated files.
- Do not create or modify a nested `workspace/` directory.
- Do not modify `progress.md`, `feature_list.json`, or `task_breakdown.md`; the harness controller updates state files after validation.
- A task is not done until pytest and Ruff pass.

## Task Breakdown Rules

- Read `task_breakdown.md` during initialization.
- Use it to identify the current active task and next step.
- Do not mark subtasks complete unless the work is implemented and validated.
- Do not remove unfinished tasks.
- Do not rewrite the task breakdown to hide failures.
- The harness controller owns final updates to task status after validation.

## Path And Import Rules
- Use paths relative to this workspace root.
- Correct generated paths look like `src/calculator.py` and `tests/test_calculator.py`.
- Incorrect generated paths look like `workspace/src/calculator.py`.
- If `pyproject.toml` has `pythonpath = ["src"]`, import modules inside `src` directly.
- Example: `src/calculator.py` should be imported as `from calculator import add`.

## Topic Docs
- `harness_map.md` - read first to understand the harness structure.
- `docs/testing-standards.md` - read when writing or repairing tests.
- `docs/repair-rules-guide.md` - read when changing validation parsing or repair prompts.
- `docs/state-management.md` - read when updating `progress.md`, `feature_list.json`, `run_history.json`, or `failure_log.json`.
- `task_breakdown.md` - read during initialization to identify the active task, acceptance criteria, validation requirements, and next step.
