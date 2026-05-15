import subprocess
from dataclasses import dataclass


@dataclass
class ValidationResult:
    passed: bool
    output: str


def run_command(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd="workspace",
        capture_output=True,
        text=True,
        shell=False,
    )

    output = f"""
Command: {" ".join(command)}
Return code: {completed.returncode}

STDOUT:
{completed.stdout}

STDERR:
{completed.stderr}
"""

    return completed.returncode, output


def run_validation() -> ValidationResult:
    commands = [
        ["pytest"],
        ["ruff", "check", "."],
    ]

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