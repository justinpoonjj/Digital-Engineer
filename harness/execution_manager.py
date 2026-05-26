import re
from pathlib import Path

WORKSPACE_DIR = Path("workspace")
PROTECTED_FILES = {"AGENTS.md", "feature_list.json", "progress.md", "task_breakdown.md"}
PROTECTED_PATH_PREFIXES = {
    "tests/test_initialization_intent.py",
    "tests/test_continuity_artifacts.py",
}

FILE_BLOCK_PATTERN = re.compile(
    r"FILE:\s*(?P<path>[^\n]+)\n```(?:python|json|markdown|toml|text)?\n(?P<content>.*?)```",
    re.DOTALL,
)


def is_safe_path(path: Path) -> bool:
    try:
        path.resolve().relative_to(WORKSPACE_DIR.resolve())
        return True
    except ValueError:
        return False


def normalize_relative_path(relative_path: str) -> str:
    cleaned = relative_path.strip().replace("\\", "/")

    if cleaned == "workspace":
        raise ValueError("Invalid path: cannot write to nested workspace directory.")

    if cleaned.startswith("workspace/"):
        raise ValueError(
            f"Invalid path `{relative_path}`. "
            "Paths must be relative to the workspace root. "
            "Use `src/...` or `tests/...`, not `workspace/src/...`."
        )

    if cleaned in PROTECTED_FILES:
        raise ValueError(
            f"Protected workspace file rejected: {relative_path}. "
            "The harness controls AGENTS.md, feature_list.json, progress.md, "
            "and task_breakdown.md."
        )

    if cleaned in PROTECTED_PATH_PREFIXES:
        raise ValueError(
            f"Protected harness test rejected: {relative_path}. "
            "The Digital Engineer may not modify harness/controller tests."
        )

    return cleaned


def extract_file_changes(llm_output: str) -> list[tuple[str, str]]:
    changes = []

    for match in FILE_BLOCK_PATTERN.finditer(llm_output):
        relative_path = match.group("path").strip()
        content = match.group("content").strip() + "\n"
        changes.append((relative_path, content))

    return changes


def apply_file_changes(llm_output: str) -> list[str]:
    if llm_output.strip() == "NO_FILE_CHANGES":
        return []

    changes = extract_file_changes(llm_output)

    if not changes:
        raise ValueError("No valid file changes found in LLM output")

    changed_files = []

    for relative_path, content in changes:
        relative_path = normalize_relative_path(relative_path)
        target_path = WORKSPACE_DIR / relative_path

        if not is_safe_path(target_path):
            raise ValueError(f"Unsafe file path rejected: {relative_path}")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        changed_files.append(str(target_path))

    return changed_files
