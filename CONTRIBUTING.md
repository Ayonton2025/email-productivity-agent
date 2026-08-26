# Contributing

## Development setup

Use the reproducible offline setup described in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). It uses mock mode and SQLite, so provider credentials are not required for local tests.

For backend work, use Python 3.11 and install the pinned development environment:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
```

For frontend work:

```powershell
Set-Location frontend
npm ci
```

## Branches and pull requests

- Keep `main` deployable.
- Create a focused branch from `main` for each feature or fix.
- Keep pull requests small enough to review and describe the behavior changed.
- Do not commit secrets, local `.env` files, credentials, database files, dependency directories, or build output.
- Update documentation when setup, configuration, or user-visible behavior changes.

## Commit style

Use imperative, focused commit messages with a short type prefix:

```text
feat: add deterministic mock billing flow
test: cover payment initialization failures
fix: validate payment amounts
refactor: split billing provider service
docs: document local test setup
ci: run security checks on pull requests
```

A commit should contain one coherent change and its tests. Avoid combining formatting-only work, unrelated refactors, and features in one commit.

## Required checks

Run the relevant checks before opening a pull request. From `backend/`:

```powershell
python -m pytest tests --cov=app --cov-report=term-missing
python -m ruff check app tests
python -m ruff format --check app tests
python -m mypy app
python -m bandit -c pyproject.toml -r app
```

From `frontend/`:

```powershell
npm test -- --run
npm run lint
npm run format:check
npm run typecheck
npm run build
```

The GitHub Actions quality workflow runs these checks, dependency audits, and the frontend build on every push and pull request.

## Tests and review

- Add or update tests with every behavior change.
- Prefer isolated tests that do not call external APIs or payment providers.
- Use mock mode for billing, AI, email, FX, and GeoIP tests.
- Add regression coverage for every bug fix.
- Review migrations and configuration changes for backward compatibility.
