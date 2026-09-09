"""Run the same clean-install quality contract on Windows and Linux."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def run(command, cwd):
    print("==> " + " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, check=True)

def main():
    if sys.version_info[:2] != (3, 11):
        raise SystemExit("Python 3.11 is required")
    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if not node or not npm:
        raise SystemExit("Node 24 and npm are required")
    version = subprocess.check_output([node, "--version"], text=True).strip()
    if version.split(".")[0] != "v24":
        raise SystemExit("Node 24 is required; found " + version)
    # TemporaryDirectory owns a unique, absolute directory and cleans only that directory.
    with tempfile.TemporaryDirectory(prefix="email-agent-verify-") as directory:
        env = Path(directory) / "venv"
        run([sys.executable, "-m", "venv", str(env)], ROOT)
        python = str(env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))
        backend = ROOT / "backend"
        run([python, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check", "--no-input", "-r", "requirements-tooling.txt"], backend)
        run([python, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "-r", "requirements-lock.txt"], backend)
        run([python, "-m", "pip", "check"], backend)
        checks = [
            ["ruff", "check", "."], ["ruff", "format", "--check", "."], ["mypy"],
            ["pytest", "tests", "--cov=app", "--cov-report=term-missing", "--cov-fail-under=31", "-q"],
            ["pytest", "tests", "--cov=app.core", "--cov=app.models", "--cov=app.utils",
             "--cov=app.services.email_service", "--cov=app.services.email", "--cov=app.services.mock_email_loader",
             "--cov=app.services.llm_orchestration_service", "--cov=app.services.model_registry",
             "--cov=app.services.prompt_registry", "--cov-report=term-missing", "--cov-fail-under=50", "-q"],
            ["pytest", "tests/test_api_schema_contract.py", "tests/test_input_validation.py", "tests/test_security_middleware.py",
             "--cov=app.api.schemas", "--cov=app.core.input_validation", "--cov-report=term-missing", "--cov-fail-under=90", "-q"],
            ["bandit", "-c", "pyproject.toml", "-r", "app", "--severity-level", "medium"], ["pip_audit"],
        ]
        for check in checks:
            run([python, "-m", *check], backend)
        frontend = ROOT / "frontend"
        run([npm, "ci"], frontend)
        for script in ["format:check", "lint", "typecheck", "test:coverage", "build"]:
            run([npm, "run", script], frontend)
        run([npm, "audit", "--audit-level=high"], frontend)
    print("Fresh-clone verification passed.", flush=True)

if __name__ == "__main__":
    main()
