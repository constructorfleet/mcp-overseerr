from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read_workflow(name: str) -> str:
    workflow_path = REPO_ROOT / ".github/workflows" / name
    assert workflow_path.exists(), f"{name} workflow file is missing"
    return workflow_path.read_text()


@pytest.fixture
def docker_workflow_contents() -> str:
    return _read_workflow("docker-publish.yml")


def test_tag_on_main_workflow_configures_main_push_tagging():
    contents = _read_workflow("tag-on-main.yml")
    assert "on:" in contents and "push:" in contents, "workflow must configure push trigger"
    assert "branches:" in contents and "- main" in contents, "workflow must target main branch"
    assert "github-tag-action" in contents, "workflow should create tags on merge to main"


def test_docker_publish_workflow_attests_ghcr_image(docker_workflow_contents: str):
    contents = docker_workflow_contents
    assert "ghcr.io/${{ github.repository }}" in contents, "image should target GHCR"
    assert "docker/build-push-action" in contents, "workflow should build docker image"
    assert "actions/attest-build-provenance" in contents, "workflow should attest build provenance"


def test_docker_publish_workflow_has_build_context():
    dockerfile_path = REPO_ROOT / "Dockerfile"
    assert dockerfile_path.exists(), "docker publish workflow must have a Dockerfile to build"


def test_docker_publish_workflow_grants_attestation_permissions(docker_workflow_contents: str):
    contents = docker_workflow_contents
    assert "attestations: write" in contents, "attestation step requires attestations: write permission"
