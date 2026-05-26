# Harness Map

## Purpose

This project is a harness engineering prototype for running agent-assisted Python development with explicit initialization, implementation, validation, repair, and handoff phases.

The harness has two layers:

- `../harness/` contains controller code for loading context, building prompts, applying allowed file changes, validating output, repairing common failures, and updating durable state.
- `./` is the generated workspace where project code, tests, state files, and agent-facing documentation live.

## Current Repository Layout

### Controller Entry Point

- `../main.py` - CLI entry point and top-level harness lifecycle coordinator.

### Harness Controller Modules

- `../harness/context_loader.py` - loads durable workspace context for the LLM.
- `../harness/execution_manager.py` - parses LLM file blocks, rejects unsafe paths, protects controller-owned state files, and supports `NO_FILE_CHANGES`.
- `../harness/llm_service.py` - wraps the OpenAI client call used during implementation and repair.
- `../harness/preflight.py` - checks workspace structure, import conventions, and pytest import hygiene before validation.
- `../harness/prompts.py` - builds plan, code, and repair prompts.
- `../harness/repair_rules.py` - applies basic deterministic repairs for common import, pytest, and Ruff issues.
- `../harness/state_manager.py` - appends progress, run history, failure logs, and controller-owned task breakdown updates.
- `../harness/validator.py` - runs workspace validation commands.

### Workspace Source And Tests

- `src/` - generated project source code.
- `tests/` - generated product tests.
- `pyproject.toml` - pytest and Ruff configuration.

### Harness Tests

- `../tests/` - harness/controller tests owned by harness developers.

### Workspace Instructions And State

- `AGENTS.md` - agent routing rules and hard constraints.
- `harness_map.md` - this subsystem map.
- `DECISIONS.md` - durable project decisions.
- `feature_list.json` - feature state.
- `progress.md` - append-only progress history.
- `run_history.json` - structured run history.
- `failure_log.json` - structured failure history.
- `task_breakdown.md` - live planning artifact owned by the harness controller.

### Workspace Docs

- `docs/repair-rules-guide.md` - repair behavior guide.
- `docs/debugging-policy.md` - repair scope and failure routing policy.
- `docs/session-handoff.md` - session handoff expectations.
- `docs/startup-readiness.md` - startup commands and readiness checklist.
- `docs/state-management.md` - state file ownership and update rules.
- `docs/testing-standards.md` - testing conventions.

## Harness Lifecycle

### 1. Initialization Phase

Owned by `../main.py`.

The harness:

- loads context with `load_context()`
- verifies required startup files exist
- checks whether `pytest` is available from `workspace/`
- checks whether Ruff is available from `workspace/`
- verifies `task_breakdown.md` has the required planning sections
- runs structural preflight checks

Initialization can run two ways:

- `python main.py --init`
- natural-language requests such as "Run startup readiness only" or "Do not implement"

Natural-language initialization-only requests are detected by `is_initialization_only_request()` and return before planning, code generation, or file application.

### 2. Implementation Phase

Owned by `run_harness()` in `../main.py`.

This phase only starts when startup readiness passes and the request is not initialization-only.

The harness:

- resolves the implementation task from `task_breakdown.md` when the user asks for the first task
- builds the allowed repair scope for the resolved task
- builds a task contract with required files, allowed files, and validation profile
- loads implementation-specific context that avoids full readiness history
- asks the LLM for a plan
- rejects no-change readiness plans for implementation requests
- asks the LLM for file changes
- retries generation once when output does not satisfy the file-change contract
- rejects empty or incomplete generation before validation
- applies file changes through `apply_file_changes()`
- reruns preflight after changes

The code prompt supports `NO_FILE_CHANGES` for requests that require no edits. `apply_file_changes()` treats that as a valid no-op and returns an empty changed-file list.

### 3. Validation And Repair Phase

Owned by `../harness/validator.py`, `../harness/repair_rules.py`, and repair prompts from `../harness/prompts.py`.

The harness:

- runs `pytest`
- runs `ruff check .`
- applies deterministic repair rules when possible
- asks the LLM for targeted fixes when validation still fails
- stops early when the same validation failure repeats
- refuses LLM repair when validation fails outside the allowed task scope

### 4. Handoff Phase

Owned by `../harness/state_manager.py` through `clock_out_success()` and `clock_out_failure()` in `../main.py`.

