from pathlib import Path


def test_ci_workflow_runs_pytest_on_pull_requests_to_main() -> None:
    workflow_path = Path('.github/workflows/tests.yml')
    assert workflow_path.exists(), "Expected CI workflow to exist at .github/workflows/tests.yml"

    contents = workflow_path.read_text(encoding="utf-8")
    required_snippets = {
        "pull_request": "Workflow must trigger on pull_request events",
        "branches:\n      - main": "Workflow must limit pull_request trigger to main branch",
        "uv run python -m pytest": "Workflow must run pytest via uv",
    }

    for snippet, message in required_snippets.items():
        assert snippet in contents, message
