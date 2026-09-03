import json
import tomllib
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


def test_lint_and_format_configuration_is_committed_and_runnable():
    backend_config = tomllib.loads((REPOSITORY_ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8"))
    ruff = backend_config["tool"]["ruff"]
    assert ruff["target-version"] == "py311"
    assert ruff["line-length"] > 0
    assert {"F63", "F7", "F82", "I"} <= set(ruff["lint"]["select"])
    assert "per-file-ignores" in ruff["lint"]
    assert "format" in ruff

    frontend = REPOSITORY_ROOT / "frontend"
    eslint = (frontend / ".eslintrc.cjs").read_text(encoding="utf-8")
    for marker in ("eslint:recommended", "plugin:react/recommended", "plugin:react-hooks/recommended"):
        assert marker in eslint
    assert "'react/react-in-jsx-scope': 'off'" in eslint

    prettier = json.loads((frontend / ".prettierrc").read_text(encoding="utf-8"))
    assert prettier["singleQuote"] is True
    assert prettier["tabWidth"] == 2
    assert prettier["trailingComma"] == "es5"

    scripts = json.loads((frontend / "package.json").read_text(encoding="utf-8"))["scripts"]
    assert {"lint", "lint:fix", "format", "format:check"} <= scripts.keys()


def test_ci_actions_and_node_runtime_are_on_supported_versions():
    workflows = "\n".join(
        path.read_text(encoding="utf-8") for path in (REPOSITORY_ROOT / ".github" / "workflows").glob("*.yml")
    )
    for current_action in ("actions/checkout@v7", "actions/setup-python@v7", "actions/setup-node@v7"):
        assert current_action in workflows
    for deprecated_action in ("actions/checkout@v4", "actions/setup-python@v5", "actions/setup-node@v4"):
        assert deprecated_action not in workflows
    assert "node-version: 20" not in workflows
    assert (REPOSITORY_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8").startswith("FROM node:24-alpine")
