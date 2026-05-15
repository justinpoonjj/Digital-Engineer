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
    with progress_path.open("a",encoding="utf-8") as file:
        file.write(entry)