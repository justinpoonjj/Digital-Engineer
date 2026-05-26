import subprocess
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


def apply_preflight_repairs(preflight_output: str) -> list[str]:
    changed_files = []

    if "uses `from src...` import" in preflight_output:
        changed_files.extend(apply_from_src_import_repairs())

    if "imports pytest but does not use pytest features" in preflight_output:
        changed_files.extend(remove_unused_pytest_imports())

    if "uses pytest features but does not import pytest" in preflight_output:
        changed_files.extend(apply_basic_pytest_repairs(preflight_output))

    return unique_files(changed_files)


def apply_from_src_import_repairs() -> list[str]:
    changed_files = []

    for test_file in (WORKSPACE_DIR / "tests").glob("test_*.py"):
        content = test_file.read_text(encoding="utf-8")
        updated = content.replace("from src.", "from ")

        if updated != content:
            test_file.write_text(updated, encoding="utf-8")
            changed_files.append(str(test_file))

    return changed_files


def remove_unused_pytest_imports() -> list[str]:
    changed_files = []

    for test_file in (WORKSPACE_DIR / "tests").glob("test_*.py"):
        content = test_file.read_text(encoding="utf-8")

        if "import pytest" not in content:
            continue

        uses_pytest = "pytest." in content or "@pytest" in content
        if uses_pytest:
            continue

        updated = content.replace("import pytest\n\n", "")
        updated = updated.replace("import pytest\n", "")

        if updated != content:
            test_file.write_text(updated, encoding="utf-8")
            changed_files.append(str(test_file))

    return changed_files


def unique_files(files: list[str]) -> list[str]:
    unique = []

    for file in files:
        if file not in unique:
            unique.append(file)

    return unique


def apply_basic_ruff_repairs(validation_output: str) -> list[str]:
    changed_files = []

    if "F401" not in validation_output and "I001" not in validation_output:
        return changed_files

    if "I001" in validation_output:
        changed_files.extend(apply_ruff_auto_fix())

    changed_files.extend(remove_unused_pytest_imports())

    return unique_files(changed_files)


def apply_ruff_auto_fix() -> list[str]:
    tracked_files = list((WORKSPACE_DIR / "src").glob("*.py"))
    tracked_files.extend((WORKSPACE_DIR / "tests").glob("test_*.py"))

    before = {
        file: file.read_text(encoding="utf-8")
        for file in tracked_files
        if file.exists()
    }

    try:
        subprocess.run(
            ["ruff", "check", ".", "--fix"],
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            shell=False,
        )
    except FileNotFoundError:
        return apply_simple_import_sort(tracked_files)

    changed_files = []

    for file, old_content in before.items():
        if file.exists() and file.read_text(encoding="utf-8") != old_content:
            changed_files.append(str(file))

    return changed_files


def apply_simple_import_sort(files: list[Path]) -> list[str]:
    changed_files = []

    for file in files:
        if not file.exists():
            continue

        content = file.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        updated_lines = []

        for line in lines:
            stripped = line.strip()

            if (
                stripped.startswith("from ")
                and " import " in stripped
                and "(" not in stripped
                and ")" not in stripped
                and "," in stripped
            ):
                prefix, imported_names = stripped.split(" import ", maxsplit=1)
                names = [name.strip() for name in imported_names.split(",")]
                line_ending = "\n" if line.endswith("\n") else ""
                updated_lines.append(
                    f"{prefix} import {', '.join(sorted(names))}{line_ending}"
                )
            else:
                updated_lines.append(line)

        updated = "".join(updated_lines)

        if updated != content:
            file.write_text(updated, encoding="utf-8")
            changed_files.append(str(file))

    return changed_files


def apply_basic_pytest_repairs(validation_output: str) -> list[str]:
    changed_files = []

    should_repair = (
        "NameError: name 'pytest' is not defined" in validation_output
        or "uses pytest features but does not import pytest" in validation_output
    )

    if not should_repair:
        return changed_files

    for test_file in (WORKSPACE_DIR / "tests").glob("test_*.py"):
        content = test_file.read_text(encoding="utf-8")

        uses_pytest = (
            "pytest." in content
            or "@pytest" in content
            or "pytest.raises" in content
        )

        already_imports_pytest = "import pytest" in content

        if uses_pytest and not already_imports_pytest:
            updated = "import pytest\n\n" + content

            test_file.write_text(updated, encoding="utf-8")
            changed_files.append(str(test_file))

    return changed_files
