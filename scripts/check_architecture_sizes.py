"""Fail when Phase 3 architecture modules reach 400 lines.

Run from the repository root. Blank and comment lines remain counted so the
limit is simple, deterministic, and difficult to game.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 400
TARGETS = (
    ROOT / "backend/app/services/llm_orchestration_service.py",
    ROOT / "backend/app/services/email_service.py",
    ROOT / "backend/app/services/llm",
    ROOT / "backend/app/services/email",
    ROOT / "frontend/src/App.jsx",
    ROOT / "frontend/src/routes",
    ROOT / "frontend/src/providers",
    ROOT / "frontend/src/components/layout",
    ROOT / "frontend/src/components/prompts",
)


def source_files(target: Path):
    if target.is_file():
        yield target
        return
    yield from (path for path in target.rglob("*") if path.suffix in {".py", ".js", ".jsx"})


def main() -> int:
    violations = []
    checked = []
    for target in TARGETS:
        for path in source_files(target):
            lines = len(path.read_text(encoding="utf-8").splitlines())
            checked.append((path, lines))
            if lines >= LIMIT:
                violations.append((path, lines))

    for path, lines in sorted(checked):
        print(f"{path.relative_to(ROOT)}: {lines} lines")
    if violations:
        print(f"Architecture limit exceeded ({LIMIT - 1} lines maximum):")
        for path, lines in violations:
            print(f"- {path.relative_to(ROOT)}: {lines}")
        return 1
    print(f"Checked {len(checked)} architecture files; all are below {LIMIT} lines.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
