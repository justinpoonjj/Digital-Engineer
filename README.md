# Harness MVP

This repository is a Python harness prototype for experimenting with reliable AI-assisted coding workflows.

The core idea is:

> A capable model is not enough. Reliable execution comes from the harness around the model.

The harness does not simply ask an LLM to write code and trust the answer. It routes intent, checks startup readiness, resolves the implementation task, builds a task contract, applies generated file changes safely, validates the result with scoped profiles, repairs predictable failures, and records durable state only through controller-owned paths.

## Project Layout

```text
.
+-- main.py                         # harness lifecycle coordinator
+-- harness/
|   +-- context_loader.py            # context loading by mode
|   +-- execution_manager.py         # safe file application
|   +-- llm_service.py               # OpenAI client wrapper
|   +-- preflight.py                 # workspace structure checks
|   +-- prompts.py                   # plan/code/fix prompts
|   +-- repair_rules.py              # deterministic repairs
|   +-- state_manager.py             # progress/history/failure/task state
|   +-- validator.py                 # validation profiles
+-- tests/                           # harness/controller tests
|   +-- test_continuity_artifacts.py
|   +-- test_initialization_intent.py
+-- workspace/                       # generated product workspace
    +-- AGENTS.md
    +-- DECISIONS.md
    +-- feature_list.json
    +-- failure_log.json
    +-- harness_map.md
    +-- progress.md
    +-- pyproject.toml
    +-- run_history.json
    +-- task_breakdown.md
    +-- docs/
    |   +-- debugging-policy.md
    |   +-- repair-rules-guide.md
    |   +-- session-handoff.md
    |   +-- startup-readiness.md
    |   +-- state-management.md
    |   +-- testing-standards.md
    +-- src/                         # generated product source
    +-- tests/                       # generated product tests
```

The root `tests/` folder is for harness/controller tests. The `workspace/tests/` folder is for generated product tests only.

## Current Architecture

The current harness flow is:

```text
User request
-> intent parser
-> initialization phase
-> task resolver
-> task reconciliation
-> task contract builder
-> file state inspection
-> implementation context loading
-> plan generation
-> plan acceptance gate
-> code generation
-> generation acceptance gate
-> required file check
-> preflight
-> deterministic preflight repair
-> scoped validation
-> failure classifier
-> repair-scope guard
-> deterministic or LLM repair
-> state update
```

The important shift in this iteration is that the harness, not the LLM, decides what the task is and what files are required.

## Running The Harness

From the repository root:

```powershell
python main.py
```

The CLI asks:

```text
What should the harness do?
```

For initialization only:

```powershell
python main.py --init
```

Natural-language readiness requests also stop after initialization:

```text
Run startup readiness only. Do not implement any feature.
```

These requests do not enter planning, code generation, or file application.

## Startup Readiness

Startup readiness is an initialization concern, not an implementation task.

The readiness report checks:

- required workspace files are found and readable
- required directories exist
- validation commands are available
- task breakdown sections are visible
- preflight passes
- final readiness is `READY` or `NOT READY`

It checks workspace landing zones such as:

```text
workspace/src
workspace/tests
```

It does not require future product files such as `src/calculator.py` or `tests/test_calculator.py` during startup. Those files are required later by the task contract after code generation.

## Task Breakdown

`workspace/task_breakdown.md` separates initialization state from implementation work:

```text
Initialization Status
Current Active Implementation Task
Acceptance Criteria
Subtasks
Validation Requirements
Blockers
Next Step
```

The LLM may propose task breakdown updates, but the harness controller owns final task status updates after validation.

## Task Resolution And Reconciliation

Ambiguous requests such as:

```text
Implement the first task from task_breakdown.md.
```

are resolved deterministically by the harness before the LLM plans. The plan and code prompts receive both:

```text
Original user request
Resolved implementation task
```

This prevents the model from treating startup readiness as the implementation task.

For direct implementation requests, the latest user prompt wins over durable
workspace state. The controller compares the latest request with
`workspace/task_breakdown.md`, classifies it as the same task, an extension, a
replacement, or new work, and passes that decision to the planner before the
full workspace context. Older task files are treated as context unless the user
explicitly asks to implement a task from `task_breakdown.md`.

The controller also inspects required source and test files before planning.
Existing files are labeled as files to modify or extend, while missing files are
labeled as files to create. This prevents plans that say to recreate
`src/calculator.py` or `tests/test_calculator.py` when those files already
exist.

## Task Contracts

Implementation tasks are converted into executable contracts.

For the current calculator task, the contract requires:

```text
src/calculator.py
tests/test_calculator.py
```

The same contract defines:

- required files
- allowed repair files
- validation profile

If generated output does not satisfy the contract, the harness fails at the generation layer before validation.

## Generation Acceptance

The harness now checks generated output before running tests.

If the LLM returns no valid `FILE:` blocks, the harness retries generation once with a focused prompt. If required files are still missing, the harness records a `generation` failure and stops.

This prevents a bad flow like:

```text
no files generated
-> pytest tests/test_calculator.py
-> file not found
-> unnecessary repair loop
```

Missing product files are generation failures, not pytest failures.

## Execution Safety

