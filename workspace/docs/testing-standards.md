# Testing Standards

## Core Rules
- New features should include tests.
- Existing tests must not be deleted to make validation pass.
- Existing tests must not be weakened unless the requirement itself changed.
- Edge-case tests should be preserved.

## Pytest Expectations
- Use pytest for all tests.
- Use simple `assert` statements for normal expected values.
- Use `pytest.raises` for expected exceptions.
- Import `pytest` only when the file uses pytest-specific features such as `pytest.raises`, `pytest.mark`, or `pytest.fixture`.
- Prefer small focused tests.
- Test normal cases and edge cases.

## Workspace Layout
- Put tests directly inside `tests/`.
- Do not put tests inside `workspace/tests/`.
- When `pyproject.toml` has `pythonpath = ["src"]`, import files inside `src/` directly.
- Example: import `src/calculator.py` as `from calculator import add`.

## Ruff Expectations
- Only import names that are actually used.
- Avoid unused imports because Ruff rule `F401` will fail validation.
- Keep imports sorted and formatted because Ruff rule `I001` will fail validation.

## Repair Behavior
When pytest fails:
1. Read the failing assertion.
2. Identify whether the implementation or the test is wrong.
3. Prefer fixing the implementation.
4. Preserve the same or greater number of tests unless the user explicitly asked to delete tests.
5. Rerun pytest.
6. Do not claim success until pytest passes.
