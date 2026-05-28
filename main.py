import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

from harness.context_loader import load_context
from harness.execution_manager import apply_file_changes
from harness.preflight import run_preflight_checks
from harness.prompts import (
    build_code_prompt,
    build_fix_prompt,
    build_generation_retry_prompt,
    build_plan_prompt,
)
from harness.repair_rules import (
    apply_basic_import_repairs,
    apply_preflight_repairs,
    apply_basic_pytest_repairs,
    apply_basic_ruff_repairs,
)
from harness.state_manager import (
    append_failure_log,
    append_progress,
    append_run_history,
    get_next_session_id,
    update_task_breakdown_after_failure,
    update_task_breakdown_after_success,
)
from harness.validator import run_validation


MAX_FIX_ATTEMPTS = 2
MAX_GENERATION_ATTEMPTS = 2
WORKSPACE_DIR = Path("workspace")
DEFAULT_IMPLEMENTATION_TASK = (
    "Create a simple calculator module with an add(a, b) function and tests."
)


@dataclass
class TaskContract:
    task_type: str
    required_files: list[str]
    allowed_files: list[str]
    validation_profile: str


@dataclass
class TaskReconciliation:
    latest_user_request: str
    task_breakdown_task: str
    resolved_task: str
    relationship: str
    decision: str


@dataclass
class GateResult:
    passed: bool
    reason: str
    missing_files: list[str] | None = None

REQUIRED_STARTUP_FILES = [
    WORKSPACE_DIR / "AGENTS.md",
    WORKSPACE_DIR / "harness_map.md",
    WORKSPACE_DIR / "progress.md",
    WORKSPACE_DIR / "feature_list.json",
    WORKSPACE_DIR / "run_history.json",
    WORKSPACE_DIR / "failure_log.json",
    WORKSPACE_DIR / "docs" / "debugging-policy.md",
    WORKSPACE_DIR / "docs" / "session-handoff.md",
    WORKSPACE_DIR / "docs" / "startup-readiness.md",
    WORKSPACE_DIR / "task_breakdown.md",
]

REQUIRED_STARTUP_DIRS = [
    WORKSPACE_DIR,
    WORKSPACE_DIR / "docs",
    WORKSPACE_DIR / "src",
    WORKSPACE_DIR / "tests",
]


def run_readiness_command(command: list[str]) -> dict:
    try:
        completed = subprocess.run(
            command,
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            shell=False,
        )
    except FileNotFoundError:
        return {
            "command": " ".join(command),
            "status": "FAIL",
            "return_code": None,
            "summary": f"Command not found: {command[0]}",
        }

    output = (completed.stdout or completed.stderr).strip()

    return {
        "command": " ".join(command),
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "return_code": completed.returncode,
        "summary": output.splitlines()[0] if output else "No output.",
    }


def check_required_files() -> list[dict]:
    results = []

    for path in REQUIRED_STARTUP_FILES:
        if not path.exists():
            results.append(
                {
                    "path": path.as_posix(),
                    "status": "MISSING",
                    "detail": "File does not exist.",
                }
            )
            continue

        try:
            path.read_text(encoding="utf-8")
            results.append(
                {
                    "path": path.as_posix(),
                    "status": "FOUND/READ",
                    "detail": "File exists and is readable.",
                }
            )
        except OSError as exc:
            results.append(
                {
                    "path": path.as_posix(),
                    "status": "UNREADABLE",
                    "detail": str(exc),
                }
            )

    return results


def check_required_directories() -> list[dict]:
    results = []

    for path in REQUIRED_STARTUP_DIRS:
        results.append(
            {
                "path": path.as_posix(),
                "status": "FOUND" if path.exists() and path.is_dir() else "MISSING",
            }
        )

    return results


def check_task_breakdown_visibility() -> list[dict]:
    task_breakdown_path = WORKSPACE_DIR / "task_breakdown.md"
    required_sections = [
        "## Initialization Status",
        "## Current Active Implementation Task",
        "## Acceptance Criteria",
        "## Subtasks",
        "## Validation Requirements",
        "## Next Step",
    ]

    if not task_breakdown_path.exists():
        return [
            {
                "section": "task_breakdown.md",
                "status": "MISSING",
                "detail": "workspace/task_breakdown.md does not exist.",
            }
        ]

    content = task_breakdown_path.read_text(encoding="utf-8")

    return [
        {
            "section": section,
            "status": "FOUND" if section in content else "MISSING",
        }
        for section in required_sections
    ]


