# Harness Map

## Purpose
This project is a harness engineering prototype for generating, validating, and repairing Python code using LLMs.

The harness has two layers:
- `../harness/` contains the controller code that builds prompts, loads context, runs tools, validates output, and applies basic repairs.
- `./` is the generated workspace where project files, tests, state, and agent-facing knowledge live.

## Harness Subsystems

### Instruction Subsystem
- `AGENTS.md`
- `harness_map.md`
- `docs/testing-standards.md`
- `docs/repair-rules-guide.md`
- `docs/state-management.md`
- `../harness/prompts.py`
- `../harness/context_loader.py`

### Tool Subsystem
- `../harness/execution_manager.py`
- file reading and writing logic in the harness controller
- command execution logic for pytest and Ruff

### Environment Subsystem
- `pyproject.toml`
- pytest configuration
- Ruff configuration
- `src/`
- `tests/`

### State Subsystem
- `progress.md`
- `feature_list.json`
- `run_history.json`
- `failure_log.json`
- `../harness/state_manager.py`

### Feedback Subsystem
- `../harness/validator.py`
- `../harness/repair_rules.py`
- pytest output
- Ruff output
- repair prompts from `../harness/prompts.py`

## Flow
1. The user requests a change.
2. The context loader reads repo-visible instructions and state.
3. The prompt builder asks the LLM for a plan and then file changes.
4. The execution manager writes allowed files into the workspace.
5. The validator runs pytest and Ruff.
6. Repair rules and repair prompts turn failures into targeted follow-up changes.
7. The state manager records completed work and validation results.

## Definition Of Done
A task is only done when:
- generated code works
- tests pass
- Ruff passes
- no tests were deleted or weakened
- `progress.md` is updated by the harness controller
- `feature_list.json` is updated if feature status changed
- validation results are recorded in `run_history.json` or `failure_log.json` when applicable
