# Session Handoff

## Clock-In Checklist

Before making changes:

- [ ] Read `AGENTS.md`
- [ ] Read `harness_map.md`
- [ ] Read `progress.md`
- [ ] Read `feature_list.json`
- [ ] Read `run_history.json`
- [ ] Read `failure_log.json`
- [ ] Run preflight checks
- [ ] Run baseline validation if possible
- [ ] Identify current task and next step

## Clock-Out Checklist

Before ending the run:

- [ ] Run pytest
- [ ] Run Ruff
- [ ] Record changed files
- [ ] Update `progress.md` if validation passed
- [ ] Update `run_history.json`
- [ ] Update `failure_log.json` if a failure occurred
- [ ] Write clear next steps

## Purpose

Long-running tasks fail when agents lose continuity across sessions. This handoff
process makes every harness run start from durable project state and end with
enough information for the next session to continue safely.
