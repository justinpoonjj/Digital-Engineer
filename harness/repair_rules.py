from pathlib import Path


WORKSPACE_DIR = Path("workspace")


def apply_basic_import_repairs(validation_output: str) -> list[str]:
    changed_files = []

    if "ModuleNotFoundError: No module named 'src'" not in validation_output:
        return changed_files

    tests_dir = WORKSPACE_DIR / "tests"

    for test_file in tests_dir.glob("test_*.py"):
        content = test_file.read_text(encoding="utf-8")
        updated = content.replace("from src.", "from ")

        if updated != content:
            test_file.write_text(updated, encoding="utf-8")
            changed_files.append(str(test_file))

    return changed_files