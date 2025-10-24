from pathlib import Path


def _read_readme_contents() -> str:
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md must exist"
    return readme_path.read_text(encoding="utf-8")


def test_readme_includes_uv_testing_instructions() -> None:
    contents = _read_readme_contents()

    required_snippets = (
        ("uv venv", "README should instruct creating a uv virtual environment"),
        (
            "uv run python -m pytest",
            "README should document running tests via uv",
        ),
    )

    for snippet, message in required_snippets:
        assert snippet in contents, message


def test_readme_includes_quickstart_run_instructions() -> None:
    contents = _read_readme_contents()

    required_snippets = (
        ("### Run", "README should document how to run the server"),
        ("uvx overseerr-mcp", "README should mention the published command"),
        ("uv run overseerr-mcp", "README should mention running from the repo"),
        (
            "OVERSEERR_API_KEY",
            "README should highlight required OVERSEERR_API_KEY environment variable",
        ),
        (
            "OVERSEERR_URL",
            "README should highlight required OVERSEERR_URL environment variable",
        ),
        (
            "Example invocation",
            "README should include an example invocation heading",
        ),
        (
            "Server started",
            "README should show a log snippet that confirms the server started",
        ),
    )

    for snippet, message in required_snippets:
        assert snippet in contents, message
