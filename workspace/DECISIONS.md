# Decisions

## 2026-05-25: Keep AGENTS.md as a routing file

### Decision

`AGENTS.md` should remain short and route to focused topic docs.

### Reason

Lecture 4 warns that one giant instruction file creates instruction bloat and
lowers instruction signal-to-noise ratio.

### Impact

Detailed testing rules stay in `docs/testing-standards.md`.
Repair logic stays in `docs/repair-rules-guide.md`.
State rules stay in `docs/state-management.md`.
Session lifecycle rules stay in `docs/session-handoff.md`.

### Revisit Condition

Revisit if agents repeatedly fail to discover the correct topic docs.

## 2026-05-25: Make continuity first-class

### Decision

Every harness run should follow an explicit clock-in and clock-out lifecycle.

### Reason

Lecture 5 identifies rebuild cost as a core risk for long-running agent work. A
fresh agent needs to know what happened, why it happened, and how to resume.

### Impact

The context loader includes durable state, decisions, and session handoff docs.
Run history includes session IDs, timestamps, changed files, and final status.
Failure logs preserve repaired intermediate failures as well as final failures.

### Revisit Condition

Revisit if run logs become noisy enough that they slow down future agents.
