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

User request:
{user_request}

Project context:
{context}

Implementation plan:
{plan}

Now generate the required file changes.

Return ONLY file changes using this exact format:

FILE: relative/path/to/file.py
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
- If the error is `ModuleNotFoundError`, inspect the import path.
- If pyproject.toml has `pythonpath = ["src"]`, then files inside `src/` are imported directly.
- Example: `src/calculator.py` should be imported as `from calculator import add`, not `from src.calculator import add`.
- Do not modify progress.md.
- Only change files related to the failure.
- Include the full content of each changed file.

Return ONLY file changes using this exact format:

FILE: relative/path/to/file.py
```python
full file content here
```
"""