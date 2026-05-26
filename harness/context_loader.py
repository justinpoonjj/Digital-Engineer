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


def load_context(mode: str = "implementation") -> str:
    if mode == "initialization":
        context_files = [
            WORKSPACE_DIR / "AGENTS.md",
            WORKSPACE_DIR / "harness_map.md",
            WORKSPACE_DIR / "docs" / "startup-readiness.md",
            WORKSPACE_DIR / "task_breakdown.md",
            WORKSPACE_DIR / "progress.md",
        ]
    elif mode == "implementation":
        context_files = [
            WORKSPACE_DIR / "AGENTS.md",
            WORKSPACE_DIR / "harness_map.md",
            WORKSPACE_DIR / "docs" / "testing-standards.md",
            WORKSPACE_DIR / "docs" / "repair-rules-guide.md",
            WORKSPACE_DIR / "docs" / "debugging-policy.md",
            WORKSPACE_DIR / "task_breakdown.md",
            WORKSPACE_DIR / "feature_list.json",
        ]
    else:
        raise ValueError(f"Unknown context mode: {mode}")

    return "\n".join(format_context_file(path) for path in context_files)
