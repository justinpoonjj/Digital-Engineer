import json
from datetime import datetime
from pathlib import Path


WORKSPACE_DIR = Path("workspace")


def append_progress(
    user_request: str,
    plan: str,
    changed_files: list[str],
    validation_output: str,
) -> None:
    progress_path = WORKSPACE_DIR / "progress.md"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    changed_files_text = "\n".join(f"- {file}" for file in changed_files)

    entry = f"""

## {timestamp}

### User Request

{user_request}

### Plan

{plan}

### Changed Files

{changed_files_text}

### Validation

```text
{validation_output}

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


def append_run_history(
    user_request: str,
    pytest_passed: bool,
    ruff_passed: bool,
    repair_attempts: int,
    modified_unrelated_files: bool = False,
    tests_deleted: bool = False,
) -> None:
    history_path = WORKSPACE_DIR / "run_history.json"
    history = read_json_list(history_path)

    entry = {
        "task_id": f"task_{len(history) + 1:03}",
        "task": user_request,
        "mode": "harness_supported",
        "pytest_passed": pytest_passed,
        "ruff_passed": ruff_passed,
        "repair_attempts": repair_attempts,
        "modified_unrelated_files": modified_unrelated_files,
        "tests_deleted": tests_deleted,
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
) -> None:
    failure_path = WORKSPACE_DIR / "failure_log.json"
    failures = read_json_list(failure_path)

    failures.append(
        {
            "task": user_request,
            "failure_layer": failure_layer,
            "tool": tool,
            "error_summary": error_summary,
            "repair_rule_used": repair_rule_used,
            "repair_successful": repair_successful,
        }
    )

    write_json_list(failure_path, failures)
