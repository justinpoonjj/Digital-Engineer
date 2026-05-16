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


def apply_basic_ruff_repairs(validation_output: str) -> list[str]:
    changed_files = []

    if "F401" not in validation_output and "I001" not in validation_output:
        return changed_files

    for test_file in (WORKSPACE_DIR / "tests").glob("test_*.py"):
        content = test_file.read_text(encoding="utf-8")
        updated = content

        if "import pytest" in updated and "pytest." not in updated and "@pytest" not in updated:
            updated = updated.replace("import pytest\n\n", "")
            updated = updated.replace("import pytest\n", "")

        if updated != content:
            test_file.write_text(updated, encoding="utf-8")
            changed_files.append(str(test_file))

    return changed_files
