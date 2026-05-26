import json
from datetime import datetime
from pathlib import Path


WORKSPACE_DIR = Path("workspace")


def append_progress(
    user_request: str,
    plan: str,
    changed_files: list[str],
    validation_output: str,
    task_interpretation: str | None = None,
    relevant_previous_state: str | None = None,
    validation_result: str | None = None,
    failures_encountered: list[str] | None = None,
    final_status: str = "Success",
    next_step: str = "Continue with the next requested feature or repair task.",
) -> None:
    progress_path = WORKSPACE_DIR / "progress.md"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    changed_files_text = "\n".join(f"- {file}" for file in changed_files)
    if not changed_files_text:
        changed_files_text = "- None"

    failures_text = "\n".join(f"- {failure}" for failure in failures_encountered or [])
    if not failures_text:
        failures_text = "- None recorded."

    task_interpretation = task_interpretation or user_request
    relevant_previous_state = (
        relevant_previous_state
        or "Loaded durable context files during clock-in and used only task-relevant state."
    )
    validation_result = validation_result or "- See validation output below."

    entry = f"""

## {timestamp}

### Current User Request

{user_request}

### Task Interpretation

{task_interpretation}

### Relevant Previous State

{relevant_previous_state}

### Plan

{plan}

### Files Changed

{changed_files_text}

### Validation Result

{validation_result}

```text
{validation_output}
```

### Failures Encountered

{failures_text}

### Final Status

{final_status}

### Next Step

{next_step}

"""
    with progress_path.open("a", encoding="utf-8") as file:
        file.write(entry)


def read_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8").strip()

    if not content:
        return []

    data = json.loads(content)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list in {path}")

    return data


def write_json_list(path: Path, entries: list[dict]) -> None:
    path.write_text(
        json.dumps(entries, indent=2) + "\n",
        encoding="utf-8",
    )


def get_next_session_id() -> str:
    history_path = WORKSPACE_DIR / "run_history.json"
    history = read_json_list(history_path)
    return f"session_{len(history) + 1:03}"


def append_run_history(
    user_request: str,
    pytest_passed: bool,
    ruff_passed: bool,
    repair_attempts: int,
    changed_files: list[str],
    final_status: str,
    session_id: str | None = None,
    modified_unrelated_files: bool = False,
    tests_deleted: bool = False,
) -> None:
    history_path = WORKSPACE_DIR / "run_history.json"
    history = read_json_list(history_path)

    entry = {
        "session_id": session_id or f"session_{len(history) + 1:03}",
        "task_id": f"task_{len(history) + 1:03}",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "task": user_request,
        "mode": "harness_supported",
        "pytest_passed": pytest_passed,
        "ruff_passed": ruff_passed,
        "repair_attempts": repair_attempts,
        "changed_files": changed_files,
        "modified_unrelated_files": modified_unrelated_files,
        "tests_deleted": tests_deleted,
        "final_status": final_status,
    }

    history.append(entry)
    write_json_list(history_path, history)


def append_failure_log(
    user_request: str,
    failure_layer: str,
    tool: str,
    error_summary: str,
    repair_rule_used: str | None,
    repair_successful: bool,
    session_id: str | None = None,
) -> None:
    failure_path = WORKSPACE_DIR / "failure_log.json"
    failures = read_json_list(failure_path)

    failures.append(
        {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "task": user_request,
            "failure_layer": failure_layer,
            "tool": tool,
            "error_summary": error_summary,
            "repair_rule_used": repair_rule_used,
            "repair_successful": repair_successful,
        }
    )

    write_json_list(failure_path, failures)


def format_list_items(items: list[str]) -> str:
    if not items:
        return "- None recorded."

    return "\n".join(f"- {item}" for item in items)


def update_task_breakdown_after_success(
    user_request: str,
    completed_subtasks: list[str],
    next_step: str,
) -> None:
    task_breakdown_path = WORKSPACE_DIR / "task_breakdown.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    completed_subtasks_text = format_list_items(completed_subtasks)

    entry = f"""

## Controller Status Update - {timestamp}

### Result

Validation passed. The harness controller approved this task status update.

### Task

{user_request}

### Completed Subtasks

{completed_subtasks_text}

### Validation Requirements

- [x] Preflight passes
- [x] Pytest passes
- [x] Ruff passes
- [x] Existing tests preserved

### Next Step

{next_step}

"""
    with task_breakdown_path.open("a", encoding="utf-8") as file:
        file.write(entry)


def update_task_breakdown_after_failure(
    user_request: str,
    failure_layer: str,
    tool: str,
    error_summary: str,
    next_step: str,
) -> None:
    task_breakdown_path = WORKSPACE_DIR / "task_breakdown.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entry = f"""

## Blocked / Failed Attempt - {timestamp}

### Result

Validation did not pass. No subtasks were marked complete.

### Task

{user_request}

### Failure

- Layer: {failure_layer}
- Tool: {tool}

```text
{error_summary[:500]}
```

### Next Step

{next_step}

"""
    with task_breakdown_path.open("a", encoding="utf-8") as file:
        file.write(entry)
