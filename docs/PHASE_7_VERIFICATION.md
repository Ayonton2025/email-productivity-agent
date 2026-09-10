# Phase 7: Existing Sentry integration and application wiring

This phase follows the repository-specific Phase 7 in the supplied feedback,
starting from Phase 6 commit `829e1d4` on branch `phase-7-monitoring-contract`.
The requirement is to verify the existing integration rather than rebuild it.

## Requirement-by-requirement review

- `main.py` imports and calls `monitoring.initialize_monitoring()` during module
  initialization; the Celery app also calls this shared helper. Sentry setup
  remains in `core/monitoring.py`.
- An empty `SENTRY_DSN` disables initialization and handled-exception forwarding.
  Tests now assert that neither SDK function is called in this mode.
- Enabled configuration tests assert the DSN, environment, release, trace sampling,
  `send_default_pii=False`, and FastAPI/Celery/SQLAlchemy/logging integrations.
- Handled-exception tests verify scoped context, exception forwarding and scope exit.
- Fresh-process tests import the real application with monitoring enabled/disabled.
  The enabled test uses the real SDK with an in-memory transport, verifies the
  bootstrap call, captures the intentional debug-route exception and a handled
  exception, and checks handled context does not leak into other events.
- The test suite explicitly disables monitoring by default. Opt-in tests use mock
  SDK calls or the in-memory transport, so no telemetry is sent to a hosted project.
- Existing debug-route tests retain the 404 guard with DEBUG disabled and the 500
  response with DEBUG enabled. The application wiring test also verifies the route
  is excluded from OpenAPI.
- Troubleshooting instructions now accurately describe the debug-only route. It is
  not authenticated as a super-admin route, and its guard is independent of DSN.
- The real enabled-SDK test exposed a startup failure: Sentry 2.35.1 instruments
  Starlette templates when MarkupSafe is present, but Starlette 1.6.0 requires
  Jinja2 to import its template module. Jinja2 was absent from runtime requirements.
  Added `Jinja2==3.1.6` consistently to pyproject.toml, requirements.txt and the lock.
  Its MarkupSafe dependency was already pinned. Existing package versions and all
  production Python modules remain unchanged.
- The added version is documented on [PyPI](https://pypi.org/project/Jinja2/3.1.6/).
  This is a targeted compatibility fix; Sentry initialization stays behind the
  existing helper instead of moving into main.py.

The earlier logging, correlation-ID and error-response feedback was handled in
Phases 5 and 6. Those implementations remain intact.

## Verification (2026-09-10)

- Focused Windows monitoring and dependency-contract checks: 17 passed.
- Focused Linux monitoring and dependency-contract checks: 17 passed; the added
  dependency installed successfully and pip check reported no broken requirements.
- Full Windows backend suite: 278 passed; application coverage 36.83% (31% required).
- Maintained-module gate: 278 passed; coverage 84.77% (50% required).
- Security/schema gate: 24 passed; coverage 98.28% (90% required).
- Ruff lint and formatting: passed (239 files checked for formatting).
- Mypy: passed for the configured 19 source files.
- Bandit: configured gate passed with no medium/high findings.
- Dependency audit: no known vulnerabilities.
- Windows installation of the added pinned dependency: passed; pip check reported
  no broken requirements. Existing package versions were retained.
- Final diff whitespace check: passed.

The enabled startup test first exposed the missing Jinja2 dependency. A subsequent
assertion was corrected to account for the existing API and Celery bootstrap calls,
while verifying that both use the monitoring helper and configured SDK options.

## Review checkpoint

Final review confirmed the Phase 7 wiring and monitoring requirements are covered.
The enabled-startup dependency gap is fixed, all verification gates pass, and no
remaining Phase 7 gaps were identified within the repository-specific plan.

Phase 7 review is complete and approved for commit and push. Verification proves
local application/SDK wiring; it does not claim hosted Sentry ingestion, production credential validity
or outbound network availability. No production DSN or service account is used.
