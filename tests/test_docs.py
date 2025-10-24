from pathlib import Path


def _read_readme_contents() -> str:
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md must exist"
    return readme_path.read_text(encoding="utf-8")
  
def assert_snippets(required_snippets) -> None:
    contents = _read_readme_contents()

    for snippet, message in required_snippets:
        assert snippet in contents, message


def test_readme_includes_uv_testing_instructions() -> None:
    required_snippets = (
        ("uv venv", "README should instruct creating a uv virtual environment"),
        (
            "uv run python -m pytest",
            "README should document running tests via uv",
        ),
    )

    assert_snippets(required_snippets)


def test_readme_includes_quickstart_run_instructions() -> None:
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

    assert_snippets(required_snippets)


def test_readme_documents_request_tool_structures() -> None:
    required_snippets = (
        (
            "#### overseerr_movie_requests response structure",
            "README should document the movie request response section",
        ),
        (
            "MovieRequestsToolHandler.get_movie_requests",
            "README should cross-reference the movie request implementation",
        ),
        (
            "`media_availability` values: `UNKNOWN`, `PENDING`, `PROCESSING`, `PARTIALLY_AVAILABLE`, `AVAILABLE`",
            "README should list media availability values for movie requests",
        ),
        (
            "`request_date` (ISO 8601 creation timestamp from Overseerr)",
            "README should describe the movie request timestamp",
        ),
        (
            "Movie request example",
            "README should provide a sample movie request payload",
        ),
        (
            "#### overseerr_tv_requests response structure",
            "README should document the tv request response section",
        ),
        (
            "TvRequestsToolHandler.get_tv_requests",
            "README should cross-reference the tv request implementation",
        ),
        (
            "`tv_episodes` is a list of episode objects containing `episode_number` and `episode_name`",
            "README should describe the tv episode entries",
        ),
        (
            "`tv_season` is formatted as",
            "README should explain the tv season formatting",
        ),
        (
            "TV request example",
            "README should provide a sample tv request payload",
        ),
    )

    assert_snippets(required_snippets)


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


def test_readme_documents_running_server_http_entrypoint() -> None:
    required_snippets = (
        (
            "### Running the server",
            "README should include a running section that follows Quickstart",
        ),
        (
            "`overseerr_mcp.server.main()` launches the FastMCP app over HTTP",
            "README should document the main entrypoint and FastMCP transport",
        ),
        (
            "http://0.0.0.0:8000/mcp",
            "README should mention the default HTTP endpoint",
        ),
        (
            (
                "override the default transport, host, or port by passing FastMCP's "
                "`transport`, `host`, or `port` arguments"
            ),
            "README should explain how to adjust FastMCP networking parameters",
        ),
        (
            "uv run overseerr-mcp",
            "README should show the uv command for launching the server",
        ),
        (
            "firewall or reverse proxy",
            "README should mention networking considerations when exposing the endpoint",
        ),
    )

    assert_snippets(required_snippets)
