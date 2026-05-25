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
from harness.state_manager import (
    append_failure_log,
    append_progress,
    append_run_history,
    get_next_session_id,
)
from harness.validator import run_validation


MAX_FIX_ATTEMPTS = 2


def clock_in() -> str:
    print("\n=== Clock In ===")
    context = load_context()

    problems = run_preflight_checks()
    if problems:
        print("\n=== Preflight problems found during clock-in ===")
        for problem in problems:
            print(f"- {problem}")
    else:
        print("Preflight passed.")

    return context


def command_passed(validation_output: str, command: str) -> bool:
    return f"Command: {command}\nReturn code: 0" in validation_output


def validation_summary(validation_output: str, preflight_passed: bool) -> str:
    pytest_result = "pass" if command_passed(validation_output, "pytest") else "fail"
    ruff_result = "pass" if command_passed(validation_output, "ruff check .") else "fail"
    preflight_result = "pass" if preflight_passed else "fail"

    return f"- Pytest: {pytest_result}\n- Ruff: {ruff_result}\n- Preflight: {preflight_result}"


def unique_files(files: list[str]) -> list[str]:
    unique = []

    for file in files:
        if file not in unique:
            unique.append(file)

    return unique


def log_repaired_failure(
    session_id: str,
    user_request: str,
    failure_layer: str,
    tool: str,
    error_summary: str,
    repair_rule_used: str,
    repair_successful: bool,
) -> None:
    append_failure_log(
        user_request=user_request,
        failure_layer=failure_layer,
        tool=tool,
        error_summary=error_summary[:500],
        repair_rule_used=repair_rule_used,
        repair_successful=repair_successful,
        session_id=session_id,
    )


def clock_out_success(
    session_id: str,
    user_request: str,
    plan: str,
    changed_files: list[str],
    validation_output: str,
    repair_attempts: int,
    failures_encountered: list[str],
) -> None:
    print("\n=== Clock Out: Success ===")

    changed_files = unique_files(changed_files)

    append_progress(
        user_request=user_request,
        plan=plan,
        changed_files=changed_files,
        validation_output=validation_output,
        validation_result=validation_summary(validation_output, preflight_passed=True),
        failures_encountered=failures_encountered,
        final_status="Success",
        next_step="Continue with the next requested feature or repair task.",
    )

    append_run_history(
        user_request=user_request,
        pytest_passed=True,
        ruff_passed=True,
        repair_attempts=repair_attempts,
        changed_files=changed_files,
        final_status="success",
        session_id=session_id,
    )


def clock_out_failure(
    session_id: str,
    user_request: str,
    failure_layer: str,
    tool: str,
    error_summary: str,
    repair_rule_used: str | None,
    changed_files: list[str],
    repair_attempts: int,
) -> None:
    print("\n=== Clock Out: Failure ===")

    append_failure_log(
        user_request=user_request,
        failure_layer=failure_layer,
        tool=tool,
        error_summary=error_summary[:500],
        repair_rule_used=repair_rule_used,
        repair_successful=False,
        session_id=session_id,
    )

    append_run_history(
        user_request=user_request,
        pytest_passed=False,
        ruff_passed=False,
        repair_attempts=repair_attempts,
        changed_files=unique_files(changed_files),
        final_status="failed",
        session_id=session_id,
    )