def build_startup_readiness_report() -> dict:
    file_results = check_required_files()
    directory_results = check_required_directories()
    command_results = [
        run_readiness_command(["pytest", "--version"]),
        run_readiness_command(["ruff", "--version"]),
    ]
    task_results = check_task_breakdown_visibility()
    preflight_problems = run_preflight_checks()

    all_passed = (
        all(item["status"] == "FOUND/READ" for item in file_results)
        and all(item["status"] == "FOUND" for item in directory_results)
        and all(item["status"] == "PASS" for item in command_results)
        and all(item["status"] == "FOUND" for item in task_results)
        and not preflight_problems
    )

    return {
        "files": file_results,
        "directories": directory_results,
        "commands": command_results,
        "task_breakdown": task_results,
        "preflight_problems": preflight_problems,
        "ready": all_passed,
    }


def print_startup_readiness_report(report: dict) -> None:
    print("\n=== Startup Readiness Report ===")

    print("\nRequired Files:")
    for item in report["files"]:
        print(f"- {item['path']}: {item['status']}")
        print(f"  {item['detail']}")

    print("\nRequired Directories:")
    for item in report["directories"]:
        print(f"- {item['path']}: {item['status']}")

    print("\nValidation Commands:")
    for item in report["commands"]:
        print(
            f"- {item['command']}: {item['status']} "
            f"(return code: {item['return_code']})"
        )
        print(f"  {item['summary']}")

    print("\nTask Visibility:")
    for item in report["task_breakdown"]:
        print(f"- {item['section']}: {item['status']}")
        if "detail" in item:
            print(f"  {item['detail']}")

    print("\nPreflight:")
    if report["preflight_problems"]:
        print("- FAIL")
        for problem in report["preflight_problems"]:
            print(f"  - {problem}")
    else:
        print("- PASS")

    print("\nFinal Decision:")
    print("READY" if report["ready"] else "NOT READY")


def readiness_report_to_problems(report: dict) -> list[str]:
    if report["ready"]:
        return []

    problems = []

    for item in report["files"]:
        if item["status"] != "FOUND/READ":
            problems.append(f"Required file {item['path']}: {item['status']}")

    for item in report["directories"]:
        if item["status"] != "FOUND":
            problems.append(f"Required directory {item['path']}: {item['status']}")

    for item in report["commands"]:
        if item["status"] != "PASS":
            problems.append(
                f"Command {item['command']}: {item['status']} - {item['summary']}"
            )

    for item in report["task_breakdown"]:
        if item["status"] != "FOUND":
            problems.append(f"Task visibility {item['section']}: {item['status']}")

    for problem in report["preflight_problems"]:
        problems.append(f"Preflight: {problem}")

    if not problems:
        problems.append("Startup readiness failed. See report above.")

    return problems


def initialize_session() -> tuple[str, list[str]]:
    print("\n=== Initialization Phase ===")
    context = load_context(mode="initialization")

    print("\n=== Running startup readiness checks ===")
    report = build_startup_readiness_report()
    print_startup_readiness_report(report)
    problems = readiness_report_to_problems(report)

    return context, problems


def clock_in() -> str:
    context, _problems = initialize_session()
    return context


def run_initialization_only() -> None:
    initialize_session()


def is_initialization_only_request(user_request: str) -> bool:
    request = user_request.lower()

    initialization_phrases = [
        "startup readiness only",
        "initialization only",
        "run initialization only",
        "run startup readiness",
        "check startup readiness",
        "readiness only",
        "do not implement",
        "do not build",
        "do not modify",
        "no feature",
    ]

    return any(phrase in request for phrase in initialization_phrases)


def is_implementation_request(user_request: str) -> bool:
    request = user_request.lower()
    implementation_phrases = [
        "implement",
        "create",
        "add",
        "build",
        "first task",
    ]

    return any(phrase in request for phrase in implementation_phrases)


