from pathlib import Path

WORKSPACE_DIR = Path("workspace")


def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def format_context_file(path: Path) -> str:
    content = read_file(path)

    if not content:
        return ""

    return f"""
# {path.as_posix()}
{content}
"""


def load_context() -> str:
    context_files = [
        WORKSPACE_DIR / "AGENTS.md",
        WORKSPACE_DIR / "harness_map.md",
        WORKSPACE_DIR / "docs" / "testing-standards.md",
        WORKSPACE_DIR / "docs" / "repair-rules-guide.md",
        WORKSPACE_DIR / "docs" / "state-management.md",
        WORKSPACE_DIR / "docs" / "session-handoff.md",
        WORKSPACE_DIR / "DECISIONS.md",
        WORKSPACE_DIR / "feature_list.json",
        WORKSPACE_DIR / "progress.md",
        WORKSPACE_DIR / "run_history.json",
        WORKSPACE_DIR / "failure_log.json",
    ]

    return "\n".join(format_context_file(path) for path in context_files)
