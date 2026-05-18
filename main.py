from harness.context_loader import load_context
from harness.execution_manager import apply_file_changes
from harness.llm_service import call_llm
from harness.preflight import run_preflight_checks
from harness.prompts import build_code_prompt, build_fix_prompt, build_plan_prompt
from harness.repair_rules import (
    apply_basic_import_repairs,
    apply_basic_pytest_repairs,
    apply_basic_ruff_repairs,
)
from harness.state_manager import append_progress
from harness.validator import run_validation


MAX_FIX_ATTEMPTS = 2


def run_harness(user_request: str) -> None:
    print("\n=== Loading context ===")
    context = load_context()

    problems = run_preflight_checks()

    if problems:
        print("\n=== Preflight problems found ===")
        for problem in problems:
            print(f"- {problem}")

    print("\n=== Planning ===")
    plan_prompt = build_plan_prompt(user_request, context)
    plan = call_llm(plan_prompt)
    print(plan)

    print("\n=== Generating code changes ===")
    code_prompt = build_code_prompt(user_request, context, plan)
    code_output = call_llm(code_prompt)

    print("\n=== Applying code changes ===")
    changed_files = apply_file_changes(code_output)
    print("Changed files:")
    for file in changed_files:
        print(f"- {file}")

    problems = run_preflight_checks()
    if problems:
        print("\n=== Preflight problems found ===")
        for problem in problems:
            print(f"- {problem}")

        repaired_files = apply_basic_pytest_repairs("\n".join(problems))

        if repaired_files:
            changed_files.extend(repaired_files)

            print("\n=== Applied pytest repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            problems = run_preflight_checks()

        if not problems:
            print("\nPreflight passed after repair.")
        else:
            print("\nStopping before validation because the workspace layout is invalid.")
            return

    print("\n=== Running validation ===")
    validation = run_validation()
    print(validation.output)

    if not validation.passed:
        repaired_files = apply_basic_ruff_repairs(validation.output)

        if repaired_files:
            changed_files.extend(repaired_files)

            print("\n=== Applied basic Ruff repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            validation = run_validation()
            print(validation.output)

    if not validation.passed:
        repaired_files = apply_basic_pytest_repairs(validation.output)

        if repaired_files:
            changed_files.extend(repaired_files)

            print("\n=== Applied pytest repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            validation = run_validation()
            print(validation.output)

    fix_attempts = 0

    previous_validation_output = validation.output

    while not validation.passed and fix_attempts < MAX_FIX_ATTEMPTS:
        fix_attempts += 1

        print(f"\n=== Fix attempt {fix_attempts} ===")
        context = load_context()

        fix_prompt = build_fix_prompt(
            user_request=user_request,
            context=context,
            validation_output=validation.output,
        )

        fix_output = call_llm(fix_prompt)

        fixed_files = apply_file_changes(fix_output)
        changed_files.extend(fixed_files)

        print("Fixed files:")
        for file in fixed_files:
            print(f"- {file}")

        print("\n=== Running validation again ===")
        validation = run_validation()
        print(validation.output)

        problems = run_preflight_checks()
        if problems:
            print("\n=== Preflight problems found ===")
            for problem in problems:
                print(f"- {problem}")

            repaired_files = apply_basic_pytest_repairs("\n".join(problems))

            if repaired_files:
                changed_files.extend(repaired_files)

                print("\n=== Applied pytest repair rules ===")
                for file in repaired_files:
                    print(f"- {file}")

                problems = run_preflight_checks()

            if problems:
                print("\nStopping because the workspace layout is invalid.")
                return

            print("\nPreflight passed after repair.")

        if not validation.passed and validation.output == previous_validation_output:
            print("\nSame validation error repeated. Stopping early.")
            break

        previous_validation_output = validation.output

    if not validation.passed:
        repaired_files = apply_basic_import_repairs(validation.output)

        if repaired_files:
            changed_files.extend(repaired_files)

            print("\n=== Applied basic repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            validation = run_validation()
            print(validation.output)

    if not validation.passed:
        print("\n=== Final Result ===")
        print("Validation failed after fix attempts.")
        return

    print("\n=== Updating progress ===")
    append_progress(
        user_request=user_request,
        plan=plan,
        changed_files=changed_files,
        validation_output=validation.output,
    )

    print("\n=== Final Result ===")
    print("Task completed successfully.")
    print("Validation passed.")


if __name__ == "__main__":
    request = input("What should the harness build? ")
    run_harness(request)