def read_active_task_from_task_breakdown() -> str:
    task_path = WORKSPACE_DIR / "task_breakdown.md"
    if not task_path.exists():
        return ""

    content = task_path.read_text(encoding="utf-8")

    marker = "## Current Active Implementation Task"
    if marker not in content:
        return ""

    after_marker = content.split(marker, 1)[1].strip()
    task_lines = []

    for line in after_marker.splitlines():
        if line.startswith("## "):
            break
        if line.strip():
            task_lines.append(line.strip())

    resolved = " ".join(task_lines).strip()

    if not resolved or "startup readiness" in resolved.lower():
        return ""

    return resolved


def request_uses_task_breakdown_as_source(user_request: str) -> bool:
    request = user_request.lower()
    return (
        "first task from task_breakdown" in request
        or "current task from task_breakdown" in request
        or "active task from task_breakdown" in request
    )


def classify_task_relationship(user_request: str, task_breakdown_task: str) -> str:
    if not task_breakdown_task:
        return "new"

    user_text = user_request.lower()
    task_text = task_breakdown_task.lower()

    if user_text.strip() == task_text.strip():
        return "same"

    if request_uses_task_breakdown_as_source(user_request):
        return "same"

    calculator_terms = [
        "calculator",
        "add",
        "subtract",
        "multiply",
        "division",
        "divide",
    ]
    user_mentions_calculator = any(term in user_text for term in calculator_terms)
    task_mentions_calculator = any(term in task_text for term in calculator_terms)

    if user_mentions_calculator and task_mentions_calculator:
        return "extension"

    return "replacement"


def reconcile_user_task(user_request: str) -> TaskReconciliation:
    task_breakdown_task = read_active_task_from_task_breakdown()

    if request_uses_task_breakdown_as_source(user_request):
        resolved_task = task_breakdown_task or DEFAULT_IMPLEMENTATION_TASK
        relationship = "same"
        decision = (
            "The latest user request explicitly asked to use task_breakdown.md, "
            "so the active task from that file is the implementation task."
        )
    else:
        resolved_task = user_request
        relationship = classify_task_relationship(user_request, task_breakdown_task)
        decision = (
            "The latest user request is the highest-priority source of truth. "
            "Workspace task files are context only and must not override it."
        )

    return TaskReconciliation(
        latest_user_request=user_request,
        task_breakdown_task=task_breakdown_task or "(none found)",
        resolved_task=resolved_task,
        relationship=relationship,
        decision=decision,
    )


def resolve_user_task(user_request: str) -> str:
    return reconcile_user_task(user_request).resolved_task


def describe_file_state(files: list[str]) -> str:
    if not files:
        return "- No task-specific required files were inferred."

    lines = []
    for file in files:
        path = WORKSPACE_DIR / file
        action = "modify or extend" if path.exists() else "create"
        state = "exists" if path.exists() else "missing"
        lines.append(f"- {file}: {state}; planner should {action}.")

    return "\n".join(lines)


def build_task_control_context(
    reconciliation: TaskReconciliation,
    contract: TaskContract,
) -> str:
    return f"""
# Task Reconciliation
- Latest user request: {reconciliation.latest_user_request}
- task_breakdown.md active task: {reconciliation.task_breakdown_task}
- Relationship: {reconciliation.relationship}
- Decision: {reconciliation.decision}
- Resolved implementation task: {reconciliation.resolved_task}

# File State Inspection
{describe_file_state(contract.required_files)}
"""


def plan_requires_no_file_changes(plan: str) -> bool:
    text = plan.lower()
    no_change_phrases = [
        "no files need to be created",
        "no files need to be modified",
        "no files need to change",
        "files changed\n\n- none",
        "files to change\nno files",
    ]

    return any(phrase in text for phrase in no_change_phrases)


def build_allowed_scope(resolved_task: str) -> list[str]:
    return build_task_contract(resolved_task).allowed_files


