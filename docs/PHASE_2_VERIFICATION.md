# Phase 2: Backend dependency architecture

This phase follows the repository-specific Phase 2 in the supplied feedback.
It starts from Phase 1 commit `5b3a565` on branch `phase-2-dependencies`.

## Requirement-by-requirement decisions

1. **Version policy:** retain backend package version 1.0.0, consistent with the
   frontend package and lock metadata. No downgrade, release tag or runtime
   APP_VERSION change was made. Runtime labels and release versioning are
   documented separately.
2. **Runtime manifests:** requirements.txt now mirrors pyproject.toml exactly,
   including extras and versions. google-auth is declared directly because the
   Gmail services import it. Existing package versions remain unchanged.
3. **Development manifests:** requirements-dev.txt mirrors the dev extra and
   includes runtime requirements. packaging is explicitly declared for the
   requirement-parsing regression tests, using its existing locked version.
4. **Transitive dependencies:** requirements.txt applies requirements-lock.txt
   as constraints. Transitive resolution pins remain in the lock rather than
   being misclassified as direct requirements.
5. **Platform completeness:** fresh Linux resolution identified uvloop 0.22.1,
   required by Uvicorn's standard extra but absent from the old Windows-derived
   lock. Its pin uses Uvicorn's platform conditions to exclude Windows, Cygwin
   and PyPy. No other existing lock pin changed.
6. **Regression protection:** tests compare names, versions, extras and markers;
   reject duplicates/unpinned lock entries; check development separation, build
   tooling compatibility and frontend package metadata; and validate dependency
   extras against platform conditions for Windows, Linux, macOS and PyPy.
7. **Installed compatibility:** pip check is an explicit backend CI step and runs
   in the canonical fresh-clone verifier after installation.
8. **Maintenance documentation:** installation modes and lock refresh now include
   development tools, exclude editable/local paths and packaging tools from a
   candidate snapshot, and require review across Windows and Linux.

## Verification (2026-09-09)

A separate local Git clone received only the Phase 2 changes. No existing .env
or installed Python environment was copied. Each installation test creates a
new disposable virtual environment. Download caches may be reused.

- Focused dependency contract: 9 tests passed.
- Clean Windows runtime-only install: passed pip check; all installed versions
  matched the committed lock/tooling pins; no test/lint tools were installed;
  every configured API router loaded.
- Linux resolver: successfully resolved the development graph and identified
  the missing uvloop pin. pip is covered separately by requirements-tooling.txt.
- Clean Windows editable-development install: passed (exit 0). Installed package
  and dependency versions matched the project, lock and tooling pins. pip check
  passed; 202 backend tests passed with 34.31% application coverage (31% required).
  Ruff lint/format and mypy passed. Dependency audit found no known vulnerabilities
  (only the local editable project itself was excluded from the PyPI audit).
- Clean Linux development install: passed (exit 0). pip check passed; 202 backend
  tests passed with 34.31% application coverage. Dependency audit found no known
  vulnerabilities. Application startup and /ready passed under uvloop. The
  disposable environment and container were cleaned up.
- Updated workflow YAML and verification-runner syntax: passed.
- Final diff whitespace check: passed.

An initial editable install hit repeated PyPI timeouts and connection resets.
The reported platformdirs conflict was checked against PyPI and was not a
version incompatibility; validation was retried with longer network timeouts.

## Review checkpoint

No application module, database schema, frontend feature or provider account was
changed. Adding uvloop can change Uvicorn's event-loop selection on Linux, so
startup under that loop is explicitly validated. Platform-marker assertions for
macOS/PyPy do not claim native test runs on those platforms.

Phase 2 is not committed or pushed. Hosted CI is pending publication. The next
phase is canonical database model ownership/consolidation, after this phase's
review and commit/push checkpoint.
