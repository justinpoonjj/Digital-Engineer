from pathlib import Path


WORKSPACE_DIR = Path("workspace")


def run_preflight_checks() -> list[str]:
    problems = []

    nested_workspace = WORKSPACE_DIR / "workspace"
    if nested_workspace.exists():
        problems.append(
            "Nested workspace directory detected at workspace/workspace. "
            "The LLM likely returned paths starting with workspace/. "
            "File paths must be relative, e.g. src/calculator.py."
        )

    expected_tests_dir = WORKSPACE_DIR / "tests"
    if not expected_tests_dir.exists():
        problems.append("Missing tests/ directory under workspace root.")

    singular_test_dir = WORKSPACE_DIR / "test"
    if singular_test_dir.exists():
        problems.append(
            "Unexpected test/ directory detected under workspace root. "
            "Tests must be placed in tests/."
        )

    expected_src_dir = WORKSPACE_DIR / "src"
    if not expected_src_dir.exists():
        problems.append("Missing src/ directory under workspace root.")

    for test_file in (WORKSPACE_DIR / "tests").glob("test_*.py"):
        content = test_file.read_text(encoding="utf-8")

        if "from src." in content:
            problems.append(
                f"{test_file}: uses `from src...` import. "
                "This project uses pythonpath=['src'], so import directly instead."
            )

        uses_pytest = "pytest." in content or "@pytest" in content
        imports_pytest = "import pytest" in content

        if uses_pytest and not imports_pytest:
            problems.append(
                f"{test_file}: uses pytest features but does not import pytest."
            )

        if imports_pytest and not uses_pytest:
            problems.append(
                f"{test_file}: imports pytest but does not use pytest features."
            )

    return problems
