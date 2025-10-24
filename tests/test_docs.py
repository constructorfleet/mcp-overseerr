from pathlib import Path


def test_readme_includes_uv_testing_instructions() -> None:
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md must exist"

    contents = readme_path.read_text(encoding="utf-8")

    required_snippets = (
        ("uv venv", "README should instruct creating a uv virtual environment"),
        (
            "uv run python -m pytest",
            "README should document running tests via uv",
        ),
    )

    for snippet, message in required_snippets:
        assert snippet in contents, message
