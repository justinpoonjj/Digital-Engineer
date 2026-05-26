import subprocess
from dataclasses import dataclass
from pathlib import Path


WORKSPACE_DIR = Path("workspace")


@dataclass
class ValidationResult:
    passed: bool
    output: str


def run_command(command: list[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            cwd="workspace",
            capture_output=True,
            text=True,
            shell=False,
        )
    except FileNotFoundError as exc:
        output = f"""
Command: {" ".join(command)}
Return code: 127

STDOUT:

STDERR:
Command not found: {command[0]}
{exc}
"""

        return 127, output

    output = f"""
Command: {" ".join(command)}
Return code: {completed.returncode}

STDOUT:
{completed.stdout}

STDERR:
{completed.stderr}
"""

    return completed.returncode, output


def commands_for_profile(profile: str) -> list[list[str]]:
    if profile == "startup":
        return [
            ["pytest", "--version"],
            ["ruff", "--version"],
        ]

    if profile in {"implementation", "calculator"}:
        return [
            ["pytest", "tests/test_calculator.py"],
            ["ruff", "check", "src/calculator.py", "tests/test_calculator.py"],
        ]

    if profile == "harness":
        return [
            ["pytest", "../tests"],
            ["ruff", "check", "../harness", "../main.py", "../tests"],
        ]

    if profile == "full":
        return [
            ["pytest"],
            ["pytest", "../tests"],
            ["ruff", "check", ".", "../harness", "../main.py", "../tests"],
        ]

    raise ValueError(f"Unknown validation profile: {profile}")


def run_validation(profile: str = "implementation") -> ValidationResult:
    if profile in {"implementation", "calculator"}:
        required_files = [
            "src/calculator.py",
            "tests/test_calculator.py",
        ]

        for file in required_files:
            if not (WORKSPACE_DIR / file).exists():
                return ValidationResult(
                    passed=False,
                    output=(
                        "Generation error: required file missing before "
                        f"validation: {file}"
                    ),
                )

    commands = commands_for_profile(profile)

    full_output = ""

    for command in commands:
        return_code, output = run_command(command)
        full_output += output + "\n"

        if return_code != 0:
            return ValidationResult(
                passed=False,
                output=full_output,
            )

    return ValidationResult(
        passed=True,
        output=full_output,
    )