def build_task_contract(resolved_task: str) -> TaskContract:
    task = resolved_task.lower()

    calculator_terms = [
        "calculator",
        "add(a, b)",
        "subtract",
        "multiply",
        "division",
        "divide",
    ]

    if any(term in task for term in calculator_terms):
        return TaskContract(
            task_type="calculator",
            required_files=["src/calculator.py", "tests/test_calculator.py"],
            allowed_files=["src/calculator.py", "tests/test_calculator.py"],
            validation_profile="calculator",
        )

    return TaskContract(
        task_type="generic",
        required_files=[],
        allowed_files=[],
        validation_profile="implementation",
    )


def required_files_exist(required_files: list[str]) -> tuple[bool, list[str]]:
    missing = []

    for file in required_files:
        if not (WORKSPACE_DIR / file).exists():
            missing.append(file)

    return len(missing) == 0, missing


def generation_satisfies_contract(
    changed_files: list[str],
    contract: TaskContract,
) -> GateResult:
    if not changed_files:
        return GateResult(
            passed=False,
            reason=(
                "Implementation request produced no file changes. "
                f"Expected required files: {', '.join(contract.required_files)}."
            ),
            missing_files=contract.required_files,
        )

    files_exist, missing_files = required_files_exist(contract.required_files)
    if not files_exist:
        return GateResult(
            passed=False,
            reason=f"Missing required files: {missing_files}",
            missing_files=missing_files,
        )

    return GateResult(passed=True, reason="Generation satisfied task contract.")


def extract_failure_files(validation_output: str) -> list[str]:
    files = []

    for line in validation_output.splitlines():
        normalized = line.replace("\\", "/")
        stripped = normalized.strip()

        if "-->" in stripped:
            file_part = stripped.split("-->", 1)[1].strip().split(":", 1)[0]
            files.append(file_part)

        if "ERROR collecting" in stripped:
            file_part = stripped.split("ERROR collecting", 1)[1].strip()
            if file_part:
                files.append(file_part.split()[0])

        if "file or directory not found:" in stripped.lower():
            file_part = stripped.split(":", 1)[1].strip()
            if file_part:
                files.append(file_part.split()[0])

    return list(dict.fromkeys(files))


def failure_is_within_scope(validation_output: str, allowed_files: list[str]) -> bool:
    failure_files = extract_failure_files(validation_output)

    if not failure_files:
        return True

    return all(file in allowed_files for file in failure_files)


def is_failure_in_allowed_scope(validation_output: str, allowed_files: list[str]) -> bool:
    return failure_is_within_scope(validation_output, allowed_files)


def classify_validation_failure(validation_output: str) -> str:
    normalized_output = validation_output.replace("\\", "/").lower()

    if "file or directory not found" in normalized_output:
        return "missing_required_file"

    if "modulenotfounderror" in normalized_output:
        return "import_error"

    if "i001" in normalized_output or "e402" in normalized_output or "f401" in normalized_output:
        return "lint_failure"

    if "assert" in normalized_output or "failed" in normalized_output:
        return "test_failure"

    if "src/calculator.py" in normalized_output:
        return "product implementation bug"

    if "tests/test_calculator.py" in normalized_output:
        return "product test bug"

    if "tests/test_initialization_intent.py" in normalized_output:
        return "harness test bug"

    if "main.py" in normalized_output:
        return "harness controller bug"

    if "harness/" in normalized_output:
        return "harness infrastructure bug"

    if "docs/" in normalized_output or ".md" in normalized_output:
        return "documentation/state issue"

    return "unknown validation failure"


def command_passed(validation_output: str, command: str) -> bool:
    return f"Command: {command}\nReturn code: 0" in validation_output


def validation_summary(validation_output: str, preflight_passed: bool) -> str:
    pytest_result = "pass" if command_passed(validation_output, "pytest") else "fail"
    ruff_result = "pass" if command_passed(validation_output, "ruff check .") else "fail"
    preflight_result = "pass" if preflight_passed else "fail"

    return f"- Pytest: {pytest_result}\n- Ruff: {ruff_result}\n- Preflight: {preflight_result}"


def unique_files(files: list[str]) -> list[str]:
    unique = []

    for file in files:
        if file not in unique:
            unique.append(file)

    return unique


