def build_plan_prompt(user_request: str, context: str) -> str:
    return f"""
You are working inside a harnessed software project.

Your job is to create an implementation plan only.

Do not write code yet.
    
User request:
{user_request}

Project context:
{context}

Return your answer in this format:

## Understanding
Explain what the user wants.

## Relevant Project State
Mention which existing files or features matter.

## Implementation Plan
Give a numbered plan.

## Files To Change
List the files that should be created or modified.

## Validation Plan
List the commands that should be run.
"""

def build_code_prompt(user_request: str, context: str, plan: str) -> str: 
    return f"""
You are working inside a harnessed software project.

The workspace root is already handled by the harness.
You must return paths relative to the workspace root.

User request:
{user_request}

Project context:
{context}

Implementation plan:
{plan}

Now generate the required file changes.

Path rules:
- Use paths relative to the workspace root.
- Never prefix paths with `workspace/` or `workspace\\`.
- Correct path: `src/calculator.py`.
- Correct path: `tests/test_calculator.py`.
- Incorrect path: `workspace/src/calculator.py`.
- Incorrect path: `workspace/tests/test_calculator.py`.
- Do not create or modify any nested `workspace/` directory.

File modification rules:
- Do not modify `AGENTS.md`.
- Do not modify `progress.md`.
- Do not modify `feature_list.json`.
- The harness controller updates progress only after validation passes.
- Do not modify unrelated files.

Python test rules:
- Put tests directly inside `tests/`.
- Do not put tests inside `workspace/tests/`.
- Do not import pytest unless the test file actually uses pytest features.
- Examples of pytest features include pytest.mark.parametrize, pytest.raises, and fixtures.
- If pytest is not directly used, write plain assert-based tests without importing pytest.
- If pyproject.toml has `pythonpath = ["src"]`, import modules inside `src/` directly.
- Example: import `src/calculator.py` as `from calculator import add`.
- All imports must be sorted and formatted according to Ruff.
- Before returning file changes, mentally check that every imported name is used.
- Avoid unused imports because Ruff F401 will fail validation.

Return ONLY file changes using this exact format:

FILE: src/example.py
```python
full file content here
```

FILE: tests/test_example.py
```python
full file content here
```
"""

def build_fix_prompt(
    user_request: str,
    context: str,
    validation_output: str,
) -> str:
    return f"""
The previous implementation failed validation.

User request:
{user_request}

Project context:
{context}

Validation output:
{validation_output}

Your task is to fix the validation failure.

Diagnose the error carefully before producing file changes.

Important rules:
- Do not repeat the same failed solution.
- Do not modify progress.md.
- Only change files related to the failure.
- Include the full content of each changed file.

Critical path rules:
- The workspace root is already handled by the harness.
- Use paths relative to the workspace root.
- Never prefix paths with `workspace/` or `workspace\\`.
- Correct path: `src/calculator.py`.
- Correct path: `tests/test_calculator.py`.
- Incorrect path: `workspace/src/calculator.py`.
- Incorrect path: `workspace/tests/test_calculator.py`.
- Do not create or modify any nested `workspace/` directory.

Critical file rules:
- Do not modify `AGENTS.md`.
- Do not modify `progress.md`.
- Do not modify `feature_list.json`.
- Only change files related to the failure.

Validation diagnosis rules:
- If pytest says "collected 0 items", check whether tests were written into the wrong directory.
- If pytest collects from `workspace/tests/...`, a nested workspace was created incorrectly.
- If `calculator` cannot be imported, check that `src/calculator.py` exists.

Import and lint rules:
- If the error is `ModuleNotFoundError`, inspect the import path.
- If pyproject.toml has `pythonpath = ["src"]`, then files inside `src/` are imported directly.
- Example: import `src/calculator.py` as `from calculator import add`.
- Do not import it as `from src.calculator import add`.
- If Ruff reports `F401`, remove the unused import.
- If Ruff reports `I001`, sort and format the import block.
- Do not import `pytest` unless pytest is directly used in the test file.
- For simple tests, use plain `assert` statements without importing pytest.

Before returning file changes, ensure:
- The calculator module path is exactly `src/calculator.py`.
- The test file path is exactly `tests/test_calculator.py`.
- No returned path starts with `workspace/`.

Return ONLY file changes using this exact format:

FILE: tests/test_example.py
```python
full file content here
```
"""
