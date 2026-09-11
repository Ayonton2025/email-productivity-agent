# Phase 13: Testing strategy and trustworthy verification

Phase 13 makes the repository's verification contract explicit after the
Phase 12 Gmail extraction. It separates behavioral evidence from quality gates,
and separates the slow cold-model compatibility check from ordinary coverage
runs so failures remain attributable.

## Verification layers

| Layer | Purpose | Examples |
| --- | --- | --- |
| Focused behavior | Prove the changed slice and its edge cases | Gmail parser/persistence tests, route contracts, frontend component tests |
| Full backend quality | Measure regression risk across maintained code | Whole-application, maintained-domain, and security-boundary coverage |
| Static and dependency checks | Catch non-runtime defects | Ruff, formatting, mypy, Bandit, pip-audit |
| Compatibility | Prove cold import and registration behavior | `test_model_compatibility.py -m slow` |
| Clean clone and deployment | Verify installation and isolated runtime behavior | `scripts/verify-fresh-clone.*`, `scripts/verify-compose.sh` |
| Hosted verification | Prove external CI and deployed integrations | GitHub Actions, Gmail delivery, Sentry, deployment checks |

## Changes

- Registered a `slow` pytest marker for compatibility/integration checks.
- Marked the cold model import-order test as slow.
- Removed slow checks from the three coverage suites and added a named CI gate
  that runs them explicitly. The test remains required; it is not skipped.
- Added the same slow compatibility command to the documented local backend
  sequence.
- Documented the evidence each layer provides and the limits of local results.

## Validation

- Phase 12 focused suite remains green: 26 tests passed.
- The cold model compatibility check is a required slow gate with a 300-second
  subprocess budget for Windows mounted-workspace startup variance.
- Ruff, syntax, whitespace, and report-link checks passed for the Phase 12
  implementation and this documentation/configuration change.
- The prior Linux full-suite run reached 318 passing tests and one failure in
  the cold model compatibility test. The failure is retained as historical
  evidence; this phase does not claim an all-green hosted or Linux result.

## Remaining limits

The cold import check still performs real fresh-process imports and can be slow
on mounted filesystems. Hosted CI, live Gmail/watch delivery, hosted Sentry,
and deployment verification require their respective environments. No test
uses production credentials, customer mailboxes, payment keys, or live AI
providers.

Phase 13 is complete when focused evidence, named quality gates, compatibility
checks, and hosted/deployment results are reported separately rather than
collapsed into an unqualified local test-pass claim.
