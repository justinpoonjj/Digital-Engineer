## Project Summary

This is a simple Python project used to test a harnessed AI coding workflow.

The AI must follow the project rules, make minimal changes, and rely on validation before claiming completion.

## Rules:
- Use paths relative to the workspace directory.
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

## Definition of Done

A task is complete only when:

* The requested behavior is implemented.
* Tests pass.
* Ruff passes.
* `progress.md` is updated.