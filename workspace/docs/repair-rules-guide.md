# Repair Rules Guide

## Purpose
Repair rules convert validation failures into targeted LLM repair instructions.

The goal is to repair the specific failure while preserving the requested behavior, existing tests, and unrelated files.

## Ruff Failures
When Ruff fails:
- identify the error code
- identify the file and line
- explain the likely fix
- avoid broad rewrites

Common examples:
- `F401`: remove only the unused import, not the test or implementation that should use it
- `I001`: sort and format imports without deleting assertions or pytest usage

## Pytest Failures
When pytest fails:
- identify the failing test
- identify the expected behavior
- preserve the test unless it is clearly invalid
- repair the implementation first

Common examples:
- `ModuleNotFoundError`: check whether imports match `pythonpath = ["src"]`
- `NameError: name 'pytest' is not defined`: add `import pytest` when the test uses `pytest.raises`, `pytest.mark`, or `pytest.fixture`
- `collected 0 items`: check whether tests were written to the wrong directory

## Forbidden Repair Shortcuts
- Do not delete tests.
- Do not skip tests.
- Do not weaken assertions.
- Do not remove exception tests such as `pytest.raises`.
- Do not remove `import pytest` when pytest features are still used.
- Do not silence Ruff without fixing the cause.

## Retry Loop
1. Run validation.
2. Parse failure.
3. Generate targeted repair prompt.
4. Apply repair.
5. Rerun validation.
6. Log result.
