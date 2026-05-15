from pathlib import Path


WORKSPACE_DIR = Path("workspace")


def run_preflight_checks() -> list[str]:
    problems = []

    for test_file in (WORKSPACE_DIR / "tests").glob("test_*.py"):
        content = test_file.read_text(encoding="utf-8")

        if "from src." in content:
            problems.append(
                f"{test_file}: uses `from src...` import. "
                "This project uses pythonpath=['src'], so import directly instead."
            )

    return problems