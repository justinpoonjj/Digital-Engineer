## Project Summary

This is a simple Python project used to test a harnessed AI coding workflow.

The AI must follow the project rules, make minimal changes, and rely on validation before claiming completion.

## Rules:
- Use paths relative to the workspace directory.
- Never prefix generated file paths with `workspace/` or `workspace\`.
- Correct generated paths look like `src/calculator.py` and `tests/test_calculator.py`.
- Incorrect generated paths look like `workspace/src/calculator.py`.
- Do not create or modify a nested `workspace/` directory.
- Include the full content of each file.
- Do not include explanations outside the file blocks.
- Do not modify unrelated files.
- Do not modify progress.md.
- The harness controller will update progress.md only after validation passes.
- Follow the import rules in AGENTS.md.
- If pyproject.toml has pythonpath = ["src"], import modules inside src directly.
- Example: src/calculator.py should be imported as `from calculator import add`.

## Verification Commands

```powershell
pytest
ruff check .
```

## Python Test Rules

- Use simple `assert` statements for basic tests.
- Put tests directly inside `tests/`.
- Do not put tests inside `workspace/tests/`.
- Do not import `pytest` unless the test file directly uses pytest-specific features.
- Only import what is actually used.
- Avoid unused imports because Ruff rule `F401` will fail validation.
- Keep imports sorted and formatted because Ruff rule `I001` will fail validation.

Correct:

```python
from calculator import add


def test_add_positive_numbers():
    assert add(2, 3) == 5
```

Incorrect:

```python
import pytest

from calculator import add


def test_add_positive_numbers():
    assert add(2, 3) == 5
```

## Definition of Done

A task is complete only when:

* The requested behavior is implemented.
* Tests pass.
* Ruff passes.
* `progress.md` is updated.
