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
def test_readme_tools_section_uses_server_identifiers() -> None:
    contents = _read_readme_contents()

    tools_section_start = contents.index("### Tools")
    tools_section_end = contents.index("### Example prompts", tools_section_start)
    tools_section = contents[tools_section_start:tools_section_end]

    expected_identifiers = {
        "- overseerr_get_status: Get the status of the Overseerr server",
        "- overseerr_get_movie_requests: Get the list of all movie requests that satisfies the filter arguments",
        "- overseerr_get_tv_requests: Get the list of all TV show requests that satisfies the filter arguments",
    }

    for line in expected_identifiers:
        assert line in tools_section, f"README Tools entry missing or mismatched: {line}"
