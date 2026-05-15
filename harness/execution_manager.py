import re
from pathlib import Path

WORKSPACE_DIR = Path("workspace")

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
    
def extract_file_changes(llm_output: str) -> list[tuple[str,str]]:
    changes = []

    for match in FILE_BLOCK_PATTERN.finditer(llm_output):
        relative_path = match.group("path").strip()
        content = match.group("content").strip() + "\n"
        changes.append((relative_path, content))
    
    return changes

def apply_file_changes(llm_output: str) -> list[str]:
    changes = extract_file_changes(llm_output)
    
    if not changes:
        raise ValueError("No valid file changes found in LLM output")
    
    changed_files = []

    for relative_path, content in changes:
        target_path = WORKSPACE_DIR / relative_path

        if not is_safe_path(target_path):
            raise ValueError(f"Unsafe file path rejected: {relative_path}")
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        changed_files.append(str(target_path))

    return changed_files