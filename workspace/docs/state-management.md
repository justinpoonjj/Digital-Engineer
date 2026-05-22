# State Management

## Purpose
State files help the harness preserve progress across runs.

They are durable project memory. They should make it possible for a fresh agent or developer to understand what has been attempted, what passed validation, and what still needs attention.

## progress.md
Use this file to record:
- current task
- completed work
- failed validation attempts
- known blockers
- next step

The harness controller should update `progress.md` after validation. Generated code responses should not edit it directly.

## feature_list.json
Use this file to track:
- feature name
- status
- files changed
- tests added
- validation status

Update `feature_list.json` when a feature is added, completed, blocked, or otherwise changes status.

## run_history.json
Use this file to track completed harness runs:
- task id
- user task
- mode
- pytest result
- Ruff result
- repair attempt count
- whether unrelated files were modified
- whether tests were deleted or weakened

## failure_log.json
Use this file to track validation failures and repair outcomes:
- task
- failure layer
- tool
- error summary
- repair rule used
- whether the repair succeeded

## Update Rules
After each task:
- update `progress.md`
- update `feature_list.json` if feature status changed
- record validation result
- record unresolved errors
- add measurable run or failure data when useful for comparing prompt-only and harness-supported runs