def log_repaired_failure(
    session_id: str,
    user_request: str,
    failure_layer: str,
    tool: str,
    error_summary: str,
    repair_rule_used: str,
    repair_successful: bool,
) -> None:
    append_failure_log(
        user_request=user_request,
        failure_layer=failure_layer,
        tool=tool,
        error_summary=error_summary[:500],
        repair_rule_used=repair_rule_used,
        repair_successful=repair_successful,
        session_id=session_id,
    )


def clock_out_success(
    session_id: str,
    user_request: str,
    plan: str,
    changed_files: list[str],
    validation_output: str,
    repair_attempts: int,
    failures_encountered: list[str],
) -> None:
    print("\n=== Clock Out: Success ===")

    changed_files = unique_files(changed_files)

    append_progress(
        user_request=user_request,
        plan=plan,
        changed_files=changed_files,
        validation_output=validation_output,
        validation_result=validation_summary(validation_output, preflight_passed=True),
        failures_encountered=failures_encountered,
        final_status="Success",
        next_step="Continue with the next requested feature or repair task.",
    )

    append_run_history(
        user_request=user_request,
        pytest_passed=True,
        ruff_passed=True,
        repair_attempts=repair_attempts,
        changed_files=changed_files,
        final_status="success",
        session_id=session_id,
    )

    completed_subtasks = [
        f"Implemented the requested task: {user_request}",
        "Ran preflight before implementation.",
        "Ran pytest and Ruff validation successfully.",
    ]
    if changed_files:
        completed_subtasks.append(
            "Updated files: " + ", ".join(changed_files)
        )

    update_task_breakdown_after_success(
        user_request=user_request,
        completed_subtasks=completed_subtasks,
        next_step="Continue with the next incomplete task from this breakdown.",
    )


def clock_out_failure(
    session_id: str,
    user_request: str,
    failure_layer: str,
    tool: str,
    error_summary: str,
    repair_rule_used: str | None,
    changed_files: list[str],
    repair_attempts: int,
) -> None:
    print("\n=== Clock Out: Failure ===")

    append_failure_log(
        user_request=user_request,
        failure_layer=failure_layer,
        tool=tool,
        error_summary=error_summary[:500],
        repair_rule_used=repair_rule_used,
        repair_successful=False,
        session_id=session_id,
    )

    append_run_history(
        user_request=user_request,
        pytest_passed=False,
        ruff_passed=False,
        repair_attempts=repair_attempts,
        changed_files=unique_files(changed_files),
        final_status="failed",
        session_id=session_id,
    )

    update_task_breakdown_after_failure(
        user_request=user_request,
        failure_layer=failure_layer,
        tool=tool,
        error_summary=error_summary,
        next_step="Resolve the blocker above, then rerun initialization and validation.",
    )


