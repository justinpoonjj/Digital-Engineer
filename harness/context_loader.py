from pathlib import Path

WORKSPACE_DIR = Path("workspace")

def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

def load_context() -> str: 
    agents = read_file(WORKSPACE_DIR / "AGENTS.md")
    feature_list = read_file(WORKSPACE_DIR / "feature_list.json")
    progress = read_file(WORKSPACE_DIR / "progress.md")

    return f"""
# AGENTS.md
{agents}

# feature_list.json

{feature_list}

#progress.md

{progress}
"""