# Startup Readiness Checklist

## Start Commands

- Run harness from repo root: `python main.py`
- Run initialization only from repo root: `python main.py --init`
- Run tests from workspace: `pytest`
- Run lint from workspace: `ruff check .`
- Run full validation from workspace: `pytest && ruff check .`

## Current State

- Workspace exists.
- Test framework is configured.
- Ruff validation is expected.
- Progress is tracked in `progress.md`.
- Feature state is tracked in `feature_list.json`.
- Run history is tracked in `run_history.json`.
- Failures are tracked in `failure_log.json`.

## Project Structure

- `src/` - generated source code
- `tests/` - generated tests
- `AGENTS.md` - agent routing instructions
- `harness_map.md` - harness subsystem map
- `docs/` - focused topic docs

## Readiness Conditions

- [ ] The harness can start from repo root.
- [ ] Pytest can run from `workspace/`.
- [ ] Ruff can run from `workspace/`.
- [ ] A fresh agent can identify current progress.
- [ ] A fresh agent can identify the next task.
- [ ] A fresh agent can identify validation commands.

## Task Breakdown Readiness

- [ ] `task_breakdown.md` exists.
- [ ] It has one clear active task.
- [ ] Each task has acceptance criteria.
- [ ] Each task has validation requirements.
- [ ] There is a clear next step.
