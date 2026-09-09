import json
import tomllib
from importlib.metadata import requires
from pathlib import Path

import pytest
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
PROJECT = tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _parse_requirements(lines):
    requirements = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = Requirement(line)
        name = canonicalize_name(requirement.name)
        assert name not in requirements, f"Duplicate requirement: {name}"
        assert requirement.url is None, f"Unversioned URL dependency: {name}"
        requirements[name] = requirement
    return requirements


def _requirements(filename, directives=()):
    lines = (BACKEND_ROOT / filename).read_text(encoding="utf-8").splitlines()
    actual_directives = [line.strip() for line in lines if line.strip().startswith("-")]
    assert actual_directives == list(directives)
    return _parse_requirements(line for line in lines if not line.strip().startswith("-"))


def _signature(requirement):
    return requirement.extras, requirement.specifier, str(requirement.marker)


def test_runtime_manifests_match_versions_extras_and_markers():
    runtime = _requirements("requirements.txt", ("-c requirements-lock.txt",))
    declared = _parse_requirements(PROJECT["project"]["dependencies"])
    assert runtime.keys() == declared.keys()
    for name, requirement in runtime.items():
        assert _signature(requirement) == _signature(declared[name]), name


def test_development_manifests_match_and_stay_separate():
    development = _requirements("requirements-dev.txt", ("-r requirements.txt",))
    declared = _parse_requirements(PROJECT["project"]["optional-dependencies"]["dev"])
    runtime = _parse_requirements(PROJECT["project"]["dependencies"])
    assert development.keys() == declared.keys()
    assert development.keys().isdisjoint(runtime)
    assert {"pytest", "ruff", "mypy", "bandit", "pip-audit"} <= development.keys()
    for name, requirement in development.items():
        assert _signature(requirement) == _signature(declared[name]), name


def test_lockfile_pins_satisfy_every_runtime_and_development_requirement():
    locked = _requirements("requirements-lock.txt")
    versions = {}
    for name, requirement in locked.items():
        pins = list(requirement.specifier)
        assert len(pins) == 1 and pins[0].operator == "==", name
        assert "*" not in pins[0].version, name
        assert not requirement.extras, name
        versions[name] = Version(pins[0].version)
    declared = _parse_requirements(
        PROJECT["project"]["dependencies"] + PROJECT["project"]["optional-dependencies"]["dev"]
    )
    assert declared.keys() <= versions.keys()
    for name, requirement in declared.items():
        assert versions[name] in requirement.specifier, f"Lock pin violates {requirement}"


@pytest.mark.parametrize(
    ("platform", "implementation"),
    [("win32", "CPython"), ("linux", "CPython"), ("darwin", "CPython"), ("linux", "PyPy")],
)
def test_declared_extras_have_compatible_lock_entries(platform, implementation):
    environment = {**default_environment(), "sys_platform": platform, "platform_python_implementation": implementation}
    locked = _requirements("requirements-lock.txt")
    for requirement in _parse_requirements(PROJECT["project"]["dependencies"]).values():
        if not requirement.extras:
            continue
        for declaration in requires(requirement.name) or []:
            dependency = Requirement(declaration)
            active = dependency.marker is None or any(
                dependency.marker.evaluate({**environment, "extra": extra}) for extra in requirement.extras | {""}
            )
            if not active:
                continue
            name = canonicalize_name(dependency.name)
            assert name in locked, f"Missing dependency of {requirement}: {dependency} on {platform}"
            pin = locked[name]
            assert pin.marker is None or pin.marker.evaluate(environment), str(pin)
            assert Version(next(iter(pin.specifier)).version) in dependency.specifier, str(dependency)


def test_packaging_tooling_satisfies_build_requirements():
    tooling = _requirements("requirements-tooling.txt")
    for requirement in _parse_requirements(PROJECT["build-system"]["requires"]).values():
        name = canonicalize_name(requirement.name)
        pins = list(tooling[name].specifier)
        assert len(pins) == 1 and pins[0].operator == "==", name
        assert Version(pins[0].version) in requirement.specifier, name


def test_frontend_package_and_lockfile_roots_match():
    package = json.loads((REPOSITORY_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((REPOSITORY_ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    lock_root = lock["packages"][""]
    assert package["dependencies"] == lock_root["dependencies"]
    assert package["devDependencies"] == lock_root["devDependencies"]
    assert package["version"] == lock_root["version"] == PROJECT["project"]["version"]