def run_harness(user_request: str) -> None:
    session_id = get_next_session_id()
    repair_attempt_count = 0
    failures_encountered = []

    context = clock_in()

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

        problem_summary = "\n".join(problems)
        repaired_files = apply_basic_pytest_repairs("\n".join(problems))

        if repaired_files:
            repair_attempt_count += 1
            changed_files.extend(repaired_files)

            print("\n=== Applied pytest repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            problems = run_preflight_checks()
            repair_successful = not problems
            if repair_successful:
                failures_encountered.append("Preflight failed and pytest repair rules fixed it.")
            else:
                failures_encountered.append(
                    "Preflight failed after pytest repair rules changed files."
                )
            log_repaired_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="preflight",
                tool="preflight",
                error_summary=problem_summary,
                repair_rule_used="pytest_preflight_repair",
                repair_successful=repair_successful,
            )

        if not problems:
            print("\nPreflight passed after repair.")
        else:
            print("\nStopping before validation because the workspace layout is invalid.")
            clock_out_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="preflight",
                tool="preflight",
                error_summary="Workspace layout is invalid.",
                repair_rule_used="pytest_preflight_repair",
                changed_files=changed_files,
                repair_attempts=repair_attempt_count,
            )
            return

    print("\n=== Running validation ===")
    validation = run_validation()
    print(validation.output)

    if not validation.passed:
        failed_output = validation.output
        repaired_files = apply_basic_ruff_repairs(validation.output)

        if repaired_files:
            repair_attempt_count += 1
            changed_files.extend(repaired_files)

            print("\n=== Applied basic Ruff repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            validation = run_validation()
            print(validation.output)
            repair_successful = validation.passed
            if repair_successful:
                failures_encountered.append("Ruff failed and basic Ruff repair rules fixed it.")
            else:
                failures_encountered.append(
                    "Ruff failed after basic Ruff repair rules changed files."
                )
            log_repaired_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="feedback",
                tool="ruff",
                error_summary=failed_output,
                repair_rule_used="apply_basic_ruff_repairs",
                repair_successful=repair_successful,
            )

    if not validation.passed:
        failed_output = validation.output
        repaired_files = apply_basic_pytest_repairs(validation.output)

        if repaired_files:
            repair_attempt_count += 1
            changed_files.extend(repaired_files)

            print("\n=== Applied pytest repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            validation = run_validation()
            print(validation.output)
            repair_successful = validation.passed
            if repair_successful:
                failures_encountered.append("Pytest failed and basic pytest repair rules fixed it.")
            else:
                failures_encountered.append(
                    "Pytest failed after basic pytest repair rules changed files."
                )
            log_repaired_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="feedback",
                tool="pytest",
                error_summary=failed_output,
                repair_rule_used="apply_basic_pytest_repairs",
                repair_successful=repair_successful,
            )

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
        failed_output = validation.output
        validation = run_validation()
        print(validation.output)

        if fixed_files:
            repair_success = validation.passed
            failures_encountered.append(
                "Validation failed and an LLM fix prompt changed files."
            )
            append_failure_log(
                user_request=user_request,
                failure_layer="feedback",
                tool="pytest_or_ruff",
                error_summary=failed_output[:500],
                repair_rule_used="llm_fix_prompt",
                repair_successful=repair_success,
                session_id=session_id,
            )

        problems = run_preflight_checks()
        if problems:
            print("\n=== Preflight problems found ===")
            for problem in problems:
                print(f"- {problem}")

            problem_summary = "\n".join(problems)
            repaired_files = apply_basic_pytest_repairs("\n".join(problems))

            if repaired_files:
                repair_attempt_count += 1
                changed_files.extend(repaired_files)

                print("\n=== Applied pytest repair rules ===")
                for file in repaired_files:
                    print(f"- {file}")

                problems = run_preflight_checks()
                repair_successful = not problems
                if repair_successful:
                    failures_encountered.append(
                        "Preflight failed and pytest repair rules fixed it."
                    )
                else:
                    failures_encountered.append(
                        "Preflight failed after pytest repair rules changed files."
                    )
                log_repaired_failure(
                    session_id=session_id,
                    user_request=user_request,
                    failure_layer="preflight",
                    tool="preflight",
                    error_summary=problem_summary,
                    repair_rule_used="pytest_preflight_repair",
                    repair_successful=repair_successful,
                )

            if problems:
                print("\nStopping because the workspace layout is invalid.")
                clock_out_failure(
                    session_id=session_id,
                    user_request=user_request,
                    failure_layer="preflight",
                    tool="preflight",
                    error_summary="Workspace layout is invalid after repair.",
                    repair_rule_used="pytest_preflight_repair",
                    changed_files=changed_files,
                    repair_attempts=repair_attempt_count + fix_attempts,
                )
                return

            print("\nPreflight passed after repair.")

        if not validation.passed and validation.output == previous_validation_output:
            print("\nSame validation error repeated. Stopping early.")
            break

        previous_validation_output = validation.output

    if not validation.passed:
        failed_output = validation.output
        repaired_files = apply_basic_import_repairs(validation.output)

        if repaired_files:
            repair_attempt_count += 1
            changed_files.extend(repaired_files)

            print("\n=== Applied basic repair rules ===")
            for file in repaired_files:
                print(f"- {file}")

            validation = run_validation()
            print(validation.output)
            repair_successful = validation.passed
            if repair_successful:
                failures_encountered.append(
                    "Import failure was fixed by basic import repair rules."
                )
            else:
                failures_encountered.append(
                    "Import failure remained after basic import repair rules changed files."
                )
            log_repaired_failure(
                session_id=session_id,
                user_request=user_request,
                failure_layer="feedback",
                tool="pytest",
                error_summary=failed_output,
                repair_rule_used="apply_basic_import_repairs",
                repair_successful=repair_successful,
            )

    if not validation.passed:
        print("\n=== Final Result ===")
        print("Validation failed after fix attempts.")
        clock_out_failure(
            session_id=session_id,
            user_request=user_request,
            failure_layer="feedback",
            tool="pytest_or_ruff",
            error_summary=validation.output[:500],
            repair_rule_used="llm_fix_prompt",
            changed_files=changed_files,
            repair_attempts=repair_attempt_count + fix_attempts,
        )
        return

    clock_out_success(
        session_id=session_id,
        user_request=user_request,
        plan=plan,
        changed_files=changed_files,
        validation_output=validation.output,
        repair_attempts=repair_attempt_count + fix_attempts,
        failures_encountered=failures_encountered,
    )

    print("\n=== Final Result ===")
    print("Task completed successfully.")
    print("Validation passed.")


if __name__ == "__main__":
    request = input("What should the harness build? ")
    run_harness(request)
