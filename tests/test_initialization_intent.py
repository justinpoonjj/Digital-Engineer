import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import main
from harness.execution_manager import apply_file_changes
from harness.repair_rules import apply_preflight_repairs
from harness.validator import run_validation


def test_initialization_only_request_is_detected():
    request = (
        "Run startup readiness only. Do not implement any feature. "
        "Check whether the workspace is ready for a fresh agent session."
    )

    assert main.is_initialization_only_request(request)


def test_implementation_request_is_not_initialization_only():
    assert not main.is_initialization_only_request("Add a modulo function with tests.")


def test_no_file_changes_output_is_supported():
    assert apply_file_changes("NO_FILE_CHANGES") == []


def test_initialization_only_request_does_not_enter_implementation(capsys, monkeypatch):
    monkeypatch.setattr(main, "initialize_session", lambda: ("context", []))
    monkeypatch.setattr(main, "get_next_session_id", lambda: "session_test")

    main.run_harness(
        "Run startup readiness only. Do not implement any feature. "
        "Check whether the workspace is ready for a fresh agent session."
    )

    output = capsys.readouterr().out

    assert "Initialization-only request completed." in output
    assert "No implementation was attempted." in output
    assert "No source or test files were modified." in output
    assert "=== Implementation Phase ===" not in output
    assert "=== Planning ===" not in output
    assert "=== Generating code changes ===" not in output
    assert "=== Applying code changes ===" not in output


def test_startup_readiness_report_prints_evidence(capsys):
    report = {
        "files": [
            {
                "path": "workspace/AGENTS.md",
                "status": "FOUND/READ",
                "detail": "File exists and is readable.",
            }
        ],
        "directories": [
            {
                "path": "workspace/tests",
                "status": "FOUND",
            }
        ],
        "commands": [
            {
                "command": "pytest --version",
                "status": "PASS",
                "return_code": 0,
                "summary": "pytest 8.3.4",
            }
        ],
        "task_breakdown": [
            {
                "section": "## Current Active Task",
                "status": "FOUND",
            }
        ],
        "preflight_problems": [],
        "ready": True,
    }

    main.print_startup_readiness_report(report)
    output = capsys.readouterr().out

    assert "=== Startup Readiness Report ===" in output
    assert "Required Files:" in output
    assert "- workspace/AGENTS.md: FOUND/READ" in output
    assert "Required Directories:" in output
    assert "- workspace/tests: FOUND" in output
    assert "Validation Commands:" in output
    assert "- pytest --version: PASS (return code: 0)" in output
    assert "Task Visibility:" in output
    assert "- ## Current Active Task: FOUND" in output
    assert "Preflight:" in output
    assert "- PASS" in output
    assert "Final Decision:" in output
    assert "READY" in output


def test_first_task_prompt_does_not_resolve_to_startup_readiness():
    user_request = (
        "Implement the first task from task_breakdown.md. "
        "If no task is defined, create a simple calculator module "
        "with an add(a, b) function and tests."
    )

    resolved = main.resolve_user_task(user_request)

    assert "startup readiness" not in resolved.lower()
    assert "add" in resolved.lower()
    assert "calculator" in resolved.lower()


def test_implementation_request_rejects_no_change_plan():
    user_request = "Implement the first task from task_breakdown.md."

    plan = """
    ## Files To Change
    No files need to be created or modified for this startup readiness check.
    """

    assert main.is_implementation_request(user_request)
    assert main.plan_requires_no_file_changes(plan)


def test_repair_scope_rejects_harness_test_failure():
    validation_output = """
    E402 Module level import not at top of file
     --> tests/test_initialization_intent.py:8:1
    """

    allowed_files = ["src/calculator.py", "tests/test_calculator.py"]

    assert not main.is_failure_in_allowed_scope(validation_output, allowed_files)


def test_out_of_scope_harness_test_failure_rejected():
    validation_output = """
    E402 Module level import not at top of file
     --> tests/test_initialization_intent.py:8:1
    """

    allowed_files = ["src/calculator.py", "tests/test_calculator.py"]

    assert not main.failure_is_within_scope(validation_output, allowed_files)


def test_digital_engineer_cannot_modify_initialization_intent_test():
    llm_output = """
FILE: tests/test_initialization_intent.py
```python
import main
```
"""

    with pytest.raises(ValueError):
        apply_file_changes(llm_output)


def test_implementation_with_no_changed_files_fails_generation_gate():
    contract = main.TaskContract(
        task_type="calculator_add",
        required_files=["src/calculator.py", "tests/test_calculator.py"],
        allowed_files=["src/calculator.py", "tests/test_calculator.py"],
        validation_profile="calculator",
    )

    result = main.generation_satisfies_contract([], contract)

    assert not result.passed
    assert "no file changes" in result.reason.lower()


def test_missing_required_test_file_fails_generation_gate(monkeypatch):
    existing_files = {main.WORKSPACE_DIR / "src/calculator.py"}

    def fake_exists(path):
        return path in existing_files

    monkeypatch.setattr(Path, "exists", fake_exists)

    contract = main.TaskContract(
        task_type="calculator_add",
        required_files=["src/calculator.py", "tests/test_calculator.py"],
        allowed_files=["src/calculator.py", "tests/test_calculator.py"],
        validation_profile="calculator",
    )

    result = main.generation_satisfies_contract(["workspace/src/calculator.py"], contract)

    assert not result.passed
    assert result.missing_files == ["tests/test_calculator.py"]


def test_validator_reports_missing_required_file_before_pytest(monkeypatch):
    existing_files = {main.WORKSPACE_DIR / "src/calculator.py"}

    def fake_exists(path):
        return path in existing_files

    monkeypatch.setattr("harness.validator.Path.exists", fake_exists)

    result = run_validation(profile="calculator")

    assert not result.passed
    assert "required file missing before validation" in result.output.lower()
    assert "tests/test_calculator.py" in result.output


def test_preflight_repairs_fix_src_import_and_unused_pytest():
    test_file = main.WORKSPACE_DIR / "tests" / "test_preflight_repair_tmp.py"
    test_file.write_text(
        "import pytest\n"
        "from src.calculator import add\n\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )

    try:
        changed_files = apply_preflight_repairs(
            "workspace/tests/test_preflight_repair_tmp.py: uses `from src...` import.\n"
            "workspace/tests/test_preflight_repair_tmp.py: imports pytest but does not use pytest features."
        )

        updated = test_file.read_text(encoding="utf-8")

        assert str(test_file) in changed_files
        assert "import pytest" not in updated
        assert "from src.calculator import add" not in updated
        assert "from calculator import add" in updated
    finally:
        if test_file.exists():
            test_file.unlink()