`harness/execution_manager.py` accepts file changes only in this format:

```text
FILE: src/example.py
```python
full file content here
```
```

Paths must be relative to the workspace root:

```text
src/calculator.py
tests/test_calculator.py
```

Paths like this are rejected:

```text
workspace/src/calculator.py
workspace/tests/test_calculator.py
```

Protected workspace files include:

- `AGENTS.md`
- `feature_list.json`
- `progress.md`
- `task_breakdown.md`

Protected harness test paths include:

- `tests/test_initialization_intent.py`
- `tests/test_continuity_artifacts.py`

The generated workspace may not modify harness/controller tests.

## Context Modes

`harness/context_loader.py` supports context modes:

```python
load_context(mode="initialization")
load_context(mode="implementation")
```

Initialization context includes startup readiness and state orientation.

Implementation context focuses on:

- agent rules
- harness map
- testing standards
- repair rules
- debugging policy
- task breakdown
- feature list

This reduces the chance that readiness documentation dominates implementation planning.

## Validation Profiles

`harness/validator.py` supports scoped profiles:

- `startup`
- `implementation`
- `calculator`
- `harness`
- `full`

The calculator profile validates product files only:

```text
pytest tests/test_calculator.py
ruff check src/calculator.py tests/test_calculator.py
```

Before running pytest or Ruff, the validator checks that required files exist. Missing required files are reported as generation errors.

## Preflight And Deterministic Repair

Preflight checks catch structural and import issues before validation.

Current checks include:

- nested `workspace/workspace`
- missing `src/`
- missing `tests/`
- incorrect `test/`
- bad `from src...` imports
- missing `import pytest` when pytest features are used
- unused `import pytest` when pytest features are not used

`harness/repair_rules.py` now includes `apply_preflight_repairs()`.

It can fix:

```python
from src.calculator import add
```

to:

```python
from calculator import add
```

and remove unused:

```python
import pytest
```

when the test only uses plain `assert`.

## Repair Scope

The harness distinguishes product bugs from harness bugs.

For the calculator task, allowed repair files are:

```text
src/calculator.py
tests/test_calculator.py
```

If validation fails in a root harness test, controller file, state file, or unrelated doc, the harness stops and logs `validation_scope` instead of asking the LLM to repair it.

The rule is documented in:

```text
workspace/docs/debugging-policy.md
```

and enforced in controller code.

## State And Handoff

The controller owns durable state updates:

- `workspace/progress.md`
- `workspace/run_history.json`
- `workspace/failure_log.json`
- `workspace/task_breakdown.md`

The LLM may not directly rewrite these through generated file changes.

Successful runs append progress and run history. Failed runs append failure history and task breakdown blockers.

## Running Tests

Run harness/controller tests from the repository root:

```powershell
pytest tests
```

Run generated product tests from the workspace:

```powershell
cd workspace
pytest tests/test_calculator.py
```

Run Ruff when available:

```powershell
cd workspace
ruff check src/calculator.py tests/test_calculator.py
```

At the time of writing, this environment reports Ruff as unavailable on PATH, so startup readiness returns `NOT READY` until Ruff is installed or exposed to the harness environment.

## Important Docs

- `workspace/AGENTS.md` - high-level agent rules
- `workspace/harness_map.md` - current architecture map
- `workspace/DECISIONS.md` - architectural decision log
- `workspace/task_breakdown.md` - active implementation task
- `workspace/docs/startup-readiness.md` - readiness checklist and report expectations
- `workspace/docs/debugging-policy.md` - scoped repair policy
- `workspace/docs/testing-standards.md` - product test conventions
- `workspace/docs/repair-rules-guide.md` - repair behavior guidance
- `workspace/docs/state-management.md` - state ownership rules
- `workspace/docs/session-handoff.md` - handoff expectations

## Design Principles

### Harness Decides, LLM Implements

The model should not infer the active task from noisy context. The harness resolves the task and passes it explicitly into prompts.

### Startup Is Not Implementation

Readiness checks confirm the workspace is safe to use. They do not count as product work.

### Generation Must Produce Artifacts

Implementation requests must generate required files before validation runs.

### Validation Is Scoped

Product implementation should not accidentally validate or repair harness tests.

### Repairs Must Stay In Scope

The Digital Engineer can repair files directly related to the active product task. Harness bugs are logged and routed separately.

### Deterministic Repairs Beat Repeated LLM Fixes

Predictable failures such as bad imports and unused pytest imports are fixed by code before asking the LLM for another repair.

## Current Known Environment Issue

Startup readiness currently reports:

```text
ruff --version: FAIL
Command not found: ruff
```

Install or expose Ruff in the Python environment used by the harness before expecting full readiness or lint validation to pass.

## Summary

This harness started as a simple prompt-driven coding loop.

It now includes:

- intent routing
- readiness reports
- deterministic task resolution
- task contracts
- generation retries
- required-file gates
- protected file writes
- separated harness and product tests
- validation profiles
- preflight repairs
- scoped repair routing
- durable state and handoff logs

The main harness-engineering pattern is:

```text
Do not rely on the model to remember every rule.
Put important rules into the controller.
Verify the result.
Repair predictable failures with code.
Record only controlled outcomes.
```