def run_harness(user_request: str) -> None:
    session_id = get_next_session_id()
    repair_attempt_count = 0
    failures_encountered = []
    initialization_only = is_initialization_only_request(user_request)
    implementation_request = is_implementation_request(user_request)

    context, startup_problems = initialize_session()
    if initialization_only:
        print("\n=== Final Result ===")
        if startup_problems:
            print("Startup readiness failed.")
        else:
            print("Startup readiness passed.")
        print("Initialization-only request completed.")
        print("No implementation was attempted.")
        print("No source or test files were modified.")
        return

    if startup_problems:
        clock_out_failure(
            session_id=session_id,
            user_request=user_request,
            failure_layer="initialization",
            tool="startup_readiness",
            error_summary="\n".join(startup_problems),
            repair_rule_used=None,
            changed_files=[],
            repair_attempts=0,
        )
        return

    reconciliation = reconcile_user_task(user_request)
    resolved_task = reconciliation.resolved_task
    contract = build_task_contract(resolved_task)
    allowed_files = contract.allowed_files
    context = (
        build_task_control_context(reconciliation, contract)
        + load_context(mode="implementation")
    )

    from harness.llm_service import call_llm

    print("\n=== Implementation Phase ===")
    print("\n=== Task Reconciliation ===")
    print(f"Latest user request: {reconciliation.latest_user_request}")
    print(f"task_breakdown.md active task: {reconciliation.task_breakdown_task}")
    print(f"Relationship: {reconciliation.relationship}")
    print(f"Decision: {reconciliation.decision}")
    print(f"Resolved implementation task: {resolved_task}")

    print("\n=== Planning ===")
    plan_prompt = build_plan_prompt(
        user_request=user_request,
        resolved_task=resolved_task,
        context=context,
    )
    plan = call_llm(plan_prompt)
    print(plan)

    if implementation_request and plan_requires_no_file_changes(plan):
        clock_out_failure(
            session_id=session_id,
            user_request=user_request,
            failure_layer="task_specification",
            tool="plan_acceptance_gate",
            error_summary=(
                "Implementation request produced a no-change readiness plan. "
                "Refusing to enter code generation."
            ),
            repair_rule_used=None,
            changed_files=[],
            repair_attempts=0,
        )
        return

    print("\n=== Generating code changes ===")
    code_prompt = build_code_prompt(
        user_request=user_request,
        resolved_task=resolved_task,
        context=context,
        plan=plan,
        required_files=contract.required_files,
    )

    print("\n=== Applying code changes ===")
    changed_files = []
    generation_error = ""
    code_output = ""

    for generation_attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        code_output = call_llm(code_prompt)

        try:
            changed_files = apply_file_changes(code_output)
        except ValueError as error:
            generation_error = str(error)
            changed_files = []

        generation_result = generation_satisfies_contract(changed_files, contract)
        if generation_result.passed:
            break

        generation_error = generation_result.reason
        if generation_attempt < MAX_GENERATION_ATTEMPTS:
            print("\n=== Generation retry ===")
            print(generation_error)
            code_prompt = build_generation_retry_prompt(
                user_request=user_request,
                resolved_task=resolved_task,
                required_files=contract.required_files,
                previous_output=code_output,
            )

    if not changed_files:
        clock_out_failure(
            session_id=session_id,
            user_request=user_request,
            failure_layer="generation",
            tool="llm_code_generation",
            error_summary=(
                generation_error
                or "LLM produced no valid FILE blocks after retry."
            ),
            repair_rule_used="generation_retry_prompt",
            changed_files=[],
            repair_attempts=0,
        )
        return

    generation_result = generation_satisfies_contract(changed_files, contract)
    if not generation_result.passed:
        clock_out_failure(
            session_id=session_id,
            user_request=user_request,
            failure_layer="generation",
            tool="code_output_acceptance_gate",
            error_summary=generation_result.reason,
            repair_rule_used=None,
            changed_files=changed_files,
            repair_attempts=0,
        )
        return

    print("Changed files:")
    for file in changed_files:
        print(f"- {file}")

    problems = run_preflight_checks()
    if problems:
        print("\n=== Preflight problems found ===")
        for problem in problems:
            print(f"- {problem}")

        problem_summary = "\n".join(problems)
        repaired_files = apply_preflight_repairs("\n".join(problems))

        if repaired_files:
            repair_attempt_count += 1
            changed_files.extend(repaired_files)

            print("\n=== Applied preflight repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            problems = run_preflight_checks()
            repair_successful = not problems
            if repair_successful:
                failures_encountered.append(
                    "Preflight failed and preflight repair rules fixed it."
                )
            else:
                failures_encountered.append(
                    "Preflight failed after preflight repair rules changed files."
                )
            log_repaired_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="preflight",
                tool="preflight",
                error_summary=problem_summary,
                repair_rule_used="apply_preflight_repairs",
                repair_successful=repair_successful,
            )

        if not problems:
            print("\nPreflight passed after repair.")
        else:
            print("\nStopping before validation because the workspace layout is invalid.")
            clock_out_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="preflight",
                tool="preflight",
                error_summary="Workspace layout is invalid.",
                repair_rule_used="apply_preflight_repairs",
                changed_files=changed_files,
                repair_attempts=repair_attempt_count,
            )
            return

    print("\n=== Running validation ===")
    validation = run_validation(profile=contract.validation_profile)
    print(validation.output)

    if not validation.passed:
        if allowed_files and not is_failure_in_allowed_scope(validation.output, allowed_files):
            failure_classification = classify_validation_failure(validation.output)
            clock_out_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="validation_scope",
                tool="scope_guard",
                error_summary=(
                    "Validation failed in a file outside the task scope. "
                    "Refusing LLM repair to avoid damaging harness tests. "
                    f"Classification: {failure_classification}"
                ),
                repair_rule_used=None,
                changed_files=changed_files,
                repair_attempts=repair_attempt_count,
            )
            return

        failed_output = validation.output
        repaired_files = apply_basic_ruff_repairs(validation.output)

        if repaired_files:
            repair_attempt_count += 1
            changed_files.extend(repaired_files)

            print("\n=== Applied basic Ruff repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            validation = run_validation(profile=contract.validation_profile)
            print(validation.output)
            repair_successful = validation.passed
            if repair_successful:
                failures_encountered.append("Ruff failed and basic Ruff repair rules fixed it.")
            else:
                failures_encountered.append(
                    "Ruff failed after basic Ruff repair rules changed files."
                )
            log_repaired_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="feedback",
                tool="ruff",
                error_summary=failed_output,
                repair_rule_used="apply_basic_ruff_repairs",
                repair_successful=repair_successful,
            )

    if not validation.passed:
        if allowed_files and not is_failure_in_allowed_scope(validation.output, allowed_files):
            failure_classification = classify_validation_failure(validation.output)
            clock_out_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="validation_scope",
                tool="scope_guard",
                error_summary=(
                    "Validation failed in a file outside the task scope. "
                    "Refusing LLM repair to avoid damaging harness tests. "
                    f"Classification: {failure_classification}"
                ),
                repair_rule_used=None,
                changed_files=changed_files,
                repair_attempts=repair_attempt_count,
            )
            return

        failed_output = validation.output
        repaired_files = apply_basic_pytest_repairs(validation.output)

        if repaired_files:
            repair_attempt_count += 1
            changed_files.extend(repaired_files)

            print("\n=== Applied pytest repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            validation = run_validation(profile=contract.validation_profile)
            print(validation.output)
            repair_successful = validation.passed
            if repair_successful:
                failures_encountered.append("Pytest failed and basic pytest repair rules fixed it.")
            else:
                failures_encountered.append(
                    "Pytest failed after basic pytest repair rules changed files."
                )
            log_repaired_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="feedback",
                tool="pytest",
                error_summary=failed_output,
                repair_rule_used="apply_basic_pytest_repairs",
                repair_successful=repair_successful,
            )

    fix_attempts = 0

    previous_validation_output = validation.output

    while not validation.passed and fix_attempts < MAX_FIX_ATTEMPTS:
        fix_attempts += 1

        print(f"\n=== Fix attempt {fix_attempts} ===")
        context = (
            build_task_control_context(reconciliation, contract)
            + load_context(mode="implementation")
        )

        fix_prompt = build_fix_prompt(
            user_request=user_request,
            resolved_task=resolved_task,
            context=context,
            validation_output=validation.output,
        )

        fix_output = call_llm(fix_prompt)

        try:
            fixed_files = apply_file_changes(fix_output)
        except ValueError as error:
            clock_out_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="execution",
                tool="apply_file_changes",
                error_summary=str(error),
                repair_rule_used="llm_fix_prompt",
                changed_files=changed_files,
                repair_attempts=repair_attempt_count + fix_attempts,
            )
            return
        changed_files.extend(fixed_files)

        print("Fixed files:")
        for file in fixed_files:
            print(f"- {file}")

        print("\n=== Running validation again ===")
        failed_output = validation.output
        validation = run_validation(profile=contract.validation_profile)
        print(validation.output)

        if not validation.passed and allowed_files:
            if not is_failure_in_allowed_scope(validation.output, allowed_files):
                failure_classification = classify_validation_failure(validation.output)
                clock_out_failure(
                    session_id=session_id,
                    user_request=user_request,
                    failure_layer="validation_scope",
                    tool="scope_guard",
                    error_summary=(
                        "Validation failed in a file outside the task scope. "
                        "Refusing LLM repair to avoid damaging harness tests. "
                        f"Classification: {failure_classification}"
                    ),
                    repair_rule_used=None,
                    changed_files=changed_files,
                    repair_attempts=repair_attempt_count + fix_attempts,
                )
                return

        if fixed_files:
            repair_success = validation.passed
            failures_encountered.append(
                "Validation failed and an LLM fix prompt changed files."
            )
            append_failure_log(
                user_request=user_request,
                failure_layer="feedback",
                tool="pytest_or_ruff",
                error_summary=failed_output[:500],
                repair_rule_used="llm_fix_prompt",
                repair_successful=repair_success,
                session_id=session_id,
            )

        problems = run_preflight_checks()
        if problems:
            print("\n=== Preflight problems found ===")
            for problem in problems:
                print(f"- {problem}")

            problem_summary = "\n".join(problems)
            repaired_files = apply_preflight_repairs("\n".join(problems))

            if repaired_files:
                repair_attempt_count += 1
                changed_files.extend(repaired_files)

                print("\n=== Applied preflight repair rules ===")
                for file in repaired_files:
                    print(f"- {file}")

                problems = run_preflight_checks()
                repair_successful = not problems
                if repair_successful:
                    failures_encountered.append(
                        "Preflight failed and preflight repair rules fixed it."
                    )
                else:
                    failures_encountered.append(
                        "Preflight failed after preflight repair rules changed files."
                    )
                log_repaired_failure(
                    session_id=session_id,
                    user_request=user_request,
                    failure_layer="preflight",
                    tool="preflight",
                    error_summary=problem_summary,
                    repair_rule_used="apply_preflight_repairs",
                    repair_successful=repair_successful,
                )

            if problems:
                print("\nStopping because the workspace layout is invalid.")
                clock_out_failure(
                    session_id=session_id,
                    user_request=user_request,
                    failure_layer="preflight",
                    tool="preflight",
                    error_summary="Workspace layout is invalid after repair.",
                    repair_rule_used="apply_preflight_repairs",
                    changed_files=changed_files,
                    repair_attempts=repair_attempt_count + fix_attempts,
                )
                return

            print("\nPreflight passed after repair.")

        if not validation.passed and validation.output == previous_validation_output:
            print("\nSame validation error repeated. Stopping early.")
            break

        previous_validation_output = validation.output

    if not validation.passed:
        failed_output = validation.output
        repaired_files = apply_basic_import_repairs(validation.output)

        if repaired_files:
            repair_attempt_count += 1
            changed_files.extend(repaired_files)

            print("\n=== Applied basic repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            validation = run_validation(profile=contract.validation_profile)
            print(validation.output)
            repair_successful = validation.passed
            if repair_successful:
                failures_encountered.append(
                    "Import failure was fixed by basic import repair rules."
                )
            else:
                failures_encountered.append(
                    "Import failure remained after basic import repair rules changed files."
                )
            log_repaired_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="feedback",
                tool="pytest",
                error_summary=failed_output,
                repair_rule_used="apply_basic_import_repairs",
                repair_successful=repair_successful,
            )

    if not validation.passed:
        print("\n=== Final Result ===")
        print("Validation failed after fix attempts.")
        clock_out_failure(
            session_id=session_id,
            user_request=user_request,
            failure_layer="feedback",
            tool="pytest_or_ruff",
            error_summary=validation.output[:500],
            repair_rule_used="llm_fix_prompt",
            changed_files=changed_files,
            repair_attempts=repair_attempt_count + fix_attempts,
        )
        return

    clock_out_success(
        session_id=session_id,
        user_request=user_request,
        plan=plan,
        changed_files=changed_files,
        validation_output=validation.output,
        repair_attempts=repair_attempt_count + fix_attempts,
        failures_encountered=failures_encountered,
    )

    print("\n=== Final Result ===")
    print("Task completed successfully.")
    print("Validation passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Harness MVP.")
    parser.add_argument(
        "--init",
        action="store_true",
        help="Run startup readiness checks without generating code.",
    )
    args = parser.parse_args()

    if args.init:
        run_initialization_only()
    else:
        request = input("What should the harness do? ")
        run_harness(request)
