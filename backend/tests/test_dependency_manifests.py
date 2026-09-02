import json
import re
import tomllib
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"


def _package_name(requirement: str) -> str:
    name = re.split(r"[<>=!~;\s]", requirement, maxsplit=1)[0]
    return re.sub(r"[-_.]+", "-", name.split("[", maxsplit=1)[0]).lower()


def _requirements(path: Path) -> set[str]:
    return {
        _package_name(line)
        for raw_line in path.read_text(encoding="utf-8").splitlines()
        if (line := raw_line.strip()) and not line.startswith(("#", "-r"))
    }


def test_backend_direct_dependencies_are_present_in_lockfile():
    direct = _requirements(BACKEND_ROOT / "requirements.txt")
    locked = _requirements(BACKEND_ROOT / "requirements-lock.txt")
    assert direct <= locked


def test_backend_development_dependencies_are_separate_and_locked():
    runtime = _requirements(BACKEND_ROOT / "requirements.txt")
    development = _requirements(BACKEND_ROOT / "requirements-dev.txt")
    locked = _requirements(BACKEND_ROOT / "requirements-lock.txt")
    assert {"pytest", "ruff", "mypy", "bandit", "pip-audit"} <= development
    assert development.isdisjoint(runtime)
    assert development <= locked


def test_pyproject_dependencies_are_present_in_lockfile():
    project = tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = {
        _package_name(requirement)
        for requirement in project["project"]["dependencies"] + project["project"]["optional-dependencies"]["dev"]
    }
    assert declared <= _requirements(BACKEND_ROOT / "requirements-lock.txt")


def test_frontend_package_and_lockfile_roots_match():
    package = json.loads((REPOSITORY_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((REPOSITORY_ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    lock_root = lock["packages"][""]
    assert package["dependencies"] == lock_root["dependencies"]
    assert package["devDependencies"] == lock_root["devDependencies"]
