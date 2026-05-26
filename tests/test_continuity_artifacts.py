from pathlib import Path

WORKSPACE = Path("workspace")


def test_continuity_files_exist():
    required_files = [
        "AGENTS.md",
        "harness_map.md",
        "progress.md",
        "feature_list.json",
        "run_history.json",
        "failure_log.json",
        "DECISIONS.md",
        "docs/debugging-policy.md",
        "docs/session-handoff.md",
    ]

    for file in required_files:
        assert (WORKSPACE / file).exists()
