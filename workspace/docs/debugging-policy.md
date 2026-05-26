# Debugging Policy

## Scope Rules

For implementation tasks, the Digital Engineer may only repair files directly related to the requested feature.

For calculator implementation tasks, allowed files are:

- `src/calculator.py`
- `tests/test_calculator.py`

## Protected Debug Targets

The Digital Engineer must not repair:

- harness controller files
- harness tests
- startup readiness tests
- continuity artifact tests
- state files
- task breakdown files

## Failure Routing

If validation fails outside the allowed task scope:

- stop implementation repair
- classify the failure as `validation_scope`
- log the failure
- do not ask the LLM to edit unrelated files

## Generation Acceptance

Implementation generation must satisfy the resolved task contract before validation runs.

For calculator implementation tasks, required files are:

- `src/calculator.py`
- `tests/test_calculator.py`

If the Digital Engineer returns no valid file changes, or if required files are still missing after generation:

- stop before validation
- classify the failure as `generation`
- log the failure
- do not run pytest
- do not enter the validation repair loop

## Validation Precheck

Scoped validation must check required files before invoking pytest or Ruff.

Missing required product files are generation failures, not pytest failures.
