from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_buyer_documentation_set_is_complete():
    required = {
        "ARCHITECTURE.md",
        "DATABASE.md",
        "SECURITY.md",
        "DEPLOYMENT.md",
        "TESTING.md",
        "TROUBLESHOOTING.md",
        "API.md",
    }
    docs = REPOSITORY_ROOT / "docs"
    assert required <= {path.name for path in docs.glob("*.md")}
    assert "```mermaid" in (docs / "ARCHITECTURE.md").read_text(encoding="utf-8")


def test_release_workflow_covers_versioned_image_publication():
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    required_markers = {
        "workflow_dispatch:",
        "git tag --annotate",
        "docker/login-action@v3",
        "docker/build-push-action@v6",
        "push: true",
        "sbom: true",
        "provenance: mode=max",
    }
    assert all(marker in workflow for marker in required_markers)


def test_dependabot_covers_all_dependency_ecosystems():
    config = (REPOSITORY_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    for ecosystem in ("pip", "npm", "github-actions"):
        assert f"package-ecosystem: {ecosystem}" in config


def test_local_quality_hooks_and_critical_coverage_gate_are_committed():
    hooks = (REPOSITORY_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")
    for marker in ("ruff check", "ruff format --check", "npm --prefix frontend run lint", "format:check"):
        assert marker in hooks
    assert "--cov-fail-under=90" in workflow
