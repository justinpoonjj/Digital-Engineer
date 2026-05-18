# Harness MVP

This repository is a small Python project used to experiment with harnessed AI
coding workflows.

The core lesson from this project is simple:

> A capable model is not enough. Reliable execution comes from the harness
> around the model.

The harness in this repo plans a task, asks an LLM to produce file changes,
applies those changes into `workspace/`, checks the result with preflight rules,
runs validation, applies deterministic repairs for known failure modes, and only
records progress after validation passes.

This README documents the robustness work added to the harness, why each part
exists, and what failure it prevents.

## Background

This project follows the harness-engineering idea described in
[Walking Labs Lecture 01: Strong Models Don't Mean Reliable Execution](https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-01-why-capable-agents-still-fail/).

The lecture makes a few points that directly apply here:

- Model capability and execution reliability are different things.
- When an agent fails, first inspect the harness instead of immediately blaming
  or replacing the model.
- A harness includes instructions, tools, environment setup, state management,
  verification feedback, and deterministic guardrails.
- A good workflow has an explicit Definition of Done, such as tests passing and
  lint passing.
- Failures should feed a diagnostic loop: run, observe failure, attribute it to
  a harness layer, fix that layer, and rerun.

This repo is a practical version of that diagnostic loop.

## Project Layout

```text
.
+-- main.py
+-- harness/
|   +-- context_loader.py
|   +-- execution_manager.py
|   +-- llm_service.py
|   +-- preflight.py
|   +-- prompts.py
|   +-- repair_rules.py
|   +-- state_manager.py
|   +-- validator.py
+-- workspace/
    +-- AGENTS.md
    +-- feature_list.json
    +-- progress.md
    +-- pyproject.toml
    +-- src/
    |   +-- calculator.py
    +-- tests/
        +-- test_calculator.py
```

The harness code lives in `harness/`.

The generated project lives in `workspace/`.

The LLM is allowed to modify project files under `workspace/`, but the harness
protects important state files such as `AGENTS.md`, `feature_list.json`, and
`progress.md`.

## How The Harness Runs

The main workflow is implemented in `main.py`.

At a high level, the loop is:

1. Load project context.
2. Run preflight checks.
3. Ask the LLM to produce a plan.
4. Ask the LLM to produce file changes.
5. Apply the file changes safely.
6. Run preflight checks again.
7. Apply deterministic repairs for known problems.
8. Run validation.
9. If validation fails, apply deterministic repairs again.
10. If needed, ask the LLM for a limited number of fix attempts.
11. Stop early if the same validation error repeats.
12. Update `progress.md` only after validation passes.

This matters because the LLM is not trusted as the final authority on whether a
task is done. The harness verifies the result.

## Definition Of Done

A task is complete only when:

- The requested behavior is implemented.
- Tests pass.
- Ruff passes.
- The workspace layout is valid.
- The harness records the successful run in `workspace/progress.md`.

This avoids the common "verification gap" where an agent claims completion even
though the code still fails tests or lint.

## Context Layer

File: `harness/context_loader.py`

The context loader reads:

- `workspace/AGENTS.md`
- `workspace/feature_list.json`
- `workspace/progress.md`

and combines them into one context string for the LLM.

This gives the LLM project rules, current feature state, and prior progress
without asking it to rediscover everything from scratch.

Why this improves robustness:

- Reduces repeated project discovery.
- Keeps project rules visible.
- Makes the repository the system of record.
- Helps avoid long-running task drift.

## Prompt Layer

File: `harness/prompts.py`

The prompt layer contains three prompts:

- `build_plan_prompt`
- `build_code_prompt`
- `build_fix_prompt`

The plan prompt asks the LLM to reason about the task before changing files.

The code prompt asks for full file changes using a strict format:

    FILE: src/example.py
    ```python
    full file content here
    ```

The fix prompt gives the LLM the validation output and asks it to repair only the
failure.

### Important Prompt Rules Added

The harness now gives explicit rules for pytest imports:

```text
If the test uses pytest.raises, pytest.mark, pytest.fixture, or any pytest.
reference, then import pytest is required.

If the test does not use any pytest. reference, do not import pytest.
```

This was added because the model previously learned only one side of the rule:

```text
Do not import pytest unless pytest is used.
```

That was incomplete. The opposite rule is also required:

```text
If pytest is used, import pytest.
```

The prompt also now says:

- Do not remove existing tests unless explicitly asked.
- Do not remove edge-case tests, especially divide-by-zero tests.
- Do not remove `pytest.raises` just to avoid importing pytest.
- If Ruff reports `I001`, only sort and format imports.
- Do not delete tests, assertions, or pytest usage to fix lint errors.
- Sort imported names alphabetically.

For the calculator example, the correct import order is:

```python
from calculator import add, divide, multiply, subtract
```

not:

```python
from calculator import add, subtract, multiply, divide
```

Why this improves robustness:

- Makes hidden assumptions explicit.
- Prevents the LLM from fixing lint by deleting meaningful tests.
- Separates behavior preservation from formatting repair.
- Gives the model a concrete example of the expected import order.

## Execution Safety Layer

File: `harness/execution_manager.py`

The execution manager parses the LLM's output and writes files into
`workspace/`.

It accepts only file blocks matching this pattern:

    FILE: path/to/file.py
    ```python
    content
    ```

It also enforces path safety.

### Protected Files

The LLM is not allowed to modify:

- `AGENTS.md`
- `feature_list.json`
- `progress.md`

These files are controlled by the harness.

### Path Rules

The LLM must return paths relative to the workspace root:

Correct:

```text
src/calculator.py
tests/test_calculator.py
```

Incorrect:

```text
workspace/src/calculator.py
workspace/tests/test_calculator.py
```

The harness rejects nested workspace paths because they create invalid project
layouts such as:

```text
workspace/workspace/src/calculator.py
```

Why this improves robustness:

- Prevents accidental writes outside the workspace.
- Prevents nested workspace directories.
- Prevents the LLM from overwriting harness-owned state files.
- Forces all changes through a predictable format.

## Preflight Layer

File: `harness/preflight.py`

Preflight checks run before validation.

They catch structural problems that are easier to diagnose before running tests.

The current preflight checks detect:

- A nested `workspace/workspace` directory.
- Missing `workspace/tests`.
- Incorrect singular `workspace/test`.
- Missing `workspace/src`.
- Bad imports such as `from src.calculator import add`.
- Test files using pytest features without `import pytest`.
- Test files importing pytest without using pytest features.

### Pytest Preflight Rule

The pytest rule is intentionally two-way:

```text
uses pytest features + no import pytest = problem
imports pytest + no pytest features = problem
```

This catches both common failures:

- The test uses `pytest.raises` but forgot `import pytest`.
- The test imports `pytest` but only uses plain `assert`, causing Ruff `F401`.

Why this improves robustness:

- Fails earlier with clearer messages.
- Catches known mistakes before the validation loop gets noisy.
- Turns a vague runtime failure into a specific harness diagnosis.

## Validation Layer

File: `harness/validator.py`

Validation runs the project commands from inside `workspace/`:

```powershell
pytest
ruff check .
```

The validator captures:

- command
- return code
- stdout
- stderr

and returns a `ValidationResult`.

If any command fails, validation stops and returns the full output collected so
far.

Why this improves robustness:

- The harness does not trust visual inspection.
- The LLM receives concrete failure output.
- The Definition of Done is machine-checkable.

## Deterministic Repair Layer

File: `harness/repair_rules.py`

This is one of the most important robustness layers.

Some failures are predictable enough that the harness should fix them directly
instead of asking the LLM to reason about them.

The current deterministic repairs are:

- `apply_basic_import_repairs`
- `apply_basic_ruff_repairs`
- `apply_ruff_auto_fix`
- `apply_simple_import_sort`
- `apply_basic_pytest_repairs`

### Repair: Bad `src.` Imports

Function:

```python
apply_basic_import_repairs(validation_output)
```

If validation reports:

```text
ModuleNotFoundError: No module named 'src'
```

the repair scans test files and replaces:

```python
from src.calculator import add
```

with:

```python
from calculator import add
```

This matches the workspace's `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
```

Because `src` is already on the Python path, modules inside `src/` are imported
directly.

### Repair: Missing `import pytest`

Function:

```python
apply_basic_pytest_repairs(validation_output)
```

This repair triggers when validation or preflight reports:

```text
NameError: name 'pytest' is not defined
```

or:

```text
uses pytest features but does not import pytest
```

It scans `workspace/tests/test_*.py`.

If a test file contains pytest usage such as:

```python
with pytest.raises(ValueError):
    divide(5, 0)
```

but does not contain:

```python
import pytest
```

the repair adds:

```python
import pytest

```

to the top of the file.

Why this matters:

- The LLM previously generated a valid pytest usage but forgot the import.
- A prompt-only fix was not enough.
- This failure is simple enough to fix with code.

### Repair: Ruff Import Sorting

Function:

```python
apply_basic_ruff_repairs(validation_output)
```

This repair handles Ruff failures such as:

```text
I001 Import block is un-sorted or un-formatted
```

When `I001` appears, the harness first calls:

```python
apply_ruff_auto_fix()
```

That function tries to run:

```powershell
ruff check . --fix
```

from inside `workspace/`.

This is the best fix because Ruff knows exactly how it wants imports organized.

If Ruff is not available on PATH, the harness falls back to:

```python
apply_simple_import_sort(files)
```

That fallback handles simple one-line imports like:

```python
from calculator import add, subtract, multiply, divide
```

and rewrites them alphabetically:

```python
from calculator import add, divide, multiply, subtract
```

Why this matters:

- Import sorting is mechanical.
- The model should not be asked to creatively solve mechanical formatting.
- In the observed failure, the LLM tried to fix `I001` by removing pytest usage
  and reducing the test count from 5 to 4.
- Deterministic import repair prevents that class of damage.

### Repair: Unused `pytest`

Function:

```python
apply_basic_ruff_repairs(validation_output)
```

When Ruff reports `F401`, the harness checks whether `import pytest` is present
but no pytest feature is used.

If pytest is unused, the repair removes the import.

The key detail is that this repair must not remove `import pytest` if the file
still contains pytest usage such as:

```python
pytest.raises
pytest.mark
@pytest
```

Why this matters:

- It handles the original "unused pytest import" case.
- It does not break the opposite case where pytest is genuinely required.

## Fix Attempt Loop

File: `main.py`

If validation fails after deterministic repairs, the harness asks the LLM to fix
the failure.

The number of LLM fix attempts is limited:

```python
MAX_FIX_ATTEMPTS = 2
```

The harness also tracks the previous validation output.

If the same validation error repeats, it stops early:

```text
Same validation error repeated. Stopping early.
```

Why this improves robustness:

- Prevents infinite loops.
- Avoids wasting tokens on repeated failed fixes.
- Makes repeated failure visible as a harness issue.

## State Layer

File: `harness/state_manager.py`

Progress is appended only after validation passes.

Each progress entry records:

- timestamp
- user request
- plan
- changed files
- validation output

This is important because `progress.md` becomes the durable memory of successful
runs.

Why this improves robustness:

- Failed attempts do not get recorded as successful progress.
- Later runs can see what was done before.
- Humans can audit what changed and why.

## Case Study: The Pytest Import Failure

The observed failure looked like this:

```python
def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(5, 0)
```

but the file did not include:

```python
import pytest
```

That caused:

```text
NameError: name 'pytest' is not defined
```

The first prompt rule only said:

```text
Do not import pytest unless pytest is directly used.
```

That rule was incomplete. The test did directly use pytest, so the correct
behavior was to import it.

The harness now handles this at three levels:

1. Prompt rule:
   if a file contains `pytest.`, it must include `import pytest`.

2. Preflight rule:
   if a test uses pytest features but does not import pytest, report a problem.

3. Deterministic repair:
   if the problem appears, insert `import pytest` automatically.

This is the desired harness pattern:

```text
Prompt rule + preflight check + deterministic repair
```

## Case Study: The Ruff `I001` Failure

The next failure was Ruff import ordering:

```text
I001 Import block is un-sorted or un-formatted
```

The correct import was:

```python
from calculator import add, divide, multiply, subtract
```

But the LLM tried to fix the problem by removing pytest usage and deleting the
divide-by-zero test.

That passed pytest with fewer tests, but it was the wrong fix.

The harness now prevents this in two ways:

1. The prompt explicitly says not to delete tests or remove `pytest.raises` to
   fix lint.

2. The repair layer handles `I001` mechanically before the LLM gets another
   chance to edit behavior.

This turns a soft instruction into an executable guardrail.

## Current Calculator Example

The current calculator module includes:

```python
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

The test file includes:

```python
import pytest

from calculator import add, divide, multiply, subtract


def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(5, 0)
```

The divide-by-zero test is important because it verifies the error behavior, not
just the happy path.

## Running The Harness

From the repository root:

```powershell
python main.py
```

Then enter a task when prompted:

```text
Add subtract, multiply, and divide functions to the existing calculator module with tests. Keep the existing add function and tests.
```

The harness will:

- load context
- ask the LLM for a plan
- ask the LLM for file changes
- apply file changes
- run preflight checks
- run deterministic repairs
- run validation
- ask for fixes if needed
- update progress only on success

## Running Validation Manually

From inside `workspace/`:

```powershell
pytest
ruff check .
```

If Ruff is not installed or not on PATH, install it in the environment used by
the harness before expecting full validation to pass.

The harness can still apply a limited fallback import sort, but final validation
requires the real `ruff` command.

## Troubleshooting

### `pytest` passes but Ruff fails with `I001`

This means imports are not sorted or formatted according to Ruff.

Expected calculator import order:

```python
from calculator import add, divide, multiply, subtract
```

The harness should now attempt `ruff check . --fix` automatically.

### `NameError: name 'pytest' is not defined`

The test file uses pytest features without importing pytest.

Expected fix:

```python
import pytest
```

at the top of the test file.

The harness should now catch this during preflight or deterministic repair.

### Ruff reports `F401` for `pytest`

This means `pytest` is imported but no pytest feature is used.

Valid options:

- remove `import pytest` if the file only uses plain asserts
- keep `import pytest` if the file uses `pytest.raises`, `pytest.mark`,
  `pytest.fixture`, or another `pytest.` reference

The harness must not remove the test code just to make the import unused.

### The LLM writes files under `workspace/workspace`

This means the LLM returned paths like:

```text
workspace/src/calculator.py
```

instead of:

```text
src/calculator.py
```

The execution manager and preflight checks reject this.

## Design Principles Used

### 1. Prompt Rules Are Soft Constraints

Prompt rules help guide the model, but they are not enough for predictable
reliability.

Whenever a failure is simple and recurring, convert it into code.

In this repo:

- pytest import mistakes became preflight and repair rules
- Ruff import sorting became deterministic repair
- nested workspace paths became path validation

### 2. Verification Is The Source Of Truth

The LLM's answer is not considered complete until validation passes.

This follows the harness-engineering idea that a Definition of Done should be
machine-verifiable.

### 3. Deterministic Repairs Beat Repeated LLM Fixes

The LLM should not be asked to solve problems that tools can fix exactly.

Examples:

- import sorting
- obvious import path rewrites
- missing `import pytest` when `pytest.` is used

### 4. Preserve Behavior While Fixing Format

Formatting and lint repairs must not delete behavior.

That is why the prompt now says:

```text
If Ruff reports I001, only sort and format the import block.
Do not delete tests, assertions, or pytest usage to fix I001.
```

### 5. Every Failure Should Strengthen The Harness

The goal is not merely to fix one run.

The goal is to make sure the same failure does not happen again.

That is why this harness now has:

- better prompt rules
- preflight detection
- deterministic repair functions
- repeated-error stopping
- validation-based progress updates

## Future Improvements

Useful next improvements:

- Add tests for the harness itself.
- Add a preflight rule that checks test counts do not decrease after a fix.
- Parse pytest output and remember how many tests were collected.
- Make `validator.py` handle missing commands more gracefully.
- Add a dependency check for `ruff` before running the harness.
- Run `ruff check . --fix` only for fixable lint categories.
- Add structured logs for each failure layer:
  task specification, context provision, environment, verification, and state.
- Add a dry-run mode that prints intended file writes before applying them.

## Summary

This harness started as a prompt-driven coding loop.

It became more robust by adding executable guardrails:

- context loading
- protected file writes
- path normalization
- preflight checks
- validation commands
- deterministic repair rules
- repeated-failure stopping
- progress logging after successful validation

That is the main harness-engineering pattern:

```text
Do not rely on the model to remember every rule.
Put important rules into the environment.
Verify the result.
Repair predictable failures with code.
Record only validated success.
```
