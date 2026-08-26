# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added

- Reproducible offline development and test setup using mock mode and SQLite.
- Backend and frontend automated test suites covering authentication, billing, AI, email, validation, and core UI flows.
- Ruff, mypy, ESLint, Prettier, Bandit, pip-audit, and npm audit quality checks.
- GitHub Actions quality workflow for tests, lint, type checking, security scans, and frontend builds.
- Dependabot configuration for weekly Python and npm dependency updates.
- Contributor guidance for focused changes, tests, and commit conventions.

### Fixed

- Isolated local test execution from live email, AI, payment, FX, GeoIP, Redis, and Celery providers.
- Added request validation for email addresses, passwords, and payment amounts.

### Changed

- Added structured monitoring integration that remains disabled when `SENTRY_DSN` is not configured.
- Pinned backend runtime and development dependencies for reproducible installs.

## 1.0.0

Initial full-stack email productivity platform release with FastAPI, React, AI-assisted email workflows, billing, provider integrations, and collaboration features.