On success, the harness updates:

- `progress.md`
- `run_history.json`
- `task_breakdown.md`

On failure, the harness updates:

- `failure_log.json`
- `run_history.json`
- `task_breakdown.md`

## Subsystems

### Instruction Subsystem

- `AGENTS.md`
- `harness_map.md`
- `task_breakdown.md`
- `docs/startup-readiness.md`
- `docs/debugging-policy.md`
- `docs/testing-standards.md`
- `docs/repair-rules-guide.md`
- `docs/state-management.md`
- `docs/session-handoff.md`
- `../harness/context_loader.py`
- `../harness/prompts.py`

### Intent And Startup Subsystem

- `../main.py`
- `is_initialization_only_request()`
- `is_implementation_request()`
- `resolve_user_task()`
- `plan_requires_no_file_changes()`
- `build_allowed_scope()`
- `build_task_contract()`
- `generation_satisfies_contract()`
- `required_files_exist()`
- `is_failure_in_allowed_scope()`
- `failure_is_within_scope()`
- `extract_failure_files()`
- `classify_validation_failure()`
- `initialize_session()`
- `build_startup_readiness_report()`
- `print_startup_readiness_report()`
- `check_required_files()`
- `check_required_directories()`
- `check_task_breakdown_visibility()`
- `run_preflight_checks()`

### Tool And Execution Subsystem

- `../harness/execution_manager.py`
- `apply_file_changes()`
- `extract_file_changes()`
- `normalize_relative_path()`
- `NO_FILE_CHANGES` no-op support
- protected file enforcement

Protected files rejected from LLM file changes:

- `AGENTS.md`
- `feature_list.json`
- `progress.md`
- `task_breakdown.md`

### Environment Subsystem

- `pyproject.toml`
- `src/`
- `tests/`
- pytest configuration
- Ruff configuration

### State Subsystem

- `progress.md`
- `feature_list.json`
- `run_history.json`
- `failure_log.json`
- `task_breakdown.md`
- `../harness/state_manager.py`

### Feedback Subsystem

- `../harness/validator.py`
- `../harness/repair_rules.py`
- validation profiles: `startup`, `implementation`, `harness`, and `full`
- pytest output
- Ruff output
- repair prompts from `../harness/prompts.py`

### Regression Test Subsystem

- `../tests/test_continuity_artifacts.py` - verifies core continuity files exist.
- `../tests/test_initialization_intent.py` - verifies initialization-only intent, task resolution, plan gates, scope guards, and protected harness tests.

## Current Control Flow

1. User starts the harness with `python main.py` or `python main.py --init`.
2. The harness loads durable context from workspace docs and state files.
3. The harness builds and prints a startup readiness report with required file, directory, command, task visibility, and preflight results.
4. If the request is initialization-only, the harness reports readiness and stops.
5. If startup readiness fails for an implementation request, the harness records failure state and stops.
6. If implementation is allowed, the harness resolves the implementation task deterministically.
7. The harness loads implementation-specific context.
8. The harness asks the LLM for a plan using both the original request and resolved task.
9. The plan acceptance gate rejects no-change readiness plans for implementation requests.
10. The harness asks the LLM for file changes or `NO_FILE_CHANGES`.
11. The execution manager applies only allowed workspace-relative file changes.
12. The generation acceptance gate verifies changed files and required files.
13. Missing task-specific product files are logged as `generation` failures before validation.
14. The harness reruns preflight.
15. The validator prechecks required files, then runs the implementation profile.
16. The scope guard classifies validation failures by file location.
17. Repair rules and repair prompts attempt targeted fixes only when failures are in scope.
18. The harness records success or failure in durable state files.
19. The controller updates `task_breakdown.md`; the LLM may propose changes but does not own final task status.

## Definition Of Done

A feature implementation task is only done when:

- startup readiness passed before implementation
- generated code works
- existing tests were preserved
- pytest passes
- Ruff passes
- no unrelated files were modified
- no protected state files were modified by generated file changes
- `progress.md` is updated by the harness controller
- `run_history.json` records the run
- `task_breakdown.md` is updated by the harness controller after validation
- `failure_log.json` is updated when failures occur

Initialization-only requests are done when:

- startup readiness checks have run
- readiness status has been reported
- no implementation phase was entered
- no source or test files were modified
- no task was marked complete
