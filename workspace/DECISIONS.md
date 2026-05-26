# Decisions

## 2026-05-25: Keep AGENTS.md as a routing file

### Decision

`AGENTS.md` should remain short and route to focused topic docs.

### Reason

Lecture 4 warns that one giant instruction file creates instruction bloat and
lowers instruction signal-to-noise ratio.

### Impact

Detailed testing rules stay in `docs/testing-standards.md`.
Repair logic stays in `docs/repair-rules-guide.md`.
State rules stay in `docs/state-management.md`.
Session lifecycle rules stay in `docs/session-handoff.md`.

### Revisit Condition

Revisit if agents repeatedly fail to discover the correct topic docs.

## 2026-05-25: Make continuity first-class

### Decision

Every harness run should follow an explicit clock-in and clock-out lifecycle.

### Reason

Lecture 5 identifies rebuild cost as a core risk for long-running agent work. A
fresh agent needs to know what happened, why it happened, and how to resume.

### Impact

The context loader includes durable state, decisions, and session handoff docs.
Run history includes session IDs, timestamps, changed files, and final status.
Failure logs preserve repaired intermediate failures as well as final failures.

### Revisit Condition

Revisit if run logs become noisy enough that they slow down future agents.

## 2026-05-26: Separate initialization from implementation

### Decision

Startup readiness is an initialization concern, not an implementation task.
`task_breakdown.md` separates `Initialization Status` from the `Current Active Implementation Task`.

### Reason

The harness should not let startup-readiness language drift into product implementation. Initialization checks decide whether the session can safely begin. Implementation tasks describe source and test changes.

### Impact

Natural-language readiness requests stop after initialization.
Implementation requests resolve a concrete task before planning.
Readiness output is a deterministic report with files, directories, commands, task visibility, preflight, and state consistency.

### Revisit Condition

Revisit if more intent categories need distinct routing, such as summary-only or repair-only requests.

## 2026-05-26: Harness owns task resolution and task status

### Decision

The harness controller resolves ambiguous requests such as "first task from task_breakdown.md" before the LLM plans or writes code.

The LLM may propose task breakdown updates, but the harness controller owns final writes to task status after validation.

### Reason

The LLM should implement the task selected by the harness, not infer or rewrite project state on its own. This prevents startup readiness or stale history from being mistaken for the active implementation task.

### Impact

Plan, code, and fix prompts receive both the original user request and the resolved implementation task.
`task_breakdown.md` is protected from normal generated file changes.
Controller updates append success or failure status only after validation or controlled failure.

### Revisit Condition

Revisit if task breakdown editing needs a richer structured format than Markdown.

## 2026-05-26: Split harness tests from workspace product tests

### Decision

Harness/controller tests live in root `tests/`.
Generated product tests live in `workspace/tests/`.

### Reason

Product implementation validation should not accidentally run or repair harness tests. The Digital Engineer may modify product tests, but not controller regression tests.

### Impact

Root `tests/` contains harness-level regression tests such as initialization intent, task resolution, generation gates, and continuity artifacts.
`workspace/tests/` is reserved for generated application tests.
`execution_manager.py` rejects protected harness test paths from generated file changes.

### Revisit Condition

Revisit if the workspace needs its own protected internal tests separate from generated product tests.

## 2026-05-26: Use validation profiles

### Decision

Validation is profile-based instead of one broad command set.

Profiles include:

- `startup`
- `implementation`
- `calculator`
- `harness`
- `full`

### Reason

Different phases need different validation scopes. A calculator implementation should validate calculator files, not root harness tests.

### Impact

Implementation validation targets product files.
Harness validation targets root controller tests and controller code.
The validator prechecks required calculator files before running pytest or Ruff.

### Revisit Condition

Revisit when additional product task types need dedicated profiles.

## 2026-05-26: Add generation acceptance gates

### Decision

Implementation generation must satisfy a task contract before validation runs.

For the calculator add task, the contract requires:

- `src/calculator.py`
- `tests/test_calculator.py`

### Reason

An implementation request that produces no file changes is a generation failure, not a pytest failure. Missing required generated files should be caught before validation.

### Impact

The harness retries generation once when output does not contain usable file blocks.
If required files are still missing, the harness logs a `generation` failure and does not run pytest or enter the validation repair loop.

### Revisit Condition

Revisit if tasks need contract data stored outside `main.py`, such as in JSON or the task breakdown file.

## 2026-05-26: Enforce repair scope

### Decision

The harness classifies validation failures by file location and allows LLM repair only when failures are inside the resolved task scope.

### Reason

The Digital Engineer should not repair unrelated harness tests, controller code, state files, or docs while implementing a product feature.

### Impact

Out-of-scope validation failures are logged as `validation_scope`.
The harness stops instead of asking the LLM to edit unrelated files.
`docs/debugging-policy.md` documents the rule, and controller code enforces it.

### Revisit Condition

Revisit if multi-file or cross-cutting product tasks need a richer allowed-scope builder.

## 2026-05-26: Check workspace landing zones during startup

### Decision

Startup readiness checks required workspace directories, not future product files for the active implementation task.

### Reason

A fresh implementation task may need the agent to create product files. Startup readiness should verify that `src/` and `tests/` exist as landing zones, while the generation acceptance gate verifies task-specific files after code generation.

### Impact

Initialization does not fail just because `src/calculator.py` or `tests/test_calculator.py` has not been created yet.
Calculator task generation still requires those files before validation runs.

### Revisit Condition

Revisit if feature completion state becomes authoritative enough to require a separate consistency audit mode.
